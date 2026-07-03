"""Scenario comparison figures for the 3D SWI PEST calibration (C/A4/B/D).

Reads diag_{base,A4,B,D}.csv (per-scenario optimal forward diagnostics) and the
recorded phi-by-group / parameter values, and writes multi-panel figures to figs/.
"""
import numpy as np, pandas as pd, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

W = pathlib.Path(__file__).resolve().parent
FIG = W / "figs"; FIG.mkdir(exist_ok=True)

# --- recorded results (from pest.iobj / pest.par of each NOPTMAX=3 run) ----------
SC = ["base", "A4", "B", "D"]
LABEL = {"base": "base\n(K2=1)", "A4": "A: 3-zone K2", "B": "B: +global RCH",
         "D": "D: +CENT RCH"}
PHI = {  # total, obs_cent, obs_nw, obs_sse, obs_other
    "base": (89.96, 42.52, 6.79, 38.71, 1.94),
    "A4":   (80.46, 35.91, 6.86, 35.76, 1.93),
    "B":    (77.86, 32.48, 6.95, 36.50, 1.93),
    "D":    (70.78, 25.51, 7.09, 36.26, 1.93),
}
PAR = {  # k2_nw, k2_cent, k2_sse, rch_mult, rch_cent
    "base": (1.0, 1.0, 1.0, 1.0, 1.0),
    "A4":   (0.3856, 0.300, 0.5046, 1.0, 1.0),
    "B":    (0.3788, 0.300, 0.8635, 1.875, 1.0),
    "D":    (0.3471, 0.300, 2.000, 3.000, 3.000),
}
PNAME = ["k2_nw", "k2_cent", "k2_sse", "rch_mult", "rch_cent"]
PBOUND = {"k2_nw": (0.3, 2.0), "k2_cent": (0.3, 2.0), "k2_sse": (0.3, 2.0),
          "rch_mult": (0.5, 3.0), "rch_cent": (0.5, 3.0)}
ZONE = {**{w: "NW" for w in ["ww02", "ww03", "ww18", "ww19", "ww20"]},
        **{w: "CENT" for w in ["ww04", "ww11", "ww12"]},
        **{w: "SSE" for w in ["ww05", "ww06", "ww07", "ww08", "ww09",
                               "ww13", "ww15", "ww17"]}}
ZCOL = {"NW": "#1f77b4", "CENT": "#d62728", "SSE": "#2ca02c"}

diag = {}
for s in SC:
    d = pd.read_csv(W / f"diag_{s}.csv")
    d = d[d["use_for_calibration"] == True].copy()
    d["zone"] = d["id"].map(ZONE)
    d = d.dropna(subset=["zone"])
    d["res"] = d["obs_used"] - d["sim_L2"]
    diag[s] = d

# =================================================================== FIGURE 1
fig, ax = plt.subplots(2, 2, figsize=(13, 10))

# (a) phi progression by group (stacked)
groups = ["obs_cent", "obs_sse", "obs_nw", "obs_other"]
gcol = {"obs_cent": "#d62728", "obs_sse": "#2ca02c", "obs_nw": "#1f77b4",
        "obs_other": "#999999"}
x = np.arange(len(SC))
bottom = np.zeros(len(SC))
vals = {g: [PHI[s][i + 1] for s in SC] for i, g in enumerate(groups)}
for g in groups:
    ax[0, 0].bar(x, vals[g], bottom=bottom, label=g, color=gcol[g], width=0.6)
    bottom += np.array(vals[g])
for xi, s in enumerate(SC):
    ax[0, 0].text(xi, PHI[s][0] + 1.2, f"{PHI[s][0]:.1f}", ha="center",
                  fontweight="bold")
ax[0, 0].set_xticks(x); ax[0, 0].set_xticklabels([LABEL[s] for s in SC])
ax[0, 0].set_ylabel("Φ (sum of weighted squared residuals)")
ax[0, 0].set_title("(a) Objective function by observation group")
ax[0, 0].legend(fontsize=8, loc="upper right")
ax[0, 0].set_ylim(0, 100)

# (b) parameter values with bounds (pinning)
for j, p in enumerate(PNAME):
    lo, hi = PBOUND[p]
    ax[0, 1].axhspan(lo, hi, xmin=(j) / len(PNAME) + 0.01,
                     xmax=(j + 1) / len(PNAME) - 0.01, color="#eeeeee", zorder=0)
mk = {"base": "o", "A4": "s", "B": "^", "D": "D"}
for s in SC:
    ys = PAR[s]
    ax[0, 1].plot(range(len(PNAME)), ys, mk[s] + "-", label=LABEL[s].replace("\n", " "),
                  ms=9, alpha=0.85)
for j, p in enumerate(PNAME):
    lo, hi = PBOUND[p]
    ax[0, 1].plot([j - 0.25, j + 0.25], [lo, lo], "k--", lw=0.8)
    ax[0, 1].plot([j - 0.25, j + 0.25], [hi, hi], "k--", lw=0.8)
