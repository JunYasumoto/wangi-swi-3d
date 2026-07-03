"""3D SWI Phase 3a — Steady-state, no tide.

Build the calibrated JpGU 3D model (NLAY=2, K1=marly cap + K2=main aquifer) plus
a NEW deep Layer 3 (-75 to -500 m) holding the saltwater wedge, then run MF6 with
SWI6 to find the equilibrium fresh/salt interface (ζ).

The L3 K = K_L2 (just an extension of the main aquifer). Because the lens stays
mostly in L1+L2 (matching PEST head calibration), adding inactive saltwater depth
below shouldn't shift heads. This is the "minimal-perturbation" approach to get
proper SWI vertical room while preserving the existing calibration.

Reads (from `.`):
  top_elevation.npy, idomain.npy, k1_field.npy, k2_field.npy
  zones.npy, params.csv, zk_values.csv

Outputs (in `./phase3a_ss/`):
  MF6 files (gwf.dis, gwf.npf, gwf.swi, gwf.swi.tva, gwf.hds, gwf.cbc, gwf.zta)
  + `_summary.json` with timing and zeta stats
"""
import os, sys, io, pathlib, time, json
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import flopy
import importlib.util

WORK = pathlib.Path(__file__).resolve().parent
RUN_TAG = os.environ.get("RUN_TAG", "")
WS   = WORK / (f"phase3a_ss{('_' + RUN_TAG) if RUN_TAG else ''}"); WS.mkdir(exist_ok=True)
MF6_EXE = str(WORK.parent / "wangi_swi" / "mf6.6.0-SWI-Tides" / "mf6.exe")
assert pathlib.Path(MF6_EXE).exists(), f"missing MF6: {MF6_EXE}"

# ---- load existing JpGU model assets ---------------------------------------
spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL = cfg.NROW, cfg.NCOL
DELR, DELC = cfg.DELR, cfg.DELC
XUL, YLL = cfg.XUL, cfg.Y_ORIGIN_BOT_LEFT

top      = np.load(WORK / "top_elevation.npy").astype(float)
idomain2d= np.load(WORK / "idomain.npy").astype(int)
k1       = np.load(WORK / "k1_field.npy").astype(float)
K2_FILE  = os.environ.get("K2_FILE", "k2_field.npy")
k2       = np.load(WORK / K2_FILE).astype(float)
print(f"K2 source: {K2_FILE}")
print(f"Grid: {NROW} × {NCOL}  ({NROW*NCOL:,} cells/layer)")
print(f"K1 range: {k1.min():.3g} .. {k1.max():.3g}  median {np.median(k1):.3g}")
print(f"K2 range: {k2.min():.3g} .. {k2.max():.3g}  median {np.median(k2):.3g}")

# ---- Global K2 multiplier (PEST scenario C parameter "k2_global_mult") -----
K2_GLOBAL_MULT = float(os.environ.get("K2_GLOBAL_MULT", "1.0"))
if K2_GLOBAL_MULT != 1.0:
    k2 = k2 * K2_GLOBAL_MULT
    print(f"K2 global multiplier ×{K2_GLOBAL_MULT} applied — new range "
          f"{k2.min():.3g} .. {k2.max():.3g}")

# ---- 3-zone K2 multipliers (PEST scenario A: k2_zones_pest.npy 1=NW/2=CENT/3=SSE) ---
K2_PEST_NW_MULT   = float(os.environ.get("K2_PEST_NW_MULT",   "1.0"))
K2_PEST_CENT_MULT = float(os.environ.get("K2_PEST_CENT_MULT", "1.0"))
K2_PEST_SSE_MULT  = float(os.environ.get("K2_PEST_SSE_MULT",  "1.0"))
if (K2_PEST_NW_MULT != 1.0 or K2_PEST_CENT_MULT != 1.0 or K2_PEST_SSE_MULT != 1.0):
    zfp = WORK / "k2_zones_pest.npy"
    if zfp.exists():
        kzones = np.load(zfp)
        if K2_PEST_NW_MULT != 1.0:
            k2 = np.where(kzones == 1, k2 * K2_PEST_NW_MULT, k2)
            print(f"K2 NW-zone (zone 1) × {K2_PEST_NW_MULT}")
        if K2_PEST_CENT_MULT != 1.0:
            k2 = np.where(kzones == 2, k2 * K2_PEST_CENT_MULT, k2)
            print(f"K2 CENT-zone (zone 2) × {K2_PEST_CENT_MULT}")
        if K2_PEST_SSE_MULT != 1.0:
            k2 = np.where(kzones == 3, k2 * K2_PEST_SSE_MULT, k2)
            print(f"K2 SSE-zone (zone 3) × {K2_PEST_SSE_MULT}")
        print(f"K2 after zonal mults — range {k2.min():.3g} .. {k2.max():.3g}")
    else:
        print(f"WARNING: k2_zones_pest.npy not found, PEST-A K2 multipliers ignored")

