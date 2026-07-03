"""Phase 3c PEST forward model — SKELETON.

This is a TEMPLATE for the integrated forward model that PEST will call.
Reads parameters → builds 3-layer SWI model → runs SS → extracts:
  - heads at 20 wells (sim_heads.csv)
  - WW4 L2 tidal range (sim_tidal.csv) [need transient]
  - NET SGD island total (sim_sgd.csv)
  - SF6 ages via MODPATH (sim_ages.csv)
  - WW4 zeta position (sim_zeta_ww4.csv)

Inputs (PEST writes these):
  params.csv: rch_mult, ghb_cond_mult, k2_z1, k2_z2, k2_z3, n_trans, k1, botm_l3
  zk_values.csv: k2_z1, k2_z2, k2_z3 (PEST-adjustable K2 zones)

Usage:
  Set up PEST .pst with parameter & observation groups → PEST calls this script
  per iteration. Script writes sim_*.csv → PEST reads, computes phi, adjusts pars.

Structure (TO BE COMPLETED in Phase 3c.1):
"""
import sys, io, pathlib, os, subprocess
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import flopy

WORK = pathlib.Path(__file__).resolve().parent
MF6_EXE = str(WORK.parent / "wangi_swi" / "mf6.6.0-SWI-Tides" / "mf6.exe")
MP7_EXE = "mp7.exe"   # MODPATH7

# ===========================================================================
# 1. Read PEST parameters
# ===========================================================================
def read_params():
    """PEST writes params.csv with current iteration values."""
    p = pd.read_csv(WORK / "params.csv", index_col=0)
    pars = {
        "rch_mult":      float(p.loc["rch_mult"].iloc[0]),
        "ghb_cond_mult": float(p.loc["ghb_cond_mult"].iloc[0]),
        "k1":            float(p.loc["k1"].iloc[0]),
        "n_trans":       float(p.loc["n_trans"].iloc[0]),
        "botm_l3":       float(p.loc["botm_l3"].iloc[0]),
        "sy":            float(p.loc["sy"].iloc[0]) if "sy" in p.index else 0.10,
        "ss":            float(p.loc["ss"].iloc[0]) if "ss" in p.index else 1e-4,
    }
    zk = pd.read_csv(WORK / "zk_values.csv").set_index("name")["value"]
    pars["k2_z1"] = float(zk["k2_z1"])
    pars["k2_z2"] = float(zk["k2_z2"])
    pars["k2_z3"] = float(zk["k2_z3"])
    return pars

# ===========================================================================
# 2. Build zonal K2 field
# ===========================================================================
def build_k_fields(pars):
    """Build K1 (cap) and K2 (3-zone) fields."""
    zones = np.load(WORK / "zones_3zone.npy")  # NEW file: 0=inactive, 1=NW, 2=Central, 3=S/SE
    k1 = np.full(zones.shape, pars["k1"])
    k1[zones == 0] = 1e-5  # inactive
    k2 = np.full(zones.shape, 1e-5)
    k2[zones == 1] = pars["k2_z1"]   # NW
    k2[zones == 2] = pars["k2_z2"]   # Central
    k2[zones == 3] = pars["k2_z3"]   # S/SE
    return k1, k2

# ===========================================================================
# 3. Build & run SS SWI model with parameters
# ===========================================================================
def run_ss_swi(pars, k1, k2):
    """Build 3-layer model with SWI, run SS, return heads + zeta."""
    # ... adapt swi_3d_phase3a_ss.py logic ...
    # Use pars["botm_l3"], pars["ghb_cond_mult"], pars["rch_mult"], pars["sy"], pars["ss"]
    # Return: heads (3D), zeta (3D), workspace path
    pass

# ===========================================================================
# 4. Extract heads at wells
# ===========================================================================
def extract_heads_at_wells(heads, top_arr, botm1, botm2, perched_set):
    """Pick L2 head for regional wells, L1 for perched."""
    wells = pd.read_csv(WORK / "calibration_targets.csv")
    wc = pd.read_csv(WORK / "well_cells.csv")[["id", "model_row", "model_col"]]
    wells = wells.merge(wc, on="id", how="left")
    sim_heads = []
    for _, w in wells.iterrows():
        r, c = int(w["model_row"]), int(w["model_col"])
        h1 = float(heads[0, r, c]); h2 = float(heads[1, r, c]); h3 = float(heads[2, r, c])
        if w["id"] in perched_set:
            h = h1 if (h1 > botm1[r, c] and -1e9 < h1 < 1e9) else h2
        else:
            h = h2 if (h2 > botm2[r, c] and -1e9 < h2 < 1e9) else h3
        sim_heads.append({"id": w["id"], "sim_head": h})
    pd.DataFrame(sim_heads).to_csv(WORK / "sim_heads.csv", index=False)

# ===========================================================================
# 5. Run short transient + extract tidal eff at WW4
# ===========================================================================
def run_short_transient_tidal(ss_heads):
    """24-hr spinup + 24-hr Kuroshima tide × 1.9, extract WW4 L2 tidal range."""
    # ... adapt swi_3d_phase3b_tidal.py for short run ...
    # Extract: max(L2[WW4]) - min(L2[WW4]) during tidal phase = tidal range
    # eff = range / sea_range (sea range from forcing = 2.22 m)
    # Write: sim_tidal.csv {ww4_tidal_eff}
    pass

# ===========================================================================
# 6. NET SGD per pixel
# ===========================================================================
def compute_net_sgd(cbc_path):
    """Read CBC, compute NET (out - in) per coast pixel, sum to island total."""
    # ... adapt analyze_3d_sgd.py NET logic ...
    # Write: sim_sgd.csv {island_steady_sgd, eps_zone_sgd, ...}
    pass

# ===========================================================================
# 7. MODPATH backward tracking with n_trans porosity
# ===========================================================================
def run_modpath_ages(pars, heads):
    """For each SF6-valid well, backward track to recharge source, compute age."""
    # ... adapt wangi_jpgu2026/forward_final_step2.py MODPATH section ...
    # Critical: pass pars["n_trans"] as POROSITY to MODPATH7 bas file
    # Write: sim_ages.csv {ww02_age, ww04_age, ww05_age, ww07_age, ww08_age, ww09_age}
    pass

# ===========================================================================
# 8. Extract WW4 zeta + estimate sw_frac
# ===========================================================================
def extract_ww4_sw_frac(zeta, ground_elev):
    """Estimate sw_frac at WW4 well screen from zeta position."""
    # zeta_at_WW4 = zeta[1, WW4_row, WW4_col]
    # If zeta is deep, well is fully fresh: sw_frac = 0
    # If zeta is shallow (close to ground), well sees seawater mix: sw_frac increases
    # Crude proxy: sw_frac ~ max(0, (ground_elev - zeta_at_WW4) / ground_elev) × 100
    # Better: requires GWT for proper Cl tracking (Paper 3 candidate)
    # Write: sim_sw_frac.csv {ww4_sw_frac}
    pass

# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    pars = read_params()
    k1, k2 = build_k_fields(pars)
    heads, zeta, ws = run_ss_swi(pars, k1, k2)
    # ... (call all extractors) ...

    print("Phase 3c PEST forward run completed.")
    # PEST will read sim_*.csv next
