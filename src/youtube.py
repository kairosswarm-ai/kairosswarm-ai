"""YouTube Data API v3 via OAuth refresh token (stored in GitHub Secrets)."""
import json, os, time
import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"


def access_token():
    r = requests.post(TOKEN_URL, timeout=30, data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise RuntimeError(f"token refresh failed: {r.status_code} {r.text[:300]}")
    return r.json()["access_token"]


def my_channel(tok):
    r = requests.get(f"{API}/channels", timeout=30, params={"part": "snippet,statistics", "mine": "true"},
                     headers={"Authorization": f"Bearer {tok}"})
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError("token works but no YouTube channel is linked to this account")
    it = items[0]
    return {"id": it["id"], "title": it["snippet"]["title"],
            "subscribers": it.get("statistics", {}).get("subscriberCount")}


def upload(tok, path, title, description, tags, privacy="public", category="27"):
    meta = {"snippet": {"title": title[:100], "description": description[:4900],
                        "tags": [t[:30] for t in (tags or [])][:15], "categoryId": category,
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                       "embeddable": True, "license": "youtube"}}
    size = os.path.getsize(path)
    init = requests.post(f"{UPLOAD}?uploadType=resumable&part=snippet,status", timeout=60,
                         headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                                  "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                         data=json.dumps(meta))
    if init.status_code != 200:
        raise RuntimeError(f"upload init failed: {init.status_code} {init.text[:500]}")
    url = init.headers["Location"]
    for attempt in range(5):
        with open(path, "rb") as f:
            r = requests.put(url, data=f, timeout=600,
                             headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"})
        if r.status_code in (200, 201):
            v = r.json()
            return {"id": v["id"], "privacy": v["status"]["privacyStatus"],
                    "url": f"https://youtube.com/shorts/{v['id']}"}
        if r.status_code in (500, 502, 503, 504):
            time.sleep(10 * (attempt + 1)); continue
        raise RuntimeError(f"upload failed: {r.status_code} {r.text[:500]}")
    raise RuntimeError("upload failed after retries")


def set_captions(tok, video_id, srt_path, name="English"):
    """Upload an SRT as closed captions (used for long-form videos)."""
    meta = {"snippet": {"videoId": video_id, "language": "en", "name": name, "isDraft": False}}
    boundary = "capboundary"
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + open(srt_path, "rb").read() + \
           f"\r\n--{boundary}--".encode()
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/captions?uploadType=multipart&part=snippet",
                      timeout=120, data=body, headers={"Authorization": f"Bearer {tok}",
                                                       "Content-Type": f"multipart/related; boundary={boundary}"})
    r.raise_for_status()
    return r.json()["id"]
