"""Topic -> calculators -> script JSON, using OpenRouter. Hooks and titles are
scored with the youtube-agent plugin tools (hookscore.py / title.py, MIT)."""
import json, os, re, random, time
import requests

from src.calc import CALC_DOCS, run_calcs
from src.ytagent import hookscore, title as titlelint

API = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-5.5")
CHANNEL = os.environ.get("CHANNEL_NAME", "Compound Shock")
HOOK_RULES = json.load(open(os.path.join(os.path.dirname(__file__), "ytagent", "hooks.json")))
FORMULAS = "\n".join(f"- {h['name']}: {h['shape']} (fails when: {h['fails_when']})" for h in HOOK_RULES["hooks"])

PILLARS = [
    ("money", 0.7, "US personal finance: credit cards, debt, interest, saving, budgeting, taxes, "
                   "retirement accounts, insurance, car and home costs, everyday money traps"),
    ("business", 0.3, "business and rich-people facts: how famous US companies really make money, "
                      "pricing tricks, unit economics, why things cost what they cost"),
]

POLICY = """Hard rules (YouTube policy + accuracy):
- Educational only. Never tell viewers to buy/sell a specific stock, coin or fund. No guarantees.
- Never invent a statistic. Only use (a) results returned by the calculators, or (b) widely
  published, stable facts that you are confident are correct, each with a named source
  (e.g. Federal Reserve, Bankrate, IRS, company annual report). If unsure, leave the number out.
- No clickbait the video does not pay off. The hook's promise must be delivered.
- No mentions of being AI, no fake personal stories ("I lost $10k"), no fake testimonials.
- No copyrighted characters, brands as mascots, or song lyrics."""


def chat(messages, temperature=0.8, max_tokens=4000, retries=3):
    key = os.environ["OPENROUTER_API_KEY"]
    for attempt in range(retries):
        try:
            r = requests.post(API, timeout=180, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                "HTTP-Referer": "https://kairosswarm-ai.github.io/kairosswarm-ai/", "X-Title": CHANNEL},
                json={"model": MODEL, "messages": messages, "temperature": temperature,
                      "max_tokens": max_tokens, "response_format": {"type": "json_object"}})
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            txt = re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.M).strip()
            return json.loads(txt)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def pick_pillar(rng):
    x, acc = rng.random(), 0
    for name, w, desc in PILLARS:
        acc += w
        if x <= acc:
            return name, desc
    return PILLARS[0][0], PILLARS[0][2]


def plan_topic(history, rng):
    pillar, desc = pick_pillar(rng)
    recent = "\n".join(f"- {h['topic']}" for h in history[-60:]) or "(none yet)"
    msg = f"""You plan YouTube Shorts for "{CHANNEL}", a faceless US-audience channel of animated
money facts (shocking but TRUE numbers, clean charts). Pillar for this video: {desc}.

Already covered (do NOT repeat or closely paraphrase):
{recent}

{POLICY}

{CALC_DOCS}

Pick ONE specific, curiosity-driven topic built around a surprising number a US viewer can relate to.
Return JSON:
{{"topic": "...", "angle": "one sentence on the surprising insight",
  "calcs": [{{"id": "c1", "name": "<calculator>", "args": {{...}}}}],
  "facts": [{{"claim": "...", "source": "..."}}]}}
Use calculators for every computed number. 'facts' only for stable published figures you are sure of."""
    plan = chat([{"role": "user", "content": msg}], temperature=0.95)
    plan["pillar"] = pillar
    plan["calc_results"] = run_calcs(plan.get("calcs"))
    return plan


SCENE_DOC = """Scene types (each scene = one beat, 3-6 seconds of narration):
- {"type":"title","line1":"WHITE TEXT","line2":"ACCENT TEXT","accent":"red|green|yellow"}
- {"type":"big_number","label":"SMALL LABEL","value":7723,"prefix":"$","suffix":"","decimals":0,"color":"red|green|white","note":"small source/context line or empty"}
- {"type":"compare","title":"...","left":{"label":"...","color":"red","rows":[["Time in debt","~23 yrs"],["Interest","$7,723"]]},"right":{...same, "color":"green"},"footer":"..."}
- {"type":"bars","title":"...","items":[{"label":"...","value":5000,"color":"white|red|green|yellow"}],"prefix":"$","note":"..."}
- {"type":"timeline","label":"TIME IN DEBT","years":23,"start_year":2026}
- {"type":"statement","lines":["BIG","WORDS"],"sub":"smaller line","accent_line":1,"accent":"green"}
- {"type":"cta","line1":"...","line2":"..."}"""


