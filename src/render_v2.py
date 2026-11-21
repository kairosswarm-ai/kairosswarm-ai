"""Compound Shock v2 renderer: AI images with motion, punchy captions, overlays, SFX cues.
1080x1920 @30fps, frames piped into ffmpeg. Text stays inside the Shorts safe zone."""
import math, os, re, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(ROOT, "fonts"))
FB = os.path.join(FONT_DIR, "Inter-Black.otf"); FS = os.path.join(FONT_DIR, "Inter-SemiBold.otf")
FM = os.path.join(FONT_DIR, "Inter-Medium.otf")
WHITE = (250, 250, 250); BLACK = (12, 12, 16); BRAND = (255, 204, 0)
COLORS = {"red": (255, 72, 72), "green": (40, 220, 120), "yellow": BRAND, "white": WHITE,
          "blue": (70, 160, 255), "orange": (255, 140, 40)}
PALETTES = [  # (accent, caption highlight)
    (BRAND, BRAND), ((40, 220, 120), BRAND), ((255, 72, 72), BRAND), ((70, 160, 255), BRAND), ((255, 140, 40), WHITE)]
CAPTION_STYLES = ["pop", "chunk", "box"]
_fc = {}
NON_BMP = re.compile("[\U00010000-\U0010FFFF☀-➿️]")


def F(p, s):
    k = (p, int(s))
    if k not in _fc: _fc[k] = ImageFont.truetype(p, int(s))
    return _fc[k]


def clean(t):
    return NON_BMP.sub("", str(t or "")).strip()


def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def back(x):  # overshoot ease for pops
    x = max(0.0, min(1.0, x)); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def col(n, d="white"): return COLORS.get(str(n).lower(), COLORS[d])


def text_w(d, t, f): return d.textlength(t, font=f)


def fit(d, t, p, s, maxw, mn=28):
    while s > mn and text_w(d, t, F(p, s)) > maxw: s -= 4
    return F(p, s)


def wrap(d, t, f, maxw):
    out, cur = [], ""
    for w in t.split():
        x = (cur + " " + w).strip()
        if text_w(d, x, f) <= maxw: cur = x
        else:
            if cur: out.append(cur)
            cur = w
    if cur: out.append(cur)
    return out


def stroke_text(d, xy, t, f, fill, sw=8, sc=BLACK):
    d.text(xy, t, font=f, fill=fill, stroke_width=sw, stroke_fill=sc)


def ctext(d, y, t, p, s, fill, maxw=W - 140, sw=8):
    t = clean(t); f = fit(d, t, p, s, maxw)
    stroke_text(d, ((W - text_w(d, t, f)) / 2, y), t, f, fill, sw)
    return f.size


def fmt(v, pre="", suf="", dec=0):
    try: return f"{pre}{float(v):,.{int(dec)}f}{suf}"
    except Exception: return f"{pre}{v}{suf}"


# ---------------- image helpers ----------------
def cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x = (im.width - w) // 2; y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def kenburns(im, p, motion, w=W, h=H):
    """im is pre-scaled to 1.18x the frame. p in 0..1 (linear drift looks most natural)."""
    zz0, zz1, dx, dy = 1.02, 1.16, 0.0, 0.0
    if motion == "zoom_out": zz0, zz1 = 1.16, 1.02
    elif motion in ("pan_left", "pan_right", "pan_up"):
        zz0 = zz1 = 1.12; dx = 1 if motion == "pan_left" else (-1 if motion == "pan_right" else 0); dy = 1 if motion == "pan_up" else 0
    zz = zz0 + (zz1 - zz0) * p
    cw, ch = int(im.width / zz), int(im.height / zz)
    mx, my = im.width - cw, im.height - ch
    x = mx / 2 + dx * (p - 0.5) * mx * 0.9; y = my / 2 + dy * (p - 0.5) * my * 0.9
    x = max(0, min(mx, x)); y = max(0, min(my, y))
    return im.crop((int(x), int(y), int(x) + cw, int(y) + ch)).resize((w, h), Image.BILINEAR)


def prep(im, w=W, h=H):
    return cover(im, int(w * 1.18), int(h * 1.18))


