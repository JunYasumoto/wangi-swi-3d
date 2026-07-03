"""Spatial residual map: sim L2 head − obs at each well, plotted on island map.

Visualizes NW under / S-SE over二峰性 — motivation for Phase 3c zonation改善.

Output: figs/residual_map_L2_baseline.png
"""
import sys, io, pathlib, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"; FIGDIR.mkdir(exist_ok=True)

spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR = cfg.NROW, cfg.NCOL, cfg.DELR
XUL, YUL = cfg.XUL, cfg.YUL
xmin = XUL; xmax = XUL + NCOL * DELR
ymax = YUL; ymin = YUL - NROW * DELR

top = np.load(WORK / "top_elevation.npy")
ido = np.load(WORK / "idomain.npy")
top_m = np.ma.masked_where(ido == 0, top)

# Load L2-corrected heads
df = pd.read_csv(WORK / "phase3a_heads_3c_baseline_L2corrected.csv")
# Bring UTM coords back from calibration_targets
ct = pd.read_csv(WORK / "calibration_targets.csv")[["id", "utm_x", "utm_y"]]
df = df.merge(ct, on="id", how="left")
# Exclude perched for the comparison
main = df[~df["perched"]].copy()

fig, axes = plt.subplots(1, 2, figsize=(18, 9), gridspec_kw={"width_ratios": [1.0, 1.0]})

# === Panel 1: residual map ===
ax = axes[0]
ax.imshow(top_m, extent=[xmin, xmax, ymin, ymax], origin="upper",
          cmap="terrain", vmin=0, vmax=200, alpha=0.7)
ax.imshow(np.where(ido == 0, 1, np.nan), extent=[xmin, xmax, ymin, ymax],
          origin="upper", cmap="Blues_r", vmin=-1, vmax=2, alpha=0.3)
# Plot main aquifer wells colored by residual
rmax = max(abs(main["resid"].min()), abs(main["resid"].max()))
sc = ax.scatter(main["utm_x"], main["utm_y"], c=main["resid"],
                 cmap="RdBu_r", vmin=-rmax, vmax=rmax, s=200, edgecolor="black",
                 linewidth=1.5, zorder=4)
# Label each well
for _, r in main.iterrows():
    ax.annotate(r["id"], (r["utm_x"], r["utm_y"]),
                xytext=(8, 6), textcoords="offset points",
                fontsize=8, color="black",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.65, edgecolor="none"))
# Perched wells (excluded) as gray X
perched = df[df["perched"]]
ax.scatter(perched["utm_x"], perched["utm_y"], marker="x", c="gray", s=120,
           linewidth=2, zorder=3)
for _, r in perched.iterrows():
    ax.annotate(f"{r['id']} (perched)", (r["utm_x"], r["utm_y"]),
                xytext=(8, -10), textcoords="offset points",
                fontsize=8, color="gray")
cb = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
cb.set_label("Residual (sim L2 − obs, m)", fontsize=11)
ax.set_aspect("equal")
ax.set_xlim(551500, 575000); ax.set_ylim(9402000, 9425000)
ax.set_xlabel("UTM Easting (m, UTM 51S)")
ax.set_ylabel("UTM Northing (m)")
ax.set_title("L2 head residual map (Phase 3a baseline, L2-corrected)\n"
             "RMSE = 2.22 m (PEST 2.53 m), bias = -0.58 m\n"
             "Blue = sim under, Red = sim over", fontsize=11)
ax.grid(alpha=0.3)
# NW / S-SE pattern annotation
ax.annotate("NW: sim UNDER\n(coast pull)",
            xy=(557500, 9420000), xytext=(553000, 9423000),
            arrowprops=dict(arrowstyle="->", color="blue", lw=1.5),
            fontsize=10, color="blue", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85, edgecolor="blue"))
ax.annotate("S/SE: sim OVER\n(L3 density push)",
            xy=(565000, 9407000), xytext=(569500, 9404500),
            arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
            fontsize=10, color="red", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85, edgecolor="red"))

# === Panel 2: sim vs obs scatter ===
ax2 = axes[1]
ax2.scatter(main["obs"], main["sim_used"], c=main["resid"],
            cmap="RdBu_r", vmin=-rmax, vmax=rmax, s=140, edgecolor="black", linewidth=1.5)
lo = min(main["obs"].min(), main["sim_used"].min()) - 0.5
hi = max(main["obs"].max(), main["sim_used"].max()) + 0.5
ax2.plot([lo, hi], [lo, hi], "k--", lw=1, alpha=0.6, label="1:1")
ax2.plot([lo, hi], [lo + 1, hi + 1], "k:", lw=0.7, alpha=0.4, label="±1 m")
ax2.plot([lo, hi], [lo - 1, hi - 1], "k:", lw=0.7, alpha=0.4)
for _, r in main.iterrows():
    ax2.annotate(r["id"], (r["obs"], r["sim_used"]),
                  xytext=(5, 4), textcoords="offset points", fontsize=8)
ax2.set_xlim(lo, hi); ax2.set_ylim(lo, hi)
ax2.set_xlabel("Observed head (m, MSL)", fontsize=11)
ax2.set_ylabel("Simulated L2 head (m, MSL)", fontsize=11)
ax2.set_title("Sim L2 vs Obs at 17 main aquifer wells\n"
              f"RMSE = 2.22 m, bias = -0.58 m, n = 17", fontsize=11)
ax2.legend(loc="upper left", fontsize=9)
ax2.grid(alpha=0.3)
ax2.set_aspect("equal")

plt.tight_layout()
out = FIGDIR / "residual_map_L2_baseline.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")
print(f"\nSpatial pattern statistics:")
main_n_under = (main["resid"] < -1.0).sum()
main_n_over  = (main["resid"] >  1.0).sum()
main_n_ok    = ((main["resid"].abs() <= 1.0)).sum()
print(f"  |resid| ≤ 1 m: {main_n_ok}/{len(main)} wells")
print(f"  resid < -1 m (sim under): {main_n_under} — {list(main[main['resid'] < -1.0]['id'])}")
print(f"  resid > +1 m (sim over) : {main_n_over} — {list(main[main['resid'] >  1.0]['id'])}")
