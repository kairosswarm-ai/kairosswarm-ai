"""Set the channel's branding watermark (shown on the channel's videos, links to subscribe)."""
import json, os, sys, datetime
import requests
from src import youtube


def main():
    tok = youtube.access_token()
    ch = youtube.my_channel(tok)
    img = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "branding", "watermark.png")
    meta = {"timing": {"type": "offsetFromStart", "offsetMs": 0}, "targetChannelId": ch["id"]}
    b = "wmboundary"
    body = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{b}\r\nContent-Type: image/png\r\n\r\n").encode() + open(img, "rb").read() + f"\r\n--{b}--".encode()
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/watermarks/set",
                      params={"channelId": ch["id"], "uploadType": "multipart"}, data=body, timeout=60,
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": f"multipart/related; boundary={b}"})
    ok = r.status_code in (200, 204)
    line = "- watermark set (whole video, links to the channel)" if ok else f"- watermark FAILED: {r.status_code} {r.text[:400]}"
    os.makedirs("reports", exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    txt = f"# Watermark ({stamp})\n\n- channel: {ch['title']}\n{line}\n"
    open("reports/watermark.md", "w").write(txt); print(txt)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
