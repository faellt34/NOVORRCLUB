from PIL import Image, ImageDraw

ACCENT = (180, 123, 255)
ACCENT2 = (110, 43, 255)


def brand_mark(size: int, bg=(8, 4, 14), fg=None) -> Image.Image:
    S = 4
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = size * S / 200
    d.ellipse((2 * k, 2 * k, 198 * k, 198 * k), fill=bg + (255,), outline=ACCENT2 + (90,), width=max(1, int(2 * k)))
    w = int(10 * k)
    for cx in (75, 125):
        d.ellipse((cx * k - 50 * k, 50 * k, cx * k + 50 * k, 150 * k), outline=ACCENT + (255,), width=w)
    for cy, r in ((100, 8), (57, 4), (143, 4)):
        d.ellipse((100 * k - r * k, cy * k - r * k, 100 * k + r * k, cy * k + r * k), fill=ACCENT + (255,))
    return im.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import sys
    out = sys.argv[1]
    for s in (192, 512):
        brand_mark(s).save(f"{out}/icon-{s}.png")
