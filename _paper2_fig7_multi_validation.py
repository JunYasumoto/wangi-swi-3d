"""Paper 2 Fig 7 — Multi-tracer validation panel.

Six independent validation lines integrated into a single figure showing
the consistent "bulk hydraulics OK / tracer transport karst-limited" story.

Panels:
 (a) L2 head residual map (NW-S/SE bimodal pattern)
 (b) Tidal validation at Kantamare (M2 amplitude obs vs sim)
 (c) Island SGD ratio (3D NET vs JpGU vs 1D over-estimate)
 (d) SF6 age sim vs obs (261× over → karst conduits)
 (e) δ18O-δ2H + GMWL (meteoric origin)
 (f) Cl- mixing (2-11% seawater fraction, conduit-driven)

Output: figs/paper2_fig7_multi_validation.png + pdf
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"

# Load all observation-comparison datasets
heads = pd.read_csv(WORK / "phase3a_heads_3c_baseline_L2corrected.csv")
sf6 = pd.read_csv(WORK / "sf6_age_comparison.csv")
chem = pd.read_csv(WORK / "ww_isotope_chem.csv")

# === Figure layout ===
fig = plt.figure(figsize=(18, 12))
gs = GridSpec(2, 3, figure=fig, hspace=0.40, wspace=0.30)

# --- (a) Heads scatter ---
ax_a = fig.add_subplot(gs[0, 0])
main = heads[~heads["perched"]]
ax_a.scatter(main["obs"], main["sim_used"], c="#2ca02c", s=140,
              edgecolor="black", linewidth=1.2, zorder=4)
for _, r in main.iterrows():
    ax_a.annotate(r["id"], (r["obs"], r["sim_used"]), xytext=(4, 4),
                   textcoords="offset points", fontsize=7)
lo = min(main["obs"].min(), main["sim_used"].min()) - 0.5
hi = max(main["obs"].max(), main["sim_used"].max()) + 0.5
ax_a.plot([lo, hi], [lo, hi], "k--", lw=1, alpha=0.7)
ax_a.set_xlim(lo, hi); ax_a.set_ylim(lo, hi)
ax_a.set_aspect("equal")
rmse = np.sqrt((main["resid"]**2).mean())
bias = main["resid"].mean()
ax_a.set_xlabel("Observed head (m, MSL)", fontsize=10)
ax_a.set_ylabel("Simulated L2 head (m)", fontsize=10)
ax_a.set_title(f"(a) Steady heads — n=17\nRMSE = {rmse:.2f} m, bias = {bias:+.2f} m\n"
               f"(PEST baseline RMSE 2.53 m)",
               fontsize=10, fontweight="bold")
ax_a.grid(alpha=0.3)

# --- (b) Tidal efficiency bar ---
ax_b = fig.add_subplot(gs[0, 1])
methods = ["1D 2-side\nSy=0.10", "1D 2-side\nSy=0.50", "3D L1\n(cap)", "3D L2\n(main)", "Obs WW4"]
effs    = [99.8, 92.3, 1.3, 20.3, 18.0]
colors  = ["#cccccc", "#999999", "#88c", "#39c", "#c33"]
bars = ax_b.bar(methods, effs, color=colors, edgecolor="black", linewidth=1.0)
for bar, e in zip(bars, effs):
    ax_b.text(bar.get_x() + bar.get_width()/2, e + 2, f"{e:.1f}%",
              ha="center", fontsize=10, fontweight="bold")
ax_b.axhline(18.0, color="red", ls=":", lw=1.5, label="Obs target")
ax_b.set_ylabel("Tidal efficiency (%)", fontsize=10)
ax_b.set_ylim(0, 110)
ax_b.set_title("(b) Tidal validation at Kantamare\n"
               "3D L2 = 20.3% matches obs 18% (Δrel 13%)",
               fontsize=10, fontweight="bold")
ax_b.grid(alpha=0.3, axis="y")
ax_b.legend(loc="upper right", fontsize=8)
plt.setp(ax_b.get_xticklabels(), fontsize=8)

# --- (c) Island SGD compare ---
ax_c = fig.add_subplot(gs[0, 2])
sgd_labels = ["Mass\nbalance\nRCH×area", "JpGU 3D\nfreshwater", "3D SWI NET\n(this study)", "1D 12-transect\n(over-estimate)"]
sgd_vals = [2.55e5, 3.06e5, 3.32e5, 7.34e5]
sgd_colors = ["#7a7", "#5a5", "#2ca02c", "#d62728"]
bars = ax_c.bar(sgd_labels, sgd_vals, color=sgd_colors, edgecolor="black", linewidth=1.0)
for bar, v in zip(bars, sgd_vals):
    ax_c.text(bar.get_x() + bar.get_width()/2, v * 1.05, f"{v:.1e}",
              ha="center", fontsize=9, fontweight="bold")
ax_c.set_ylabel("Steady SGD (m³/d)", fontsize=10)
ax_c.set_title("(c) Island-scale SGD\n3D NET = 3.32e5 matches JpGU 3D (×1.08)",
               fontsize=10, fontweight="bold")
ax_c.grid(alpha=0.3, axis="y")
plt.setp(ax_c.get_xticklabels(), fontsize=7)
ax_c.set_yscale("log")
ax_c.set_ylim(1e5, 1e6)

# --- (d) SF6 ages scatter ---
ax_d = fig.add_subplot(gs[1, 0])
ok = sf6[sf6["flag"] == "ok"]
mod = sf6[sf6["flag"] == "<1 yr"]
ax_d.scatter(ok["obs_age_yr"], ok["sim_age_yr"], s=140, c="#2ca02c",
              edgecolor="black", linewidth=1.2, zorder=4, label=f"Valid (n={len(ok)})")
ax_d.scatter([0.5]*len(mod), mod["sim_age_yr"], s=140, c="#1f77b4",
              edgecolor="black", linewidth=1.2, zorder=4, marker="s",
              label=f"Modern obs (n={len(mod)})")
for _, r in sf6.iterrows():
    if pd.notna(r["sim_age_yr"]):
        xp = r["obs_age_yr"] if r["obs_age_yr"] > 0 else 0.5
        ax_d.annotate(r["id"].upper(), (xp, r["sim_age_yr"]),
                       xytext=(4, 4), textcoords="offset points", fontsize=7)
xx = np.logspace(-0.5, 4.5, 100)
ax_d.plot(xx, xx, "k--", lw=1)
ax_d.plot(xx, xx*100, "r-", lw=0.6, alpha=0.5, label="sim = 100× obs")
ax_d.plot(xx, xx*1000, "r-", lw=0.6, alpha=0.5)
ax_d.set_xscale("log"); ax_d.set_yscale("log")
ax_d.set_xlim(0.3, 1e3); ax_d.set_ylim(1, 1e5)
ax_d.set_xlabel("Observed SF6 age (yr)", fontsize=10)
ax_d.set_ylabel("Simulated MODPATH age (yr)", fontsize=10)
ax_d.set_title(f"(d) SF6 transit times\nGeomean over ×261 → karst conduits\n(n_eff ≈ 4×10⁻⁴ matches literature)",
               fontsize=10, fontweight="bold")
ax_d.legend(loc="upper left", fontsize=8)
ax_d.grid(alpha=0.3, which="both")

# --- (e) δ18O-δ2H ---
ax_e = fig.add_subplot(gs[1, 1])
PERCHED_CHEM = {"WW10"}
nperc = chem[~chem["well"].isin(PERCHED_CHEM)]
x_iso = np.linspace(-8, 1, 200)
ax_e.plot(x_iso, 8*x_iso + 10, "k-", lw=1.8, label="GMWL: δ²H = 8·δ¹⁸O + 10")
ax_e.scatter(nperc["d18O"], nperc["d2H"], s=140, c="#2ca02c",
              edgecolor="black", linewidth=1.2, zorder=4, label=f"Wangi GW (n={len(nperc)})")
for _, r in nperc.iterrows():
    ax_e.annotate(r["well"], (r["d18O"], r["d2H"]), xytext=(5, 4),
                   textcoords="offset points", fontsize=7)
slope, intercept = np.polyfit(nperc["d18O"], nperc["d2H"], 1)
ax_e.plot(x_iso, slope*x_iso + intercept, "r--", lw=1.5,
           label=f"Wangi: δ²H = {slope:.2f}·δ¹⁸O + {intercept:.2f}")
ax_e.set_xlim(-8, 0); ax_e.set_ylim(-50, 5)
ax_e.set_xlabel("δ¹⁸O (‰ VSMOW)", fontsize=10)
ax_e.set_ylabel("δ²H (‰ VSMOW)", fontsize=10)
ax_e.set_title(f"(e) Stable isotopes → meteoric origin\n"
               f"Slope = {slope:.2f} ≈ GMWL 8 (mild evap)",
               fontsize=10, fontweight="bold")
ax_e.legend(loc="upper left", fontsize=8)
ax_e.grid(alpha=0.3)

# --- (f) Cl mixing ---
ax_f = fig.add_subplot(gs[1, 2])
SEAWATER_CL = 19000.0; SEAWATER_d18O = 0.0
RAIN_CL = 3.0; RAIN_d18O = -5.5
f_sw = np.linspace(0, 1, 200)
mix_Cl = f_sw * SEAWATER_CL + (1 - f_sw) * RAIN_CL
mix_d18O = f_sw * SEAWATER_d18O + (1 - f_sw) * RAIN_d18O
ax_f.plot(mix_Cl, mix_d18O, "b--", lw=1.5, label="SW-rain mixing")
ax_f.scatter(nperc["Cl"], nperc["d18O"], s=140, c="#2ca02c",
              edgecolor="black", linewidth=1.2, zorder=4)
for _, r in nperc.iterrows():
    ax_f.annotate(r["well"], (r["Cl"], r["d18O"]),
                   xytext=(5, 4), textcoords="offset points", fontsize=7)
for f in [0.01, 0.05, 0.10, 0.5]:
    cl = f * SEAWATER_CL + (1-f) * RAIN_CL
    d18 = f * SEAWATER_d18O + (1-f) * RAIN_d18O
    ax_f.scatter(cl, d18, marker="s", c="blue", s=30, zorder=5)
    ax_f.annotate(f"{f*100:g}%", (cl, d18), xytext=(3, -10),
                   textcoords="offset points", fontsize=7, color="blue")
ax_f.scatter(SEAWATER_CL, SEAWATER_d18O, marker="*", s=200, c="cyan",
              edgecolor="black", linewidth=1.2, label="Seawater")
ax_f.set_xscale("log")
ax_f.set_xlim(1, 30000); ax_f.set_ylim(-8, 1)
ax_f.set_xlabel("Cl⁻ (mg/L)", fontsize=10)
ax_f.set_ylabel("δ¹⁸O (‰ VSMOW)", fontsize=10)
ax_f.set_title("(f) Cl-δ¹⁸O seawater fraction\n"
               "WW5 11%, WW6/8 2-3% — conduit-driven mixing",
               fontsize=10, fontweight="bold")
ax_f.legend(loc="upper left", fontsize=8)
ax_f.grid(alpha=0.3, which="both")

# === Master title ===
fig.suptitle("Multi-tracer validation of the 3D SWI Wangi-Wangi model\n"
             "(a-c) Bulk hydraulics OK   |   (d-f) Karst conduit flow constrains tracer transport",
             fontsize=14, fontweight="bold", y=0.99)

plt.tight_layout(rect=[0, 0, 1, 0.96])
out_png = FIGDIR / "paper2_fig7_multi_validation.png"
plt.savefig(out_png, dpi=180, bbox_inches="tight")
out_pdf = FIGDIR / "paper2_fig7_multi_validation.pdf"
plt.savefig(out_pdf, bbox_inches="tight")
plt.close()
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
