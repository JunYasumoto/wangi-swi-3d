"""Paper 2 Fig 1: Site map / hydrogeological setting.

Wangi-Wangi island with DEM hillshade, 20 wells colored by residual class
(NW under / S-SE over / OK / perched), Kantamare HOBO, west coast EPS zone,
12-transect overlay (small), Wakatobi inset.

Outputs:
  figs/paper2_fig1_site_map.png  (high-DPI)
  figs/paper2_fig1_site_map.pdf  (vector)
"""
import sys, io, pathlib, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.colors import LightSource

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

# Hillshade for terrain texture
ls = LightSource(azdeg=315, altdeg=45)
hs = ls.shade(top, cmap=plt.cm.terrain, vert_exag=2.0, blend_mode="overlay",
              vmin=0, vmax=200)
# Mask sea
sea_mask = (ido == 0)

# Wells with residual classification
df = pd.read_csv(WORK / "phase3a_heads_3c_baseline_L2corrected.csv")
ct = pd.read_csv(WORK / "calibration_targets.csv")[["id", "utm_x", "utm_y", "ground_elev"]] \
       if False else pd.read_csv(WORK / "calibration_targets.csv")[["id", "utm_x", "utm_y"]]
df = df.merge(ct, on="id", how="left")

def category(row):
    if row["perched"]: return "perched"
    r = row["resid"]
    if abs(r) <= 1.0: return "ok"
    return "under" if r < 0 else "over"
df["category"] = df.apply(category, axis=1)

CAT_COLOR = {"perched": "gray", "ok": "#2ca02c", "under": "#1f77b4", "over": "#d62728"}
CAT_MARKER = {"perched": "x", "ok": "o", "under": "v", "over": "^"}
CAT_LABEL = {"perched": "Perched (excluded, n=3)",
             "ok":      "L2 sim ≈ obs (|res|≤1m, n=5)",
             "under":   "Sim under (NW Wangi, n=7)",
             "over":    "Sim over (S/SE/E, n=5)"}

# Kantamare HOBO + EPS zone
KANT_X, KANT_Y = 559298.124, 9412207.827
EPS_X_MIN, EPS_X_MAX = 553000, 558000
EPS_Y_MIN, EPS_Y_MAX = 9408500, 9420000

# Figure
fig = plt.figure(figsize=(13, 11))
ax = fig.add_axes([0.07, 0.08, 0.72, 0.88])

# Sea (blue)
ax.imshow(np.where(sea_mask, 1, np.nan), extent=[xmin, xmax, ymin, ymax],
          origin="upper", cmap="Blues", vmin=0, vmax=2, alpha=0.55)
# Land hillshade
land_rgba = hs.copy()
land_rgba[sea_mask] = (1, 1, 1, 0)
ax.imshow(land_rgba, extent=[xmin, xmax, ymin, ymax], origin="upper", alpha=0.95)

# Contours: 50/100/150/200 m
levels = [50, 100, 150, 200, 250]
cs = ax.contour(np.where(ido == 1, top, np.nan),
                levels=levels,
                extent=[xmin, xmax, ymin, ymax], origin="upper",
                colors="black", linewidths=0.5, alpha=0.4)
ax.clabel(cs, inline=True, fontsize=7, fmt="%d m")

# Wells by category
for cat in ["under", "ok", "over", "perched"]:
    sub = df[df["category"] == cat]
    ax.scatter(sub["utm_x"], sub["utm_y"], c=CAT_COLOR[cat],
               marker=CAT_MARKER[cat], s=170 if cat != "perched" else 200,
               edgecolor="black", linewidth=1.2 if cat != "perched" else 2.0,
               label=CAT_LABEL[cat], zorder=10)
    for _, r in sub.iterrows():
        ax.annotate(r["id"].upper(), (r["utm_x"], r["utm_y"]),
                    xytext=(8, 6), textcoords="offset points",
                    fontsize=7, color="black", zorder=11,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.6, edgecolor="none"))

# Kantamare HOBO star
ax.plot(KANT_X, KANT_Y, marker="*", ms=28, mfc="gold", mec="black", mew=1.5,
        label="Kantamare HOBO (WW4)", zorder=12)

# Highland pivot
top_land = np.where(ido == 1, top, -np.inf)
PIVOT_R, PIVOT_C = np.unravel_index(np.argmax(top_land), top_land.shape)
PIVOT_X = XUL + (PIVOT_C + 0.5) * DELR
PIVOT_Y = YUL - (PIVOT_R + 0.5) * DELR
ax.plot(PIVOT_X, PIVOT_Y, marker="^", ms=14, mfc="orange", mec="black", mew=1.3,
        label=f"Highland (+{top[PIVOT_R, PIVOT_C]:.0f} m)", zorder=11)

