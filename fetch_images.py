#!/usr/bin/env python3
"""Fetch a daily set of landscape photos per emirate from Unsplash and write images.json.

Runs once a day in CI with UNSPLASH_ACCESS_KEY so app users never call Unsplash directly.
Each emirate uses a few landmark searches; a photo is kept only if its text does not point to a
different emirate (or that emirate's landmarks) and it looks like scenery, not an object.
Output: {"dubai": [{url, credit, license, pageURL, downloadLocation}], ...}
"""
import json, os, re, sys, urllib.parse, urllib.request

KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
if not KEY:
    sys.exit("UNSPLASH_ACCESS_KEY is not set")

EMIRATES = {
    "abuDhabi": {
        "queries": ["Abu Dhabi skyline", "Sheikh Zayed Grand Mosque", "Abu Dhabi corniche", "Louvre Abu Dhabi"],
        "names": r"abu ?dhabi|أبوظبي|أبو ظبي|al ain|yas island|saadiyat|sheikh zayed (grand )?mosque|louvre abu dhabi|qasr al watan|emirates palace|liwa",
    },
    "dubai": {
        "queries": ["Dubai skyline", "Burj Khalifa", "Dubai Marina", "Dubai creek"],
        "names": r"dubai|دبي|burj khalifa|burj al arab|palm jumeirah|jumeirah|dubai marina|museum of the future|hatta|deira",
    },
    "sharjah": {
        "queries": ["Sharjah city", "Sharjah corniche", "Al Noor Mosque Sharjah", "Khor Fakkan"],
        "names": r"sharjah|الشارقة|khor ?fakkan|kalba|al noor mosque|al majaz|mleiha",
    },
    "ajman": {
        "queries": ["Ajman", "Ajman corniche", "Ajman beach"],
        "names": r"ajman|عجمان",
    },
    "ummAlQuwain": {
        "queries": ["Umm al Quwain", "Umm Al Quwain mangroves", "Umm Al Quwain beach"],
        "names": r"umm ?al ?quwain|أم القيوين",
    },
    "rasAlKhaimah": {
        "queries": ["Ras Al Khaimah", "Jebel Jais", "Ras Al Khaimah mountains"],
        "names": r"ras ?al ?khaimah|رأس الخيمة|jebel jais|jais",
    },
    "fujairah": {
        "queries": ["Fujairah mountains", "Fujairah beach", "Fujairah fort", "Dibba"],
        "names": r"fujairah|الفجيرة|dibba|masafi|gulf of oman|east coast|al bidyah|bidiyah",
    },
}

# Subjects that are not a city/landscape view.
REJECT_SUBJECT = re.compile(
    r"\b(guitar|plant|flower|leaf|leaves|chandelier|ceiling|giraffe|camel close|cat|dog|bird|horse|food|coffee|"
    r"cup|plate|portrait|selfie|face|hand|holding|close[- ]?up|interior|room|bedroom|sofa|car interior|"
    r"bottle|shoe|watch|phone|laptop|logo|text|sign|menu|toy|statue of a|wedding|bride)\b", re.I)
# Words that suggest an outdoor view worth putting in a header.
SCENERY = re.compile(
    r"\b(skyline|city|cityscape|building|buildings|skyscraper|tower|mosque|dome|beach|sea|ocean|water|coast|"
    r"shore|bay|marina|harbo|port|boat|mountain|mountains|hill|desert|dune|road|highway|bridge|sunset|sunrise|"
    r"aerial|landscape|fort|castle|village|mangrove|island|lake|creek|park|night|lights|sky|panorama|view)\b", re.I)

# Scenes that cannot be the UAE (mislabelled uploads).
NOT_UAE = re.compile(r"\b(snow|snowy|forest|pine|autumn|fall foliage|lush|waterfall|glacier|ice|frozen|alps|river running|green valley)\b", re.I)

# Openverse titles that are not views of the place.
NOT_VIEW_TITLE = re.compile(r"plate|hypermarket|supermarket|\bmall\b|city cent|banner|stadium|estadio|free zone|cannon|logo|\bmap\b|flag|sign|entrance|interior|hotel room|nesto|lulu", re.I)

UTM = "utm_source=uae_news&utm_medium=referral"
OPENVERSE_NAMES = {"abuDhabi": "Abu Dhabi", "dubai": "Dubai", "sharjah": "Sharjah", "ajman": "Ajman",
                   "ummAlQuwain": "Umm al-Quwain", "rasAlKhaimah": "Ras al-Khaimah", "fujairah": "Fujairah"}


