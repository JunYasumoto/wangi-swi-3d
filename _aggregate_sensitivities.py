"""Aggregate residuals across all Phase 3c sensitivity scenarios.

Compare RMSE / bias / zonal stats across:
  - baseline (BOTM_L3=-500, GHB=1.0)
  - L3 shallow (BOTM_L3=-200, GHB=1.0)
  - L3 250 (BOTM_L3=-250, GHB=1.0)
  - GHB mult 0.1
  - GHB mult 0.01
  - K2 global 0.5
  - + combinations

Output:
  scenario_comparison.csv
  figs/scenario_comparison.png (multi-panel zonal RMSE/bias)
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent

PERCHED = {"ww10", "ww14", "ww16"}
NW_WELLS  = {"ww02","ww03","ww17","ww18","ww19","ww05","ww06"}
SSE_WELLS = {"ww07","ww08","ww09","ww13","ww15"}
CENT_WELLS = {"ww04","ww11","ww12","ww20"}

WW4_TRUTH = 2.418   # HOBO long-term mean

# Merge with truth-based calibration targets (Step 4 of 2026-06-08 plan).
# `obs_used` here is PPP-corrected truth; `use_for_calibration=False` excludes
# highland perched (ww01/14/16), `weight=0.1` down-weights ww10 anomaly.
TARGETS_FP = WORK / "calibration_targets_corrected.csv"
targets = pd.read_csv(TARGETS_FP)[["id", "obs_used", "use_for_calibration", "weight"]]
targets = targets.rename(columns={"obs_used": "obs_truth"})

# List of scenarios to load (head files)
scenarios = [
    ("baseline",      "phase3a_heads_3c_baseline.csv",       "Phase 3a baseline (L3=-500)"),
    ("L3shallow",     "phase3a_heads_3c_L3shallow.csv",      "Phase 3c L3-shallow (L3=-200)"),
    ("L3_250",        "phase3a_heads_3c_L3_250.csv",         "L3 = -250 m"),
    ("L3_300",        "phase3a_heads_3c_L3_300.csv",         "L3 = -300 m"),
    ("NWk25",         "phase3a_heads_3c_L3sh_NWk25.csv",     "L3-shallow + NW K2=25"),
    ("NWk10",         "phase3a_heads_3c_L3sh_NWzone.csv",    "L3-shallow + NW K2=10 (FAIL)"),
    ("GHBmult01",     "phase3a_heads_3c_L3sh_GHBmult01.csv", "L3-shallow + GHB cond × 0.1 (FAIL)"),
    ("GHBmult05",     "phase3a_heads_3c_L3sh_GHBmult05.csv", "L3-shallow + GHB cond × 0.5 (FAIL)"),
    ("NWrch14",       "phase3a_heads_3c_L3sh_NWrch14.csv",   "L3-shallow + NW RCH×1.4"),
    ("NWk2_05",       "phase3a_heads_3c_L3sh_NWk2_05.csv",   "L3-shallow + NW K2×0.5 (FAIL)"),
    ("K2glob05",      "phase3a_heads_3c_K2glob05.csv",       "L3-shallow + K2 global × 0.5"),
]

rows = []
for tag, fname, label in scenarios:
    fp = WORK / fname
    if not fp.exists():
        print(f"SKIP {tag}: {fname} not found")
        continue
    df = pd.read_csv(fp).merge(targets, on="id", how="left")
    if "sim_L2" not in df.columns:
        print(f"SKIP {tag}: legacy CSV without sim_L2 column")
        continue
    # Always compare regional/main-aquifer wells to L2 (the screened layer)
    df["resid_truth"] = df["sim_L2"] - df["obs_truth"]
    cal = df[df["use_for_calibration"] == True].dropna(subset=["obs_truth"])
    nw   = cal[cal["id"].isin(NW_WELLS)]
    sse  = cal[cal["id"].isin(SSE_WELLS)]
    cent = cal[cal["id"].isin(CENT_WELLS)]
    w = cal["weight"].values
    r = cal["resid_truth"].values
    rmse_wt = float(np.sqrt(np.average(r**2, weights=w))) if w.sum() > 0 else np.nan
    bias_wt = float(np.average(r, weights=w)) if w.sum() > 0 else np.nan
    rows.append({
        "tag": tag, "label": label,
        "n_all": len(cal),
        "rmse_all":  rmse_wt,
        "bias_all":  bias_wt,
        "rmse_NW":   float(np.sqrt((nw["resid_truth"]**2).mean())) if len(nw) else np.nan,
        "bias_NW":   float(nw["resid_truth"].mean()) if len(nw) else np.nan,
        "rmse_SSE":  float(np.sqrt((sse["resid_truth"]**2).mean())) if len(sse) else np.nan,
        "bias_SSE":  float(sse["resid_truth"].mean()) if len(sse) else np.nan,
        "rmse_CENT": float(np.sqrt((cent["resid_truth"]**2).mean())) if len(cent) else np.nan,
        "bias_CENT": float(cent["resid_truth"].mean()) if len(cent) else np.nan,
        "ww4_sim":            float(df[df["id"]=="ww04"]["sim_L2"].iloc[0]) if "ww04" in df["id"].values else np.nan,
        "ww4_bias_vs_truth":  float(df[df["id"]=="ww04"]["sim_L2"].iloc[0]) - WW4_TRUTH if "ww04" in df["id"].values else np.nan,
    })

out = pd.DataFrame(rows)
print("\n=== Phase 3c sensitivity aggregate ===")
print(out.to_string(index=False, float_format="%.2f"))
out.to_csv(WORK / "scenario_comparison.csv", index=False, float_format="%.3f")
print(f"\nSaved: scenario_comparison.csv")

# Plot
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
x = np.arange(len(out))
labels_short = [r["tag"] for _, r in out.iterrows()]

# (a) RMSE all
ax = axes[0,0]
ax.bar(x, out["rmse_all"], color="navy", edgecolor="black")
for i, v in enumerate(out["rmse_all"]):
    ax.text(i, v+0.05, f"{v:.2f}", ha="center", fontsize=9, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(labels_short, rotation=30, fontsize=9)
ax.set_ylabel("RMSE vs PPP truth, weighted (m)", fontsize=11)
ax.set_title("(a) Overall RMSE vs PPP truth (lower = better)", fontweight="bold")
ax.grid(alpha=0.3, axis="y")

# (b) Bias all
ax = axes[0,1]
colors = ["red" if b > 0 else "blue" for b in out["bias_all"]]
ax.bar(x, out["bias_all"], color=colors, edgecolor="black")
ax.axhline(0, color="black", lw=0.7)
for i, v in enumerate(out["bias_all"]):
    y = v + (0.1 if v > 0 else -0.15)
    ax.text(i, y, f"{v:+.2f}", ha="center", fontsize=9, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(labels_short, rotation=30, fontsize=9)
ax.set_ylabel("Bias vs PPP truth, weighted (m)", fontsize=11)
ax.set_title("(b) Overall bias vs PPP truth (closer to 0 = better)", fontweight="bold")
ax.grid(alpha=0.3, axis="y")

# (c) Zonal bias breakdown
ax = axes[1,0]
w = 0.25
ax.bar(x - w, out["bias_NW"], w, color="#1f77b4", edgecolor="black", label="NW (was under)")
ax.bar(x,     out["bias_CENT"], w, color="#2ca02c", edgecolor="black", label="Central")
ax.bar(x + w, out["bias_SSE"], w, color="#d62728", edgecolor="black", label="S/SE")
ax.axhline(0, color="black", lw=0.7)
ax.set_xticks(x); ax.set_xticklabels(labels_short, rotation=30, fontsize=9)
ax.set_ylabel("Zonal bias (m)", fontsize=11)
ax.set_title("(c) Zone-wise bias evolution", fontweight="bold")
ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="y")

# (d) WW4 vs truth
ax = axes[1,1]
ax.bar(x, out["ww4_bias_vs_truth"], color="purple", edgecolor="black")
ax.axhline(0, color="black", lw=0.7)
for i, v in enumerate(out["ww4_bias_vs_truth"]):
    if not np.isnan(v):
        y = v + (0.1 if v > 0 else -0.15)
        ax.text(i, y, f"{v:+.2f}", ha="center", fontsize=9, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(labels_short, rotation=30, fontsize=9)
ax.set_ylabel("WW4 sim − truth (+2.418 m MSL)", fontsize=11)
ax.set_title("(d) WW4 vs HOBO truth (8-month)", fontweight="bold")
ax.grid(alpha=0.3, axis="y")

fig.suptitle("Phase 3c sensitivity comparison vs PPP-corrected truth\n"
             "(ww01/14/16 highland-perched excluded; ww10 anomaly weight 0.1)",
             fontsize=13, fontweight="bold", y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.96])
out_fig = WORK / "figs" / "scenario_comparison.png"
plt.savefig(out_fig, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out_fig}")
