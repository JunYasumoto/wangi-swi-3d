"""Convert WW4 (Kantamare) 8-month HOBO water column to GW elevation (MSL).

Sensor elevation derived from survey (memory: project-wangi-ww4-kantamare):

  WELL_TOP_ELEV         = 8.7071 m MSL (2025 PPP: AJ 10.7901 - AL 2.083)
  LEVEL_INSTRUMENT_HI   = 1.325 m
  FS_TO_CISTERN         = 3.015 m
  STAIRCASE_SUM         = 3.465 m (16 stair steps from field notebook)
  STAIRS_TO_ANCHOR      = 1.040 m
  CORD_LENGTH           = 1.945 m
  -> SENSOR_ELEV        = +0.5671 m MSL

  GW_elev_MSL = SENSOR_ELEV + water_col_m_above_sensor
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

WELL_TOP_ELEV       = 8.7071
LEVEL_INSTRUMENT_HI = 1.325
FS_TO_CISTERN       = 3.015
STAIRCASE_SUM       = 3.465
STAIRS_TO_ANCHOR    = 1.040
CORD_LENGTH         = 1.945
SENSOR_ELEV = (WELL_TOP_ELEV + LEVEL_INSTRUMENT_HI - FS_TO_CISTERN
               - STAIRCASE_SUM - STAIRS_TO_ANCHOR - CORD_LENGTH)
print(f"Sensor elevation = +{SENSOR_ELEV:.4f} m MSL")

df = pd.read_csv(WORK / "ww4_8mo_processed.csv")
df["datetime"] = pd.to_datetime(df["datetime"])
df["GW_elev_MSL"] = SENSOR_ELEV + df["water_col_m"]

print(f"\nGW elevation (MSL) over 8 months:")
print(f"  Period   : {df['datetime'].min()} -> {df['datetime'].max()}")
print(f"  N records: {len(df):,}")
print(f"  Mean     : {df['GW_elev_MSL'].mean():.3f} m MSL")
print(f"  Median   : {df['GW_elev_MSL'].median():.3f} m")
print(f"  Min      : {df['GW_elev_MSL'].min():.3f} m")
print(f"  Max      : {df['GW_elev_MSL'].max():.3f} m")
print(f"  Range    : {df['GW_elev_MSL'].max() - df['GW_elev_MSL'].min():.3f} m")

df["date"] = df["datetime"].dt.date
daily = df.groupby("date").agg(
    GW_mean=("GW_elev_MSL", "mean"),
    GW_min=("GW_elev_MSL", "min"),
    GW_max=("GW_elev_MSL", "max"),
).reset_index()
daily["date"] = pd.to_datetime(daily["date"])

PEST_obs_head_ww04 = 4.155
P3a_sim_L2_ww04 = 5.020
P3a_sim_L1_ww04 = 7.873
gw_truth_mean = df['GW_elev_MSL'].mean()

print(f"\n=== Cross-reference at WW4 ===")
print(f"  PEST obs_head (DTW=5.8 assumed): {PEST_obs_head_ww04:.3f} m")
print(f"  8-month HOBO mean (truth)      : {gw_truth_mean:.3f} m MSL")
print(f"  3D Phase 3a sim L2             : {P3a_sim_L2_ww04:.3f} m")
print(f"  3D Phase 3a sim L1 (cap)       : {P3a_sim_L1_ww04:.3f} m")
print(f"\nBias sim L2 vs HOBO truth       : {P3a_sim_L2_ww04 - gw_truth_mean:+.3f} m")
print(f"Bias sim L2 vs PEST target       : {P3a_sim_L2_ww04 - PEST_obs_head_ww04:+.3f} m")
print(f"PEST target vs HOBO truth        : {PEST_obs_head_ww04 - gw_truth_mean:+.3f} m")

out_csv = WORK / "ww4_8mo_MSL_elev.csv"
df[["datetime", "water_col_m", "GW_elev_MSL", "Temp_C_WP"]].to_csv(
    out_csv, index=False, float_format="%.4f")
print(f"\nSaved: {out_csv}")

fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True,
                          gridspec_kw={"height_ratios": [3, 2]})
ax = axes[0]
ax.plot(df["datetime"], df["GW_elev_MSL"], "b-", lw=0.3, alpha=0.6,
        label=f"Instantaneous (n={len(df):,})")
ax.plot(daily["date"], daily["GW_mean"], "k-", lw=1.5, label="Daily mean")
ax.fill_between(daily["date"], daily["GW_min"], daily["GW_max"],
                color="black", alpha=0.15, label="Daily min-max envelope")
ax.axhline(gw_truth_mean, color="navy", ls="-", lw=1.5, alpha=0.8,
           label=f"8-mo mean = {gw_truth_mean:.2f} m MSL")
ax.axhline(PEST_obs_head_ww04, color="red", ls="--", lw=1.5,
           label=f"PEST obs_head: {PEST_obs_head_ww04:.2f} m (assumed)")
ax.axhline(P3a_sim_L2_ww04, color="green", ls=":", lw=2.0,
           label=f"3D Phase 3a sim L2: {P3a_sim_L2_ww04:.2f} m")
ax.set_ylabel("GW elevation (m, MSL)", fontsize=11)
ax.set_title("WW4 (Kantamare) - 8-month GW elevation in MSL\n"
             f"Sensor elev = +{SENSOR_ELEV:.3f} m MSL (survey) + water col",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)

ax2 = axes[1]
ax2.plot(daily["date"], daily["GW_mean"], "g-", lw=1.4)
daily["GW_mean_30d"] = daily["GW_mean"].rolling(30, min_periods=10).mean()
ax2.plot(daily["date"], daily["GW_mean_30d"], "darkred", lw=2.0,
         label="30-day rolling mean")
days_x = (daily["date"] - daily["date"].iloc[0]).dt.days.values
slope_per_day, intercept = np.polyfit(days_x, daily["GW_mean"].values, 1)
trend = intercept + slope_per_day * days_x
ax2.plot(daily["date"], trend, "k--", lw=1.0,
         label=f"Linear trend: {slope_per_day*30*1000:.1f} mm/month")
ax2.set_xlabel("Date", fontsize=11)
ax2.set_ylabel("Daily mean GW elev (m, MSL)", fontsize=11)
ax2.set_title(f"Seasonal drift Dec 2024 -> Aug 2025 "
              f"(start {daily['GW_mean'].iloc[0]:.2f} -> end {daily['GW_mean'].iloc[-1]:.2f} = "
              f"{daily['GW_mean'].iloc[-1] - daily['GW_mean'].iloc[0]:+.2f} m)",
              fontsize=11, fontweight="bold")
ax2.legend(loc="upper right", fontsize=9)
ax2.grid(alpha=0.3)

plt.tight_layout()
out_fig = FIGDIR / "ww4_8mo_GW_elev_MSL.png"
plt.savefig(out_fig, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out_fig}")
