"""Learn from our own uploads: which of our Shorts are doing best and worst, so each new batch
leans into what works on THIS channel. Also blocks repeats of topics, hooks and looks."""
import re
import requests

API = "https://www.googleapis.com/youtube/v3"
STOP = set("the a an of to in on for and or is are your you it at by with how why what this that from".split())


def own_stats(tok, hist, k=40):
    ids = [h["id"] for h in hist if h.get("id")][-k:]
    rows = []
    for i in range(0, len(ids), 50):
        r = requests.get(f"{API}/videos", timeout=30, headers={"Authorization": f"Bearer {tok}"},
                         params={"part": "statistics,snippet", "id": ",".join(ids[i:i + 50])})
        if r.status_code != 200:
            break
        for v in r.json().get("items", []):
            st = v.get("statistics", {})
            rows.append({"title": v["snippet"]["title"], "views": int(st.get("viewCount") or 0),
                         "likes": int(st.get("likeCount") or 0), "comments": int(st.get("commentCount") or 0)})
    by_id = {h.get("title"): h for h in hist}
    for r in rows:
        h = by_id.get(r["title"], {})
        r["format"] = h.get("format"); r["hook"] = h.get("hook", "")
    rows.sort(key=lambda r: -r["views"])
    return rows


def lessons(rows):
    if len(rows) < 4:
        return "(not enough of our own videos yet - lean on the market research)"
    top, low = rows[:3], rows[-3:]
    f = lambda r: f"- {r['views']:,} views, {r['likes']} likes, {r['comments']} comments | {r.get('format')} | \"{r['title']}\" | hook: {r.get('hook', '')[:90]}"
    return "OUR BEST so far (do more of what made these work, but never repeat them):\n" + "\n".join(map(f, top)) + \
           "\nOUR WEAKEST (avoid their patterns):\n" + "\n".join(map(f, low))


def words(t):
    return {w for w in re.findall(r"[a-z0-9$%]+", str(t).lower()) if w not in STOP and len(w) > 2}


def too_similar(script, hist, limit=0.45):
    """Return a reason string if this script repeats a past topic, title or hook opening."""
    topic = script.get("plan", {}).get("topic", ""); title = script.get("title", "")
    hook = (script.get("scenes") or [{}])[0].get("voice", "")
    opening = " ".join(str(hook).lower().split()[:3])
    tw = words(topic) | words(title)
    for h in hist[-120:]:
        hw = words(h.get("topic", "")) | words(h.get("title", ""))
        if tw and hw and len(tw & hw) / len(tw | hw) > limit:
            return f"too close to an earlier video: \"{h.get('title')}\""
        if opening and opening == " ".join(str(h.get("hook", "")).lower().split()[:3]):
            return f"hook opens with the same words as an earlier video (\"{opening}\")"
    return None
