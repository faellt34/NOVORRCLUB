import math
import os
import random
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

MEDIA_DIR = Path(__file__).parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)
FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _noise(x, y, z):
    return math.sin(x * 3.1 + y * 1.7) * math.cos(z * 2.9 - x * 1.3) + math.sin((x + z) * 5.3) * 0.5 + math.cos(y * 4.7 + z * 2.1) * 0.6


def render_story(out_path: Path, name: str, handle: str, coupon: str, discount: float, partner: str, site: str = "rrclub.online", W=720, H=1280, F=90):
    rnd = random.Random(7)
    pts = []
    N = 6000
    for i in range(N * 2):
        y = 1 - (i / (N * 2 - 1)) * 2
        r = math.sqrt(max(0, 1 - y * y))
        th = i * 2.399963
        j = lambda: (rnd.random() - 0.5) * 0.035
        p = (r * math.cos(th) + j(), y + j(), r * math.sin(th) + j())
        nv = _noise(*p)
        if nv > 0.15 or (nv > -0.4 and i % 3 == 0) or i % 9 == 0:
            pts.append(p)
    links = [(rnd.randrange(len(pts)), rnd.randrange(len(pts)), rnd.random() * 6) for _ in range(18)]
    stars = [(rnd.random() * W, rnd.random() * H, rnd.random()) for _ in range(200)]
    fbig = ImageFont.truetype(FB, 80); flogo = ImageFont.truetype(FB, 72); fname = ImageFont.truetype(FB, 40)
    fsm = ImageFont.truetype(FR, 30); fcoupon = ImageFont.truetype(FB, 46); ftag = ImageFont.truetype(FR, 24)
    ov = Image.new("RGB", (W, H), (91, 33, 182))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse([-W * 0.9, -H * 0.15, W * 0.75, H * 1.15], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(45))
    tmp = tempfile.mkdtemp()
    for f in range(F):
        t = f / F * 2 * math.pi
        img = Image.new("RGB", (W, H), (8, 6, 24)); img.paste(ov, (0, 0), mask); d = ImageDraw.Draw(img)
        for sx, sy, ph in stars:
            c = int(255 * (0.4 + 0.6 * abs(math.sin(t * 3 + ph * 6)))); d.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=(c, c, c))
        cx, cy, R = W / 2, H * 0.47, W * 0.4

        def proj(p):
            x = p[0] * math.cos(t) - p[2] * math.sin(t); z = p[0] * math.sin(t) + p[2] * math.cos(t); s = 1 / (1.7 - z * 0.45)
            return (cx + x * R * s, cy + p[1] * R * s, z, s)
        for p in pts:
            x, y, z, s = proj(p)
            if z < -0.05:
                continue
            a = min(1, 0.45 + z * 0.7); c = int(120 + 135 * a); sz = 1.8 * s
            d.rectangle([x - sz, y - sz, x + sz, y + sz], fill=(c, c, 255))
        for a_, b_, ph0 in links:
            ax, ay, az, _ = proj(pts[a_]); bx, by, bz, _ = proj(pts[b_])
            if az < 0 or bz < 0:
                continue
            ph = (f / F * 12 + ph0) % 6; k = min(1, ph / 3); fade = 1 - (ph - 3) / 3 if ph > 3 else 1; c = int(255 * fade)
            mx = (ax + bx) / 2 + (ay - by) * 0.25; my = (ay + by) / 2 - abs(ax - bx) * 0.25
            seg = [((1 - u) ** 2 * ax + 2 * (1 - u) * u * mx + u * u * bx, (1 - u) ** 2 * ay + 2 * (1 - u) * u * my + u * u * by) for u in [i / 30 for i in range(int(30 * k) + 1)]]
            if len(seg) > 1:
                d.line(seg, fill=(c, c, c), width=3)
            d.ellipse([ax - 4, ay - 4, ax + 4, ay + 4], fill=(c, c, c))
        from brand import brand_mark
        mk = brand_mark(104, bg=(124, 58, 237)); img.paste(mk, (int(W / 2 - 52), 110), mk)
        d.text((W / 2, 272), "RRclub", font=flogo, fill="white", anchor="mm"); d.text((W / 2, 322), "L U X U R Y   E X P E R I E N C E S", font=ftag, fill=(216, 180, 254), anchor="mm")
        d.text((W / 2, H - 330), name, font=fname, fill="white", anchor="mm")
        if handle:
            d.text((W / 2, H - 288), handle, font=fsm, fill=(216, 180, 254), anchor="mm")
        pulse = 1 + 0.03 * math.sin(t * 2)
        bw, bh = 300 * pulse, 70 * pulse
        d.rounded_rectangle([W / 2 - bw, H - 235 - bh / 2, W / 2 + bw, H - 235 + bh / 2], radius=18, fill=(124, 58, 237))
        d.text((W / 2, H - 235), coupon, font=fcoupon, fill="white", anchor="mm")
        d.text((W / 2, H - 165), f"{discount:g}% OFF em {partner}", font=fsm, fill="white", anchor="mm")
        d.text((W / 2, H - 90), f"{site}/c/{coupon}", font=fsm, fill=(251, 191, 36), anchor="mm")
        img.save(f"{tmp}/f{f:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", f"{tmp}/f%04d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-movflags", "+faststart", str(out_path)], check=True)
    for p in Path(tmp).glob("*.png"):
        p.unlink()
    os.rmdir(tmp)
    return out_path
