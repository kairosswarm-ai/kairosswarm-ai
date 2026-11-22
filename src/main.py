"""Entry point.
  python -m src.main check            # secrets + OpenRouter + YouTube auth, no video
  python -m src.main short            # make one Short, do not upload
  python -m src.main short --upload   # make one Short and upload it
"""
import json, os, sys, time, datetime, tempfile, shutil, traceback

import random
from concurrent.futures import ThreadPoolExecutor
from src import script_gen, voice, youtube, research, images as imgmod, sfx, render_v2, learn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "data", "history.json")
OUT = os.path.join(ROOT, "out")
REPORT = os.path.join(ROOT, "reports", "last_run.md")
NEEDED = ["OPENROUTER_API_KEY", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]


def load_hist():
    try: return json.load(open(HIST))
    except Exception: return []


def save_hist(h):
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    json.dump(h[-500:], open(HIST, "w"), indent=1)


def report(lines):
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    txt = f"# Last run ({stamp})\n\n" + "\n".join(lines) + "\n"
    open(REPORT, "w").write(txt)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(txt)
    print(txt)


def check():
    lines, ok = [], True
    for n in NEEDED:
        present = bool(os.environ.get(n))
        ok &= present
        lines.append(f"- secret `{n}`: {'OK' if present else 'MISSING'}")
    try:
        r = script_gen.chat([{"role": "user", "content": 'Reply with JSON {"pong": true}'}], temperature=0, max_tokens=20)
        lines.append(f"- OpenRouter ({script_gen.MODEL}): {'OK' if r.get('pong') else 'unexpected reply'}")
    except Exception as e:
        ok = False; lines.append(f"- OpenRouter: FAILED ({str(e)[:200]})")
    try:
        tok = youtube.access_token(); ch = youtube.my_channel(tok)
        lines.append(f"- YouTube auth: OK, channel **{ch['title']}** ({ch['id']}), subscribers {ch['subscribers']}")
        sc = [x.rsplit("/", 1)[-1] for x in youtube.token_scopes(tok)]
        lines.append(f"- token scopes: {', '.join(sc) or 'unknown'}"
                     )
        okc, detail = youtube.can_reply_comments(tok)
        lines.append(f"- comment reply permission: {'OK' if okc else 'MISSING'} (probe: {detail[:120]})")
    except Exception as e:
        ok = False; lines.append(f"- YouTube auth: FAILED ({str(e)[:300]})")
    return ok, lines


# Publish slots in US Eastern time (YouTube makes each Short public at exactly this time)
SLOTS_ET = [s.strip() for s in os.environ.get("SLOTS_ET", "09:00,14:00,18:00").split(",") if s.strip()]


