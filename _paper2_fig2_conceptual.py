"""Paper 2 Fig 2: Conceptual hydrogeological model.

Cross-section schematic showing:
 - 3-layer structure (L1 marly cap, L2 main aquifer, L3 deep extension)
 - Recharge accumulation in L1 (pile-up head)
 - Lateral flow in L2 (high K, fast)
 - Fresh-salt interface (ζ) sinking into L3
 - Density-corrected sea boundary GHB
 - Well screen position in L2 (the observation reference)
 - Annotation that L1 head (cap) > L2 head (main aquifer = obs)

Output: figs/paper2_fig2_conceptual.png + .pdf
"""
import sys, io, pathlib
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, FancyBboxPatch, Polygon

FIGDIR = pathlib.Path(__file__).resolve().parent / "figs"
FIGDIR.mkdir(exist_ok=True)

fig, ax = plt.subplots(figsize=(15, 9))

# Geometry
xL, xR = 0, 10000           # 0 to 10 km
xland_L, xland_R = 1500, 8500  # coast at 1.5 and 8.5 km
ytop_peak = 150.0           # highland peak elev
yL2_bot = -75.0             # L2 base
yL3_bot = -500.0
sea_level = 0.0
LAYER1_THICKNESS = 30.0

# Topography parabolic
x_arr = np.linspace(xL, xR, 800)
def topo(x):
    if x < xland_L or x > xland_R:
        # below sea — assume bathy slope
        if x < xland_L:
            return -80 - (xland_L - x) * 0.06  # gentle slope to deeper sea
        else:
            return -80 - (x - xland_R) * 0.06
    # land: parabolic peak at center
    xn = (x - (xland_L + xland_R)/2) / ((xland_R - xland_L)/2)
    return ytop_peak * (1 - xn**2)

top = np.array([topo(x) for x in x_arr])
botm1 = top - LAYER1_THICKNESS
land_mask = (x_arr >= xland_L) & (x_arr <= xland_R)

# Water table — Dupuit ellipse on land, =0 in sea
def head_L2(x):
    if x < xland_L or x > xland_R: return sea_level
    xn = (x - (xland_L + xland_R)/2) / ((xland_R - xland_L)/2)
    h_max = 5.0
    return h_max * np.sqrt(max(1 - xn**2, 0))
h_L2 = np.array([head_L2(x) for x in x_arr])
# L1 head = L2 head + cap pile-up (Darcy ~3m extra)
h_L1 = h_L2 + 3.0
h_L1[~land_mask] = sea_level

# Zeta (fresh-salt interface) — Ghyben-Herzberg: ζ = -40 × h_fresh
zeta = -40.0 * h_L2
zeta[~land_mask] = sea_level   # at sea, ζ at surface

# === Layers ===
# Sea (left and right)
ax.fill_between(x_arr, top, yL3_bot, where=(x_arr < xland_L) | (x_arr > xland_R),
                color="lightblue", alpha=0.45, label=None, zorder=1)
# L3 deep: from yL2_bot down to yL3_bot, all under salty side
# Below zeta (salt zone) in L3 — pale red
ax.fill_between(x_arr, np.minimum(zeta, yL2_bot), yL3_bot,
                color="#ff9999", alpha=0.35, label="Saltwater zone (below ζ)", zorder=2)
# L3 above zeta where applicable (= freshwater portion of L3)
ax.fill_between(x_arr, yL2_bot, np.minimum(zeta, yL2_bot),
                color="#aac6e6", alpha=0.5, label=None, zorder=2)

# L2 main aquifer (yL2_bot to botm1)
ax.fill_between(x_arr, botm1, yL2_bot, color="#5fa0d8", alpha=0.55,
                label="L2 main aquifer (K₂ = 53 m/d)", zorder=3)

# L1 marly cap (botm1 to top), only on land
ax.fill_between(x_arr[land_mask], top[land_mask], botm1[land_mask],
                color="#c8a070", alpha=0.7,
                label="L1 marly cap (K₁ = 0.085 m/d)", zorder=4)

# Topography line
ax.plot(x_arr, top, "k-", lw=1.5, zorder=5)
# Sea level
ax.axhline(sea_level, color="navy", ls="--", lw=1.0, alpha=0.7, zorder=4)

# Water tables (L1 high cap head + L2 main head)
ax.plot(x_arr[land_mask], h_L1[land_mask], color="#8B4513", lw=2.5, ls="-",
        zorder=10, label="L1 (cap) head ≈ 8 m  [pile-up: not observed]")
ax.plot(x_arr[land_mask], h_L2[land_mask], color="darkblue", lw=2.5, ls="-",
        zorder=10, label="L2 (main aquifer) head ≈ 5 m  [= observation target]")

# Zeta interface
ax.plot(x_arr, zeta, "r-", lw=2.0, zorder=8, label="Fresh-salt interface ζ (Ghyben-Herzberg)")

# === Recharge arrows on L1 ===
rch_x = np.arange(2500, 8000, 700)
for xr in rch_x:
    ax.annotate("", xy=(xr, topo(xr) - 5), xytext=(xr, topo(xr) + 25),
                arrowprops=dict(arrowstyle="->", color="green", lw=1.6))
ax.text(5000, 195, "Recharge (600 mm/yr)", ha="center", color="green",
        fontsize=11, fontweight="bold")

