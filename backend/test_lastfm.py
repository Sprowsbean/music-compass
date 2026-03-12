import urllib.request, urllib.parse, json, os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("LASTFM_API_KEY", "")

if not API_KEY:
    print("❌ No LASTFM_API_KEY found in .env")
    exit(1)

print(f"✓ Key loaded: {API_KEY[:6]}...")

params = urllib.parse.urlencode({
    "method":      "track.gettoptags",
    "api_key":     API_KEY,
    "artist":      "Arctic Monkeys",
    "track":       "Do I Wanna Know",
    "format":      "json",
    "autocorrect": 1,
})

try:
    url = f"https://ws.audioscrobbler.com/2.0/?{params}"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode())

    if "error" in data:
        print(f"❌ Last.fm API error {data['error']}: {data.get('message')}")
    else:
        tags = data.get("toptags", {}).get("tag", [])
        print(f"✓ Last.fm working — {len(tags)} tags returned")
        for t in tags[:5]:
            print(f"    {t['name']} (count: {t['count']})")

except Exception as e:
    print(f"❌ Request failed: {e}")