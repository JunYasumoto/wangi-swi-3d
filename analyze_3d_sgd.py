"""Extract SGD from validated 3D SWI Phase 3b transient run.

Reads gwf.cbc, identifies coastal GHB outflow per cell, aggregates by:
 (1) Island totals (steady spinup-final + tidal-mean)
 (2) Azimuthal sectors (12 × 30°) from highland pivot
 (3) Per-coast region (W, E, N, S quadrants)
 (4) West coast EPS zone (553-558 km E × 9408.5-9420 km N)

Compare against:
 - JpGU 3D freshwater SGD = 3.06e5 m³/d
 - 1D multi-transect (over-estimated 7.34e5) — to show correction
 - Mass balance (RCH × island area = 2.55e5)
"""
import sys, io, pathlib, importlib.util, json
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import flopy

WORK = pathlib.Path(__file__).resolve().parent
WS = WORK / "phase3b_tidal_notva_full138_v2"
FIGDIR = WORK / "figs"; FIGDIR.mkdir(exist_ok=True)
SPINUP_HOURS = 24.0

spec = importlib.util.spec_from_file_location("cfg", str(WORK / "model_config.py"))
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
NROW, NCOL, DELR, DELC = cfg.NROW, cfg.NCOL, cfg.DELR, cfg.DELC
XUL, YLL = cfg.XUL, cfg.Y_ORIGIN_BOT_LEFT
YUL = cfg.YUL

# Pivot (highland peak)
top_arr = np.load(WORK / "top_elevation.npy")
idomain2d = np.load(WORK / "idomain.npy")
top_land = np.where(idomain2d == 1, top_arr, -np.inf)
pivot_idx = np.unravel_index(np.argmax(top_land), top_land.shape)
PIVOT_R, PIVOT_C = pivot_idx
PIVOT_X = XUL + (PIVOT_C + 0.5) * DELR
PIVOT_Y = YUL - (PIVOT_R + 0.5) * DELC
print(f"Highland pivot: row={PIVOT_R}, col={PIVOT_C}, UTM ({PIVOT_X:.0f}, {PIVOT_Y:.0f}), elev={top_arr[PIVOT_R,PIVOT_C]:.0f}m")

# ---- read GHB cells / fluxes -----------------------------------------------
try:
    cbc = flopy.utils.CellBudgetFile(str(WS / "gwf.cbc"), precision="double")
except Exception as e:
    print(f"double precision read failed: {e}")
    print("Trying single precision ...")
    cbc = flopy.utils.CellBudgetFile(str(WS / "gwf.cbc"), precision="single")
times = np.array(cbc.get_times())
print(f"CBC has {len(times)} time records, span {times[0]:.1f} .. {times[-1]:.1f} hr")

# Spinup-final (≤ SPINUP_HOURS)
spin_mask_t = times <= SPINUP_HOURS + 1e-3
spin_end_t = times[spin_mask_t][-1]
tidal_t = times[~spin_mask_t]
print(f"Spinup-final at t={spin_end_t:.1f} hr, tidal n={len(tidal_t)}")


def read_ghb_per_cell(t):
    """Return dict: (lay,row,col) -> q (m³/d, negative = out)."""
    recs = cbc.get_data(text="GHB", totim=t)[0]
    d = {}
    NLAY = 3
    cells_per_layer = NROW * NCOL
    for r in recs:
        node = r['node'] - 1  # 0-based
        lay = node // cells_per_layer
        rem = node % cells_per_layer
        row = rem // NCOL
        col = rem % NCOL
        d[(lay, row, col)] = float(r['q'])
    return d


print("Reading spinup-final fluxes ...")
ghb_spin = read_ghb_per_cell(spin_end_t)
print(f"  {len(ghb_spin)} GHB cells at t={spin_end_t:.1f}")

print(f"Reading tidal-mean fluxes (averaging {len(tidal_t)} time records) ...")
ghb_tidal_sum = {}
ghb_tidal_count = {}
for ti, t in enumerate(tidal_t):
    d = read_ghb_per_cell(t)
    for k, q in d.items():
        if k not in ghb_tidal_sum:
            ghb_tidal_sum[k] = 0.0; ghb_tidal_count[k] = 0
        ghb_tidal_sum[k] += q; ghb_tidal_count[k] += 1
