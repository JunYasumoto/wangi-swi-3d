"""Paper 2 Fig 7 v2 — 8-panel multi-tracer validation.

Extends original Fig 7 (6 panels) to include long-term EC validation:
 (a) Steady L2 head scatter
 (b) Tidal efficiency bar
 (c) Island SGD compare
 (d) SF6 ages scatter (karst conduit)
 (e) δ18O-δ2H GMWL
 (f) Cl- mixing (10-sample snapshot)
 (g) NEW: 5-month EC time series with seasonal trend
 (h) NEW: EC vs WP cross-correlation (conduit transit time)

Output: figs/paper2_fig7_v2_8panels.png + .pdf
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.dates import DateFormatter, MonthLocator
from scipy.signal import correlate

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

heads = pd.read_csv(WORK / "phase3a_heads_3c_baseline_L2corrected.csv")
sf6 = pd.read_csv(WORK / "sf6_age_comparison.csv")
chem = pd.read_csv(WORK / "ww_isotope_chem.csv")
ec_wp = pd.read_csv(WORK / "ww4_combined_EC_WP.csv")
ec_wp["datetime"] = pd.to_datetime(ec_wp["datetime"])

fig = plt.figure(figsize=(20, 12))
gs = GridSpec(2, 4, figure=fig, hspace=0.42, wspace=0.32)

# --- (a) Heads scatter ---
ax = fig.add_subplot(gs[0, 0])
main = heads[~heads["perched"]]
ax.scatter(main["obs"], main["sim_used"], c="#2ca02c", s=130,
           edgecolor="black", linewidth=1.2, zorder=4)
for _, r in main.iterrows():
    ax.annotate(r["id"], (r["obs"], r["sim_used"]), xytext=(4, 4),
                textcoords="offset points", fontsize=7)
lo = min(main["obs"].min(), main["sim_used"].min()) - 0.5
hi = max(main["obs"].max(), main["sim_used"].max()) + 0.5
ax.plot([lo, hi], [lo, hi], "k--", lw=1, alpha=0.7)
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
rmse = np.sqrt((main["resid"]**2).mean())
bias = main["resid"].mean()
ax.set_xlabel("Obs head (m, MSL)", fontsize=9)
ax.set_ylabel("Sim L2 head (m)", fontsize=9)
ax.set_title(f"(a) Steady heads — n=17\nRMSE {rmse:.2f}m, bias {bias:+.2f}m\n"
             f"(PEST baseline 2.53m)\n** NB: WW4 target 4.16m needs correction → 2.38m **",
             fontsize=9, fontweight="bold")
ax.grid(alpha=0.3)

# --- (b) Tidal efficiency bar ---
ax = fig.add_subplot(gs[0, 1])
methods = ["1D 2-side\nSy=0.10", "1D 2-side\nSy=0.50", "3D L1\n(cap)", "3D L2\n(main)", "Obs WW4"]
effs    = [99.8, 92.3, 1.3, 20.3, 18.0]
colors  = ["#cccccc", "#999999", "#88c", "#39c", "#c33"]
bars = ax.bar(methods, effs, color=colors, edgecolor="black", linewidth=1.0)
for bar, e in zip(bars, effs):
    ax.text(bar.get_x() + bar.get_width()/2, e + 2, f"{e:.1f}%",
            ha="center", fontsize=9, fontweight="bold")
ax.axhline(18.0, color="red", ls=":", lw=1.5, label="Obs target")
ax.set_ylabel("Tidal efficiency (%)", fontsize=9)
ax.set_ylim(0, 110)
ax.set_title("(b) Tidal validation at WW4\n3D L2 20.3% matches obs 18%",
             fontsize=9, fontweight="bold")
ax.grid(alpha=0.3, axis="y")
ax.legend(loc="upper right", fontsize=7)
plt.setp(ax.get_xticklabels(), fontsize=7)

# --- (c) Island SGD ---
ax = fig.add_subplot(gs[0, 2])
sgd_labels = ["Mass\nbalance", "JpGU 3D", "3D SWI NET\n(this)", "1D 12-trans"]
sgd_vals = [2.55e5, 3.06e5, 3.32e5, 7.34e5]
sgd_colors = ["#7a7", "#5a5", "#2ca02c", "#d62728"]
bars = ax.bar(sgd_labels, sgd_vals, color=sgd_colors, edgecolor="black", linewidth=1.0)
for bar, v in zip(bars, sgd_vals):
    ax.text(bar.get_x() + bar.get_width()/2, v * 1.05, f"{v:.1e}",
            ha="center", fontsize=8, fontweight="bold")
ax.set_ylabel("Steady SGD (m³/d)", fontsize=9)
ax.set_title("(c) Island SGD\n3D matches JpGU 3D (×1.08)",
             fontsize=9, fontweight="bold")
ax.grid(alpha=0.3, axis="y")
plt.setp(ax.get_xticklabels(), fontsize=7)
ax.set_yscale("log"); ax.set_ylim(1e5, 1e6)

# --- (d) SF6 ages ---
ax = fig.add_subplot(gs[0, 3])
ok = sf6[sf6["flag"] == "ok"]
mod = sf6[sf6["flag"] == "<1 yr"]
ax.scatter(ok["obs_age_yr"], ok["sim_age_yr"], s=120, c="#2ca02c",
           edgecolor="black", linewidth=1.2, zorder=4, label=f"Valid (n={len(ok)})")
ax.scatter([0.5]*len(mod), mod["sim_age_yr"], s=120, c="#1f77b4",
           edgecolor="black", linewidth=1.2, zorder=4, marker="s",
           label=f"Modern (n={len(mod)})")
for _, r in sf6.iterrows():
    if pd.notna(r["sim_age_yr"]):
        xp = r["obs_age_yr"] if r["obs_age_yr"] > 0 else 0.5
        ax.annotate(r["id"].upper(), (xp, r["sim_age_yr"]),
                    xytext=(3, 3), textcoords="offset points", fontsize=6)
xx = np.logspace(-0.5, 4.5, 100)
ax.plot(xx, xx, "k--", lw=1)
ax.plot(xx, xx*100, "r-", lw=0.5, alpha=0.5)
ax.plot(xx, xx*1000, "r-", lw=0.5, alpha=0.5)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(0.3, 1e3); ax.set_ylim(1, 1e5)
ax.set_xlabel("Obs SF6 age (yr)", fontsize=9)
ax.set_ylabel("Sim MODPATH age (yr)", fontsize=9)
ax.set_title(f"(d) SF6 transit times\nGeomean ×261 → karst conduit\n(n_eff ≈ 4e-4)",
             fontsize=9, fontweight="bold")
ax.legend(loc="upper left", fontsize=7)
ax.grid(alpha=0.3, which="both")

# --- (e) δ18O-δ2H ---
ax = fig.add_subplot(gs[1, 0])
PERCHED = {"WW10"}
nperc = chem[~chem["well"].isin(PERCHED)]
x_iso = np.linspace(-8, 1, 200)
ax.plot(x_iso, 8*x_iso + 10, "k-", lw=1.6, label="GMWL")
ax.scatter(nperc["d18O"], nperc["d2H"], s=110, c="#2ca02c",
           edgecolor="black", linewidth=1.2, zorder=4)
for _, r in nperc.iterrows():
    ax.annotate(r["well"], (r["d18O"], r["d2H"]), xytext=(4, 3),
                textcoords="offset points", fontsize=7)
slope, intercept = np.polyfit(nperc["d18O"], nperc["d2H"], 1)
ax.plot(x_iso, slope*x_iso + intercept, "r--", lw=1.4,
        label=f"Wangi: δ²H = {slope:.2f}·δ¹⁸O + {intercept:.2f}")
ax.set_xlim(-8, 0); ax.set_ylim(-50, 5)
ax.set_xlabel("δ¹⁸O (‰)", fontsize=9)
ax.set_ylabel("δ²H (‰)", fontsize=9)
ax.set_title(f"(e) Stable isotopes → meteoric\nslope = {slope:.2f}",
             fontsize=9, fontweight="bold")
ax.legend(loc="upper left", fontsize=7)
ax.grid(alpha=0.3)

# --- (f) Cl- mixing ---
ax = fig.add_subplot(gs[1, 1])
SEAWATER_CL = 19000.0; SEAWATER_d18O = 0.0
RAIN_CL = 3.0; RAIN_d18O = -5.5
f_sw = np.linspace(0, 1, 200)
mix_Cl = f_sw * SEAWATER_CL + (1 - f_sw) * RAIN_CL
mix_d18O = f_sw * SEAWATER_d18O + (1 - f_sw) * RAIN_d18O
ax.plot(mix_Cl, mix_d18O, "b--", lw=1.4)
ax.scatter(nperc["Cl"], nperc["d18O"], s=110, c="#2ca02c",
           edgecolor="black", linewidth=1.2, zorder=4)
for _, r in nperc.iterrows():
    ax.annotate(r["well"], (r["Cl"], r["d18O"]),
                xytext=(4, 3), textcoords="offset points", fontsize=7)
for f in [0.01, 0.05, 0.5]:
    cl = f * SEAWATER_CL + (1-f) * RAIN_CL
    d18 = f * SEAWATER_d18O + (1-f) * RAIN_d18O
    ax.scatter(cl, d18, marker="s", c="blue", s=25, zorder=5)
    ax.annotate(f"{f*100:g}%", (cl, d18), xytext=(2, -8),
                textcoords="offset points", fontsize=6, color="blue")
ax.scatter(SEAWATER_CL, SEAWATER_d18O, marker="*", s=180, c="cyan",
           edgecolor="black", linewidth=1.2)
ax.set_xscale("log")
ax.set_xlim(1, 30000); ax.set_ylim(-8, 1)
ax.set_xlabel("Cl⁻ (mg/L)", fontsize=9)
ax.set_ylabel("δ¹⁸O (‰)", fontsize=9)
ax.set_title("(f) Cl-δ¹⁸O mixing — 10 samples\nWW5 11% sw, conduit-driven",
             fontsize=9, fontweight="bold")
ax.grid(alpha=0.3, which="both")

# --- (g) NEW: EC monthly time series ---
ax = fig.add_subplot(gs[1, 2])
CLEAN_START = pd.Timestamp("2025-01-16")
clean = ec_wp[ec_wp["datetime"] >= CLEAN_START].copy()
clean["date"] = clean["datetime"].dt.date
clean["month"] = clean["datetime"].dt.to_period("M").astype(str)
monthly = clean.groupby("month").agg(
    EC_mean=("EC_uScm", "mean"),
    EC_std=("EC_uScm", "std"),
    GW_mean=("GW_elev_MSL", "mean"),
).reset_index()

axt = ax.twinx()
x_m = np.arange(len(monthly))
b1 = ax.bar(x_m - 0.2, monthly["EC_mean"], 0.4, color="darkred",
            label="EC monthly mean", alpha=0.85)
ax.errorbar(x_m - 0.2, monthly["EC_mean"], yerr=monthly["EC_std"],
            fmt="none", color="black", capsize=3, lw=0.7)
b2 = axt.bar(x_m + 0.2, monthly["GW_mean"], 0.4, color="darkblue",
             label="GW elev mean", alpha=0.85)
ax.set_xticks(x_m); ax.set_xticklabels(monthly["month"], rotation=45, fontsize=7)
ax.set_ylabel("EC (µS/cm)", color="darkred", fontsize=9)
axt.set_ylabel("GW elev (m MSL)", color="darkblue", fontsize=9)
ax.tick_params(axis="y", labelcolor="darkred", labelsize=8)
axt.tick_params(axis="y", labelcolor="darkblue", labelsize=8)
from scipy.stats import pearsonr
rm, pm = pearsonr(monthly["GW_mean"], monthly["EC_mean"])
ax.set_title(f"(g) NEW: 5-mo monthly EC vs GW elev\n"
             f"Anti-corr r = {rm:.2f} → lens freshening (Jan→May)",
             fontsize=9, fontweight="bold")
ax.legend([b1, b2], ["EC ± std", "GW elev"], loc="upper right", fontsize=7)
ax.grid(alpha=0.3, axis="y")

# --- (h) NEW: EC-WP lagged cross-correlation ---
ax = fig.add_subplot(gs[1, 3])
wc_n = (clean["water_col_m"].values - clean["water_col_m"].mean()) / clean["water_col_m"].std()
ec_n = (clean["EC_uScm"].values - clean["EC_uScm"].mean()) / clean["EC_uScm"].std()
ccor = correlate(ec_n, wc_n, mode="full") / len(wc_n)
mid = len(ccor) // 2
HALF = 72  # ±36 hr
sl = ccor[mid-HALF:mid+HALF+1]
lag_30min = np.arange(-HALF, HALF+1)
peak_idx = np.argmax(np.abs(sl))
peak_lag = lag_30min[peak_idx]
peak_val = sl[peak_idx]
ax.plot(lag_30min*30/60, sl, "b-", lw=1.3)
ax.axvline(0, color="gray", lw=0.5)
ax.axvline(peak_lag*30/60, color="red", ls="--",
           label=f"Peak r={peak_val:+.2f}\nlag = {peak_lag*30:+d} min\n(EC lags water)")
ax.set_xlabel("Lag (hours)", fontsize=9)
ax.set_ylabel("Cross-correlation", fontsize=9)
ax.set_title("(h) NEW: EC vs water lag-correlation\nClean window (122 d)\n"
             "→ Conduit transit time ≈ 30 min",
             fontsize=9, fontweight="bold")
ax.legend(fontsize=7, loc="upper right")
ax.grid(alpha=0.3)

# Master title
fig.suptitle("Multi-tracer validation of 3D SWI Wangi-Wangi model — 8 independent lines\n"
             "(a-c) Bulk hydraulics ✓  |  (d-f) Geochemistry & karst conduit  |  (g-h) NEW: 5-mo EC dynamics",
             fontsize=14, fontweight="bold", y=0.99)

plt.tight_layout(rect=[0, 0, 1, 0.96])
out_png = FIGDIR / "paper2_fig7_v2_8panels.png"
plt.savefig(out_png, dpi=170, bbox_inches="tight")
out_pdf = FIGDIR / "paper2_fig7_v2_8panels.pdf"
plt.savefig(out_pdf, bbox_inches="tight")
plt.close()
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
