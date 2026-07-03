import pandas as pd, numpy as np
g={"ww02":"NW","ww03":"NW","ww18":"NW","ww19":"NW","ww20":"NW",
   "ww04":"CENT","ww11":"CENT","ww12":"CENT",
   "ww05":"SSE","ww06":"SSE","ww07":"SSE","ww08":"SSE","ww09":"SSE","ww13":"SSE","ww15":"SSE","ww17":"SSE"}
d=pd.read_csv("pest_iter_diagnostic.csv")
d=d[d["use_for_calibration"]==True].copy()
d["zone"]=d["id"].map(g)
d=d.dropna(subset=["zone"])
d["res"]=d["obs_used"]-d["sim_L2"]
print("Per-zone (optimal k2_nw=0.5, k2_cent=0.5, k2_sse=0.525):")
for z,sub in d.groupby("zone"):
    print(f"  {z:5s} n={len(sub)} RMSE={np.sqrt((sub.res**2).mean()):.3f}  bias={sub.res.mean():+.3f}")
print(f"  ALL   n={len(d)} RMSE={np.sqrt((d.res**2).mean()):.3f}  bias={d.res.mean():+.3f}")