_SHADE = None


def darken(img, top=0.35, bottom=0.65):
    """Gradient shade so white text always reads (mask built once)."""
    global _SHADE
    if _SHADE is None:
        g = Image.new("L", (1, H))
        for y in range(H):
            t = y / H
            g.putpixel((0, y), int(255 * min(0.85, top * (1 - t) ** 2 + bottom * t ** 1.5)))
        _SHADE = (g.resize((W, H)), Image.new("RGB", (W, H), (0, 0, 0)))
    return Image.composite(_SHADE[1], img, _SHADE[0])


# ---------------- captions ----------------
def caption(d, txt, p, style, hl):
    txt = clean(txt)
    if not txt: return
    words = txt.split(); n = len(words)
    k = min(n, max(1, math.ceil(p * n * 1.06)))
    Y = 1180
    if style == "chunk":  # 2-3 big words at a time
        size = 3 if n > 6 else 2
        start = ((k - 1) // size) * size
        chunk = " ".join(words[start:start + size]).upper()
        local = ((p * n * 1.06) - start) / size
        s = 0.85 + 0.15 * back(min(1, local * 3))
        f = fit(d, chunk, FB, int(104 * s), W - 120)
        stroke_text(d, ((W - text_w(d, chunk, f)) / 2, Y), chunk, f, hl if (start // size) % 2 else WHITE, 10)
        return
    f = F(FB, 64)
    lines = wrap(d, txt, f, W - 170)[:3]
    if style == "box":  # whole line visible, current word boxed
        idx = 0; y = Y
        for ln in lines:
            x = (W - text_w(d, ln, f)) / 2
            for w in ln.split():
                ww = text_w(d, w, f)
                if idx == k - 1:
                    d.rounded_rectangle((x - 10, y - 6, x + ww + 10, y + 78), 14, fill=hl)
                    d.text((x, y), w, font=f, fill=BLACK)
                else:
                    stroke_text(d, (x, y), w, f, WHITE if idx < k else (200, 200, 200), 7)
                x += text_w(d, w + " ", f); idx += 1
            y += 90
        return
    idx = 0; y = Y  # pop: words appear one by one, current one highlighted and bigger
    for ln in lines:
        x = (W - text_w(d, ln, f)) / 2
        for w in ln.split():
            if idx < k:
                if idx == k - 1:
                    fb = F(FB, 72)
                    stroke_text(d, (x - 4, y - 5), w, fb, hl, 8)
                else:
                    stroke_text(d, (x, y), w, f, WHITE, 8)
            x += text_w(d, w + " ", f); idx += 1
        y += 86


# ---------------- scene painters ----------------
def overlay_number(d, ov, p, acc):
    if not ov: return
    v = ov.get("value", 0)
    try: shown = float(v) * ease(p * 2.2)
    except Exception: shown = v
    s = back(min(1, p * 4))
    lab = clean(ov.get("label", ""))
    if lab: ctext(d, 470, lab, FB, 56, WHITE, sw=7)
    size = int(210 * max(0.3, s))
    ctext(d, 560, fmt(shown, ov.get("prefix", ""), ov.get("suffix", ""), ov.get("decimals", 0)), FB, size,
          col(ov.get("color", "yellow"), "yellow"), sw=12)
    if ov.get("note"): ctext(d, 820, ov["note"], FS, 38, (230, 230, 230), sw=5)


def headline(d, t, p):
    t = clean(t).upper()
    if not t: return
    f = F(FB, 92); lines = wrap(d, t, f, W - 140)[:3]
    s = back(min(1, p * 4)); y = 380
    for ln in lines:
        ff = fit(d, ln, FB, int(92 * max(0.4, s)), W - 140)
        stroke_text(d, ((W - text_w(d, ln, ff)) / 2, y), ln, ff, WHITE, 10); y += 104


def s_image(frame, d, s, p, t, imgs, acc):
    if s.get("overlay") and s.get("headline"):
        hl_ = clean(s["headline"]).upper()
        ctext(d, 330, hl_, FB, int(76 * max(0.4, back(min(1, p * 4)))), WHITE, sw=9)
        overlay_number(d, s.get("overlay"), p, acc)
        return
    headline(d, s.get("headline", ""), p)
    overlay_number(d, s.get("overlay"), p, acc)


def s_versus(frame, d, s, p, t, imgs, acc):
    # two images stacked, each with label + rows
    for i, side in enumerate([s.get("left", {}), s.get("right", {})]):
        y0 = 250 + i * 455; e = ease(p * 2.5 - i * 0.4)
        if e <= 0: continue
        im = imgs.get(f"v{i}")
        x_off = int((1 - e) * (W if i == 0 else -W))
        box = (60 + x_off, y0, W - 60 + x_off, y0 + 420)
        if im is not None:
            tile = cover(im, box[2] - box[0], 420)
            tile = ImageEnhance.Brightness(tile).enhance(0.55)
            m = Image.new("L", tile.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, tile.width - 1, 419), 36, fill=255)
            frame.paste(tile, (box[0], box[1]), m)
        c = col(side.get("color", "red" if i == 0 else "green"))
        d.rounded_rectangle(box, 36, outline=c, width=8)
        lab = clean(side.get("label", "")).upper()
        stroke_text(d, (box[0] + 40, y0 + 26), lab, fit(d, lab, FB, 74, 880), c, 8)
        for j, row in enumerate((side.get("rows") or [])[:3]):
            k_, v_ = (list(row) + ["", ""])[:2]
            stroke_text(d, (box[0] + 40, y0 + 140 + j * 92), clean(k_), F(FS, 44), WHITE, 6)
            vf = fit(d, clean(v_), FB, 70, 420)
            stroke_text(d, (box[2] - 40 - text_w(d, clean(v_), vf), y0 + 128 + j * 92), clean(v_), vf, WHITE, 8)
    if s.get("title"):
        ctext(d, 140, s["title"], FB, 68, BRAND, sw=9)
    vs = back(min(1, p * 3))
    if vs > 0.1:
        r = int(64 * vs); cx, cy = W // 2, 250 + 437
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BRAND, outline=BLACK, width=6)
        f = F(FB, int(56 * vs)); d.text((cx - text_w(d, "VS", f) / 2, cy - f.size * 0.62), "VS", font=f, fill=BLACK)


def s_receipt(frame, d, s, p, t, imgs, acc):
    items = (s.get("items") or [])[:5]
    n = len(items) + 2
    shown = int(min(n, p * n * 1.5 + 1))
    x0, x1 = 150, W - 150; y0 = 260
    h = 170 + shown * 110 + 60
    # paper with zigzag bottom
    d.rectangle((x0, y0, x1, y0 + h), fill=(250, 248, 240))
    for x in range(x0, x1, 30):
        d.polygon([(x, y0 + h), (x + 15, y0 + h + 22), (x + 30, y0 + h)], fill=(250, 248, 240))
    title = clean(s.get("title", "RECEIPT")).upper()
    f = fit(d, title, FB, 60, x1 - x0 - 60)
    d.text(((W - text_w(d, title, f)) / 2, y0 + 40), title, font=f, fill=BLACK)
    d.line((x0 + 40, y0 + 140, x1 - 40, y0 + 140), fill=(150, 150, 150), width=3)
    y = y0 + 170
    for i, it in enumerate(items[:max(0, shown - 1)]):
        a, b = (list(it) + ["", ""])[:2]
        vf = fit(d, clean(b), FB, 48, 300); vw = text_w(d, clean(b), vf)
        d.text((x0 + 40, y), clean(a), font=fit(d, clean(a), FS, 44, x1 - x0 - 120 - vw), fill=(60, 60, 60))
        d.text((x1 - 40 - vw, y - 2), clean(b), font=vf, fill=BLACK); y += 110
    if shown >= n and s.get("total"):
        a, b = (list(s["total"]) + ["", ""])[:2]
        d.line((x0 + 40, y - 20, x1 - 40, y - 20), fill=BLACK, width=4)
        vf = fit(d, clean(b), FB, 64, 340); vw = text_w(d, clean(b), vf)
        d.text((x0 + 40, y), clean(a).upper(), font=fit(d, clean(a).upper(), FB, 52, x1 - x0 - 120 - vw), fill=BLACK)
        d.text((x1 - 40 - vw, y - 8), clean(b), font=vf, fill=COLORS["red"])


def s_list_item(frame, d, s, p, t, imgs, acc):
    num = str(s.get("number", ""))
    sc = back(min(1, p * 4))
    r = int(120 * sc); cx, cy = W // 2, 470
    if r > 4:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=acc, outline=BLACK, width=8)
        f = F(FB, int(150 * sc)); d.text((cx - text_w(d, num, f) / 2, cy - f.size * 0.62), num, font=f, fill=BLACK)
    t_ = clean(s.get("headline", "")).upper()
    f = F(FB, 84); y = 640
    for ln in wrap(d, t_, f, W - 140)[:3]:
        ff = fit(d, ln, FB, 84, W - 140); stroke_text(d, ((W - text_w(d, ln, ff)) / 2, y), ln, ff, WHITE, 10); y += 98
    overlay = s.get("overlay")
    if overlay: ctext(d, y + 20, fmt(overlay.get("value", 0), overlay.get("prefix", ""), overlay.get("suffix", "")),
                      FB, 120, col(overlay.get("color", "yellow"), "yellow"), sw=10)