def slot_times(now_utc=None):
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    now = now_utc or datetime.datetime.now(datetime.timezone.utc)
    day = now.astimezone(et).date()
    out = []
    for sl in SLOTS_ET:
        hh, mm = map(int, sl.split(":"))
        t = datetime.datetime(day.year, day.month, day.day, hh, mm, tzinfo=et).astimezone(datetime.timezone.utc)
        earliest = now + datetime.timedelta(minutes=30)
        if t < earliest:  # run was late: publish soon instead of in the past
            t = earliest + datetime.timedelta(minutes=10 * len(out))
        out.append(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return out


def do_research():
    """Market research once per run; never fatal (falls back to no data)."""
    try:
        res = research.trending(youtube.access_token())
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        open(os.path.join(ROOT, "reports", "research.md"), "w").write(
            f"# Market research ({datetime.datetime.utcnow():%Y-%m-%d %H:%M} UTC)\n\n" + research.to_markdown(res) + "\n")
        return res
    except Exception as e:
        print("research failed:", e)
        return None


FORMAT_NAMES = list(script_gen.FORMATS)


def pick_format(hist):
    recent = [h.get("format") for h in hist[-2:]]
    choices = [f for f in FORMAT_NAMES if f not in recent] or FORMAT_NAMES
    return random.choice(choices)


def scene_images(script, cache):
    if os.environ.get("BG_MODE", "sober") == "sober":  # clean dark animated background, no photos
        return {}, {"ai": 0, "fallback": 0, "cache": 0, "mode": "sober"}
    style = script.get("visual_style") or "cinematic photo, natural light, shallow depth of field"
    jobs = {}
    for i, sc in enumerate(script["scenes"]):
        if sc.get("type") == "cta":
            continue
        if sc.get("type") == "versus":
            for side, key in (("left", "v0"), ("right", "v1")):
                pr = (sc.get(side) or {}).get("image_prompt")
                if pr: jobs[(i, key)] = pr
            if sc.get("image_prompt"): jobs[(i, "bg")] = sc["image_prompt"]
        else:
            jobs[(i, None)] = sc.get("image_prompt") or sc.get("caption") or sc.get("voice", "money")
    out, stats = {}, {"ai": 0, "fallback": 0, "cache": 0}  # BG_MODE=photo
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {k: ex.submit(imgmod.generate, pr, style, cache) for k, pr in jobs.items()}
        for (i, key), f in futs.items():
            im, src = f.result(); stats[src] += 1
            if key is None: out[i] = im
            else: out.setdefault(i, {})[key] = im
    return out, stats


def make_short(do_upload=False, publish_at=None, res=None, avoid=(), lessons=""):
    os.makedirs(OUT, exist_ok=True)
    hist = load_hist()
    t0 = time.time()
    fmt = pick_format(hist)
    style_idx = random.randrange(0, 15)
    script = script_gen.generate(hist, trends=research.summary_for_prompt(res) if res else None,
                                 trend_tags=" ".join("#" + h for h in (res or {}).get("hashtags", [])[:20]),
                                 avoid=avoid, fmt=fmt, lessons=lessons,
                                 similar=lambda sc: learn.too_similar(sc, hist))
    work = tempfile.mkdtemp()
    json.dump(script, open(os.path.join(OUT, "last_script.json"), "w"), indent=1)
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    mp4 = os.path.join(OUT, f"short-{stamp}.mp4")
    try:
        segs, wav, total = voice.synth_scenes(script["scenes"], work)
        for _ in range(2):
            if total <= 55:
                break
            words = sum(len(str(s.get("voice", "")).split()) for s in script["scenes"])
            script = script_gen.shorten(script, int(words * 48 / total))
            segs, wav, total = voice.synth_scenes(script["scenes"], work)
        if total > 70:
            raise RuntimeError(f"narration too long for a Short ({total:.1f}s)")
        pics, istats = scene_images(script, os.path.join(ROOT, "out", "imgcache"))
        mixed = os.path.join(work, "mix.wav")
        sfx.mix(wav, render_v2.sfx_events(script["scenes"], segs), total, mixed, seed=style_idx)
        render_v2.render(script["scenes"], segs, mixed, mp4, total, pics, style_idx=style_idx,
                         logo_path=os.path.join(ROOT, "branding", "logo_final.png"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    json.dump(script, open(mp4.replace(".mp4", ".json"), "w"), indent=1)
    lines = [f"- topic: {script['plan']['topic']} ({script['plan']['pillar']})",
             f"- inspired by trend: {script['plan'].get('inspired_by', '-')}",
             f"- title: {script['title']} (title score {script.get('title_score')}, hook score {script.get('hook_score')})",
             f"- format: {fmt}, look #{style_idx}, images: {istats}",
             f"- length: {total:.1f}s, built in {time.time() - t0:.0f}s",
             f"- fact check: (revisions {script.get('revisions')}) {'passed' if script['fact_check'].get('ok') else script['fact_check']}"]
    entry = {"date": stamp, "topic": script["plan"]["topic"], "title": script["title"], "pillar": script["plan"]["pillar"],
             "format": fmt, "style": script.get("visual_style", ""),
             "hook": (script.get("scenes") or [{}])[0].get("voice", "")}
    if do_upload:
        tok = youtube.access_token()
        desc = script.get("description", "")
        res = youtube.upload(tok, mp4, script["title"], desc, script.get("tags", []),
                             privacy=os.environ.get("PRIVACY", "public"), publish_at=publish_at)
        entry.update(res)
        when = f", goes live {res.get('publish_at')} UTC" if publish_at else ""
        lines.append(f"- uploaded: {res['url']} (privacy now: {res['privacy']}{when})")
    else:
        lines.append(f"- not uploaded (dry run): {os.path.basename(mp4)}")
    hist.append(entry); save_hist(hist)
    return lines


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "batch":  # make len(SLOTS_ET) Shorts, each scheduled for its slot
        ok, lines = check()
        if not ok:
            report(["## Setup check"] + lines); sys.exit(1)
        lines = ["## Setup check"] + lines
        res = do_research()
        try:
            rows = learn.own_stats(youtube.access_token(), load_hist()); lessons = learn.lessons(rows)
        except Exception as e:
            rows, lessons = [], ""
        lines += ["", f"## Own channel: {len(rows)} past Shorts checked" + (f", best so far {rows[0]['views']:,} views" if rows else "")]
        lines += ["", f"## Market research: {'OK, ' + str(len(res['videos'])) + ' trending Shorts analysed (see reports/research.md)' if res else 'failed, continuing without it'}"]
        done, made = 0, []
        for i, t in enumerate(slot_times()):
            lines += ["", f"## Short {i + 1} (slot {SLOTS_ET[i]} ET = {t})"]
            try:
                out = make_short(True, publish_at=t, res=res, avoid=made, lessons=lessons); lines += out; done += 1
                made += [l[9:] for l in out if l.startswith("- topic: ")]
            except Exception as e:
                lines += [f"- FAILED: {e}", "```", traceback.format_exc()[-1500:], "```"]
        report(lines)
        sys.exit(0 if done else 1)
    try:
        if cmd == "check":
            ok, lines = check(); report(["## Setup check"] + lines); sys.exit(0 if ok else 1)
        if cmd == "short":
            ok, lines = check()
            if not ok:
                report(["## Setup check"] + lines); sys.exit(1)
            res = do_research()
            lines = ["## Setup check"] + lines + ["", "## Short"] + make_short("--upload" in sys.argv, res=res)
            report(lines)
    except SystemExit:
        raise
    except Exception as e:
        report([f"## FAILED: {e}", "```", traceback.format_exc()[-2500:], "```"]); sys.exit(1)


if __name__ == "__main__":
    main()
