"""Verification of WW4 (Kantamare) groundwater level in MSL.

Cross-check the sensor elevation derivation against multiple data sources:
 (1) Component-by-component breakdown of SENSOR_ELEV (+0.5671 m MSL)
 (2) Pre cord-break vs Post re-tie mean water column (should match if cord length preserved)
 (3) Field survey single-point on 2024-12-12 (Dec 12 14:00 measurement)
 (4) Compare with HOBO at 2024-12-12 14:00
 (5) Uncertainty propagation (each component ± measurement error)

Output: report + verification figure.
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

# === (1) Component breakdown ===
print("=" * 72)
print("(1) SENSOR ELEVATION DERIVATION")
print("=" * 72)
components = [
    ("WELL_TOP_ELEV",         +8.7471, 0.03,  "PPP 2025: AJ 10.7901 - AL 2.043 m (CORRECTED)"),
    ("LEVEL_INSTRUMENT_HI",   +1.325,  0.005, "instrument above ground at GNSS station"),
    ("FS_TO_CISTERN",         -3.015,  0.005, "FS staff reading at cistern entrance"),
    ("STAIRCASE_SUM",         -3.465,  0.020, "16 steps sum (9,26,23,19.5,...,20 cm)"),
    ("STAIRS_TO_ANCHOR",      -1.040,  0.010, "stairs end → cord anchor vertical"),
    ("CORD_LENGTH",           -1.945,  0.010, "sensor suspension cord (re-tied 2025-01-16)"),
]
print(f"{'Component':<24} {'Value (m)':>10} {'± σ (m)':>10}  Note")
print("-" * 72)
sensor_elev = 0.0
var_sum = 0.0
for name, val, sig, note in components:
    sensor_elev += val
    var_sum += sig**2
    sign = "+" if val > 0 else ""
    print(f"  {name:<22} {sign}{val:>9.4f} {sig:>9.4f}  {note}")
sigma = np.sqrt(var_sum)
print(f"\n  {'SENSOR_ELEV':<22} {sensor_elev:>+10.4f} ±{sigma:>9.3f} m MSL")

# === (2) Pre vs Post cord break ===
print("\n" + "=" * 72)
print("(2) PRE CORD-BREAK vs POST RE-TIE WATER COLUMN")
print("=" * 72)
df = pd.read_csv(WORK / "ww4_8mo_processed.csv")
df["datetime"] = pd.to_datetime(df["datetime"])

# Pre cord-break: 2024-12-14 14:00 → 2024-12-28 23:59 (before sudden jump on 12-29)
pre = df[(df["datetime"] >= "2024-12-14 14:00") &
         (df["datetime"] <  "2024-12-29 00:00")]
# Cord break interval (sensor fallen): 2024-12-30 → 2025-01-14
during = df[(df["datetime"] >= "2024-12-30 00:00") &
            (df["datetime"] <  "2025-01-15 00:00")]
# Post re-tie: 2025-01-16 onwards
post = df[df["datetime"] >= "2025-01-16 00:00"]

print(f"  Pre  break (Dec 14-28, n={len(pre):5d}): water col mean = {pre['water_col_m'].mean():.3f} m,  std {pre['water_col_m'].std():.3f}")
print(f"  During fall (Dec 30-Jan 14, n={len(during):5d}): mean = {during['water_col_m'].mean():.3f} m,  std {during['water_col_m'].std():.3f}")
print(f"  Post re-tie (Jan 16+, n={len(post):5d}): mean = {post['water_col_m'].mean():.3f} m,  std {post['water_col_m'].std():.3f}")
print()
delta = post['water_col_m'].mean() - pre['water_col_m'].mean()
print(f"  Δ (post - pre) = {delta:+.3f} m")
if abs(delta) < 0.10:
    print(f"  → cord length essentially preserved after re-tying (|Δ| < 10 cm)")
else:
    print(f"  → cord length may have changed during re-tying (|Δ| ≥ 10 cm)")
seasonal_days = (post['datetime'].mean() - pre['datetime'].mean()).days
print(f"  Note: time gap pre→post mean = {seasonal_days} days")
print(f"        seasonal drift over that = {seasonal_days * -0.0057:+.3f} m (using -5.7 mm/month)")
print(f"        cord-length-only Δ would be {delta - seasonal_days * -0.0057:+.3f} m (after removing season)")

# === (3) Field survey single point at 2024-12-12 15:57 ===
print("\n" + "=" * 72)
print("(3) FIELD SURVEY single measurement (2024-12-12 15:57)")
print("=" * 72)
field_water_surface = 7.385   # depth from casing top to water (m)
field_casing_height = 0.0     # casing flush with ground
ground_elev_pest = 10.0       # PEST calibration_targets ground_elev (approx from ALOS DEM)
pest_obs_head = 4.155         # PEST calibration target
# Two interpretations:
ws_from_PEST_ground = ground_elev_pest + field_casing_height - field_water_surface
ws_from_PPP_top     = 8.7071 - field_water_surface
print(f"  field 'Water Surface' (depth from casing top) = {field_water_surface:.3f} m")
print(f"  Casing height above ground (field)             = {field_casing_height:.3f} m")
print()
print(f"  Interpretation A — using PEST approximate ground elev (10 m):")
print(f"    water level = ground 10 + 0 - 7.385 = {ws_from_PEST_ground:+.3f} m MSL")
print(f"    Matches PEST obs_head {pest_obs_head}? Δ = {ws_from_PEST_ground - pest_obs_head:+.3f} m")
print()
print(f"  Interpretation B — using PPP precise casing top (8.7071 m):")
print(f"    water level = casing top 8.7071 - 7.385 = {ws_from_PPP_top:+.3f} m MSL")
print(f"    Matches HOBO? Δ vs HOBO Dec mean (~2.38 m) = {ws_from_PPP_top - 2.378:+.3f} m")
print()
print("  ⚠ The two interpretations give different answers because PEST ground_elev (10 m)")
print("    does not equal the PPP casing top (8.7071 m). PEST DEM was approximate.")

# === (4) HOBO at 2024-12-12 15:57 (same time as field survey) ===
print("\n" + "=" * 72)
print("(4) HOBO READING AT FIELD-SURVEY TIME (2024-12-12 15:57)")
print("=" * 72)
# Find closest HOBO record
target_time = pd.Timestamp("2024-12-12 15:57")
df_full = df.copy()  # full 8-month including pre-break
nearest = df_full.iloc[(df_full["datetime"] - target_time).abs().argsort()[:1]]
print(f"  Nearest HOBO record (within {(nearest['datetime'].iloc[0] - target_time).total_seconds()/60:.1f} min):")
print(f"  Time = {nearest['datetime'].iloc[0]}")
print(f"  Water column above sensor = {nearest['water_col_m'].iloc[0]:.3f} m")
hobo_gw_at_survey = sensor_elev + nearest['water_col_m'].iloc[0]
print(f"  HOBO-derived GW elev (this instant) = {hobo_gw_at_survey:+.3f} m MSL")
print(f"  Field survey Interpretation A      = {ws_from_PEST_ground:+.3f} m MSL")
print(f"  Field survey Interpretation B      = {ws_from_PPP_top:+.3f} m MSL")
print()
print("  ⇒ HOBO instantaneous and Interpretation B disagree by "
      f"{hobo_gw_at_survey - ws_from_PPP_top:+.2f} m at the same instant.")
print("    Possible reasons: (i) tidal phase between the two measurements;")
print("    (ii) field 'Water Surface' measured from a different reference;")
print("    (iii) cord length at time of field survey differed from now;")
print("    (iv) PEST ground_elev (10 m) is more correct than PPP casing top (8.7071 m).")

# === (5) Long-term means with uncertainty ===
print("\n" + "=" * 72)
print("(5) LONG-TERM MEAN GW ELEV WITH PROPAGATED UNCERTAINTY")
print("=" * 72)
periods = [
    ("Pre cord-break (Dec 14-28, 15 d)", pre),
    ("Post re-tie (Jan 16+, 209 d)",    post),
]
for label, sub in periods:
    wc_mean = sub['water_col_m'].mean()
    wc_sem  = sub['water_col_m'].std() / np.sqrt(len(sub))
    gw_mean = sensor_elev + wc_mean
    gw_sigma_total = np.sqrt(sigma**2 + wc_sem**2)
    print(f"  {label}: GW elev = {gw_mean:+.3f} ± {gw_sigma_total:.3f} m MSL")
    print(f"    (sensor σ={sigma:.3f}, water-column SEM={wc_sem:.4f})")

# === Save report CSV ===
out_csv = WORK / "ww4_msl_verification.csv"
report_rows = [
    {"step": "Sensor elev (sum)", "value_m": sensor_elev, "sigma_m": sigma, "note": "WELL_TOP + INST - FS - STAIRS - ANCHOR - CORD"},
    {"step": "Pre cord-break mean water col", "value_m": pre['water_col_m'].mean(), "sigma_m": pre['water_col_m'].std()/np.sqrt(len(pre)), "note": "n=15 days"},
    {"step": "Post re-tie mean water col", "value_m": post['water_col_m'].mean(), "sigma_m": post['water_col_m'].std()/np.sqrt(len(post)), "note": "n=209 days"},
    {"step": "Pre cord-break GW elev", "value_m": sensor_elev + pre['water_col_m'].mean(), "sigma_m": np.sqrt(sigma**2 + (pre['water_col_m'].std()/np.sqrt(len(pre)))**2), "note": "best snapshot"},
    {"step": "Post re-tie GW elev", "value_m": sensor_elev + post['water_col_m'].mean(), "sigma_m": np.sqrt(sigma**2 + (post['water_col_m'].std()/np.sqrt(len(post)))**2), "note": "long-term anchor"},
    {"step": "Field survey Interp A (PEST ground=10)", "value_m": ws_from_PEST_ground, "sigma_m": 0.5, "note": "ground elev DEM ±0.5m"},
    {"step": "Field survey Interp B (PPP top=8.7071)", "value_m": ws_from_PPP_top, "sigma_m": 0.04, "note": "PPP top ±0.03 m"},
    {"step": "HOBO at field-survey time (Dec 12 15:57)", "value_m": hobo_gw_at_survey, "sigma_m": sigma, "note": "instantaneous"},
    {"step": "PEST calibration_targets obs_head", "value_m": pest_obs_head, "sigma_m": 0.5, "note": "calibration data"},
]
report = pd.DataFrame(report_rows)
report.to_csv(out_csv, index=False, float_format="%.4f")
print(f"\nSaved verification CSV: {out_csv}")

# === Figure ===
fig, axes = plt.subplots(2, 1, figsize=(15, 10))

# Top: pre/during/post water column zoom
ax = axes[0]
zoom = df[(df["datetime"] >= "2024-12-14") & (df["datetime"] <= "2025-02-01")]
ax.plot(zoom["datetime"], zoom["water_col_m"], "b-", lw=0.4, alpha=0.6)
ax.axvspan("2024-12-14", "2024-12-29", alpha=0.10, color="green", label="Pre break")
ax.axvspan("2024-12-30", "2025-01-15", alpha=0.10, color="red",   label="Sensor fallen")
ax.axvspan("2025-01-16", "2025-02-01", alpha=0.10, color="blue",  label="Post re-tie")
ax.axhline(pre['water_col_m'].mean(), color="green", ls="--", lw=1.2,
           label=f"Pre mean {pre['water_col_m'].mean():.3f} m")
ax.axhline(post['water_col_m'].mean(), color="blue", ls="--", lw=1.2,
           label=f"Post mean {post['water_col_m'].mean():.3f} m")
ax.set_ylabel("Water column above sensor (m)", fontsize=11)
ax.set_title("WW4 cord-break event window — pre/during/post comparison\n"
             f"Δ(post-pre) = {delta*1000:+.0f} mm "
             f"(cord length essentially preserved if |Δ| < 60 mm)",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)
ax.xaxis.set_major_locator(DayLocator(interval=5))
ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))

# Bottom: GW elev with all reference points
ax2 = axes[1]
methods = [
    ("Pre cord-break mean", sensor_elev + pre['water_col_m'].mean(),
     sigma, "green"),
    ("Post re-tie mean (long-term)", sensor_elev + post['water_col_m'].mean(),
     sigma, "blue"),
    ("Field survey (PEST ground=10m)", ws_from_PEST_ground, 0.5, "orange"),
    ("Field survey (PPP top=8.71m)", ws_from_PPP_top, 0.04, "darkred"),
    ("PEST calib target", pest_obs_head, 0.5, "red"),
    ("HOBO @ field-survey instant", hobo_gw_at_survey, sigma, "purple"),
]
labels = [m[0] for m in methods]
vals = [m[1] for m in methods]
sigs = [m[2] for m in methods]
colors = [m[3] for m in methods]
y = np.arange(len(methods))
ax2.barh(y, vals, color=colors, edgecolor="black", linewidth=1.0, alpha=0.85)
ax2.errorbar(vals, y, xerr=sigs, fmt="none", color="black", capsize=6, lw=1.5)
for i, (l, v, s) in enumerate(zip(labels, vals, sigs)):
    ax2.text(v + 0.1, i, f"{v:+.2f} ± {s:.2f} m", va="center", fontsize=10, fontweight="bold")
ax2.set_yticks(y); ax2.set_yticklabels(labels)
ax2.axvline(0, color="navy", ls="--", lw=0.7, label="MSL")
ax2.set_xlabel("Groundwater elevation (m MSL)", fontsize=11)
ax2.set_title("WW4 GW elevation — independent estimates with uncertainty", fontsize=12, fontweight="bold")
ax2.legend(loc="lower right", fontsize=9)
ax2.grid(alpha=0.3, axis="x")
ax2.set_xlim(-0.5, max(vals) + 1.5)

plt.tight_layout()
out_fig = FIGDIR / "ww4_msl_verification.png"
plt.savefig(out_fig, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out_fig}")
