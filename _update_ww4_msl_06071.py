"""Update WW4 MSL with corrected sensor elevation +0.6071 m (per user correction).

Root cause of the 4 cm correction:
  PPP correction: AL = 2.043 m (not 2.083 m as I had).
  → WELL_TOP_ELEV = AJ - AL = 10.7901 - 2.043 = 8.7471 m (was 8.7071)
  This is a +4 cm correction to the GNSS-station ground elevation.

Component breakdown (CORRECTED):
  WELL_TOP_ELEV         = 8.7471 m  (GNSS-station ground, corrected from 8.7071)
  LEVEL_INSTRUMENT_HI   = 1.325 m
  FS_TO_CISTERN         = -3.015 m
  STAIRCASE_SUM         = -3.465 m
  STAIRS_TO_ANCHOR      = -1.040 m
  CORD_LENGTH           = -1.945 m
  SENSOR_ELEV           = +0.6071 m MSL  ✓

Apply correction across:
 1. Long-term mean (post re-tie) — new truth value +2.418 m
 2. Comparison with PEST and 3D model
 3. Tidal-amplitude unaffected (relative quantity, not affected)

Outputs:
  ww4_msl_06071_summary.csv
  figs/ww4_msl_06071_overview.png
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MonthLocator

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

# Use the corrected sensor elev
SENSOR_ELEV = 0.6071  # m MSL — user-corrected from field records
SIGMA = 0.039         # propagated uncertainty (same as before)
print(f"Corrected sensor elevation: +{SENSOR_ELEV:.4f} ± {SIGMA:.3f} m MSL\n")

df = pd.read_csv(WORK / "ww4_8mo_processed.csv")
df["datetime"] = pd.to_datetime(df["datetime"])
df["GW_elev_MSL"] = SENSOR_ELEV + df["water_col_m"]

# Phase windows
pre = df[(df["datetime"] >= "2024-12-14 14:00") & (df["datetime"] <  "2024-12-29 00:00")]
post = df[df["datetime"] >= "2025-01-16 00:00"]
df_clean = pd.concat([pre, post])

print("=== Updated WW4 GW elevation (m MSL) with sensor +0.6071 m ===")
for label, sub in [("Pre cord-break (Dec 14-28, 15 d)", pre),
                    ("Post re-tie (Jan 16+, 209 d)",   post),
                    ("Combined clean window",         df_clean)]:
    gw_mean = sub["GW_elev_MSL"].mean()
    sem = sub["GW_elev_MSL"].std() / np.sqrt(len(sub))
    sigma_total = np.sqrt(SIGMA**2 + sem**2)
    print(f"  {label}: GW elev = {gw_mean:+.3f} ± {sigma_total:.3f} m MSL (n={len(sub):,})")

# Update vs PEST and 3D model
PEST_obs = 4.155
P3a_baseline_sim = 5.020   # sim L2 with BOTM_L3=-500 (baseline)
P3c_L3shallow_sim = 2.817  # sim L2 with BOTM_L3=-200 (Phase 3c)
truth_post = post["GW_elev_MSL"].mean()

print(f"\n=== Updated cross-reference at WW4 ===")
print(f"  Truth (post re-tie HOBO, 209 d) : {truth_post:.3f} m MSL")
print(f"  PEST calibration target           : {PEST_obs:.3f} m  (Δ vs truth = {PEST_obs - truth_post:+.3f} m)")
print(f"  Phase 3a baseline (BOTM_L3=-500)  : {P3a_baseline_sim:.3f} m  (Δ vs truth = {P3a_baseline_sim - truth_post:+.3f} m)")
print(f"  Phase 3c L3-shallow (BOTM_L3=-200): {P3c_L3shallow_sim:.3f} m  (Δ vs truth = {P3c_L3shallow_sim - truth_post:+.3f} m)")

# Daily aggregations
df["date"] = df["datetime"].dt.date
daily = df.groupby("date").agg(
    GW_mean=("GW_elev_MSL", "mean"),
    GW_min=("GW_elev_MSL", "min"),
    GW_max=("GW_elev_MSL", "max"),
).reset_index()
daily["date"] = pd.to_datetime(daily["date"])

# Save corrected CSV
out_csv = WORK / "ww4_msl_06071_full.csv"
df[["datetime", "water_col_m", "GW_elev_MSL"]].to_csv(
    out_csv, index=False, float_format="%.4f")
print(f"\nSaved: {out_csv}")

# Save summary
summary = pd.DataFrame([
    {"metric": "sensor_elev_m_MSL", "value": SENSOR_ELEV, "uncertainty": SIGMA, "note": "user-corrected from field-survey records"},
    {"metric": "GW_mean_pre_break_m_MSL", "value": pre["GW_elev_MSL"].mean(),
     "uncertainty": np.sqrt(SIGMA**2 + (pre["GW_elev_MSL"].std()/np.sqrt(len(pre)))**2),
     "note": "Dec 14-28 2024, n=692"},
    {"metric": "GW_mean_post_retie_m_MSL", "value": truth_post,
     "uncertainty": np.sqrt(SIGMA**2 + (post["GW_elev_MSL"].std()/np.sqrt(len(post)))**2),
     "note": "Jan 16 - Aug 13 2025, n=10054, THIS IS THE TRUTH"},
    {"metric": "PEST_obs_head_inflation_m", "value": PEST_obs - truth_post, "uncertainty": np.nan,
     "note": "positive = PEST too high"},
    {"metric": "P3c_L3shallow_bias_m", "value": P3c_L3shallow_sim - truth_post, "uncertainty": np.nan,
     "note": "sim - truth, positive = sim too high"},
])
summary.to_csv(WORK / "ww4_msl_06071_summary.csv", index=False, float_format="%.4f")
print(f"Saved: {WORK / 'ww4_msl_06071_summary.csv'}")

# Plot
fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True,
                          gridspec_kw={"height_ratios": [3, 1]})

ax = axes[0]
# Mark cord-break window
ax.axvspan(pd.Timestamp("2024-12-29"), pd.Timestamp("2025-01-15"),
           alpha=0.10, color="red", label="Cord-fall window (excluded)")
ax.plot(df["datetime"], df["GW_elev_MSL"], "b-", lw=0.3, alpha=0.6,
        label=f"Instantaneous (n={len(df):,})")
ax.plot(daily["date"], daily["GW_mean"], "k-", lw=1.4, label="Daily mean")
ax.fill_between(daily["date"], daily["GW_min"], daily["GW_max"],
                color="black", alpha=0.13, label="Daily min-max")
ax.axhline(truth_post, color="navy", ls="-", lw=1.8, alpha=0.85,
           label=f"Post re-tie mean = {truth_post:.2f} m MSL (THE TRUTH)")
ax.axhline(PEST_obs, color="red", ls="--", lw=1.4,
           label=f"PEST obs_head: {PEST_obs:.2f} m (inflated by {PEST_obs - truth_post:+.2f} m)")
ax.axhline(P3c_L3shallow_sim, color="green", ls=":", lw=2.0,
           label=f"3D Phase 3c L3-shallow sim L2: {P3c_L3shallow_sim:.2f} m "
                 f"(bias {P3c_L3shallow_sim - truth_post:+.2f} m)")
ax.axhline(P3a_baseline_sim, color="purple", ls=":", lw=1.4, alpha=0.7,
           label=f"3D Phase 3a baseline sim L2: {P3a_baseline_sim:.2f} m "
                 f"(bias {P3a_baseline_sim - truth_post:+.2f} m)")
ax.set_ylabel("GW elevation (m, MSL)", fontsize=11)
ax.set_title(f"WW4 (Kantamare) — Corrected MSL with sensor elev = +0.6071 m\n"
             f"Long-term mean = +{truth_post:.3f} m MSL  (Phase 3c L3-shallow bias = {P3c_L3shallow_sim - truth_post:+.3f} m)",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=8)
ax.grid(alpha=0.3)

ax2 = axes[1]
ax2.plot(daily["date"], daily["GW_mean"], "g-", lw=1.4, label="Daily mean")
daily["GW_30d"] = daily["GW_mean"].rolling(30, min_periods=10).mean()
ax2.plot(daily["date"], daily["GW_30d"], "darkred", lw=2.0, label="30-d rolling")
ax2.axhline(truth_post, color="navy", ls="-", lw=1.5, alpha=0.7)
ax2.set_xlabel("Date"); ax2.set_ylabel("Daily mean GW elev (m MSL)")
ax2.legend(loc="upper right", fontsize=9)
ax2.grid(alpha=0.3)

plt.tight_layout()
out_fig = FIGDIR / "ww4_msl_06071_overview.png"
plt.savefig(out_fig, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out_fig}")
