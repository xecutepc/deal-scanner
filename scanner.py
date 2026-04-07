import requests
import sys
import json
import os
import re
import time
import random
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup

PUSHOVER_USER_KEY = os.environ.get("PUSHOVER_USER_KEY", "")
PUSHOVER_TOKEN = os.environ.get("PUSHOVER_TOKEN", "")
MIN_DISCOUNT = 80
SEEN_DEALS_FILE = "data/seen_deals.json"

MIN_ORIGINAL_PRICE = {
    "flipping": 200,
    "electronics": 50,
    "gaming": 30,
    "clothing": 40,
    "general": 20,
}

MIN_SALE_PRICE = {
    "flipping": 10,
    "electronics": 5,
    "gaming": 5,
    "clothing": 5,
    "general": 3,
}

GLITCH_MIN_ORIGINAL = 50
GLITCH_MIN_DISCOUNT = 90

CATEGORIES = {
    "flipping": [
        "tv", "television", "oled", "qled", "4k tv", "8k tv", "smart tv",
        "refrigerator", "fridge", "freezer", "washer", "dryer", "dishwasher",
        "oven", "range", "stove", "microwave", "espresso", "kitchenaid",
        "vacuum", "dyson", "robot vacuum", "roomba", "air purifier",
        "air conditioner", "portable ac", "generator", "pressure washer",
        "lawnmower", "lawn mower", "riding mower", "snow blower", "chainsaw",
        "dewalt", "milwaukee", "makita", "ryobi", "table saw", "miter saw",
        "drill press", "welder", "air compressor",
        "treadmill", "elliptical", "exercise bike", "peloton", "rowing machine",
        "squat rack", "power rack", "home gym",
        "sofa", "couch", "sectional", "recliner", "mattress", "bed frame",
        "dresser", "wardrobe", "desk", "standing desk", "office chair",
        "dining table", "dining set", "patio furniture", "outdoor furniture",
        "hot tub", "sauna", "trampoline", "electric bike", "ebike",
        "piano", "guitar", "drum set", "synthesizer",
        "camera", "dslr", "mirrorless", "drone", "projector",
        "massage chair", "electric fireplace", "safe", "gun safe",
        "3d printer", "laser engraver", "sewing machine",
    ],
    "electronics": [
        "laptop", "macbook", "chromebook", "iphone", "samsung galaxy",
        "ipad", "tablet", "headphones", "airpods", "earbuds",
        "monitor", "keyboard", "mouse", "speaker", "soundbar",
        "gpu", "graphics card", "rtx", "radeon", "cpu", "processor",
        "ssd", "nvme", "hard drive", "smartwatch", "apple watch",
        "printer", "router", "wifi", "smart home", "echo",
        "streaming device", "roku", "fire stick", "vr headset",
    ],
    "clothing": [
        "shoes", "sneakers", "boots", "nike", "adidas", "jordan",
        "shirt", "pants", "jacket", "coat", "hoodie", "dress",
        "suit", "blazer", "handbag", "luggage", "suitcase", "sunglasses",
    ],
    "gaming": [
        "ps5", "playstation 5", "xbox series", "nintendo switch",
        "steam deck", "gaming pc", "controller", "gaming headset",
        "gaming chair", "video game", "graphics card gaming",
    ],
    "general": []
}

