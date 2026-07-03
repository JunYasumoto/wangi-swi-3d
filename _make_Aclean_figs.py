"""A-clean (perched-excluded, 14-well) main-result figures.

Conceptual message: not "force-fit every well" but "recognise observations
represent different hydraulic states and define the physically-assimilable set."

Fig 1 (conceptual): why ww10/11/12 (and suspects ww05/08) are perched —
  depth-to-water ~0 (water table at land surface) and head decoupled from the sea.
Fig 2 (calibration): the A-clean 3-zone K2 fit over the 14 assimilable wells.
"""
import numpy as np, pandas as pd, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W = pathlib.Path(__file__).resolve().parent
FIG = W / "figs"; FIG.mkdir(exist_ok=True)

# ---- data ------------------------------------------------------------------
d = pd.read_csv(W / "diag_Aclean.csv")          # 20 wells, A-clean optimum sims
wc = pd.read_csv(W / "well_cells.csv").set_index("id")
idom = np.squeeze(np.load(W / "idomain.npy")).astype(int)
pad = np.pad(idom, 1, mode="constant", constant_values=0)
is_coast = (idom == 1) & ((pad[0:-2, 1:-1] == 0) | (pad[2:, 1:-1] == 0)
                          | (pad[1:-1, 0:-2] == 0) | (pad[1:-1, 2:] == 0))
cr, cc = np.where(is_coast)

def dist_sea(wid):
    r, c = int(wc.loc[wid, "row"]), int(wc.loc[wid, "col"])
    return np.sqrt(((cr - r) * 30.0) ** 2 + ((cc - c) * 30.0) ** 2).min()

d["dist_sea"] = d["id"].map(lambda w: dist_sea(w) if w in wc.index else np.nan)
d["obs"] = d["obs_truth_ppp"]
d["dtw"] = d["terrain_elev_m"] - d["obs"]        # depth to water
d["res"] = d["obs"] - d["sim_L2"]

PERCHED_HI = ["ww01", "ww14", "ww16"]            # central highland (long excluded)
PERCHED_NEW = ["ww10", "ww11", "ww12"]           # newly excluded this session
SUSPECT = ["ww05", "ww08"]                       # perched-signature, kept (sensitivity)
ZONE = {**{w: "NW" for w in ["ww02", "ww03", "ww18", "ww19", "ww20"]},
        **{w: "CENT" for w in ["ww04", "ww11", "ww12"]},
        **{w: "SSE" for w in ["ww05", "ww06", "ww07", "ww08", "ww09",
                               "ww13", "ww15", "ww17"]}}
ZCOL = {"NW": "#1f77b4", "CENT": "#9467bd", "SSE": "#2ca02c"}
d["zone"] = d["id"].map(ZONE)
cal = d[d["use_for_calibration"] == True].copy()   # the 14 assimilable wells

# =============================================================== FIGURE 1
fig, ax = plt.subplots(1, 2, figsize=(13, 5.6))
low = d[(d["terrain_elev_m"] < 30) & d["dist_sea"].notna()].copy()  # drop highland

# (a) depth-to-water vs distance to sea
def cat(w):
    if w in PERCHED_NEW: return "excluded (perched)"
    if w in SUSPECT: return "perched-suspect (kept)"
    return "assimilable (regional)"
low["cat"] = low["id"].map(cat)
cmap = {"excluded (perched)": "#d62728", "perched-suspect (kept)": "#ff7f0e",
        "assimilable (regional)": "#1f77b4"}
for c, sub in low.groupby("cat"):
    ax[0].scatter(sub["dist_sea"], sub["dtw"], c=cmap[c], s=80, label=c,
                  edgecolor="k", linewidth=0.4, zorder=3)
for _, r in low.iterrows():
    ax[0].annotate(r["id"], (r["dist_sea"], r["dtw"]), fontsize=7,
                   xytext=(3, 3), textcoords="offset points")
ax[0].axhspan(-1, 0.7, color="#ffe0e0", zorder=0)
ax[0].text(low["dist_sea"].max() * 0.55, 0.0,
           "water table at land surface\n→ perched signature", fontsize=8, color="#a00")
ax[0].set_xlabel("distance to sea (m)")
ax[0].set_ylabel("depth to water = terrain − head (m)")
ax[0].set_title("(a) Perched diagnostic: water table at surface\nnear the coast = decoupled from sea")
ax[0].legend(fontsize=8, loc="lower right"); ax[0].grid(alpha=0.3)

# (b) observed head vs terrain elevation (perched fall on 1:1)
for c, sub in low.groupby("cat"):
    ax[1].scatter(sub["terrain_elev_m"], sub["obs"], c=cmap[c], s=80,
                  edgecolor="k", linewidth=0.4, zorder=3, label=c)
