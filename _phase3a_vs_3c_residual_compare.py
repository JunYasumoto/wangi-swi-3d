"""Side-by-side comparison: Phase 3a baseline (BOTM_L3=-500m) vs Phase 3c L3-shallow.

Show how the L3-shallow fix reduced the +5m S/SE overshoot to near zero,
while preserving NW residual structure that needs zonation.

Output: figs/phase3a_vs_3c_residuals.png (2 spatial maps + 2 scatter)
"""
import sys, io, pathlib, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

# Load all three Phase 3c head files
p3a = pd.read_csv(WORK / "phase3a_heads_3c_baseline_L2corrected.csv")
p3c = pd.read_csv(WORK / "phase3a_heads_3c_L3shallow.csv")

# Add UTM
ct = pd.read_csv(WORK / "calibration_targets.csv")[["id", "utm_x", "utm_y"]]
p3a = p3a.merge(ct, on="id", how="left")
p3c = p3c.merge(ct, on="id", how="left")

# Apply WW4 truth correction (+2.418) to both
WW4_TRUTH = 2.418
p3a.loc[p3a["id"] == "ww04", "resid"] = p3a.loc[p3a["id"] == "ww04", "sim_used"].values[0] - WW4_TRUTH
p3c.loc[p3c["id"] == "ww04", "resid"] = p3c.loc[p3c["id"] == "ww04", "sim_used"].values[0] - WW4_TRUTH

# Load top + idomain
spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR = cfg.NROW, cfg.NCOL, cfg.DELR
XUL, YUL = cfg.XUL, cfg.YUL
xmin = XUL; xmax = XUL + NCOL*DELR
ymax = YUL; ymin = YUL - NROW*DELR
top = np.load(WORK / "top_elevation.npy")
ido = np.load(WORK / "idomain.npy")
top_m = np.ma.masked_where(ido == 0, top)

fig = plt.figure(figsize=(17, 10))
gs = GridSpec(2, 2, figure=fig, hspace=0.30, wspace=0.25)

PERCHED = {"ww10", "ww14", "ww16"}

def panel_map(ax, df, title, vmax=None):
    main = df[~df["id"].isin(PERCHED)]
    if vmax is None:
        vmax = max(abs(main["resid"].min()), abs(main["resid"].max()))
    ax.imshow(top_m, extent=[xmin, xmax, ymin, ymax], origin="upper",
              cmap="terrain", vmin=0, vmax=200, alpha=0.6)
    ax.imshow(np.where(ido == 0, 1, np.nan), extent=[xmin, xmax, ymin, ymax],
              origin="upper", cmap="Blues_r", vmin=-1, vmax=2, alpha=0.3)
    sc = ax.scatter(main["utm_x"], main["utm_y"], c=main["resid"],
                    cmap="RdBu_r", vmin=-vmax, vmax=vmax, s=170, edgecolor="black",
                    linewidth=1.3, zorder=4)
    perched = df[df["id"].isin(PERCHED)]
    ax.scatter(perched["utm_x"], perched["utm_y"], marker="x", c="gray", s=110,
               linewidth=2, zorder=3)
    for _, r in main.iterrows():
        ax.annotate(f"{r['id']}\n{r['resid']:+.1f}", (r["utm_x"], r["utm_y"]),
                    xytext=(6, 4), textcoords="offset points",
                    fontsize=6, bbox=dict(boxstyle="round,pad=0.1", fc="white",
                                          alpha=0.6, edgecolor="none"))
    cb = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("Residual (m)", fontsize=9)
    ax.set_aspect("equal")
    ax.set_xlim(551500, 575000); ax.set_ylim(9402000, 9425500)
    rmse = np.sqrt((main["resid"]**2).mean())
    bias = main["resid"].mean()
    ax.set_title(f"{title}\nRMSE = {rmse:.2f} m, bias = {bias:+.2f} m",
                 fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3)
    return vmax

def panel_scatter(ax, df, title, vmax=None):
    main = df[~df["id"].isin(PERCHED)]
    if vmax is None:
        vmax = max(abs(main["resid"].min()), abs(main["resid"].max()))
    obs_used = main["sim_used"] - main["resid"]
    ax.scatter(obs_used, main["sim_used"], c=main["resid"],
               cmap="RdBu_r", vmin=-vmax, vmax=vmax, s=120, edgecolor="black",
               linewidth=1.0, zorder=4)
    for _, r in main.iterrows():
        ax.annotate(r["id"], (r["sim_used"]-r["resid"], r["sim_used"]),
                    xytext=(4, 3), textcoords="offset points", fontsize=7)
    lo, hi = 0, 11
    ax.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax.plot([lo, hi], [lo+1, hi+1], "k:", lw=0.5, alpha=0.6)
    ax.plot([lo, hi], [lo-1, hi-1], "k:", lw=0.5, alpha=0.6)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_xlabel("Obs head (m, MSL)", fontsize=10)
    ax.set_ylabel("Sim L2 (m)", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3)

# Use same colormap range for both maps for fair comparison
vmax_global = 6.0

ax = fig.add_subplot(gs[0, 0])
panel_map(ax, p3a, "(a) Phase 3a baseline (BOTM_L3=-500m)", vmax=vmax_global)
ax = fig.add_subplot(gs[0, 1])
panel_map(ax, p3c, "(b) Phase 3c L3-shallow (BOTM_L3=-200m)", vmax=vmax_global)

ax = fig.add_subplot(gs[1, 0])
panel_scatter(ax, p3a, "(c) Phase 3a baseline — sim vs obs", vmax=vmax_global)
ax = fig.add_subplot(gs[1, 1])
panel_scatter(ax, p3c, "(d) Phase 3c L3-shallow — sim vs obs", vmax=vmax_global)

fig.suptitle("Phase 3a baseline vs Phase 3c L3-shallow — residual evolution\n"
             "L3-shallow removes the +5m S/SE inflation while preserving lens dynamics\n"
             "(WW4 uses corrected truth +2.418 m MSL for both)",
             fontsize=13, fontweight="bold", y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.96])
out = FIGDIR / "phase3a_vs_3c_residuals.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")

# Print summary table
def print_zones(df, label):
    main = df[~df["id"].isin(PERCHED)]
    NW = {"ww02","ww03","ww17","ww18","ww19","ww05","ww06"}
    SSE = {"ww07","ww08","ww09","ww13","ww15"}
    CENT = {"ww04","ww11","ww12","ww20"}
    print(f"\n{label}")
    for zone_name, zset in [("NW + extreme S coastal", NW),
                              ("S/SE/E inland", SSE),
                              ("Central / Kantamare", CENT)]:
        sub = main[main["id"].isin(zset)]
        if len(sub) > 0:
            print(f"  {zone_name:30s} n={len(sub):2d}, RMSE = {np.sqrt((sub['resid']**2).mean()):5.2f} m, "
                  f"bias = {sub['resid'].mean():+5.2f} m")
    print(f"  Overall                        n={len(main):2d}, "
          f"RMSE = {np.sqrt((main['resid']**2).mean()):5.2f} m, "
          f"bias = {main['resid'].mean():+5.2f} m")

print_zones(p3a, "=== Phase 3a baseline ===")
print_zones(p3c, "=== Phase 3c L3-shallow ===")
