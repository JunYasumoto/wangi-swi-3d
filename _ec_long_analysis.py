"""Full 5-month EC + WP+AP combined analysis at WW4 (Kantamare).

Datasets:
  ww4_EC_long_processed.csv  (5 months EC, 30-min sampling, 2024-12-14 to 2025-05-18)
  ww4_8mo_processed.csv      (8 months WP+AP, same start)
Combined: 5 months of EC + WP + AP (limit by EC end)

Sensor elevation +0.5671 m MSL (survey-derived).

Analyses:
 (1) Filter to clean post-cord-retie window (2025-01-16 onwards) for tidal/seasonal stats
 (2) Tidal coupling: lag-correlation EC vs water column (M2 phase)
 (3) Spring-neap modulation: 14-day envelope of EC and WC
 (4) Cl-EC conversion: sea fraction (%) time series
 (5) Seasonal trend: monthly mean Cl% to test recharge dilution

Outputs:
 ww4_combined_EC_WP.csv
 figs/ww4_ec_long_timeseries.png       (5mo time series)
 figs/ww4_ec_wp_lagged_correlation.png (cross-correlation)
 figs/ww4_ec_seasonal.png               (monthly/spring-neap envelopes)
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MonthLocator
from scipy.signal import correlate

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

SENSOR_ELEV = 0.5671
CLEAN_START = pd.Timestamp("2025-01-16 00:00:00")

# Load
ec = pd.read_csv(WORK / "ww4_EC_long_processed.csv")
ec["dt"] = pd.to_datetime(ec["dt"])
ec = ec.rename(columns={"dt": "datetime", "EC": "EC_uScm", "T_C": "Temp_EC_C"})

wp = pd.read_csv(WORK / "ww4_8mo_processed.csv")
wp["datetime"] = pd.to_datetime(wp["datetime"])
wp["GW_elev_MSL"] = SENSOR_ELEV + wp["water_col_m"]

# Merge on nearest time (within 30 min)
merged = pd.merge_asof(wp.sort_values("datetime"),
                       ec.sort_values("datetime"),
                       on="datetime", tolerance=pd.Timedelta("30min"))
merged = merged.dropna(subset=["EC_uScm"])
print(f"Merged: {len(merged)} records covering {merged.datetime.min()} -> {merged.datetime.max()}")
print(f"  span: {(merged.datetime.max() - merged.datetime.min()).days} days")

# Clean window
clean = merged[merged["datetime"] >= CLEAN_START].copy()
print(f"\nClean post-retie window: {len(clean)} records "
      f"({clean.datetime.min()} -> {clean.datetime.max()}, "
      f"{(clean.datetime.max() - clean.datetime.min()).days} days)")

# Save
merged_path = WORK / "ww4_combined_EC_WP.csv"
merged[["datetime", "GW_elev_MSL", "water_col_m",
        "EC_uScm", "Temp_EC_C", "Temp_C_WP"]].to_csv(
    merged_path, index=False, float_format="%.3f")
print(f"Saved: {merged_path}")

# ---- Cl-EC conversion ----
# Empirical relation for seawater dilution at typical conditions:
#   EC at 25°C [µS/cm] ≈ 1.85 × Cl- [mg/L] + 800  (mixed waters, freshwater offset ~800)
# Or simpler binary mixing:
#   sw_frac = (EC - EC_rain) / (EC_sw - EC_rain)
EC_RAIN = 100.0     # µS/cm pure rain
EC_SW = 53000.0     # µS/cm typical Wakatobi seawater
clean["sw_frac_pct"] = (clean["EC_uScm"] - EC_RAIN) / (EC_SW - EC_RAIN) * 100
print(f"\nSW fraction (clean window): mean {clean['sw_frac_pct'].mean():.2f}%, "
      f"range {clean['sw_frac_pct'].min():.2f} - {clean['sw_frac_pct'].max():.2f}%")

# ---- Tidal correlation (clean window) ----
print(f"\n=== Tidal coupling (clean window) ===")
from scipy.stats import pearsonr
r, p = pearsonr(clean["water_col_m"].values, clean["EC_uScm"].values)
print(f"Pearson r(water_col, EC) = {r:+.3f}  p={p:.2e}")

# Lagged
wc_n = (clean["water_col_m"].values - clean["water_col_m"].mean()) / clean["water_col_m"].std()
ec_n = (clean["EC_uScm"].values - clean["EC_uScm"].mean()) / clean["EC_uScm"].std()
ccor = correlate(ec_n, wc_n, mode="full") / len(wc_n)
mid = len(ccor) // 2
HALF = 72  # ±36 hr at 30-min sampling
sl = ccor[mid-HALF:mid+HALF+1]
lag_30min = np.arange(-HALF, HALF+1)
peak_idx = np.argmax(np.abs(sl))
peak_lag = lag_30min[peak_idx]
peak_val = sl[peak_idx]
print(f"Peak |corr| = {peak_val:+.3f} at lag = {peak_lag*30} min "
      f"({'EC leads' if peak_lag<0 else 'EC lags'} water column)")

# ---- Daily means ----
clean["date"] = clean["datetime"].dt.date
daily = clean.groupby("date").agg(
    EC_mean=("EC_uScm", "mean"),
    EC_min=("EC_uScm", "min"),
    EC_max=("EC_uScm", "max"),
    EC_range=("EC_uScm", lambda x: x.max() - x.min()),
    sw_frac_mean=("sw_frac_pct", "mean"),
    GW_mean=("GW_elev_MSL", "mean"),
).reset_index()
daily["date"] = pd.to_datetime(daily["date"])

# ---- 14-day rolling envelope ----
daily["EC_min_14d"] = daily["EC_mean"].rolling(14, min_periods=7, center=True).min()
daily["EC_max_14d"] = daily["EC_mean"].rolling(14, min_periods=7, center=True).max()
daily["EC_med_14d"] = daily["EC_mean"].rolling(14, min_periods=7, center=True).median()
daily["GW_med_14d"] = daily["GW_mean"].rolling(14, min_periods=7, center=True).median()

# ---- Plot 1: 5-month time series ----
fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True)

ax = axes[0]
ax.plot(merged["datetime"], merged["EC_uScm"], "k-", lw=0.3, alpha=0.6,
        label=f"Instantaneous (n={len(merged):,})")
ax.plot(daily["date"], daily["EC_mean"], "r-", lw=1.5, label="Daily mean (clean)")
ax.fill_between(daily["date"], daily["EC_min"], daily["EC_max"],
                color="red", alpha=0.12, label="Daily min-max")
ax.axvline(CLEAN_START, color="orange", ls="--", lw=1.5, alpha=0.7,
           label="Cord re-tied 2025-01-16")
ax.set_ylabel("EC (µS/cm)", fontsize=11)
ax.set_title(f"WW4 (Kantamare) — 5-month EC continuous record (2024-12-14 to 2025-05-18)\n"
             f"Clean mean EC = {clean['EC_uScm'].mean():.0f} µS/cm, "
             f"daily range median = {daily['EC_range'].median():.0f}",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)

# WP + EC combined
ax2 = axes[1]
ax2t = ax2.twinx()
l1 = ax2.plot(daily["date"], daily["GW_mean"], "b-", lw=1.4, label="Daily mean GW elev (MSL)")
l2 = ax2.plot(daily["date"], daily["GW_med_14d"], "darkblue", lw=2.2, alpha=0.9,
              label="14-day median GW elev")
l3 = ax2t.plot(daily["date"], daily["EC_mean"], "r-", lw=1.4, label="Daily mean EC")
l4 = ax2t.plot(daily["date"], daily["EC_med_14d"], "darkred", lw=2.2, alpha=0.9,
                label="14-day median EC")
ax2.set_ylabel("GW elev (m MSL)", fontsize=11, color="darkblue")
ax2t.set_ylabel("EC (µS/cm)", fontsize=11, color="darkred")
ax2.tick_params(axis="y", labelcolor="darkblue")
ax2t.tick_params(axis="y", labelcolor="darkred")
ax2.set_title("GW elev vs EC daily means (clean window) — looking for anti-correlation",
              fontsize=11, fontweight="bold")
ls = l1 + l2 + l3 + l4
ax2.legend(ls, [l.get_label() for l in ls], loc="upper right", fontsize=8)
ax2.grid(alpha=0.3)

# Seawater fraction
ax3 = axes[2]
ax3.plot(daily["date"], daily["sw_frac_mean"], "purple", lw=1.4)
sw_field_dec = 2.27
ax3.axhline(sw_field_dec, color="orange", ls="--", lw=1.2,
            label=f"Dec 2024 single sample Cl-: {sw_field_dec:.2f}%")
ax3.set_ylabel("Seawater fraction (%)", fontsize=11)
ax3.set_xlabel("Date", fontsize=11)
ax3.set_title(f"Seawater fraction time series (EC-based, EC_rain=100, EC_sw=53000)\n"
              f"Mean = {clean['sw_frac_pct'].mean():.2f}% "
              f"(range {clean['sw_frac_pct'].min():.2f}-{clean['sw_frac_pct'].max():.2f}%)",
              fontsize=11, fontweight="bold")
ax3.legend(loc="upper right", fontsize=9)
ax3.grid(alpha=0.3)
ax3.xaxis.set_major_locator(MonthLocator())
ax3.xaxis.set_major_formatter(DateFormatter("%Y-%m"))

plt.tight_layout()
out1 = FIGDIR / "ww4_ec_long_timeseries.png"
plt.savefig(out1, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out1}")

# ---- Plot 2: Lag cross-correlation + spring-neap zoom ----
fig, axes = plt.subplots(2, 1, figsize=(14, 9))

ax = axes[0]
ax.plot(lag_30min*30/60, sl, "b-", lw=1.4)
ax.axvline(0, color="gray", lw=0.5)
ax.axvline(peak_lag*30/60, color="red", ls="--",
           label=f"Peak |corr|={peak_val:+.3f} at lag={peak_lag*30:+d} min "
                 f"({'EC leads' if peak_lag<0 else 'EC lags'})")
ax.set_xlabel("Lag of EC vs water column (hours)")
ax.set_ylabel("Cross-correlation")
ax.set_title(f"EC vs water column cross-correlation, clean window\n"
             f"({len(clean):,} records, n=±{HALF*30/60:.0f} hr lag scan)",
             fontsize=11, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(alpha=0.3)

# Spring-neap zoom: pick a 30-day window with clear spring-neap cycle
zoom_start = pd.Timestamp("2025-02-01")
zoom_end   = pd.Timestamp("2025-03-15")
zoom = clean[(clean["datetime"] >= zoom_start) & (clean["datetime"] <= zoom_end)].copy()
ax2 = axes[1]
ax2t = ax2.twinx()
l1 = ax2.plot(zoom["datetime"], zoom["water_col_m"], "b-", lw=0.5, alpha=0.8, label="Water col")
l2 = ax2t.plot(zoom["datetime"], zoom["EC_uScm"], "r-", lw=0.5, alpha=0.8, label="EC")
ax2.set_ylabel("Water column above sensor (m)", color="darkblue")
ax2t.set_ylabel("EC (µS/cm)", color="darkred")
ax2.tick_params(axis="y", labelcolor="darkblue")
ax2t.tick_params(axis="y", labelcolor="darkred")
ax2.set_title(f"Zoom: {zoom_start:%Y-%m-%d} to {zoom_end:%Y-%m-%d} "
              f"(spring-neap cycle visible)",
              fontsize=11, fontweight="bold")
ls = l1 + l2
ax2.legend(ls, [l.get_label() for l in ls], loc="upper right", fontsize=10)
ax2.grid(alpha=0.3)
ax2.xaxis.set_major_locator(MonthLocator())

plt.tight_layout()
out2 = FIGDIR / "ww4_ec_wp_lagged_correlation.png"
plt.savefig(out2, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out2}")

# ---- Plot 3: monthly statistics ----
clean["month"] = clean["datetime"].dt.to_period("M").astype(str)
monthly = clean.groupby("month").agg(
    EC_mean=("EC_uScm", "mean"),
    EC_std=("EC_uScm", "std"),
    EC_range_med=("EC_uScm", lambda x: x.max() - x.min()),
    GW_mean=("GW_elev_MSL", "mean"),
    sw_frac_mean=("sw_frac_pct", "mean"),
    n=("EC_uScm", "count"),
).reset_index()
print("\n=== Monthly stats (clean window) ===")
print(monthly.to_string(index=False, float_format="%.2f"))

fig, ax = plt.subplots(figsize=(11, 6))
ax2 = ax.twinx()
x = np.arange(len(monthly))
b1 = ax.bar(x - 0.2, monthly["EC_mean"], 0.4, color="darkred",
            label="EC monthly mean", alpha=0.85)
ax.errorbar(x - 0.2, monthly["EC_mean"], yerr=monthly["EC_std"],
            fmt="none", color="black", capsize=4)
b2 = ax2.bar(x + 0.2, monthly["GW_mean"], 0.4, color="darkblue",
             label="GW elev monthly mean (MSL)", alpha=0.85)
ax.set_xticks(x); ax.set_xticklabels(monthly["month"], rotation=45)
ax.set_ylabel("EC (µS/cm)", color="darkred")
ax2.set_ylabel("GW elev (m MSL)", color="darkblue")
ax.tick_params(axis="y", labelcolor="darkred")
ax2.tick_params(axis="y", labelcolor="darkblue")
ax.set_title("Monthly mean EC and GW elev (clean post-retie window)\n"
             "Higher GW = less SWI? Lower EC = more freshwater? Test seasonal coupling",
             fontsize=11, fontweight="bold")
ax.legend([b1, b2], ["EC monthly mean ± std", "GW elev monthly mean"], loc="upper left")
ax.grid(alpha=0.3, axis="y")
plt.tight_layout()
out3 = FIGDIR / "ww4_ec_seasonal.png"
plt.savefig(out3, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out3}")

# ---- Anti-correlation across months ----
gw_monthly = monthly["GW_mean"].values
ec_monthly = monthly["EC_mean"].values
if len(gw_monthly) >= 3:
    rm, pm = pearsonr(gw_monthly, ec_monthly)
    print(f"\nMonthly Pearson r(GW_elev, EC) = {rm:+.3f}, p = {pm:.3f}")
    print(f"  ({'Anti-corr: higher GW → lower EC = lens-freshening' if rm < -0.3 else 'corr not strong or positive'})")