# ---- SSE coastal/inland sub-zone K2 (diagnostic: k2_sse_split.npy 31=coastal/32=inland) ---
K2_PEST_SSE_COAST_MULT  = float(os.environ.get("K2_PEST_SSE_COAST_MULT",  "1.0"))
K2_PEST_SSE_INLAND_MULT = float(os.environ.get("K2_PEST_SSE_INLAND_MULT", "1.0"))
if (K2_PEST_SSE_COAST_MULT != 1.0 or K2_PEST_SSE_INLAND_MULT != 1.0):
    sfp = WORK / "k2_sse_split.npy"
    if sfp.exists():
        ssplit = np.squeeze(np.load(sfp))
        if K2_PEST_SSE_COAST_MULT != 1.0:
            k2 = np.where(ssplit == 31, k2 * K2_PEST_SSE_COAST_MULT, k2)
            print(f"K2 SSE-coastal (zone 31) × {K2_PEST_SSE_COAST_MULT}")
        if K2_PEST_SSE_INLAND_MULT != 1.0:
            k2 = np.where(ssplit == 32, k2 * K2_PEST_SSE_INLAND_MULT, k2)
            print(f"K2 SSE-inland (zone 32) × {K2_PEST_SSE_INLAND_MULT}")
        print(f"K2 after SSE split — range {k2.min():.3g} .. {k2.max():.3g}")
    else:
        print(f"WARNING: k2_sse_split.npy not found, SSE split multipliers ignored")

# ---- Optional NW-zone K2/K1 multiplier (zone 1 in zones_3zone.npy) ---------
K2_NW_MULT = float(os.environ.get("K2_NW_MULT", "1.0"))
K1_NW_MULT = float(os.environ.get("K1_NW_MULT", "1.0"))
if (K2_NW_MULT != 1.0 or K1_NW_MULT != 1.0):
    zfp = WORK / "zones_3zone.npy"
    if zfp.exists():
        zones_nw = np.load(zfp)
        nw_mask = (zones_nw == 1)
        if K2_NW_MULT != 1.0:
            k2 = np.where(nw_mask, k2 * K2_NW_MULT, k2)
            print(f"NW-zone K2 multiplier ×{K2_NW_MULT} applied to {nw_mask.sum():,} cells")
        if K1_NW_MULT != 1.0:
            k1 = np.where(nw_mask, k1 * K1_NW_MULT, k1)
            print(f"NW-zone K1 multiplier ×{K1_NW_MULT} applied to {nw_mask.sum():,} cells")
    else:
        print(f"WARNING: zones_3zone.npy not found, NW-zone K multipliers ignored")

# ---- 3-layer geometry ------------------------------------------------------
LAYER1_THICKNESS = 30.0
Z_BASE_L2 = -75.0
Z_BASE_L3 = float(os.environ.get("BOTM_L3", "-500.0"))
botm1 = top - LAYER1_THICKNESS
botm2 = np.full_like(top, Z_BASE_L2)
botm2 = np.minimum(botm2, botm1 - 10.0)
botm3 = np.full_like(top, Z_BASE_L3)
botm3 = np.minimum(botm3, botm2 - 10.0)
print(f"L1: top..top-{LAYER1_THICKNESS:.0f}, L2: ..{Z_BASE_L2:.0f}, L3: ..{Z_BASE_L3:.0f} m")

# K stack: L3 = same K as L2 (extension of main aquifer)
k_3d = np.stack([k1, k2, k2], axis=0)

# idomain stack: all 3 layers share 2D mask
idomain = np.stack([idomain2d, idomain2d, idomain2d], axis=0)

# ---- build simulation ------------------------------------------------------
sim_name = "wangi3d"
gwf_name = "gwf"

sim = flopy.mf6.MFSimulation(sim_ws=str(WS), exe_name=MF6_EXE, sim_name=sim_name)
# Single SS stress period
flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)], time_units="DAYS")

