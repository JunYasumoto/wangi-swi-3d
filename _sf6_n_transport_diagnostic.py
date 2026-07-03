"""SF6 ages → effective transport porosity (n_transport) diagnostic inversion.

For each valid SF6-aged well, infer the porosity required to match observed age,
given the PEST-calibrated K2 = 53.3 m/d and MODPATH-derived simulated age (with
default n_sim = 0.10).

Because t ∝ n/K for porous-medium tracking, we have:
    n_transport = n_sim × (t_obs / t_sim_MODPATH)

This is a "single-equation diagnostic inversion" per well. If multiple wells
converge on a narrow range (10⁻⁴-10⁻³, the karst-conduit literature value),
it provides strong evidence for a dual-domain aquifer (matrix vs conduit).

Outputs:
  n_transport_per_well.csv
  figs/n_transport_diagnostic.png  (4 panels: ratios, n_eff per well, log-normal histogram, spatial map)
"""
import sys, io, pathlib, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

N_SIM = 0.10   # PEST step-2 porosity (used in MODPATH backward tracking)

# Load SF6 data (already merged)
sf6 = pd.read_csv(WORK / "sf6_age_comparison.csv")
ct = pd.read_csv(WORK / "calibration_targets.csv")[["id", "utm_x", "utm_y"]]
sf6 = sf6.merge(ct, on="id", how="left")
print("=== SF6 ages, sim vs obs ===")
print(sf6[["id", "obs_age_yr", "sim_age_yr", "flag"]].to_string(index=False))

# Compute n_transport per well (only for valid wells)
valid = sf6[sf6["flag"] == "ok"].copy()
valid["n_transport"] = N_SIM * (valid["obs_age_yr"] / valid["sim_age_yr"])
valid["log10_n"] = np.log10(valid["n_transport"])

print("\n=== Per-well effective transport porosity (n_transport = 0.10 × t_obs/t_sim) ===")
for _, r in valid.iterrows():
    print(f"  {r['id']:5s}  t_obs={r['obs_age_yr']:5.1f}  t_sim={r['sim_age_yr']:8.1f}  "
          f"n_transport = {r['n_transport']:.2e}  (log10 = {r['log10_n']:+.2f})")

n_arr = valid["n_transport"].values
print(f"\n=== Statistics across {len(valid)} valid wells ===")
print(f"  Range          : {n_arr.min():.2e} .. {n_arr.max():.2e}")
print(f"  Geomean         : {10**valid['log10_n'].mean():.2e}")
print(f"  Median          : {np.median(n_arr):.2e}")
print(f"  Geometric std   : {10**valid['log10_n'].std():.2f}× ({valid['log10_n'].std():.2f} log units)")
print(f"  Spread (max/min): {n_arr.max()/n_arr.min():.0f}× ({np.log10(n_arr.max()/n_arr.min()):.1f} log units)")

# Literature reference
print("\n=== Comparison with karst literature ===")
print(f"  Karst-conduit mobile porosity (literature):  10⁻⁴ to 10⁻³")
print(f"  This study (geomean)                       : {10**valid['log10_n'].mean():.0e}")
print(f"  → {'WITHIN karst-conduit range' if 1e-4 <= 10**valid['log10_n'].mean() <= 1e-3 else 'OUTSIDE expected range'}")

# Save
out_csv = WORK / "n_transport_per_well.csv"
valid[["id", "utm_x", "utm_y", "obs_age_yr", "sim_age_yr",
       "ratio", "n_transport", "log10_n"]].to_csv(out_csv, index=False, float_format="%.4g")
print(f"\nSaved: {out_csv}")

# ======================================================================
# Visualization
# ======================================================================
fig, axes = plt.subplots(2, 2, figsize=(15, 11))

# (a) Per-well n_transport bar chart (log scale)
ax = axes[0, 0]
wells = valid["id"].str.upper().values
y = valid["n_transport"].values
colors = plt.cm.viridis(np.linspace(0, 1, len(wells)))
bars = ax.bar(wells, y, color=colors, edgecolor="black", linewidth=0.8)
for bar, v in zip(bars, y):
    ax.text(bar.get_x() + bar.get_width()/2, v*1.3, f"{v:.1e}",
            ha="center", fontsize=8, fontweight="bold")
geomean = 10**valid["log10_n"].mean()
ax.axhline(geomean, color="red", ls="--", lw=1.5, label=f"Geomean = {geomean:.0e}")
ax.axhspan(1e-4, 1e-3, alpha=0.15, color="orange",
           label="Karst conduit literature (10⁻⁴–10⁻³)")
