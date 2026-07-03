"""Publication figures for the A-clean (preferred calibration) results.

Fig 1  well classification map  : regional / perched / boundary-controlled
Fig 2  A-clean observed vs simulated (assimilated wells)
Fig 3  scenario comparison table
(Fig 4 = figs/Aclean_FOSM.png, already produced)
"""
import numpy as np, pandas as pd, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

W = pathlib.Path(__file__).resolve().parent
FIG = W / "figs"; FIG.mkdir(exist_ok=True)

# ---- classification --------------------------------------------------------
PERCHED   = ["ww01", "ww14", "ww16", "ww10", "ww11", "ww12", "ww05", "ww08"]
SUSPECT_KEPT = ["ww05", "ww08"]            # perched-signature but kept in A-clean
EXCLUDED_NEW = ["ww10", "ww11", "ww12"]    # excluded this session
EXCLUDED_OLD = ["ww01", "ww14", "ww16"]    # highland, long excluded
BOUNDARY  = ["ww06", "ww17"]               # coastal, K-insensitive (GHB-controlled)
REGIONAL  = ["ww02", "ww03", "ww04", "ww07", "ww09", "ww13", "ww15",
             "ww18", "ww19", "ww20"]

def klass(w):
    if w in BOUNDARY: return "boundary"
    if w in PERCHED: return "perched"
    return "regional"

COL = {"regional": "#1f77b4", "perched": "#d62728", "boundary": "#ff7f0e"}

d = pd.read_csv(W / "diag_Aclean.csv")
d["k"] = d["id"].map(klass)
d["obs"] = d["obs_truth_ppp"]

# ---- coastline (idomain edge) ---------------------------------------------
idom = np.squeeze(np.load(W / "idomain.npy")).astype(int)
pad = np.pad(idom, 1, mode="constant", constant_values=0)
is_coast = (idom == 1) & ((pad[0:-2, 1:-1] == 0) | (pad[2:, 1:-1] == 0)
                          | (pad[1:-1, 0:-2] == 0) | (pad[1:-1, 2:] == 0))
XUL, YUL, DEL = 552770.0, 9424415.7031, 30.0
cr, cc = np.where(is_coast)
coast_x = XUL + (cc + 0.5) * DEL
coast_y = YUL - (cr + 0.5) * DEL

# =============================================================== FIG 1: map
fig, ax = plt.subplots(figsize=(9, 9.5))
ax.scatter(coast_x, coast_y, s=1, c="#cccccc", marker=".", zorder=0,
           label="_coast")
for k in ["regional", "perched", "boundary"]:
    sub = d[d.k == k]
    # excluded perched hollow, kept solid
    for _, r in sub.iterrows():
        kept = not (r["id"] in EXCLUDED_NEW or r["id"] in EXCLUDED_OLD)
        ax.scatter(r["utm_x"], r["utm_y"], s=160,
                   facecolor=COL[k] if kept else "white",
                   edgecolor=COL[k], linewidth=2.2, zorder=3)
        ax.annotate(r["id"], (r["utm_x"], r["utm_y"]), fontsize=8,
                    xytext=(7, 4), textcoords="offset points")
leg = [Patch(facecolor=COL["regional"], label="regional aquifer (assimilated, n=10*)"),
       Patch(facecolor=COL["boundary"], label="boundary-controlled (coastal, K-insensitive)"),
       Patch(facecolor=COL["perched"], label="perched (water table at surface)"),
       Patch(facecolor="white", edgecolor="k", label="hollow = excluded from assimilation")]
ax.legend(handles=leg, fontsize=9, loc="upper right")
ax.set_xlabel("UTM E (m, zone 51S)"); ax.set_ylabel("UTM N (m)")
ax.set_aspect("equal")
ax.set_title("Well classification by hydraulic state\n"
             "(grey = coastline; *ww05/ww08 kept but perched-suspect)",
             fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(FIG / "paper_well_classification.png", dpi=160)
print("saved figs/paper_well_classification.png")

# =============================================================== FIG 2: obs-sim
cal = d[d["use_for_calibration"] == True].copy()
fig2, ax2 = plt.subplots(figsize=(7, 7))
for k in ["regional", "boundary", "perched"]:
    sub = cal[cal.k == k]
    if len(sub):
        ax2.scatter(sub["obs"], sub["sim_L2"], s=90, c=COL[k], edgecolor="k",
                    linewidth=0.5, zorder=3,
                    label={"regional": "regional", "boundary": "boundary-controlled",
                           "perched": "perched-suspect (kept)"}[k])
lim = [-1, 9]
ax2.plot(lim, lim, "k-", lw=1.2, label="1:1")
for off in (1, -1):
    ax2.plot(lim, [l + off for l in lim], "k:", lw=0.6)
for _, r in cal.iterrows():
    ax2.annotate(r["id"], (r["obs"], r["sim_L2"]), fontsize=7,
                 xytext=(4, 2), textcoords="offset points")
ax2.set_xlim(lim); ax2.set_ylim(lim)
ax2.set_xlabel("observed head (m)"); ax2.set_ylabel("simulated head (m)")
ax2.set_title("A-clean preferred calibration — observed vs simulated\n"
              "14 assimilated wells, RMSE = 1.75 m (±1 m dotted)",
              fontsize=11, fontweight="bold")
ax2.legend(fontsize=9, loc="upper left")
fig2.tight_layout()
fig2.savefig(FIG / "paper_obs_vs_sim.png", dpi=160)
print("saved figs/paper_obs_vs_sim.png")

# =============================================================== FIG 3: table
rows = [
    ["base",      "17", "0", "89.96", "2.21", "—",         "K2=1, perched included"],
    ["B",         "17", "4", "77.86", "2.18", "—",         "exploration: +global RCH"],
    ["D",         "17", "5", "70.78", "2.07", "—",         "diagnostic: recharge unphysical"],
    ["A-clean",   "14", "3", "42.74", "1.75", "1.60",      "PREFERRED (perched excluded)"],
    ["strict-12", "12", "3", "28.03", "1.53", "1.52",      "robustness (drop ww05/08)"],
    ["SSE-split", "12", "4", "27.78", "—",    "c2.0/i1.45", "diagnostic: split = no gain"],
]
cols = ["scenario", "wells", "n_par", "Φ", "RMSE(m)", "k2_sse", "role"]
fig3, ax3 = plt.subplots(figsize=(13.5, 3.0)); ax3.axis("off")
tbl = ax3.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center",
                colWidths=[0.11, 0.07, 0.07, 0.09, 0.10, 0.11, 0.30])
tbl.auto_set_font_size(False); tbl.set_fontsize(10); tbl.scale(1, 1.7)
for j in range(len(cols)):
    tbl[0, j].set_facecolor("#404040"); tbl[0, j].set_text_props(color="w", fontweight="bold")
for i in range(1, len(rows) + 1):
    if rows[i - 1][0] == "A-clean":
        for j in range(len(cols)):
            tbl[i, j].set_facecolor("#d9ead3")
ax3.set_title("Calibration scenarios — Φ falls with parameters, but A-clean is the "
              "physically-defensible preferred solution",
              fontsize=11, fontweight="bold", pad=14)
fig3.savefig(FIG / "paper_scenario_table.png", dpi=160, bbox_inches="tight")
print("saved figs/paper_scenario_table.png")
