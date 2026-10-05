#!/usr/bin/env python3
"""Publish the hand-curated header photos as images.json.

The set lives in curation/curated.json (picked by eye from curation/candidates.json, so every photo
is the right emirate and a strong landscape). Each run:
  * keeps the order stable but rotates the starting point daily, so the app's 4-hour slots vary;
  * tells Unsplash once per photo that it is in use (download_location), as their API guidelines ask.
Output: {"dubai": [{url, credit, license, pageURL, downloadLocation}], ...}
"""
import datetime, json, os, urllib.request

KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
curated = json.load(open("curation/curated.json"))
tracked_path = "curation/tracked.json"
tracked = set(json.load(open(tracked_path))) if os.path.exists(tracked_path) else set()

def track(location):
    if not KEY or location in tracked:
        return
    req = urllib.request.Request(location, headers={"Authorization": f"Client-ID {KEY}", "Accept-Version": "v1"})
    try:
        urllib.request.urlopen(req, timeout=30).read()
        tracked.add(location)
    except Exception as e:
        print("track failed", e)

day = datetime.date.today().toordinal()
out = {}
for emirate, photos in curated.items():
    for p in photos:
        if p.get("downloadLocation"):
            track(p["downloadLocation"])
    shift = day % max(len(photos), 1)
    out[emirate] = photos[shift:] + photos[:shift]
    print(emirate, len(photos))

json.dump(out, open("images.json", "w"), indent=1, ensure_ascii=False)
json.dump(sorted(tracked), open(tracked_path, "w"), indent=0)
