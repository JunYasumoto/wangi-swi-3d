import numpy as np, pathlib
W=pathlib.Path(".")
r,c = 737,462   # 0-based for MF6 (2,738,463)
def L(n): 
    a=np.load(W/n); return a
top=L("top_elevation.npy").astype(float)
idom=L("idomain.npy").astype(int)
k2=L("k2_field.npy").astype(float)
kz=L("k2_zones_pest.npy")
b1=L("botm1_field.npy").astype(float); b2=L("botm2_field.npy").astype(float)
print("shapes top",top.shape,"idomain",idom.shape,"k2",k2.shape,"kzones",kz.shape,"botm1",b1.shape)
def at(a):
    a=np.squeeze(a)
    if a.ndim==2: return a[r,c]
    if a.ndim==3: return [float(a[k,r,c]) for k in range(a.shape[0])]
    return None
print("cell (row737,col462) 0-based / MF6 (2,738,463):")
print("  k2_zone     =", at(kz), " (1=NW,2=CENT,3=SSE,0=none)")
print("  k2_field    =", at(k2))
print("  top         =", at(top))
print("  botm1       =", at(b1))
print("  botm2       =", at(b2))
print("  idomain     =", at(idom))
print("  L2 thickness=", float(np.squeeze(b1)[r,c]-np.squeeze(b2)[r,c]))
# neighborhood zone/k2
kzs=np.squeeze(kz); k2s=np.squeeze(k2)
print("  3x3 zone block:\n", kzs[r-1:r+2,c-1:c+2])
print("  3x3 k2 block:\n", k2s[r-1:r+2,c-1:c+2])
# how many cells in each zone
u,cnt=np.unique(kzs,return_counts=True); print("  zone counts:",dict(zip(u.tolist(),cnt.tolist())))
