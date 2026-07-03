import pandas as pd, pathlib
W=pathlib.Path(".")
f=W/"calibration_targets_corrected.csv"
d=pd.read_csv(f)
perched=["ww10","ww11","ww12"]
d.loc[d["id"].isin(perched),"use_for_calibration"]=False
d.loc[d["id"].isin(perched),"weight"]=0.0
d.to_csv(f,index=False)
n=int((d["use_for_calibration"]==True).sum())
print("calibration wells now:",n)
print(d[["id","use_for_calibration","weight"]][d["id"].isin(perched)].to_string(index=False))
