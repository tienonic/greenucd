"""
AgTech CA Scraper — Standalone Colab/Cloud Script
=================================================
Self-contained script that runs all API-based scrapers (no browser needed).
Outputs a SQLite database file you can download.

Usage in Google Colab:
  1. Upload this file or paste into a cell
  2. Run it
  3. Download the resulting agtech_ca.db

Usage locally:
  python colab_scraper.py
"""

import csv
import io
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Try importing requests, fall back to urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    log.info("requests not installed, using urllib (pip install requests for better experience)")


# ============================================================
# Models
# ============================================================

class Category(str, Enum):
    PRECISION_AG = "PRECISION_AG"
    FARM_SOFTWARE = "FARM_SOFTWARE"
    BIOTECH = "BIOTECH"
    ROBOTICS = "ROBOTICS"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    WATER_IRRIGATION = "WATER_IRRIGATION"
    INDOOR_CEA = "INDOOR_CEA"
    AG_FINTECH = "AG_FINTECH"
    LIVESTOCK = "LIVESTOCK"
    FOOD_SAFETY = "FOOD_SAFETY"
    AG_BIOCONTROL = "AG_BIOCONTROL"
    CONNECTIVITY = "CONNECTIVITY"
    UNKNOWN = "UNKNOWN"


CATEGORY_KEYWORDS = {
    Category.PRECISION_AG: ["precision agriculture", "precision ag", "drone", "uav", "satellite imagery", "remote sensing", "sensor", "crop monitoring", "ndvi", "gps guidance", "soil mapping", "geospatial", "aerial imaging"],
    Category.FARM_SOFTWARE: ["farm management", "farm software", "farm erp", "farm analytics", "agri marketplace", "crop planning", "agriculture saas"],
    Category.BIOTECH: ["gene editing", "crispr", "biologicals", "biostimulant", "crop science", "seed trait", "plant breeding", "genomics", "microbiome", "nitrogen fixation", "synthetic biology"],
    Category.ROBOTICS: ["robot", "autonomous", "harvesting robot", "weeding robot", "agricultural automation", "farm automation", "robotic", "machine vision", "automated harvest"],
    Category.SUPPLY_CHAIN: ["supply chain", "traceability", "cold chain", "post-harvest", "food logistics", "grain storage"],
    Category.WATER_IRRIGATION: ["irrigation", "water management", "water conservation", "drip irrigation", "smart irrigation", "soil moisture"],
    Category.INDOOR_CEA: ["indoor farming", "vertical farming", "controlled environment", "greenhouse technology", "hydroponics", "aeroponics"],
    Category.AG_FINTECH: ["crop insurance", "farm lending", "farm finance", "agricultural finance", "ag fintech", "trade finance"],
    Category.LIVESTOCK: ["livestock", "dairy", "cattle", "poultry", "animal health", "feed optimization", "animal monitoring", "herd management", "aquaculture"],
    Category.FOOD_SAFETY: ["food safety", "pathogen detection", "food testing", "quality assurance", "foodborne"],
    Category.AG_BIOCONTROL: ["pest management", "biocontrol", "bio-pesticide", "biopesticide", "integrated pest", "ipm", "biological control", "crop protection", "pheromone"],
    Category.CONNECTIVITY: ["rural broadband", "farm connectivity", "agricultural iot", "agricultural connectivity"],
}


def classify(text):
    if not text:
        return Category.UNKNOWN
    scores = {}
    lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[cat] = score
    return max(scores, key=scores.get) if scores else Category.UNKNOWN