def s_quiz(frame, d, s, p, t, imgs, acc):
    ctext(d, 260, "GUESS", FB, 70, BRAND, sw=8)
    q = clean(s.get("question", ""))
    f = F(FB, 70); y = 360
    for ln in wrap(d, q, f, W - 140)[:3]:
        ff = fit(d, ln, FB, 70, W - 140); stroke_text(d, ((W - text_w(d, ln, ff)) / 2, y), ln, ff, WHITE, 9); y += 84
    opts = (s.get("options") or [])[:3]; ans = int(s.get("answer_index", 0) or 0)
    reveal = p > 0.62
    for i, o in enumerate(opts):
        e = ease(p * 4 - i * 0.4)
        if e <= 0: continue
        by = y + 40 + i * 150; bx0, bx1 = 140, W - 140
        good = reveal and i == ans; bad = reveal and i != ans
        fill = COLORS["green"] if good else ((60, 60, 70) if bad else (25, 25, 32))
        d.rounded_rectangle((bx0, by, bx1, by + 120), 28, fill=fill, outline=BRAND if not reveal else fill, width=5)
        lab = f"{'ABC'[i]}   {clean(o)}"
        d.text((bx0 + 40, by + 28), lab, font=fit(d, lab, FB, 58, bx1 - bx0 - 80), fill=BLACK if good else WHITE)
    if not reveal:
        left = max(0, 3 - int(p / 0.62 * 3))
        ctext(d, y + 520, str(left if left else "!"), FB, 120, BRAND, sw=10)


