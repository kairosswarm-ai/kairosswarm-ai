"""Render a vertical Short (1080x1920, 30fps) from script scenes + voice timings.
Frames are piped straight into ffmpeg. No progress bar, no watermark."""
import math, os, subprocess
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts"))
FB = os.path.join(FONT_DIR, "Inter-Black.otf")
FS = os.path.join(FONT_DIR, "Inter-SemiBold.otf")
FM = os.path.join(FONT_DIR, "Inter-Medium.otf")
BG = (11, 14, 20); FG = (240, 242, 245); MUTED = (140, 148, 160); GRID = (16, 20, 28)
COL = {"red": (255, 77, 77), "green": (46, 214, 120), "yellow": (255, 204, 0), "white": FG, "muted": MUTED}
YEL = COL["yellow"]
_fc = {}


def F(path, size):
    k = (path, int(size))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, int(size))
    return _fc[k]


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def col(name, default="white"):
    return COL.get(str(name).lower(), COL[default])


def fit(d, txt, path, size, maxw):
    """Shrink font until text fits maxw."""
    while size > 24 and d.textlength(txt, font=F(path, size)) > maxw:
        size -= 4
    return F(path, size)


def center(d, y, txt, path, size, fill, maxw=W - 120):
    txt = str(txt)
    f = fit(d, txt, path, size, maxw)
    w = d.textlength(txt, font=f)
    d.text(((W - w) / 2, y), txt, font=f, fill=fill)


def wrap(d, txt, font, maxw):
    words, lines, cur = str(txt).split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = wd
    if cur: lines.append(cur)
    return lines


def fmt(v, prefix="", suffix="", decimals=0):
    try:
        v = float(v)
    except Exception:
        return f"{prefix}{v}{suffix}"
    s = f"{v:,.{int(decimals)}f}"
    return f"{prefix}{s}{suffix}"


def card(d, x, y, w, h, c):
    d.rounded_rectangle((x, y, x + w, y + h), 36, fill=(22, 27, 37), outline=c, width=4)


def caption(d, txt, p):
    font = F(FB, 60)
    lines = wrap(d, txt, font, W - 160)[:4]
    words = " ".join(lines).split(); n = max(1, len(words))
    shown = max(1, math.ceil(min(1, p * 1.08) * n))
    y = 1440 if len(lines) <= 3 else 1400; idx = 0
    for ln in lines:
        x = (W - d.textlength(ln, font=font)) / 2
        for wd in ln.split():
            if idx < shown:
                c = YEL if idx == shown - 1 else FG
                d.text((x + 3, y + 4), wd, font=font, fill=(0, 0, 0))
                d.text((x, y), wd, font=font, fill=c)
            x += d.textlength(wd + " ", font=font); idx += 1
        y += 76


# ---------------- scene painters ----------------
def s_title(d, s, p, t):
    center(d, 330, s.get("line1", ""), FB, 110, FG)
    center(d, 460, s.get("line2", ""), FB, 110, col(s.get("accent", "red"), "red"))


def s_big_number(d, s, p, t):
    center(d, 380, s.get("label", ""), FS, 54, MUTED)
    v = s.get("value", 0)
    try: shown = float(v) * ease(p * 1.6)
    except Exception: shown = v
    center(d, 470, fmt(shown, s.get("prefix", ""), s.get("suffix", ""), s.get("decimals", 0)), FB, 240, col(s.get("color", "white")))
    if s.get("note"): center(d, 820, s["note"], FM, 40, MUTED)


def s_compare(d, s, p, t):
    center(d, 200, s.get("title", ""), FB, 70, FG)
    for i, side in enumerate([s.get("left", {}), s.get("right", {})]):
        y = 340 + i * 480; c = col(side.get("color", "red" if i == 0 else "green"))
        e = ease(p * 1.8 - i * 0.35)
        if e <= 0: continue
        card(d, 110, y, 860, 420, c)
        d.text((160, y + 36), str(side.get("label", "")), font=fit(d, str(side.get("label", "")), FB, 64, 760), fill=c)
        for j, row in enumerate((side.get("rows") or [])[:3]):
            k, v = (row + ["", ""])[:2]
            d.text((160, y + 140 + j * 90), str(k), font=F(FM, 40), fill=MUTED)
            vf = fit(d, str(v), FB, 60, 330)
            d.text((930 - d.textlength(str(v), font=vf), y + 128 + j * 90), str(v), font=vf, fill=FG)
    if s.get("footer") and p > 0.5: center(d, 1310, s["footer"], FB, 58, COL["green"])


