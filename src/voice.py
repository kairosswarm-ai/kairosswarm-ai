"""Kokoro TTS (Apache-2.0). Produces per-scene wavs and one mixed narration track."""
import os, re, subprocess
import soundfile as sf

MODEL_DIR = os.environ.get("KOKORO_DIR", "models")
VOICE = os.environ.get("VOICE", "am_michael")
SPEED = float(os.environ.get("VOICE_SPEED", "1.08"))
_k = None


def _kokoro():
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
    return _k


def normalize(t):
    t = t.replace("~", "about ").replace("APR", "A P R").replace("&", " and ")
    t = re.sub(r"(\d)%", r"\1 percent", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def synth_scenes(scenes, workdir, gap=0.15, lead=0.35, tail=0.6):
    k = _kokoro()
    segs, wavs, t = [], [], lead
    for i, s in enumerate(scenes):
        p = os.path.join(workdir, f"seg{i}.wav")
        text = normalize(str(s.get("voice") or s.get("caption") or ""))
        if text:
            samples, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        else:  # no words for this beat: hold the visual for 1.5 s
            import numpy as np
            sr = 24000; samples = np.zeros(int(1.5 * sr), dtype="float32")
        sf.write(p, samples, sr)
        d = len(samples) / sr
        segs.append((t, t + d)); wavs.append((p, t))
        t += d + gap
    total = t + tail
    out = os.path.join(workdir, "voice.wav")
    inputs, filt = [], []
    for j, (p, off) in enumerate(wavs):
        inputs += ["-i", p]
        ms = int(off * 1000)
        filt.append(f"[{j}]adelay={ms}|{ms}[a{j}]")
    filt.append("".join(f"[a{j}]" for j in range(len(wavs))) +
                f"amix=inputs={len(wavs)}:normalize=0,apad=whole_dur={total},loudnorm=I=-14:TP=-1.5[out]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "[out]", "-ar", "48000", out], check=True)
    return segs, out, total
