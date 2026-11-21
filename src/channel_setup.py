"""One-time channel branding: description, keywords, language, banner.
(The profile picture cannot be set through the YouTube Data API.)"""
import json, os, sys, datetime
import requests
from src import youtube

DESCRIPTION = """Compound Shock turns the hidden math of money into short, clear facts.

Credit card traps, interest, debt, saving, taxes, retirement, and how big companies really make their money. Every number is calculated, and every outside fact names its source.

New money facts every day.

Educational content only. Not financial advice."""

KEYWORDS = ('"personal finance" "money facts" "credit cards" "compound interest" "credit card debt" '
            '"saving money" "money tips" "business facts" "how companies make money" "finance shorts"')


def main():
    tok = youtube.access_token()
    h = {"Authorization": f"Bearer {tok}"}
    ch = youtube.my_channel(tok)
    lines = [f"- channel: {ch['title']} ({ch['id']})"]

    banner_url = None
    bp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "branding", "banner.jpg")
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/channelBanners/insert?uploadType=media",
                      timeout=120, headers={**h, "Content-Type": "image/jpeg"}, data=open(bp, "rb").read())
    if r.status_code == 200:
        banner_url = r.json()["url"]; lines.append("- banner uploaded")
    else:
        lines.append(f"- banner upload FAILED: {r.status_code} {r.text[:300]}")

    cur = requests.get("https://www.googleapis.com/youtube/v3/channels", timeout=30, headers=h,
                       params={"part": "brandingSettings", "id": ch["id"]}).json()["items"][0]
    bs = cur.get("brandingSettings", {})
    bs.setdefault("channel", {})
    bs["channel"].update({"description": DESCRIPTION, "keywords": KEYWORDS, "defaultLanguage": "en"})
    if banner_url:
        bs.setdefault("image", {})["bannerExternalUrl"] = banner_url
    r = requests.put("https://www.googleapis.com/youtube/v3/channels?part=brandingSettings", timeout=60,
                     headers={**h, "Content-Type": "application/json"},
                     data=json.dumps({"id": ch["id"], "brandingSettings": bs}))
    if r.status_code == 200:
        lines.append("- description, keywords, language: updated" + (", banner set" if banner_url else ""))
    else:
        lines.append(f"- channel update FAILED: {r.status_code} {r.text[:400]}")

    os.makedirs("reports", exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    txt = f"# Channel setup ({stamp})\n\n" + "\n".join(lines) + "\n"
    open("reports/channel_setup.md", "w").write(txt); print(txt)
    sys.exit(0 if all("FAILED" not in l for l in lines) else 1)


if __name__ == "__main__":
    main()
