"""FOSM parameter uncertainty figure for A-clean (k2_sse is the only informed param)."""
import numpy as np, pandas as pd, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W = pathlib.Path(__file__).resolve().parent
FIG = W / "figs"
u = pd.read_csv(W / "pest.par.usum.csv")
order = ["k2_sse", "k2_nw", "k2_cent"]
u = u.set_index("name").loc[order].reset_index()

fig, ax = plt.subplots(1, 2, figsize=(12, 5))

# (a) prior vs posterior stdev (log10) — informedness
x = np.arange(len(order)); wd = 0.36
ax[0].bar(x - wd / 2, u["prior_stdev"], wd, label="prior σ", color="#bbbbbb")
ax[0].bar(x + wd / 2, u["post_stdev"], wd, label="posterior σ", color="#2ca02c")
for i, r in u.iterrows():
    red = 100 * (1 - r["post_stdev"] / r["prior_stdev"])
    ax[0].text(i, max(r["prior_stdev"], r["post_stdev"]) + 0.004,
               f"−{red:.0f}%", ha="center", fontsize=9, fontweight="bold")
ax[0].set_xticks(x); ax[0].set_xticklabels(order)
ax[0].set_ylabel("parameter σ (log10 multiplier)")
ax[0].set_title("(a) FOSM uncertainty reduction\nonly k2_sse is informed by the data")
ax[0].legend()

# (b) k2_sse posterior with CI (natural units)
m = u.set_index("name").loc["k2_sse", "post_mean"]
s = u.set_index("name").loc["k2_sse", "post_stdev"]
best = 10 ** m
ci1 = [10 ** (m - s), 10 ** (m + s)]
ci2 = [10 ** (m - 1.96 * s), min(10 ** (m + 1.96 * s), 2.0)]
ax[1].errorbar([best], [1], xerr=[[best - ci1[0]], [ci1[1] - best]], fmt="o",
               ms=12, capsize=6, lw=2, color="#2ca02c", label="1σ")
ax[1].plot(ci2, [1, 1], "g-", lw=1, alpha=0.5)
ax[1].plot(ci2, [1, 1], "g|", ms=14, label="2σ (clip @2.0)")
ax[1].axvline(2.0, color="r", ls="--", lw=1, label="upper bound")
ax[1].axvline(1.0, color="k", ls=":", lw=0.8)
ax[1].text(best, 1.08, f"k2_sse = {best:.2f}\n×/÷ {10**s:.2f} (1σ)",
           ha="center", fontsize=10)
ax[1].set_xlim(0.3, 2.3); ax[1].set_ylim(0.7, 1.4); ax[1].set_yticks([])
ax[1].set_xlabel("k2_sse multiplier"); ax[1].legend(loc="lower right", fontsize=8)
ax[1].set_title("(b) k2_sse posterior estimate\n(the only identifiable parameter)")

fig.suptitle("A-clean FOSM — k2_sse identifiable (×/÷1.4); k2_nw/k2_cent uninformed; "
             "params near-uncorrelated", fontsize=11, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(FIG / "Aclean_FOSM.png", dpi=150)
print("saved figs/Aclean_FOSM.png")
print(f"k2_sse best={best:.3f} 1sigma=[{ci1[0]:.2f},{ci1[1]:.2f}] 2sigma=[{ci2[0]:.2f},{ci2[1]:.2f}]")
