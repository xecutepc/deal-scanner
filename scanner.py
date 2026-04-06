#!/usr/bin/env python3
"""
Deal Scanner - Finds 80%+ off deals and notifies via Pushover
Sources: Slickdeals, DealNews, Reddit + direct retailer scraping
Retailers: Amazon, Walmart, Target, Home Depot, Newegg, Best Buy
"""

import requests
import json
import os
import re
import time
import random
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
PUSHOVER_USER_KEY  = os.environ.get("PUSHOVER_USER_KEY", "")
PUSHOVER_TOKEN     = os.environ.get("PUSHOVER_TOKEN", "")
MIN_DISCOUNT       = 80

MIN_ORIGINAL_PRICE = {
    "flipping":    500,
    "electronics": 50,
    "gaming":      30,
    "clothing":    40,
    "general":     20,
}

MIN_SALE_PRICE = {
    "flipping":    10,
    "electronics": 5,
    "gaming":      5,
    "clothing":    5,
    "general":     3,
}

SEEN_DEALS_FILE = "data/seen_deals.json"

CATEGORIES = {
    "flipping": [
        # TVs & displays
        "tv", "television", "oled", "qled", "4k tv", "8k tv", "smart tv", "projector screen",
        # Large appliances
        "refrigerator", "fridge", "french door fridge", "chest freezer", "upright freezer",
        "washer", "dryer", "washer dryer", "dishwasher", "oven", "range", "stove",
        "microwave", "hood range", "wine cooler", "wine fridge", "ice maker",
        # Small appliances (high value)
        "espresso machine", "coffee maker", "keurig", "nespresso", "vitamix", "blender",
        "stand mixer", "kitchenaid", "air fryer", "instant pot", "pressure cooker",
        "bread maker", "juicer", "food processor", "vacuum", "dyson", "robot vacuum",
        "roomba", "air purifier", "dehumidifier", "humidifier", "space heater",
        # Home comfort
        "portable ac", "window ac", "air conditioner", "heat pump", "electric fireplace",
        "massage chair", "zero gravity chair",
        # Power & outdoor
        "generator", "solar panel", "power station", "portable power",
        "pressure washer", "lawnmower", "lawn mower", "riding mower", "zero turn",
        "snow blower", "leaf blower", "chainsaw", "pole saw", "hedge trimmer",
        # Power tools
        "power tool", "dewalt", "milwaukee", "makita", "ryobi", "craftsman", "bosch",
        "table saw", "miter saw", "circular saw", "jigsaw", "reciprocating saw",
        "drill press", "band saw", "router", "planer", "jointer", "lathe",
        "air compressor", "nail gun", "impact wrench", "angle grinder", "welder",
        # Fitness equipment
        "treadmill", "elliptical", "exercise bike", "peloton", "rowing machine",
        "weight bench", "squat rack", "power rack", "cable machine", "smith machine",
        "dumbbells", "barbell", "kettlebell", "home gym",
        # Furniture
        "sofa", "couch", "sectional", "loveseat", "recliner", "sleeper sofa",
        "bed frame", "platform bed", "headboard", "mattress", "memory foam mattress",
        "dresser", "nightstand", "wardrobe", "armoire", "bookshelf", "bookcase",
        "desk", "standing desk", "office chair", "dining table", "dining set",
        "coffee table", "end table", "tv stand", "entertainment center",
        "patio furniture", "outdoor furniture", "deck furniture", "gazebo",
        # Musical instruments
        "piano", "keyboard instrument", "electric guitar", "acoustic guitar", "bass guitar",
        "drum set", "drum kit", "synthesizer", "audio interface", "studio monitor",
        # Photography & video
        "camera", "dslr", "mirrorless camera", "canon camera", "sony camera", "nikon camera",
        "camera lens", "gimbal", "drone", "gopro", "camcorder", "tripod",
        # Other big ticket
        "hot tub", "spa", "sauna", "pool", "above ground pool", "trampoline",
        "electric scooter", "electric bike", "ebike", "hoverboard",
        "golf clubs", "golf set", "kayak", "paddleboard", "surfboard",
        "sewing machine", "embroidery machine", "3d printer", "laser engraver",
        "safe", "gun safe", "security camera", "nvr system",
    ],
    "electronics": [
        "laptop", "macbook", "chromebook", "gaming laptop", "ultrabook",
        "iphone", "samsung galaxy", "pixel phone", "android phone", "smartphone",
        "ipad", "tablet", "android tablet", "surface pro",
        "headphones", "airpods", "earbuds", "wireless headphones", "noise cancelling",
        "monitor", "gaming monitor", "ultrawide monitor", "4k monitor",
        "keyboard", "mechanical keyboard", "gaming keyboard",
        "mouse", "gaming mouse", "trackpad",
        "speaker", "bluetooth speaker", "soundbar", "home theater",
        "gpu", "graphics card", "rtx", "radeon",
        "cpu", "processor", "intel", "amd ryzen",
        "ssd", "nvme", "hard drive", "nas",
        "smartwatch", "apple watch", "garmin", "fitbit",
        "smart home", "echo", "google home", "smart display",
        "printer", "laser printer", "inkjet printer",
        "router", "wifi router", "mesh wifi", "networking",
        "ups battery", "power supply", "pc case",
        "ram", "memory", "ddr5",
        "tablet drawing", "wacom", "drawing tablet",
        "streaming device", "roku", "fire stick", "apple tv",
        "vr headset", "meta quest", "virtual reality",
    ],
    "clothing": [
        "shoes", "sneakers", "boots", "running shoes", "nike", "adidas", "jordan",
        "shirt", "dress shirt", "polo",
        "pants", "jeans", "chinos", "trousers",
        "jacket", "coat", "parka", "puffer jacket", "winter coat",
        "hoodie", "sweatshirt", "sweater",
        "dress", "gown", "blouse",
        "suit", "blazer", "sport coat",
        "handbag", "purse", "backpack", "luggage", "suitcase",
        "watch", "luxury watch", "fossil", "seiko",
        "sunglasses", "rayban", "oakley",
        "athletic wear", "gym clothes", "leggings",
        "underwear", "socks", "accessories",
    ],
    "gaming": [
        "ps5", "playstation 5", "xbox series x", "xbox series s",
        "nintendo switch", "switch oled", "steam deck",
        "gaming pc", "prebuilt pc", "gaming desktop",
        "controller", "ps5 controller", "xbox controller",
        "gaming headset", "gaming chair",
        "video game", "ps5 game", "xbox game", "nintendo game",
        "graphics card gaming", "gaming monitor",
        "capture card", "streaming setup",
        "gaming keyboard mouse", "razer", "corsair", "logitech gaming",
    ],
    "general": []
}

