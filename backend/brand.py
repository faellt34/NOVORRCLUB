import math
from PIL import Image, ImageDraw

NODES = [(50, 8), (86, 30), (86, 70), (50, 92), (14, 70), (14, 30), (50, 50), (68, 42), (36, 60)]
LINKS = [(0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (7, 1), (7, 2), (8, 4), (8, 3), (7, 8)]


def brand_mark(size: int, bg=(91, 33, 182), fg=(255, 255, 255)) -> Image.Image:
    S = 4
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = size * S / 100
    d.ellipse((2 * k, 2 * k, 98 * k, 98 * k), fill=bg + (255,))
    for a, b in LINKS:
        d.line((NODES[a][0] * k, NODES[a][1] * k, NODES[b][0] * k, NODES[b][1] * k), fill=fg + (190,), width=max(1, int(1.6 * k)))
    for i, (x, y) in enumerate(NODES):
        r = 7 if i == 6 else 3.5 if i > 6 else 5
        d.ellipse((x * k - r * k, y * k - r * k, x * k + r * k, y * k + r * k), fill=fg + (255,))
    d.ellipse((50 * k - 3.2 * k, 50 * k - 3.2 * k, 50 * k + 3.2 * k, 50 * k + 3.2 * k), fill=bg + (255,))
    return im.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    out = sys.argv[1]
    for s in (192, 512):
        brand_mark(s).save(f"{out}/icon-{s}.png")
