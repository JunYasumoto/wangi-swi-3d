"""Process the 8-month WW4 (Kantamare) HOBO record:
 - 20241214_WW4_WP.csv  (water pressure)
 - 20241214_WW4_AP.csv  (atmospheric pressure)
 - 22085294.hobo         (EC, probably)

Compute AP-corrected water column and groundwater elevation time series.
Save processed CSV + multi-panel summary figure.
"""
import sys, io, pathlib, re
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
SRC = pathlib.Path(r"C:\Users\安元純\Dropbox\卒論　幸喜泰斗（kouki taito）\2024-2025_Indonesia\HOBOdata")
FIGDIR = WORK / "figs"; FIGDIR.mkdir(exist_ok=True)

WP_FILE = SRC / "20241214_WW4_WP.csv"
AP_FILE = SRC / "20241214_WW4_AP.csv"


def parse_hobo_csv(path):
    df = pd.read_csv(path, skiprows=1)
    dt_col = [c for c in df.columns if "日付" in c or "Date" in c or "GMT" in c][0]
    p_col  = [c for c in df.columns if "絶対圧力" in c or "Pressure" in c or "kPa" in c][0]
    t_col  = [c for c in df.columns if "温度" in c or "Temperature" in c or "°C" in c][0]

    # Parse Japanese AM/PM date format: 12/14/24 02:00:00 午後
    def parse_one(s):
        if pd.isna(s): return None
        s = str(s)
        ampm = "PM" if "午後" in s else ("AM" if "午前" in s else "")
        s2 = re.sub(r"\s*午[前後]\s*", "", s).strip()
        try:
            return pd.to_datetime(f"{s2} {ampm}", format="%m/%d/%y %I:%M:%S %p")
        except Exception:
            try:
                return pd.to_datetime(s2)
            except Exception:
                return None

    df["datetime"] = df[dt_col].apply(parse_one)
    df["P_kPa"]    = pd.to_numeric(df[p_col], errors="coerce")
    df["Temp_C"]   = pd.to_numeric(df[t_col], errors="coerce")
    df = df.dropna(subset=["datetime", "P_kPa"])
    return df[["datetime", "P_kPa", "Temp_C"]]


print("Loading water pressure (WP) ...")
wp = parse_hobo_csv(WP_FILE)
print(f"  WP n={len(wp)}, range {wp.datetime.min()} .. {wp.datetime.max()}")

print("Loading atmospheric pressure (AP) ...")
ap = parse_hobo_csv(AP_FILE)
print(f"  AP n={len(ap)}, range {ap.datetime.min()} .. {ap.datetime.max()}")

# Merge on datetime (inner)
merged = pd.merge_asof(wp.sort_values("datetime"),
                        ap.sort_values("datetime"),
                        on="datetime", suffixes=("_WP", "_AP"),
                        tolerance=pd.Timedelta("5min"))
merged = merged.dropna(subset=["P_kPa_AP"])
print(f"Merged: {len(merged)} records covering "
      f"{merged.datetime.min()} .. {merged.datetime.max()} "
      f"({(merged.datetime.max() - merged.datetime.min()).days} days)")

# Net pressure → water column (kPa to m, using density 1000 kg/m³ × g = 9.789 for freshwater)
merged["dP_kPa"] = merged["P_kPa_WP"] - merged["P_kPa_AP"]
merged["water_col_m"] = merged["dP_kPa"] / 9.789
# Subtract sensor depth offset to get groundwater elevation (relative).
# Assume sensor at well bottom, water_col represents head above sensor.
# For absolute MSL elevation, need sensor's MSL elevation (not known without survey).
# Use water_col for relative GW variation.

# Save processed
out_csv = WORK / "ww4_8mo_processed.csv"
merged[["datetime", "P_kPa_WP", "P_kPa_AP", "dP_kPa", "water_col_m",
        "Temp_C_WP", "Temp_C_AP"]].to_csv(out_csv, index=False, float_format="%.4f")
print(f"Saved processed: {out_csv}")

# === Diagnostics ===
wc = merged["water_col_m"].values
print(f"\nWater column (m above sensor):")
print(f"  range : {wc.min():.3f} .. {wc.max():.3f}  (span {wc.max()-wc.min():.3f} m)")
print(f"  mean  : {wc.mean():.3f}  median {np.median(wc):.3f}")
print(f"  std   : {wc.std():.3f}")