# Search terms — comprehensive coverage of all big ticket categories
SEARCH_TERMS = [
    # TVs & displays
    "OLED TV clearance", "4K TV sale", "smart TV deal", "TV open box",
    # Large appliances
    "refrigerator clearance", "washer dryer sale", "dishwasher deal", "oven range clearance",
    # Small appliances
    "espresso machine sale", "kitchenaid mixer deal", "dyson clearance", "robot vacuum sale",
    # Fitness
    "treadmill clearance", "elliptical sale", "exercise bike deal", "home gym clearance",
    # Furniture
    "mattress sale", "sectional clearance", "office chair deal", "standing desk sale",
    "patio furniture clearance", "dining set clearance",
    # Tools & outdoor
    "dewalt clearance", "milwaukee tool sale", "pressure washer deal", "lawn mower clearance",
    "generator sale", "chainsaw deal",
    # Electronics
    "laptop clearance", "monitor sale", "headphones clearance", "tablet deal",
    "graphics card sale", "gaming laptop clearance",
    # Gaming
    "PS5 deal", "Xbox clearance", "gaming PC sale", "Nintendo Switch deal",
    # Photography
    "mirrorless camera clearance", "camera lens deal", "drone sale",
    # Musical
    "piano keyboard sale", "guitar clearance", "drum set deal",
    # Outdoor & recreation
    "electric bike clearance", "kayak sale", "hot tub deal", "trampoline clearance",
    # Open box & clearance (catches glitches)
    "open box clearance", "scratch dent appliance", "floor model sale",
    "liquidation electronics", "overstock furniture",
]

