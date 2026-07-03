"""3D SWI Phase 3b — Transient with TVA tide.

Builds on Phase 3a v1 (SS converged) by adding:
 - TDIS: 1 spinup SP + N_TIDAL hourly stress periods
 - TVA package: time-varying saltwater_head (Kuroshima 138-hr × 1.9 scale)
 - Per-period GHB heads (density-corrected freshwater-equivalent)
 - STO storage (Sy, Ss)
 - Warm-start from Phase 3a v1 SS heads + zeta

Env vars:
  N_TIDAL        number of tidal hourly SPs (default 24 = 1 day for quick test)
  SPINUP_HOURS   spinup duration (default 24 hr)
  SPINUP_STEPS   spinup substeps (default 12)
  RUN_TAG        workspace suffix

Outputs:
  phase3b_tidal_<RUN_TAG>/  MF6 files + heads + zeta
"""
import os, sys, io, pathlib, time, json, importlib.util
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import flopy

WORK = pathlib.Path(__file__).resolve().parent
RUN_TAG = os.environ.get("RUN_TAG", "test24")
WS = WORK / f"phase3b_tidal_{RUN_TAG}"; WS.mkdir(exist_ok=True)
WS_3a = WORK / "phase3a_ss"   # warm-start source (v1)
MF6_EXE = str(WORK.parent / "wangi_swi" / "mf6.6.0-SWI-Tides" / "mf6.exe")
assert (WS_3a / "gwf.hds").exists(), f"missing Phase 3a v1 results in {WS_3a}"

# ---- config ----------------------------------------------------------------
spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR, DELC = cfg.NROW, cfg.NCOL, cfg.DELR, cfg.DELC
XUL, YLL = cfg.XUL, cfg.Y_ORIGIN_BOT_LEFT

top = np.load(WORK / "top_elevation.npy").astype(float)
idomain2d = np.load(WORK / "idomain.npy").astype(int)
k1 = np.load(WORK / "k1_field.npy").astype(float)
k2 = np.load(WORK / "k2_field.npy").astype(float)

LAYER1_THICKNESS = 30.0
Z_BASE_L2 = -75.0
Z_BASE_L3 = -500.0
botm1 = top - LAYER1_THICKNESS
botm2 = np.full_like(top, Z_BASE_L2); botm2 = np.minimum(botm2, botm1 - 10.0)
botm3 = np.full_like(top, Z_BASE_L3); botm3 = np.minimum(botm3, botm2 - 10.0)
k_3d = np.stack([k1, k2, k2], axis=0)
idomain = np.stack([idomain2d]*3, axis=0)

# ---- tide series -----------------------------------------------------------
ktide_spec = importlib.util.spec_from_file_location("ktide",
    str(WORK.parent / "wangi_swi" / "_kuroshima_tide.py"))
ktide = importlib.util.module_from_spec(ktide_spec)
ktide_spec.loader.exec_module(ktide)
kuro = np.array(ktide.KUROSHIMA_TIDE)
TIDE_SCALE = float(os.environ.get("TIDE_SCALE", "1.9"))
kuro_c = kuro - kuro.mean()
tide_full = kuro_c * TIDE_SCALE

N_TIDAL = int(os.environ.get("N_TIDAL", "24"))
SPINUP_HOURS = float(os.environ.get("SPINUP_HOURS", "24.0"))
SPINUP_STEPS = int(os.environ.get("SPINUP_STEPS", "12"))
SKIP_TVA = os.environ.get("SKIP_TVA", "0") == "1"
N_TIDAL = min(N_TIDAL, len(tide_full))
tide = tide_full[:N_TIDAL]
print(f"Tide series: {N_TIDAL} hours, range {tide.min():+.2f} .. {tide.max():+.2f} m")
print(f"Spinup: {SPINUP_HOURS:.0f} hr / {SPINUP_STEPS} steps")
print(f"Total NPER = 1 + {N_TIDAL} = {1 + N_TIDAL}")

NPER = 1 + N_TIDAL
# Per-period sea level: SP 1 = 0 (quiet spinup), SP 2..N+1 = tide[0..N-1]
sea_per_sp = np.concatenate([[0.0], tide])

# ---- sim -------------------------------------------------------------------
sim_name = "wangi3d_tide"
gwf_name = "gwf"
sim = flopy.mf6.MFSimulation(sim_ws=str(WS), exe_name=MF6_EXE, sim_name=sim_name)
period_data = [(SPINUP_HOURS, SPINUP_STEPS, 1.0)] + [(1.0, 4, 1.0/4)] * N_TIDAL
flopy.mf6.ModflowTdis(sim, nper=NPER, perioddata=period_data, time_units="HOURS")