# EPS zone rectangle
ax.add_patch(Rectangle((EPS_X_MIN, EPS_Y_MIN), EPS_X_MAX-EPS_X_MIN, EPS_Y_MAX-EPS_Y_MIN,
                        fill=False, edgecolor="green", linewidth=2.0, linestyle="--",
                        zorder=8, label="EPS zone (SS1-SS10)"))
ax.text((EPS_X_MIN+EPS_X_MAX)/2, EPS_Y_MAX+450, "West coast\nEPS survey\n(SS1-SS10)",
        ha="center", fontsize=9, color="darkgreen", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85, edgecolor="green"))

# Coast outline
from scipy.ndimage import binary_dilation
coast_band = binary_dilation(ido == 0, iterations=1) & (ido == 1)
ax.contour(coast_band.astype(int), levels=[0.5],
           extent=[xmin, xmax, ymin, ymax], origin="upper",
           colors="navy", linewidths=0.8, alpha=0.6)

# Scale bar (5 km)
scale_y = ymin + 1200
ax.plot([553000, 558000], [scale_y, scale_y], "k-", lw=3)
ax.text(555500, scale_y - 700, "5 km", ha="center", fontsize=10, fontweight="bold")
# North arrow
ax.annotate("N", xy=(573500, 9422000), xytext=(573500, 9420000),
            arrowprops=dict(arrowstyle="->", lw=2.5, color="black"),
            ha="center", fontsize=14, fontweight="bold")

ax.set_xlim(551500, 575500)
ax.set_ylim(9402000, 9425500)
ax.set_aspect("equal")
ax.set_xlabel("UTM Easting (m, UTM 51S)", fontsize=11)
ax.set_ylabel("UTM Northing (m)", fontsize=11)
ax.set_title("Wangi-Wangi Island — site map, observation network, and head residual classification",
             fontsize=12, fontweight="bold", pad=10)
ax.grid(alpha=0.25)

# Legend on the right
ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=10,
          framealpha=0.95, edgecolor="black")

# Wakatobi inset (lower-left)
ax_inset = fig.add_axes([0.08, 0.10, 0.18, 0.18])
# Schematic: Sulawesi + Wakatobi
ax_inset.add_patch(Rectangle((0, 0), 1, 1, facecolor="lightblue", edgecolor="navy"))
# Sulawesi schematic
ax_inset.plot([0.1, 0.18, 0.3, 0.32, 0.25, 0.18, 0.12, 0.08],
              [0.55, 0.7, 0.62, 0.45, 0.35, 0.42, 0.5, 0.5], "g-", lw=2, alpha=0.6)
ax_inset.fill([0.1, 0.18, 0.3, 0.32, 0.25, 0.18, 0.12, 0.08],
              [0.55, 0.7, 0.62, 0.45, 0.35, 0.42, 0.5, 0.5], color="khaki", alpha=0.7)
ax_inset.text(0.18, 0.6, "Sulawesi", fontsize=7, ha="center")
# Wakatobi marker
ax_inset.plot(0.65, 0.32, "ro", ms=8, mec="black", mew=1.2)
ax_inset.text(0.7, 0.28, "Wangi-Wangi\n(Wakatobi)", fontsize=7, va="top")
ax_inset.text(0.5, 0.9, "Indonesia", fontsize=8, ha="center", fontweight="bold",
              bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))
ax_inset.set_xlim(0, 1); ax_inset.set_ylim(0, 1)
ax_inset.set_xticks([]); ax_inset.set_yticks([])
ax_inset.set_title("Location", fontsize=8)

# Right margin: brief stats
stats_text = (
    "Hydrogeology:\n"
    "  L1 cap K1 = 0.085 m/d\n"
    "  L2 main K2 = 53.3 m/d\n"
    "  L3 deep K3 = K2 (extension)\n"
    "\n"
    "Observation:\n"
    "  17 main aquifer wells\n"
    "  3 perched (excluded)\n"
    "  HOBO at WW4 (Kantamare)\n"
    "\n"
    "Validation (Phase 3a/3b):\n"
    "  L2 head RMSE = 2.22 m\n"
    "  Tidal eff: 20.3% vs obs 18%\n"
    "  Island NET SGD = 3.32e5 m³/d"
)
fig.text(0.81, 0.10, stats_text, fontsize=8.5,
         verticalalignment="bottom",
         bbox=dict(boxstyle="round,pad=0.4", fc="lightyellow",
                   alpha=0.95, edgecolor="black"))

out_png = FIGDIR / "paper2_fig1_site_map.png"
plt.savefig(out_png, dpi=180, bbox_inches="tight")
out_pdf = FIGDIR / "paper2_fig1_site_map.pdf"
plt.savefig(out_pdf, bbox_inches="tight")
plt.close()
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
