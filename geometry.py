"""
geometry.py - live matplotlib sketch of the leaf antenna.

This is a PREVIEW ONLY, to make the UI legible while tuning. It is NOT the
simulated geometry - CST's macro owns the real geometry. We just draw a
recognizable leaf whose vein count and proportions track the sliders.
"""

from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend; the server renders the Figure object
import matplotlib.pyplot as plt

ACCENT = "#0f766e"   # teal, matches the app
GROUND = "#334155"   # slate for the ground plane / feed


def draw_leaf(params: dict):
    """Return a matplotlib Figure sketching the REAL leaf antenna topology.

    Matches the CST macro's geometry, not a generic leaf: two rim splines that
    meet near the base (bottom) but stay OPEN at the tip (top), a straight
    center stem running down to the ground plane, and horizontal cross-fins.
    """
    fins = int(params["num_fin_pairs"])
    leaf_length = float(params["leaf_length"])
    rim_width = float(params["rim_width"])
    stem_width = float(params["center_stem_width"])
    fin_width = float(params["fin_width"])
    ground_gap = float(params["leaf_ground_gap"])

    H = 10.0          # leaf body height (base at y=0 -> tip at y=H)
    W = 3.0           # max half-width in the middle
    TOP_GAP = 0.5     # half-gap where the two rim tips DON'T meet (open top)
    POWER = 0.72      # rim arch shape (macro rim_curve_bias)

    fig, ax = plt.subplots(figsize=(3.6, 5.2))
    ax.set_aspect("equal")
    ax.axis("off")

    # --- rim half-width vs height: 0 at the base (closed), TOP_GAP at the tip ---
    def hw(t):
        base_y = TOP_GAP * t                      # 0 at base -> TOP_GAP at tip
        return base_y + (W - base_y) * np.sin(np.pi * t) ** POWER

    t = np.linspace(0.0, 1.0, 160)
    y = t * H
    x = hw(t)
    rim_lw = 1.8 + (rim_width - 2.0) / 4.0 * 2.6   # thicker line with rim_width

    # two open rim traces (left + right); they meet at the base, gap at the top
    ax.plot(x, y, color=ACCENT, lw=rim_lw, solid_capstyle="round")
    ax.plot(-x, y, color=ACCENT, lw=rim_lw, solid_capstyle="round")

    # --- ground plane + feed drop below the base ---
    gnd_y = -(1.4 + (ground_gap - 2.0) / 10.0 * 1.6)
    gnd_half = W * 0.85
    ax.plot([-gnd_half, gnd_half], [gnd_y, gnd_y], color=GROUND, lw=3.4, solid_capstyle="round")

    # --- straight center stem: from just above the open tip down to the ground ---
    stem_lw = 1.4 + (stem_width - 2.0) / 4.0 * 3.2
    ax.plot([0, 0], [gnd_y, H * 1.0], color=ACCENT, lw=stem_lw, solid_capstyle="round")
    # small feed marker at the port (base/ground junction)
    ax.plot(0, gnd_y, marker="o", ms=5, color="#b91c1c", zorder=5)

    # --- horizontal cross-fins along the stem (perpendicular, like the macro) ---
    fin_lw = 1.0 + (fin_width - 0.8) / 2.2 * 2.4
    ts = _spread(0.16, 0.84, fins)
    for ti in ts:
        yi = ti * H
        span = 0.82 * hw(ti)                       # stay inside the rim
        ax.plot([-span, span], [yi, yi], color=ACCENT, lw=fin_lw,
                alpha=0.95, solid_capstyle="round")

    ax.set_xlim(-W - 1.1, W + 1.1)
    ax.set_ylim(gnd_y - 0.6, H + 0.7)
    ax.set_title(f"{fins} fins - {leaf_length:g} mm", fontsize=9, color=GROUND)
    fig.tight_layout(pad=0.3)
    return fig


def _spread(lo: float, hi: float, n: int):
    """n evenly spaced positions in [lo, hi]; handles n==1 gracefully."""
    if n <= 1:
        return [(lo + hi) / 2.0]
    step = (hi - lo) / (n - 1)
    return [lo + i * step for i in range(n)]