ims = flopy.mf6.ModflowIms(
    sim,
    print_option="SUMMARY",
    complexity="COMPLEX",
    linear_acceleration="BICGSTAB",
    under_relaxation="DBD",
    under_relaxation_theta=0.7,
    under_relaxation_kappa=0.08,
    under_relaxation_gamma=0.0,
    under_relaxation_momentum=0.0,
    backtracking_number=20,
    backtracking_tolerance=1.1,
    backtracking_reduction_factor=0.3,
    backtracking_residual_limit=0.5,
    outer_maximum=800,
    inner_maximum=400,
    outer_dvclose=5e-3,
    inner_dvclose=5e-4,
    relaxation_factor=0.97,
)
gwf = flopy.mf6.ModflowGwf(
    sim, modelname=gwf_name, print_input=False, save_flows=True,
    newtonoptions="NEWTON UNDER_RELAXATION",
)
sim.register_ims_package(ims, [gwf_name])

flopy.mf6.ModflowGwfdis(
    gwf, nlay=3, nrow=NROW, ncol=NCOL,
    delr=DELR, delc=DELC, top=top,
    botm=np.stack([botm1, botm2, botm3], axis=0),
    idomain=idomain, xorigin=XUL, yorigin=YLL,
)
flopy.mf6.ModflowGwfnpf(
    gwf, icelltype=[1, 1, 1], k=k_3d, k33=k_3d / 10.0,
    save_specific_discharge=True,
)

# Warm start IC priority:
#   (1) warmstart_base.hds — the converged base (all-K2=1.0) 3-layer solution.
#       Used during PEST so each perturbed forward starts near the base solution;
#       a small K perturbation then stays in the convergent basin instead of
#       diverging at high-K cells (e.g. SSE zone, K2~53 m/d).
#   (2) JPGU heads (coarse 2-layer prior model).
#   (3) cold start.
BASE_WARM = WORK / "warmstart_base.hds"
JPGU_HDS = WORK.parent / "wangi_jpgu2026" / "wangi.hds"
if BASE_WARM.exists():
    hw = flopy.utils.HeadFile(str(BASE_WARM)).get_data(kstpkper=(0, 0))
    # Filter HDRY/HNOFLO sentinel (1e30) only; base heads are already physical.
    hb = [np.where(np.abs(hw[k]) > 1e9, np.maximum(top, 0.5), hw[k])
          for k in range(hw.shape[0])]
    strt = np.stack(hb, axis=0)
    print(f"Warm-start from base solution (warmstart_base.hds) — "
          f"L1 {strt[0].min():.2f}..{strt[0].max():.2f}, "
          f"L2 {strt[1].min():.2f}..{strt[1].max():.2f}, "
          f"L3 {strt[2].min():.2f}..{strt[2].max():.2f}")
elif JPGU_HDS.exists():
    h_warm = flopy.utils.HeadFile(str(JPGU_HDS)).get_data(kstpkper=(0, 0))
    # Filter out HDRY/HNOFLO sentinel (1e30): replace with safe defaults
    h1 = np.where(np.abs(h_warm[0]) > 1e9, np.maximum(top, 0.5), h_warm[0])
    h2 = np.where(np.abs(h_warm[1]) > 1e9, np.maximum(top, 0.5), h_warm[1])
    # Clip to physically reasonable range to avoid stuck Newton
    h1 = np.clip(h1, 0.1, 20.0)
    h2 = np.clip(h2, 0.1, 20.0)
    strt = np.stack([h1, h2, h2], axis=0)
    print(f"Warm-start (filtered) — L1 range {h1.min():.2f}..{h1.max():.2f}, L2 {h2.min():.2f}..{h2.max():.2f}")
else:
    strt_init = np.where(top > 0, 0.5 * top, 0.5)
    strt_init = np.clip(strt_init, 0.1, 20.0)
    strt = np.stack([strt_init, strt_init, strt_init], axis=0)
    print("Cold start from 0.5 × top (clipped)")
flopy.mf6.ModflowGwfic(gwf, strt=strt)

flopy.mf6.ModflowGwfsto(
    gwf, save_flows=True, iconvert=1,
    ss=1e-4, sy=0.10, steady_state={0: True},
)

flopy.mf6.ModflowGwfoc(
    gwf,
    head_filerecord=f"{gwf_name}.hds",
    budget_filerecord=f"{gwf_name}.cbc",
    saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")],
)

