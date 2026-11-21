"""Draw the Compound Shock logo (800x800) and banner (2560x1440)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "fonts")
BG = (11, 14, 20); GRID = (20, 25, 35); FG = (240, 242, 245)
GREEN = (46, 214, 120); YEL = (255, 204, 0); RED = (255, 77, 77); MUTED = (140, 148, 160)


def bolt(cx, cy, s):
    """Lightning bolt polygon centred at (cx, cy), height ~s."""
    pts = [(0.10, -0.50), (-0.28, 0.06), (-0.02, 0.06), (-0.12, 0.50), (0.30, -0.10), (0.04, -0.10), (0.16, -0.50)]
    return [(cx + x * s, cy + y * s) for x, y in pts]


def curve(x0, y0, x1, y1, n=80, k=3.2):
    import math
    pts = []
    for i in range(n + 1):
        t = i / n
        y = (math.exp(k * t) - 1) / (math.exp(k) - 1)
        pts.append((x0 + (x1 - x0) * t, y0 - (y0 - y1) * y))
    return pts


def logo(path, size=800, ss=4):
    S = size * ss
    im = Image.new("RGB", (S, S), BG); d = ImageDraw.Draw(im)
    step = S // 10
    for g in range(0, S, step):
        d.line((g, 0, g, S), fill=GRID, width=ss * 2); d.line((0, g, S, g), fill=GRID, width=ss * 2)
    # compound-growth curve
    c = curve(S * 0.16, S * 0.78, S * 0.84, S * 0.20)
    d.line(c, fill=GREEN, width=int(S * 0.045), joint="curve")
    for p in (c[0], c[-1]):
        r = S * 0.03; d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=GREEN)
    # glow + bolt
    glow = Image.new("L", (S, S), 0); gd = ImageDraw.Draw(glow)
    gd.polygon(bolt(S * 0.5, S * 0.52, S * 0.62), fill=180)
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.03))
    im.paste(Image.new("RGB", (S, S), YEL), (0, 0), glow.point(lambda v: v // 3))
    d = ImageDraw.Draw(im)
    d.polygon(bolt(S * 0.5, S * 0.52, S * 0.62), fill=YEL, outline=BG, width=int(S * 0.012))
    im.resize((size, size), Image.LANCZOS).save(path)


def banner(path, logo_path):
    W, H = 2560, 1440
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    for g in range(0, W, 80): d.line((g, 0, g, H), fill=GRID, width=2)
    for g in range(0, H, 80): d.line((0, g, W, g), fill=GRID, width=2)
    # faint growth curve across the whole banner
    d.line(curve(0, H * 0.97, W, H * 0.30, k=5.0), fill=(24, 58, 42), width=12, joint="curve")
    # safe area (1546 x 423 centred) holds the important stuff
    lg = Image.open(logo_path).resize((300, 300), Image.LANCZOS)
    mask = Image.new("L", (300, 300), 0); ImageDraw.Draw(mask).ellipse((0, 0, 299, 299), fill=255)
    x0 = (W - 1546) // 2 + 40; y0 = (H - 300) // 2
    im.paste(lg, (x0, y0), mask)
    fb = ImageFont.truetype(os.path.join(FONTS, "Inter-Black.otf"), 150)
    fs = ImageFont.truetype(os.path.join(FONTS, "Inter-SemiBold.otf"), 56)
    tx = x0 + 350
    d.text((tx, y0 + 10), "COMPOUND", font=fb, fill=FG)
    d.text((tx + d.textlength("COMPOUND ", font=fb), y0 + 10), "SHOCK", font=fb, fill=YEL)
    d.text((tx + 4, y0 + 200), "The hidden math of money.", font=fs, fill=GREEN)
    d.text((tx + 4, y0 + 270), "New money facts every day.", font=fs, fill=MUTED)
    im.save(path, quality=92)


if __name__ == "__main__":
    lp = os.path.join(HERE, "logo.png"); bp = os.path.join(HERE, "banner.jpg")
    logo(lp); banner(bp, lp); print("ok", lp, bp)
