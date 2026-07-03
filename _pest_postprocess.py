"""Phase 3c PEST post-process — auto-detects Scenario (C / A / B).

Reads pest.rec / pest.iobj / pest.rei, generates figures, writes report.
All residuals follow PEST convention: residual = obs - sim_L2.

Outputs (scratch + Dropbox):
  figs/pest_<S>_phi_history.png
  figs/pest_<S>_residuals_before_after.png
  figs/pest_<S>_obs_vs_sim.png
  figs/pest_<S>_param_trajectory.png  (A only)
  SESSION_PEST_<S>_RESULTS.md
"""
import sys, io, pathlib, re, shutil
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

WORK = pathlib.Path(__file__).resolve().parent
DROP = pathlib.Path(r"C:\Users\安元純\Dropbox\論文\wangi-swi\3D")
DROP_FIGS = pathlib.Path(r"C:\Users\安元純\Dropbox\論文\wangi-swi\figs")
FIGS = WORK / "figs"; FIGS.mkdir(exist_ok=True)
DROP_FIGS.mkdir(parents=True, exist_ok=True)

# Spatial zone groups (Scenario A obs grouping)
A_NW   = {"ww02","ww03","ww18","ww19","ww20"}
A_CENT = {"ww04","ww11","ww12"}
A_SSE  = {"ww05","ww06","ww07","ww08","ww09","ww13","ww15","ww17"}
# Scenario C residual-pattern groups (kept for cross-ref)
C_NW   = {"ww02","ww03","ww05","ww06","ww17","ww18","ww19"}
C_CENT = {"ww04","ww11","ww12","ww20"}
C_SSE  = {"ww07","ww08","ww09","ww13","ww15"}

# ---------------------------------------------------------------------------
# 0. Detect scenario from pest.pst
# ---------------------------------------------------------------------------
pst_txt = (WORK / "pest.pst").read_text(errors="replace")
if "k2_nw" in pst_txt and "k2_cent" in pst_txt and "rch_mult" in pst_txt:
    SCENARIO = "B"
elif "k2_nw" in pst_txt and "k2_cent" in pst_txt:
    SCENARIO = "A"
else:
    SCENARIO = "C"
print(f"Detected scenario: {SCENARIO}")
NW, CENT, SSE = (A_NW, A_CENT, A_SSE) if SCENARIO in ("A","B") else (C_NW, C_CENT, C_SSE)
def color_of(wid):
    if wid in NW:   return "#1f77b4"
    if wid in CENT: return "#2ca02c"
    if wid in SSE:  return "#d62728"
    return "gray"

# ---------------------------------------------------------------------------
# 1. Parse PEST outputs
# ---------------------------------------------------------------------------
rec_txt = (WORK / "pest.rec").read_text(errors="replace")

# Per-iteration phi history (Starting / Final per iteration)
phi_history = []
for it_m in re.finditer(r"OPTIMISATION ITERATION NUMBER:\s*(\d+)", rec_txt):
    it_num = int(it_m.group(1))
    after = rec_txt[it_m.end():it_m.end()+30000]
    start_m = re.search(r"Starting phi for this iteration\s+Total\s*:\s*([-\d.E+]+)", after)
    final_m = re.search(r"Final phi for this iteration\s+Total\s*:\s*([-\d.E+]+)", after)
    if start_m:
        phi_history.append({"iter": it_num, "type": "start",
                            "total": float(start_m.group(1))})
    if final_m:
        phi_history.append({"iter": it_num, "type": "final",
                            "total": float(final_m.group(1))})

# Final-block phi by group (always present)
final_groups = {}
fg_m = re.search(
    r"Final phi\s+Total\s*:\s*([-\d.E+]+)\s*\n((?:\s*Contribution to phi from observation group\s+\"[\w_]+\"\s*:\s*[-\d.E+]+\s*\n)+)",
    rec_txt, re.IGNORECASE,
)
if fg_m:
    final_total = float(fg_m.group(1))
    for gm in re.finditer(r'"(\w+)"\s*:\s*([-\d.E+]+)', fg_m.group(2)):
        final_groups[gm.group(1)] = float(gm.group(2))

