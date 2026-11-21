"""Entry point.
  python -m src.main check            # secrets + OpenRouter + YouTube auth, no video
  python -m src.main short            # make one Short, do not upload
  python -m src.main short --upload   # make one Short and upload it
"""
import json, os, sys, time, datetime, tempfile, shutil, traceback

from src import script_gen, voice, render_short, youtube

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
    except Exception as e:
        ok = False; lines.append(f"- YouTube auth: FAILED ({str(e)[:300]})")
    return ok, lines


def make_short(do_upload=False):
    os.makedirs(OUT, exist_ok=True)
    hist = load_hist()
    t0 = time.time()
    script = script_gen.generate(hist)
    work = tempfile.mkdtemp()
    try:
        segs, wav, total = voice.synth_scenes(script["scenes"], work)
        for _ in range(2):
            if total <= 52:
                break
            words = sum(len(str(s.get("voice", "")).split()) for s in script["scenes"])
            script = script_gen.shorten(script, int(words * 48 / total))
            segs, wav, total = voice.synth_scenes(script["scenes"], work)
        if total > 70:
            raise RuntimeError(f"narration too long for a Short ({total:.1f}s)")
        stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
        mp4 = os.path.join(OUT, f"short-{stamp}.mp4")
        render_short.render(script["scenes"], segs, wav, mp4, total)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    json.dump(script, open(mp4.replace(".mp4", ".json"), "w"), indent=1)
    lines = [f"- topic: {script['plan']['topic']} ({script['plan']['pillar']})",
             f"- title: {script['title']} (title score {script.get('title_score')}, hook score {script.get('hook_score')})",
             f"- length: {total:.1f}s, built in {time.time() - t0:.0f}s",
             f"- fact check: {'passed' if script['fact_check'].get('ok') else script['fact_check']}"]
    entry = {"date": stamp, "topic": script["plan"]["topic"], "title": script["title"], "pillar": script["plan"]["pillar"]}
    if do_upload:
        tok = youtube.access_token()
        desc = script.get("description", "")
        res = youtube.upload(tok, mp4, script["title"], desc, script.get("tags", []),
                             privacy=os.environ.get("PRIVACY", "public"))
        entry.update(res)
        lines.append(f"- uploaded: {res['url']} (privacy: {res['privacy']})")
        if res["privacy"] != os.environ.get("PRIVACY", "public"):
            lines.append("- note: YouTube kept it private (API project not audited yet)")
    else:
        lines.append(f"- not uploaded (dry run): {os.path.basename(mp4)}")
    hist.append(entry); save_hist(hist)
    return lines


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    try:
        if cmd == "check":
            ok, lines = check(); report(["## Setup check"] + lines); sys.exit(0 if ok else 1)
        if cmd == "short":
            ok, lines = check()
            if not ok:
                report(["## Setup check"] + lines); sys.exit(1)
            lines = ["## Setup check"] + lines + ["", "## Short"] + make_short("--upload" in sys.argv)
            report(lines)
    except SystemExit:
        raise
    except Exception as e:
        report([f"## FAILED: {e}", "```", traceback.format_exc()[-2500:], "```"]); sys.exit(1)


if __name__ == "__main__":
    main()