flopy.mf6.ModflowIms(
    sim, print_option="SUMMARY", complexity="COMPLEX",
    linear_acceleration="BICGSTAB",
    under_relaxation="DBD",
    under_relaxation_theta=0.7, under_relaxation_kappa=0.08,
    under_relaxation_gamma=0.0, under_relaxation_momentum=0.0,
    backtracking_number=20, backtracking_tolerance=1.1,
    backtracking_reduction_factor=0.3, backtracking_residual_limit=1.0,
    outer_maximum=800, inner_maximum=400,
    outer_dvclose=5e-2, inner_dvclose=5e-3, relaxation_factor=0.97,
)
gwf = flopy.mf6.ModflowGwf(
    sim, modelname=gwf_name, print_input=False, save_flows=True,
    newtonoptions="NEWTON UNDER_RELAXATION",
)
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

# ---- warm-start IC from Phase 3a SS ---------------------------------------
h_warm = flopy.utils.HeadFile(str(WS_3a / "gwf.hds")).get_data(kstpkper=(0, 0))
print(f"Warm-start from Phase 3a SS: L1 {h_warm[0].min():.2f}..{h_warm[0].max():.2f}, "
      f"L2 {h_warm[1].min():.2f}..{h_warm[1].max():.2f}, "
      f"L3 {h_warm[2].min():.2f}..{h_warm[2].max():.2f}")
# Filter sentinels and clip
strt_layers = []
for il in range(3):
    h = h_warm[il].copy()
    h = np.where(np.abs(h) > 1e9, np.maximum(top, 0.5), h)
    h = np.clip(h, 0.1, 20.0)
    strt_layers.append(h)
strt = np.stack(strt_layers, axis=0)
flopy.mf6.ModflowGwfic(gwf, strt=strt)

# ---- STO (transient) -------------------------------------------------------
transient = {iper: True for iper in range(NPER)}
flopy.mf6.ModflowGwfsto(
    gwf, save_flows=True, iconvert=1,
    ss=1e-4, sy=0.10, transient=transient,
)

# ---- OC --------------------------------------------------------------------
flopy.mf6.ModflowGwfoc(
    gwf, head_filerecord=f"{gwf_name}.hds",
    budget_filerecord=f"{gwf_name}.cbc",
    saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")],
)

# ---- RCH (constant land cells) --------------------------------------------
p = pd.read_csv(WORK / "params.csv", index_col=0)
rch_mult = float(p.loc["rch_mult"].iloc[0])
RECHARGE_M_D = (600.0 / 1000.0) / 365.25 * rch_mult
land = idomain2d == 1
rch_spd = [[(0, r, c), RECHARGE_M_D] for r, c in zip(*np.where(land))]
flopy.mf6.ModflowGwfrch(gwf, stress_period_data={0: rch_spd}, pname="rch")
print(f"RCH: {len(rch_spd):,} cells × {RECHARGE_M_D*365.25*1000:.0f} mm/yr")

# ---- GHB per period (density-corrected, sea level varies) ------------------
DENS_RATIO = 0.025
GHB_COND = 5000.0 * DELR * DELC
padded = np.pad(idomain2d, 1, mode="constant", constant_values=0)
is_coast = (idomain2d == 1) & (
    (padded[0:-2, 1:-1] == 0) | (padded[2:, 1:-1] == 0)
    | (padded[1:-1, 0:-2] == 0) | (padded[1:-1, 2:] == 0)
)
SEA_BUFFER = -0.5
coast_cells = list(zip(*np.where(is_coast)))
print(f"Coast cells: {len(coast_cells)}")

HEAD_FLOOR = 0.2   # safety margin above cell bottom; required by MF6
ghb_spd = {}
max_ghb = 0
for iper in range(NPER):
    sea = sea_per_sp[iper]
    data = []
    for r, c in coast_cells:
        # Layer 1: only apply GHB if the cell base actually sits below current sea
        # (avoids unphysical GHB at high-cliff cells dipping below cell bottom at low tide)
        if botm1[r, c] < SEA_BUFFER and top[r, c] < 1.0:
            elev = top[r, c]
            fh = sea + (sea - min(elev, sea)) * DENS_RATIO
            fh = max(fh, botm1[r, c] + HEAD_FLOOR)
            data.append([(0, r, c), fh, GHB_COND])
        if botm2[r, c] < SEA_BUFFER:
            mid = 0.5 * (botm1[r, c] + botm2[r, c])
            fh = sea + (sea - mid) * DENS_RATIO
            fh = max(fh, botm2[r, c] + HEAD_FLOOR)
            data.append([(1, r, c), fh, GHB_COND])
        if botm3[r, c] < SEA_BUFFER:
            mid = 0.5 * (botm2[r, c] + botm3[r, c])
            fh = sea + (sea - mid) * DENS_RATIO
            fh = max(fh, botm3[r, c] + HEAD_FLOOR)
            data.append([(2, r, c), fh, GHB_COND])
    ghb_spd[iper] = data
    max_ghb = max(max_ghb, len(data))