# === L2 lateral flow arrows ===
for sgn, xpos in [(-1, xland_L + 200), (+1, xland_R - 200)]:
    yflow = (yL2_bot + botm1[np.searchsorted(x_arr, xpos)]) / 2
    ax.annotate("", xy=(xpos + sgn*900, yflow),
                xytext=(xpos - sgn*100, yflow),
                arrowprops=dict(arrowstyle="->", color="white", lw=2.8,
                                 mutation_scale=22))
ax.text((xland_L + xland_R)/2, -45, "Lateral fresh-water flow in L2 → SGD",
        ha="center", color="white", fontsize=11, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#5fa0d8", alpha=0.9, edgecolor="white"))

# === Density-corrected sea boundary GHB ===
for xc, label in [(xland_L - 100, "L"), (xland_R + 100, "R")]:
    # L2 GHB label
    ax.annotate(f"GHB$_{{L2}}$\nfh = 1.3 m",
                xy=(xc, -50), xytext=(xc + (-700 if label=="L" else 700), -45),
                fontsize=8, color="white", ha="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="#3a78ad", alpha=0.95,
                          edgecolor="white"),
                arrowprops=dict(arrowstyle="->", color="white", lw=1.2))
    # L3 GHB label
    ax.annotate(f"GHB$_{{L3}}$\nfh = 7.2 m",
                xy=(xc, -300), xytext=(xc + (-700 if label=="L" else 700), -300),
                fontsize=8, color="white", ha="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="#a64040", alpha=0.95,
                          edgecolor="white"),
                arrowprops=dict(arrowstyle="->", color="white", lw=1.2))

# Sea labels
ax.text(750, -100, "SEA", fontsize=14, color="navy", fontweight="bold", alpha=0.7)
ax.text(9250, -100, "SEA", fontsize=14, color="navy", fontweight="bold", alpha=0.7)

# === Observation well ===
wellx = 4500
well_top = topo(wellx)
well_screen_top = botm1[np.searchsorted(x_arr, wellx)]   # = top - 30
well_screen_bot = -30  # screen ~20m into L2
# Well casing (solid black tube)
ax.plot([wellx, wellx], [well_top, well_screen_top], "k-", lw=4, zorder=11)
# Screen portion (dashed indicating slotted)
ax.plot([wellx, wellx], [well_screen_top, well_screen_bot], "k-", lw=4,
        dashes=(1, 0.8), zorder=11)
# Well water level marker at L2 head
ax.plot(wellx, h_L2[np.searchsorted(x_arr, wellx)], marker="v", ms=14,
        mfc="cyan", mec="black", mew=1.4, zorder=12)
# Well label
ax.annotate("Observation well\n(screened in L2)\n→ measures L2 head",
            xy=(wellx, h_L2[np.searchsorted(x_arr, wellx)]),
            xytext=(wellx + 700, well_top + 50),
            fontsize=10, color="black", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow",
                      alpha=0.95, edgecolor="black"),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.4))

# === Layer labels (right margin) ===
ax.text(xR + 200, 30, "L1\nmarly cap\nK₁ = 0.085\n(traps RCH)",
        fontsize=9, color="#8B4513", va="center")
ax.text(xR + 200, -45, "L2\nmain aquifer\nK₂ = 53\n(fast flow)",
        fontsize=9, color="#1f77b4", va="center")
ax.text(xR + 200, -300, "L3\ndeep extension\nK₃ = K₂\n(salt wedge\n+ ζ tracking)",
        fontsize=9, color="#a64040", va="center")

# === Key insight box ===
insight = (
    "Why L2 ≠ L1 for observation comparison:\n"
    "• L1 cap (K₁ low) traps recharge → head pile-up of ~3 m\n"
    "• L2 main aquifer (K₂ high) drains fast → lower head\n"
    "• Observation wells are open / equilibrate to L2\n"
    "• Comparing sim L1 with obs gives spurious +3 m bias\n"
    "• Comparing sim L2 with obs: RMSE 2.22 m (this study)"
)
ax.text(0.02, 0.04, insight, transform=ax.transAxes,
        fontsize=9.5, va="bottom", ha="left",
        bbox=dict(boxstyle="round,pad=0.5", fc="#fffacd",
                  alpha=0.95, edgecolor="black", linewidth=1.5))

# === Cosmetic ===
ax.set_xlim(xL, xR + 1500)
ax.set_ylim(yL3_bot - 30, 230)
ax.set_xticks(np.arange(0, 11000, 2000))
ax.set_xticklabels([f"{int(v/1000)}" for v in np.arange(0, 11000, 2000)])
ax.set_xlabel("Distance along cross-section (km)", fontsize=11)
ax.set_ylabel("Elevation (m, MSL)", fontsize=11)
ax.set_title("Conceptual hydrogeological model of Wangi-Wangi karst SIDS\n"
             "3-layer system: L1 cap + L2 main aquifer + L3 deep extension with SWI ζ tracking",
             fontsize=12, fontweight="bold", pad=12)
ax.grid(alpha=0.2, linestyle="--")
ax.legend(loc="upper right", fontsize=9, framealpha=0.95)

plt.tight_layout()
out_png = FIGDIR / "paper2_fig2_conceptual.png"
plt.savefig(out_png, dpi=180, bbox_inches="tight")
out_pdf = FIGDIR / "paper2_fig2_conceptual.pdf"
plt.savefig(out_pdf, bbox_inches="tight")
plt.close()
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