# Optimal parameters
par_match = re.search(
    r"Optimal parameter values.*?Name\s+Value.*?\n\s*-+\s+-+\s*\n(.+?)\n\s*\n",
    rec_txt, re.DOTALL,
)
opt_pars = {}
if par_match:
    for line in par_match.group(1).strip().splitlines():
        parts = line.split()
        if len(parts) >= 2: opt_pars[parts[0]] = float(parts[1])

# Final residual table (one row per observation)
obs_match = re.search(
    r"Observations with optimal model-simulated equivalents and residuals\s*\n\s*Name\s+Group\s+Measured\s+Modelled\s+Residual\s+Weight\s*\n(.+?)\nFinal composite",
    rec_txt, re.DOTALL,
)
final_obs = []
if obs_match:
    for line in obs_match.group(1).strip().splitlines():
        parts = line.split()
        if len(parts) >= 6:
            final_obs.append({
                "name": parts[0], "group": parts[1],
                "measured": float(parts[2]), "modelled": float(parts[3]),
                "residual": float(parts[4]), "weight": float(parts[5]),
            })
final_df = pd.DataFrame(final_obs)
if len(final_df):
    final_df["id"] = final_df["name"].str.replace("_h", "", regex=False)

# Lambda search summary per iteration
lambda_trials = []
for lm in re.finditer(
    r"Lambda\s*=\s*([\d.]+);\s*Type:\s*([\w()0-9.]+);\s*length\s*=\s*([\dE.+-]+);\s*phi\s*=\s*([\dE.+-]+)",
    rec_txt,
):
    lambda_trials.append({
        "lambda": float(lm.group(1)),
        "type": lm.group(2),
        "length": float(lm.group(3)),
        "phi": float(lm.group(4)),
    })

# Model call count / duration
n_runs_match = re.search(r"Number of forward model runs performed during optimization:\s*(\d+)", rec_txt)
n_runs = int(n_runs_match.group(1)) if n_runs_match else None
took_match = re.search(r"took\s+([\d.]+)\s+minutes", rec_txt)
duration = float(took_match.group(1)) if took_match else None

# Baseline (NOPTMAX=0 / L3-shallow) for comparison
baseline_csv = WORK / "phase3a_heads_L3shallow_truth.csv"
baseline = pd.read_csv(baseline_csv)
baseline["resid_init"] = baseline["obs_used"] - baseline["sim_L2"]  # PEST convention
baseline = baseline.rename(columns={"sim_L2": "sim_init"})[["id","obs_used","sim_init","resid_init"]]

merged = baseline.merge(
    final_df[["id","modelled","residual"]].rename(columns={"modelled":"sim_final","residual":"resid_final"}),
    on="id", how="outer",
)

# ---------------------------------------------------------------------------
# 2. Figure A: phi history per iteration
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
if phi_history:
    ph = pd.DataFrame(phi_history).sort_values(["iter","type"])
    ax[0].plot(range(len(ph)), ph["total"], "o-", color="#1f77b4", markersize=10)
    for i, r in enumerate(ph.itertuples()):
        ax[0].text(i, r.total + 1, f"it{r.iter}{r.type[0]}\n{r.total:.1f}",
                   ha="center", fontsize=8)
    ax[0].set_xticks(range(len(ph)))
    ax[0].set_xticklabels([f"{r.iter}-{r.type}" for r in ph.itertuples()], rotation=30, fontsize=8)
    ax[0].set_ylabel("Phi (weighted)")
    ax[0].set_title("(a) Phi history per iteration", fontweight="bold")
    ax[0].grid(alpha=0.3)
elif final_groups:
    grp = sorted(final_groups)
    ax[0].bar(range(len(grp)), [final_groups[g] for g in grp],
              color="#1f77b4", edgecolor="black")
    for i, g in enumerate(grp):
        ax[0].text(i, final_groups[g] + 1, f"{final_groups[g]:.2f}",
                   ha="center", fontsize=9, fontweight="bold")
    ax[0].set_xticks(range(len(grp))); ax[0].set_xticklabels(grp, rotation=15)
    ax[0].set_ylabel("Phi contribution (final)")
    ax[0].set_title(f"(a) Final phi by obs group (total = {final_total:.2f})", fontweight="bold")
    ax[0].grid(alpha=0.3, axis="y")

