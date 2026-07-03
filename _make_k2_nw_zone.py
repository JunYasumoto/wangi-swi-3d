"""Create k2_field_NWzone.npy: K2 main aquifer with NW zone reduced.

Zone definition (matches the 7 NW + extreme-S 'under' wells from residual analysis):
  NW zone:  row < 320 AND col < 280  (NW corner, includes ww02/03/18/19)
  Extreme-S coastal: row > 600 AND col > 350 (includes ww05/06/17)

In both zones: K2 = K2_NW_VALUE (default 10 m/d, 5× lower than 53)
Elsewhere: K2 = original PEST value (53.3 m/d)
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os, numpy as np

WORK = pathlib.Path(__file__).resolve().parent
K2_NW = float(os.environ.get("K2_NW", "10.0"))

k2 = np.load(WORK / "k2_field.npy").astype(float)
print(f"Original k2: min {k2.min():.3g}, max {k2.max():.3g}, median {np.median(k2):.3g}")

NROW, NCOL = k2.shape

# NW zone mask (row < 320 AND col < 280)
mask_nw = np.zeros_like(k2, dtype=bool)
mask_nw[:320, :280] = True
# Extreme-S coast mask (row > 600 AND col > 350)
mask_s = np.zeros_like(k2, dtype=bool)
mask_s[600:, 350:] = True

# Combined "low-K" mask, but only where the model is active (k2 > K_FLOOR)
K_FLOOR = 1e-5
active = k2 > K_FLOOR * 10   # truly assigned cells (not floor)
zone_low = (mask_nw | mask_s) & active

k2_new = k2.copy()
k2_new[zone_low] = K2_NW
print(f"NW + S-coast 'low-K' zone: {zone_low.sum():,} active cells set to K2 = {K2_NW} m/d")
print(f"New k2: min {k2_new.min():.3g}, max {k2_new.max():.3g}, median {np.median(k2_new[active]):.3g}")

out = WORK / "k2_field_NWzone.npy"
np.save(out, k2_new)
print(f"Saved: {out}")

# Also save the zone mask for visualization
np.save(WORK / "k2_zone_low_mask.npy", zone_low.astype(np.uint8))
