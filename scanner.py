#!/usr/bin/env python3
"""
Deal Scanner - Finds 80%+ off deals and notifies via Pushover
Sources: Slickdeals, DealNews, Reddit
"""

import requests
import json
import os
import re
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
PUSHOVER_USER_KEY  = os.environ.get("PUSHOVER_USER_KEY", "")
PUSHOVER_TOKEN     = os.environ.get("PUSHOVER_TOKEN", "")
MIN_DISCOUNT       = 80  # minimum % off to trigger notification
SEEN_DEALS_FILE    = "data/seen_deals.json"

CATEGORIES = {
    "electronics": ["electronics", "laptop", "phone", "tv", "camera", "tablet", "headphone", "monitor", "keyboard", "mouse", "speaker", "console", "gpu", "cpu", "ssd", "hard drive"],
    "clothing":    ["clothing", "shoes", "shirt", "pants", "jacket", "boots", "sneakers", "dress", "hoodie", "coat", "apparel", "fashion"],
    "gaming":      ["gaming", "game", "xbox", "playstation", "nintendo", "steam", "ps5", "ps4", "switch", "controller", "gpu", "graphics card"],
    "general":     []  # catches everything else
}

SOURCES = [
    {
        "name": "Slickdeals",
        "url": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
        "type": "rss"
    },
    {
        "name": "DealNews",
        "url": "https://www.dealnews.com/rss/",
        "type": "rss"
    },
    {
        "name": "Reddit r/deals",
        "url": "https://www.reddit.com/r/deals/new.json?limit=25",
        "type": "reddit"
    },
    {
        "name": "Reddit r/buildapcsales",
        "url": "https://www.reddit.com/r/buildapcsales/new.json?limit=25",
        "type": "reddit"
    },
    {
        "name": "Reddit r/GameDeals",
        "url": "https://www.reddit.com/r/GameDeals/new.json?limit=25",
        "type": "reddit"
    },
    {
        "name": "Reddit r/frugalmalefashion",
        "url": "https://www.reddit.com/r/frugalmalefashion/new.json?limit=25",
        "type": "reddit"
    }
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen_deals():
    try:
        with open(SEEN_DEALS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen_deals(seen):
    os.makedirs("data", exist_ok=True)
    # keep only last 1000 to avoid file bloat
    seen_list = list(seen)[-1000:]
    with open(SEEN_DEALS_FILE, "w") as f:
        json.dump(seen_list, f)

def deal_id(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()

def extract_discount(text):
    """Try to find a discount percentage in text like '80% off', 'save 85%', etc."""
    patterns = [
        r'(\d+)%\s*off',
        r'save\s+(\d+)%',
        r'(\d+)%\s*discount',
        r'\((\d+)%\s*off\)',
        r'-(\d+)%',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

def extract_prices(text):
    """Try to extract was/now prices and compute discount."""
    # patterns like "$100 $20", "was $100 now $15", "$100 -> $18"
    patterns = [
        r'was\s*\$?([\d,]+\.?\d*)\s*(?:now|for)?\s*\$?([\d,]+\.?\d*)',
        r'\$?([\d,]+\.?\d*)\s*[-–→]\s*\$?([\d,]+\.?\d*)',
        r'retail[:\s]*\$?([\d,]+\.?\d*).*?(?:sale|now|for)[:\s]*\$?([\d,]+\.?\d*)',
        r'orig(?:inal)?[:\s]*\$?([\d,]+\.?\d*).*?\$?([\d,]+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                original = float(match.group(1).replace(",", ""))
                sale     = float(match.group(2).replace(",", ""))
                if original > sale > 0:
                    discount = round((1 - sale / original) * 100)
                    return original, sale, discount
            except:
                pass
    return None, None, None

def categorize(title, description=""):
    text = (title + " " + description).lower()
    for cat, keywords in CATEGORIES.items():
        if cat == "general":
            continue
        if any(kw in text for kw in keywords):
            return cat
    return "general"

def check_deal(title, description, url, source):
    """Return deal dict if it qualifies, else None."""
    combined = f"{title} {description}"

    discount = extract_discount(combined)
    original, sale, computed_discount = extract_prices(combined)

    # prefer computed from prices if available
    if computed_discount and computed_discount >= MIN_DISCOUNT:
        discount = computed_discount
    elif discount and discount >= MIN_DISCOUNT:
        pass  # use extracted discount
    else:
        return None

    category = categorize(title, description)

    return {
        "title":    title.strip(),
        "url":      url,
        "source":   source,
        "discount": discount,
        "original": original,
        "sale":     sale,
        "category": category,
        "found_at": datetime.utcnow().isoformat()
    }

# ── Fetchers ──────────────────────────────────────────────────────────────────

def fetch_rss(source):
    deals = []
    headers = {"User-Agent": "DealScanner/1.0"}
    try:
        r = requests.get(source["url"], headers=headers, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        for item in items:
            title = item.findtext("title") or ""
            desc  = item.findtext("description") or ""
            url   = item.findtext("link") or ""
            deal  = check_deal(title, desc, url, source["name"])
            if deal:
                deals.append(deal)
    except Exception as e:
        print(f"RSS error ({source['name']}): {e}")
    return deals

def fetch_reddit(source):
    deals = []
    headers = {"User-Agent": "DealScanner/1.0"}
    try:
        r = requests.get(source["url"], headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        posts = data.get("data", {}).get("children", [])
        for post in posts:
            d     = post.get("data", {})
            title = d.get("title", "")
            desc  = d.get("selftext", "")
            url   = d.get("url", "")
            permalink = "https://reddit.com" + d.get("permalink", "")
            deal  = check_deal(title, desc, url or permalink, source["name"])
            if deal:
                deals.append(deal)
    except Exception as e:
        print(f"Reddit error ({source['name']}): {e}")
    return deals

# ── Notifier ──────────────────────────────────────────────────────────────────

def send_pushover(deal):
    if not PUSHOVER_USER_KEY or not PUSHOVER_TOKEN:
        print("Pushover keys not set — skipping notification")
        return

    original_str = f"${deal['original']:.2f}" if deal['original'] else "?"
    sale_str     = f"${deal['sale']:.2f}"     if deal['sale']     else "?"

    if deal['original'] and deal['sale']:
        price_line = f"{original_str} → {sale_str}"
    else:
        price_line = ""

    message = (
        f"🏷 {deal['discount']}% OFF\n"
        f"{price_line}\n"
        f"📂 {deal['category'].title()}\n"
        f"🔗 {deal['source']}"
    ).strip()

    payload = {
        "token":   PUSHOVER_TOKEN,
        "user":    PUSHOVER_USER_KEY,
        "title":   deal["title"][:100],
        "message": message,
        "url":     deal["url"],
        "url_title": "View Deal",
        "priority": 0,
        "sound":   "cashregister"
    }

    try:
        r = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
        r.raise_for_status()
        print(f"Notified: {deal['title'][:60]}")
    except Exception as e:
        print(f"Pushover error: {e}")

# ── Deal log (for the web app) ────────────────────────────────────────────────

def update_deals_log(new_deals):
    log_file = "data/deals.json"
    try:
        with open(log_file, "r") as f:
            existing = json.load(f)
    except:
        existing = []

    # prepend new deals, keep last 200
    combined = new_deals + existing
    combined = combined[:200]

    os.makedirs("data", exist_ok=True)
    with open(log_file, "w") as f:
        json.dump(combined, f, indent=2)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.utcnow().isoformat()}] Deal scanner starting...")
    seen = load_seen_deals()
    all_new_deals = []

    for source in SOURCES:
        print(f"Checking {source['name']}...")
        if source["type"] == "rss":
            deals = fetch_rss(source)
        elif source["type"] == "reddit":
            deals = fetch_reddit(source)
        else:
            deals = []

        for deal in deals:
            did = deal_id(deal["title"], deal["url"])
            if did not in seen:
                seen.add(did)
                all_new_deals.append(deal)
                print(f"  NEW DEAL ({deal['discount']}% off): {deal['title'][:60]}")
                send_pushover(deal)
            else:
                print(f"  Already seen: {deal['title'][:60]}")

    if all_new_deals:
        update_deals_log(all_new_deals)

    save_seen_deals(seen)
    print(f"Done. {len(all_new_deals)} new deals found.")

if __name__ == "__main__":
    main()
