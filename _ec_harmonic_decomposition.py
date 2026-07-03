"""Harmonic decomposition of 5-month EC and water column at WW4 (Kantamare).

Decompose both signals into the main tidal constituents (M2, S2, K1, O1, N2)
using least-squares harmonic fitting. Then compare amplitude ratios and phase
lags constituent-by-constituent — this reveals how the conduit network filters
different tidal frequencies and gives independent transit time estimates.

For each constituent ω:
  signal(t) = A·cos(ωt) + B·sin(ωt) + linear drift
  amplitude = sqrt(A²+B²)
  phase     = atan2(B, A)

For each (EC, water_col) constituent pair:
  - amplitude ratio (EC / water): conduit's salt advection efficiency at that ω
  - phase lag: travel time for that frequency

Output: figs/ec_harmonic_decomposition.png + table
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MonthLocator

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

CLEAN_START = pd.Timestamp("2025-01-16")
df = pd.read_csv(WORK / "ww4_combined_EC_WP.csv")
df["datetime"] = pd.to_datetime(df["datetime"])
df = df[df["datetime"] >= CLEAN_START].copy().reset_index(drop=True)
print(f"Clean window: {df['datetime'].min()} -> {df['datetime'].max()}, n={len(df)}")

# Time in days since first record
t0 = df["datetime"].iloc[0]
df["t_days"] = (df["datetime"] - t0).dt.total_seconds() / 86400.0

# Tidal constituent periods (hours)
constituents = {
    "M2": 12.4206,
    "S2": 12.0000,
    "N2": 12.6583,
    "K1": 23.9345,
    "O1": 25.8193,
    "K2":  11.9672,
}

def fit_harmonic(t_days, y, periods_hr):
    """Least-squares fit: y = c0 + c1·t + Σ (A_i·cos(ω_i t) + B_i·sin(ω_i t))"""
    n = len(t_days)
    n_const = len(periods_hr)
    G = np.zeros((n, 2 + 2*n_const))
    G[:, 0] = 1.0
    G[:, 1] = t_days  # linear drift
    for i, T_hr in enumerate(periods_hr):
        omega = 2*np.pi / (T_hr/24)   # rad / day
        G[:, 2 + 2*i]     = np.cos(omega * t_days)
        G[:, 2 + 2*i + 1] = np.sin(omega * t_days)
    coefs, _, _, _ = np.linalg.lstsq(G, y, rcond=None)
    return coefs

# Fit both EC and water column
periods_hr = list(constituents.values())
period_names = list(constituents.keys())
ec_coefs = fit_harmonic(df["t_days"].values, df["EC_uScm"].values, periods_hr)
wc_coefs = fit_harmonic(df["t_days"].values, df["water_col_m"].values, periods_hr)

# Extract per-constituent amplitudes and phases
results = []
for i, (name, T_hr) in enumerate(constituents.items()):
    A_ec = ec_coefs[2 + 2*i]
    B_ec = ec_coefs[2 + 2*i + 1]
    A_wc = wc_coefs[2 + 2*i]
    B_wc = wc_coefs[2 + 2*i + 1]
    amp_ec = np.sqrt(A_ec**2 + B_ec**2)
    amp_wc = np.sqrt(A_wc**2 + B_wc**2)
    # Phase in radians; convert to time delay in minutes
    phase_ec = np.arctan2(B_ec, A_ec)
    phase_wc = np.arctan2(B_wc, A_wc)
    # Phase difference: EC relative to water; positive = EC lags
    dphi = (phase_ec - phase_wc + np.pi) % (2*np.pi) - np.pi  # wrap to [-π, π]
    lag_min = dphi / (2*np.pi) * (T_hr * 60)
    # Amplitude ratio
    amp_ratio = amp_ec / amp_wc   # µS/cm per m of water column
    results.append({
        "constituent": name,
        "period_hr": T_hr,
        "wc_amp_m": amp_wc,
        "ec_amp_uScm": amp_ec,
        "amp_ratio_uS_per_m": amp_ratio,
        "phase_lag_min": lag_min,
    })

res = pd.DataFrame(results)
print("\n=== Per-constituent harmonic analysis ===")
print(res.to_string(index=False, float_format="%.3f"))

res.to_csv(WORK / "ec_wc_harmonics.csv", index=False, float_format="%.4f")
print(f"\nSaved: ec_wc_harmonics.csv")

# ===== Plot =====
fig, axes = plt.subplots(2, 2, figsize=(15, 11))

# (a) Constituent amplitudes — bar plot
ax = axes[0, 0]
x = np.arange(len(res))
w = 0.35
ax.bar(x - w/2, res["wc_amp_m"]*100, w, color="steelblue",
       edgecolor="black", label="Water column (cm)")
axb = ax.twinx()
axb.bar(x + w/2, res["ec_amp_uScm"], w, color="darkred",
        edgecolor="black", label="EC (µS/cm)")
ax.set_xticks(x); ax.set_xticklabels(res["constituent"])
ax.set_ylabel("Water amplitude (cm)", color="steelblue", fontsize=11)
axb.set_ylabel("EC amplitude (µS/cm)", color="darkred", fontsize=11)
ax.tick_params(axis="y", labelcolor="steelblue")
axb.tick_params(axis="y", labelcolor="darkred")
ax.set_title("(a) Per-constituent amplitudes\n"
             "M2 dominant in both, K1/O1 also significant",
             fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, axis="y")

# (b) Phase lag per constituent
ax = axes[0, 1]
colors = ["green" if l > 0 else "red" for l in res["phase_lag_min"]]
bars = ax.bar(res["constituent"], res["phase_lag_min"], color=colors,
              edgecolor="black", linewidth=1.0)
for bar, lag in zip(bars, res["phase_lag_min"]):
    y_text = lag + (5 if lag > 0 else -5)
    ax.text(bar.get_x() + bar.get_width()/2, y_text,
            f"{lag:+.0f} min", ha="center", fontsize=9, fontweight="bold")
ax.axhline(0, color="black", lw=0.7)
ax.set_ylabel("EC lag relative to water (min)", fontsize=11)
ax.set_title("(b) EC-water phase lag per constituent\n"
             "Positive = EC lags water (= conduit transit)",
             fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, axis="y")

# (c) Amplitude ratio per frequency
ax = axes[1, 0]
ax.bar(res["constituent"], res["amp_ratio_uS_per_m"],
       color="purple", edgecolor="black", linewidth=1.0)
for i, v in enumerate(res["amp_ratio_uS_per_m"]):
    ax.text(i, v*1.05, f"{v:.0f}", ha="center", fontsize=10, fontweight="bold")
ax.set_ylabel("EC amplitude / water amplitude (µS/cm per m)", fontsize=11)
ax.set_title("(c) Conduit advection efficiency by frequency\n"
             "Higher ratio = stronger salt advection per unit pressure swing",
             fontsize=11, fontweight="bold")
ax.grid(alpha=0.3, axis="y")

# (d) Fitted vs observed time series (zoom)
ax = axes[1, 1]
# Reconstruct fitted EC signal
G = np.zeros((len(df), 2 + 2*len(constituents)))
G[:, 0] = 1.0
G[:, 1] = df["t_days"].values
for i, T_hr in enumerate(periods_hr):
    omega = 2*np.pi / (T_hr/24)
    G[:, 2 + 2*i]     = np.cos(omega * df["t_days"].values)
    G[:, 2 + 2*i + 1] = np.sin(omega * df["t_days"].values)
ec_fit = G @ ec_coefs
zoom_start = pd.Timestamp("2025-02-15"); zoom_end = pd.Timestamp("2025-02-22")
zoom = df[(df["datetime"] >= zoom_start) & (df["datetime"] <= zoom_end)]
zoom_fit = ec_fit[zoom.index.values]
ax.plot(zoom["datetime"], zoom["EC_uScm"], "k-", lw=0.6, alpha=0.7,
        label="Observed EC")
ax.plot(zoom["datetime"], zoom_fit, "r-", lw=1.2,
        label="Harmonic fit (6 constituents)")
residual_std = (zoom["EC_uScm"] - zoom_fit).std()
ax.set_ylabel("EC (µS/cm)", fontsize=11)
ax.set_title(f"(d) Observed vs harmonic-fit EC (1 week zoom)\n"
             f"Residual std = {residual_std:.0f} µS/cm",
             fontsize=11, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))

fig.suptitle("WW4 5-month harmonic decomposition: EC vs water column\n"
             "Independent conduit-transit estimate per tidal frequency",
             fontsize=14, fontweight="bold", y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.97])
out = FIGDIR / "ec_harmonic_decomposition.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")
