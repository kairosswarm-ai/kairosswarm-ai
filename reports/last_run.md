# Last run (2026-11-21 18:17 UTC)

## FAILED: could not produce a verified script: calculator error: [{'id': 'c1', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 0.4, 'years': 1, 'monthly_contribution': 0}, 'result': {'future_value': 10040.07, 'total_contributed': 10000, 'growth': 40.07}}, {'id': 'c2', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 4.0, 'years': 1, 'monthly_contribution': 0}, 'result': {'future_value': 10407.42, 'total_contributed': 10000, 'growth': 407.42}}, {'id': 'c3', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 0.4, 'years': 5, 'monthly_contribution': 0}, 'result': {'future_value': 10201.98, 'total_contributed': 10000, 'growth': 201.98}}, {'id': 'c4', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 4.0, 'years': 5, 'monthly_contribution': 0}, 'result': {'future_value': 12209.97, 'total_contributed': 10000, 'growth': 2209.97}}, {'id': 'c5', 'name': 'arithmetic', 'args': {'expression': 'c4.future_value - c3.future_value'}, 'result': {'error': 'only plain arithmetic allowed'}}]
```
Traceback (most recent call last):
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/main.py", line 215, in main
    lines = ["## Setup check"] + lines + ["", "## Short"] + make_short("--upload" in sys.argv, res=res)
                                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/main.py", line 134, in make_short
    script = script_gen.generate(hist, trends=research.summary_for_prompt(res) if res else None,
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/kairosswarm-ai/kairosswarm-ai/src/script_gen.py", line 330, in generate
    raise RuntimeError(f"could not produce a verified script: {last_err}")
RuntimeError: could not produce a verified script: calculator error: [{'id': 'c1', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 0.4, 'years': 1, 'monthly_contribution': 0}, 'result': {'future_value': 10040.07, 'total_contributed': 10000, 'growth': 40.07}}, {'id': 'c2', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 4.0, 'years': 1, 'monthly_contribution': 0}, 'result': {'future_value': 10407.42, 'total_contributed': 10000, 'growth': 407.42}}, {'id': 'c3', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 0.4, 'years': 5, 'monthly_contribution': 0}, 'result': {'future_value': 10201.98, 'total_contributed': 10000, 'growth': 201.98}}, {'id': 'c4', 'name': 'compound_growth', 'args': {'principal': 10000, 'annual_rate_pct': 4.0, 'years': 5, 'monthly_contribution': 0}, 'result': {'future_value': 12209.97, 'total_contributed': 10000, 'growth': 2209.97}}, {'id': 'c5', 'name': 'arithmetic', 'args': {'expression': 'c4.future_value - c3.future_value'}, 'result': {'error': 'only plain arithmetic allowed'}}]

```