# ---- RCH (L1 land cells) ---------------------------------------------------
p = pd.read_csv(WORK / "params.csv", index_col=0)
rch_mult = float(p.loc["rch_mult"].iloc[0])
RECHARGE_M_D = (600.0 / 1000.0) / 365.25 * rch_mult
land = idomain2d == 1
# Per-cell recharge multiplier field: global rch_mult (already in RECHARGE_M_D)
# combined with optional zonal multipliers (NW via zones_3zone.npy zone 1,
# CENT via k2_zones_pest.npy zone 2 — PEST scenario D for the CENT structural residual).
RCH_NW_MULT   = float(os.environ.get("RCH_NW_MULT",   "1.0"))
RCH_CENT_MULT = float(os.environ.get("RCH_CENT_MULT", "1.0"))
rmult2d = np.ones((NROW, NCOL), float)
if RCH_NW_MULT != 1.0 and (WORK / "zones_3zone.npy").exists():
    nw_mask2d = (np.load(WORK / "zones_3zone.npy") == 1)
    rmult2d = np.where(nw_mask2d, rmult2d * RCH_NW_MULT, rmult2d)
    print(f"RCH NW-zone (zones_3zone==1) ×{RCH_NW_MULT}, {int(nw_mask2d[land].sum()):,} land cells")
if RCH_CENT_MULT != 1.0 and (WORK / "k2_zones_pest.npy").exists():
    cent_mask2d = (np.squeeze(np.load(WORK / "k2_zones_pest.npy")) == 2)
    rmult2d = np.where(cent_mask2d, rmult2d * RCH_CENT_MULT, rmult2d)
    print(f"RCH CENT-zone (k2_zones_pest==2) ×{RCH_CENT_MULT}, {int(cent_mask2d[land].sum()):,} land cells")
rch_spd = [[(0, r, c), RECHARGE_M_D * rmult2d[r, c]] for r, c in zip(*np.where(land))]
print(f"RCH: {len(rch_spd):,} cells × {RECHARGE_M_D*365.25*1000:.0f} mm/yr base "
      f"(global ×{rch_mult}, NW ×{RCH_NW_MULT}, CENT ×{RCH_CENT_MULT})")
flopy.mf6.ModflowGwfrch(gwf, stress_period_data={0: rch_spd}, pname="rch")

# ---- GHB at coast (density-corrected freshwater-equivalent, scenario-aware) ---
# Phase 3c sensitivity: scale L1/L2/L3 conductance independently, optionally skip layers.
DENS_RATIO = 0.025
GHB_COND_MULT_GLOBAL = float(os.environ.get("GHB_COND_MULT", "1.0"))
GHB_COND_BASE = 5000.0 * DELR * DELC * GHB_COND_MULT_GLOBAL   # 4.5e6 m²/d × global multiplier
print(f"GHB base cond = {GHB_COND_BASE:.2e} m²/d (global mult ×{GHB_COND_MULT_GLOBAL})")
GHB_L1_MULT = float(os.environ.get("GHB_L1_MULT", "1.0"))
GHB_L2_MULT = float(os.environ.get("GHB_L2_MULT", "1.0"))
GHB_L3_MULT = float(os.environ.get("GHB_L3_MULT", "1.0"))
SKIP_L1 = os.environ.get("SKIP_L1_GHB", "0") == "1"
SKIP_L3 = os.environ.get("SKIP_L3_GHB", "0") == "1"
USE_DENSITY_GHB = os.environ.get("USE_DENSITY_GHB", "1") == "1"
# Per-layer density toggles (override the global if explicitly set)
L1_DENSITY = os.environ.get("L1_DENSITY", "1") == "1"
L2_DENSITY = os.environ.get("L2_DENSITY", "1") == "1"
L3_DENSITY = os.environ.get("L3_DENSITY", "1") == "1"
print(f"GHB scenario: L1×{GHB_L1_MULT}{' (skip)' if SKIP_L1 else ''}, "
      f"L2×{GHB_L2_MULT}, L3×{GHB_L3_MULT}{' (skip)' if SKIP_L3 else ''}, "
      f"density={'ON' if USE_DENSITY_GHB else 'OFF'}")