def s_bars(d, s, p, t):
    center(d, 220, s.get("title", ""), FB, 72, FG)
    items = (s.get("items") or [])[:5]
    if not items: return
    vals = [abs(float(i.get("value", 0) or 0)) for i in items]; mx = max(vals) or 1
    base, maxh = 1180, 760; n = len(items)
    bw = min(220, int((W - 200) / n) - 40); gap = (W - 160 - n * bw) / max(1, n)
    for k, it in enumerate(items):
        e = ease(p * 1.6 - k * 0.12)
        h = maxh * vals[k] / mx * e
        x = 80 + gap / 2 + k * (bw + gap)
        d.rounded_rectangle((x, base - h, x + bw, base), 18, fill=col(it.get("color", "white")))
        lab = str(it.get("label", ""))
        lf = fit(d, lab, FM, 36, bw + gap - 10)
        d.text((x + bw / 2 - d.textlength(lab, font=lf) / 2, base + 18), lab, font=lf, fill=FG)
        if e > 0.5:
            vt = fmt(it.get("value", 0), s.get("prefix", ""), s.get("suffix", ""))
            vf = fit(d, vt, FB, 44, bw + gap - 10)
            d.text((x + bw / 2 - d.textlength(vt, font=vf) / 2, base - h - 60), vt, font=vf, fill=FG)
    if s.get("note"): center(d, 1290, s["note"], FM, 34, MUTED)


def s_timeline(d, s, p, t):
    center(d, 300, s.get("label", ""), FS, 54, MUTED)
    yrs = float(s.get("years", 0) or 0); e = ease(p * 1.4)
    center(d, 390, f"{yrs * e:.0f} YEARS", FB, 190, COL["red"])
    x0, x1, y = 120, 960, 760
    d.rounded_rectangle((x0, y, x1, y + 50), 25, fill=(35, 40, 52))
    d.rounded_rectangle((x0, y, x0 + max(50, (x1 - x0) * e), y + 50), 25, fill=COL["red"])
    sy = int(s.get("start_year", 2026))
    d.text((x0, y + 70), str(sy), font=F(FM, 40), fill=MUTED)
    ey = str(sy + int(round(yrs)))
    d.text((x1 - d.textlength(ey, font=F(FM, 40)), y + 70), ey, font=F(FM, 40), fill=MUTED)


def s_statement(d, s, p, t):
    lines = (s.get("lines") or [])[:3]
    acc = s.get("accent_line", -1); ac = col(s.get("accent", "green"), "green")
    y = 460 if len(lines) <= 2 else 400
    for i, ln in enumerate(lines):
        center(d, y, ln, FB, 170 if len(lines) <= 2 else 130, ac if i == acc else FG)
        y += 200 if len(lines) <= 2 else 160
    if s.get("sub"): center(d, y + 30, s["sub"], FS, 60, YEL)


def s_cta(d, s, p, t):
    center(d, 600, s.get("line1", ""), FB, 110, FG)
    center(d, 740, s.get("line2", ""), FB, 110, COL["green"])
    r = 70 + 8 * math.sin(t * 6)
    d.ellipse((W / 2 - r, 980 - r, W / 2 + r, 980 + r), fill=COL["red"])
    center(d, 940, "+", FB, 80, FG)


PAINT = {"title": s_title, "big_number": s_big_number, "compare": s_compare, "bars": s_bars,
         "timeline": s_timeline, "statement": s_statement, "cta": s_cta}


def render(scenes, segs, audio_path, out_path, total):
    """segs: list of (start, end) per scene, in seconds."""
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio_path,
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path],
                            stdin=subprocess.PIPE)
    bg = Image.new("RGB", (W, H), BG); bd = ImageDraw.Draw(bg)
    for gx in range(0, W, 90): bd.line((gx, 0, gx, H), fill=GRID)
    for gy in range(0, H, 90): bd.line((0, gy, W, gy), fill=GRID)
    nf = int(total * FPS)
    for fi in range(nf):
        tt = fi / FPS
        k = 0
        for i, (a, b) in enumerate(segs):
            if tt >= a - 0.15: k = i
        a, b = segs[k]; s = scenes[k]
        p = max(0.0, min(1.0, (tt - a) / max(0.1, b - a)))
        img = bg.copy(); d = ImageDraw.Draw(img)
        try:
            PAINT.get(s.get("type"), s_statement)(d, s, p, tt - a)
        except Exception as e:  # a malformed scene must not kill the video
            center(d, 600, str(s.get("caption", ""))[:40], FB, 80, FG)
        caption(d, s.get("caption") or s.get("voice", ""), p)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