RSS_SOURCES = [
    {"name": "Slickdeals",           "url": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1", "type": "rss"},
    {"name": "DealNews",             "url": "https://www.dealnews.com/rss/",                                                             "type": "rss"},
    {"name": "Reddit r/deals",       "url": "https://www.reddit.com/r/deals/new.json?limit=25",                                         "type": "reddit"},
    {"name": "Reddit r/buildapcsales","url": "https://www.reddit.com/r/buildapcsales/new.json?limit=25",                                 "type": "reddit"},
    {"name": "Reddit r/GameDeals",   "url": "https://www.reddit.com/r/GameDeals/new.json?limit=25",                                     "type": "reddit"},
    {"name": "Reddit r/frugalmalefashion", "url": "https://www.reddit.com/r/frugalmalefashion/new.json?limit=25",                       "type": "reddit"},
    {"name": "Reddit r/glitch_in_the_matrix", "url": "https://www.reddit.com/r/glitch_in_the_matrix/new.json?limit=25",                "type": "reddit"},
]

# ── Browser headers rotation ───────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

def get_headers(referer="https://www.google.com"):
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def polite_delay():
    """Random delay between requests so we don't look like a bot."""
    time.sleep(random.uniform(2.5, 5.0))

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen_deals():
    try:
        with open(SEEN_DEALS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen_deals(seen):
    os.makedirs("data", exist_ok=True)
    with open(SEEN_DEALS_FILE, "w") as f:
        json.dump(list(seen)[-1000:], f)

def deal_id(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()

def extract_discount(text):
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

def compute_discount(original, sale):
    if original and sale and original > sale > 0:
        return round((1 - sale / original) * 100)
    return None

def parse_price(text):
    """Extract a dollar price from a string."""
    if not text:
        return None
    text = text.strip().replace(",", "")
    match = re.search(r'\$?([\d]+\.?\d*)', text)
    if match:
        try:
            return float(match.group(1))
        except:
            pass
    return None

def categorize(title, description=""):
    text = (title + " " + description).lower()
    for cat, keywords in CATEGORIES.items():
        if cat == "general":
            continue
        if any(kw in text for kw in keywords):
            return cat
    return "general"

def build_deal(title, url, source, original, sale, discount, category=None):
    """Validate and build a deal dict, returns None if it doesn't qualify."""
    if not category:
        category = categorize(title)

    # must have a discount
    if not discount:
        discount = compute_discount(original, sale)
    if not discount or discount < MIN_DISCOUNT:
        return None

    # flipping needs 90%+
    if category == "flipping" and discount < 90:
        return None

    # price floor checks
    if original and original < MIN_ORIGINAL_PRICE.get(category, 20):
        return None
    if sale and sale < MIN_SALE_PRICE.get(category, 3):
        return None

    return {
        "title":    title.strip()[:200],
        "url":      url,
        "source":   source,
        "discount": discount,
        "original": original,
        "sale":     sale,
        "category": category,
        "found_at": datetime.utcnow().isoformat(),
    }

# ── RSS + Reddit fetchers ─────────────────────────────────────────────────────

def fetch_rss(source):
    deals = []
    try:
        r = requests.get(source["url"], headers={"User-Agent": "DealScanner/1.0"}, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            desc  = item.findtext("description") or ""
            url   = item.findtext("link") or ""
            combined = f"{title} {desc}"
            original, sale = None, None
            discount = extract_discount(combined)
            # try to pull prices
            price_match = re.search(r'was\s*\$?([\d,]+\.?\d*).*?now\s*\$?([\d,]+\.?\d*)', combined, re.IGNORECASE)
            if price_match:
                original = parse_price(price_match.group(1))
                sale     = parse_price(price_match.group(2))
            deal = build_deal(title, url, source["name"], original, sale, discount)
            if deal:
                deals.append(deal)
    except Exception as e:
        print(f"  RSS error ({source['name']}): {e}")
    return deals

def fetch_reddit(source):
    deals = []
    try:
        r = requests.get(source["url"], headers={"User-Agent": "DealScanner/1.0"}, timeout=15)
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
        for post in posts:
            d     = post.get("data", {})
            title = d.get("title", "")
            desc  = d.get("selftext", "")
            url   = d.get("url", "") or "https://reddit.com" + d.get("permalink", "")
            combined = f"{title} {desc}"
            original, sale = None, None
            discount = extract_discount(combined)
            price_match = re.search(r'\$?([\d,]+\.?\d*)\s*[-–→]\s*\$?([\d,]+\.?\d*)', combined)
            if price_match:
                original = parse_price(price_match.group(1))
                sale     = parse_price(price_match.group(2))
            deal = build_deal(title, url, source["name"], original, sale, discount)
            if deal:
                deals.append(deal)
    except Exception as e:
        print(f"  Reddit error ({source['name']}): {e}")
    return deals

# ── Retailer scrapers ─────────────────────────────────────────────────────────

def scrape_amazon(search_term):
    deals = []
    url = f"https://www.amazon.com/s?k={requests.utils.quote(search_term)}&s=price-asc-rank"
    try:
        polite_delay()
        r = requests.get(url, headers=get_headers("https://www.amazon.com"), timeout=20)
        if r.status_code != 200:
            print(f"  Amazon blocked ({r.status_code}) for: {search_term}")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select('[data-component-type="s-search-result"]')
        for item in items[:10]:
            try:
                title_el = item.select_one("h2 a span")
                link_el  = item.select_one("h2 a")
                sale_el  = item.select_one(".a-price .a-offscreen")
                was_el   = item.select_one(".a-text-price .a-offscreen")
                badge_el = item.select_one(".savingsPercentage")

                if not title_el or not link_el:
                    continue

                title    = title_el.get_text(strip=True)
                link     = "https://www.amazon.com" + link_el.get("href", "").split("?")[0]
                sale     = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = None
                if badge_el:
                    discount = extract_discount(badge_el.get_text())

                deal = build_deal(title, link, "Amazon", original, sale, discount)
                if deal:
                    print(f"  Amazon deal: {title[:60]} — {deal['discount']}% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print(f"  Amazon error for '{search_term}': {e}")
    return deals

def scrape_walmart(search_term):
    deals = []
    url = f"https://www.walmart.com/search?q={requests.utils.quote(search_term)}&sort=price_low"
    try:
        polite_delay()
        r = requests.get(url, headers=get_headers("https://www.walmart.com"), timeout=20)
        if r.status_code != 200:
            print(f"  Walmart blocked ({r.status_code}) for: {search_term}")
            return deals

        # Walmart embeds JSON data in a script tag
        soup = BeautifulSoup(r.text, "html.parser")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script:
            print(f"  Walmart: no data found for '{search_term}'")
            return deals

        data = json.loads(script.string)
        items = (data.get("props", {})
                     .get("pageProps", {})
                     .get("initialData", {})
                     .get("searchResult", {})
                     .get("itemStacks", [{}])[0]
                     .get("items", []))

        for item in items[:15]:
            try:
                title    = item.get("name", "")
                sale     = item.get("priceInfo", {}).get("currentPrice", {}).get("price")
                original = item.get("priceInfo", {}).get("wasPrice", {}).get("price")
                link     = "https://www.walmart.com" + item.get("canonicalUrl", "")
                discount = compute_discount(original, sale)

                deal = build_deal(title, link, "Walmart", original, sale, discount)
                if deal:
                    print(f"  Walmart deal: {title[:60]} — {deal['discount']}% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print(f"  Walmart error for '{search_term}': {e}")
    return deals

def scrape_target(search_term):
    deals = []
    url = f"https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?keyword={requests.utils.quote(search_term)}&count=24&offset=0&channel=WEB&country=US&pricing_store_id=3991"
    try:
        polite_delay()
        headers = get_headers("https://www.target.com")
        headers["Accept"] = "application/json"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"  Target blocked ({r.status_code}) for: {search_term}")
            return deals

        data = r.json()
        items = data.get("data", {}).get("search", {}).get("products", [])

        for item in items[:15]:
            try:
                title    = item.get("item", {}).get("product_description", {}).get("title", "")
                price_info = item.get("price", {})
                sale     = price_info.get("current_retail")
                original = price_info.get("reg_retail")
                tcin     = item.get("item", {}).get("tcin", "")
                link     = f"https://www.target.com/p/-/A-{tcin}"
                discount = compute_discount(original, sale)

                deal = build_deal(title, link, "Target", original, sale, discount)
                if deal:
                    print(f"  Target deal: {title[:60]} — {deal['discount']}% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print(f"  Target error for '{search_term}': {e}")
    return deals

def scrape_homedepot(search_term):
    deals = []
    url = f"https://www.homedepot.com/s/{requests.utils.quote(search_term)}?sortorder=asc&sortby=price"
    try:
        polite_delay()
        r = requests.get(url, headers=get_headers("https://www.homedepot.com"), timeout=20)
        if r.status_code != 200:
            print(f"  Home Depot blocked ({r.status_code}) for: {search_term}")
            return deals

        soup = BeautifulSoup(r.text, "html.parser")

        # Home Depot embeds product data in a script tag too
        for script in soup.find_all("script"):
            text = script.string or ""
            if "__REDUX_STATE__" in text or "productResults" in text:
                try:
                    json_match = re.search(r'window\.__REDUX_STATE__\s*=\s*({.*?});', text, re.DOTALL)
                    if json_match:
                        data  = json.loads(json_match.group(1))
                        prods = (data.get("productSearch", {})
                                     .get("productSearchResult", {})
                                     .get("products", []))
                        for prod in prods[:15]:
                            try:
                                title    = prod.get("modelIdentifier", "") + " " + prod.get("productLabel", "")
                                sale     = prod.get("pricing", {}).get("value")
                                original = prod.get("pricing", {}).get("original")
                                item_id  = prod.get("itemId", "")
                                link     = f"https://www.homedepot.com/p/{item_id}"
                                discount = compute_discount(original, sale)
                                deal = build_deal(title.strip(), link, "Home Depot", original, sale, discount)
                                if deal:
                                    print(f"  Home Depot deal: {title[:60]} — {deal['discount']}% off")
                                    deals.append(deal)
                            except:
                                continue
                except:
                    pass
    except Exception as e:
        print(f"  Home Depot error for '{search_term}': {e}")
    return deals

def scrape_newegg(search_term):
    deals = []
    url = f"https://www.newegg.com/p/pl?d={requests.utils.quote(search_term)}&Order=1"
    try:
        polite_delay()
        r = requests.get(url, headers=get_headers("https://www.newegg.com"), timeout=20)
        if r.status_code != 200:
            print(f"  Newegg blocked ({r.status_code}) for: {search_term}")
            return deals

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".item-cell")

        for item in items[:15]:
            try:
                title_el   = item.select_one(".item-title")
                sale_el    = item.select_one(".price-current")
                was_el     = item.select_one(".price-was-data")
                link_el    = item.select_one(".item-title")
                discount_el= item.select_one(".price-save-percent")

                if not title_el:
                    continue

                title    = title_el.get_text(strip=True)
                link     = title_el.get("href", "") if title_el.name == "a" else (link_el.get("href", "") if link_el else "")
                sale     = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = extract_discount(discount_el.get_text() if discount_el else "")

                deal = build_deal(title, link, "Newegg", original, sale, discount)
                if deal:
                    print(f"  Newegg deal: {title[:60]} — {deal['discount']}% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print(f"  Newegg error for '{search_term}': {e}")
    return deals

def scrape_bestbuy(search_term):
    deals = []
    url = f"https://www.bestbuy.com/site/searchpage.jsp?st={requests.utils.quote(search_term)}&sort=pricelow"
    try:
        polite_delay()
        r = requests.get(url, headers=get_headers("https://www.bestbuy.com"), timeout=20)
        if r.status_code != 200:
            print(f"  Best Buy blocked ({r.status_code}) for: {search_term}")
            return deals

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".sku-item")

        for item in items[:15]:
            try:
                title_el    = item.select_one(".sku-title a")
                sale_el     = item.select_one(".priceView-customer-price span")
                was_el      = item.select_one(".pricing-price__regular-price")
                savings_el  = item.select_one(".pricing-price__savings-percentage")

                if not title_el:
                    continue

                title    = title_el.get_text(strip=True)
                link     = "https://www.bestbuy.com" + title_el.get("href", "")
                sale     = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = extract_discount(savings_el.get_text() if savings_el else "")

                deal = build_deal(title, link, "Best Buy", original, sale, discount)
                if deal:
                    print(f"  Best Buy deal: {title[:60]} — {deal['discount']}% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print(f"  Best Buy error for '{search_term}': {e}")
    return deals

# ── Notifier ──────────────────────────────────────────────────────────────────

def should_notify(deal):
    """Only push notify for high value flipper and glitch deals."""
    is_glitch = deal.get('discount', 0) >= 90 and deal.get('original', 0) and deal['original'] >= 100
    is_flipper = deal.get('category') == 'flipping'
    return is_glitch or is_flipper
    if not PUSHOVER_USER_KEY or not PUSHOVER_TOKEN:
        print("  Pushover keys not set — skipping")
        return

    original_str = f"${deal['original']:.2f}" if deal['original'] else "?"
    sale_str     = f"${deal['sale']:.2f}"     if deal['sale']     else "?"
    price_line   = f"{original_str} → {sale_str}" if deal['original'] and deal['sale'] else ""

    is_glitch = deal['discount'] >= 90 and deal.get('original', 0) and deal['original'] >= 100
    title_prefix = "⚡ GLITCH PRICE" if is_glitch else "🏷 Deal Alert"

    message = (
        f"{deal['discount']}% OFF  {price_line}\n"
        f"📂 {deal['category'].title()}\n"
        f"🏪 {deal['source']}"
    ).strip()

    payload = {
        "token":     PUSHOVER_TOKEN,
        "user":      PUSHOVER_USER_KEY,
        "title":     f"{title_prefix}: {deal['title'][:80]}",
        "message":   message,
        "url":       deal["url"],
        "url_title": "View Deal",
        "priority":  1 if is_glitch else 0,
        "sound":     "cashregister",
    }

    try:
        r = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
        r.raise_for_status()
        print(f"  Notified: {deal['title'][:60]}")
    except Exception as e:
        print(f"  Pushover error: {e}")

# ── Deal log ──────────────────────────────────────────────────────────────────

# How long to keep deals before expiring them
DEAL_EXPIRY_HOURS = {
    "glitch":      2,    # glitch prices disappear fast — remove after 2 hours
    "retailer":    24,   # direct retailer scrapes — remove after 24 hours
    "rss":         48,   # RSS/Reddit deals — keep 48 hours
}

RETAILER_SOURCES = {"Amazon", "Walmart", "Target", "Home Depot", "Newegg", "Best Buy"}

def is_expired(deal):
    """Return True if the deal is too old to show."""
    try:
        found = datetime.fromisoformat(deal["found_at"])
        age_hours = (datetime.utcnow() - found).total_seconds() / 3600

        is_glitch   = deal.get("discount", 0) >= 90 and deal.get("original", 0) >= 100
        is_retailer = deal.get("source", "") in RETAILER_SOURCES

        if is_glitch:
            return age_hours > DEAL_EXPIRY_HOURS["glitch"]
        elif is_retailer:
            return age_hours > DEAL_EXPIRY_HOURS["retailer"]
        else:
            return age_hours > DEAL_EXPIRY_HOURS["rss"]
    except:
        return False

def update_deals_log(new_deals, active_urls=None):
    """Merge new deals in, expire old ones, optionally remove deals no longer seen."""
    log_file = "data/deals.json"
    try:
        with open(log_file, "r") as f:
            existing = json.load(f)
    except:
        existing = []

    # Remove expired deals
    before = len(existing)
    existing = [d for d in existing if not is_expired(d)]
    expired_count = before - len(existing)
    if expired_count:
        print(f"  Removed {expired_count} expired deal(s)")

    # Remove retailer deals whose URL was scanned this run but price no longer qualifies
    if active_urls is not None:
        scanned_sources = {d.get("source") for d in new_deals if d.get("source") in RETAILER_SOURCES}
        before = len(existing)
        existing = [
            d for d in existing
            if not (d.get("source") in scanned_sources and d.get("url") not in active_urls)
        ]
        removed = before - len(existing)
        if removed:
            print(f"  Removed {removed} deal(s) no longer at discount price")

    # Merge — new deals go to the top, keep max 200
    combined = (new_deals + existing)[:200]
    os.makedirs("data", exist_ok=True)
    with open(log_file, "w") as f:
        json.dump(combined, f, indent=2)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.utcnow().isoformat()}] Deal scanner starting...")
    seen = load_seen_deals()
    all_new_deals = []
    active_urls   = set()  # tracks every URL that qualified this run

    # ── RSS + Reddit
    for source in RSS_SOURCES:
        print(f"Checking {source['name']}...")
        if source["type"] == "rss":
            deals = fetch_rss(source)
        else:
            deals = fetch_reddit(source)
        for deal in deals:
            did = deal_id(deal["title"], deal["url"])
            if did not in seen:
                seen.add(did)
                all_new_deals.append(deal)
                print(f"  NEW: {deal['title'][:60]} ({deal['discount']}% off)")
                if should_notify(deal):
                    send_pushover(deal)

    # ── Retailer scrapers
    retailers = [
        ("Amazon",     scrape_amazon),
        ("Walmart",    scrape_walmart),
        ("Target",     scrape_target),
        ("Home Depot", scrape_homedepot),
        ("Newegg",     scrape_newegg),
        ("Best Buy",   scrape_bestbuy),
    ]

    for retailer_name, scraper_fn in retailers:
        print(f"\nScraping {retailer_name}...")
        terms = random.sample(SEARCH_TERMS, min(8, len(SEARCH_TERMS)))
        for term in terms:
            print(f"  Searching: {term}")
            try:
                deals = scraper_fn(term)
                for deal in deals:
                    active_urls.add(deal["url"])  # track every qualifying URL
                    did = deal_id(deal["title"], deal["url"])
                    if did not in seen:
                        seen.add(did)
                        all_new_deals.append(deal)
                        if should_notify(deal):
                            send_pushover(deal)
            except Exception as e:
                print(f"  Error scraping {retailer_name} for '{term}': {e}")
            polite_delay()

    # Update log — passes active_urls so stale retailer deals get removed
    update_deals_log(all_new_deals, active_urls=active_urls)
    save_seen_deals(seen)
    print(f"\nDone. {len(all_new_deals)} new deals found.")

if __name__ == "__main__":
    main()
