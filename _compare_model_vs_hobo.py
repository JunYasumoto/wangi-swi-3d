"""Compare 3D SWI Phase 3b model output vs WW4 HOBO observation at Kantamare."""
import sys, io, pathlib, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent

# --- Load model time series ---
ts = pd.read_csv(WORK / "phase3b_kant_ts_notva_full138_v2.csv")
SPINUP = 24.0
tid_m = ts["is_tidal_phase"].values
t_hr_model = ts["time_hr"].values[tid_m] - SPINUP   # hours after spinup
h_L2_model = ts["head_L2_kant"].values[tid_m]
h_L1_model = ts["head_L1_kant"].values[tid_m]

# Center model heads around their mean for amplitude comparison
h_L2_centered = h_L2_model - h_L2_model.mean()
h_L1_centered = h_L1_model - h_L1_model.mean()
print(f"Model L2 mean = {h_L2_model.mean():.3f} m, range = {h_L2_centered.max()-h_L2_centered.min():.3f} m")

# --- Load HOBO obs ---
wp = pd.read_csv(r"C:\Users\安元純\Dropbox\地球研\Wakatobi\wangiwangi_HOBO\wangiwangi_HOBO\20241212_WW4_WP_processed.csv")
ap = pd.read_csv(r"C:\Users\安元純\Dropbox\地球研\Wakatobi\wangiwangi_HOBO\wangiwangi_HOBO\20241212_WW4_AP_processed.csv")
wp["Date"] = pd.to_datetime(wp["Date"]); wp = wp.set_index("Date")
ap["Date"] = pd.to_datetime(ap["Date"]); ap = ap.set_index("Date")
df = wp.join(ap, lsuffix="_wp", rsuffix="_ap", how="inner")
df["head_m"] = (df["Absolute_Pressure_wp"] - df["Absolute_Pressure_ap"]) / 9.789
# Convert observation timestamps to hours-from-start
t0_obs = df.index[0]
df["t_hr_obs"] = (df.index - t0_obs).total_seconds() / 3600.0
# Center HOBO around its mean
h_obs_mean = df["head_m"].mean()
df["head_centered"] = df["head_m"] - h_obs_mean
print(f"HOBO mean = {h_obs_mean:.3f} m, range = {df['head_centered'].max()-df['head_centered'].min():.3f} m")
print(f"HOBO period: {t0_obs} .. {df.index[-1]} ({df['t_hr_obs'].iloc[-1]:.0f} hr)")

# --- Tide forcing (same series as model) ---
spec = importlib.util.spec_from_file_location("ktide",
        str(WORK.parent / "wangi_swi" / "_kuroshima_tide.py"))
ktide = importlib.util.module_from_spec(spec); spec.loader.exec_module(ktide)
kuro = np.array(ktide.KUROSHIMA_TIDE)
tide = (kuro - kuro.mean()) * 1.9
t_tide = np.arange(len(tide))

# --- Plot ---
fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)

# Top: centered head comparison
ax = axes[0]
ax.plot(t_hr_model, h_L2_centered, "b-", lw=1.6, label=f"3D SWI Model L2 (range {h_L2_centered.max()-h_L2_centered.min():.3f}m, eff 20.3%)")
ax.plot(t_hr_model, h_L1_centered, "g-", lw=1.2, alpha=0.8, label=f"3D SWI Model L1 (range {h_L1_centered.max()-h_L1_centered.min():.3f}m, eff 1.3%)")
ax.plot(df["t_hr_obs"], df["head_centered"], "r-", lw=1.6,
        label=f"HOBO WW4 obs (range {df['head_centered'].max()-df['head_centered'].min():.3f}m, eff 18%)")
ax.plot(t_tide[:138], tide[:138], "k--", lw=1.0, alpha=0.6,
        label=f"Sea level forcing (range {tide.max()-tide.min():.3f}m, 100%)")
ax.axhline(0, color="gray", ls=":", lw=0.5)
ax.set_ylabel("Head deviation from mean (m)", fontsize=11)
ax.set_title("Kantamare WW4 — 3D SWI model vs HOBO observation\n"
             "Model L2 efficiency 20.3% ≈ Obs 18% (Δ=13% relative) — 3D physics validated",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)
ax.set_xlim(0, 138)

# Bottom: comparison of 1D vs 3D tidal efficiency
ax2 = axes[1]
methods = ["1D 2-side\n(Sy=0.10)", "1D 2-side\n(Sy=0.50)", "3D L1 (cap)", "3D L2 (main)", "Obs WW4"]
effs    = [99.8, 92.3, 1.3, 20.3, 18.0]
colors  = ["#cccccc", "#999999", "#88c", "#39c", "#c33"]
bars = ax2.bar(methods, effs, color=colors, edgecolor="black", linewidth=1.0)
for bar, e in zip(bars, effs):
    ax2.text(bar.get_x() + bar.get_width()/2, e + 2, f"{e:.1f}%",
              ha="center", fontsize=10, fontweight="bold")
ax2.axhline(18.0, color="red", ls=":", lw=1.5, label="Obs target")
ax2.set_ylabel("Tidal efficiency (%)", fontsize=11)
ax2.set_ylim(0, 110)
ax2.set_title("Tidal efficiency: 1D vs 3D vs Observation", fontsize=12, fontweight="bold")
ax2.grid(alpha=0.3, axis="y")
ax2.legend()

plt.tight_layout()
out = WORK / "figs"; out.mkdir(exist_ok=True)
out_path = out / "kantamare_tidal_validation_3d_vs_1d_vs_obs.png"
plt.savefig(out_path, dpi=140, bbox_inches="tight")
print(f"\nSaved: {out_path}")
