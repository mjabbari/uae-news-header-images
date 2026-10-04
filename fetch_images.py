#!/usr/bin/env python3
"""Fetch a daily set of landscape photos per emirate from Unsplash and write images.json.

Runs once a day in CI with UNSPLASH_ACCESS_KEY so that app users never call Unsplash
directly (7 requests per day in total instead of one per device).
Output format matches the app's DailyImage: {"dubai": [{url, credit, license, pageURL, downloadLocation}], ...}
"""
import json, os, sys, urllib.parse, urllib.request

KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
if not KEY:
    sys.exit("UNSPLASH_ACCESS_KEY is not set")

QUERIES = {
    "abuDhabi": "Abu Dhabi skyline", "dubai": "Dubai skyline", "sharjah": "Sharjah", "ajman": "Ajman",
    "ummAlQuwain": "Umm al-Quwain", "rasAlKhaimah": "Ras al-Khaimah", "fujairah": "Fujairah",
}
UTM = "utm_source=uae_news&utm_medium=referral"
out = {}
for emirate, query in QUERIES.items():
    params = urllib.parse.urlencode({"query": query, "orientation": "landscape", "content_filter": "high", "count": 30})
    req = urllib.request.Request(f"https://api.unsplash.com/photos/random?{params}",
                                 headers={"Authorization": f"Client-ID {KEY}", "Accept-Version": "v1", "User-Agent": "UAENews-header-images/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            photos = json.load(r)
    except Exception as e:  # keep yesterday's set for this emirate if the call fails
        print(f"{emirate}: {e}", file=sys.stderr)
        continue
    items = []
    for p in photos:
        if p.get("width", 0) <= p.get("height", 0):
            continue
        items.append({
            "url": p["urls"]["raw"] + "&w=1600&q=80&fm=jpg&fit=max",
            "credit": f"Photo by {p['user']['name']} on Unsplash",
            "license": "",
            "pageURL": p["user"]["links"]["html"] + "?" + UTM,
            "downloadLocation": p["links"]["download_location"],
        })
    if len(items) >= 3:
        out[emirate] = items
    print(f"{emirate}: {len(items)} photos")

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images.json")
previous = {}
if os.path.exists(path):
    with open(path) as f:
        previous = json.load(f)
previous.update(out)
with open(path, "w") as f:
    json.dump(previous, f, ensure_ascii=False, indent=1)
print("wrote", path)