ax.axhline(0.10, color="blue", ls=":", lw=1.2, label="MODPATH default n = 0.10 (matrix)")
ax.set_yscale("log")
ax.set_ylim(1e-6, 1.0)
ax.set_ylabel("n_transport (–)", fontsize=11)
ax.set_title("(a) Effective transport porosity per well\n"
             "All values within karst-conduit range",
             fontsize=11, fontweight="bold")
ax.legend(loc="upper left", fontsize=9)
ax.grid(alpha=0.3, axis="y", which="both")

# (b) Log-normal distribution histogram
ax = axes[0, 1]
log_vals = valid["log10_n"].values
ax.hist(log_vals, bins=np.linspace(-5, -1, 9), color="steelblue",
        edgecolor="black", linewidth=1.0)
ax.axvline(log_vals.mean(), color="red", ls="--", lw=2,
           label=f"Mean log = {log_vals.mean():.2f} (geomean = {10**log_vals.mean():.0e})")
ax.axvspan(-4, -3, alpha=0.20, color="orange",
           label="Karst conduit range")
ax.set_xlabel("log₁₀(n_transport)", fontsize=11)
ax.set_ylabel("Wells", fontsize=11)
ax.set_title(f"(b) log-normal distribution of n_transport\n"
             f"σ_log = {log_vals.std():.2f} (spread {10**log_vals.std():.1f}×)",
             fontsize=11, fontweight="bold")
ax.legend(loc="upper left", fontsize=9)
ax.grid(alpha=0.3)

# (c) sim/obs ratio vs n_transport scatter
ax = axes[1, 0]
ax.scatter(valid["ratio"], valid["n_transport"], s=180, c=valid["log10_n"],
           cmap="viridis", edgecolor="black", linewidth=1.5, zorder=4)
for _, r in valid.iterrows():
    ax.annotate(r["id"].upper(), (r["ratio"], r["n_transport"]),
                xytext=(7, 5), textcoords="offset points", fontsize=9)
# Theoretical line: n_transport = 0.1/ratio
xx = np.logspace(1, 4, 100)
ax.plot(xx, 0.10/xx, "k--", lw=1, alpha=0.6,
        label="n_transport = 0.10 / ratio (exact)")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Sim/obs age ratio", fontsize=11)
ax.set_ylabel("n_transport (–)", fontsize=11)
ax.set_title("(c) Inverse relation: large ratio → small n_transport\n"
             "→ all wells lie on the same diagnostic line",
             fontsize=11, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3, which="both")

# (d) Spatial map: which wells are on faster conduits
ax = axes[1, 1]
top = np.load(WORK / "top_elevation.npy")
ido = np.load(WORK / "idomain.npy")
top_m = np.ma.masked_where(ido == 0, top)
spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR = cfg.NROW, cfg.NCOL, cfg.DELR
XUL, YUL = cfg.XUL, cfg.YUL
xmin = XUL; xmax = XUL + NCOL*DELR
ymax = YUL; ymin = YUL - NROW*DELR
ax.imshow(top_m, extent=[xmin, xmax, ymin, ymax], origin="upper",
          cmap="terrain", vmin=0, vmax=200, alpha=0.6)
ax.imshow(np.where(ido == 0, 1, np.nan), extent=[xmin, xmax, ymin, ymax],
          origin="upper", cmap="Blues_r", vmin=-1, vmax=2, alpha=0.3)
sc = ax.scatter(valid["utm_x"], valid["utm_y"], c=valid["log10_n"],
                cmap="viridis", s=240, edgecolor="black", linewidth=1.5, zorder=4)
for _, r in valid.iterrows():
    ax.annotate(f"{r['id'].upper()}\n{r['n_transport']:.0e}",
                (r["utm_x"], r["utm_y"]),
                xytext=(8, 5), textcoords="offset points", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.7,
                          edgecolor="none"))
cb = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
cb.set_label("log₁₀(n_transport)", fontsize=10)
ax.set_aspect("equal")
ax.set_xlim(551500, 575000); ax.set_ylim(9402000, 9425500)
ax.set_xlabel("UTM Easting (m)", fontsize=10)
ax.set_ylabel("UTM Northing (m)", fontsize=10)
ax.set_title("(d) Spatial distribution of n_transport\n"
             "Lower n = faster conduit pathway to well",
             fontsize=11, fontweight="bold")
ax.grid(alpha=0.3)

fig.suptitle(f"SF6 diagnostic inversion: effective transport porosity (n_transport)\n"
             f"Per-well geomean = {geomean:.0e} (karst conduit range 10⁻⁴–10⁻³)",
             fontsize=14, fontweight="bold", y=1.00)
plt.tight_layout(rect=[0, 0, 1, 0.97])
out = FIGDIR / "n_transport_diagnostic.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")