TAG_MAP = {
    "robotics": Category.ROBOTICS, "autonomous vehicles": Category.ROBOTICS,
    "drone": Category.PRECISION_AG, "drones": Category.PRECISION_AG,
    "sensor": Category.PRECISION_AG, "sensors": Category.PRECISION_AG,
    "iot": Category.PRECISION_AG, "hardware": Category.PRECISION_AG,
    "software": Category.FARM_SOFTWARE, "saas": Category.FARM_SOFTWARE,
    "b2b software": Category.FARM_SOFTWARE, "analytics": Category.FARM_SOFTWARE,
    "data": Category.FARM_SOFTWARE, "artificial intelligence": Category.FARM_SOFTWARE,
    "machine learning": Category.FARM_SOFTWARE,
    "biotech": Category.BIOTECH, "biotechnology": Category.BIOTECH, "genomics": Category.BIOTECH,
    "supply chain": Category.SUPPLY_CHAIN, "logistics": Category.SUPPLY_CHAIN,
    "e-commerce": Category.SUPPLY_CHAIN, "marketplace": Category.SUPPLY_CHAIN,
    "water": Category.WATER_IRRIGATION, "irrigation": Category.WATER_IRRIGATION,
    "hydroponics": Category.INDOOR_CEA, "vertical farming": Category.INDOOR_CEA,
    "fintech": Category.AG_FINTECH, "finance": Category.AG_FINTECH, "insurance": Category.AG_FINTECH,
    "livestock": Category.LIVESTOCK, "animal": Category.LIVESTOCK, "aquaculture": Category.LIVESTOCK,
    "food safety": Category.FOOD_SAFETY,
}
TAG_PRIORITY = {
    Category.ROBOTICS: 10, Category.BIOTECH: 9, Category.INDOOR_CEA: 9,
    Category.LIVESTOCK: 8, Category.AG_BIOCONTROL: 8, Category.FOOD_SAFETY: 8,
    Category.WATER_IRRIGATION: 7, Category.AG_FINTECH: 7, Category.SUPPLY_CHAIN: 6,
    Category.PRECISION_AG: 5, Category.FARM_SOFTWARE: 4,
}


def classify_tags(tag_string):
    if not tag_string:
        return Category.UNKNOWN
    tags = [t.strip().lower() for t in tag_string.split(",")]
    scores = {}
    for tag in tags:
        if tag in TAG_MAP:
            cat = TAG_MAP[tag]
            scores[cat] = scores.get(cat, 0) + TAG_PRIORITY.get(cat, 1)
    return max(scores, key=scores.get) if scores else Category.UNKNOWN


# ============================================================
# Dedup
# ============================================================

STRIP_SUFFIXES = re.compile(
    r",?\s*\b(inc\.?|llc\.?|corp\.?|corporation|ltd\.?|limited|co\.?|"
    r"company|incorporated|lp\.?|plc\.?|gmbh|s\.?a\.?|"
    r"technologies|technology|tech|labs?|systems?|solutions?|"
    r"ventures?|group|holdings?|enterprises?)\b\.?", re.IGNORECASE)

def normalize_name(name):
    result = STRIP_SUFFIXES.sub("", name)
    result = re.sub(r"[^a-z0-9\s]", "", result.lower())
    return re.sub(r"\s+", " ", result).strip()

def to_slug(name):
    return re.sub(r"\s+", "-", normalize_name(name))

def sanitize(val):
    if val is None:
        return None
    return val.replace("\x00", "").replace("\r", "").strip()


# ============================================================
# HTTP helpers
# ============================================================

