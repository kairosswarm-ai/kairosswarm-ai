# Last run (2026-11-21 14:16 UTC)

## FAILED: Nothing to synthesize, '' produced no phonemes
```
Traceback (most recent call last):
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/main.py", line 107, in main
    lines = ["## Setup check"] + lines + ["", "## Short"] + make_short("--upload" in sys.argv)
                                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/main.py", line 63, in make_short
    segs, wav, total = voice.synth_scenes(script["scenes"], work)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/voice.py", line 31, in synth_scenes
    samples, sr = k.create(normalize(s.get("voice", "")), voice=VOICE, speed=SPEED, lang="en-us")
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/kokoro_onnx/__init__.py", line 258, in create
    audio, sample_rate, _ = self.create_timed(
                            ^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/kokoro_onnx/__init__.py", line 291, in create_timed
    voice, phonemes, batches = self._prepare(
                               ^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/kokoro_onnx/__init__.py", line 199, in _prepare
    raise ValueError(f"Nothing to synthesize, {text!r} produced no phonemes")
ValueError: Nothing to synthesize, '' produced no phonemes

```