ghb_tidal_mean = {k: ghb_tidal_sum[k] / ghb_tidal_count[k] for k in ghb_tidal_sum}
print(f"  {len(ghb_tidal_mean)} unique GHB cells across tidal phase")

cbc.close()

# ---- assemble per-cell table ----------------------------------------------
all_keys = set(ghb_spin.keys()) | set(ghb_tidal_mean.keys())
rows = []
for (lay, row, col) in all_keys:
    x = XUL + (col + 0.5) * DELR
    y = YUL - (row + 0.5) * DELC
    dx = x - PIVOT_X; dy = y - PIVOT_Y
    az = np.degrees(np.arctan2(dx, dy)) % 360
    dist = np.hypot(dx, dy)
    q_s = ghb_spin.get((lay, row, col), 0.0)
    q_t = ghb_tidal_mean.get((lay, row, col), 0.0)
    rows.append(dict(
        layer=lay, row=row, col=col,
        easting=x, northing=y,
        azim_from_pivot=az, dist_from_pivot=dist,
        q_steady=q_s,           # signed: negative = OUT (SGD), positive = IN (recirc)
        q_tidal_mean=q_t,
        out_steady=max(-q_s, 0.0),
        in_steady=max(q_s, 0.0),
        net_steady=-q_s,        # positive = net OUT (real SGD direction)
        out_tidal_mean=max(-q_t, 0.0),
        in_tidal_mean=max(q_t, 0.0),
        net_tidal_mean=-q_t,
    ))
cells = pd.DataFrame(rows)
# Per-(row,col) net across all 3 layers — this is the TRUE SGD at each coast pixel
# (collapses salt-circulation between L2 and L3 into net freshwater flow)
net_2d = cells.groupby(["row", "col", "easting", "northing"]).agg(
    net_steady_sum=("net_steady", "sum"),
    net_tidal_sum=("net_tidal_mean", "sum"),
    out_steady_sum=("out_steady", "sum"),
    in_steady_sum=("in_steady", "sum"),
).reset_index()
# Map azim back to (row, col)
def coords_to_az(r, c):
    x = XUL + (c + 0.5) * DELR; y = YUL - (r + 0.5) * DELC
    return np.degrees(np.arctan2(x - PIVOT_X, y - PIVOT_Y)) % 360
net_2d["azim_from_pivot"] = net_2d.apply(lambda r: coords_to_az(r["row"], r["col"]), axis=1)
# net_steady_positive = real SGD (outflow); negative = real saltwater inflow (artifact)
net_2d["sgd_net_steady"]    = net_2d["net_steady_sum"].clip(lower=0)
net_2d["sgd_net_tidal_mean"] = net_2d["net_tidal_sum"].clip(lower=0)
print(f"Total GHB cell-layer records: {len(cells)}")
print(f"Coast pixels (2D): {len(net_2d)}")
print(f"  pixels with net OUT (real SGD)  : {(net_2d['net_steady_sum'] > 0).sum()}")
print(f"  pixels with net IN  (artifact)  : {(net_2d['net_steady_sum'] < 0).sum()}")

# ---- island-scale totals ---------------------------------------------------
JPGU_3D = 3.06e5
RCH_TOTAL = (600.0 / 1000.0) / 365.25 * 155e6   # 600 mm/yr × 155 km²
print("\n" + "=" * 78)
print("ISLAND-SCALE SGD TOTALS (3D SWI, validated by tidal efficiency 20.3% ≈ 18% obs)")
print("=" * 78)
print("\nRAW LAYER-BY-LAYER (includes SWI salt-circulation between L2 and L3):")
totals = {}
for label, col in [("Steady GHB out (raw)", "out_steady"),
                    ("Steady GHB in  (raw)", "in_steady"),
                    ("Tidal-mean GHB out (raw)",   "out_tidal_mean"),
                    ("Tidal-mean GHB in  (raw)", "in_tidal_mean")]:
    total = cells[col].sum()
    totals[label] = total
    print(f"  {label:38s}: {total:10.3e} m³/d")
