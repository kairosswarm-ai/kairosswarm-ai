"""Scene images from an OpenRouter image model (vertical 9:16). Falls back to a generated
abstract background if the model fails, so a video is never lost because of one image."""
import base64, hashlib, io, os, random, time
import requests
from PIL import Image, ImageDraw, ImageFilter

API = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("IMAGE_MODEL", "google/gemini-3.1-flash-lite-image")
SAFE = ("Vertical 9:16 photo. Absolutely no text, letters, numbers, logos, watermarks or brand names "
        "anywhere in the image. No real or famous people; any people are anonymous and not looking at camera. ")


def _fallback(prompt, size=(1080, 1920)):
    rng = random.Random(hashlib.md5(prompt.encode()).hexdigest())
    w, h = size
    a = (rng.randint(10, 60), rng.randint(10, 60), rng.randint(30, 90))
    b = (rng.randint(60, 160), rng.randint(40, 120), rng.randint(10, 80))
    im = Image.new("RGB", size, a); d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        d.line((0, y, w, y), fill=tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    for _ in range(14):
        r = rng.randint(80, 380); x = rng.randint(0, w); y = rng.randint(0, h)
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(min(255, c + rng.randint(20, 70)) for c in b))
    return im.filter(ImageFilter.GaussianBlur(60))


def generate(prompt, style, cache_dir, retries=2):
    os.makedirs(cache_dir, exist_ok=True)
    full = SAFE + f"Style: {style}. Scene: {prompt}"
    key = hashlib.md5(full.encode()).hexdigest()[:16]
    path = os.path.join(cache_dir, f"{key}.png")
    if os.path.exists(path):
        return Image.open(path).convert("RGB"), "cache"
    for attempt in range(retries + 1):
        try:
            r = requests.post(API, timeout=180, headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"},
                json={"model": MODEL, "modalities": ["image", "text"],
                      "image_config": {"aspect_ratio": "9:16"},
                      "messages": [{"role": "user", "content": full}]})
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            url = (msg.get("images") or [{}])[0].get("image_url", {}).get("url", "")
            if not url.startswith("data:image"):
                raise ValueError("no image in response")
            im = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")
            im.save(path)
            return im, "ai"
        except Exception as e:
            err = e
            time.sleep(4 * (attempt + 1))
    print("image fallback:", str(err)[:200])
    return _fallback(prompt), "fallback"
