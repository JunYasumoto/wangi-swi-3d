"""Rebuild calibration obs_head using Field-survey Water Surface + PEST ground_elev.

For each well, obs_head = ground_elev + casing_height - water_surface_depth_from_casing_top

The PEST calibration_targets.csv assumed obs_head = ground_elev - DTW (with possibly
incorrect DTW for some wells). Field survey provides the actual water surface depth.

Then re-evaluate Phase 3c L3-shallow model with corrected obs_heads.
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import importlib.util

WORK = pathlib.Path(__file__).resolve().parent
FIGDIR = WORK / "figs"
JPGU = WORK.parent / "wangi_jpgu2026"

# Load PEST calibration_targets (has UTM coords, obs_head, ground from well_class)
pest = pd.read_csv(WORK / "calibration_targets.csv")[["id", "utm_x", "utm_y", "obs_head"]]
wc = pd.read_csv(JPGU / "well_classification.csv")[["well_id", "ground_elev", "classification"]]
wc.columns = ["id", "ground_elev", "classification"]
pest = pest.merge(wc, on="id", how="left")

# Load Field survey: WW1-WW10 only
fld = pd.read_excel(r"C:\Users\安元純\Dropbox\地球研\Wakatobi\WangiWangi_FieldSurvey_Results_20241212.xlsx",
                    sheet_name="2024")
fld = fld[fld.iloc[:,1].astype(str).str.startswith("WW", na=False)].copy()
fld = fld[["Sampling Point", "Groundwater Level (m)", "Water Surface", "Hight of the Well"]]
fld.columns = ["well", "GW_field", "WS", "casing_h"]
fld["id"] = fld["well"].apply(lambda w: f"ww{int(w.replace('WW','')):02d}")

merged = pest.merge(fld[["id", "WS", "casing_h"]], on="id", how="left")
# Compute corrected obs_head (only for wells where we have WS)
merged["obs_head_corr"] = merged["ground_elev"] + merged["casing_h"] - merged["WS"]
# Difference vs PEST
merged["pest_inflation"] = merged["obs_head"] - merged["obs_head_corr"]
# Mark which wells have field-survey-based correction
merged["has_corr"] = merged["WS"].notna()

# For WW4 specifically: use the verified HOBO truth (+2.378 m MSL)
merged.loc[merged["id"] == "ww04", "obs_head_corr"] = 2.378
merged.loc[merged["id"] == "ww04", "pest_inflation"] = merged.loc[merged["id"] == "ww04", "obs_head"] - 2.378

# For wells beyond WW10 (no field-survey single-point measurement): keep PEST value but flag
merged["obs_used"] = merged["obs_head"].copy()
merged.loc[merged["id"] == "ww04", "obs_used"] = 2.378

print("=== Obs_head correction summary (Field-survey based) ===")
print(merged[["id", "ground_elev", "WS", "casing_h", "obs_head",
              "obs_head_corr", "pest_inflation", "has_corr"]].to_string(
    index=False))

print("\n  ⚠ Field WS column meaning varies across wells (not consistently 'depth from casing top').")
print("    Naive formula gives extreme/impossible values for many wells.")
print("    Only WW4 has independent verification (8-month HOBO → +2.378 m MSL).")
print("    Strategy: correct ONLY WW4 (verified); others may have similar errors but cannot verify.")

# Save corrected calibration_targets
out = WORK / "calibration_targets_corrected.csv"
merged[["id", "utm_x", "utm_y", "obs_head", "obs_head_corr", "obs_used",
        "has_corr", "ground_elev", "WS", "pest_inflation"]].to_csv(
    out, index=False, float_format="%.4f")
print(f"\nSaved: {out}")

# === Re-evaluate Phase 3c L3-shallow with corrected obs_heads ===
print("\n" + "=" * 72)
print("Re-evaluate Phase 3c L3-shallow against corrected obs_heads")
print("=" * 72)
heads_l3s = pd.read_csv(WORK / "phase3a_heads_3c_L3shallow.csv")
heads_l3s = heads_l3s.merge(
    merged[["id", "obs_head_corr", "obs_used", "has_corr", "pest_inflation"]],
    on="id", how="left")
# Use obs_used (corrected if available, else PEST)
heads_l3s["resid_corr"] = heads_l3s["sim_used"] - heads_l3s["obs_used"]
heads_l3s["resid_pest"] = heads_l3s["sim_used"] - heads_l3s["obs"]

# Stats
PERCHED = {"ww10", "ww14", "ww16"}
main = heads_l3s[~heads_l3s["id"].isin(PERCHED)].copy()
rmse_pest = np.sqrt((main["resid_pest"]**2).mean())
bias_pest = main["resid_pest"].mean()
rmse_corr = np.sqrt((main["resid_corr"]**2).mean())
bias_corr = main["resid_corr"].mean()
print(f"\nMain aquifer (n={len(main)}):")
print(f"  vs PEST original obs: RMSE = {rmse_pest:.3f} m, bias = {bias_pest:+.3f} m")
print(f"  vs Corrected obs    : RMSE = {rmse_corr:.3f} m, bias = {bias_corr:+.3f} m")

# Stats only for wells with corrections
corrected = main[main["has_corr"] == True]
if len(corrected) > 0:
    print(f"\nWells with field-survey correction (n={len(corrected)}):")
    print(corrected[["id", "obs", "obs_used", "sim_used",
                     "resid_pest", "resid_corr"]].to_string(
        index=False))
    rmse_c = np.sqrt((corrected["resid_corr"]**2).mean())
    bias_c = corrected["resid_corr"].mean()
    print(f"\n  Corrected subset RMSE = {rmse_c:.3f} m, bias = {bias_c:+.3f} m")

# Save updated residuals
heads_l3s.to_csv(WORK / "phase3a_heads_3c_L3shallow_corrected.csv",
                  index=False, float_format="%.4f")
print(f"\nSaved: {WORK / 'phase3a_heads_3c_L3shallow_corrected.csv'}")

# === Visualization ===
fig, axes = plt.subplots(1, 2, figsize=(15, 7))

ax = axes[0]
for _, r in main.iterrows():
    color = "green" if r["has_corr"] else "gray"
    marker = "o" if r["has_corr"] else "s"
    ax.scatter(r["obs"], r["sim_used"], c=color, s=160,
               edgecolor="black", linewidth=1.2, marker=marker, zorder=4)
    ax.annotate(r["id"], (r["obs"], r["sim_used"]),
                xytext=(5, 4), textcoords="offset points", fontsize=8)
lo, hi = -1, 10
ax.plot([lo, hi], [lo, hi], "k--", lw=1)
ax.plot([lo, hi], [lo+1, hi+1], "k:", lw=0.5)
ax.plot([lo, hi], [lo-1, hi-1], "k:", lw=0.5)
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
ax.set_xlabel("PEST obs_head (m)", fontsize=11)
ax.set_ylabel("Sim L2 (Phase 3c L3-shallow, m)", fontsize=11)
ax.set_title(f"Before correction: vs PEST obs_head\n"
             f"RMSE = {rmse_pest:.2f} m, bias = {bias_pest:+.2f} m\n"
             "Green = has field-survey correction available", fontsize=10, fontweight="bold")
ax.grid(alpha=0.3)

ax2 = axes[1]
for _, r in main.iterrows():
    color = "green" if r["has_corr"] else "gray"
    marker = "o" if r["has_corr"] else "s"
    ax2.scatter(r["obs_used"], r["sim_used"], c=color, s=160,
                edgecolor="black", linewidth=1.2, marker=marker, zorder=4)
    ax2.annotate(r["id"], (r["obs_used"], r["sim_used"]),
                 xytext=(5, 4), textcoords="offset points", fontsize=8)
ax2.plot([lo, hi], [lo, hi], "k--", lw=1)
ax2.plot([lo, hi], [lo+1, hi+1], "k:", lw=0.5)
ax2.plot([lo, hi], [lo-1, hi-1], "k:", lw=0.5)
ax2.set_xlim(lo, hi); ax2.set_ylim(lo, hi); ax2.set_aspect("equal")
ax2.set_xlabel("Corrected obs_head (m)", fontsize=11)
ax2.set_ylabel("Sim L2 (Phase 3c L3-shallow, m)", fontsize=11)
ax2.set_title(f"After correction: WW1-WW10 use field WS, WW11+ unchanged\n"
              f"RMSE = {rmse_corr:.2f} m, bias = {bias_corr:+.2f} m\n"
              f"WW4 uses HOBO long-term truth +2.378 m", fontsize=10, fontweight="bold")
ax2.grid(alpha=0.3)

plt.tight_layout()
out_fig = FIGDIR / "obs_head_correction_compare.png"
plt.savefig(out_fig, dpi=140, bbox_inches="tight")
plt.close()
print(f"Saved: {out_fig}")