def write_script(plan):
    results = json.dumps(plan["calc_results"], indent=1)
    facts = json.dumps(plan.get("facts", []), indent=1)
    msg = f"""Write a YouTube Short (35-45 seconds spoken, 90-105 words of narration in total, count them) for "{CHANNEL}".
Topic: {plan['topic']}
Angle: {plan.get('angle','')}

Calculator results (the ONLY computed numbers you may use; round sensibly, e.g. ~$7,700):
{results}
Facts you may use (always mention the source on screen in a note):
{facts}

{POLICY}

Hook formulas (first line must use one; confirm the title, open a gap, prove a payoff exists):
{FORMULAS}

{SCENE_DOC}

Structure: hook (first 3 s) -> setup -> the shocking number -> the twist/why -> the fix or takeaway -> cta.
No channel intro. One idea. The cta is one short line (e.g. follow for one money fact a day).
Narration ("voice") must sound natural spoken US English; write numbers as digits with $ and % (they are read aloud correctly).
"caption" is the on-screen subtitle for that beat (can equal voice, max ~18 words).

Return JSON:
{{"hooks": ["5 alternative first lines, 9-24 words each"],
  "titles": ["10 title options, <= 60 chars, with a number, no more than 2 ALL-CAPS words"],
  "description": "2-3 sentence description with the source names, then 3 relevant hashtags incl #shorts",
  "tags": ["8-12 search tags"],
  "scenes": [{{"type": "...", ..., "voice": "...", "caption": "..."}}]}}
The first scene's voice must be the best of your hooks."""
    return chat([{"role": "user", "content": msg}], temperature=0.8, max_tokens=5000)


def verify(plan, script):
    msg = f"""You are a strict fact checker for a US personal finance YouTube Short.
Allowed numbers come only from these calculator results:
{json.dumps(plan['calc_results'], indent=1)}
or these sourced facts: {json.dumps(plan.get('facts', []))}

Script scenes: {json.dumps(script.get('scenes', []), indent=1)}
Titles: {json.dumps(script.get('titles', []))}

{POLICY}

Check every number, claim and title. A number is OK if it is a calculator result (sensibly rounded)
or a sourced fact you are confident is accurate. Flag anything invented, wrong, misleading,
or any policy problem. Return JSON: {{"ok": true|false, "problems": ["..."]}}"""
    return chat([{"role": "user", "content": msg}], temperature=0.0, max_tokens=1500)


def best_hook_and_title(script):
    hooks = [h for h in script.get("hooks", []) if isinstance(h, str)]
    first_voice = script["scenes"][0].get("voice", "")
    if first_voice and first_voice not in hooks:
        hooks.append(first_voice)
    scored = sorted(((hookscore.score(h)[1], h) for h in hooks), reverse=True)
    if scored and scored[0][1] != first_voice:
        script["scenes"][0]["voice"] = scored[0][1]
        script["scenes"][0]["caption"] = scored[0][1]
    titles = [t for t in script.get("titles", []) if isinstance(t, str)]
    ranked = sorted((titlelint.check(t) for t in titles), key=lambda r: -r["score"])
    script["title"] = ranked[0]["title"][:100] if ranked else script.get("titles", ["Money fact"])[0]
    script["hook_score"] = scored[0][0] if scored else None
    script["title_score"] = ranked[0]["score"] if ranked else None
    return script


def shorten(script, max_words):
    """Trim narration while keeping every number and the scene structure."""
    msg = f"""Shorten the narration of this YouTube Short to at most {max_words} words in total.
Keep the same scenes, order, types, visuals and every number exactly as they are.
Only rewrite each scene's "voice" (and set "caption" to match). Keep the first line a strong hook.
Scenes: {json.dumps(script['scenes'], indent=1)}
Return JSON: {{"scenes": [...same scenes with shorter voice/caption...]}}"""
    out = chat([{"role": "user", "content": msg}], temperature=0.3, max_tokens=4000)
    if out.get("scenes") and len(out["scenes"]) == len(script["scenes"]):
        script["scenes"] = out["scenes"]
    return script


def generate(history, seed=None, max_attempts=3):
    rng = random.Random(seed)
    last_err = None
    for attempt in range(max_attempts):
        plan = plan_topic(history, rng)
        if any("error" in c["result"] for c in plan["calc_results"]):
            last_err = f"calculator error: {plan['calc_results']}"
            continue
        script = write_script(plan)
        if not script.get("scenes"):
            last_err = "empty script"
            continue
        check = verify(plan, script)
        if not check.get("ok"):
            last_err = f"fact check failed: {check.get('problems')}"
            continue
        script = best_hook_and_title(script)
        script["plan"] = plan
        script["fact_check"] = check
        return script
    raise RuntimeError(f"could not produce a verified script: {last_err}")
