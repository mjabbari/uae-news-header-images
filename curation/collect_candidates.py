#!/usr/bin/env python3
"""Collect a wide pool of Unsplash candidates per emirate for hand curation.

Runs in CI (secret UNSPLASH_ACCESS_KEY). Writes curation/candidates.json; nothing in the app reads it.
About 40 search requests in total, inside the 50/hour demo limit.
"""
import json, os, sys, time, urllib.parse, urllib.request

KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip() or sys.exit("UNSPLASH_ACCESS_KEY is not set")
QUERIES = {
    "abuDhabi": ["Abu Dhabi", "Sheikh Zayed Grand Mosque", "Louvre Abu Dhabi", "Abu Dhabi skyline night", "Qasr Al Watan", "Al Ain"],
    "dubai": ["Dubai", "Burj Khalifa", "Dubai Marina", "Burj Al Arab", "Dubai creek abra", "Museum of the Future"],
    "sharjah": ["Sharjah", "Sharjah Al Noor Mosque", "Sharjah Al Majaz", "Khor Fakkan", "Sharjah desert", "Mleiha"],
    "ajman": ["Ajman", "Ajman beach", "Ajman corniche", "Ajman mosque"],
    "ummAlQuwain": ["Umm Al Quwain", "Umm al Quwain beach", "Umm al Quwain mangrove", "Umm al Quwain fort"],
    "rasAlKhaimah": ["Ras Al Khaimah", "Jebel Jais", "Ras Al Khaimah beach", "Ras al Khaimah desert", "Dhayah Fort"],
    "fujairah": ["Fujairah", "Fujairah beach", "Fujairah mountains", "Dibba", "Al Bidya mosque", "Khor Fakkan beach"],
}

def search(q, page=1):
    url = "https://api.unsplash.com/search/photos?" + urllib.parse.urlencode(
        {"query": q, "orientation": "landscape", "per_page": 30, "page": page, "content_filter": "high", "order_by": "relevant"})
    req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {KEY}", "Accept-Version": "v1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(q, "remaining", r.headers.get("X-Ratelimit-Remaining"), flush=True)
        return json.load(r)["results"]

out = {}
for em, qs in QUERIES.items():
    seen, items = set(), []
    for q in qs:
        try:
            results = search(q)
        except Exception as e:
            print("fail", q, e); continue
        for p in results:
            if p["id"] in seen or p["width"] < 3000 or p["width"] < p["height"] * 1.3:
                continue
            seen.add(p["id"])
            items.append({
                "id": p["id"], "query": q, "likes": p.get("likes", 0),
                "desc": (p.get("description") or p.get("alt_description") or "")[:160],
                "thumb": p["urls"]["small"], "raw": p["urls"]["raw"],
                "credit": p["user"]["name"], "userURL": p["user"]["links"]["html"],
                "pageURL": p["links"]["html"], "downloadLocation": p["links"]["download_location"],
            })
        time.sleep(1)
    out[em] = items
    print(em, len(items), flush=True)

os.makedirs("curation", exist_ok=True)
json.dump(out, open("curation/candidates.json", "w"), indent=1, ensure_ascii=False)
