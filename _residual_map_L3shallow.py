"""Residual map for L3-shallow scenario — visualize NW under residual after L3 fix."""
import sys, io, pathlib, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd, flopy
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"
WS = WORK / "phase3a_ss_3c_L3shallow"

spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR = cfg.NROW, cfg.NCOL, cfg.DELR
XUL, YUL = cfg.XUL, cfg.YUL
xmin = XUL; xmax = XUL + NCOL * DELR
ymax = YUL; ymin = YUL - NROW * DELR

top_arr = np.load(WORK / "top_elevation.npy")
ido = np.load(WORK / "idomain.npy")
top_m = np.ma.masked_where(ido == 0, top_arr)

heads = pd.read_csv(WORK / "phase3a_heads_3c_L3shallow.csv")
heads["utm_x"] = pd.read_csv(WORK / "calibration_targets.csv")["utm_x"].values
heads["utm_y"] = pd.read_csv(WORK / "calibration_targets.csv")["utm_y"].values

main = heads[~heads["perched"]].copy()
PEST_ww4_inflated = 4.155; HOBO_ww4_truth = 2.378
# Build residual using L2 sim_used vs obs
# Add a corrected version for WW4
main["resid_corr"] = main["resid"]
main.loc[main["id"] == "ww04", "resid_corr"] = main.loc[main["id"] == "ww04", "sim_used"].values - HOBO_ww4_truth

# Side-by-side: residual using PEST obs vs corrected obs
fig, axes = plt.subplots(1, 2, figsize=(18, 9))

for col, (resid_col, title) in enumerate([
    ("resid", "L3-shallow vs PEST obs (n=17)"),
    ("resid_corr", "L3-shallow vs corrected obs\n(WW4 → 2.378m HOBO truth)"),
]):
    ax = axes[col]
    ax.imshow(top_m, extent=[xmin, xmax, ymin, ymax], origin="upper",
              cmap="terrain", vmin=0, vmax=200, alpha=0.65)
    ax.imshow(np.where(ido == 0, 1, np.nan), extent=[xmin, xmax, ymin, ymax],
              origin="upper", cmap="Blues_r", vmin=-1, vmax=2, alpha=0.3)
    rmax = max(abs(main[resid_col].min()), abs(main[resid_col].max()))
    sc = ax.scatter(main["utm_x"], main["utm_y"], c=main[resid_col],
                    cmap="RdBu_r", vmin=-rmax, vmax=rmax, s=180, edgecolor="black",
                    linewidth=1.3, zorder=4)
    for _, r in main.iterrows():
        ax.annotate(f"{r['id']}\n{r[resid_col]:+.1f}", (r["utm_x"], r["utm_y"]),
                    xytext=(7, 5), textcoords="offset points",
                    fontsize=7, color="black",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.65,
                              edgecolor="none"))
    perched = heads[heads["perched"]]
    ax.scatter(perched["utm_x"], perched["utm_y"], marker="x", c="gray", s=120,
               linewidth=2, zorder=3)
    cb = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("Residual sim L2 − obs (m)", fontsize=10)
    ax.set_aspect("equal")
    ax.set_xlim(551500, 575000); ax.set_ylim(9402000, 9425500)
    ax.set_xlabel("UTM Easting (m)"); ax.set_ylabel("UTM Northing (m)")
    ax.set_title(f"{title}\nRMSE = {np.sqrt((main[resid_col]**2).mean()):.2f} m, "
                  f"bias = {main[resid_col].mean():+.2f} m",
                  fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3)

fig.suptitle("Phase 3c L3-shallow (BOTM_L3 = -200 m) — L3 density push removed\n"
             "Inland S/SE residual (was +5m) now matches obs; NW under (-3m) becomes the new target for K2 zonation",
             fontsize=13, fontweight="bold", y=1.02)
plt.tight_layout()
out = FIGDIR / "residual_map_L3shallow.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")

# Print summary
print(f"\n=== Phase 3c L3-shallow residual summary ===")
print(f"PEST obs (uncorrected):")
print(f"  RMSE: {np.sqrt((main['resid']**2).mean()):.3f} m, bias: {main['resid'].mean():+.3f}")
print(f"Corrected WW4 only (4.155 → 2.378):")
print(f"  RMSE: {np.sqrt((main['resid_corr']**2).mean()):.3f} m, bias: {main['resid_corr'].mean():+.3f}")
print(f"\nBy zone:")
NW_wells = {"ww02","ww03","ww17","ww18","ww19","ww05","ww06"}
SSE_wells = {"ww07","ww08","ww09","ww13","ww15"}
CENT_wells = {"ww04","ww11","ww12","ww20"}
for label, wset in [("NW (was under)", NW_wells), ("S/SE (was over)", SSE_wells),
                     ("Central/Kantamare", CENT_wells)]:
    sub = main[main["id"].isin(wset)]
    print(f"  {label:25s} n={len(sub)}, RMSE = {np.sqrt((sub['resid']**2).mean()):5.2f} m, "
          f"bias = {sub['resid'].mean():+5.2f} m")