# Daily aggregations for monthly/seasonal view
merged["date"] = merged["datetime"].dt.date
daily = merged.groupby("date").agg(
    wc_min=("water_col_m", "min"),
    wc_max=("water_col_m", "max"),
    wc_mean=("water_col_m", "mean"),
    wc_range=("water_col_m", lambda x: x.max() - x.min()),
).reset_index()
daily["date"] = pd.to_datetime(daily["date"])
print(f"\nDaily ranges (tidal+ETO):")
print(f"  median daily range: {daily['wc_range'].median():.3f} m")
print(f"  max daily range   : {daily['wc_range'].max():.3f} m")
print(f"\nDaily mean drift (Dec → Aug):")
print(f"  start (first 7d mean): {daily['wc_mean'].head(7).mean():.3f} m")
print(f"  end   (last 7d mean) : {daily['wc_mean'].tail(7).mean():.3f} m")
print(f"  drift across 8 months: {daily['wc_mean'].tail(7).mean() - daily['wc_mean'].head(7).mean():+.3f} m")

# === Plot ===
fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True,
                         gridspec_kw={"height_ratios": [3, 2, 1]})

# (1) Full 8-month water column
ax = axes[0]
ax.plot(merged["datetime"], merged["water_col_m"], "b-", lw=0.4, alpha=0.7,
        label=f"WW4 water column (n={len(merged)})")
# Daily mean overlay
ax.plot(daily["date"], daily["wc_mean"], "r-", lw=1.4, label="daily mean")
ax.fill_between(daily["date"], daily["wc_min"], daily["wc_max"],
                color="red", alpha=0.15, label="daily min-max envelope")
ax.set_ylabel("Water column above sensor (m)", fontsize=11)
ax.set_title(f"WW4 (Kantamare) — 8-month HOBO observation, AP-corrected\n"
             f"{merged.datetime.min():%Y-%m-%d} to {merged.datetime.max():%Y-%m-%d}  "
             f"({(merged.datetime.max() - merged.datetime.min()).days} days, "
             f"{len(merged):,} records)",
             fontsize=12, fontweight="bold")
ax.grid(alpha=0.3)
ax.legend(loc="upper right", fontsize=9)

# (2) Daily range (tidal amplitude over time)
ax2 = axes[1]
ax2.plot(daily["date"], daily["wc_range"], "g-", lw=1.0,
         label="Daily range (max − min)")
ax2.axhline(daily["wc_range"].median(), color="purple", ls="--", lw=1,
            alpha=0.7, label=f"median {daily['wc_range'].median():.2f} m")
ax2.axhline(0.464, color="red", ls=":", lw=1.5, alpha=0.8,
            label="Original 43-hr median (0.464 m)")
ax2.set_ylabel("Daily range (m)", fontsize=11)
ax2.legend(loc="upper right", fontsize=9)
ax2.grid(alpha=0.3)

# (3) Temperature
ax3 = axes[2]
ax3.plot(merged["datetime"], merged["Temp_C_WP"], "k-", lw=0.4, alpha=0.6,
         label="Water T (WP sensor)")
ax3.set_ylabel("Temp (°C)", fontsize=11)
ax3.set_xlabel("Date", fontsize=11)
ax3.legend(loc="upper right", fontsize=9)
ax3.grid(alpha=0.3)

plt.tight_layout()
out_fig = FIGDIR / "ww4_8mo_overview.png"
plt.savefig(out_fig, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved figure: {out_fig}")

# === Spectral / tidal harmonic analysis ===
from scipy.signal import welch
fs_records_per_day = 48  # 30-min sampling
# Ensure uniform sampling
merged_idx = merged.set_index("datetime").asfreq("30min").interpolate("linear")
wc_uniform = merged_idx["water_col_m"].values
# Detrend
wc_detrend = wc_uniform - np.nanmean(wc_uniform)
freqs, psd = welch(wc_detrend, fs=fs_records_per_day, nperseg=2048,
                    detrend="linear")
periods = 1 / freqs[1:]  # period in days
psd = psd[1:]

fig2, ax = plt.subplots(figsize=(11, 5))
ax.loglog(periods * 24, psd, "k-", lw=1.0)
# Tidal markers
for T, name in [(12.42/24, "M2"), (12.0/24, "S2"), (24.0/24, "K1"),
                 (25.82/24, "O1"), (12.66/24, "N2"), (14.0, "spring-neap")]:
    ax.axvline(T * 24, color="red", ls="--", alpha=0.5, lw=0.8)
    ax.text(T * 24, psd.max() * 0.5, name, rotation=90, fontsize=9, color="red",
            ha="right", va="top")
ax.set_xlabel("Period (hours)", fontsize=11)
ax.set_ylabel("PSD (m² / cph)", fontsize=11)
ax.set_title(f"WW4 8-month water column — power spectral density\n"
             "Welch's method, 30-min sampling, 2048-pt segments",
             fontsize=11)
ax.grid(alpha=0.3, which="both")
plt.tight_layout()
out_psd = FIGDIR / "ww4_8mo_psd.png"
plt.savefig(out_psd, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved PSD: {out_psd}")