def search(query):
    params = urllib.parse.urlencode({"query": query, "orientation": "landscape", "content_filter": "high", "per_page": 30})
    req = urllib.request.Request(f"https://api.unsplash.com/search/photos?{params}",
                                 headers={"Authorization": f"Client-ID {KEY}", "Accept-Version": "v1",
                                          "User-Agent": "UAENews-header-images/2.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("results", [])


def openverse(emirate):
    """Top-up source for emirates with few Unsplash photos; titles must name the emirate."""
    params = urllib.parse.urlencode({"q": OPENVERSE_NAMES[emirate], "license_type": "commercial", "aspect_ratio": "wide",
                                     "size": "large", "page_size": 20})
    req = urllib.request.Request(f"https://api.openverse.org/v1/images/?{params}", headers={"User-Agent": "UAENews-header-images/2.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        results = json.load(r).get("results", [])
    items = []
    for it in results:
        title = it.get("title") or ""
        w, h = it.get("width") or 0, it.get("height") or 0
        if w < 1920 or w / max(h, 1) < 1.3 or not re.search(EMIRATES[emirate]["names"], title, re.I) or NOT_UAE.search(title) or NOT_VIEW_TITLE.search(title):
            continue
        if any(re.search(cfg["names"], title, re.I) for other, cfg in EMIRATES.items() if other != emirate):
            continue
        url = it["url"]
        if it.get("provider") == "wikimedia" and "/wikipedia/commons/" in url and "/thumb/" not in url:
            url = url.replace("/wikipedia/commons/", "/wikipedia/commons/thumb/") + "/1920px-" + url.rsplit("/", 1)[-1]
        license_ = "CC " + (it.get("license") or "").upper() + (" " + it["license_version"] if it.get("license_version") else "")
        items.append({"url": url, "credit": (it.get("creator") or it.get("provider", "")).strip()[:50],
                      "license": license_, "pageURL": it.get("foreign_landing_url") or url, "downloadLocation": None})
    return items


def text_of(photo):
    loc = photo.get("location") or {}
    parts = [photo.get("description"), photo.get("alt_description"), loc.get("name"), loc.get("city")]
    parts += [t.get("title") for t in photo.get("tags", []) if isinstance(t, dict)]
    return " ".join(p for p in parts if p)


def belongs(emirate, photo):
    text = text_of(photo)
    own = re.search(EMIRATES[emirate]["names"], text, re.I) is not None
    for other, cfg in EMIRATES.items():
        if other == emirate:
            continue
        if re.search(cfg["names"], text, re.I) and not own:
            return False, f"names {other}"
        # Strong landmark of another emirate overrides even a loose own-emirate mention.
        if other == "abuDhabi" and re.search(r"sheikh zayed (grand )?mosque|louvre abu dhabi|qasr al watan", text, re.I) and emirate != "abuDhabi":
            return False, "Abu Dhabi landmark"
        if other == "dubai" and re.search(r"burj khalifa|burj al arab|museum of the future", text, re.I) and emirate != "dubai":
            return False, "Dubai landmark"
    alt = photo.get("alt_description") or ""
    if NOT_UAE.search(text):
        return False, "not a UAE scene"
    if REJECT_SUBJECT.search(alt):
        return False, "not scenery"
    if not own and not SCENERY.search(alt):
        return False, "no scenery words"
    return True, "own" if own else "scenery"


out, report = {}, {}
for emirate, cfg in EMIRATES.items():
    seen, items, rejected = set(), [], []
    for query in cfg["queries"]:
        try:
            results = search(query)
        except Exception as e:
            print(f"{emirate}/{query}: {e}", file=sys.stderr)
            continue
        for p in results:
            if p["id"] in seen or p.get("width", 0) <= p.get("height", 0) or p.get("width", 0) < 1600:
                continue
            seen.add(p["id"])
            ok, why = belongs(emirate, p)
            if not ok:
                rejected.append(f"{why}: {(p.get('description') or p.get('alt_description') or '')[:60]}")
                continue
            items.append({
                "url": p["urls"]["raw"] + "&w=1600&q=80&fm=jpg&fit=max",
                "credit": f"Photo by {p['user']['name']} on Unsplash",
                "license": "",
                "pageURL": p["user"]["links"]["html"] + "?" + UTM,
                "downloadLocation": p["links"]["download_location"],
                "_own": why == "own",
            })
    # Prefer photos that explicitly name the emirate, then scenery matches.
    items.sort(key=lambda x: not x["_own"])
    own_count = sum(1 for x in items if x["_own"])
    for x in items:
        x.pop("_own")
    if own_count < 8:
        try:
            extra = openverse(emirate)
            items = items[:own_count] + extra + items[own_count:]
            print(f"{emirate}: +{len(extra)} from Openverse")
        except Exception as e:
            print(f"{emirate}/openverse: {e}", file=sys.stderr)
    if len(items) >= 3:
        out[emirate] = items[:40]
    report[emirate] = (len(items), len(rejected), rejected[:6])
    print(f"{emirate}: kept {len(items)}, rejected {len(rejected)}")

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images.json")
previous = {}
if os.path.exists(path):
    with open(path) as f:
        previous = json.load(f)
previous.update(out)
with open(path, "w") as f:
    json.dump(previous, f, ensure_ascii=False, indent=1)
if os.environ.get("VERBOSE"):
    for e, (_, _, rej) in report.items():
        for r in rej:
            print(f"  {e} rejected → {r}")
print("wrote", path)
