"""Re-analyze WW4 (Kantamare) using only post-cord-retie data (2025-01-16 onwards).

Tasks:
 1. Filter to clean window (post 2025-01-16)
 2. Convert to MSL using survey-derived sensor elev +0.5671 m
 3. Re-compute mean, range, seasonal drift
 4. Search for pumping signatures:
    - Diurnal cycle (24-hr period vs M2 12.4 hr)
    - Weekly pattern (school/weekend usage)
    - Sudden drops (pumping events) — autocorrelation, periodogram, rolling std
 5. Compare to model

Outputs:
  ww4_clean_MSL.csv
  figs/ww4_clean_overview.png
  figs/ww4_diurnal_pumping.png
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import welch, periodogram
from matplotlib.dates import DateFormatter, HourLocator

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

SENSOR_ELEV = 0.5671   # m MSL (survey-derived)
CLEAN_START = pd.Timestamp("2025-01-16 00:00:00")   # post re-tie

# Load 8-month processed + filter
df_all = pd.read_csv(WORK / "ww4_8mo_processed.csv")
df_all["datetime"] = pd.to_datetime(df_all["datetime"])

df = df_all[df_all["datetime"] >= CLEAN_START].copy().reset_index(drop=True)
df["GW_elev_MSL"] = SENSOR_ELEV + df["water_col_m"]
print(f"Clean window: {df['datetime'].min()} -> {df['datetime'].max()}")
print(f"  Duration: {(df['datetime'].max() - df['datetime'].min()).days} days")
print(f"  N records: {len(df):,}")

print(f"\n=== WW4 GW elev (MSL), clean record only ===")
print(f"  Mean   : {df['GW_elev_MSL'].mean():.3f} m MSL")
print(f"  Median : {df['GW_elev_MSL'].median():.3f} m")
print(f"  Min    : {df['GW_elev_MSL'].min():.3f} m")
print(f"  Max    : {df['GW_elev_MSL'].max():.3f} m")
print(f"  Range  : {df['GW_elev_MSL'].max() - df['GW_elev_MSL'].min():.3f} m")
print(f"  Std    : {df['GW_elev_MSL'].std():.3f} m")

# Save clean MSL
df[["datetime", "water_col_m", "GW_elev_MSL", "Temp_C_WP"]].to_csv(
    WORK / "ww4_clean_MSL.csv", index=False, float_format="%.4f")
print(f"Saved: ww4_clean_MSL.csv")

# Cross-reference
PEST_obs_head_ww04 = 4.155
P3a_sim_L2_ww04   = 5.020
print(f"\n=== Cross-reference (clean truth) ===")
print(f"  Clean HOBO mean        : {df['GW_elev_MSL'].mean():.3f} m MSL  ← TRUE Kantamare")
print(f"  PEST obs_head          : {PEST_obs_head_ww04:.3f} m")
print(f"  3D Phase 3a sim L2     : {P3a_sim_L2_ww04:.3f} m")
print(f"  Bias sim L2 vs clean   : {P3a_sim_L2_ww04 - df['GW_elev_MSL'].mean():+.3f} m")
print(f"  PEST vs clean truth    : {PEST_obs_head_ww04 - df['GW_elev_MSL'].mean():+.3f} m")

# Daily stats
df["date"] = df["datetime"].dt.date
daily = df.groupby("date").agg(
    GW_mean=("GW_elev_MSL", "mean"),
    GW_min=("GW_elev_MSL", "min"),
    GW_max=("GW_elev_MSL", "max"),
    GW_range=("GW_elev_MSL", lambda x: x.max() - x.min()),
).reset_index()
daily["date"] = pd.to_datetime(daily["date"])

# === Diurnal / pumping signal analysis ===
# Compute mean by hour of day (over all days in clean window)
df["hour"] = df["datetime"].dt.hour
df["min_in_hr"] = df["datetime"].dt.minute
df["doy"] = df["datetime"].dt.dayofyear
diurnal = df.groupby("hour")["GW_elev_MSL"].agg(["mean", "std", "count"]).reset_index()
diurnal["mean_dev"] = diurnal["mean"] - df["GW_elev_MSL"].mean()
print("\n=== Diurnal-mean GW elev (m MSL deviation from overall mean) ===")
print(diurnal[["hour", "mean", "mean_dev", "std"]].to_string(index=False, float_format="%.4f"))

# Day-of-week analysis
df["dow"] = df["datetime"].dt.dayofweek
dow_means = df.groupby("dow")["GW_elev_MSL"].mean()
print("\n=== Day-of-week mean ===")
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for d, name in zip(dow_means.index, days):
    print(f"  {name}: {dow_means[d]:.3f} m")

# PSD focusing on pumping bands
df_idx = df.set_index("datetime").asfreq("30min").interpolate("linear")
wc = df_idx["GW_elev_MSL"].values
wc = wc - np.nanmean(wc)
# Detrend
wc = wc - np.linspace(np.nanmean(wc[:200]), np.nanmean(wc[-200:]), len(wc))
fs = 48  # samples/day (30-min sampling)
freqs, psd = welch(wc, fs=fs, nperseg=4096, detrend="linear")
periods_hr = 1 / freqs[1:] * 24
psd_arr = psd[1:]

# === Plot 1: Time series overview ===
fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True,
                          gridspec_kw={"height_ratios": [3, 2, 1]})
ax = axes[0]
ax.plot(df["datetime"], df["GW_elev_MSL"], "b-", lw=0.3, alpha=0.6,
         label=f"Instantaneous (n={len(df):,})")
ax.plot(daily["date"], daily["GW_mean"], "k-", lw=1.5, label="Daily mean")
ax.fill_between(daily["date"], daily["GW_min"], daily["GW_max"],
                 color="black", alpha=0.15, label="Daily min-max")
ax.axhline(df["GW_elev_MSL"].mean(), color="navy", ls="-", lw=1.4, alpha=0.8,
            label=f"Clean mean = {df['GW_elev_MSL'].mean():.2f} m MSL")
ax.axhline(P3a_sim_L2_ww04, color="green", ls=":", lw=2.0,
            label=f"3D Phase 3a sim L2: {P3a_sim_L2_ww04:.2f} m")
ax.axhline(PEST_obs_head_ww04, color="red", ls="--", lw=1.2,
            label=f"PEST target: {PEST_obs_head_ww04:.2f} m")
ax.set_ylabel("GW elev (m MSL)", fontsize=11)
ax.set_title(f"WW4 (Kantamare) — clean post-cord-retie record\n"
              f"2025-01-16 to 2025-08-13 ({(df['datetime'].max() - df['datetime'].min()).days} days)",
              fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)

ax2 = axes[1]
days_x = (daily["date"] - daily["date"].iloc[0]).dt.days.values
slope_per_day, intercept = np.polyfit(days_x, daily["GW_mean"].values, 1)
trend = intercept + slope_per_day * days_x
ax2.plot(daily["date"], daily["GW_mean"], "g-", lw=1.4, label="Daily mean")
daily["GW_30d"] = daily["GW_mean"].rolling(30, min_periods=10).mean()
ax2.plot(daily["date"], daily["GW_30d"], "darkred", lw=2.0, label="30-day rolling mean")
ax2.plot(daily["date"], trend, "k--", lw=1.0,
          label=f"Trend: {slope_per_day*30*1000:.1f} mm/month")
ax2.set_ylabel("Daily mean (m MSL)", fontsize=10)
ax2.set_title(f"Seasonal drift "
               f"(start {daily['GW_mean'].iloc[0]:.2f} -> end {daily['GW_mean'].iloc[-1]:.2f} = "
               f"{daily['GW_mean'].iloc[-1] - daily['GW_mean'].iloc[0]:+.2f} m)",
               fontsize=10)
ax2.legend(loc="upper right", fontsize=9)
ax2.grid(alpha=0.3)

ax3 = axes[2]
ax3.plot(daily["date"], daily["GW_range"], "orange", lw=1.0)
ax3.axhline(daily["GW_range"].median(), color="purple", ls="--", lw=1,
             alpha=0.7, label=f"median {daily['GW_range'].median():.2f} m")
ax3.set_ylabel("Daily range (m)", fontsize=10)
ax3.set_xlabel("Date")
ax3.legend(loc="upper right", fontsize=9)
ax3.grid(alpha=0.3)

plt.tight_layout()
out1 = FIGDIR / "ww4_clean_overview.png"
plt.savefig(out1, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out1}")

# === Plot 2: Pumping signature search ===
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

# (a) Diurnal cycle
ax = axes[0, 0]
ax.bar(diurnal["hour"], diurnal["mean_dev"], color="steelblue", edgecolor="black", linewidth=0.5)
ax.set_xticks(range(0, 24, 2))
ax.set_xlabel("Hour of day (local)")
ax.set_ylabel("Mean GW elev anomaly (m)")
ax.set_title(f"Diurnal cycle — pump signature?\n"
              f"amplitude = {diurnal['mean_dev'].max() - diurnal['mean_dev'].min():.4f} m peak-to-peak",
              fontsize=11, fontweight="bold")
ax.axhline(0, color="black", lw=0.5)
ax.grid(alpha=0.3)

# (b) Day-of-week pattern
ax = axes[0, 1]
dow_dev = dow_means.values - df["GW_elev_MSL"].mean()
ax.bar(days, dow_dev, color="orange", edgecolor="black", linewidth=0.5)
ax.set_ylabel("Mean GW elev anomaly (m)")
ax.set_title(f"Day-of-week pattern — weekly pump cycle?\n"
              f"amplitude = {dow_dev.max() - dow_dev.min():.4f} m",
              fontsize=11, fontweight="bold")
ax.axhline(0, color="black", lw=0.5)
ax.grid(alpha=0.3)

# (c) PSD (broad period range)
ax = axes[1, 0]
ax.loglog(periods_hr, psd_arr, "k-", lw=0.9)
for T, name, color in [(12.42, "M2", "red"), (24.0, "K1+24h", "purple"),
                        (12.0, "S2", "red"), (25.82, "O1", "purple"),
                        (168, "weekly", "orange"), (8, "diurnal-pump?", "green")]:
    ax.axvline(T, color=color, ls=":", lw=1.0, alpha=0.7)
    ax.text(T, psd_arr.max() * 0.5, name, fontsize=9, color=color,
             rotation=90, ha="right", va="top")
ax.set_xlabel("Period (hours)")
ax.set_ylabel("PSD")
ax.set_title("Power spectral density — clean window\n(M2 + S2 = tidal, K1 + O1 also tidal but 24h = pump?)",
              fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, which="both")

# (d) Hour-of-day composite (median across all days, in time-of-day units)
ax = axes[1, 1]
df["minute_of_day"] = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
mod = df.groupby("minute_of_day")["GW_elev_MSL"].agg(["mean", "std"]).reset_index()
mod["hod"] = mod["minute_of_day"] / 60
mod["mean_dev"] = mod["mean"] - df["GW_elev_MSL"].mean()
ax.plot(mod["hod"], mod["mean_dev"], "b-", lw=1.5)
ax.fill_between(mod["hod"], mod["mean_dev"] - mod["std"], mod["mean_dev"] + mod["std"],
                 alpha=0.2, color="blue")
ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Hour of day (local, fine resolution)")
ax.set_ylabel("Mean GW elev anomaly (m)")
ax.set_title(f"Composite diurnal cycle (high-res)\nstd band shows day-to-day variability",
              fontsize=11, fontweight="bold")
ax.set_xticks(range(0, 25, 3))
ax.set_xlim(0, 24)
ax.grid(alpha=0.3)

plt.tight_layout()
out2 = FIGDIR / "ww4_diurnal_pumping.png"
plt.savefig(out2, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out2}")

# Pumping interpretation
print("\n=== Pumping signature interpretation ===")
diurnal_amp = diurnal["mean_dev"].max() - diurnal["mean_dev"].min()
weekly_amp = dow_dev.max() - dow_dev.min()
print(f"  Diurnal anomaly amplitude (peak-to-peak): {diurnal_amp*1000:.1f} mm")
print(f"  Weekly anomaly amplitude (peak-to-peak) : {weekly_amp*1000:.1f} mm")
if diurnal_amp > 0.05:
    print("  → Diurnal cycle > 5 cm: pumping likely visible")
elif diurnal_amp > 0.02:
    print("  → Diurnal cycle 2-5 cm: subtle pumping signature")
else:
    print("  → Diurnal cycle < 2 cm: pumping not strongly detected (or compensated by tides)")
if weekly_amp > 0.05:
    print("  → Weekly pattern > 5 cm: weekly pumping schedule detectable")
else:
    print("  → Weekly pattern weak: no obvious week-cycle")