flopy.mf6.ModflowGwfghb(gwf, maxbound=max_ghb,
                         stress_period_data=ghb_spd, pname="ghb")
print(f"GHB: up to {max_ghb} cells/SP × {NPER} SPs")

# ---- write + inject SWI + TVA ---------------------------------------------
sim.write_simulation(silent=True)

ZETA_START = -100.0
if SKIP_TVA:
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
    print("SWI written WITHOUT TVA (skip-tva test mode)")
else:
    (WS / f"{gwf_name}.swi").write_text(
        "BEGIN options\n"
        f"  ZETA  FILEOUT  {gwf_name}.zta\n"
        f"  TVA6  FILEIN   {gwf_name}.swi.tva\n"
        "END options\n\n"
        "BEGIN griddata\n"
        "  zetastrt\n"
        f"    CONSTANT      {ZETA_START:.6f}\n"
        "END griddata\n",
        encoding="utf-8",
    )
    # TVA: saltwater_head per period
    lines = ["BEGIN options", "  auxiliary  saltwater_head", "END options", ""]
    for iper in range(NPER):
        sea = sea_per_sp[iper]
        lines.append(f"BEGIN period  {iper + 1}")
        lines.append("  saltwater_head")
        lines.append(f"    CONSTANT      {sea:.8f}")
        lines.append(f"END period  {iper + 1}")
        lines.append("")
    (WS / f"{gwf_name}.swi.tva").write_text("\n".join(lines), encoding="utf-8")
# Patch NAM
nam_path = WS / f"{gwf_name}.nam"
nam_txt = nam_path.read_text(encoding="utf-8")
if "SWI6" not in nam_txt:
    nam_txt = nam_txt.replace(
        "BEGIN packages",
        "BEGIN packages\n  SWI6  gwf.swi  swi",
        1,
    )
    nam_path.write_text(nam_txt, encoding="utf-8")
print(f"SWI + TVA injected ({NPER} periods)")

# ---- run -------------------------------------------------------------------
print("\n=== Running MF6 3D SWI Phase 3b transient ===")
t0 = time.time()
success, buff = sim.run_simulation(silent=True)
dt = time.time() - t0
print(f"Runtime: {dt:.0f} s ({dt/60:.1f} min)")
print(f"Success: {success}")
if not success:
    for ln in buff[-20:]:
        print(ln)
    sys.exit(1)

# ---- post-process: Kantamare tidal response ----
hds = flopy.utils.HeadFile(str(WS / f"{gwf_name}.hds"))
times = np.array(hds.get_times())
# Find Kantamare row,col from wells
wells = pd.read_csv(WORK / "calibration_targets.csv")
ww4 = wells[wells["id"] == "ww04"].iloc[0]
KANT_R, KANT_C = int(ww4["row"]), int(ww4["col"])
print(f"\nKantamare cell: row={KANT_R}, col={KANT_C}")

heads_kant_L1 = np.array([hds.get_data(totim=t)[0, KANT_R, KANT_C] for t in times])
heads_kant_L2 = np.array([hds.get_data(totim=t)[1, KANT_R, KANT_C] for t in times])
tidal_mask = times > SPINUP_HOURS + 1e-3
print(f"Time records: {len(times)}, tidal phase records: {tidal_mask.sum()}")

for lyr_name, h_series in [("L1", heads_kant_L1), ("L2", heads_kant_L2)]:
    if tidal_mask.sum() < 2:
        continue
    h_tidal = h_series[tidal_mask]
    rng = h_tidal.max() - h_tidal.min()
    sea_rng = tide.max() - tide.min()
    eff = rng / sea_rng if sea_rng > 0 else np.nan
    print(f"  {lyr_name}: tidal range = {rng:.3f} m (sea {sea_rng:.3f}) → efficiency {eff*100:.1f}%")

# Save head time series
ts_df = pd.DataFrame({
    "time_hr": times,
    "head_L1_kant": heads_kant_L1,
    "head_L2_kant": heads_kant_L2,
    "is_tidal_phase": tidal_mask,
})
out_csv = WORK / f"phase3b_kant_ts_{RUN_TAG}.csv"
ts_df.to_csv(out_csv, index=False)
print(f"\nSaved: {out_csv}")

print("\nObserved WW4: range 0.40 m, efficiency 18% (target)")
