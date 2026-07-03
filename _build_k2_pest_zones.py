"""Build spatial K2 zonation for Phase 3c Scenario A PEST.

Zones (bounding boxes informed by well positions):
  Zone 1 NW   : row<320 AND col<300 — contains ww02/03/18/19/20
  Zone 2 CENT : row in [350,450] AND col in [200,260] — Kantamare cluster (ww04/11/12)
  Zone 3 SSE  : all other active cells — covers ww05/06/07/08/09/10/13/15/17 (+ perched)

Saves k2_zones_pest.npy and a diagnostic figure with well overlays.
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

WORK = pathlib.Path(__file__).resolve().parent
idomain = np.load(WORK / "idomain.npy").astype(int)
NROW, NCOL = idomain.shape

zones = np.zeros((NROW, NCOL), dtype=int)
# Default: zone 3 (SSE) for active cells
zones[idomain == 1] = 3
# Zone 1 NW
nw_mask = (np.arange(NROW)[:, None] < 320) & (np.arange(NCOL)[None, :] < 300)
zones[(idomain == 1) & nw_mask] = 1
# Zone 2 CENT (Kantamare cluster)
cent_mask = (
    (np.arange(NROW)[:, None] >= 350) & (np.arange(NROW)[:, None] < 450)
    & (np.arange(NCOL)[None, :] >= 200) & (np.arange(NCOL)[None, :] < 260)
)
zones[(idomain == 1) & cent_mask] = 2

# Stats
for z, name in [(1, "NW corner"), (2, "Central / Kantamare"), (3, "S / SE / E rest")]:
    n = (zones == z).sum()
    print(f"Zone {z} ({name}): {n:,} active cells "
          f"({100*n/(idomain==1).sum():.1f}% of active)")
print(f"Total active: {(idomain == 1).sum():,}")

# Verify well-to-zone assignment
wells = pd.read_csv(WORK / "well_cells.csv")
targets = pd.read_csv(WORK / "calibration_targets_corrected.csv")
wells = wells.merge(targets[["id", "use_for_calibration", "weight"]], on="id", how="left")
wells["k2_zone"] = wells.apply(lambda r: zones[int(r["model_row"]), int(r["model_col"])], axis=1)
zone_label = {0: "inactive", 1: "NW", 2: "CENT", 3: "SSE"}
wells["k2_zone_label"] = wells["k2_zone"].map(zone_label)
print("\n=== Well-to-zone assignment ===")
print(wells[["id", "model_row", "model_col", "k2_zone_label",
             "use_for_calibration", "weight"]].to_string(index=False))

# Save
np.save(WORK / "k2_zones_pest.npy", zones)
print(f"\nSaved: k2_zones_pest.npy")
wells[["id", "k2_zone", "k2_zone_label"]].to_csv(
    WORK / "wells_k2_zone_assignment.csv", index=False)

# Diagnostic figure
fig, ax = plt.subplots(figsize=(11, 11))
cmap = ListedColormap(["white", "#3a78ad", "#f4c542", "#a64040"])
ax.imshow(zones, cmap=cmap, vmin=0, vmax=3, alpha=0.85)
ax.set_xlim(0, NCOL); ax.set_ylim(NROW, 0)
# Overlay wells colored by use_for_calibration
for _, w in wells.iterrows():
    color = "black" if w["use_for_calibration"] else "gray"
    marker = "o" if w["weight"] >= 1.0 else "s"
    ax.scatter(w["model_col"], w["model_row"], c=color, s=120,
               edgecolor="white", linewidth=1.5, marker=marker, zorder=5)
    ax.annotate(
        f"{w['id']}\n[{w['k2_zone_label']}]",
        (w["model_col"], w["model_row"]),
        xytext=(8, 8), textcoords="offset points",
        fontsize=8, fontweight="bold",
        color="black" if w["use_for_calibration"] else "gray",
    )
ax.set_title(
    "Phase 3c Scenario A — spatial K2 zonation\n"
    "Zone 1 NW (blue)  Zone 2 CENT/Kantamare (yellow)  Zone 3 SSE (red)\n"
    "wells: black=calibration, gray=diagnostic; square=ww10 (weight 0.1)",
    fontsize=11, fontweight="bold",
)
ax.set_xlabel("Column"); ax.set_ylabel("Row")
plt.tight_layout()
FIGS = WORK / "figs"
FIGS.mkdir(exist_ok=True)
out = FIGS / "k2_zones_pest.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")
