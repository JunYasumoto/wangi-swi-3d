"""Phase 3c retrospective re-evaluation against PPP-corrected truth.

Step 1: Build new calibration_targets_corrected.csv where obs_used = GW_Level_best_m
        from wells_truth.csv (PPP-corrected truth, 2026-06-03).
        - WW4 (ww04) override to HOBO 8-month mean +2.418 m (per memory).
        - Highland perched (ww01, ww14, ww16) flagged diagnostic-only.
        - ww10 down-weighted as anomaly.
Step 2: Re-evaluate the existing L3-shallow / L3_250 / NWrch14 heads CSVs against truth.
Step 3: Plot residual map + observed vs simulated (truth basis).

Backup of prior calibration_targets_corrected.csv -> calibration_targets_pest_baseline.csv.
"""
import sys, io, pathlib, shutil
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
TRUTH_FP = pathlib.Path(r"C:\Users\安元純\.gemini\antigravity\scratch\wangi_swi\wells_truth.csv")
TARGETS  = WORK / "calibration_targets_corrected.csv"
BACKUP   = WORK / "calibration_targets_pest_baseline.csv"

# WW4 anchor (HOBO 8-month mean, supersedes wells_truth GW_Level_best_m=2.397)
WW4_TRUTH = 2.418

# Highland perched — diagnostic only (excluded from regional RMSE)
DIAG_ONLY = {"ww01", "ww14", "ww16"}
# Anomaly / special condition — down-weight in PEST
DOWN_WEIGHT = {"ww10": 0.1}

# ---------------------------------------------------------------------------
# Step 1: Build truth-based calibration targets
# ---------------------------------------------------------------------------
truth = pd.read_csv(TRUTH_FP)
truth = truth.rename(columns={"int_name": "id"})
truth = truth[["id", "aquifer_class", "GW_Level_best_m", "terrain_elev_m"]]
truth.loc[truth["id"] == "ww04", "GW_Level_best_m"] = WW4_TRUTH

if TARGETS.exists() and not BACKUP.exists():
    shutil.copy2(TARGETS, BACKUP)
    print(f"Backup: {BACKUP.name} (prior PEST-baseline targets)")
elif BACKUP.exists():
    print(f"Backup already exists: {BACKUP.name}")

prior = pd.read_csv(TARGETS) if TARGETS.exists() else pd.DataFrame()
new = truth.copy()
if not prior.empty and {"utm_x", "utm_y"}.issubset(prior.columns):
    new = new.merge(prior[["id", "utm_x", "utm_y", "obs_head"]].rename(columns={"obs_head": "obs_pest_baseline"}),
                    on="id", how="left")
new = new.rename(columns={"GW_Level_best_m": "obs_truth_ppp"})
new["obs_used"] = new["obs_truth_ppp"]
new["use_for_calibration"] = ~new["id"].isin(DIAG_ONLY)
new["weight"] = 1.0
for wid, w in DOWN_WEIGHT.items():
    new.loc[new["id"] == wid, "weight"] = w
new.loc[new["id"].isin(DIAG_ONLY), "weight"] = 0.0
new["target_source"] = "wells_truth_PPP_2026-06-03"
new.loc[new["id"] == "ww04", "target_source"] = "WW4_HOBO_8mo_mean_+2.418"

cols = ["id", "aquifer_class", "terrain_elev_m", "obs_truth_ppp", "obs_used",
        "use_for_calibration", "weight", "target_source"]
if "utm_x" in new.columns: cols += ["utm_x", "utm_y"]
if "obs_pest_baseline" in new.columns: cols += ["obs_pest_baseline"]
new = new[cols]
new.to_csv(TARGETS, index=False, float_format="%.4f")
print(f"\nWrote: {TARGETS.name}")
print(new.to_string(index=False))

# ---------------------------------------------------------------------------
# Step 2: Re-evaluate existing scenarios against truth
# ---------------------------------------------------------------------------
NW   = {"ww02","ww03","ww17","ww18","ww19","ww05","ww06"}
SSE  = {"ww07","ww08","ww09","ww13","ww15"}
CENT = {"ww04","ww11","ww12","ww20"}

scenarios = [
    ("L3shallow", "phase3a_heads_3c_L3shallow.csv",      "Phase 3c L3-shallow (L3=-200)"),
    ("L3_250",    "phase3a_heads_3c_L3_250.csv",         "L3 = -250 m"),
    ("NWrch14",   "phase3a_heads_3c_L3sh_NWrch14.csv",   "L3-shallow + NW RCH×1.4"),
]

truth_map = new.set_index("id")[["obs_used", "use_for_calibration", "weight"]]