RSS_SOURCES = [
    {"name": "Slickdeals", "url": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"},
    {"name": "DealNews Electronics", "url": "https://www.dealnews.com/c142/Electronics/?rss=1"},
    {"name": "DealNews Computers", "url": "https://www.dealnews.com/c39/Computers/?rss=1"},
    {"name": "DealNews Home", "url": "https://www.dealnews.com/c238/Home/?rss=1"},
    {"name": "DealNews Tools", "url": "https://www.dealnews.com/c825/Tools-Garden/?rss=1"},
    {"name": "Reddit r/deals", "url": "https://www.reddit.com/r/deals/.rss"},
    {"name": "Reddit r/buildapcsales", "url": "https://www.reddit.com/r/buildapcsales/.rss"},
    {"name": "Reddit r/GameDeals", "url": "https://www.reddit.com/r/GameDeals/.rss"},
    {"name": "Reddit r/frugalmalefashion", "url": "https://www.reddit.com/r/frugalmalefashion/.rss"},
    {"name": "Reddit r/glitch_in_the_matrix", "url": "https://www.reddit.com/r/glitch_in_the_matrix/.rss"},
]

SEARCH_TERMS = [
    "OLED TV clearance", "4K TV sale", "smart TV deal",
    "refrigerator clearance", "washer dryer sale", "dishwasher deal",
    "espresso machine sale", "dyson clearance", "robot vacuum sale",
    "treadmill clearance", "elliptical sale", "exercise bike deal",
    "mattress sale", "sectional clearance", "office chair deal",
    "standing desk sale", "patio furniture clearance", "dining set clearance",
    "dewalt clearance", "milwaukee tool sale", "pressure washer deal",
    "lawn mower clearance", "generator sale", "chainsaw deal",
    "laptop clearance", "monitor sale", "headphones clearance", "tablet deal",
    "graphics card sale", "gaming laptop clearance",
    "PS5 deal", "Xbox clearance", "Nintendo Switch deal",
    "mirrorless camera clearance", "drone sale",
    "electric bike clearance", "hot tub deal", "trampoline clearance",
    "open box clearance", "scratch dent appliance", "floor model sale",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

def get_headers(referer="https://www.google.com"):
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
    }

def polite_delay():
    time.sleep(random.uniform(2.0, 4.0))

def make_session(base_url):
    session = requests.Session()
    session.headers.update(get_headers(base_url))
    try:
        session.get(base_url, timeout=8)
        polite_delay()
    except:
        pass
    return session

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
    return hashlib.md5((title + url).encode()).hexdigest()

def extract_discount(text):
    patterns = [
        r'(\d+)%\s*off',
        r'save\s+(\d+)%',
        r'(\d+)%\s*discount',
        r'\((\d+)%\s*off\)',
        r'-(\d+)%',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            v = int(m.group(1))
            if 50 <= v <= 99:
                return v
    return None

def parse_price(text):
    if not text:
        return None
    text = str(text).strip().replace(",", "")
    m = re.search(r'\$?([\d]+\.?\d*)', text)
    if m:
        try:
            v = float(m.group(1))
            return v if v > 0 else None
        except:
            pass
    return None

def compute_discount(original, sale):
    if original and sale and original > sale > 0:
        return round((1 - sale / original) * 100)
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
    if not title or not url:
        return None
    if not category:
        category = categorize(title)
    if not discount:
        discount = compute_discount(original, sale)
    if not discount or discount < MIN_DISCOUNT:
        return None
    if category == "flipping" and discount < 90:
        return None
    if original and original < MIN_ORIGINAL_PRICE.get(category, 20):
        return None
    if sale and sale < MIN_SALE_PRICE.get(category, 3):
        return None
    is_glitch = bool(discount >= GLITCH_MIN_DISCOUNT and original and original >= GLITCH_MIN_ORIGINAL)
    return {
        "title": title.strip()[:200],
        "url": url,
        "source": source,
        "discount": discount,
        "original": original,
        "sale": sale,
        "category": category,
        "glitch": is_glitch,
        "found_at": datetime.utcnow().isoformat(),
    }

def fetch_rss(source):
    deals = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DealScanner/1.0)"}
        r = requests.get(source["url"], headers=headers, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = (root.findall(".//item") or
                 root.findall(".//atom:entry", ns) or
                 root.findall(".//entry"))
        for item in items:
            title = (item.findtext("title") or
                     item.findtext("atom:title", namespaces=ns) or "")
            title = re.sub(r'<[^>]+>', '', title).strip()
            desc = (item.findtext("description") or
                    item.findtext("atom:summary", namespaces=ns) or
                    item.findtext("atom:content", namespaces=ns) or "")
            desc = re.sub(r'<[^>]+>', '', desc).strip()
            link_el = item.find("link")
            if link_el is not None:
                url = link_el.text or link_el.get("href", "")
            else:
                url = ""
            combined = title + " " + desc
            discount = extract_discount(combined)
            original, sale = None, None
            price_match = re.search(
                r'(?:was|reg|retail|orig)[:\s]*\$?([\d,]+\.?\d*).*?(?:now|sale|for|only)[:\s]*\$?([\d,]+\.?\d*)',
                combined, re.IGNORECASE)
            if price_match:
                original = parse_price(price_match.group(1))
                sale = parse_price(price_match.group(2))
            else:
                arrow = re.search(r'\$?([\d,]+\.?\d*)\s*[-]+\s*\$?([\d,]+\.?\d*)', combined)
                if arrow:
                    original = parse_price(arrow.group(1))
                    sale = parse_price(arrow.group(2))
            deal = build_deal(title, url, source["name"], original, sale, discount)
            if deal:
                deals.append(deal)
    except Exception as e:
        print("  RSS error (" + source["name"] + "): " + str(e))
    return deals

def scrape_amazon(search_term):
    deals = []
    try:
        session = make_session("https://www.amazon.com")
        url = "https://www.amazon.com/s?k=" + requests.utils.quote(search_term) + "&s=price-asc-rank"
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  Amazon blocked (" + str(r.status_code) + ") for: " + search_term)
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select('[data-component-type="s-search-result"]')
        if not items:
            print("  Amazon: no results for: " + search_term)
            return deals
        for item in items[:10]:
            try:
                title_el = item.select_one("h2 a span")
                link_el = item.select_one("h2 a")
                sale_el = item.select_one(".a-price .a-offscreen")
                was_el = item.select_one(".a-text-price .a-offscreen")
                badge_el = item.select_one(".savingsPercentage")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                link = "https://www.amazon.com" + link_el.get("href", "").split("?")[0]
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = extract_discount(badge_el.get_text() if badge_el else "")
                deal = build_deal(title, link, "Amazon", original, sale, discount)
                if deal:
                    print("  Amazon deal: " + title[:60] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Amazon error for " + search_term + ": " + str(e))
    return deals

def scrape_walmart(search_term):
    deals = []
    try:
        session = make_session("https://www.walmart.com")
        url = "https://www.walmart.com/search?q=" + requests.utils.quote(search_term) + "&sort=price_low"
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  Walmart blocked (" + str(r.status_code) + ") for: " + search_term)
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script or not script.string:
            print("  Walmart: no data for: " + search_term)
            return deals
        data = json.loads(script.string)
        try:
            stacks = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"]
            items = []
            for stack in stacks:
                items.extend(stack.get("items", []))
        except (KeyError, TypeError):
            return deals
        for item in items[:20]:
            try:
                if not isinstance(item, dict):
                    continue
                title = item.get("name", "")
                price_info = item.get("priceInfo", {}) or {}
                sale = (price_info.get("currentPrice") or {}).get("price")
                original = (price_info.get("wasPrice") or {}).get("price")
                canon = item.get("canonicalUrl", "")
                link = "https://www.walmart.com" + canon if canon else "https://www.walmart.com"
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Walmart", original, sale, discount)
                if deal:
                    print("  Walmart deal: " + title[:60] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Walmart error for " + search_term + ": " + str(e))
    return deals

def scrape_target(search_term):
    deals = []
    try:
        session = make_session("https://www.target.com")
        api_url = (
            "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2"
            "?keyword=" + requests.utils.quote(search_term) +
            "&count=24&offset=0&channel=WEB&country=US&pricing_store_id=3991&visitor_id=anonymous"
        )
        session.headers.update({"Accept": "application/json"})
        r = session.get(api_url, timeout=20)
        if r.status_code != 200:
            print("  Target blocked (" + str(r.status_code) + ") for: " + search_term)
            return deals
        data = r.json()
        products = data.get("data", {}).get("search", {}).get("products", [])
        for item in products[:15]:
            try:
                title = item.get("item", {}).get("product_description", {}).get("title", "")
                price_info = item.get("price", {}) or {}
                sale = price_info.get("current_retail")
                original = price_info.get("reg_retail")
                tcin = item.get("item", {}).get("tcin", "")
                link = "https://www.target.com/p/-/A-" + tcin
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Target", original, sale, discount)
                if deal:
                    print("  Target deal: " + title[:60] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Target error for " + search_term + ": " + str(e))
    return deals

def scrape_bestbuy(search_term):
    deals = []
    try:
        session = make_session("https://www.bestbuy.com")
        url = "https://www.bestbuy.com/site/searchpage.jsp?st=" + requests.utils.quote(search_term) + "&sort=pricelow"
        r = session.get(url, timeout=25)
        if r.status_code != 200:
            print("  Best Buy blocked (" + str(r.status_code) + ") for: " + search_term)
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".sku-item")
        if not items:
            print("  Best Buy: no results for: " + search_term)
            return deals
        for item in items[:15]:
            try:
                title_el = item.select_one(".sku-title a")
                sale_el = item.select_one(".priceView-customer-price span")
                was_el = item.select_one(".pricing-price__regular-price")
                savings_el = item.select_one(".pricing-price__savings-percentage")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link = "https://www.bestbuy.com" + title_el.get("href", "")
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = extract_discount(savings_el.get_text() if savings_el else "")
                deal = build_deal(title, link, "Best Buy", original, sale, discount)
                if deal:
                    print("  Best Buy deal: " + title[:60] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Best Buy error for " + search_term + ": " + str(e))
    return deals

def scrape_homedepot(search_term):
    deals = []
    try:
        session = make_session("https://www.homedepot.com")
        url = "https://www.homedepot.com/s/" + requests.utils.quote(search_term) + "?sortorder=asc&sortby=price"
        r = session.get(url, timeout=25)
        if r.status_code != 200:
            print("  Home Depot blocked (" + str(r.status_code) + ") for: " + search_term)
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        for script in soup.find_all("script"):
            text = script.string or ""
            if "__REDUX_STATE__" in text:
                try:
                    match = re.search(r'__REDUX_STATE__\s*=\s*({.*?});\s*</script>', text, re.DOTALL)
                    if not match:
                        continue
                    data = json.loads(match.group(1))
                    prods = (data.get("productSearch", {})
                                 .get("productSearchResult", {})
                                 .get("products", []))
                    for prod in prods[:15]:
                        try:
                            title = prod.get("productLabel", "")
                            sale = prod.get("pricing", {}).get("value")
                            original = prod.get("pricing", {}).get("original")
                            item_id = prod.get("itemId", "")
                            link = "https://www.homedepot.com/p/" + item_id
                            discount = compute_discount(original, sale)
                            deal = build_deal(title, link, "Home Depot", original, sale, discount)
                            if deal:
                                print("  Home Depot deal: " + title[:60] + " - " + str(deal["discount"]) + "% off")
                                deals.append(deal)
                        except:
                            continue
                except Exception as e:
                    print("  Home Depot parse error: " + str(e))
    except Exception as e:
        print("  Home Depot error for " + search_term + ": " + str(e))
    return deals

def scrape_newegg(search_term):
    deals = []
    try:
        session = make_session("https://www.newegg.com")
        url = "https://www.newegg.com/p/pl?d=" + requests.utils.quote(search_term) + "&Order=1"
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  Newegg blocked (" + str(r.status_code) + ") for: " + search_term)
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".item-cell")
        if not items:
            print("  Newegg: no results for: " + search_term)
            return deals
        for item in items[:15]:
            try:
                title_el = item.select_one(".item-title")
                sale_el = item.select_one(".price-current")
                was_el = item.select_one(".price-was-data")
                discount_el = item.select_one(".price-save-percent")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "") if title_el.name == "a" else ""
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = extract_discount(discount_el.get_text() if discount_el else "")
                deal = build_deal(title, link, "Newegg", original, sale, discount)
                if deal:
                    print("  Newegg deal: " + title[:60] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Newegg error for " + search_term + ": " + str(e))
    return deals

def should_notify(deal):
    return deal.get("glitch", False) or deal.get("category") == "flipping"

def send_pushover(deal):
    if not PUSHOVER_USER_KEY or not PUSHOVER_TOKEN:
        return
    is_glitch = deal.get("glitch", False)
    title_prefix = "GLITCH PRICE" if is_glitch else "Flipper Deal"
    original_str = "$" + str(round(deal["original"], 2)) if deal["original"] else "?"
    sale_str = "$" + str(round(deal["sale"], 2)) if deal["sale"] else "?"
    price_line = original_str + " -> " + sale_str if deal["original"] and deal["sale"] else ""
    message = str(deal["discount"]) + "% OFF  " + price_line + "\nCat: " + deal["category"].title() + "\nStore: " + deal["source"]
    payload = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title_prefix + ": " + deal["title"][:80],
        "message": message,
        "url": deal["url"],
        "url_title": "View Deal",
        "priority": 1 if is_glitch else 0,
        "sound": "cashregister",
    }
    try:
        r = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
        r.raise_for_status()
        print("  Notified: " + deal["title"][:60])
    except Exception as e:
        print("  Pushover error: " + str(e))

DEAL_EXPIRY_HOURS = {"glitch": 2, "retailer": 24, "rss": 48}
RETAILER_SOURCES = {"Amazon", "Walmart", "Target", "Best Buy", "Home Depot", "Newegg"}

def is_expired(deal):
    try:
        age = (datetime.utcnow() - datetime.fromisoformat(deal["found_at"])).total_seconds() / 3600
        if deal.get("glitch"):
            return age > DEAL_EXPIRY_HOURS["glitch"]
        if deal.get("source") in RETAILER_SOURCES:
            return age > DEAL_EXPIRY_HOURS["retailer"]
        return age > DEAL_EXPIRY_HOURS["rss"]
    except:
        return False

def update_deals_log(new_deals, active_urls=None):
    log_file = "data/deals.json"
    try:
        with open(log_file, "r") as f:
            existing = json.load(f)
    except:
        existing = []
    before = len(existing)
    existing = [d for d in existing if not is_expired(d)]
    if len(existing) < before:
        print("  Removed " + str(before - len(existing)) + " expired deals")
    if active_urls:
        scanned = {d.get("source") for d in new_deals if d.get("source") in RETAILER_SOURCES}
        before = len(existing)
        existing = [d for d in existing if not (d.get("source") in scanned and d.get("url") not in active_urls)]
        if len(existing) < before:
            print("  Removed " + str(before - len(existing)) + " stale deals")
    combined = (new_deals + existing)[:200]
    os.makedirs("data", exist_ok=True)
    with open(log_file, "w") as f:
        json.dump(combined, f, indent=2)

def main():
    sys.stdout.reconfigure(line_buffering=True)
    print("[" + datetime.utcnow().isoformat() + "] Deal scanner starting...")
    seen = load_seen_deals()
    all_new_deals = []
    active_urls = set()

    for source in RSS_SOURCES:
        print("Checking " + source["name"] + "...")
        for deal in fetch_rss(source):
            did = deal_id(deal["title"], deal["url"])
            if did not in seen:
                seen.add(did)
                all_new_deals.append(deal)
                print("  NEW: " + deal["title"][:60] + " (" + str(deal["discount"]) + "% off)")
                if should_notify(deal):
                    send_pushover(deal)

    retailers = [
        ("Amazon", scrape_amazon),
        ("Walmart", scrape_walmart),
        ("Target", scrape_target),
        ("Best Buy", scrape_bestbuy),
        ("Home Depot", scrape_homedepot),
        ("Newegg", scrape_newegg),
    ]

    for retailer_name, scraper_fn in retailers:
        print("\nScraping " + retailer_name + "...")
        terms = random.sample(SEARCH_TERMS, min(6, len(SEARCH_TERMS)))
        for term in terms:
            print("  Searching: " + term)
            try:
                for deal in scraper_fn(term):
                    active_urls.add(deal["url"])
                    did = deal_id(deal["title"], deal["url"])
                    if did not in seen:
                        seen.add(did)
                        all_new_deals.append(deal)
                        if should_notify(deal):
                            send_pushover(deal)
            except Exception as e:
                print("  Error: " + str(e))
            polite_delay()

    update_deals_log(all_new_deals, active_urls=active_urls)
    save_seen_deals(seen)
    print("\nDone. " + str(len(all_new_deals)) + " new deals found.")

if __name__ == "__main__":
    main()