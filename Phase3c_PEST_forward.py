"""Phase 3c PEST forward wrapper — supports Scenario C and Scenario A.

Reads pest_params.csv (PEST writes this from pest_params.csv.tpl) and runs the
3D SWI SS forward via swi_3d_phase3a_ss.py. Extracts heads at calibration wells
and writes sim_heads_pest.txt for PEST to read back via .ins.

Recognised parameter names (any subset may be present):
  rch_mult          — global recharge multiplier (passes through params.csv)
  k2_global_mult    — global K2 multiplier (env K2_GLOBAL_MULT) [Scenario C]
  k2_nw             — NW-zone K2 multiplier (env K2_PEST_NW_MULT) [Scenario A]
  k2_cent           — CENT-zone K2 multiplier (env K2_PEST_CENT_MULT) [Scenario A]
  k2_sse            — SSE-zone K2 multiplier (env K2_PEST_SSE_MULT) [Scenario A]

Residual convention (PEST): residual = obs − sim_L2.
"""
import sys, io, os, pathlib, subprocess
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd

WORK = pathlib.Path(__file__).resolve().parent
PEST_PARAMS = WORK / "pest_params.csv"
MAIN_PARAMS = WORK / "params.csv"
RUN_TAG = "pest_iter"
HEADS_CSV = WORK / f"phase3a_heads_{RUN_TAG}.csv"
SIM_OUT = WORK / "sim_heads_pest.txt"
TARGETS = WORK / "calibration_targets_corrected.csv"

# ---------------------------------------------------------------------------
# 1. Read PEST parameters
# ---------------------------------------------------------------------------
pp = pd.read_csv(PEST_PARAMS).set_index("name")["value"].astype(float)
print(f"[PEST forward] params: {dict(pp)}")

env = os.environ.copy()
env["RUN_TAG"] = RUN_TAG
env["BOTM_L3"] = "-200"

# Patch main params.csv if rch_mult is a PEST parameter; otherwise leave at default
if "rch_mult" in pp.index:
    mp = pd.read_csv(MAIN_PARAMS).set_index("name")
    mp.loc["rch_mult", "value"] = float(pp["rch_mult"])
    mp.reset_index().to_csv(MAIN_PARAMS, index=False)

# Scenario C: global K2 multiplier
if "k2_global_mult" in pp.index:
    env["K2_GLOBAL_MULT"] = f"{float(pp['k2_global_mult']):.6g}"

# Scenario A: zone K2 multipliers
if "k2_nw" in pp.index:
    env["K2_PEST_NW_MULT"] = f"{float(pp['k2_nw']):.6g}"
if "k2_cent" in pp.index:
    env["K2_PEST_CENT_MULT"] = f"{float(pp['k2_cent']):.6g}"
if "k2_sse" in pp.index:
    env["K2_PEST_SSE_MULT"] = f"{float(pp['k2_sse']):.6g}"

# Scenario D: CENT-zone recharge multiplier (k2_zones_pest.npy zone 2)
if "rch_cent" in pp.index:
    env["RCH_CENT_MULT"] = f"{float(pp['rch_cent']):.6g}"

# SSE coastal/inland sub-zone K2 (diagnostic: k2_sse_split.npy 31/32)
if "k2_sse_coast" in pp.index:
    env["K2_PEST_SSE_COAST_MULT"] = f"{float(pp['k2_sse_coast']):.6g}"
if "k2_sse_inland" in pp.index:
    env["K2_PEST_SSE_INLAND_MULT"] = f"{float(pp['k2_sse_inland']):.6g}"

# ---------------------------------------------------------------------------
# 2. Run the SS SWI forward
# ---------------------------------------------------------------------------
cmd = [sys.executable, str(WORK / "swi_3d_phase3a_ss.py")]
print(f"[PEST forward] Launching: {' '.join(cmd)}")
ret = subprocess.run(cmd, env=env, cwd=str(WORK),
                     capture_output=True, text=True, errors="replace")
print(ret.stdout[-2000:] if ret.stdout else "")
if ret.returncode != 0:
    print(f"[PEST forward] FORWARD RUN FAILED (returncode={ret.returncode})")
    print(ret.stderr[-2000:] if ret.stderr else "")
    if TARGETS.exists():
        tt = pd.read_csv(TARGETS)
        cal = tt[tt["use_for_calibration"] == True].sort_values("id")
        # Sentinel: very large residual to signal failure to PEST
        with open(SIM_OUT, "w") as f:
            for _, r in cal.iterrows():
                f.write(f"{r['id']} -999.0\n")
    sys.exit(0)

# ---------------------------------------------------------------------------
# 3. Read sim heads, merge with calibration targets, write PEST output
# ---------------------------------------------------------------------------
heads = pd.read_csv(HEADS_CSV)
targets = pd.read_csv(TARGETS)
cal = targets[targets["use_for_calibration"] == True].sort_values("id")[["id"]]
m = cal.merge(heads[["id", "sim_L2"]], on="id", how="left")

with open(SIM_OUT, "w") as f:
    for _, r in m.iterrows():
        f.write(f"{r['id']} {r['sim_L2']:.6f}\n")
print(f"[PEST forward] Wrote {SIM_OUT.name} with {len(m)} obs")

# Diagnostic: full table with all 20 wells, residual sign convention noted
diag = targets.merge(heads[["id", "sim_L1", "sim_L2", "sim_L3"]], on="id", how="left")
# Sign convention: residual_PEST = obs - sim (PEST standard, positive = sim too low)
diag["residual_PEST"] = diag["obs_used"] - diag["sim_L2"]
diag.to_csv(WORK / "pest_iter_diagnostic.csv", index=False, float_format="%.4f")
print(f"[PEST forward] Wrote diagnostic CSV (residual_PEST = obs - sim_L2)")