lim = [-1, 18]
ax[1].plot(lim, lim, "k--", lw=1, label="head = terrain (perched)")
for _, r in low.iterrows():
    ax[1].annotate(r["id"], (r["terrain_elev_m"], r["obs"]), fontsize=7,
                   xytext=(3, -8), textcoords="offset points")
ax[1].set_xlim(lim); ax[1].set_ylim(lim)
ax[1].set_xlabel("terrain elevation (m)"); ax[1].set_ylabel("observed head (m)")
ax[1].set_title("(b) Perched wells sit on head = terrain;\nregional wells plot below")
ax[1].legend(fontsize=8, loc="upper left")
fig.suptitle("Defining the physically-assimilable well set — observations represent "
             "different hydraulic states (not a fitting failure)",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(FIG / "Aclean_perched_diagnostic.png", dpi=150)
print("saved figs/Aclean_perched_diagnostic.png")

# =============================================================== FIGURE 2
fig2, ax2 = plt.subplots(2, 2, figsize=(13, 10))

# (a) obs vs sim for the 14 assimilable wells, by zone
for z, sub in cal.groupby("zone"):
    ax2[0, 0].scatter(sub["obs"], sub["sim_L2"], c=ZCOL[z], s=70, label=z,
                      edgecolor="k", linewidth=0.4, zorder=3)
lim = [-1, 9]
ax2[0, 0].plot(lim, lim, "k-", lw=1)
for off in (1, -1):
    ax2[0, 0].plot(lim, [l + off for l in lim], "k:", lw=0.6)
for _, r in cal.iterrows():
    ax2[0, 0].annotate(r["id"], (r["obs"], r["sim_L2"]), fontsize=6.5,
                       xytext=(3, 2), textcoords="offset points")
ax2[0, 0].set_xlim(lim); ax2[0, 0].set_ylim(lim)
ax2[0, 0].set_xlabel("observed head (m)"); ax2[0, 0].set_ylabel("simulated head (m)")
ax2[0, 0].set_title("(a) A-clean fit: 14 assimilable wells (±1 m dotted)\n"
                    "RMSE = 1.75 m")
ax2[0, 0].legend(fontsize=9)

# (b) phi by group base(clean) vs A-clean optimum
grp = ["obs_cent", "obs_nw", "obs_sse"]
base_phi = [1.475, 6.886, 39.696]
opt_phi = [0.485, 6.817, 35.436]
xg = np.arange(len(grp)); wd = 0.35
ax2[0, 1].bar(xg - wd / 2, base_phi, wd, label="base (K2=1)  Φ=48.1", color="#bbbbbb")
ax2[0, 1].bar(xg + wd / 2, opt_phi, wd, label="A-clean opt  Φ=42.7", color="#2ca02c")
ax2[0, 1].set_xticks(xg); ax2[0, 1].set_xticklabels(grp)
ax2[0, 1].set_ylabel("Φ contribution")
ax2[0, 1].set_title("(b) Φ by group — residual concentrated in SSE")
ax2[0, 1].legend(fontsize=9)

# (c) zonal RMSE
zones = ["NW", "CENT\n(ww04)", "SSE"]
rms = [np.sqrt((cal[cal.zone == z].res ** 2).mean())
       for z in ["NW", "CENT", "SSE"]]
ax2[1, 0].bar(zones, rms, color=[ZCOL["NW"], ZCOL["CENT"], ZCOL["SSE"]])
for i, v in enumerate(rms):
    ax2[1, 0].text(i, v + 0.03, f"{v:.2f}", ha="center", fontweight="bold")
ax2[1, 0].set_ylabel("RMSE (m)")
ax2[1, 0].set_title("(c) Zonal RMSE — NW & CENT well-fit, SSE remains")

# (d) SSE per-well residuals (the remaining heterogeneity)
sse = cal[cal.zone == "SSE"].sort_values("res")
colors = ["#d62728" if w in SUSPECT else "#2ca02c" for w in sse["id"]]
ax2[1, 1].barh(sse["id"], sse["res"], color=colors)
ax2[1, 1].axvline(0, color="k", lw=0.8)
ax2[1, 1].set_xlabel("residual obs − sim (m)")
ax2[1, 1].set_title("(d) SSE residuals: mixed +/- = intra-zone heterogeneity\n"
                    "(red = perched-suspect ww05/ww08)")
fig2.suptitle("A-clean — physically-defensible 3-zone K2 calibration "
              "(main result, RMSE 1.75 m)", fontsize=13, fontweight="bold")
fig2.tight_layout(rect=[0, 0, 1, 0.96])
fig2.savefig(FIG / "Aclean_calibration_result.png", dpi=150)
print("saved figs/Aclean_calibration_result.png")
