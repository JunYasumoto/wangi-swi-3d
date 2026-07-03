"""Identify the cord-break + re-tying interval in the 8-month WW4 record.

Visualize the daily mean / range pattern to find:
 - When water column shoots up (cord broke = sensor sank deeper)
 - When it returns to normal baseline (cord re-tied)

Output: zoom plot of the first month to see exact transition dates.
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

df = pd.read_csv(WORK / "ww4_8mo_processed.csv")
df["datetime"] = pd.to_datetime(df["datetime"])
df["water_col_m"] = df["water_col_m"].astype(float)

# Daily stats
df["date"] = df["datetime"].dt.date
daily = df.groupby("date").agg(
    wc_mean=("water_col_m", "mean"),
    wc_min=("water_col_m", "min"),
    wc_max=("water_col_m", "max"),
    wc_std=("water_col_m", "std"),
).reset_index()
daily["date"] = pd.to_datetime(daily["date"])

# Print first 30 days
print("=== First 40 daily statistics (look for jump and return) ===")
print(daily.head(40).to_string(index=False, float_format="%.3f"))

# Sudden change detector: daily means shifting > 0.3 m suggests possible event
daily["dmean"] = daily["wc_mean"].diff()
print("\n=== Days with daily-mean shift > 0.3 m ===")
sus = daily[(daily["dmean"].abs() > 0.3)].copy()
print(sus.to_string(index=False, float_format="%.3f"))

# Visualize the first 40 days only
fig, ax = plt.subplots(figsize=(15, 7))
first_month = df[df["datetime"] < pd.Timestamp("2025-02-01")]
ax.plot(first_month["datetime"], first_month["water_col_m"],
        "b-", lw=0.5, alpha=0.7, label="Instantaneous water col (m above sensor)")
daily_zoom = daily[daily["date"] < pd.Timestamp("2025-02-01")]
ax.plot(daily_zoom["date"], daily_zoom["wc_mean"], "k-", lw=2, label="Daily mean")
ax.fill_between(daily_zoom["date"], daily_zoom["wc_min"], daily_zoom["wc_max"],
                color="black", alpha=0.15, label="Daily min-max")
ax.xaxis.set_major_locator(DayLocator(interval=3))
ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))
plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
ax.set_ylabel("Water column above sensor (m)", fontsize=11)
ax.set_xlabel("2024-12 to 2025-01")
ax.set_title("WW4 HOBO — first ~50 days zoom\n"
             "Identify cord-break event (sensor falls = water col reads HIGHER) and re-tying date",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)
ax.axhline(daily["wc_mean"].iloc[35:].mean(), color="red", ls="--", lw=1, alpha=0.6,
           label=f"steady baseline ≈ {daily['wc_mean'].iloc[35:].mean():.2f} m")
plt.tight_layout()
out = FIGDIR / "ww4_cord_break_zoom.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"\nSaved: {out}")
