import pandas as pd, pathlib
f=pathlib.Path("calibration_targets_corrected.csv")
d=pd.read_csv(f)
for w in ["ww05","ww08"]:
    d.loc[d["id"]==w,"use_for_calibration"]=False
    d.loc[d["id"]==w,"weight"]=0.0
d.to_csv(f,index=False)
print("calibration wells now:",int((d["use_for_calibration"]==True).sum()))