def s_cta(frame, d, s, p, t, imgs, acc, logo=None):
    if logo is not None:
        sc = back(min(1, p * 3)); size = int(300 * max(0.2, sc))
        lg = logo.resize((size, size), Image.LANCZOS)
        m = Image.new("L", (size, size), 0); ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
        frame.paste(lg, (W // 2 - size // 2, 330 - size // 2 + 150), m)
    ctext(d, 680, s.get("line1", "FOLLOW + LIKE"), FB, 100, WHITE, sw=10)
    l2 = clean(s.get("line2", "Comment your money question"))
    f = F(FB, 62); y = 820
    for ln in wrap(d, l2, f, W - 160)[:2]:
        ff = fit(d, ln, FB, 62, W - 160); stroke_text(d, ((W - text_w(d, ln, ff)) / 2, y), ln, ff, BRAND, 8); y += 76
    # bouncing arrow pointing down to the comments
    a = 16 * math.sin(t * 7); cx = W // 2; ay = y + 40 + a
    d.polygon([(cx - 60, ay), (cx + 60, ay), (cx, ay + 70)], fill=BRAND, outline=BLACK)


PAINT = {"image": s_image, "versus": s_versus, "receipt": s_receipt, "list_item": s_list_item,
         "quiz": s_quiz, "cta": s_cta}


def sfx_events(scenes, segs):
    ev = []
    for i, (s, (a, b)) in enumerate(zip(scenes, segs)):
        ty = s.get("type")
        if i > 0: ev.append((max(0, a - 0.25), "whoosh"))
        if ty == "image" and s.get("overlay"): ev.append((a + 0.05, "hit")); ev.append((a + 0.9, "ding"))
        if ty == "image" and s.get("headline"): ev.append((a + 0.02, "pop"))
        if ty == "versus": ev.append((a + 0.1, "hit"))
        if ty == "receipt":
            n = len(s.get("items") or []) + 2
            for k in range(n): ev.append((a + (b - a) * k / (n * 1.5), "tick"))
            ev.append((a + (b - a) * 0.75, "cash"))
        if ty == "list_item": ev.append((a + 0.05, "pop"))
        if ty == "quiz": ev.append((a + (b - a) * 0.62, "ding"))
        if ty == "cta": ev.append((a + 0.05, "pop"))
    return ev


def render(scenes, segs, audio_path, out_path, total, images, style_idx=0, logo_path=None):
    """images: {scene_index: PIL image or {'v0':..,'v1':..}} ; style_idx picks palette + caption style."""
    acc, hl = PALETTES[style_idx % len(PALETTES)]
    cap_style = CAPTION_STYLES[style_idx % len(CAPTION_STYLES)]
    logo = Image.open(logo_path).convert("RGB") if logo_path and os.path.exists(logo_path) else None
    bug = None
    if logo is not None:
        bug = logo.resize((92, 92), Image.LANCZOS)
        bm = Image.new("L", (92, 92), 0); ImageDraw.Draw(bm).ellipse((0, 0, 91, 91), fill=220)
    pre = {}
    for i, s in enumerate(scenes):
        im = images.get(i)
        if isinstance(im, Image.Image):
            pre[i] = prep(im)
        elif isinstance(im, dict) and im.get("bg") is not None:
            pre[i] = prep(im["bg"])
    motions = ["zoom_in", "pan_left", "zoom_out", "pan_up", "pan_right"]
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio_path,
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path],
                            stdin=subprocess.PIPE)
    nf = int(total * FPS); last_bg = None
    for fi in range(nf):
        tt = fi / FPS; k = 0
        for i, (a, b) in enumerate(segs):
            if tt >= a - 0.12: k = i
        a, b = segs[k]; s = scenes[k]
        p = max(0.0, min(1.0, (tt - a) / max(0.1, b - a)))
        if k in pre:
            frame = kenburns(pre[k], p, s.get("motion") or motions[k % len(motions)])
            last_bg = frame
        elif last_bg is not None:
            frame = last_bg.copy()
        else:
            frame = Image.new("RGB", (W, H), (16, 16, 22))
        if s.get("type") in ("receipt", "quiz", "cta", "versus"):
            frame = frame.filter(ImageFilter.GaussianBlur(14)) if k in pre else frame
            frame = ImageEnhance.Brightness(frame).enhance(0.55)
        frame = darken(frame)
        # punch-in on scene start
        local = tt - a
        if 0 <= local < 0.2 and k > 0:
            z = 1.0 + 0.06 * (1 - local / 0.2)
            cw, ch = int(W / z), int(H / z)
            frame = frame.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.BILINEAR)
        d = ImageDraw.Draw(frame)
        try:
            if s.get("type") == "cta":
                s_cta(frame, d, s, p, local, images.get(k) or {}, acc, logo=logo)
            else:
                PAINT.get(s.get("type"), s_image)(frame, d, s, p, local, images.get(k) if isinstance(images.get(k), dict) else {}, acc)
        except Exception:
            pass
        if s.get("type") not in ("cta",):
            caption(d, s.get("caption") or s.get("voice", ""), p, cap_style, hl)
        if bug is not None:
            frame.paste(bug, (48, 150), bm)
        if s.get("type") == "image" and s.get("overlay") and 0 <= local < 0.08:
            frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 255, 255)), 0.35)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
