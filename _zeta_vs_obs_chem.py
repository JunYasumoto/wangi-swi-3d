"""Compare model ζ depth at each well location with observed seawater fraction.

This is a direct SWI validation: wells far above ζ should have pure freshwater,
wells close to ζ should show seawater intrusion (high Cl).

Outputs:
  zeta_vs_chem.csv
  figs/zeta_vs_chem_validation.png
"""
import sys, io, pathlib, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd, flopy
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
WS_3A = WORK / "phase3a_ss"

spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR = cfg.NROW, cfg.NCOL, cfg.DELR
XUL, YUL = cfg.XUL, cfg.YUL

# Load ζ from Phase 3a SS
zta = flopy.utils.binaryfile.HeadFile(str(WS_3A / "gwf.zta"),
                                       text="ZETA").get_data(kstpkper=(0, 0))
# Filter HDRY sentinel (1e30)
zta = np.where(np.abs(zta) > 1e9, np.nan, zta)
print(f"ζ shape: {zta.shape}")
print(f"  L1 ζ: {np.nanmin(zta[0]):.1f} .. {np.nanmax(zta[0]):.1f} mean {np.nanmean(zta[0]):.1f}")
print(f"  L2 ζ: {np.nanmin(zta[1]):.1f} .. {np.nanmax(zta[1]):.1f} mean {np.nanmean(zta[1]):.1f}")
print(f"  L3 ζ: {np.nanmin(zta[2]):.1f} .. {np.nanmax(zta[2]):.1f} mean {np.nanmean(zta[2]):.1f}")
top = np.load(WORK / "top_elevation.npy")
botm3 = np.full_like(top, -500.0)

# Load chem + well coords
chem = pd.read_csv(WORK / "ww_isotope_chem.csv")
# Convert WW1 → ww01, WW10 → ww10, etc.
def well_to_id(w):
    n = int(w.replace("WW", ""))
    return f"ww{n:02d}"
chem["id"] = chem["well"].apply(well_to_id)
wells_ct = pd.read_csv(WORK / "calibration_targets.csv")[["id", "utm_x", "utm_y"]]
chem = chem.merge(wells_ct, on="id", how="left")
print(chem[["well", "id", "utm_x", "utm_y"]].head())

# Endmembers
SEAWATER_CL = 19000.0; RAIN_CL = 3.0
chem["sw_frac_pct"] = (chem["Cl"] - RAIN_CL) / (SEAWATER_CL - RAIN_CL) * 100

# At each well location, get model ζ in L1, L2, L3 (where finite)
def get_zeta(row):
    if pd.isna(row.get("utm_x")): return pd.Series([np.nan]*4, index=["zeta_L1","zeta_L2","zeta_L3","zeta_min"])
    r = int((YUL - row["utm_y"]) / DELR)
    c = int((row["utm_x"] - XUL) / DELR)
    if not (0 <= r < NROW and 0 <= c < NCOL):
        return pd.Series([np.nan]*4, index=["zeta_L1","zeta_L2","zeta_L3","zeta_min"])
    z1 = zta[0, r, c] if abs(zta[0, r, c]) < 1e9 else np.nan
    z2 = zta[1, r, c] if abs(zta[1, r, c]) < 1e9 else np.nan
    z3 = zta[2, r, c] if abs(zta[2, r, c]) < 1e9 else np.nan
    # The lowest finite ζ is the actual fresh-salt interface
    zmin = np.nanmin([z1, z2, z3])
    return pd.Series([z1, z2, z3, zmin], index=["zeta_L1","zeta_L2","zeta_L3","zeta_min"])

zeta_at_wells = chem.apply(get_zeta, axis=1)
chem = pd.concat([chem, zeta_at_wells], axis=1)
# Distance from ground (top) to ζ = lens thickness above the wedge
def get_topo(row):
    if pd.isna(row.get("utm_x")): return np.nan
    r = int((YUL - row["utm_y"]) / DELR)
    c = int((row["utm_x"] - XUL) / DELR)
    if 0 <= r < NROW and 0 <= c < NCOL:
        return float(top[r, c])
    return np.nan
