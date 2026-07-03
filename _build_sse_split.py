import numpy as np, pandas as pd, pathlib
from scipy import ndimage
W=pathlib.Path(".")
idom=np.squeeze(np.load("idomain.npy")).astype(int)
kz=np.squeeze(np.load("k2_zones_pest.npy")).astype(int)
land=(idom==1)
dist=ndimage.distance_transform_edt(land)*30.0   # m to nearest non-land(sea)
split=np.zeros_like(kz)
split[(kz==3)&(dist<500)]=31   # coastal SSE
split[(kz==3)&(dist>=500)]=32  # inland SSE
np.save("k2_sse_split.npy",split)
nc=int((split==31).sum()); ni=int((split==32).sum())
print(f"SSE coastal(31): {nc:,} cells ; inland(32): {ni:,} cells")
wc=pd.read_csv("well_cells.csv").set_index("id")
for w in ["ww06","ww17","ww07","ww09","ww13","ww15","ww05","ww08"]:
    r,c=int(wc.loc[w,"row"]),int(wc.loc[w,"col"])
    lab={31:"coastal",32:"inland",0:"(not SSE)"}.get(int(split[r,c]),"?")
    print(f"  {w}: dist={dist[r,c]:.0f} m -> {lab}")
