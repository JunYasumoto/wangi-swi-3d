"""Explore per-well n_transport correlations with hydrogeological variables.

For each SF6-valid well, plot n_transport against:
 (a) distance to coast (proxy for travel path length)
 (b) distance to highland pivot (proxy for recharge source)
 (c) sim_age_yr (porous-medium MODPATH age, since they're inversely correlated by definition)
 (d) ground_elev (highland vs lowland correlations)

Output: figs/n_transport_correlations.png (4-panel)
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"
JPGU = WORK.parent / "wangi_jpgu2026"

# Load n_transport per well
nt = pd.read_csv(WORK / "n_transport_per_well.csv")
# Add ground_elev from well_classification
wc = pd.read_csv(JPGU / "well_classification.csv")[["well_id", "ground_elev"]]
wc.columns = ["id", "ground_elev"]
nt = nt.merge(wc, on="id", how="left")

# Highland pivot (from earlier analysis)
PIVOT_X = 562295.0; PIVOT_Y = 9415580.7

# Compute distances
nt["dist_pivot_m"] = np.hypot(nt["utm_x"] - PIVOT_X, nt["utm_y"] - PIVOT_Y)

# Distance to coast: approximate as distance from nearest inactive cell
import importlib.util
spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR = cfg.NROW, cfg.NCOL, cfg.DELR
XUL, YUL = cfg.XUL, cfg.YUL
ido = np.load(WORK / "idomain.npy")
# Build distance-to-sea (inactive) raster
from scipy.ndimage import distance_transform_edt
dist_to_sea_cells = distance_transform_edt(ido == 1)  # cells to sea
dist_to_sea_m = dist_to_sea_cells * DELR

def get_dist_to_coast(row):
    r = int((YUL - row["utm_y"]) / DELR)
    c = int((row["utm_x"] - XUL) / DELR)
    if 0 <= r < NROW and 0 <= c < NCOL:
        return dist_to_sea_m[r, c]
    return np.nan
nt["dist_coast_m"] = nt.apply(get_dist_to_coast, axis=1)

print("=== n_transport correlations data ===")
print(nt[["id", "n_transport", "log10_n", "obs_age_yr", "sim_age_yr",
          "ground_elev", "dist_coast_m", "dist_pivot_m"]].to_string(index=False, float_format="%.3g"))

# Plot
fig, axes = plt.subplots(2, 2, figsize=(14, 11))

panels = [
    ("dist_coast_m", "Distance to coast (m)", "(a) n_transport vs distance to coast"),
    ("dist_pivot_m", "Distance from highland pivot (m)", "(b) n_transport vs distance to pivot"),
    ("sim_age_yr", "MODPATH sim age (yr)", "(c) n_transport vs sim age"),
    ("ground_elev", "Ground elevation (m)", "(d) n_transport vs ground elev"),
]

for (xcol, xlabel, title), ax in zip(panels, axes.flat):
    ax.scatter(nt[xcol], nt["n_transport"], s=200, c=np.log10(nt["n_transport"]),
               cmap="viridis", edgecolor="black", linewidth=1.3, zorder=4)
    for _, r in nt.iterrows():
        ax.annotate(r["id"].upper(), (r[xcol], r["n_transport"]),
                    xytext=(7, 5), textcoords="offset points", fontsize=10)
    if xcol == "sim_age_yr":
        ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("n_transport (–)", fontsize=11)
    rho, p = spearmanr(nt[xcol], nt["n_transport"], nan_policy="omit")
    ax.set_title(f"{title}\nSpearman ρ = {rho:+.2f}, p = {p:.3f}",
                 fontsize=11, fontweight="bold")
    ax.axhspan(1e-4, 1e-3, alpha=0.15, color="orange",
               label="karst conduit literature")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3, which="both")

fig.suptitle("n_transport correlations with hydrogeology\n"
             "What controls the per-well effective transport porosity?",
             fontsize=13, fontweight="bold", y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.97])
out = FIGDIR / "n_transport_correlations.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")
