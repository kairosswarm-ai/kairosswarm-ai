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
- Never divide or subtract figures of different kinds (revenue vs profit, gross vs net, yearly vs
  monthly). Prefer topics the calculators can fully prove. State facts with their year.
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


def plan_topic(history, rng, trends=None, avoid=(), lessons=""):
    pillar, desc = pick_pillar(rng)
    recent = "\n".join(f"- {h['topic']}" for h in history[-60:]) or "(none yet)"
    msg = f"""You plan YouTube Shorts for "{CHANNEL}", a faceless US-audience channel of animated
money facts (shocking but TRUE numbers, clean charts). Pillar for this video: {desc}.

Already covered (do NOT repeat or closely paraphrase):
{recent}
{chr(10).join("- " + a for a in avoid)}

MARKET RESEARCH - US money/business Shorts that beat their own channel the most this week
(multiple = views / channel subscribers; formula = hook pattern of the title):
{trends or "(no research data this run)"}

WHAT WORKS ON OUR OWN CHANNEL:
{lessons or "(no data yet)"}

Use the research: pick a theme, angle or hook pattern that is clearly working right now, then
make it OUR OWN with a fresh, provable number. Never copy a title or a video.

{POLICY}

{CALC_DOCS}

Pick ONE specific, curiosity-driven topic built around a surprising number a US viewer can relate to.
It must be a situation the viewer is living RIGHT NOW (their paycheck, card, car, rent, groceries, phone bill,
job, taxes) so it feels like it is happening to them, and it must end in a concrete fix they can do today.
It must be clearly different from every covered topic above: new situation, new number, new angle.
Return JSON:
{{"topic": "...", "angle": "one sentence on the surprising insight",
  "inspired_by": "which trending theme/pattern from the research this rides (or 'none')",
  "calcs": [{{"id": "c1", "name": "<calculator>", "args": {{...}}}}],
  "facts": [{{"claim": "...", "source": "..."}}]}}
Use calculators for every computed number. 'facts' only for stable published figures you are sure of."""
    plan = chat([{"role": "user", "content": msg}], temperature=0.95)
    plan["pillar"] = pillar
    plan["calc_results"] = run_calcs(plan.get("calcs"))
    return plan


SCENE_DOC = """Scene types (each scene = one beat, 3-7 seconds of narration). Every scene except cta has an
"image_prompt": a vivid, specific, cinematic photo description that SHOWS the beat (real places, objects,
everyday US life, money, cars, homes, stores, cards). NO text, numbers, logos, brands or famous people in it.
- {"type":"image","image_prompt":"...","motion":"zoom_in|zoom_out|pan_left|pan_right|pan_up|crash_zoom|drift",
   "headline":"optional 2-5 WORD title on screen",
   "overlay":{"value":8100,"prefix":"$","suffix":"","label":"IN INTEREST","color":"red|green|yellow","note":"optional source"}}
   (use overlay only for the key number of that beat; headline and overlay are both optional)
- {"type":"versus","title":"SAME $5,000","left":{"label":"MINIMUMS","color":"red","image_prompt":"...","rows":[["Years","~19"],["Interest","$8,100"]]},
   "right":{"label":"$200/MONTH","color":"green","image_prompt":"...","rows":[["Years","~3"],["Interest","$1,750"]]},"image_prompt":"background..."}
- {"type":"receipt","title":"YOUR CAR LOAN","image_prompt":"background...","items":[["Car price","$35,000"],["Interest","$9,212"]],"total":["YOU PAY","$44,212"]}
- {"type":"list_item","number":3,"headline":"short headline","image_prompt":"...","overlay":{"value":1460,"prefix":"$"}}
- {"type":"quiz","question":"...","options":["A","B","C"],"answer_index":1,"image_prompt":"background..."}
- {"type":"cta","line1":"FOLLOW + LIKE","line2":"Comment your money question"}"""

FORMATS = {
    "story": "STORY: 5-7 'image' scenes that tell a tiny story with conflict (but... so...), 2-3 of them carry an overlay number; then cta.",
    "versus": "VERSUS: hook 'image' scene, one 'versus' scene comparing two choices, 1-2 'image' scenes explaining why, then cta.",
    "receipt": "RECEIPT: hook 'image' scene, a 'receipt' scene itemising what something really costs, 1-2 'image' scenes (why + the fix), then cta.",
    "top3": "TOP 3 LIST: hook 'image' scene, three 'list_item' scenes counting down 3, 2, 1, then cta.",
    "quiz": "QUIZ: first scene is a 'quiz' (the narration asks the viewer to guess and pauses), then 2-3 'image' scenes revealing and explaining, then cta.",
}