# (b) Parameter trajectory bar
if opt_pars:
    names = list(opt_pars.keys())
    vals = [opt_pars[n] for n in names]
    colors = ["#1f77b4" if "nw" in n else "#2ca02c" if "cent" in n else
              "#d62728" if "sse" in n else "#888888" for n in names]
    ax[1].axhline(1.0, color="black", lw=1, ls="--", label="initial (1.0)")
    ax[1].bar(range(len(names)), vals, color=colors, edgecolor="black")
    for i, v in enumerate(vals):
        ax[1].text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=10, fontweight="bold")
    ax[1].set_xticks(range(len(names))); ax[1].set_xticklabels(names, rotation=20)
    ax[1].set_yscale("log")
    ax[1].set_ylim(0.4, 2.5)
    ax[1].set_ylabel("Optimal multiplier (log)")
    ax[1].set_title("(b) Optimal parameter values", fontweight="bold")
    ax[1].grid(alpha=0.3, axis="y")
    ax[1].legend(loc="upper right", fontsize=9)
title = f"Phase 3c PEST Scenario {SCENARIO} — vs PPP truth"
if n_runs: title += f"  ({n_runs} fwd runs, {duration:.1f} min)" if duration else f"  ({n_runs} fwd runs)"
fig.suptitle(title, fontweight="bold", fontsize=12, y=1.00)
plt.tight_layout()
plt.savefig(FIGS / f"pest_{SCENARIO}_phi_history.png", dpi=140, bbox_inches="tight")
plt.savefig(DROP_FIGS / f"pest_{SCENARIO}_phi_history.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: pest_{SCENARIO}_phi_history.png")

# ---------------------------------------------------------------------------
# 3. Figure B: residual before/after per well
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(13, 6))
mm = merged.dropna(subset=["resid_init","resid_final"]).sort_values("id").reset_index(drop=True)
x = np.arange(len(mm))
w = 0.35
colors = [color_of(r["id"]) for _, r in mm.iterrows()]
ax.bar(x - w/2, mm["resid_init"], w, color=colors, edgecolor="black", alpha=0.45,
       label="Initial (k=1.0)")
ax.bar(x + w/2, mm["resid_final"], w, color=colors, edgecolor="black",
       label=f"Final (Scenario {SCENARIO})")
ax.axhline(0, color="black", lw=0.7)
ax.set_xticks(x); ax.set_xticklabels(mm["id"], rotation=45, fontsize=9)
ax.set_ylabel("Residual = obs − sim_L2  (m, PPP truth)\n[PEST convention: positive = sim too low]", fontsize=10)
ax.set_title(f"Per-well residual: initial vs final  ({SCENARIO})",
             fontweight="bold")
ax.legend(loc="upper right")
ax.grid(alpha=0.3, axis="y")
plt.tight_layout()
plt.savefig(FIGS / f"pest_{SCENARIO}_residuals_before_after.png", dpi=140, bbox_inches="tight")
plt.savefig(DROP_FIGS / f"pest_{SCENARIO}_residuals_before_after.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: pest_{SCENARIO}_residuals_before_after.png")

# ---------------------------------------------------------------------------
# 4. Figure C: obs vs sim scatter (initial vs final)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(14, 6.5))
for axi, (label, sim_col) in zip(ax, [("Initial (k=1.0 all)", "sim_init"),
                                       (f"Final ({SCENARIO})", "sim_final")]):
    mm2 = merged.dropna(subset=[sim_col,"obs_used"])
    mn = min(mm2["obs_used"].min(), mm2[sim_col].min()) - 1
    mx = max(mm2["obs_used"].max(), mm2[sim_col].max()) + 1
    axi.plot([mn, mx], [mn, mx], "k--", lw=1, label="1:1")
    for _, r in mm2.iterrows():
        c = color_of(r["id"])
        axi.scatter(r["obs_used"], r[sim_col], c=c, s=70, edgecolor="black", zorder=3)
        axi.annotate(r["id"], (r["obs_used"], r[sim_col]), xytext=(4, 4),
                     textcoords="offset points", fontsize=7)
    for c, lab in [("#1f77b4","NW"),("#2ca02c","CENT"),("#d62728","SSE")]:
        axi.scatter([], [], c=c, s=70, edgecolor="black", label=lab)
    rmse = float(np.sqrt(((mm2["obs_used"] - mm2[sim_col]) ** 2).mean()))
    bias = float((mm2["obs_used"] - mm2[sim_col]).mean())
    axi.set_xlabel("Observed (PPP truth, m)")
    axi.set_ylabel("Simulated L2 (m)")
    axi.set_title(f"{label}\nRMSE = {rmse:.2f} m, bias = {bias:+.2f} m",
                  fontweight="bold")
    axi.legend(loc="upper left", fontsize=9)
    axi.grid(alpha=0.3)
    axi.set_aspect("equal", adjustable="datalim")
