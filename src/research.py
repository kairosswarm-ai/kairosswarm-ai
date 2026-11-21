"""Market research before each batch: what US money/business Shorts are blowing up this week.

Uses the YouTube Data API (search + videos + channels). Each video is scored the
youtube-agent way (yt-viral): not by raw views, but by how far it beat its own channel.
Here the baseline is the channel's subscriber count (cheap to fetch), so a 300k-view
Short on a 5k-subscriber channel ranks far above a 300k-view Short on a 3M channel.
"""
import collections, datetime, json, os, random, re
import requests


API = "https://www.googleapis.com/youtube/v3"
HOOKS = json.load(open(os.path.join(os.path.dirname(__file__), "ytagent", "hooks.json")))["hooks"]

QUERIES = [
    "credit card", "credit card debt", "personal finance", "money tips", "saving money",
    "car loan", "mortgage", "taxes", "401k", "roth ira", "compound interest", "budgeting",
    "how companies make money", "business facts", "rich vs poor", "side hustle", "inflation",
    "insurance", "student loans", "costco", "billionaire",
]


MONEY_WORDS = re.compile(r"\$|money|rich|poor|credit|debt|tax|loan|sav(e|ing)|invest|income|salary|price|cost|"
                         r"business|compan|billion|million|budget|bank|interest|mortgage|401k|ira|stock|dollar|"
                         r"cash|pay|broke|wealth|afford|rent|insurance|retire|financ|econom|inflation|profit", re.I)
SKIP_CATEGORIES = {"1", "10", "20"}  # film/animation, music, gaming


def is_english(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    non_latin = sum(1 for c in letters if ord(c) > 0x024F)
    return non_latin / len(letters) < 0.1


def classify(title):
    best = (0, "Unclassified")
    for f in HOOKS:
        n = sum(1 for p in f["match"] if re.search(p, title, re.I))
        if n > best[0]:
            best = (n, f["name"])
    return best[1]


def _get(tok, path, params):
    r = requests.get(f"{API}/{path}", params=params, timeout=30, headers={"Authorization": f"Bearer {tok}"})
    r.raise_for_status()
    return r.json()


def trending(tok, n_queries=5, days=7, seed=None):
    rng = random.Random(seed)
    qs = rng.sample(QUERIES, n_queries)
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = []
    for q in qs:  # 100 quota units each
        js = _get(tok, "search", {"part": "id", "q": f"{q} #shorts", "type": "video", "videoDuration": "short",
                                  "order": "viewCount", "publishedAfter": since, "regionCode": "US",
                                  "relevanceLanguage": "en", "maxResults": 25})
        ids += [i["id"]["videoId"] for i in js.get("items", []) if i.get("id", {}).get("videoId")]
    ids = list(dict.fromkeys(ids))
    vids = []
    for i in range(0, len(ids), 50):  # 1 unit per call
        js = _get(tok, "videos", {"part": "snippet,statistics", "id": ",".join(ids[i:i + 50])})
        vids += js.get("items", [])
    chans = list({v["snippet"]["channelId"] for v in vids})
    subs = {}
    for i in range(0, len(chans), 50):
        js = _get(tok, "channels", {"part": "statistics", "id": ",".join(chans[i:i + 50])})
        for c in js.get("items", []):
            subs[c["id"]] = int(c.get("statistics", {}).get("subscriberCount") or 0)
    rows, tags = [], collections.Counter()
    for v in vids:
        sn, st = v["snippet"], v.get("statistics", {})
        views = int(st.get("viewCount") or 0)
        lang = (sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "en").lower()
        text_all = f"{sn.get('title', '')} {sn.get('description', '')[:300]}"
        if (views < 20000 or not lang.startswith("en") or not is_english(sn["title"])
                or sn.get("categoryId") in SKIP_CATEGORIES or not MONEY_WORDS.search(text_all)):
            continue
        s = max(subs.get(sn["channelId"], 0), 1000)
        rows.append({"title": sn["title"], "channel": sn["channelTitle"], "views": views,
                     "multiple": round(views / s, 1), "formula": classify(sn["title"]),
                     "url": f"https://youtube.com/shorts/{v['id']}"})
        text = f"{sn.get('title', '')} {sn.get('description', '')}"
        for h in set(re.findall(r"#([A-Za-z][A-Za-z0-9_]{2,29})", text)):
            tags[h.lower()] += 1
    rows.sort(key=lambda r: -r["multiple"])
    return {"queries": qs, "videos": rows[:20], "hashtags": [h for h, _ in tags.most_common(25)]}


def summary_for_prompt(res, k=12):
    lines = [f"- {r['multiple']}x its channel | {r['views']:,} views | {r['formula']} | \"{r['title']}\""
             for r in res["videos"][:k]]
    return "\n".join(lines) or "(no data)"


def to_markdown(res):
    out = [f"Searched: {', '.join(res['queries'])}", "", "| x channel | views | formula | title |", "|---|---|---|---|"]
    for r in res["videos"][:15]:
        t = r["title"].replace("|", "/")
        out.append(f"| {r['multiple']} | {r['views']:,} | {r['formula']} | [{t}]({r['url']}) |")
    out += ["", "Top hashtags: " + " ".join("#" + h for h in res["hashtags"][:15])]
    return "\n".join(out)
