"""Frequency-domain conduit characterization from harmonic analysis.

If we model the conduit as a 1st-order linear filter (advection + dispersion):
  EC_response(ω) = amp_ratio · water(ω) · exp(-iωτ)

The transit time τ should be consistent across constituents IF the system is
truly linear and 1st-order. Comparing per-constituent transit times reveals
whether the conduit has:
  - single-pulse (uniform τ across constituents) → simple advective conduit
  - frequency-dependent τ → diffusion + advection, or multi-pathway

Output: figs/harmonic_transit_time.png — per-constituent τ + dispersion analysis
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

res = pd.read_csv(WORK / "ec_wc_harmonics.csv")
print("=== Frequency-domain conduit characterization ===")
print(res.to_string(index=False, float_format="%.3f"))

# Filter to semi-diurnal (M2/S2/N2) and diurnal (K1/O1) separately
semi = res[res["constituent"].isin(["M2", "S2", "N2"])]
diur = res[res["constituent"].isin(["K1", "O1"])]

print(f"\n=== Semi-diurnal constituents (12-13 hr) ===")
print(f"  Mean phase lag: {semi['phase_lag_min'].mean():.1f} ± {semi['phase_lag_min'].std():.1f} min")
print(f"  Mean amp ratio: {semi['amp_ratio_uS_per_m'].mean():.0f} ± {semi['amp_ratio_uS_per_m'].std():.0f} µS/cm/m")
print(f"\n=== Diurnal constituents (24-26 hr) ===")
print(f"  Mean phase lag: {diur['phase_lag_min'].mean():.1f} ± {diur['phase_lag_min'].std():.1f} min")
print(f"  Mean amp ratio: {diur['amp_ratio_uS_per_m'].mean():.0f} ± {diur['amp_ratio_uS_per_m'].std():.0f} µS/cm/m")

# Theoretical: for pure delay τ, phase lag = ω · τ (linear in frequency)
# Plot phase lag vs frequency
res["omega_per_hr"] = 1 / res["period_hr"]
res["phase_lag_hr"] = res["phase_lag_min"] / 60

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# (a) phase lag vs frequency
ax = axes[0]
sd = res[res["constituent"].isin(["M2", "S2", "N2", "K2"])]
ax.scatter(sd["omega_per_hr"], sd["phase_lag_hr"], c="red", s=170,
           edgecolor="black", linewidth=1.3, label="Semi-diurnal", zorder=4)
for _, r in sd.iterrows():
    ax.annotate(r["constituent"], (r["omega_per_hr"], r["phase_lag_hr"]),
                xytext=(5, 5), textcoords="offset points", fontsize=10)
diur = res[res["constituent"].isin(["K1", "O1"])]
ax.scatter(diur["omega_per_hr"], diur["phase_lag_hr"], c="blue", s=170,
           edgecolor="black", linewidth=1.3, label="Diurnal", zorder=4)
for _, r in diur.iterrows():
    ax.annotate(r["constituent"], (r["omega_per_hr"], r["phase_lag_hr"]),
                xytext=(5, 5), textcoords="offset points", fontsize=10)
ax.axhline(0, color="gray", lw=0.5)
# Mean transit (semi-diurnal mean)
mean_tau_semi = semi["phase_lag_min"].mean() / 60
ax.axhline(mean_tau_semi, color="orange", ls="--", lw=1.2,
           label=f"Semi-diurnal mean τ = {mean_tau_semi*60:.0f} min")
ax.set_xlabel("Frequency (per hour)", fontsize=11)
ax.set_ylabel("Phase lag (hr)", fontsize=11)
ax.set_title("(a) Phase lag vs tidal frequency\n"
             "If pure delay → linear; if filter → curved",
             fontsize=11, fontweight="bold")
ax.legend(loc="best", fontsize=9)
ax.grid(alpha=0.3)

# (b) Effective transit time per constituent (= lag in minutes)
ax2 = axes[1]
colors = ["red" if c in ["M2","S2","N2","K2"] else "blue" for c in res["constituent"]]
bars = ax2.bar(res["constituent"], res["phase_lag_min"], color=colors,
               edgecolor="black", linewidth=1.0)
for bar, lag in zip(bars, res["phase_lag_min"]):
    y = lag + (3 if lag > 0 else -3)
    ax2.text(bar.get_x() + bar.get_width()/2, y, f"{lag:+.0f} min",
             ha="center", fontsize=10, fontweight="bold")
ax2.axhline(0, color="black", lw=0.7)
ax2.axhspan(20, 60, alpha=0.10, color="green",
            label="20-60 min conduit transit window")
ax2.set_ylabel("EC-water phase lag (min, ≈ transit time)", fontsize=11)
ax2.set_title("(b) Per-constituent transit-time signature\n"
              "Semi-diurnal: M2/S2/N2 show +4 to +75 min;\n"
              "Diurnal: K1/O1 in quasi-equilibrium",
              fontsize=11, fontweight="bold")
ax2.legend(loc="upper right", fontsize=9)
ax2.grid(alpha=0.3, axis="y")

fig.suptitle("Wangi-Wangi conduit transit-time signature from EC harmonic decomposition\n"
             "Semi-diurnal lag ≈ advective transit; diurnal lag ≈ 0 = forced equilibrium",
             fontsize=13, fontweight="bold", y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.94])
out = FIGDIR / "harmonic_transit_time.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out}")
