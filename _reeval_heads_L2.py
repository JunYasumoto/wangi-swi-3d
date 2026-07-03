"""Re-evaluate well head comparison using L2 head for regional wells.

The original phase3a_summary used L1 head where L1 is saturated, but regional
wells (per well_classification.csv) are screened in main aquifer (L2). Re-pick.

Reads:
  phase3a_ss_3c_baseline/gwf.hds
  calibration_targets.csv, well_cells.csv

Outputs:
  phase3a_heads_3c_baseline_L2corrected.csv
  console summary
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd, flopy

WORK = pathlib.Path(__file__).resolve().parent

scenarios = ["3c_baseline"]  # extend later as more scenarios converge

PERCHED = {"ww10", "ww14", "ww16"}

top = np.load(WORK / "top_elevation.npy").astype(float)
botm1 = top - 30.0
botm2 = np.full_like(top, -75.0)
botm2 = np.minimum(botm2, botm1 - 10.0)
botm3 = np.full_like(top, -500.0)
botm3 = np.minimum(botm3, botm2 - 10.0)

wells = pd.read_csv(WORK / "calibration_targets.csv")
wc = pd.read_csv(WORK / "well_cells.csv")[["id", "model_row", "model_col"]]
wells = wells.merge(wc, on="id", how="left")

print(f"{'scenario':<20s} {'RMSE_all':>9s} {'RMSE_main':>10s} {'bias_main':>10s} {'n_wells':>8s}")
print("-" * 70)

for tag in scenarios:
    ws = WORK / f"phase3a_ss_{tag}"
    if not (ws / "gwf.hds").exists():
        print(f"  {tag}: missing")
        continue
    hds = flopy.utils.HeadFile(str(ws / "gwf.hds")).get_data(kstpkper=(0, 0))
    rows = []
    for _, w in wells.iterrows():
        r, c = int(w["model_row"]), int(w["model_col"])
        h1 = float(hds[0, r, c])
        h2 = float(hds[1, r, c])
        h3 = float(hds[2, r, c])
        is_perched = w["id"] in PERCHED
        if is_perched:
            h_used = h1 if (h1 > botm1[r, c] and -1e9 < h1 < 1e9) else h2
        else:
            # Always pick L2 for regional wells (main aquifer)
            if -1e9 < h2 < 1e9 and h2 > botm2[r, c]:
                h_used = h2
            elif -1e9 < h3 < 1e9:
                h_used = h3
            else:
                h_used = h1
        obs = float(w["obs_head"])
        rows.append(dict(id=w["id"], obs=obs, sim_L1=h1, sim_L2=h2, sim_L3=h3,
                          sim_used=h_used, resid=h_used - obs,
                          perched=is_perched, dry=abs(h_used) < 1e-3))
    res = pd.DataFrame(rows)
    res.to_csv(WORK / f"phase3a_heads_{tag}_L2corrected.csv", index=False, float_format="%.3f")

    # Diagnostics
    rmse_all = np.sqrt(np.mean(res["resid"]**2))
    main = res[~res["perched"]]
    rmse_main = np.sqrt(np.mean(main["resid"]**2))
    bias_main = main["resid"].mean()
    print(f"{tag:<20s} {rmse_all:9.3f} {rmse_main:10.3f} {bias_main:+10.3f} {len(main):8d}")
    print()
    print(f"Per-well detail ({tag}):")
    print(res[["id", "obs", "sim_L1", "sim_L2", "sim_L3", "sim_used", "resid", "perched"]]
            .to_string(index=False))
    print()
