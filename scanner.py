import requests
import json
import os
import re
import time
import random
import hashlib
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup

sys.stdout.reconfigure(line_buffering=True)

PUSHOVER_USER_KEY = os.environ.get("PUSHOVER_USER_KEY", "")
PUSHOVER_TOKEN = os.environ.get("PUSHOVER_TOKEN", "")
MIN_DISCOUNT = 80
SEEN_DEALS_FILE = "data/seen_deals.json"
CLOUDFLARE_PROXY = "https://bitter-meadow-98b9.xecutepc.workers.dev"

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
HOT_MIN_DISCOUNT = 50
HOT_MIN_ORIGINAL = 50

CATEGORIES = {
    "flipping": [
        "tv", "television", "oled", "qled", "refrigerator", "fridge",
        "washer", "dryer", "dishwasher", "oven", "stove", "freezer",
        "espresso", "kitchenaid", "dyson", "vacuum", "robot vacuum",
        "air conditioner", "generator", "pressure washer", "lawn mower",
        "chainsaw", "dewalt", "milwaukee", "makita", "table saw",
        "treadmill", "elliptical", "exercise bike", "rowing machine",
        "squat rack", "home gym", "sofa", "couch", "sectional",
        "mattress", "bed frame", "dresser", "standing desk", "office chair",
        "dining table", "patio furniture", "hot tub", "trampoline",
        "electric bike", "piano", "guitar", "drum", "camera", "drone",
        "massage chair", "safe", "3d printer", "sewing machine",
    ],
    "electronics": [
        "laptop", "macbook", "iphone", "samsung", "ipad", "tablet",
        "headphones", "airpods", "earbuds", "monitor", "keyboard",
        "mouse", "speaker", "soundbar", "gpu", "graphics card",
        "cpu", "processor", "ssd", "hard drive", "smartwatch",
        "printer", "router", "smart home", "roku", "fire stick",
        "vr headset", "projector",
    ],
    "clothing": [
        "shoes", "sneakers", "boots", "nike", "adidas", "jordan",
        "shirt", "pants", "jacket", "coat", "hoodie", "dress",
        "suit", "handbag", "luggage", "sunglasses",
    ],
    "gaming": [
        "ps5", "playstation", "xbox", "nintendo switch", "steam deck",
        "gaming pc", "controller", "gaming headset", "gaming chair",
    ],
    "general": []
}

