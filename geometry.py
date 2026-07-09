"""
geometry.py - live matplotlib sketch of the leaf antenna.

This is a PREVIEW ONLY, to make the UI legible while tuning. It is NOT the
simulated geometry - CST's macro owns the real geometry. We just draw a
recognizable leaf whose vein count and proportions track the sliders.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # headless backend; Streamlit renders the Figure object
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

ACCENT = "#0f766e"  # teal, matches the app


def draw_leaf(params: dict):
    """Return a matplotlib Figure sketching the leaf for the given params."""
    fins = int(params["num_fin_pairs"])
    leaf_length = float(params["leaf_length"])
    rim_width = float(params["rim_width"])
    stem_width = float(params["center_stem_width"])
    fin_width = float(params["fin_width"])
    ground_gap = float(params["leaf_ground_gap"])

    # Normalize length to a fixed drawing height so the sketch stays framed;
    # width follows a leaf-like aspect ratio.
    height = 10.0
    half_w = 3.2  # half-width of the leaf body

    fig, ax = plt.subplots(figsize=(3.6, 5.2))
    ax.set_aspect("equal")
    ax.axis("off")

    # Leaf tip at top (y = +height/2), stem base at bottom (y = -height/2).
    y_top = height / 2.0
    y_base = -height / 2.0

    # --- outer rim (leaf outline as an ellipse) ---
    # rim_width modulates the outline thickness of the drawn rim.
    rim_lw = 1.5 + (rim_width - 2.0) / 4.0 * 3.0  # 1.5..4.5 pts across 2..6 mm
    outline = Ellipse(
        (0, 0), width=2 * half_w, height=height,
        fill=False, edgecolor=ACCENT, linewidth=rim_lw,
    )
    ax.add_patch(outline)

    # --- central stem / midrib ---
    stem_lw = 1.0 + (stem_width - 2.0) / 4.0 * 3.5  # thicker with stem_width
    ax.plot([0, 0], [y_base, y_top], color=ACCENT, linewidth=stem_lw, solid_capstyle="round")

    # --- mirrored vein pairs ---
    # Distribute veins along the midrib between base and tip; each vein angles
    # outward and upward, tapering (shorter) toward the tip, staying inside rim.
    fin_lw = 0.8 + (fin_width - 0.8) / 2.2 * 2.6  # thicker with fin_width
    margin = 0.12 * height
    ys = _spread(y_base + margin, y_top - margin, fins)
    for y in ys:
        # Half-width of the ellipse at this height (keep veins inside the rim).
        frac = 1.0 - (y / (height / 2.0)) ** 2
        frac = max(frac, 0.0)
        rim_x = half_w * (frac ** 0.5)
        vein_len = 0.82 * rim_x  # leave a little gap to the rim
        dx = vein_len
        dy = 0.28 * vein_len  # veins angle up toward the tip
        for sign in (-1, 1):
            ax.plot([0, sign * dx], [y, y + dy],
                    color=ACCENT, linewidth=fin_lw, alpha=0.9, solid_capstyle="round")

    # --- ground bar at the stem base ---
    # Its distance below the leaf grows with leaf_ground_gap.
    gnd_y = y_base - (0.15 + (ground_gap - 2.0) / 10.0 * 0.9)
    gnd_half = half_w * 0.7
    ax.plot([-gnd_half, gnd_half], [gnd_y, gnd_y],
            color="#334155", linewidth=3.0, solid_capstyle="round")
    ax.plot([0, 0], [y_base, gnd_y], color="#334155", linewidth=1.2)  # feed drop

    # Frame with a little padding.
    ax.set_xlim(-half_w - 1.2, half_w + 1.2)
    ax.set_ylim(gnd_y - 0.8, y_top + 0.8)

    ax.set_title(f"{fins} fin pairs - {leaf_length:g} mm", fontsize=9, color="#334155")
    fig.tight_layout(pad=0.3)
    return fig


def _spread(lo: float, hi: float, n: int):
    """n evenly spaced positions in [lo, hi]; handles n==1 gracefully."""
    if n <= 1:
        return [(lo + hi) / 2.0]
    step = (hi - lo) / (n - 1)
    return [lo + i * step for i in range(n)]
