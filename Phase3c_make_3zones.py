"""Build zones_3zone.npy for Phase 3c K2 zonation PEST calibration.

3 K2 zones based on residual pattern from Phase 3c L3-shallow:
  Zone 1 (NW + extreme S coastal): wells systematically under-predicted
    Bounding box: row < 320 AND col < 280   (NW corner)
    OR           row > 600 AND col > 350   (S coast)
  Zone 2 (Central + Kantamare area)
  Zone 3 (S/SE inland)

Output: zones_3zone.npy with values 0=inactive, 1=NW, 2=Central, 3=S/SE.
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
idomain = np.load(WORK / "idomain.npy").astype(int)
NROW, NCOL = idomain.shape

zones = np.zeros((NROW, NCOL), dtype=int)
zones[idomain == 1] = 2   # default: Central

# Zone 1: NW corner
zones[:320, :280] = np.where(idomain[:320, :280] == 1, 1, 0)
# Zone 1 also for extreme-S coastal cluster
zones[600:, 350:] = np.where(idomain[600:, 350:] == 1, 1, 0)
# Zone 3: S/SE inland
zones[400:, 200:500] = np.where(
    (idomain[400:, 200:500] == 1) & (zones[400:, 200:500] == 2), 3, zones[400:, 200:500]
)

# Stats
for z, name in [(1, "NW + extreme S coastal"), (2, "Central"), (3, "S/SE inland")]:
    n = (zones == z).sum()
    print(f"Zone {z} ({name}): {n:,} active cells ({100*n/(idomain==1).sum():.1f}% of active)")
print(f"Total active: {(idomain == 1).sum():,}")

np.save(WORK / "zones_3zone.npy", zones)
print(f"Saved: zones_3zone.npy")

# Visualization
fig, ax = plt.subplots(figsize=(11, 11))
cmap = plt.cm.colors.ListedColormap(["white", "#3a78ad", "#f4c542", "#a64040"])
ax.imshow(zones, cmap=cmap, vmin=0, vmax=3, alpha=0.85)
ax.set_title("Phase 3c K2 zonation\n0 = inactive (white), 1 = NW (blue), 2 = Central (yellow), 3 = S/SE (red)",
             fontsize=12, fontweight="bold")
ax.set_xlabel("Column"); ax.set_ylabel("Row")
plt.tight_layout()
out = WORK / "figs" / "Phase3c_K2_3zones.png"
out.parent.mkdir(exist_ok=True)
plt.savefig(out, dpi=130, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")