def http_get(url, headers=None, timeout=30):
    h = {"User-Agent": "AgTechCAScraper/0.1 (research)"}
    if headers:
        h.update(headers)
    if HAS_REQUESTS:
        resp = requests.get(url, headers=h, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    else:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")


def http_post_json(url, payload, timeout=30):
    h = {"User-Agent": "AgTechCAScraper/0.1 (research)", "Content-Type": "application/json"}
    if HAS_REQUESTS:
        resp = requests.post(url, json=payload, headers=h, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


def http_get_stream(url, timeout=300):
    """Stream a large file download, return the full text."""
    if HAS_REQUESTS:
        resp = requests.get(url, stream=True, timeout=timeout,
                            headers={"User-Agent": "AgTechCAScraper/0.1"})
        resp.raise_for_status()
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=1024*1024, decode_unicode=True):
            if chunk:
                chunks.append(chunk)
                total += len(chunk)
                if total % (10*1024*1024) < 1024*1024:
                    log.info(f"  Downloaded {total//(1024*1024)}MB...")
        return "".join(chunks)
    else:
        return http_get(url, timeout=timeout)


# ============================================================
# Database
# ============================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE,
    category TEXT DEFAULT 'UNKNOWN', hq_city TEXT, hq_state TEXT,
    state_of_incorporation TEXT, country TEXT DEFAULT 'US',
    founded_year INTEGER, status TEXT DEFAULT 'UNKNOWN',
    website TEXT, website_live BOOLEAN, last_verified_date TEXT,
    description TEXT, source TEXT NOT NULL,
    crunchbase_url TEXT, linkedin_url TEXT
);
CREATE TABLE IF NOT EXISTS funding_rounds (
    id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id),
    round_type TEXT, amount_usd REAL, date TEXT, investors TEXT, source TEXT
);
CREATE TABLE IF NOT EXISTS grants (
    id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id),
    agency TEXT, program TEXT, title TEXT, amount_usd REAL,
    award_date TEXT, end_date TEXT, abstract TEXT, source TEXT
);
"""


class DB:
    def __init__(self, path="agtech_ca.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert(self, name, category="UNKNOWN", hq_city=None, hq_state=None,
               country="US", website=None, description=None, source=""):
        slug = to_slug(name)
        existing = self.conn.execute("SELECT id, source FROM companies WHERE slug=?", (slug,)).fetchone()
        if existing:
            sources = set(existing["source"].split("|"))
            sources.add(source)
            self.conn.execute(
                """UPDATE companies SET
                   category=CASE WHEN ?!='UNKNOWN' THEN ? ELSE category END,
                   hq_city=COALESCE(?,hq_city), hq_state=COALESCE(?,hq_state),
                   website=COALESCE(?,website), description=COALESCE(?,description),
                   source=? WHERE slug=?""",
                (category, category, sanitize(hq_city), sanitize(hq_state),
                 sanitize(website), sanitize(description),
                 "|".join(sorted(sources)), slug))
            self.conn.commit()
            return existing["id"]
        else:
            cur = self.conn.execute(
                """INSERT INTO companies (name,slug,category,hq_city,hq_state,country,
                   website,description,source,status)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (sanitize(name), slug, category, sanitize(hq_city), sanitize(hq_state),
                 sanitize(country), sanitize(website), sanitize(description), source, "UNKNOWN"))
            self.conn.commit()
            return cur.lastrowid

    def add_grant(self, company_id, agency, program, title, amount, award_date, source):
        self.conn.execute(
            "INSERT INTO grants (company_id,agency,program,title,amount_usd,award_date,source) VALUES (?,?,?,?,?,?,?)",
            (company_id, agency, program, sanitize(title), amount, award_date, source))
        self.conn.commit()

    def add_funding(self, company_id, round_type, amount, date, source):
        self.conn.execute(
            "INSERT INTO funding_rounds (company_id,round_type,amount_usd,date,source) VALUES (?,?,?,?,?)",
            (company_id, round_type, amount, date, source))
        self.conn.commit()

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]

    def stats(self):
        total = self.count()
        cats = dict(self.conn.execute("SELECT category,COUNT(*) FROM companies GROUP BY category ORDER BY COUNT(*) DESC").fetchall())
        return total, cats


# ============================================================
# Scrapers
# ============================================================

GOV_WORDS = ["university", "college", "regents", "board of trustees", "department of",
             "community college", "school district", "experiment station", "polytechnic",
             "extension service", "county of", "state of", "agricultural research service"]

AG_KEYWORDS = ["agriculture", "crop", "farm", "irrigation", "livestock", "plant science",
               "soil", "food safety", "pest", "harvest", "seed", "horticulture", "dairy",
               "forestry", "aquaculture", "pollinator", "weed", "fertilizer", "grain",
               "vineyard", "orchard", "agtech", "precision ag"]


def is_gov(name):
    lower = name.lower()
    return any(w in lower for w in GOV_WORDS)