ax[0, 1].set_xticks(range(len(PNAME))); ax[0, 1].set_xticklabels(PNAME, rotation=20)
ax[0, 1].set_ylabel("multiplier (log scale)"); ax[0, 1].set_yscale("log")
ax[0, 1].set_title("(b) Parameter values vs bounds (dashed = bounds)")
ax[0, 1].legend(fontsize=8)

# (c) obs vs sim: base vs D
for s, mk2, cl in [("base", "o", "#888888"), ("D", "D", "#d62728")]:
    d = diag[s]
    ax[1, 0].scatter(d["obs_used"], d["sim_L2"], marker=mk2, s=55,
                     edgecolor="k", linewidth=0.4, alpha=0.8,
                     label=LABEL[s].replace("\n", " "), c=cl)
lim = [-1, 9]
ax[1, 0].plot(lim, lim, "k-", lw=1)
ax[1, 0].set_xlim(lim); ax[1, 0].set_ylim(lim)
ax[1, 0].set_xlabel("observed head (m)"); ax[1, 0].set_ylabel("simulated head (m)")
ax[1, 0].set_title("(c) Observed vs simulated (base → D)")
ax[1, 0].legend(fontsize=9)
for _, r in diag["D"].iterrows():
    if r["zone"] == "CENT":
        ax[1, 0].annotate(r["id"], (r["obs_used"], r["sim_L2"]), fontsize=7,
                          xytext=(3, 3), textcoords="offset points")

# (d) zonal RMSE by scenario
zones = ["NW", "CENT", "SSE"]
xz = np.arange(len(zones)); wbar = 0.2
for k, s in enumerate(SC):
    rms = [np.sqrt((diag[s][diag[s].zone == z].res ** 2).mean()) for z in zones]
    ax[1, 1].bar(xz + (k - 1.5) * wbar, rms, wbar, label=LABEL[s].replace("\n", " "))
ax[1, 1].set_xticks(xz); ax[1, 1].set_xticklabels(zones)
ax[1, 1].set_ylabel("RMSE (m)"); ax[1, 1].set_title("(d) Zonal head RMSE by scenario")
ax[1, 1].legend(fontsize=8)

fig.suptitle("3D SWI PEST calibration — scenario comparison (C inactive: Φ unchanged)",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(FIG / "scenario_comparison_CABD.png", dpi=150)
print("saved figs/scenario_comparison_CABD.png")

# =================================================================== FIGURE 2
# CENT local structural problem: ww04/11/12 within ~200 m, heads differ ~5 m
fig2, ax2 = plt.subplots(1, 2, figsize=(13, 5.5))
cent = diag["D"][diag["D"].zone == "CENT"].copy()
# (a) map of CENT wells, obs vs sim(D)
x0, y0 = cent["utm_x"].mean(), cent["utm_y"].mean()
cent["dx"] = cent["utm_x"] - x0; cent["dy"] = cent["utm_y"] - y0
sc = ax2[0].scatter(cent["dx"], cent["dy"], c=cent["obs_used"], s=420,
                    cmap="viridis", edgecolor="k", vmin=2, vmax=8, zorder=3)
for _, r in cent.iterrows():
    ax2[0].annotate(f"{r['id']}\nobs {r['obs_used']:.1f}\nsim {r['sim_L2']:.1f}",
                    (r["dx"], r["dy"]), fontsize=9, ha="center", va="center",
                    xytext=(0, -45), textcoords="offset points")
plt.colorbar(sc, ax=ax2[0], label="observed head (m)")
ax2[0].set_xlabel("Δx (m)"); ax2[0].set_ylabel("Δy (m)")
ax2[0].set_title("(a) CENT wells: observed head\n(~200 m apart, ~5 m head range)")
ax2[0].set_aspect("equal"); ax2[0].grid(alpha=0.3)

# (b) per-well obs vs sim across scenarios for CENT wells
cw = ["ww04", "ww11", "ww12"]
xw = np.arange(len(cw))
for k, s in enumerate(SC):
    d = diag[s].set_index("id")
    sims = [d.loc[w, "sim_L2"] for w in cw]
    ax2[1].plot(xw, sims, mk[s] + "-", ms=9, label=LABEL[s].replace("\n", " "))
obs = [diag["D"].set_index("id").loc[w, "obs_used"] for w in cw]
ax2[1].plot(xw, obs, "k*", ms=18, label="observed", zorder=5)
ax2[1].set_xticks(xw); ax2[1].set_xticklabels(cw)
ax2[1].set_ylabel("head (m)")
ax2[1].set_title("(b) CENT wells: sim converges toward obs\nbut ww04 overshoots when lifting ww11/ww12")
ax2[1].legend(fontsize=8)
fig2.suptitle("Structural limit of the CENT zone — a continuous-aquifer model cannot "
              "match a ~5 m head difference over ~200 m", fontsize=12, fontweight="bold")
fig2.tight_layout(rect=[0, 0, 1, 0.95])
fig2.savefig(FIG / "scenario_CENT_structural.png", dpi=150)
print("saved figs/scenario_CENT_structural.png")