padded = np.pad(idomain2d, 1, mode="constant", constant_values=0)
is_coast = (idomain2d == 1) & (
    (padded[0:-2, 1:-1] == 0) | (padded[2:, 1:-1] == 0)
    | (padded[1:-1, 0:-2] == 0) | (padded[1:-1, 2:] == 0)
)
SEA_BUFFER = -0.5
SEA_LEVEL = 0.0
HEAD_FLOOR = 0.2
ghb_spd = []
for r, c in zip(*np.where(is_coast)):
    if (not SKIP_L1) and botm1[r, c] < SEA_BUFFER and top[r, c] < 1.0:
        elev = top[r, c]
        if USE_DENSITY_GHB and L1_DENSITY:
            fh = SEA_LEVEL + (SEA_LEVEL - min(elev, 0.0)) * DENS_RATIO
        else:
            fh = SEA_LEVEL
        fh = max(fh, botm1[r, c] + HEAD_FLOOR)
        ghb_spd.append([(0, r, c), fh, GHB_COND_BASE * GHB_L1_MULT])
    if botm2[r, c] < SEA_BUFFER:
        mid_L2 = 0.5 * (botm1[r, c] + botm2[r, c])
        if USE_DENSITY_GHB and L2_DENSITY:
            fh = SEA_LEVEL + (SEA_LEVEL - mid_L2) * DENS_RATIO
        else:
            fh = SEA_LEVEL
        fh = max(fh, botm2[r, c] + HEAD_FLOOR)
        ghb_spd.append([(1, r, c), fh, GHB_COND_BASE * GHB_L2_MULT])
    if (not SKIP_L3) and botm3[r, c] < SEA_BUFFER:
        mid_L3 = 0.5 * (botm2[r, c] + botm3[r, c])
        if USE_DENSITY_GHB and L3_DENSITY:
            fh = SEA_LEVEL + (SEA_LEVEL - mid_L3) * DENS_RATIO
        else:
            fh = SEA_LEVEL
        fh = max(fh, botm3[r, c] + HEAD_FLOOR)
        ghb_spd.append([(2, r, c), fh, GHB_COND_BASE * GHB_L3_MULT])
flopy.mf6.ModflowGwfghb(gwf, maxbound=len(ghb_spd),
                         stress_period_data={0: ghb_spd}, pname="ghb")
print(f"GHB: {len(ghb_spd):,} cells")

# ---- write base sim --------------------------------------------------------
print("\nWriting MF6 input files ...")
sim.write_simulation(silent=True)

# ---- inject SWI6 -----------------------------------------------------------
ZETA_START = float(os.environ.get("ZETA_START", "-100.0"))
(WS / f"{gwf_name}.swi").write_text(
    "BEGIN options\n"
    f"  ZETA  FILEOUT  {gwf_name}.zta\n"
    "END options\n\n"
    "BEGIN griddata\n"
    "  zetastrt\n"
    f"    CONSTANT      {ZETA_START:.6f}\n"
    "END griddata\n",
    encoding="utf-8",
)
nam_path = WS / f"{gwf_name}.nam"
nam_txt = nam_path.read_text(encoding="utf-8")
if "SWI6" not in nam_txt:
    nam_txt = nam_txt.replace(
        "BEGIN packages",
        "BEGIN packages\n  SWI6  gwf.swi  swi",
        1,
    )
    nam_path.write_text(nam_txt, encoding="utf-8")
print(f"SWI6 injected (ζ_start = {ZETA_START} m)")

# ---- run -------------------------------------------------------------------
print("\n=== Running MF6 (3D SWI Phase 3a SS) ===")
t0 = time.time()
success, buff = sim.run_simulation(silent=True)
dt = time.time() - t0
print(f"Runtime: {dt:.1f} s ({dt/60:.1f} min)")
print(f"Success: {success}")
if not success:
    print("--- last 30 lines of MF6 output ---")
    for ln in buff[-30:]:
        print(ln)
    sys.exit(1)

# ---- post-process ----------------------------------------------------------
hds = flopy.utils.HeadFile(str(WS / f"{gwf_name}.hds")).get_data(kstpkper=(0, 0))
print(f"\nHead summary (L1, L2, L3):")
for ilay, name in enumerate(["L1 (cap)", "L2 (main)", "L3 (deep)"]):
    h = hds[ilay]
    h_valid = h[np.isfinite(h) & (h > -1e9) & (h < 1e9)]
    print(f"  {name}: min {h_valid.min():.2f}  max {h_valid.max():.2f}  mean {h_valid.mean():.2f} m")