def scrape_usaspending(db):
    """USASpending.gov — USDA grants to CA companies."""
    log.info("=== USASpending.gov ===")
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    keyword_batches = [
        ["agriculture technology", "agtech", "precision agriculture"],
        ["crop sensor", "farm management software", "agricultural robotics"],
        ["irrigation technology", "food safety technology", "livestock technology"],
        ["plant science", "biological control", "soil sensor"],
        ["harvest automation", "drone agriculture", "vertical farming"],
        ["crop protection", "seed technology", "agricultural drone"],
        ["farm automation", "smart irrigation", "controlled environment agriculture"],
    ]
    seen = set()
    count = 0
    for batch in keyword_batches:
        payload = {
            "filters": {
                "agencies": [{"type": "awarding", "tier": "toptier", "name": "Department of Agriculture"}],
                "place_of_performance_locations": [{"country": "USA", "state": "CA"}],
                "award_type_codes": ["02", "03", "04", "05"],
                "time_period": [{"start_date": "2022-01-01", "end_date": "2026-12-31"}],
                "keywords": batch,
            },
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Sub Agency",
                        "Start Date", "End Date", "Description", "Place of Performance City Name"],
            "limit": 100, "page": 1, "sort": "Award Amount", "order": "desc",
        }
        try:
            data = http_post_json(url, payload, timeout=30)
        except Exception as e:
            log.warning(f"  Batch {batch[0]}: {e}")
            continue
        for r in data.get("results", []):
            aid = r.get("Award ID", "")
            if aid in seen:
                continue
            seen.add(aid)
            name = r.get("Recipient Name", "").strip()
            if not name or is_gov(name):
                continue
            desc = r.get("Description", "") or ""
            cat = classify(desc)
            cid = db.upsert(name, cat.value, hq_city=r.get("Place of Performance City Name"),
                            hq_state="CA", description=desc[:500], source="usaspending")
            amt = r.get("Award Amount")
            if amt:
                db.add_grant(cid, "USDA", r.get("Awarding Sub Agency"), desc[:200],
                             amt, r.get("Start Date"), "usaspending")
            count += 1
    log.info(f"  USASpending: {count} records processed")


def scrape_sbir_bulk(db):
    """SBIR bulk CSV — 65MB download, filter to CA ag companies."""
    log.info("=== SBIR Bulk CSV (this may take a few minutes) ===")
    url = "https://data.www.sbir.gov/awarddatapublic/award_data_no_abstract.csv"

    cache = Path("sbir_ca_cache.csv")
    if cache.exists():
        log.info("  Using cached SBIR CA data")
        with open(cache, encoding="utf-8", errors="replace") as f:
            ca_rows = list(csv.DictReader(f))
    else:
        try:
            log.info("  Downloading 65MB CSV...")
            text = http_get_stream(url, timeout=600)
            log.info(f"  Downloaded {len(text)//(1024*1024)}MB, filtering CA rows...")
        except Exception as e:
            log.error(f"  SBIR download failed: {e}")
            return

        reader = csv.DictReader(io.StringIO(text))
        ca_rows = [r for r in reader if (r.get("State", "").strip().upper() in ("CA", "CALIFORNIA"))]

        if ca_rows:
            with open(cache, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=ca_rows[0].keys())
                w.writeheader()
                w.writerows(ca_rows)
            log.info(f"  Cached {len(ca_rows)} CA rows")

    count = 0
    for row in ca_rows:
        firm = row.get("Company", "").strip()
        if not firm:
            continue
        agency = row.get("Agency", "")
        title = row.get("Award Title", "") or ""
        try:
            year = int(row.get("Award Year", "0") or row.get("Year", "0"))
        except ValueError:
            year = 0
        if year < 2022:
            continue

        if agency != "USDA":
            combined = f"{title} {firm}".lower()
            if not any(kw in combined for kw in AG_KEYWORDS):
                continue

        cat = classify(title)
        amt_str = (row.get("Award Amount", "") or "").replace(",", "").replace("$", "")
        try:
            amt = float(amt_str) if amt_str else None
        except ValueError:
            amt = None

        cid = db.upsert(firm, cat.value, hq_city=row.get("City"),
                         hq_state=row.get("State"), website=row.get("Company Website"),
                         description=title[:500], source="sbir_bulk")
        if amt:
            db.add_grant(cid, agency, f"SBIR {row.get('Phase', '')}".strip(),
                         title[:200], amt, row.get("Award Start Date") or row.get("Proposal Award Date"),
                         "sbir_bulk")
        count += 1

    log.info(f"  SBIR Bulk: {count} CA ag records (2022+)")