def write_script(plan, trend_tags="", fmt="story", recent_styles=(), recent_hooks=()):
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

FORMAT FOR THIS VIDEO (follow it exactly): {FORMATS.get(fmt, FORMATS['story'])}
Also give "visual_style": one line describing a consistent CINEMATIC film look for all images of this video
(film stock / colour grade, lighting, lens), e.g. "anamorphic 40mm, teal-and-orange grade, neon rim light, rain".
It must be clearly different from these recent looks: {list(recent_styles)[-6:]}
Each image_prompt must read like a film shot: shot type (extreme close-up, wide establishing, low angle,
over-the-shoulder, top-down, dutch angle), subject and action, setting, light. Vary the shot type every scene.
Pick "motion" per scene from: zoom_in, zoom_out, pan_left, pan_right, pan_up, crash_zoom, drift.

Trending hashtags in this niche right now: {trend_tags}

Length and pacing: 6-8 scenes, each scene 1-2 short sentences (max 24 words), so the picture changes every 4-6 seconds.
VOICE: talk TO the viewer in second person, like a friend who caught them in the act.
- The hook drops them into the moment: "You just...", "POV: you...", "If you have a ... right now...",
  "Stop. Before you swipe that card...". It names their exact situation and opens a loop the video pays off.
- Make it interactive: ask them something they answer in their head ("Guess how much...", "Be honest...",
  "Check your last statement..."), and later pay it off.
- Middle: the twist with the true number, then WHY it happens in one line.
- End: give THE SOLUTION as 1-3 concrete steps they can do today (exact action, not vague advice).
- Never start the hook the way these recent hooks start: {list(recent_hooks)[-15:]}
Structure: hook (first 3 s) -> setup -> the shocking number -> the twist/why -> the fix or takeaway -> cta.
No channel intro. One idea. The LAST scene is type "cta" and must ask for all three, in ~15 spoken words:
follow, like, and comment a money question that we will answer in a future video
(e.g. "Follow and like for more. Got a money question? Comment it, and we'll answer it in a video.").
Its line1/line2 on screen: e.g. "FOLLOW + LIKE" / "Comment your money question 👇".
Narration ("voice") must sound natural spoken US English; write numbers as digits with $ and % (they are read aloud correctly).
"caption" is the on-screen subtitle for that beat (can equal voice, max ~18 words).

