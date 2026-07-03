"""Generate PEST control / template / instruction files.

Scenario selectable via SCENARIO variable:
  "C" — 2 params (rch_mult, k2_global_mult). Diagnostic only.
  "A" — 3 params (k2_nw, k2_cent, k2_sse). rch_mult fixed at 1.0.
  "B" — 4 params (rch_mult + 3 zone K2). Reserved for next step.

Constraints (per 2026-06-09 user spec for A):
  - log-scale multipliers
  - bounds 0.5 .. 2.0
  - initial 1.0
  - lambda initial = 10
  - NOPTMAX = 3
  - obs groups match spatial K2 zones (NW, CENT, SSE, other)
  - ww01/14/16 diagnostic-only (excluded), ww10 weight 0.1
  - residual convention: PEST standard, residual = obs - sim

Outputs:
  pest_params.csv.tpl
  pest_params.csv
  sim_heads_pest.ins
  pest.pst
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import numpy as np
import pandas as pd

SCENARIO = os.environ.get("SCENARIO", "A").upper()
WORK = pathlib.Path(__file__).resolve().parent
TARGETS = pd.read_csv(WORK / "calibration_targets_corrected.csv")
WCELLS  = pd.read_csv(WORK / "well_cells.csv")[["id", "model_row", "model_col"]]

print(f"Scenario: {SCENARIO}")

# Spatial zone assignment using k2_zones_pest.npy
KZONES = np.load(WORK / "k2_zones_pest.npy")
def well_zone(wid):
    w = WCELLS[WCELLS["id"] == wid]
    if len(w) == 0: return 0
    r, c = int(w["model_row"].iloc[0]), int(w["model_col"].iloc[0])
    return int(KZONES[r, c])

ZONE_LABEL = {1: "obs_nw", 2: "obs_cent", 3: "obs_sse", 0: "obs_inactive"}

CAL = TARGETS[TARGETS["use_for_calibration"] == True].sort_values("id").reset_index(drop=True)
CAL["k2_zone"] = CAL["id"].apply(well_zone)
CAL["obs_group"] = CAL["k2_zone"].map(ZONE_LABEL)
# ww10 is anomaly: separate group for clarity
CAL.loc[CAL["id"] == "ww10", "obs_group"] = "obs_other"

print(f"Calibration set: {len(CAL)} wells")
print(CAL[["id", "obs_used", "weight", "k2_zone", "obs_group"]].to_string(index=False))

# ---------------------------------------------------------------------------
# 1. Define parameters by scenario
# ---------------------------------------------------------------------------
if SCENARIO == "C":
    PARAMS = [
        # name, init, lower, upper, group
        ("rch_mult",       1.0, 0.30, 3.00, "pg_rch"),
        ("k2_global_mult", 1.0, 0.10, 10.0, "pg_k2"),
    ]
    NOPTMAX = 1
    LAMBDA_INIT = 5.0
elif SCENARIO == "A":
    PARAMS = [
        ("k2_nw",   1.0, 0.5, 2.0, "pg_k2"),
        ("k2_cent", 1.0, 0.5, 2.0, "pg_k2"),
        ("k2_sse",  1.0, 0.5, 2.0, "pg_k2"),
    ]
    NOPTMAX = 3
    LAMBDA_INIT = 10.0
elif SCENARIO == "B":
    PARAMS = [
        ("rch_mult", 1.0, 0.5, 2.0, "pg_rch"),
        ("k2_nw",    1.0, 0.5, 2.0, "pg_k2"),
        ("k2_cent",  1.0, 0.5, 2.0, "pg_k2"),
        ("k2_sse",   1.0, 0.5, 2.0, "pg_k2"),
    ]
    NOPTMAX = 3
    LAMBDA_INIT = 10.0
else:
    raise ValueError(f"Unknown SCENARIO={SCENARIO}")

# ---------------------------------------------------------------------------
# 2. Template + initial values
# ---------------------------------------------------------------------------
TPL = WORK / "pest_params.csv.tpl"
INIT = WORK / "pest_params.csv"
tpl_lines = ["ptf $", "name,value"]
init_lines = ["name,value"]
for name, init, *_ in PARAMS:
    tag = name[:9].ljust(9)
    tpl_lines.append(f"{name},${tag}$")
    init_lines.append(f"{name},{init}")
TPL.write_text("\n".join(tpl_lines) + "\n")
INIT.write_text("\n".join(init_lines) + "\n")
print(f"\nWrote {TPL.name}, {INIT.name}")

# ---------------------------------------------------------------------------
# 3. Instruction file (one well per line, alphabetical)
# ---------------------------------------------------------------------------
INS = WORK / "sim_heads_pest.ins"
ins_lines = ["pif #"]
for _, r in CAL.iterrows():
    ins_lines.append(f"l1 w !{r['id']}_h!")
INS.write_text("\n".join(ins_lines) + "\n")
print(f"Wrote {INS.name} ({len(CAL)} obs)")

# ---------------------------------------------------------------------------
# 4. PEST control file
# ---------------------------------------------------------------------------
NPAR = len(PARAMS)
NOBS = len(CAL)
PAR_GROUPS = sorted({p[4] for p in PARAMS})
OBS_GROUPS = sorted(CAL["obs_group"].unique())

pst = []
pst.append("pcf")
pst.append("* control data")
pst.append("restart estimation")
pst.append(f"   {NPAR}   {NOBS}     {len(PAR_GROUPS)}     0    {len(OBS_GROUPS)}")
pst.append("    1     1 single point 1 0 0")
# RLAMBDA1 RLAMFAC PHIRATSUF PHIREDLAM NUMLAM
pst.append(f"  {LAMBDA_INIT:.1f}  -3.0   0.3  0.03    7")
pst.append("  3.0   3.0 0.001")
pst.append("  0.1")
pst.append(f" {NOPTMAX}  0.005  4  4  0.005  4")
pst.append(" 1  1  1")
pst.append("* parameter groups")
for g in PAR_GROUPS:
    pst.append(f"{g}    relative 0.01  0.0  switch  2.0 parabolic")
pst.append("* parameter data")
# name PARTRANS PARCHGLIM PARVAL1 PARLBND PARUBND PARGP SCALE OFFSET DERCOM
for name, init, lo, hi, grp in PARAMS:
    pst.append(f"{name:<14} log   factor   {init:.4f}  {lo:.4f}  {hi:.4f}   {grp}  1.0  0.0  1")
pst.append("* observation groups")
for g in OBS_GROUPS:
    pst.append(g)
pst.append("* observation data")
for _, r in CAL.iterrows():
    pst.append(f"{r['id']}_h     {float(r['obs_used']):>14.4f}{float(r['weight']):>10.3f}  {r['obs_group']}")
pst.append("* model command line")
pst.append("C:\\anaconda3\\python.exe Phase3c_PEST_forward.py")
pst.append("* model input/output")
pst.append("pest_params.csv.tpl  pest_params.csv")
pst.append("sim_heads_pest.ins   sim_heads_pest.txt")
# pestpp options
pst.append("++lambdas(10,100,1000)")
pst.append("++forgive_unknown_args(true)")

PST = WORK / "pest.pst"
PST.write_text("\n".join(pst) + "\n")
print(f"Wrote {PST.name}\n")
print("=== PST preview ===")
print("\n".join(pst[:30]))
print("...")
print("\n".join(pst[-15:]))