# True SGD = NET outflow per coast pixel (collapses L2-L3 circulation)
true_sgd_steady = net_2d["sgd_net_steady"].sum()
true_sgd_tidal  = net_2d["sgd_net_tidal_mean"].sum()
totals["TRUE Steady SGD (net)"] = true_sgd_steady
totals["TRUE Tidal-mean SGD (net)"] = true_sgd_tidal
print(f"\nTRUE SGD (NET per coast pixel, salt-circulation cancelled):")
print(f"  Steady SGD (net out)                  : {true_sgd_steady:10.3e} m³/d")
print(f"  Tidal-mean SGD (net out)              : {true_sgd_tidal:10.3e} m³/d")
print(f"\nReference values:")
print(f"  RCH × island area (mass balance)      : {RCH_TOTAL:10.3e} m³/d")
print(f"  JpGU 3D freshwater SGD                : {JPGU_3D:10.3e} m³/d")
print(f"  1D multi-transect (over-estimate)     : 7.34e+05 m³/d")
print(f"\nRatios (TRUE SGD vs reference):")
print(f"  3D NET steady / mass balance          : {true_sgd_steady/RCH_TOTAL:.2f}")
print(f"  3D NET steady / JpGU 3D               : {true_sgd_steady/JPGU_3D:.2f}")
print(f"  3D NET tidal-mean / JpGU 3D           : {true_sgd_tidal/JPGU_3D:.2f}")

# ---- aggregate by layer ----------------------------------------------------
print("\n" + "=" * 78)
print("By layer:")
print("=" * 78)
for lay in [0, 1, 2]:
    sub = cells[cells["layer"] == lay]
    print(f"  L{lay+1}: steady out = {sub['out_steady'].sum():.3e}, "
          f"tidal-mean out = {sub['out_tidal_mean'].sum():.3e}, "
          f"n={len(sub)} cells")

