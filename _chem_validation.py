# -*- coding: utf-8 -*-
"""Independent chemical/age validation of the hydraulic well classification.

Tests whether the head-based classification (regional / perched / boundary) is
corroborated by SF6 groundwater age, Cl / seawater fraction, and stable isotopes.
Chemistry covers ww01-ww10 only (WW1..WW10).
"""
import numpy as np, pandas as pd, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic"]
plt.rcParams["axes.unicode_minus"] = False

W = pathlib.Path(__file__).resolve().parent
FIG = W / "figs"; FIG.mkdir(exist_ok=True)


def norm(w):
    w = str(w).lower()
    if w.startswith("ww"):
        num = "".join(c for c in w[2:] if c.isdigit())
        return f"ww{int(num):02d}" if num else w
    return w


iso = pd.read_csv(W / "ww_isotope_chem.csv"); iso["id"] = iso["well"].map(norm)
zeta = pd.read_csv(W / "zeta_vs_chem.csv"); zeta["id"] = zeta["well"].map(norm)
sf6 = pd.read_csv(W / "sf6_age_comparison.csv"); sf6["id"] = sf6["id"].map(norm)

df = iso[["id", "d18O", "d2H", "Cl"]].merge(
    zeta[["id", "sw_frac_pct"]], on="id", how="outer").merge(
    sf6[["id", "obs_age_yr", "flag", "sim_age_yr"]], on="id", how="outer")

# ---- hydraulic classification (head-based) ---------------------------------
KL = {"ww01": "perched", "ww10": "perched",
      "ww05": "perched-suspect", "ww08": "perched-suspect",
      "ww06": "boundary",
      "ww02": "regional", "ww03": "regional", "ww04": "regional",
      "ww07": "regional", "ww09": "regional"}
df["klass"] = df["id"].map(KL)
df = df[df["klass"].notna()].sort_values(["klass", "id"])
COL = {"regional": "#1f77b4", "perched": "#d62728",
       "perched-suspect": "#ff7f0e", "boundary": "#9467bd"}

# obs age numeric (Modern -> 0)
df["age"] = pd.to_numeric(df["obs_age_yr"], errors="coerce")

print(df[["id", "klass", "age", "flag", "Cl", "sw_frac_pct", "d18O"]].to_string(index=False))
print("\n-- mean obs SF6 age by class --")
print(df.groupby("klass")["age"].agg(["mean", "min", "max", "count"]).round(1).to_string())

# =============================================================== FIGURE
fig, ax = plt.subplots(1, 2, figsize=(13, 5.6))

# (a) SF6 observed age by category
order = ["regional", "perched-suspect", "perched", "boundary"]
xmap = {k: i for i, k in enumerate(order)}
for _, r in df.iterrows():
    x = xmap[r["klass"]] + np.random.uniform(-0.13, 0.13) if False else xmap[r["klass"]]
for i, (_, r) in enumerate(df.iterrows()):
    x = xmap[r["klass"]]
    jit = (hash(r["id"]) % 7 - 3) * 0.04
    if pd.notna(r["age"]):
        ax[0].scatter(x + jit, r["age"], s=130, c=COL[r["klass"]], edgecolor="k",
                      linewidth=0.6, zorder=3)
        ax[0].annotate(r["id"], (x + jit, r["age"]), fontsize=8,
                       xytext=(7, 0), textcoords="offset points", va="center")
    else:
        ax[0].scatter(x + jit, -1.5, s=110, marker="x", c=COL[r["klass"]], zorder=3)
        ax[0].annotate(r["id"] + "\n(汚染/欠測)" if False else r["id"], (x + jit, -1.5),
                       fontsize=7, xytext=(7, 0), textcoords="offset points", va="center")
ax[0].axhspan(-0.5, 1.0, color="#ffe0e0", zorder=0)
ax[0].text(2.0, 0.2, "modern (<1 yr)\n= 局所涵養", fontsize=9, color="#a00")
ax[0].set_xticks(range(len(order)))
ax[0].set_xticklabels(["regional", "perched-\nsuspect", "perched", "boundary\n(contam.)"])
ax[0].set_ylabel("observed SF$_6$ groundwater age (yr)")
ax[0].set_ylim(-3, 22)
ax[0].set_title("(a) SF$_6$ 年代: 宙水(ww01,ww10)は modern、\n広域は 8–18 yr の老齢集団")
ax[0].grid(axis="y", alpha=0.3)

# (b) seawater fraction by category
for i, (_, r) in enumerate(df.iterrows()):
    x = xmap[r["klass"]]; jit = (hash(r["id"]) % 7 - 3) * 0.04
    if pd.notna(r["sw_frac_pct"]):
        ax[1].scatter(x + jit, r["sw_frac_pct"], s=130, c=COL[r["klass"]],
                      edgecolor="k", linewidth=0.6, zorder=3)
        ax[1].annotate(r["id"], (x + jit, r["sw_frac_pct"]), fontsize=8,
                       xytext=(7, 0), textcoords="offset points", va="center")
ax[1].set_xticks(range(len(order)))
ax[1].set_xticklabels(["regional", "perched-\nsuspect", "perched", "boundary"])
ax[1].set_ylabel("seawater fraction (%)  (Cl ベース)")
ax[1].set_title("(b) 海水混合率: 沿岸/塩水寄りの井戸を識別\n(coastal position を反映)")
ax[1].grid(axis="y", alpha=0.3)

fig.suptitle("水理分類の独立検証 — SF$_6$ 年代と海水混合率が head-based 分類を裏付ける",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(FIG / "chem_age_validation.png", dpi=160)
print("\nsaved figs/chem_age_validation.png")