Return JSON:
{{"hooks": ["5 alternative first lines, 9-24 words each"],
  "titles": ["10 title options, 25-45 characters, punchy, curiosity + a number, no emojis, no hashtags, max 2 ALL-CAPS words"],
  "emojis": ["the 2 emojis that best fit the title, e.g. a money or shock emoji"],
  "hashtags": ["3 topic hashtags without #, chosen from the trending hashtags below when relevant"],
  "description": "2-3 sentence description with the source names, then 3 relevant hashtags incl #shorts",
  "tags": ["8-12 search tags"],
  "visual_style": "...",
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
    core = ranked[0]["title"] if ranked else (script.get("titles") or ["Money fact"])[0]
    core = re.sub(r"#\w+", "", core).strip()[:60]
    emo = "".join(e for e in (script.get("emojis") or [])[:2] if isinstance(e, str) and len(e) <= 4)
    base = ["shorts", "ytshorts", "viral"]
    script["title"] = f"{core} {emo} " + " ".join("#" + h for h in base)
    script["title"] = re.sub(r"\s+", " ", script["title"]).strip()[:100]
    topic_tags = [re.sub(r"[^A-Za-z0-9]", "", str(h)).lower() for h in (script.get("hashtags") or [])]
    topic_tags = [h for h in topic_tags if 2 < len(h) <= 30 and h not in base][:3]
    tagline = " ".join("#" + h for h in dict.fromkeys(base + topic_tags + ["personalfinance", "money"]))
    desc = re.sub(r"#\w+", "", script.get("description", "")).strip()
    script["description"] = f"{desc}\n\n{tagline}"
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
    new = out.get("scenes") or []
    if len(new) == len(script["scenes"]) and all(str(n.get("voice", "")).strip() for n in new):
        for old, n in zip(script["scenes"], new):  # keep visuals, take only the new words
            old["voice"] = str(n["voice"]).strip()
            old["caption"] = str(n.get("caption") or n["voice"]).strip()
    return script


def structure_problems(script, fmt):
    sc = script.get("scenes") or []
    pr = []
    if not 5 <= len(sc) <= 9:
        pr.append(f"The video must have 5 to 9 scenes (it has {len(sc)}). Split long beats into separate scenes.")
    if not sc or sc[-1].get("type") != "cta":
        pr.append("The last scene must be the cta scene (follow + like + comment your money question).")
    for i, x in enumerate(sc):
        n = len(str(x.get("voice", "")).split())
        if n > 24:
            pr.append(f"Scene {i + 1} narration has {n} words; max 24 per scene. Split it into two scenes.")
        if len(str(x.get("caption", "")).split()) > 14:
            pr.append(f"Scene {i + 1} caption is too long; max 14 words.")
        if x.get("type") == "receipt":
            for it in x.get("items") or []:
                if len(str(it[0])) > 20 or len(str(it[1] if len(it) > 1 else "")) > 9:
                    pr.append(f"Receipt rows must be short: label <= 20 chars, amount <= 9 chars like $9,212 (bad: {it}).")
            tot = x.get("total") or ["", ""]
            if len(str(tot[0])) > 10 or len(str(tot[1] if len(tot) > 1 else "")) > 9:
                pr.append("Receipt total must be short: label <= 10 chars, amount <= 9 chars.")
    kinds = [x.get("type") for x in sc]
    need = {"versus": "versus", "receipt": "receipt", "top3": "list_item", "quiz": "quiz"}.get(fmt)
    if need and need not in kinds:
        pr.append(f"This video's format requires a '{need}' scene.")
    return pr


def revise(plan, script, problems):
    msg = f"""A fact checker rejected this YouTube Short. Fix EVERY problem below. If a claim cannot be
made accurate, remove it (and any title using it) rather than rewording it. Keep the same JSON shape.
Allowed numbers: calculator results {json.dumps(plan['calc_results'])} and sourced facts {json.dumps(plan.get('facts', []))}.

{POLICY}

Problems:
{json.dumps(problems, indent=1)}

Current script JSON:
{json.dumps({k: script[k] for k in ('hooks', 'titles', 'emojis', 'hashtags', 'description', 'tags', 'visual_style', 'scenes') if k in script}, indent=1)}

Return the full corrected JSON with keys hooks, titles, emojis, hashtags, description, tags, visual_style, scenes."""
    return chat([{"role": "user", "content": msg}], temperature=0.4, max_tokens=5000)


def generate(history, seed=None, max_topics=4, max_revisions=2, trends=None, trend_tags="", avoid=(), fmt="story",
             lessons="", similar=None):
    rng = random.Random(seed)
    last_err = None
    for _ in range(max_topics):
        plan = plan_topic(history, rng, trends, list(avoid), lessons)
        if any("error" in c["result"] for c in plan["calc_results"]):
            last_err = f"calculator error: {plan['calc_results']}"
            continue
        script = write_script(plan, trend_tags, fmt,
                              recent_styles=[h.get("style", "") for h in history[-6:] if h.get("style")],
                              recent_hooks=[h.get("hook", "")[:40] for h in history[-15:] if h.get("hook")])
        for rev in range(max_revisions + 1):
            if not script.get("scenes"):
                last_err = "empty script"; break
            sp = structure_problems(script, fmt)
            if sp:
                last_err = f"structure: {sp}"
                if rev < max_revisions:
                    old = script
                    script = revise(plan, script, sp)
                    for k in ("emojis", "hashtags", "visual_style"):
                        script.setdefault(k, old.get(k))
                continue
            check = verify(plan, script)
            if check.get("ok"):
                script = best_hook_and_title(script)
                script["plan"] = plan
                why = similar(script) if similar else None
                if why:
                    last_err = f"repeat blocked: {why}"
                    avoid = list(avoid) + [plan.get("topic", "")]
                    break
                script["fact_check"] = check
                script["revisions"] = rev
                return script
            last_err = f"fact check failed: {check.get('problems')}"
            if rev < max_revisions:
                old = script
                script = revise(plan, script, check.get("problems", []))
                for k in ("emojis", "hashtags", "visual_style"):
                    script.setdefault(k, old.get(k))
    raise RuntimeError(f"could not produce a verified script: {last_err}")