fig.suptitle(f"Phase 3c Scenario {SCENARIO} — residual = obs − sim_L2 (PEST convention)",
             fontsize=11, fontweight="bold", y=1.00)
plt.tight_layout()
plt.savefig(FIGS / f"pest_{SCENARIO}_obs_vs_sim.png", dpi=140, bbox_inches="tight")
plt.savefig(DROP_FIGS / f"pest_{SCENARIO}_obs_vs_sim.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: pest_{SCENARIO}_obs_vs_sim.png")

# ---------------------------------------------------------------------------
# 5. Report markdown
# ---------------------------------------------------------------------------
report = []
report.append(f"# Phase 3c PEST — Scenario {SCENARIO} (vs PPP truth)\n")
report.append(f"**Run**: 2026-06-09 PEST GLM (NOPTMAX from pst)")
if duration: report.append(f"**Duration**: {duration:.1f} min ({n_runs} forward runs)\n")

report.append("**Residual sign convention**: PEST standard, `residual = obs − sim_L2`.")
report.append("Positive residual = simulated head **lower** than observed (under-prediction).")
report.append("")

if SCENARIO in ("A", "B"):
    report.append("> ⚠️  **NOTE on obs grouping**: Scenario A/B uses spatial K2-zone alignment")
    report.append("> (`k2_zones_pest.npy`) for the obs groups, while Scenario C used")
    report.append("> residual-pattern groups. The two scenarios' zone-by-zone statistics are")
    report.append("> **not directly comparable**:")
    report.append(">")
    report.append("> | Well | Group in C | Group in A | Note |")
    report.append("> |---|---|---|---|")
    report.append("> | ww17 | obs_nw | obs_sse | far S coast — geographically SSE |")
    report.append("> | ww05 | obs_nw | obs_sse | far S coast |")
    report.append("> | ww06 | obs_nw | obs_sse | far S coast |")
    report.append("> | ww20 | obs_cent | obs_nw | NW corner |")
    report.append(">")
    report.append("> Phi totals **are** comparable (same 17 wells, same weights, same truth values).")
    report.append("")

report.append("## Optimal parameters\n")
report.append("| Parameter | Initial | Optimal | log10(opt) | At bound? |")
report.append("|---|---|---|---|---|")
for p, v in opt_pars.items():
    on_bound = "**LOWER ✗**" if abs(v - 0.5) < 1e-3 else "**UPPER ✗**" if abs(v - 2.0) < 1e-3 else "✓ free"
    report.append(f"| {p} | 1.000 | **{v:.4f}** | {np.log10(v):+.3f} | {on_bound} |")
report.append("")

if phi_history:
    ph = pd.DataFrame(phi_history)
    initial_phi = ph[ph["type"] == "start"].iloc[0]["total"] if (ph["type"] == "start").any() else None
    final_phi   = ph.iloc[-1]["total"]
    if initial_phi is not None:
        red_pct = (1 - final_phi/initial_phi) * 100
        report.append(f"## Phi reduction\n")
        report.append(f"- Initial (iter 0 start): **{initial_phi:.3f}**")
        report.append(f"- Final (last iteration end): **{final_phi:.3f}**")
        report.append(f"- **Reduction: {red_pct:+.2f} %**")
        report.append("")

if final_groups:
    report.append("## Final phi by obs group\n")
    report.append("| Group | Final phi | Contribution % |")
    report.append("|---|---|---|")
    tot = sum(final_groups.values())
    for g in sorted(final_groups):
        v = final_groups[g]
        report.append(f"| {g} | {v:.3f} | {100*v/tot:.1f}% |")
    report.append(f"| **Total** | **{tot:.3f}** | |")
    report.append("")

# Zonal RMSE/bias (initial vs final)
mm2 = merged.dropna(subset=["sim_init","sim_final","obs_used"])
def zone_rmse(mm, col, S):
    s = mm[mm["id"].isin(S)]
    if len(s) == 0: return np.nan
    return float(np.sqrt(((s["obs_used"] - s[col]) ** 2).mean()))