rows = []
for tag, fname, label in scenarios:
    fp = WORK / fname
    if not fp.exists():
        print(f"SKIP {tag}: {fname} not found")
        continue
    df = pd.read_csv(fp).merge(truth_map, left_on="id", right_index=True, how="left")
    df["resid_truth"] = df["sim_L2"] - df["obs_used"]
    df["resid_old"]   = df["sim_used"] - df["obs"]
    df.to_csv(WORK / f"phase3a_heads_{tag}_truth.csv", index=False, float_format="%.4f")

    cal = df[df["use_for_calibration"] == True]
    cal_wt = cal.dropna(subset=["obs_used"])
    w = cal_wt["weight"].values
    r = cal_wt["resid_truth"].values
    rmse_wt = np.sqrt(np.average(r**2, weights=w)) if w.sum() > 0 else np.nan
    bias_wt = np.average(r, weights=w) if w.sum() > 0 else np.nan
    def zone_stats(S):
        s = df[df["id"].isin(S) & (df["use_for_calibration"] == True)].dropna(subset=["obs_used"])
        if len(s) == 0: return (0, np.nan, np.nan)
        return (len(s), float(np.sqrt((s["resid_truth"]**2).mean())), float(s["resid_truth"].mean()))
    n_nw,  rmse_nw,  bias_nw  = zone_stats(NW)
    n_cent,rmse_cent,bias_cent= zone_stats(CENT)
    n_sse, rmse_sse, bias_sse = zone_stats(SSE)
    rows.append(dict(
        tag=tag, label=label,
        n=len(cal_wt), rmse_truth_wt=rmse_wt, bias_truth_wt=bias_wt,
        n_NW=n_nw, rmse_NW=rmse_nw, bias_NW=bias_nw,
        n_CENT=n_cent, rmse_CENT=rmse_cent, bias_CENT=bias_cent,
        n_SSE=n_sse, rmse_SSE=rmse_sse, bias_SSE=bias_sse,
        ww4_sim=float(df[df["id"]=="ww04"]["sim_L2"].iloc[0]) if "ww04" in df["id"].values else np.nan,
        ww4_truth=WW4_TRUTH,
    ))

out = pd.DataFrame(rows)
print("\n=== Phase 3c re-evaluation against PPP truth ===")
print(out.to_string(index=False, float_format="%.3f"))
out.to_csv(WORK / "scenario_comparison_truth.csv", index=False, float_format="%.4f")
print(f"\nSaved: scenario_comparison_truth.csv")

# ---------------------------------------------------------------------------
# Step 3: Figures (residual map + obs vs sim) for L3-shallow against truth
# ---------------------------------------------------------------------------
df = pd.read_csv(WORK / "phase3a_heads_L3shallow_truth.csv")
wcells = pd.read_csv(WORK / "well_cells.csv")
df = df.merge(wcells[["id","model_row","model_col"]], on="id", how="left")

fig, axes = plt.subplots(1, 2, figsize=(15, 7))

ax = axes[0]
cal = df[df["use_for_calibration"] == True].dropna(subset=["obs_used"])
diag = df[df["use_for_calibration"] == False].dropna(subset=["obs_used"])
mn = min(cal["obs_used"].min(), cal["sim_L2"].min()) - 0.5
mx = max(cal["obs_used"].max(), cal["sim_L2"].max()) + 0.5
ax.plot([mn, mx], [mn, mx], "k--", lw=1, label="1:1")
for _, r in cal.iterrows():
    if r["id"] in NW:   c, lab = "#1f77b4", "NW"
    elif r["id"] in CENT: c, lab = "#2ca02c", "CENT"
    elif r["id"] in SSE: c, lab = "#d62728", "SSE"
    else: c, lab = "gray", "other"
    ax.scatter(r["obs_used"], r["sim_L2"], c=c, s=80, edgecolor="black", zorder=3)
    ax.annotate(r["id"], (r["obs_used"], r["sim_L2"]), xytext=(4, 4),
                textcoords="offset points", fontsize=8)
# legend dummies
for c, lab in [("#1f77b4","NW"),("#2ca02c","CENT"),("#d62728","SSE")]:
    ax.scatter([], [], c=c, s=80, edgecolor="black", label=lab)
ax.set_xlabel("Observed (PPP truth, m MSL)", fontsize=11)
ax.set_ylabel("Simulated L2 head (m MSL)", fontsize=11)
ax.set_title(f"(a) L3-shallow vs PPP truth — RMSE = {out[out.tag=='L3shallow'].rmse_truth_wt.iloc[0]:.2f} m, bias = {out[out.tag=='L3shallow'].bias_truth_wt.iloc[0]:+.2f} m (n=16, ww10 wt 0.1)",
             fontsize=11, fontweight="bold")
ax.legend(fontsize=10, loc="upper left")
ax.grid(alpha=0.3)
ax.set_aspect("equal", adjustable="datalim")

ax = axes[1]
top = np.load(WORK / "top_elevation.npy")
idomain = np.load(WORK / "idomain.npy")
ax.imshow(np.where(idomain == 1, 0, np.nan), cmap="Greys_r", alpha=0.15)
for _, r in cal.iterrows():
    rv = r["resid_truth"]
    col = "red" if rv > 0 else "blue"
    sz = 30 + 250 * min(abs(rv) / 3.0, 1.0)
    ax.scatter(r["model_col"], r["model_row"], c=col, s=sz,
               edgecolor="black", linewidth=1.0, alpha=0.85)
    ax.annotate(f"{r['id']}\n{rv:+.1f}", (r["model_col"], r["model_row"]),
                xytext=(6, 6), textcoords="offset points", fontsize=7.5, fontweight="bold")
ax.set_title("(b) Residual map (sim_L2 − truth)  red=over, blue=under", fontsize=11, fontweight="bold")
ax.set_xlabel("Column"); ax.set_ylabel("Row")
ax.invert_yaxis()

fig.suptitle("Phase 3c L3-shallow re-evaluation against PPP-corrected truth",
             fontsize=13, fontweight="bold", y=1.00)
plt.tight_layout()
out_fig = WORK / "figs" / "L3shallow_vs_truth.png"
out_fig.parent.mkdir(exist_ok=True)
plt.savefig(out_fig, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out_fig}")
