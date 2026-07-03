"""Cross-check PEST calibration obs_head values vs field survey direct measurements.

For each well, PEST used:
  obs_head_PEST = ground_elev - DTW_assumed

Field survey gives:
  Water Surface (m) = depth from casing top to water table
  Hight of the Well (m) = casing top above ground level
  -> obs_head_field = ground_elev + Hight_well - Water_Surface

Compare both and flag wells where DTW assumed in PEST disagrees with field.
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd, numpy as np

WORK = pathlib.Path(__file__).resolve().parent
JPGU = WORK.parent / "wangi_jpgu2026"

# Load PEST targets (calibration_targets has obs_head only; ground_elev is in JpGU well_classification.csv)
pest_h = pd.read_csv(WORK / "calibration_targets.csv")[["id", "obs_head"]]
wc = pd.read_csv(JPGU / "well_classification.csv")[["well_id", "ground_elev"]]
wc.columns = ["id", "ground_elev"]
pest = pest_h.merge(wc, on="id", how="left")

# Load field survey (sheet '2024') and pull only WW1..WW10 with values
import openpyxl
src = r"C:\Users\安元純\Dropbox\地球研\Wakatobi\WangiWangi_FieldSurvey_Results_20241212.xlsx"
fld = pd.read_excel(src, sheet_name="2024")
fld = fld[fld.iloc[:, 1].astype(str).str.startswith("WW", na=False)].copy()
fld_clean = fld[["Sampling Point", "Groundwater Level (m)", "Water Surface", "Hight of the Well"]].copy()
fld_clean.columns = ["well", "GW_level_field", "water_surface_m", "casing_height_m"]
# Lowercase + zero-pad
fld_clean["id"] = fld_clean["well"].apply(lambda x: f"ww{int(x.replace('WW','')):02d}")

merged = pest.merge(fld_clean, on="id", how="inner")
merged["obs_head_field"] = (merged["ground_elev"]
                             + merged["casing_height_m"]
                             - merged["water_surface_m"])
merged["bias_PEST_vs_field"] = merged["obs_head"] - merged["obs_head_field"]
merged["bias_pct"] = merged["bias_PEST_vs_field"] / merged["obs_head_field"].abs() * 100

print("Comparison: PEST obs_head (DTW assumed) vs Field-survey-derived obs_head")
print("=" * 95)
print(merged[["id", "ground_elev", "casing_height_m", "water_surface_m",
               "obs_head", "obs_head_field", "bias_PEST_vs_field"]].to_string(
    index=False,
    formatters={"obs_head": "{:7.3f}".format, "obs_head_field": "{:7.3f}".format,
                 "bias_PEST_vs_field": "{:+7.3f}".format,
                 "ground_elev": "{:6.1f}".format, "casing_height_m": "{:5.2f}".format,
                 "water_surface_m": "{:6.2f}".format}))

merged.to_csv(WORK / "obs_head_correction.csv", index=False, float_format="%.4f")
print(f"\nSaved: {WORK / 'obs_head_correction.csv'}")

# Summary stats
biases = merged["bias_PEST_vs_field"].values
print(f"\nBias stats (PEST - field):")
print(f"  mean: {np.mean(biases):+.3f} m")
print(f"  median: {np.median(biases):+.3f} m")
print(f"  range: {np.min(biases):+.3f} to {np.max(biases):+.3f} m")
print(f"  abs mean: {np.mean(np.abs(biases)):.3f} m")

# Wells where PEST disagrees > 1 m
disagree = merged[merged["bias_PEST_vs_field"].abs() > 1.0]
print(f"\nWells where PEST disagrees > 1 m with field (n={len(disagree)}/{len(merged)}):")
print(disagree[["id", "obs_head", "obs_head_field", "bias_PEST_vs_field"]].to_string(index=False))
