# -*- coding: utf-8 -*-
"""FloPy/MODFLOW stack diagram for the slide deck."""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic"]
plt.rcParams["axes.unicode_minus"] = False
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG = pathlib.Path(__file__).resolve().parent / "figs"
fig, ax = plt.subplots(figsize=(9, 6.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")

def box(x, y, w, h, txt, fc, tc="white", fs=13, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                                fc=fc, ec="none"))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center",
            fontsize=fs, color=tc, fontweight="bold" if bold else "normal")

CLAY = "#C15F3C"; DARK = "#2B2B2B"; BLUE = "#3B6FA0"; GREEN = "#3C8C4A"; GREY = "#777777"

# top: human + claude code
box(0.6, 8.4, 3.7, 1.2, "あなた\n（方針・判断）", "#888888", fs=13)
box(5.7, 8.4, 3.7, 1.2, "Claude Code\n（実行・編集・検証）", CLAY, fs=13)
ax.add_patch(FancyArrowPatch((4.3, 9.0), (5.7, 9.0), arrowstyle="<->", mutation_scale=18, color=DARK, lw=2))

# arrow down
ax.add_patch(FancyArrowPatch((7.55, 8.4), (7.55, 7.5), arrowstyle="-|>", mutation_scale=18, color=CLAY, lw=2.5))

# conda env container
ax.add_patch(FancyBboxPatch((0.6, 1.0), 8.8, 6.3, boxstyle="round,pad=0.1,rounding_size=0.15",
                            fc="#F2EEE9", ec=GREY, lw=1.5, ls="--"))
ax.text(1.0, 6.95, "conda 仮想環境 (Python 3.x)", fontsize=12, color=GREY, fontweight="bold")

# flopy
box(1.2, 5.2, 4.2, 1.3, "flopy  (Python API)\nMODFLOW をコードで記述", BLUE, fs=13)
# modflow binary
box(6.0, 5.2, 2.9, 1.3, "MODFLOW 6\nmf6.exe (実行体)", DARK, fs=12)
ax.add_patch(FancyArrowPatch((5.4, 5.85), (6.0, 5.85), arrowstyle="-|>", mutation_scale=16, color=DARK, lw=2))

# analysis libs
box(1.2, 3.4, 4.2, 1.3, "numpy / pandas\nmatplotlib / scipy", GREEN, fs=12)
# pest
box(6.0, 3.4, 2.9, 1.3, "PEST++ / pyemu\nキャリブレーション", "#9467bd", fs=11)

# output
box(1.2, 1.5, 7.7, 1.1, "地下水モデル解析（水頭・塩水侵入・不確実性）", CLAY, fs=13)

ax.text(5.0, 0.45, "Claude Code が各層のセットアップ・実行・修正を代行",
        ha="center", fontsize=11, color=GREY, style="italic")

fig.tight_layout()
fig.savefig(FIG / "flopy_stack.png", dpi=160, bbox_inches="tight")
print("saved figs/flopy_stack.png")