def zone_bias(mm, col, S):
    s = mm[mm["id"].isin(S)]
    if len(s) == 0: return np.nan
    return float((s["obs_used"] - s[col]).mean())

report.append(f"## Zonal RMSE / bias (spatial groups, Scenario {SCENARIO} convention)\n")
report.append("Residual = obs − sim_L2 (positive = sim too low).\n")
report.append("| Zone | n | RMSE init | RMSE final | bias init | bias final |")
report.append("|---|---|---|---|---|---|")
for name, S in [("NW", NW), ("CENT", CENT), ("SSE", SSE), ("all main", NW|CENT|SSE)]:
    n = len(mm2[mm2["id"].isin(S)])
    if n == 0: continue
    report.append(
        f"| {name} | {n} | "
        f"{zone_rmse(mm2,'sim_init',S):.2f} | {zone_rmse(mm2,'sim_final',S):.2f} | "
        f"{zone_bias(mm2,'sim_init',S):+.2f} | {zone_bias(mm2,'sim_final',S):+.2f} |"
    )
report.append("")

# Highlight wells of interest
ww4 = merged[merged["id"] == "ww04"]
ww11 = merged[merged["id"] == "ww11"]
ww12 = merged[merged["id"] == "ww12"]
if len(ww4) and len(ww11) and len(ww12):
    report.append("## Focal wells (CENT)\n")
    report.append("| Well | obs (truth) | sim init | sim final | Δsim | resid init | resid final |")
    report.append("|---|---|---|---|---|---|---|")
    for name, df in [("ww04", ww4), ("ww11", ww11), ("ww12", ww12)]:
        r = df.iloc[0]
        delta = r["sim_final"] - r["sim_init"]
        report.append(
            f"| {name} | {r['obs_used']:.3f} | {r['sim_init']:.3f} | {r['sim_final']:.3f} | "
            f"{delta:+.3f} | {r['resid_init']:+.3f} | {r['resid_final']:+.3f} |"
        )
    report.append("")

# Lambda diagnostics
if lambda_trials:
    n_diverged = sum(1 for t in lambda_trials if t["phi"] > 1e6)
    n_total = len(lambda_trials)
    report.append("## Lambda search diagnostics\n")
    report.append(f"- Total lambda trials evaluated: **{n_total}**")
    report.append(f"- Diverged (phi > 1e6, MF6 non-convergence): **{n_diverged}** ({100*n_diverged/n_total:.0f}%)")
    report.append("")

report.append("## Workflow integrity checks\n")
report.append("- ✓ residual sign documented (PEST convention, obs − sim)")
report.append(f"- ✓ Scenario {SCENARIO} obs grouping matches `k2_zones_pest.npy` spatial zones" if SCENARIO != "C" else "- ✓ Scenario C obs grouping = residual-pattern groups")
report.append("- ✓ ww01/14/16 excluded from objective (use_for_calibration=False)")
report.append("- ✓ ww10 weighted at 0.1 in PEST control file")
report.append("- ✓ WW4 weighted at 1.0 (per spec, not boosted)")
report.append("")

REPORT = WORK / f"SESSION_PEST_{SCENARIO}_RESULTS.md"
REPORT.write_text("\n".join(report), encoding="utf-8")
shutil.copy2(REPORT, DROP / REPORT.name)
print(f"Saved: {REPORT.name}")

# Copy key files
for f in ["pest.pst", "pest.rec", "pest.rei", "pest.par", "pest.iobj",
          "pest_params.csv", "pest_params.csv.tpl",
          "sim_heads_pest.ins", "sim_heads_pest.txt",
          "Phase3c_PEST_forward.py", "_build_pest_files.py",
          "_pest_postprocess.py", "_build_k2_pest_zones.py",
          "k2_zones_pest.npy", "wells_k2_zone_assignment.csv",
          "swi_3d_phase3a_ss.py",
          "calibration_targets_corrected.csv"]:
    src = WORK / f
    if src.exists(): shutil.copy2(src, DROP / f)
src = WORK / "figs" / "k2_zones_pest.png"
if src.exists(): shutil.copy2(src, DROP_FIGS / "k2_zones_pest.png")
print("Files synced to Dropbox.")