# Amazon category pages sorted by discount
AMAZON_CATEGORIES = [
    ("Electronics",        "https://www.amazon.com/s?i=electronics&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Computers",          "https://www.amazon.com/s?i=computers&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Video Games",        "https://www.amazon.com/s?i=videogames&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Appliances",         "https://www.amazon.com/s?i=appliances&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Tools",              "https://www.amazon.com/s?i=tools&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Furniture",          "https://www.amazon.com/s?i=furniture&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Sports",             "https://www.amazon.com/s?i=sporting-goods&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Clothing",           "https://www.amazon.com/s?i=fashion&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Toys",               "https://www.amazon.com/s?i=toys-and-games&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Automotive",         "https://www.amazon.com/s?i=automotive&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Musical Instruments","https://www.amazon.com/s?i=mi&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Camera",             "https://www.amazon.com/s?i=photo&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Office",             "https://www.amazon.com/s?i=office-products&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Pet Supplies",       "https://www.amazon.com/s?i=pets&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Garden",             "https://www.amazon.com/s?i=lawngarden&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Health",             "https://www.amazon.com/s?i=hpc&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Baby",               "https://www.amazon.com/s?i=baby-products&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Kitchen",            "https://www.amazon.com/s?i=kitchen&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Luggage",            "https://www.amazon.com/s?i=luggage&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Shoes",              "https://www.amazon.com/s?i=shoes&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Watches",            "https://www.amazon.com/s?i=watches&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
    ("Industrial",         "https://www.amazon.com/s?i=industrial&rh=p_n_pct-off-with-tax%3A8-&s=price-asc-rank"),
]

WALMART_CATEGORIES = [
    ("Electronics",        "https://www.walmart.com/browse/electronics/3944"),
    ("TVs",                "https://www.walmart.com/browse/electronics/tvs/3944_1060825_447913"),
    ("Laptops",            "https://www.walmart.com/browse/electronics/laptops/3944_3951_132959"),
    ("Cell Phones",        "https://www.walmart.com/browse/electronics/cell-phones/3944_1105910"),
    ("Video Games",        "https://www.walmart.com/browse/video-games/2636"),
    ("Appliances",         "https://www.walmart.com/browse/appliances/1115153"),
    ("Refrigerators",      "https://www.walmart.com/browse/appliances/refrigerators/1115153_1067317"),
    ("Washers Dryers",     "https://www.walmart.com/browse/appliances/washers-dryers/1115153_1067319"),
    ("Furniture",          "https://www.walmart.com/browse/furniture/103150"),
    ("Mattresses",         "https://www.walmart.com/browse/furniture/mattresses/103150_3093924"),
    ("Tools",              "https://www.walmart.com/browse/tools/1032764"),
    ("Power Tools",        "https://www.walmart.com/browse/tools/power-tools/1032764_1229722"),
    ("Sports",             "https://www.walmart.com/browse/sports-outdoors/4125"),
    ("Exercise",           "https://www.walmart.com/browse/sports-outdoors/exercise-fitness/4125_4134"),
    ("Clothing",           "https://www.walmart.com/browse/clothing/5438"),
    ("Shoes",              "https://www.walmart.com/browse/shoes/1334134"),
    ("Toys",               "https://www.walmart.com/browse/toys/4171"),
    ("Auto",               "https://www.walmart.com/browse/auto-tires/91083"),
    ("Garden",             "https://www.walmart.com/browse/garden-outdoor/5428"),
    ("Patio Furniture",    "https://www.walmart.com/browse/garden-outdoor/patio-furniture/5428_1231459"),
    ("Home",               "https://www.walmart.com/browse/home/4044"),
    ("Bedding",            "https://www.walmart.com/browse/home/bedding/4044_103652"),
    ("Kitchen",            "https://www.walmart.com/browse/home/kitchen/4044_623679"),
    ("Baby",               "https://www.walmart.com/browse/baby/5427"),
    ("Health",             "https://www.walmart.com/browse/health/976760"),
    ("Jewelry",            "https://www.walmart.com/browse/jewelry-watches/3891"),
    ("Outdoor Power",      "https://www.walmart.com/browse/garden-outdoor/outdoor-power-equipment/5428_1231461"),
]

TARGET_CATEGORIES = [
    ("Electronics",        "https://www.target.com/c/electronics/-/N-5xt1a"),
    ("TVs",                "https://www.target.com/c/tvs-home-theater/-/N-5xtge"),
    ("Computers",          "https://www.target.com/c/computers-tablets/-/N-5xt92"),
    ("Cell Phones",        "https://www.target.com/c/cell-phones/-/N-5xt1e"),
    ("Video Games",        "https://www.target.com/c/video-games/-/N-5xt44"),
    ("Appliances",         "https://www.target.com/c/appliances/-/N-55b1y"),
    ("Kitchen Appliances", "https://www.target.com/c/kitchen-appliances/-/N-5xszn"),
    ("Furniture",          "https://www.target.com/c/furniture/-/N-5xtnr"),
    ("Outdoor Furniture",  "https://www.target.com/c/patio-garden-furniture/-/N-5xtjz"),
    ("Mattresses",         "https://www.target.com/c/mattresses/-/N-5xu1n"),
    ("Sports",             "https://www.target.com/c/sports-outdoors/-/N-5xte9"),
    ("Exercise",           "https://www.target.com/c/exercise-fitness/-/N-4y1ay"),
    ("Clothing",           "https://www.target.com/c/clothing/-/N-5xtg6"),
    ("Shoes",              "https://www.target.com/c/shoes/-/N-55b13"),
    ("Toys",               "https://www.target.com/c/toys/-/N-5xt1b"),
    ("Baby",               "https://www.target.com/c/baby/-/N-5xtb1"),
    ("Home",               "https://www.target.com/c/home/-/N-5xtvd"),
    ("Bedding",            "https://www.target.com/c/bedding/-/N-5xtlf"),
    ("Kitchen",            "https://www.target.com/c/kitchen-dining/-/N-5xszo"),
    ("Tools",              "https://www.target.com/c/tools-hardware/-/N-5xtzz"),
    ("Outdoor",            "https://www.target.com/c/patio-garden/-/N-5xt76"),
    ("Auto",               "https://www.target.com/c/automotive/-/N-55b1s"),
    ("Health",             "https://www.target.com/c/health/-/N-55b1g"),
    ("Beauty",             "https://www.target.com/c/beauty/-/N-55b0z"),
    ("Luggage",            "https://www.target.com/c/luggage/-/N-5xtjs"),
]

BESTBUY_CATEGORIES = [
    ("TVs",           "https://www.bestbuy.com/site/searchpage.jsp?st=tv&sort=pricelow"),
    ("Laptops",       "https://www.bestbuy.com/site/searchpage.jsp?st=laptop&sort=pricelow"),
    ("Desktops",      "https://www.bestbuy.com/site/searchpage.jsp?st=desktop+computer&sort=pricelow"),
    ("Tablets",       "https://www.bestbuy.com/site/searchpage.jsp?st=tablet&sort=pricelow"),
    ("Cell Phones",   "https://www.bestbuy.com/site/searchpage.jsp?st=smartphone&sort=pricelow"),
    ("Appliances",    "https://www.bestbuy.com/site/searchpage.jsp?st=appliance&sort=pricelow"),
    ("Refrigerators", "https://www.bestbuy.com/site/searchpage.jsp?st=refrigerator&sort=pricelow"),
    ("Washers",       "https://www.bestbuy.com/site/searchpage.jsp?st=washer&sort=pricelow"),
    ("Video Games",   "https://www.bestbuy.com/site/searchpage.jsp?st=video+game&sort=pricelow"),
    ("Consoles",      "https://www.bestbuy.com/site/searchpage.jsp?st=gaming+console&sort=pricelow"),
    ("Headphones",    "https://www.bestbuy.com/site/searchpage.jsp?st=headphones&sort=pricelow"),
    ("Speakers",      "https://www.bestbuy.com/site/searchpage.jsp?st=speaker&sort=pricelow"),
    ("Camera",        "https://www.bestbuy.com/site/searchpage.jsp?st=camera&sort=pricelow"),
    ("Smart Home",    "https://www.bestbuy.com/site/searchpage.jsp?st=smart+home&sort=pricelow"),
    ("Wearables",     "https://www.bestbuy.com/site/searchpage.jsp?st=smartwatch&sort=pricelow"),
    ("Car Audio",     "https://www.bestbuy.com/site/searchpage.jsp?st=car+audio&sort=pricelow"),
    ("Monitors",      "https://www.bestbuy.com/site/searchpage.jsp?st=monitor&sort=pricelow"),
    ("Printers",      "https://www.bestbuy.com/site/searchpage.jsp?st=printer&sort=pricelow"),
]

HOMEDEPOT_CATEGORIES = [
    ("Tools",         "https://www.homedepot.com/s/tools?sortorder=asc&sortby=price"),
    ("Power Tools",   "https://www.homedepot.com/s/power+tools?sortorder=asc&sortby=price"),
    ("Hand Tools",    "https://www.homedepot.com/s/hand+tools?sortorder=asc&sortby=price"),
    ("Appliances",    "https://www.homedepot.com/s/appliances?sortorder=asc&sortby=price"),
    ("Refrigerators", "https://www.homedepot.com/s/refrigerator?sortorder=asc&sortby=price"),
    ("Washers",       "https://www.homedepot.com/s/washer?sortorder=asc&sortby=price"),
    ("Lawn Mowers",   "https://www.homedepot.com/s/lawn+mower?sortorder=asc&sortby=price"),
    ("Generators",    "https://www.homedepot.com/s/generator?sortorder=asc&sortby=price"),
    ("Patio",         "https://www.homedepot.com/s/patio+furniture?sortorder=asc&sortby=price"),
    ("Lighting",      "https://www.homedepot.com/s/lighting?sortorder=asc&sortby=price"),
    ("Storage",       "https://www.homedepot.com/s/storage?sortorder=asc&sortby=price"),
    ("Heating",       "https://www.homedepot.com/s/heater?sortorder=asc&sortby=price"),
    ("Pressure Wash", "https://www.homedepot.com/s/pressure+washer?sortorder=asc&sortby=price"),
    ("Chainsaws",     "https://www.homedepot.com/s/chainsaw?sortorder=asc&sortby=price"),
    ("Flooring",      "https://www.homedepot.com/s/flooring?sortorder=asc&sortby=price"),
]

NEWEGG_CATEGORIES = [
    ("Computer Parts",     "https://www.newegg.com/p/pl?N=100167523&Order=4"),
    ("CPUs",               "https://www.newegg.com/p/pl?N=100007671&Order=4"),
    ("GPUs",               "https://www.newegg.com/p/pl?N=100007709&Order=4"),
    ("Laptops",            "https://www.newegg.com/p/pl?N=100006740&Order=4"),
    ("Monitors",           "https://www.newegg.com/p/pl?N=100006652&Order=4"),
    ("SSDs",               "https://www.newegg.com/p/pl?N=100167523+601189910&Order=4"),
    ("RAM",                "https://www.newegg.com/p/pl?N=100007611&Order=4"),
    ("Motherboards",       "https://www.newegg.com/p/pl?N=100007627&Order=4"),
    ("Networking",         "https://www.newegg.com/p/pl?N=100007643&Order=4"),
    ("Storage",            "https://www.newegg.com/p/pl?N=100007974&Order=4"),
    ("Cases",              "https://www.newegg.com/p/pl?N=100007583&Order=4"),
    ("Power Supplies",     "https://www.newegg.com/p/pl?N=100007657&Order=4"),
    ("Cooling",            "https://www.newegg.com/p/pl?N=100007588&Order=4"),
    ("Headphones",         "https://www.newegg.com/p/pl?N=100009485&Order=4"),
    ("Keyboards",          "https://www.newegg.com/p/pl?N=100009931&Order=4"),
    ("Mice",               "https://www.newegg.com/p/pl?N=100010110&Order=4"),
    ("Speakers",           "https://www.newegg.com/p/pl?N=100009504&Order=4"),
    ("Desktops",           "https://www.newegg.com/p/pl?N=100006644&Order=4"),
    ("Printers",           "https://www.newegg.com/p/pl?N=100006745&Order=4"),
    ("Smart Home",         "https://www.newegg.com/p/pl?N=100020001&Order=4"),
]


# Harbor Freight category pages
HARBORFREIGHT_CATEGORIES = [
    ("Tools",         "https://www.harborfreight.com/power-tools.html"),
    ("Hand Tools",    "https://www.harborfreight.com/hand-tools.html"),
    ("Air Tools",     "https://www.harborfreight.com/air-tools-compressors.html"),
    ("Welding",       "https://www.harborfreight.com/welding.html"),
    ("Automotive",    "https://www.harborfreight.com/automotive.html"),
    ("Outdoor",       "https://www.harborfreight.com/outdoor-garden-farm.html"),
    ("Storage",       "https://www.harborfreight.com/material-handling-storage.html"),
    ("Generators",    "https://www.harborfreight.com/generators.html"),
]

# Big Lots category pages
BIGLOTS_CATEGORIES = [
    ("Furniture",     "https://www.biglots.com/furniture"),
    ("Mattresses",    "https://www.biglots.com/mattresses"),
    ("Home Decor",    "https://www.biglots.com/home-decor"),
    ("Outdoor",       "https://www.biglots.com/patio-garden"),
    ("Electronics",   "https://www.biglots.com/electronics"),
    ("Toys",          "https://www.biglots.com/toys"),
    ("Seasonal",      "https://www.biglots.com/seasonal"),
]

# Menards category pages
MENARDS_CATEGORIES = [
    ("Tools",         "https://www.menards.com/main/tools/c-1502.htm"),
    ("Appliances",    "https://www.menards.com/main/appliances/c-1510.htm"),
    ("Outdoor",       "https://www.menards.com/main/lawn-garden/c-1507.htm"),
    ("Generators",    "https://www.menards.com/main/lawn-garden/outdoor-power-equipment/generators/c-13253.htm"),
    ("Lighting",      "https://www.menards.com/main/lighting-ceiling-fans/c-1511.htm"),
    ("Storage",       "https://www.menards.com/main/storage-organization/c-1527.htm"),
]

# Overstock/Bed Bath Beyond category pages
OVERSTOCK_CATEGORIES = [
    ("Furniture",     "https://www.overstock.com/Home-Garden/Furniture/2/store.html?sort=Price"),
    ("Bedding",       "https://www.overstock.com/Bedding-Bath/Bedding/12321/store.html?sort=Price"),
    ("Rugs",          "https://www.overstock.com/Home-Garden/Rugs/2111/store.html?sort=Price"),
    ("Outdoor",       "https://www.overstock.com/Home-Garden/Patio-Furniture/Outdoor-Furniture/2624/store.html?sort=Price"),
    ("Kitchen",       "https://www.overstock.com/Home-Garden/Kitchen-Dining/2038/store.html?sort=Price"),
]

# Wayfair category pages
WAYFAIR_CATEGORIES = [
    ("Furniture",     "https://www.wayfair.com/furniture/cat/furniture-c45974.html?sortby=Price_Asc"),
    ("Mattresses",    "https://www.wayfair.com/bed-bath/sb1/mattresses-c1874774.html?sortby=Price_Asc"),
    ("Outdoor",       "https://www.wayfair.com/outdoor/cat/outdoor-furniture-c1870024.html?sortby=Price_Asc"),
    ("Lighting",      "https://www.wayfair.com/lighting/cat/lighting-c215606.html?sortby=Price_Asc"),
    ("Rugs",          "https://www.wayfair.com/rugs/cat/area-rugs-c1870020.html?sortby=Price_Asc"),
]

# B&H Photo
BH_CATEGORIES = [
    ("Cameras",       "https://www.bhphotovideo.com/c/browse/Cameras/ci/9811/N/4288586282?sort=priceUp"),
    ("Lenses",        "https://www.bhphotovideo.com/c/browse/Lenses/ci/977/N/4288586282?sort=priceUp"),
    ("Electronics",   "https://www.bhphotovideo.com/c/browse/Electronics/ci/6766/N/4288586282?sort=priceUp"),
    ("Computers",     "https://www.bhphotovideo.com/c/browse/Computers/ci/6780/N/4288586282?sort=priceUp"),
    ("Audio",         "https://www.bhphotovideo.com/c/browse/Audio/ci/9812/N/4288586282?sort=priceUp"),
    ("Drones",        "https://www.bhphotovideo.com/c/browse/Drones-Quadcopters/ci/27822?sort=priceUp"),
]

# Adorama
ADORAMA_CATEGORIES = [
    ("Cameras",       "https://www.adorama.com/cat/cameras?sortby=PriceLowToHigh"),
    ("Lenses",        "https://www.adorama.com/cat/lenses?sortby=PriceLowToHigh"),
    ("Electronics",   "https://www.adorama.com/cat/electronics?sortby=PriceLowToHigh"),
    ("Computers",     "https://www.adorama.com/cat/computers?sortby=PriceLowToHigh"),
    ("Audio",         "https://www.adorama.com/cat/audio?sortby=PriceLowToHigh"),
]

# Costco clearance
COSTCO_CATEGORIES = [
    ("Electronics",   "https://www.costco.com/electronics.html"),
    ("Appliances",    "https://www.costco.com/appliances.html"),
    ("Furniture",     "https://www.costco.com/furniture.html"),
    ("Outdoor",       "https://www.costco.com/patio-garden.html"),
    ("Tools",         "https://www.costco.com/tools-home-improvement.html"),
    ("Sports",        "https://www.costco.com/sporting-goods.html"),
    ("Clearance",     "https://www.costco.com/clearance.html"),
]

RSS_SOURCES = [
    # Major deal aggregators
    {"name": "Slickdeals",              "url": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1"},
    {"name": "Slickdeals Hot",          "url": "https://slickdeals.net/newsearch.php?mode=popdeals&searcharea=deals&searchin=first&rss=1"},
    {"name": "DealNews Electronics",    "url": "https://www.dealnews.com/c142/Electronics/?rss=1"},
    {"name": "DealNews Computers",      "url": "https://www.dealnews.com/c39/Computers/?rss=1"},
    {"name": "DealNews Home",           "url": "https://www.dealnews.com/c238/Home/?rss=1"},
    {"name": "DealNews Tools",          "url": "https://www.dealnews.com/c825/Tools-Garden/?rss=1"},
    {"name": "DealNews Sports",         "url": "https://www.dealnews.com/c304/Sports/?rss=1"},
    {"name": "DealNews Clothing",       "url": "https://www.dealnews.com/c60/Clothing/?rss=1"},
    {"name": "DealNews Automotive",     "url": "https://www.dealnews.com/c272/Automotive/?rss=1"},
    {"name": "Woot All",                "url": "https://www.woot.com/feeds/all"},
    {"name": "Woot Electronics",        "url": "https://electronics.woot.com/feeds/all"},
    {"name": "Woot Computers",          "url": "https://computers.woot.com/feeds/all"},
    {"name": "Woot Home",               "url": "https://home.woot.com/feeds/all"},
    {"name": "Woot Tools",              "url": "https://tools.woot.com/feeds/all"},
    {"name": "Woot Sports",             "url": "https://sport.woot.com/feeds/all"},
    {"name": "Techbargains",            "url": "https://www.techbargains.com/rss.cfm"},
    {"name": "Gottadeal",               "url": "https://www.gottadeal.com/feed"},
    {"name": "Brads Deals",             "url": "https://www.bradsdeals.com/feed"},
    {"name": "FatWallet",               "url": "https://www.fatwallet.com/rss/hot-deals.xml"},
    # Reddit deal communities
    {"name": "Reddit r/deals",                  "url": "https://www.reddit.com/r/deals/.rss"},
    {"name": "Reddit r/buildapcsales",           "url": "https://www.reddit.com/r/buildapcsales/.rss"},
    {"name": "Reddit r/GameDeals",               "url": "https://www.reddit.com/r/GameDeals/.rss"},
    {"name": "Reddit r/frugalmalefashion",       "url": "https://www.reddit.com/r/frugalmalefashion/.rss"},
    {"name": "Reddit r/glitch_in_the_matrix",    "url": "https://www.reddit.com/r/glitch_in_the_matrix/.rss"},
    {"name": "Reddit r/hotdeals",                "url": "https://www.reddit.com/r/hotdeals/.rss"},
    {"name": "Reddit r/priceglitches",           "url": "https://www.reddit.com/r/priceglitches/.rss"},
    {"name": "Reddit r/consoles",                "url": "https://www.reddit.com/r/consoles/.rss"},
    {"name": "Reddit r/hardwareswap",            "url": "https://www.reddit.com/r/hardwareswap/.rss"},
    {"name": "Reddit r/laptops",                 "url": "https://www.reddit.com/r/laptops/.rss"},
    {"name": "Reddit r/frugal",                  "url": "https://www.reddit.com/r/Frugal/.rss"},
    {"name": "Reddit r/flipping",                "url": "https://www.reddit.com/r/Flipping/.rss"},
    {"name": "Reddit r/thriftstore",             "url": "https://www.reddit.com/r/ThriftStoreHauls/.rss"},
    {"name": "Reddit r/amazondeals",             "url": "https://www.reddit.com/r/amazondeals/.rss"},
    {"name": "Reddit r/walmartdeals",            "url": "https://www.reddit.com/r/walmartdeals/.rss"},
    {"name": "Reddit r/targetdeals",             "url": "https://www.reddit.com/r/targetdeals/.rss"},
    {"name": "Reddit r/HomeImprovement",         "url": "https://www.reddit.com/r/HomeImprovement/.rss"},
    {"name": "Reddit r/tools",                   "url": "https://www.reddit.com/r/Tools/.rss"},
    {"name": "Reddit r/appliances",              "url": "https://www.reddit.com/r/Appliances/.rss"},
    {"name": "Reddit r/hometheater",             "url": "https://www.reddit.com/r/hometheater/.rss"},
    {"name": "Reddit r/audiophile",              "url": "https://www.reddit.com/r/audiophile/.rss"},
    {"name": "Reddit r/photography",             "url": "https://www.reddit.com/r/photography/.rss"},
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
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
    time.sleep(random.uniform(0.5, 1.2))

def make_session(base_url):
    session = requests.Session()
    session.headers.update(get_headers(base_url))
    try:
        session.get(base_url, timeout=8)
        polite_delay()
    except:
        pass
    return session

def proxy_get(url, timeout=15):
    proxy_url = CLOUDFLARE_PROXY + "?url=" + requests.utils.quote(url, safe="")
    return requests.get(proxy_url, timeout=timeout, headers={"User-Agent": random.choice(USER_AGENTS)})

def load_seen_deals():
    try:
        with open(SEEN_DEALS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen_deals(seen):
    os.makedirs("data", exist_ok=True)
    with open(SEEN_DEALS_FILE, "w") as f:
        json.dump(list(seen)[-2000:], f)

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
            if 10 <= v <= 99:
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
    if not discount or discount < HOT_MIN_DISCOUNT:
        return None
    if original and original < HOT_MIN_ORIGINAL:
        return None
    if sale and sale < MIN_SALE_PRICE.get(category, 3):
        return None
    is_glitch = bool(discount >= GLITCH_MIN_DISCOUNT and original and original >= GLITCH_MIN_ORIGINAL)
    is_hot = discount >= HOT_MIN_DISCOUNT and discount < MIN_DISCOUNT
    return {
        "title": title.strip()[:200],
        "url": url,
        "source": source,
        "discount": discount,
        "original": original,
        "sale": sale,
        "category": category,
        "glitch": is_glitch,
        "hot": is_hot,
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
            pm = re.search(r'(?:was|reg|retail|orig)[:\s]*\$?([\d,]+\.?\d*).*?(?:now|sale|for|only)[:\s]*\$?([\d,]+\.?\d*)', combined, re.IGNORECASE)
            if pm:
                original = parse_price(pm.group(1))
                sale = parse_price(pm.group(2))
            deal = build_deal(title, url, source["name"], original, sale, discount)
            if deal:
                deals.append(deal)
    except Exception as e:
        print("  RSS error (" + source["name"] + "): " + str(e))
    return deals

def scrape_amazon_category(name, url):
    deals = []
    try:
        session = make_session("https://www.amazon.com")
        polite_delay()
        for page in range(1, 3):
            page_url = url + "&page=" + str(page)
            r = session.get(page_url, timeout=20)
            if r.status_code != 200:
                print("  Amazon " + name + " blocked (" + str(r.status_code) + ")")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select('[data-component-type="s-search-result"]')
            print("  Amazon " + name + " pg" + str(page) + ": " + str(len(items)) + " items, status=" + str(r.status_code) + ", len=" + str(len(r.text)))
            if not items:
                break
            found = 0
            for item in items:
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
                        print("  Amazon " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                        deals.append(deal)
                        found += 1
                except:
                    continue
            if found == 0:
                break
            polite_delay()
    except Exception as e:
        print("  Amazon " + name + " error: " + str(e))
    return deals

def scrape_walmart_category(name, url):
    deals = []
    try:
        session = make_session("https://www.walmart.com")
        for pg in range(1, 3):
            page_url = url + "?sort=price_low&page=" + str(pg)
            r = session.get(page_url, timeout=20)
            if r.status_code != 200:
                print("  Walmart " + name + " blocked (" + str(r.status_code) + ")")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            script = soup.find("script", {"id": "__NEXT_DATA__"})
            script_found = "YES" if (script and script.string) else "NO"
            print("  Walmart " + name + " pg" + str(pg) + ": status=" + str(r.status_code) + " script=" + script_found + " len=" + str(len(r.text)))
            if not script or not script.string:
                break
            data = json.loads(script.string)
            try:
                stacks = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"]
                items = []
                for stack in stacks:
                    items.extend(stack.get("items", []))
            except (KeyError, TypeError):
                break
            for item in items[:40]:
                try:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("name", "")
                    price_info = item.get("priceInfo", {}) or {}
                    curr = price_info.get("currentPrice") or {}
                    was = price_info.get("wasPrice") or {}
                    sale = curr.get("price") or curr.get("priceString")
                    original = was.get("price") or was.get("priceString")
                    # also try top level price fields
                    if not sale:
                        sale = item.get("price") or item.get("salePrice")
                    if not original:
                        original = item.get("wasPrice") or item.get("listPrice")
                    # convert string prices
                    if isinstance(sale, str):
                        sale = parse_price(sale)
                    if isinstance(original, str):
                        original = parse_price(original)
                    canon = item.get("canonicalUrl", "")
                    link = "https://www.walmart.com" + canon if canon else "https://www.walmart.com"
                    discount = compute_discount(original, sale)
                    if title and (discount or 0) > 10:
                        print("  Walmart debug: " + title[:40] + " orig=" + str(original) + " sale=" + str(sale) + " disc=" + str(discount))
                    deal = build_deal(title, link, "Walmart", original, sale, discount)
                    if deal:
                        print("  Walmart " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                        deals.append(deal)
                except:
                    continue
            polite_delay()
    except Exception as e:
        print("  Walmart " + name + " error: " + str(e))
    return deals

def scrape_target_category(name, url):
    deals = []
    try:
        for pg in range(1, 3):
            page_url = url + "?sortBy=priceDesc&Nrpp=24&page=" + str(pg)
            r = proxy_get(page_url)
            if r.status_code != 200:
                print("  Target " + name + " blocked (" + str(r.status_code) + ")")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select("[data-test='product-details']")
            print("  Target " + name + " pg" + str(pg) + ": status=" + str(r.status_code) + " items=" + str(len(items)) + " len=" + str(len(r.text)))
            if not items:
                break
            for item in items:
                try:
                    title_el = item.select_one("a[data-test='product-title']")
                    sale_el = item.select_one("[data-test='current-price']")
                    was_el = item.select_one("[data-test='previous-price']")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    link = "https://www.target.com" + title_el.get("href", "")
                    sale = parse_price(sale_el.get_text() if sale_el else None)
                    original = parse_price(was_el.get_text() if was_el else None)
                    discount = compute_discount(original, sale)
                    deal = build_deal(title, link, "Target", original, sale, discount)
                    if deal:
                        print("  Target " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                        deals.append(deal)
                except:
                    continue
            polite_delay()
    except Exception as e:
        print("  Target " + name + " error: " + str(e))
    return deals

def scrape_bestbuy_category(name, url):
    deals = []
    try:
        for pg in range(1, 3):
            page_url = url + "?cp=" + str(pg)
            r = proxy_get(page_url)
            if r.status_code != 200:
                print("  Best Buy " + name + " blocked (" + str(r.status_code) + ")")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select(".sku-item")
            if not items:
                break
            for item in items:
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
                        print("  Best Buy " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                        deals.append(deal)
                except:
                    continue
            polite_delay()
    except Exception as e:
        print("  Best Buy " + name + " error: " + str(e))
    return deals

def scrape_homedepot_category(name, url):
    deals = []
    try:
        for pg in range(1, 3):
            sep = "&" if "?" in url else "?"
            page_url = url + sep + "Nao=" + str((pg - 1) * 24)
            r = proxy_get(page_url)
            if r.status_code != 200:
                print("  Home Depot " + name + " blocked (" + str(r.status_code) + ")")
                break
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
                        for prod in prods:
                            try:
                                title = prod.get("productLabel", "")
                                sale = prod.get("pricing", {}).get("value")
                                original = prod.get("pricing", {}).get("original")
                                item_id = prod.get("itemId", "")
                                link = "https://www.homedepot.com/p/" + item_id
                                discount = compute_discount(original, sale)
                                deal = build_deal(title, link, "Home Depot", original, sale, discount)
                                if deal:
                                    print("  Home Depot " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                                    deals.append(deal)
                            except:
                                continue
                    except:
                        pass
            polite_delay()
    except Exception as e:
        print("  Home Depot " + name + " error: " + str(e))
    return deals

def scrape_newegg_category(name, url):
    deals = []
    try:
        session = make_session("https://www.newegg.com")
        for pg in range(1, 3):
            page_url = url + "&page=" + str(pg)
            r = session.get(page_url, timeout=20)
            if r.status_code != 200:
                print("  Newegg " + name + " blocked (" + str(r.status_code) + ")")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select(".item-cell")
            if not items:
                break
            for item in items:
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
                        print("  Newegg " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                        deals.append(deal)
                except:
                    continue
            polite_delay()
    except Exception as e:
        print("  Newegg " + name + " error: " + str(e))
    return deals


def scrape_generic_category(name, url, source, title_sel, sale_sel, was_sel, link_sel, base_url="", use_proxy=False):
    deals = []
    try:
        for pg in range(1, 3):
            page_url = url if pg == 1 else url + ("&" if "?" in url else "?") + "page=" + str(pg)
            if use_proxy:
                r = proxy_get(page_url)
            else:
                session = make_session(base_url or url)
                r = session.get(page_url, timeout=20)
            if r.status_code != 200:
                print("  " + source + " " + name + " blocked (" + str(r.status_code) + ")")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select(title_sel)
            if not items:
                break
            for item in items[:30]:
                try:
                    title_el = item if item.name in ["a","h2","h3","h4"] else item.select_one("a, h2, h3, h4")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href","") if title_el.name == "a" else (item.select_one("a") or {}).get("href","")
                    link = (base_url + href) if href and not href.startswith("http") else href
                    sale_el = item.select_one(sale_sel) if sale_sel else None
                    was_el = item.select_one(was_sel) if was_sel else None
                    sale = parse_price(sale_el.get_text() if sale_el else None)
                    original = parse_price(was_el.get_text() if was_el else None)
                    discount = compute_discount(original, sale)
                    deal = build_deal(title, link, source, original, sale, discount)
                    if deal:
                        print("  " + source + " " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                        deals.append(deal)
                except:
                    continue
            polite_delay()
    except Exception as e:
        print("  " + source + " " + name + " error: " + str(e))
    return deals

def scrape_harborfreight_category(name, url):
    deals = []
    try:
        session = make_session("https://www.harborfreight.com")
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  Harbor Freight " + name + " blocked (" + str(r.status_code) + ")")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".product-tile, .grid-tile")
        for item in items[:30]:
            try:
                title_el = item.select_one(".product-title, .product-name, h3 a, h2 a")
                sale_el = item.select_one(".price-standard, .product-price .price")
                was_el = item.select_one(".price-original, .price-was, del")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href","") if title_el.name == "a" else (item.select_one("a") or {}).get("href","")
                link = "https://www.harborfreight.com" + href if href and not href.startswith("http") else href
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Harbor Freight", original, sale, discount)
                if deal:
                    print("  Harbor Freight " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Harbor Freight " + name + " error: " + str(e))
    return deals

def scrape_biglots_category(name, url):
    deals = []
    try:
        session = make_session("https://www.biglots.com")
        r = session.get(url + "?prefn1=isOnSale&prefv1=true&start=0&sz=48&srule=price-low-to-high", timeout=20)
        if r.status_code != 200:
            print("  Big Lots " + name + " blocked (" + str(r.status_code) + ")")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".product-tile, .product-grid-tile")
        for item in items[:30]:
            try:
                title_el = item.select_one(".product-name a, .tile-body a")
                sale_el = item.select_one(".sales .value, .price-sales")
                was_el = item.select_one(".strike-through .value, .price-standard")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href","")
                link = "https://www.biglots.com" + href if href and not href.startswith("http") else href
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Big Lots", original, sale, discount)
                if deal:
                    print("  Big Lots " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Big Lots " + name + " error: " + str(e))
    return deals

def scrape_menards_category(name, url):
    deals = []
    try:
        session = make_session("https://www.menards.com")
        r = session.get(url + "&sortByValue=price_asc", timeout=20)
        if r.status_code != 200:
            print("  Menards " + name + " blocked (" + str(r.status_code) + ")")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".product-card, [class*=product-listing]")
        for item in items[:30]:
            try:
                title_el = item.select_one("a[class*=title], .product-title a, h2 a, h3 a")
                sale_el = item.select_one("[class*=sale-price], [class*=current-price]")
                was_el = item.select_one("[class*=regular-price], [class*=was-price]")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href","")
                link = "https://www.menards.com" + href if href and not href.startswith("http") else href
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Menards", original, sale, discount)
                if deal:
                    print("  Menards " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Menards " + name + " error: " + str(e))
    return deals

def scrape_overstock_category(name, url):
    deals = []
    try:
        session = make_session("https://www.overstock.com")
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  Overstock " + name + " blocked (" + str(r.status_code) + ")")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".product-tile, [class*=ProductCard]")
        for item in items[:30]:
            try:
                title_el = item.select_one("a[class*=title], .product-title, h3 a, h2 a")
                sale_el = item.select_one("[class*=sale], [class*=current-price], .price")
                was_el = item.select_one("[class*=original], [class*=was], del, s")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href","")
                link = "https://www.overstock.com" + href if href and not href.startswith("http") else href
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Overstock", original, sale, discount)
                if deal:
                    print("  Overstock " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Overstock " + name + " error: " + str(e))
    return deals

def scrape_costco_category(name, url):
    deals = []
    try:
        session = make_session("https://www.costco.com")
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  Costco " + name + " blocked (" + str(r.status_code) + ")")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".product, [class*=product-tile]")
        for item in items[:30]:
            try:
                title_el = item.select_one("a.description, .description a, h3 a, h2 a")
                sale_el = item.select_one(".your-price .value, [class*=sale-price]")
                was_el = item.select_one(".before-price, [class*=was-price], del")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href","")
                link = "https://www.costco.com" + href if href and not href.startswith("http") else href
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Costco", original, sale, discount)
                if deal:
                    print("  Costco " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Costco " + name + " error: " + str(e))
    return deals

def scrape_bh_category(name, url):
    deals = []
    try:
        session = make_session("https://www.bhphotovideo.com")
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  B&H " + name + " blocked (" + str(r.status_code) + ")")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("[data-selenium=productItem], .product-item")
        for item in items[:30]:
            try:
                title_el = item.select_one("[data-selenium=productTitle] a, .product-title a")
                sale_el = item.select_one("[data-selenium=itemPrice], .price")
                was_el = item.select_one("[data-selenium=itemOriginalPrice], .original-price, del")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href","")
                link = "https://www.bhphotovideo.com" + href if href and not href.startswith("http") else href
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "B&H Photo", original, sale, discount)
                if deal:
                    print("  B&H " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  B&H " + name + " error: " + str(e))
    return deals


# Additional retailer categories
OVERSTOCK_CATEGORIES = [
    ("Furniture",      "https://www.overstock.com/Home-Garden/Furniture/241/cat.html?sort=PriceAsc"),
    ("Bedding",        "https://www.overstock.com/Home-Garden/Bedding-Bath/233/cat.html?sort=PriceAsc"),
    ("Rugs",           "https://www.overstock.com/Home-Garden/Rugs/1649/cat.html?sort=PriceAsc"),
    ("Lighting",       "https://www.overstock.com/Home-Garden/Lighting/1588/cat.html?sort=PriceAsc"),
    ("Jewelry",        "https://www.overstock.com/Jewelry-Watches/Jewelry/1117/cat.html?sort=PriceAsc"),
    ("Electronics",    "https://www.overstock.com/Electronics/2/cat.html?sort=PriceAsc"),
    ("Sports",         "https://www.overstock.com/Sports-Toys/Sports/340/cat.html?sort=PriceAsc"),
]

HARBORFREIGHT_CATEGORIES = [
    ("Tools",          "https://www.harborfreight.com/hand-tools.html"),
    ("Power Tools",    "https://www.harborfreight.com/power-tools.html"),
    ("Outdoor",        "https://www.harborfreight.com/outdoor-garden-farm.html"),
    ("Automotive",     "https://www.harborfreight.com/automotive.html"),
    ("Storage",        "https://www.harborfreight.com/storage-organization.html"),
    ("Welding",        "https://www.harborfreight.com/welding.html"),
    ("Generators",     "https://www.harborfreight.com/generators-engines-motors.html"),
]

BIGLOTS_CATEGORIES = [
    ("Furniture",      "https://www.biglots.com/furniture?pref_sortrule=lowPrice"),
    ("Electronics",    "https://www.biglots.com/electronics?pref_sortrule=lowPrice"),
    ("Home",           "https://www.biglots.com/home?pref_sortrule=lowPrice"),
    ("Outdoor",        "https://www.biglots.com/seasonal-outdoor?pref_sortrule=lowPrice"),
    ("Toys",           "https://www.biglots.com/toys?pref_sortrule=lowPrice"),
    ("Food",           "https://www.biglots.com/food-grocery?pref_sortrule=lowPrice"),
    ("Clothing",       "https://www.biglots.com/apparel?pref_sortrule=lowPrice"),
]

MENARDS_CATEGORIES = [
    ("Tools",          "https://www.menards.com/main/tools/c-10637.htm?sort=price&order=asc"),
    ("Appliances",     "https://www.menards.com/main/appliances/c-2706.htm?sort=price&order=asc"),
    ("Outdoor",        "https://www.menards.com/main/lawn-garden/c-2675.htm?sort=price&order=asc"),
    ("Building",       "https://www.menards.com/main/building-materials/c-2683.htm?sort=price&order=asc"),
    ("Lighting",       "https://www.menards.com/main/lighting-ceiling-fans/c-2686.htm?sort=price&order=asc"),
    ("Plumbing",       "https://www.menards.com/main/plumbing/c-2692.htm?sort=price&order=asc"),
    ("Heating",        "https://www.menards.com/main/heating-cooling/c-2697.htm?sort=price&order=asc"),
]

BH_CATEGORIES = [
    ("Cameras",        "https://www.bhphotovideo.com/c/browse/Cameras/ci/9811/N/4294967268?sort=PRICE_L"),
    ("Lenses",         "https://www.bhphotovideo.com/c/browse/Lenses/ci/9816/N/4294967268?sort=PRICE_L"),
    ("Lighting",       "https://www.bhphotovideo.com/c/browse/Lighting/ci/10045/N/4294967268?sort=PRICE_L"),
    ("Audio",          "https://www.bhphotovideo.com/c/browse/Audio/ci/9812/N/4294967268?sort=PRICE_L"),
    ("Computers",      "https://www.bhphotovideo.com/c/browse/Computers/ci/9826/N/4294967268?sort=PRICE_L"),
    ("Drones",         "https://www.bhphotovideo.com/c/browse/Drones-UAVs/ci/43581/N/4294967268?sort=PRICE_L"),
    ("Video",          "https://www.bhphotovideo.com/c/browse/Camcorders/ci/9814/N/4294967268?sort=PRICE_L"),
]

ADORAMA_CATEGORIES = [
    ("Cameras",        "https://www.adorama.com/cat/cameras?sortBy=PRICE_ASC"),
    ("Lenses",         "https://www.adorama.com/cat/lenses?sortBy=PRICE_ASC"),
    ("Computers",      "https://www.adorama.com/cat/computers?sortBy=PRICE_ASC"),
    ("Audio",          "https://www.adorama.com/cat/audio?sortBy=PRICE_ASC"),
    ("TV",             "https://www.adorama.com/cat/tv?sortBy=PRICE_ASC"),
    ("Drones",         "https://www.adorama.com/cat/drones?sortBy=PRICE_ASC"),
]

EBAY_CATEGORIES = [
    ("Electronics",    "https://www.ebay.com/b/Electronics/bn_7000259124?LH_Sale=1&_sop=15"),
    ("Computers",      "https://www.ebay.com/b/Computers-Tablets/bn_7000259102?LH_Sale=1&_sop=15"),
    ("Tools",          "https://www.ebay.com/b/Home-Garden/bn_7000259105?LH_Sale=1&_sop=15"),
    ("Clothing",       "https://www.ebay.com/b/Clothing-Shoes/bn_7000259093?LH_Sale=1&_sop=15"),
    ("Sporting",       "https://www.ebay.com/b/Sporting-Goods/bn_7000259120?LH_Sale=1&_sop=15"),
    ("Auto",           "https://www.ebay.com/b/eBay-Motors/bn_7000259088?LH_Sale=1&_sop=15"),
    ("Collectibles",   "https://www.ebay.com/b/Collectibles/bn_7000259096?LH_Sale=1&_sop=15"),
]

COSTCO_CATEGORIES = [
    ("Electronics",    "https://www.costco.com/electronics.html"),
    ("Appliances",     "https://www.costco.com/appliances.html"),
    ("Furniture",      "https://www.costco.com/furniture.html"),
    ("Tools",          "https://www.costco.com/tools-home-improvement.html"),
    ("Sports",         "https://www.costco.com/sporting-goods.html"),
    ("Outdoor",        "https://www.costco.com/patio-and-pool.html"),
    ("Jewelry",        "https://www.costco.com/jewelry.html"),
    ("Tires",          "https://www.costco.com/tires.html"),
]

def scrape_generic_category(name, url, source_name, proxy=False):
    deals = []
    try:
        for pg in range(1, 3):
            if proxy:
                r = proxy_get(url)
            else:
                session = make_session(url.split("/")[0] + "//" + url.split("/")[2])
                r = session.get(url, timeout=20)
            if r.status_code != 200:
                print("  " + source_name + " " + name + " blocked (" + str(r.status_code) + ")")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            found = 0
            # Generic price extraction - look for any element with price and original price
            # Try common price patterns across different sites
            for el in soup.select("[class*=price], [class*=Price], [class*=sale], [class*=Sale]")[:100]:
                try:
                    text = el.get_text(strip=True)
                    # Look for crossed out / original price nearby
                    parent = el.parent
                    if not parent:
                        continue
                    parent_text = parent.get_text(" ", strip=True)
                    # Find title - look for nearby heading or link
                    title_el = parent.find(["h2","h3","h4","a"], recursive=True)
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if len(title) < 5:
                        continue
                    link_el = parent.find("a", href=True)
                    link = link_el.get("href", "") if link_el else ""
                    if link and not link.startswith("http"):
                        base = url.split("/")[0] + "//" + url.split("/")[2]
                        link = base + link
                    discount = extract_discount(parent_text)
                    # Try to find prices
                    prices = re.findall(r'[\$]([\d,]+\.?\d*)', parent_text)
                    original, sale = None, None
                    if len(prices) >= 2:
                        p1 = parse_price(prices[0])
                        p2 = parse_price(prices[1])
                        if p1 and p2:
                            original = max(p1, p2)
                            sale = min(p1, p2)
                    elif len(prices) == 1:
                        sale = parse_price(prices[0])
                    deal = build_deal(title, link, source_name, original, sale, discount)
                    if deal:
                        print("  " + source_name + " " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                        deals.append(deal)
                        found += 1
                except:
                    continue
            if found == 0:
                break
            polite_delay()
    except Exception as e:
        print("  " + source_name + " " + name + " error: " + str(e))
    return deals

def scrape_ebay_category(name, url):
    deals = []
    try:
        session = make_session("https://www.ebay.com")
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  eBay " + name + " blocked (" + str(r.status_code) + ")")
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".s-item")
        for item in items[:30]:
            try:
                title_el = item.select_one(".s-item__title")
                sale_el = item.select_one(".s-item__price")
                was_el = item.select_one(".s-item__original-price")
                link_el = item.select_one(".s-item__link")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                if title == "Shop on eBay":
                    continue
                link = link_el.get("href", "")
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "eBay", original, sale, discount)
                if deal:
                    print("  eBay " + name + ": " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  eBay " + name + " error: " + str(e))
    return deals

def scrape_google_shopping(query):
    deals = []
    try:
        url = "https://shopping.google.com/search?q=" + requests.utils.quote(query) + "&tbs=p_ord:pd"
        session = make_session("https://shopping.google.com")
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("  Google Shopping blocked (" + str(r.status_code) + ") for: " + query)
            return deals
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".sh-dgr__grid-result, .i0X6df, .g-blk")
        for item in items[:20]:
            try:
                title_el = item.select_one("h3, .tAxDx, .sh-np__click-target")
                sale_el = item.select_one(".a8Pemb, .OFFNJ, [class*=price]")
                was_el = item.select_one(".e10twf, [class*=original]")
                link_el = item.select_one("a[href]")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link = link_el.get("href", "") if link_el else ""
                sale = parse_price(sale_el.get_text() if sale_el else None)
                original = parse_price(was_el.get_text() if was_el else None)
                discount = compute_discount(original, sale)
                deal = build_deal(title, link, "Google Shopping", original, sale, discount)
                if deal:
                    print("  Google Shopping: " + title[:50] + " - " + str(deal["discount"]) + "% off")
                    deals.append(deal)
            except:
                continue
    except Exception as e:
        print("  Google Shopping error for " + query + ": " + str(e))
    return deals

GOOGLE_SHOPPING_QUERIES = [
    "tv clearance sale", "laptop sale", "refrigerator clearance",
    "furniture sale", "tools clearance", "gaming console deal",
    "appliance sale", "mattress clearance", "headphones sale",
    "exercise equipment clearance", "outdoor furniture sale",
    "power tools sale", "camera clearance", "tablet deal",
]

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

RETAILER_SOURCES = {"Amazon", "Walmart", "Target", "Best Buy", "Home Depot", "Newegg"}

def is_expired(deal):
    try:
        age = (datetime.utcnow() - datetime.fromisoformat(deal["found_at"])).total_seconds() / 3600
        if deal.get("glitch"):
            return age > 2
        if deal.get("source") in RETAILER_SOURCES:
            return age > 24
        return age > 48
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
    combined = (new_deals + existing)[:500]
    os.makedirs("data", exist_ok=True)
    with open(log_file, "w") as f:
        json.dump(combined, f, indent=2)

def main():
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

    amazon_batch = AMAZON_CATEGORIES
    walmart_batch = WALMART_CATEGORIES
    target_batch = TARGET_CATEGORIES
    bestbuy_batch = BESTBUY_CATEGORIES
    homedepot_batch = HOMEDEPOT_CATEGORIES
    newegg_batch = NEWEGG_CATEGORIES

    harborfreight_batch = HARBORFREIGHT_CATEGORIES
    biglots_batch = BIGLOTS_CATEGORIES
    menards_batch = MENARDS_CATEGORIES
    overstock_batch = OVERSTOCK_CATEGORIES
    costco_batch = COSTCO_CATEGORIES
    bh_batch = BH_CATEGORIES

    batches = [
        ("Amazon",         amazon_batch,         scrape_amazon_category),
        ("Walmart",        walmart_batch,         scrape_walmart_category),
        ("Target",         target_batch,          scrape_target_category),
        ("Best Buy",       bestbuy_batch,         scrape_bestbuy_category),
        ("Home Depot",     homedepot_batch,       scrape_homedepot_category),
        ("Newegg",         newegg_batch,          scrape_newegg_category),
        ("Harbor Freight", harborfreight_batch,   scrape_harborfreight_category),
        ("Big Lots",       biglots_batch,         scrape_biglots_category),
        ("Menards",        menards_batch,         scrape_menards_category),
        ("Overstock",      overstock_batch,       scrape_overstock_category),
        ("Costco",         costco_batch,          scrape_costco_category),
        ("B&H Photo",      bh_batch,              scrape_bh_category),
    ]

    for retailer, batch, fn in batches:
        print("\nScraping " + retailer + "...")
        for name, url in batch:
            print("  Category: " + name)
            try:
                for deal in fn(name, url):
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

    # Google Shopping
    print("\nSearching Google Shopping...")
    gq_batch = random.sample(GOOGLE_SHOPPING_QUERIES, min(5, len(GOOGLE_SHOPPING_QUERIES)))
    for query in gq_batch:
        print("  Query: " + query)
        try:
            for deal in scrape_google_shopping(query):
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
