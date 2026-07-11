"""Generate assets/leaf_icon.ico - a bold, legible teal leaf app icon."""
import os, math
from PIL import Image, ImageDraw, ImageFilter

S = 512
TEAL = (13, 110, 102)       # bg top
TEAL_DK = (9, 66, 60)       # bg bottom
LEAF = (240, 253, 249)      # crisp mint-white leaf
VEIN = (13, 110, 102)       # teal veins cut into the leaf


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def gradient(size, top, bottom):
    g = Image.new("RGB", (size, size), top)
    px = g.load()
    for y in range(size):
        t = y / (size - 1)
        px_row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(size):
            px[x, y] = px_row
    return g


def leaf_pts(cx, cy, half_w, half_h, n=90):
    """Pointed leaf: sharp tip at top, gently rounded at the base."""
    pts = []
    for i in range(n + 1):                      # right edge, base -> tip
        t = i / n
        y = cy + half_h - 2 * half_h * t
        w = half_w * (math.sin(math.pi * t) ** 0.62) * (0.55 + 0.45 * t)
        pts.append((cx + w, y))
    for i in range(n + 1):                       # left edge, tip -> base
        t = 1 - i / n
        y = cy + half_h - 2 * half_h * t
        w = half_w * (math.sin(math.pi * t) ** 0.62) * (0.55 + 0.45 * t)
        pts.append((cx - w, y))
    return pts


def build_leaf_layer():
    """A tilted white leaf with teal midrib + veins, on a transparent layer."""
    L = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    cx, cy = S * 0.5, S * 0.5
    hw, hh = S * 0.20, S * 0.34

    d.polygon(leaf_pts(cx, cy, hw, hh), fill=LEAF)

    # midrib
    mid_w = max(6, int(S * 0.02))
    d.line([(cx, cy - hh + S * 0.02), (cx, cy + hh - S * 0.02)], fill=VEIN, width=mid_w)

    # 4 bold vein pairs angling toward the tip
    vw = max(5, int(S * 0.016))
    for k in range(1, 5):
        t = k / 5.0
        y = cy + hh - 2 * hh * t
        w = hw * (math.sin(math.pi * t) ** 0.62) * (0.55 + 0.45 * t) * 0.8
        dy = w * 0.42
        d.line([(cx, y), (cx + w, y - dy)], fill=VEIN, width=vw)
        d.line([(cx, y), (cx - w, y - dy)], fill=VEIN, width=vw)

    return L.rotate(-20, resample=Image.BICUBIC, center=(cx, cy))


def draw_icon():
    bg = gradient(S, TEAL, TEAL_DK).convert("RGBA")
    bg.putalpha(rounded_mask(S, int(S * 0.23)))

    leaf = build_leaf_layer()
    # soft drop shadow for depth
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sa = leaf.split()[3].point(lambda a: int(a * 0.35))
    shadow.putalpha(sa)
    shadow = shadow.filter(ImageFilter.GaussianBlur(S * 0.02))
    black = Image.new("RGBA", (S, S), (0, 40, 36, 255))
    black.putalpha(shadow.split()[3])
    bg.alpha_composite(black, (int(S * 0.015), int(S * 0.02)))
    bg.alpha_composite(leaf)
    bg.putalpha(rounded_mask(S, int(S * 0.23)))  # re-clip to rounded square

    os.makedirs("assets", exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = [bg.resize((s, s), Image.LANCZOS) for s in sizes]
    icons[0].save("assets/leaf_icon.ico", format="ICO",
                  sizes=[(s, s) for s in sizes], append_images=icons[1:])
    bg.resize((256, 256), Image.LANCZOS).save("assets/leaf_icon.png")
    # small previews to judge legibility
    for s in (32, 48):
        bg.resize((s, s), Image.LANCZOS).save(f"assets/leaf_icon_{s}.png")
    print("wrote assets/leaf_icon.ico + previews")


if __name__ == "__main__":
    draw_icon()