zta_path = WS / f"{gwf_name}.zta"
if zta_path.exists():
    zta = flopy.utils.binaryfile.HeadFile(str(zta_path), text="ZETA").get_data(kstpkper=(0, 0))
    print(f"\nZeta (fresh/salt interface) summary:")
    for ilay, name in enumerate(["L1", "L2", "L3"]):
        z = zta[ilay]
        z_valid = z[np.isfinite(z) & (z > -1e9) & (z < 1e9)]
        print(f"  {name}: min {z_valid.min():.2f}  max {z_valid.max():.2f}  mean {z_valid.mean():.2f} m")

# ---- compare to PEST heads at wells ----------------------------------------
wells = pd.read_csv(WORK / "calibration_targets.csv")
wc = pd.read_csv(WORK / "well_cells.csv")[["id", "model_row", "model_col"]]
wells = wells.merge(wc, on="id", how="left")
# Perched wells per memory: ww10, ww14, ww16
# All other regional wells are screened in main aquifer (L2) per well_classification.csv
PERCHED = {"ww10", "ww14", "ww16"}
sim_heads = []
for _, w in wells.iterrows():
    r, c = int(w["model_row"]), int(w["model_col"])
    h1 = float(hds[0, r, c])
    h2 = float(hds[1, r, c])
    h3 = float(hds[2, r, c])
    is_perched = w["id"] in PERCHED
    # Regional wells are open / screened in the main aquifer (L2) — always compare to L2 head.
    # For dry L2 (high ground / deep water table), fall back to L3.
    if is_perched:
        # perched well — compare to L1 (the trapped lens)
        h = h1 if (h1 > botm1[r, c] and -1e9 < h1 < 1e9) else h2
    else:
        # regional / main aquifer well — always use L2 (the screened layer)
        if -1e9 < h2 < 1e9 and h2 > botm2[r, c]:
            h = h2
        elif -1e9 < h3 < 1e9:
            h = h3
        else:
            h = h1   # last resort
    obs = float(w.get("obs_head", w.get("head_obs", np.nan)))
    sim_heads.append({
        "id": w["id"], "obs": obs,
        "sim_L1": h1, "sim_L2": h2, "sim_L3": h3,
        "sim_used": h, "resid": h - obs,
        "perched": is_perched, "dry": abs(h) < 1e-3,
    })
res_df = pd.DataFrame(sim_heads)
out_heads = WORK / f"phase3a_heads{('_' + RUN_TAG) if RUN_TAG else ''}.csv"
res_df.to_csv(out_heads, index=False)
print(f"\nWell head comparison (n={len(res_df)}):")
print(res_df.to_string(index=False))

# RMSE with progressive filtering
rmse_all = float(np.sqrt(np.nanmean(res_df["resid"]**2)))
no_perched = res_df[~res_df["perched"]]
rmse_no_perched = float(np.sqrt(np.nanmean(no_perched["resid"]**2)))
no_perched_no_dry = no_perched[~no_perched["dry"]]
rmse_clean = float(np.sqrt(np.nanmean(no_perched_no_dry["resid"]**2)))
mean_bias_clean = float(no_perched_no_dry["resid"].mean())
print(f"\nRMSE all wells (n={len(res_df)})              = {rmse_all:.3f} m")
print(f"RMSE excl. perched (n={len(no_perched)})       = {rmse_no_perched:.3f} m")
print(f"RMSE clean (excl. perched+dry, n={len(no_perched_no_dry)}) = {rmse_clean:.3f} m")
print(f"Mean bias (clean)                          = {mean_bias_clean:+.3f} m   ← target ~0")
print(f"(PEST baseline freshwater-only RMSE ≈ 2.53 m)")

summary = dict(
    run_tag=RUN_TAG,
    runtime_sec=round(dt, 1),
    success=bool(success),
    rmse_all=rmse_all,
    rmse_no_perched=rmse_no_perched,
    rmse_clean=rmse_clean,
    mean_bias_clean=mean_bias_clean,
    n_wells_all=len(res_df),
    n_wells_clean=len(no_perched_no_dry),
    ghb_l1_mult=GHB_L1_MULT,
    ghb_l2_mult=GHB_L2_MULT,
    ghb_l3_mult=GHB_L3_MULT,
    skip_l1_ghb=SKIP_L1,
    skip_l3_ghb=SKIP_L3,
    use_density_ghb=USE_DENSITY_GHB,
    botm_l3=Z_BASE_L3,
)
out_json = WORK / f"phase3a_summary{('_' + RUN_TAG) if RUN_TAG else ''}.json"
out_json.write_text(json.dumps(summary, indent=2))
print(f"\nSaved: {out_json}")