def scrape_nifa(db):
    """NIFA paginated JSON — 2,821 CA records."""
    log.info("=== NIFA Paginated JSON ===")
    base = "https://portal.nifa.usda.gov/lmd4/recent_awards/get_data.js"
    filters = json.dumps({"State Name": "CALIFORNIA"})
    encoded = urllib.parse.quote(filters)

    count = 0
    for page in range(1, 100):
        url = f"{base}?page={page}&columnFilters={encoded}"
        try:
            text = http_get(url, timeout=30)
            data = json.loads(text)
        except Exception as e:
            log.warning(f"  NIFA page {page}: {e}")
            break

        rows = data if isinstance(data, list) else data.get("data", [])
        if not rows:
            break

        for row in rows:
            if isinstance(row, dict):
                grantee = row.get("Grantee Name", "").strip()
                title = row.get("Grant Title", "").strip()
                program = row.get("Program Name", "") or ""
                amt_str = str(row.get("Award Dollars", "")).replace(",", "").replace("$", "").strip()
                award_date = row.get("Award Date", "")
            elif isinstance(row, list) and len(row) >= 6:
                grantee = row[5] if len(row) > 5 else ""
                title = row[3] if len(row) > 3 else ""
                amt_str = str(row[6]).replace(",", "").replace("$", "").strip() if len(row) > 6 else ""
                program = row[7] if len(row) > 7 else ""
                award_date = row[0] if len(row) > 0 else ""
            else:
                continue

            if not grantee or is_gov(grantee):
                continue

            cat = classify(f"{title} {program}")
            try:
                amt = float(amt_str) if amt_str else None
            except ValueError:
                amt = None

            cid = db.upsert(grantee, cat.value, hq_state="CA",
                            description=title[:500], source="nifa")
            if amt:
                db.add_grant(cid, "USDA", f"NIFA {program}".strip(),
                             title[:200], amt, award_date, "nifa")
            count += 1

        if len(rows) < 30:
            break
        if page % 10 == 0:
            log.info(f"  NIFA page {page}...")

    log.info(f"  NIFA: {count} private CA records")


def scrape_sec_edgar(db):
    """SEC EDGAR Form D filings with ag keywords."""
    log.info("=== SEC EDGAR Form D ===")
    base = "https://efts.sec.gov/LATEST/search-index"
    terms = ['"agtech"', '"precision agriculture"', '"agriculture technology"',
             '"agricultural robotics"', '"vertical farming"', '"crop technology"']
    headers = {"User-Agent": "AgTechCAScraper/0.1 (agtech-research@example.com)",
               "Accept": "application/json"}

    count = 0
    for term in terms:
        params = f"?q={urllib.parse.quote(term)}&forms=D&dateRange=custom&startdt=2022-01-01&enddt=2026-12-31"
        try:
            text = http_get(base + params, headers=headers, timeout=15)
            data = json.loads(text)
        except Exception as e:
            log.debug(f"  EDGAR {term}: {e}")
            continue

        hits = data.get("hits", {}).get("hits", [])
        for hit in hits:
            src = hit.get("_source", {})
            name = src.get("entity_name", "").strip()
            if not name:
                names = src.get("display_names", [])
                name = names[0] if names else ""
            if not name:
                continue

            cat = classify(term)
            db.upsert(name, cat.value, state_of_incorporation=src.get("state_of_inc"),
                       description=f"SEC Form D: {term}", source="sec_edgar")
            count += 1
        time.sleep(2)

    log.info(f"  SEC EDGAR: {count} filings")


