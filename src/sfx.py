"""Sound effects and a soft background bed, synthesised from scratch (no licensing issues)."""
import numpy as np, soundfile as sf

SR = 48000


def _env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))
    return e


def whoosh(d=0.45):
    n = int(SR * d); noise = np.random.randn(n)
    # sweep a simple one-pole low-pass from dark to bright and back
    out = np.zeros(n); y = 0.0
    for i in range(n):
        c = 0.02 + 0.5 * np.sin(np.pi * i / n) ** 2
        y += c * (noise[i] - y); out[i] = y
    return 0.5 * out * np.sin(np.pi * np.arange(n) / n)


def pop(f=880, d=0.12):
    n = int(SR * d); t = np.arange(n) / SR
    return 0.5 * np.sin(2 * np.pi * f * t * (1 + 0.6 * np.exp(-t * 40))) * _env(n, 0.002, 0.04)


def ding(f=1320, d=0.9):
    n = int(SR * d); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) + 0.25 * np.sin(2 * np.pi * f * 5.4 * t)
    return 0.3 * s * _env(n, 0.002, 0.25)


def hit(d=0.5):
    n = int(SR * d); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (55 + 120 * np.exp(-t * 18)) * t) * _env(n, 0.001, 0.18)
    return 0.8 * body + 0.15 * np.random.randn(n) * _env(n, 0.001, 0.03)


def cash(d=0.8):
    return np.concatenate([0.4 * np.random.randn(int(SR * 0.05)) * _env(int(SR * 0.05), 0.001, 0.02),
                           np.zeros(int(SR * 0.03)), ding(2100, d)])


def tick(d=0.05):
    n = int(SR * d)
    return 0.25 * np.random.randn(n) * _env(n, 0.0005, 0.008)


SOUNDS = {"whoosh": whoosh, "pop": pop, "ding": ding, "hit": hit, "cash": cash, "tick": tick}

PROGRESSIONS = [  # semitone offsets of chord roots, all gentle
    [0, 5, 9, 7], [0, 9, 5, 7], [0, 7, 9, 5], [0, 3, 8, 10], [0, 8, 3, 10],
]


def music_bed(total, seed=0, bpm=88):
    """Soft pad + light kick/hat, mixed far under the voice."""
    rng = np.random.default_rng(seed)
    n = int(SR * total); out = np.zeros(n)
    root = 110 * 2 ** (rng.integers(0, 7) / 12)
    prog = PROGRESSIONS[int(rng.integers(0, len(PROGRESSIONS)))]
    minor = bool(rng.integers(0, 2))
    beat = 60 / bpm; bar = 4 * beat
    t_all = np.arange(n) / SR
    for i in range(int(total / bar) + 1):
        s0 = int(i * bar * SR); s1 = min(n, int((i + 1) * bar * SR))
        if s0 >= n: break
        f = root * 2 ** (prog[i % len(prog)] / 12)
        third = 3 if minor else 4
        t = t_all[s0:s1] - i * bar
        chord = sum(np.sin(2 * np.pi * f * 2 ** (k / 12) * t) for k in (0, third, 7, 12)) / 4
        fade = np.minimum(1, t / 0.6) * np.minimum(1, (bar - t) / 0.6)
        out[s0:s1] += 0.25 * chord * fade
    for k in range(int(total / beat)):
        s = int(k * beat * SR)
        kick = hit(0.3) * 0.35
        if k % 2 == 0 and s + len(kick) < n: out[s:s + len(kick)] += kick
        h = tick() * 0.6; sh = s + int(beat / 2 * SR)
        if sh + len(h) < n: out[sh:sh + len(h)] += h
    fade_n = int(SR * 1.0)
    out[:fade_n] *= np.linspace(0, 1, fade_n); out[-fade_n:] *= np.linspace(1, 0, fade_n)
    return out


def mix(voice_path, events, total, out_path, seed=0, music_db=-26, sfx_db=-10):
    """events: list of (time_s, sound_name)."""
    v, sr = sf.read(voice_path)
    if v.ndim > 1: v = v.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(v) - 1, int(len(v) * SR / sr)); v = np.interp(idx, np.arange(len(v)), v)
    n = max(len(v), int(SR * total)); out = np.zeros(n)
    out[:len(v)] += v
    bed = music_bed(total, seed)[:n]
    out[:len(bed)] += bed * 10 ** (music_db / 20)
    g = 10 ** (sfx_db / 20)
    for t, name in events:
        s = SOUNDS[name](); i = int(t * SR)
        if i < n:
            m = min(len(s), n - i); out[i:i + m] += s[:m] * g
    peak = np.max(np.abs(out)) or 1
    out = out / peak * 0.95
    sf.write(out_path, out.astype(np.float32), SR)
