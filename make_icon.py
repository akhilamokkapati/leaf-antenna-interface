"""Generate assets/leaf_icon.ico - a clean teal leaf app icon."""
import os, math
from PIL import Image, ImageDraw

S = 512  # supersample master size
TEAL = (15, 118, 110)       # #0f766e
TEAL_DK = (11, 79, 73)      # #0b4f49
LEAF = (233, 250, 246)      # near-white mint
VEIN = (15, 118, 110)


def rounded_rect_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def vertical_gradient(size, top, bottom):
    g = Image.new("RGB", (size, size), top)
    px = g.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        gg = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, gg, b)
    return g


def leaf_polygon(cx, cy, half_w, half_h, n=80):
    """A pointed leaf (almond) outline centered at (cx,cy)."""
    pts = []
    for i in range(n + 1):          # right side, tip(top) -> base(bottom)
        t = i / n
        y = cy - half_h + 2 * half_h * t
        w = half_w * math.sin(math.pi * t) ** 0.75
        pts.append((cx + w, y))
    for i in range(n + 1):          # left side back up
        t = 1 - i / n
        y = cy - half_h + 2 * half_h * t
        w = half_w * math.sin(math.pi * t) ** 0.75
        pts.append((cx - w, y))
    return pts


def draw_icon():
    img = vertical_gradient(S, TEAL, TEAL_DK).convert("RGBA")
    img.putalpha(rounded_rect_mask(S, int(S * 0.22)))
    d = ImageDraw.Draw(img)

    cx, cy = S * 0.5, S * 0.47
    hw, hh = S * 0.26, S * 0.36

    # leaf body
    d.polygon(leaf_polygon(cx, cy, hw, hh), fill=LEAF)

    # central vein (stem) + stem down to a small ground bar
    lw = max(3, int(S * 0.018))
    d.line([(cx, cy - hh), (cx, cy + hh + S * 0.10)], fill=VEIN, width=lw)

    # chevron side veins
    for k in range(1, 6):
        t = k / 6.0
        y = cy - hh + 2 * hh * t
        w = hw * math.sin(math.pi * t) ** 0.75 * 0.82
        dy = w * 0.34
        d.line([(cx, y), (cx + w, y - dy)], fill=VEIN, width=max(2, int(S * 0.012)))
        d.line([(cx, y), (cx - w, y - dy)], fill=VEIN, width=max(2, int(S * 0.012)))

    # little ground bar (antenna feed)
    gy = cy + hh + S * 0.10
    d.line([(cx - S * 0.11, gy), (cx + S * 0.11, gy)], fill=LEAF, width=max(4, int(S * 0.024)))

    os.makedirs("assets", exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = [img.resize((s, s), Image.LANCZOS) for s in sizes]
    icons[0].save("assets/leaf_icon.ico", format="ICO",
                  sizes=[(s, s) for s in sizes], append_images=icons[1:])
    img.resize((256, 256), Image.LANCZOS).save("assets/leaf_icon.png")
    print("wrote assets/leaf_icon.ico and .png")


if __name__ == "__main__":
    draw_icon()