# ---- 12 azimuthal sectors --------------------------------------------------
print("\n" + "=" * 78)
print("12 azimuthal sectors (30° each, from highland pivot)")
print("=" * 78)
SECTOR_DEG = 30.0
net_2d["sector"] = (net_2d["azim_from_pivot"] // SECTOR_DEG).astype(int)
sector_agg = net_2d.groupby("sector").agg(
    sgd_steady=("sgd_net_steady", "sum"),
    sgd_tidal_mean=("sgd_net_tidal_mean", "sum"),
    n_pixels=("row", "count"),
).reset_index()
sector_agg["azim_center"] = sector_agg["sector"] * SECTOR_DEG + 15
print(sector_agg[["sector", "azim_center", "sgd_steady", "sgd_tidal_mean", "n_pixels"]].to_string(index=False,
        formatters={"sgd_steady": "{:10.3e}".format, "sgd_tidal_mean": "{:10.3e}".format}))

# ---- 4 quadrant regions ----------------------------------------------------
def quadrant(az):
    if   45 <= az < 135: return "E"
    elif 135 <= az < 225: return "S"
    elif 225 <= az < 315: return "W"
    else:                return "N"
net_2d["quadrant"] = net_2d["azim_from_pivot"].apply(quadrant)
print("\n" + "=" * 78)
print("By quadrant (N/E/S/W) — net SGD:")
print("=" * 78)
q_agg = net_2d.groupby("quadrant").agg(
    sgd_steady=("sgd_net_steady", "sum"),
    sgd_tidal_mean=("sgd_net_tidal_mean", "sum"),
    n_pixels=("row", "count"),
).reset_index()
print(q_agg.to_string(index=False))

# ---- west coast EPS zone ---------------------------------------------------
EPS_X_MIN, EPS_X_MAX = 553000, 558000
EPS_Y_MIN, EPS_Y_MAX = 9408500, 9420000
in_eps_2d = ((net_2d["easting"] >= EPS_X_MIN) & (net_2d["easting"] <= EPS_X_MAX)
              & (net_2d["northing"] >= EPS_Y_MIN) & (net_2d["northing"] <= EPS_Y_MAX))
eps_2d = net_2d[in_eps_2d]
eps_coast_length_m = (EPS_Y_MAX - EPS_Y_MIN)   # approx, ~11.5 km N-S
print("\n" + "=" * 78)
print("West coast EPS zone (553-558 km E × 9408.5-9420 km N)  [TRUE NET SGD]")
print("=" * 78)
print(f"  Bounding box: {EPS_X_MAX-EPS_X_MIN}m × {EPS_Y_MAX-EPS_Y_MIN}m")
print(f"  Approx coast length: ~{eps_coast_length_m/1000:.1f} km")
print(f"  Coast pixels inside: {len(eps_2d)}")
print(f"  Steady NET SGD       : {eps_2d['sgd_net_steady'].sum():.3e} m³/d")
print(f"  Tidal-mean NET SGD   : {eps_2d['sgd_net_tidal_mean'].sum():.3e} m³/d")
print(f"  Per-m-coast steady    : {eps_2d['sgd_net_steady'].sum()/eps_coast_length_m:.3f} m³/d/m")
print(f"  Per-m-coast tidal-mean: {eps_2d['sgd_net_tidal_mean'].sum()/eps_coast_length_m:.3f} m³/d/m")
print(f"\n  Comparison (per-m-coast):")
print(f"    1D multi-transect W said : 9.85 m³/d/m  (over)")
print(f"    Kuroshima paper avg      : ~0.1 m³/d/m  (× 3.3 Wangi recharge → ~0.33)")

# ---- save CSVs -------------------------------------------------------------
cells.to_csv(WORK / "sgd_3d_per_cell.csv", index=False, float_format="%.4f")
net_2d.to_csv(WORK / "sgd_3d_net_per_pixel.csv", index=False, float_format="%.4f")
sector_agg.to_csv(WORK / "sgd_3d_sector.csv", index=False, float_format="%.4f")
print(f"\nSaved: sgd_3d_per_cell.csv ({len(cells)} rows, raw by layer)")
print(f"Saved: sgd_3d_net_per_pixel.csv ({len(net_2d)} rows, NET per coast pixel)")
print(f"Saved: sgd_3d_sector.csv (12 sectors)")

# ---- polar plot azimuthal ---------------------------------------------------
fig = plt.figure(figsize=(11, 10))
ax = fig.add_subplot(111, projection="polar")
theta_center = np.deg2rad((90 - sector_agg["azim_center"].values) % 360)
r_steady = sector_agg["sgd_steady"].values / 1000   # k m³/d
r_tidal = sector_agg["sgd_tidal_mean"].values / 1000
# Close the polygon
th = np.concatenate([theta_center, theta_center[:1]])
rs = np.concatenate([r_steady, r_steady[:1]])
rt = np.concatenate([r_tidal, r_tidal[:1]])
ax.plot(th, rs, "b-o", lw=2, ms=8, label="Steady (spinup-final)")
ax.plot(th, rt, "r-s", lw=2, ms=8, label="Tidal-mean")
ax.fill(th, rs, color="blue", alpha=0.1)
ax.fill(th, rt, color="red", alpha=0.1)
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
ax.set_rlabel_position(135)
ax.set_title("3D SWI Azimuthal SGD Distribution (validated)\n"
             f"r = sector SGD (k m³/d), perimeter from highland pivot",
             fontsize=12)
ax.grid(True, alpha=0.4)
ax.legend(loc="lower left", bbox_to_anchor=(-0.1, -0.05), fontsize=10)
plt.tight_layout()
plt.savefig(FIGDIR / "sgd_3d_azimuthal.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {FIGDIR / 'sgd_3d_azimuthal.png'}")

# ---- spatial map with EPS box ----------------------------------------------
fig, ax = plt.subplots(figsize=(11, 11))
xmin = XUL; xmax = XUL + NCOL * DELR
ymax = YUL; ymin = YUL - NROW * DELR
top_m = np.ma.masked_where(idomain2d == 0, top_arr)
ax.imshow(top_m, extent=[xmin, xmax, ymin, ymax], origin="upper",
          cmap="terrain", vmin=0, vmax=200, alpha=0.7)
ax.imshow(np.where(idomain2d == 0, 1, np.nan), extent=[xmin, xmax, ymin, ymax],
          origin="upper", cmap="Blues_r", vmin=-1, vmax=2, alpha=0.3)
# Use NET per pixel (real SGD) for the map
sc = ax.scatter(net_2d["easting"], net_2d["northing"],
                 c=net_2d["sgd_net_tidal_mean"],
                 s=30, marker="s",
                 cmap="plasma", edgecolor="black", linewidth=0.2,
                 vmin=0, vmax=max(net_2d["sgd_net_tidal_mean"].quantile(0.95), 1.0),
                 zorder=4)
cbar = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
cbar.set_label("Tidal-mean NET SGD (m³/d, per 30 m coast pixel)", fontsize=10)
# Pivot + Kantamare
ax.plot(PIVOT_X, PIVOT_Y, "k^", ms=18, mec="white", mew=1.5, label=f"Highland pivot")
ax.plot(559298.124, 9412207.827, "m*", ms=20, mec="black", mew=1.4, label="Kantamare HOBO")
# EPS zone rectangle
ax.add_patch(Rectangle((EPS_X_MIN, EPS_Y_MIN), EPS_X_MAX-EPS_X_MIN, EPS_Y_MAX-EPS_Y_MIN,
                        fill=False, edgecolor="green", linewidth=2.5, linestyle="--"))
ax.text((EPS_X_MIN+EPS_X_MAX)/2, EPS_Y_MAX+500,
        f"West coast EPS zone\nSteady NET SGD={eps_2d['sgd_net_steady'].sum():.2e}, "
        f"Tidal-mean={eps_2d['sgd_net_tidal_mean'].sum():.2e} m³/d",
        ha="center", fontsize=10, color="darkgreen", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.92, edgecolor="green"))
