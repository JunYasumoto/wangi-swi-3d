import numpy as np, pandas as pd, pathlib
W=pathlib.Path(".")
idom=np.squeeze(np.load("idomain.npy")).astype(int)
NROW,NCOL=idom.shape
# coast = active cell adjacent to inactive(sea) cell
pad=np.pad(idom,1,mode="constant",constant_values=0)
is_coast=(idom==1)&((pad[0:-2,1:-1]==0)|(pad[2:,1:-1]==0)|(pad[1:-1,0:-2]==0)|(pad[1:-1,2:]==0))
cr,cc=np.where(is_coast)
print(f"coast cells: {len(cr)}")
wc=pd.read_csv("well_cells.csv").set_index("id")
tg=pd.read_csv("calibration_targets_corrected.csv").set_index("id")
rows=[]
for wid in wc.index:
    r,c=int(wc.loc[wid,"row"]),int(wc.loc[wid,"col"])
    d=np.sqrt(((cr-r)*30.0)**2+((cc-c)*30.0)**2).min()
    obs=tg.loc[wid,"obs_truth_ppp"] if wid in tg.index else np.nan
    terr=tg.loc[wid,"terrain_elev_m"] if wid in tg.index else np.nan
    use=tg.loc[wid,"use_for_calibration"] if wid in tg.index else None
    cls=tg.loc[wid,"aquifer_class"] if wid in tg.index else ""
    rows.append([wid,round(d),round(float(obs),2) if pd.notna(obs) else None,
                 round(float(terr),1) if pd.notna(terr) else None,use,cls])
df=pd.DataFrame(rows,columns=["well","dist_sea_m","obs_head_m","terrain_m","use_cal","class"])
df["head_per_km"]=(df["obs_head_m"]/(df["dist_sea_m"]/1000.0)).round(1)
df=df.sort_values("dist_sea_m")
pd.set_option("display.width",200); pd.set_option("display.max_columns",20)
print(df.to_string(index=False))