def scrape_world_agritech(db):
    """World Agri-Tech Summit — JSON-LD from startups page."""
    log.info("=== World Agri-Tech Summit ===")
    try:
        html = http_get("https://worldagritechusa.com/start-ups", timeout=30)
    except Exception as e:
        log.warning(f"  World Agri-Tech: {e}")
        return

    count = 0
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "Organization":
            name = data.get("name", "").strip()
            if not name:
                continue
            url = data.get("url", "")
            desc = data.get("description", "")
            cat = classify(f"{name} {desc}")
            db.upsert(name, cat.value, website=url, description=desc[:500], source="world_agritech")
            count += 1

    log.info(f"  World Agri-Tech: {count} companies")


def scrape_growthlist(db):
    """GrowthList free 100 — HTML table with funding data."""
    log.info("=== GrowthList (free 100) ===")
    try:
        html = http_get("https://growthlist.co/agriculture-startups/", timeout=30)
    except Exception as e:
        log.warning(f"  GrowthList: {e}")
        return

    # Find the footable
    table_match = re.search(r'<table[^>]*id="[^"]*footable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table_match:
        log.warning("  GrowthList: table not found")
        return

    rows = re.findall(r'<tr>(.*?)</tr>', table_match.group(1), re.DOTALL)
    count = 0
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 5:
            continue
        name = re.sub(r'<[^>]+>', '', cells[0]).strip()
        website = re.sub(r'<[^>]+>', '', cells[1]).strip() if len(cells) > 1 else ""
        industry = re.sub(r'<[^>]+>', '', cells[2]).strip() if len(cells) > 2 else ""
        country = re.sub(r'<[^>]+>', '', cells[3]).strip() if len(cells) > 3 else ""
        funding_str = re.sub(r'<[^>]+>', '', cells[4]).strip() if len(cells) > 4 else ""
        round_type = re.sub(r'<[^>]+>', '', cells[5]).strip() if len(cells) > 5 else ""
        fund_date = re.sub(r'<[^>]+>', '', cells[6]).strip() if len(cells) > 6 else ""

        if not name:
            continue

        cat = classify_tags(industry)
        if cat == Category.UNKNOWN:
            cat = classify(industry)

        ws = f"https://{website}" if website and not website.startswith("http") else website
        cid = db.upsert(name, cat.value, country=country or "US",
                         website=ws, description=industry, source="growthlist")

        # Parse funding
        cleaned = funding_str.replace("$", "").replace(",", "").strip()
        try:
            amt = float(cleaned) if cleaned else None
        except ValueError:
            amt = None
        if amt:
            db.add_funding(cid, round_type, amt, fund_date, "growthlist")

        count += 1

    log.info(f"  GrowthList: {count} companies")


# ============================================================
# Main
# ============================================================

def main():
    db_path = "agtech_ca.db"
    log.info(f"Output: {db_path}")
    db = DB(db_path)

    initial = db.count()
    log.info(f"Starting with {initial} companies in database\n")

    scrapers = [
        ("USASpending", scrape_usaspending),
        ("GrowthList", scrape_growthlist),
        ("World Agri-Tech", scrape_world_agritech),
        ("SEC EDGAR", scrape_sec_edgar),
        ("NIFA", scrape_nifa),
        ("SBIR Bulk", scrape_sbir_bulk),
    ]

    for name, func in scrapers:
        try:
            func(db)
        except Exception as e:
            log.error(f"{name} FAILED: {e}")
            log.info("Continuing with next scraper...\n")
        print()

    final = db.count()
    total, cats = db.stats()
    grants = db.conn.execute("SELECT COUNT(*) FROM grants").fetchone()[0]
    funding = db.conn.execute("SELECT COUNT(*) FROM funding_rounds").fetchone()[0]

    print("\n" + "="*50)
    print(f"DONE — {final} companies ({final - initial} new)")
    print(f"Grants: {grants} | Funding rounds: {funding}")
    print(f"\nBy category:")
    for cat, cnt in cats.items():
        print(f"  {cat:20s} {cnt}")
    print(f"\nDatabase saved to: {os.path.abspath(db_path)}")
    print("="*50)

    # Colab: auto-download
    try:
        from google.colab import files
        files.download(db_path)
        log.info("Download triggered in Colab!")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