ax.set_aspect("equal")
ax.set_xlim(551500, 575000)
ax.set_ylim(9405000, 9425000)
ax.set_xlabel("UTM Easting (m, UTM 51S)")
ax.set_ylabel("UTM Northing (m)")
ax.set_title(f"3D SWI tidal-mean NET SGD distribution (validated model, eff 20.3%≈18% obs)\n"
             f"Island NET steady = {true_sgd_steady:.2e}, "
             f"tidal-mean = {true_sgd_tidal:.2e} m³/d (mass balance RCH = {RCH_TOTAL:.2e})",
             fontsize=11)
ax.legend(loc="upper right", fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIGDIR / "sgd_3d_spatial_map.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {FIGDIR / 'sgd_3d_spatial_map.png'}")

# ---- summary JSON ----------------------------------------------------------
out_json = WORK / "sgd_3d_summary.json"
summary = dict(
    runtime_phase3b_sec=2263,
    nlay=3, ncell_total=NROW*NCOL*3,
    ncoast_layer_cells=len(cells),
    n_coast_pixels=len(net_2d),
    # RAW (includes salt-circulation artifact)
    raw_steady_out_m3_d=float(totals["Steady GHB out (raw)"]),
    raw_tidal_out_m3_d=float(totals["Tidal-mean GHB out (raw)"]),
    raw_tidal_in_m3_d=float(totals["Tidal-mean GHB in  (raw)"]),
    # TRUE (NET per coast pixel, salt-circulation removed)
    true_steady_sgd_m3_d=float(true_sgd_steady),
    true_tidal_mean_sgd_m3_d=float(true_sgd_tidal),
    # References
    mass_balance_RCH_m3_d=RCH_TOTAL,
    jpgu_3d_freshwater_sgd_m3_d=JPGU_3D,
    # EPS zone
    eps_zone_steady_m3_d=float(eps_2d["sgd_net_steady"].sum()),
    eps_zone_tidal_mean_m3_d=float(eps_2d["sgd_net_tidal_mean"].sum()),
    eps_zone_per_m_coast_steady=float(eps_2d["sgd_net_steady"].sum()/eps_coast_length_m),
    eps_zone_per_m_coast_tidal=float(eps_2d["sgd_net_tidal_mean"].sum()/eps_coast_length_m),
    eps_zone_coast_length_m=eps_coast_length_m,
    # Validation
    kantamare_l2_tidal_eff_pct=20.3,
    kantamare_obs_tidal_eff_pct=18.0,
)
out_json.write_text(json.dumps(summary, indent=2))
print(f"\nSaved summary JSON: {out_json}")