chem["topo_m"] = chem.apply(get_topo, axis=1)
chem["lens_thickness_m"] = chem["topo_m"] - chem["zeta_min"]

print("\n=== ζ at well locations + observed seawater fraction ===")
keep = ["well", "topo_m", "zeta_L1", "zeta_L2", "zeta_L3", "zeta_min",
        "lens_thickness_m", "Cl", "sw_frac_pct"]
print(chem[keep].to_string(index=False))

chem[keep].to_csv(WORK / "zeta_vs_chem.csv", index=False, float_format="%.2f")

# === Plot ===
fig, axes = plt.subplots(1, 2, figsize=(15, 7))

# Panel A: lens thickness vs Cl
ax = axes[0]
PERCHED = {"ww10", "ww14", "ww16"}
nperc = chem[~chem["well"].str.lower().isin(PERCHED)]
ax.scatter(nperc["lens_thickness_m"], nperc["Cl"], s=180,
            c=nperc["sw_frac_pct"], cmap="plasma", vmin=0, vmax=12,
            edgecolor="black", linewidth=1.5, zorder=4)
for _, r in nperc.iterrows():
    ax.annotate(r["well"], (r["lens_thickness_m"], r["Cl"]),
                 xytext=(6, 5), textcoords="offset points", fontsize=10)
ax.set_xlabel("Model lens thickness above ζ at well (m)", fontsize=11)
ax.set_ylabel("Observed Cl⁻ (mg/L)", fontsize=11)
ax.set_yscale("log")
ax.set_title("Model lens thickness vs observed Cl⁻\n"
             "(thicker lens → expect lower Cl, but other factors matter)",
             fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, which="both")
# Trend line
if len(nperc) > 3:
    valid = nperc[nperc["lens_thickness_m"].notna() & nperc["Cl"].notna()]
    if len(valid) > 2:
        from scipy.stats import spearmanr
        rho, p = spearmanr(valid["lens_thickness_m"], valid["Cl"])
        ax.text(0.05, 0.95, f"Spearman ρ = {rho:.2f}\np = {p:.3f}",
                transform=ax.transAxes, va="top",
                bbox=dict(fc="lightyellow", alpha=0.9, edgecolor="black"))

# Panel B: bar — ζ position + lens thickness + Cl
ax2 = axes[1]
sorted_chem = nperc.sort_values("Cl").reset_index(drop=True)
wells_x = np.arange(len(sorted_chem))
# Top of lens (ground)
ax2.bar(wells_x, sorted_chem["topo_m"], color="lightgreen", edgecolor="black",
         linewidth=0.8, label="Ground topo")
# Lens bottom (ζ min)
ax2.bar(wells_x, sorted_chem["zeta_min"], color="lightcoral", edgecolor="black",
         linewidth=0.8, label="ζ (fresh-salt interface)")
ax2.axhline(0, color="navy", ls="--", lw=1, alpha=0.7)
for i, r in sorted_chem.iterrows():
    ax2.text(i, r["topo_m"] + 5, f"{r['well']}\nCl={r['Cl']:.0f}\nsw={r['sw_frac_pct']:.1f}%",
              ha="center", fontsize=8)
ax2.set_xticks(wells_x)
ax2.set_xticklabels([w for w in sorted_chem["well"]], rotation=45, ha="right")
ax2.set_ylabel("Elevation (m, MSL)", fontsize=11)
ax2.set_title("Model lens depth profile at each well\n"
              "(ordered by observed Cl⁻; ζ deeper = more freshwater = lower Cl?)",
              fontsize=11, fontweight="bold")
ax2.legend(loc="lower left")
ax2.grid(alpha=0.3, axis="y")

plt.tight_layout()
out = WORK / "figs" / "zeta_vs_chem_validation.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"\nSaved: {out}")
