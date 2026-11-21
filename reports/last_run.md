# Last run (2026-11-21 14:12 UTC)

## FAILED: narration too long for a Short (60.1s)
```
Traceback (most recent call last):
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/main.py", line 101, in main
    lines = ["## Setup check"] + lines + ["", "## Short"] + make_short("--upload" in sys.argv)
                                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/main.py", line 65, in make_short
    raise RuntimeError(f"narration too long for a Short ({total:.1f}s)")
RuntimeError: narration too long for a Short (60.1s)

```
