"""
Import Israeli agtech companies from israelagri.com and SNC Finder Wayback data.
Uses upsert (fill-gaps merge) to avoid overwriting existing data.
"""
import json
import re
from pathlib import Path

from src.db import Database
from src.dedup import to_slug
from src.models import Category, Company, Status

DB_PATH = Path(__file__).parent.parent.parent / "agtech_ca.db"
EXPORTS = Path(__file__).parent.parent.parent / "exports"

# Map israelagri categories to our Category enum
ISRAELAGRI_CAT_MAP = {
    "biological pest management": Category.AG_BIOCONTROL,
    "consulting": Category.UNKNOWN,
    "control and automation": Category.ROBOTICS,
    "cultivation": Category.PRECISION_AG,
    "distribution": Category.SUPPLY_CHAIN,
    "export": Category.SUPPLY_CHAIN,
    "farm management": Category.FARM_SOFTWARE,
    "fertilizers": Category.BIOTECH,
    "finance": Category.AG_FINTECH,
    "fresh produce": Category.SUPPLY_CHAIN,
    "greenhouses": Category.INDOOR_CEA,
    "growing technology": Category.PRECISION_AG,
    "indoor farming": Category.INDOOR_CEA,
    "livestock": Category.LIVESTOCK,
    "manufacturing": Category.UNKNOWN,
    "medical cannabis": Category.BIOTECH,
    "organic": Category.BIOTECH,
    "packaging": Category.SUPPLY_CHAIN,
    "post harvest technologies": Category.SUPPLY_CHAIN,
    "seeding": Category.BIOTECH,
    "seeds": Category.BIOTECH,
    "sorting": Category.ROBOTICS,
    "water management": Category.WATER_IRRIGATION,
}

# Map SNC tagline/description to our categories
SNC_CAT_KEYWORDS = {
    Category.PRECISION_AG: ['precision', 'sensor', 'drone', 'remote sensing', 'satellite', 'gps', 'mapping'],
    Category.FARM_SOFTWARE: ['farm management', 'agri software', 'farm data', 'agri platform'],
    Category.BIOTECH: ['biotech', 'genetic', 'seed', 'breed', 'plant science', 'microbial', 'biopesticide'],
    Category.ROBOTICS: ['robot', 'automat', 'harvest.*machine', 'mechanical', 'autonomous'],
    Category.SUPPLY_CHAIN: ['supply chain', 'logistics', 'cold chain', 'marketplace', 'trade', 'post.harvest'],
    Category.WATER_IRRIGATION: ['water', 'irrig', 'desalin', 'hydro'],
    Category.INDOOR_CEA: ['indoor', 'vertical farm', 'greenhouse', 'controlled environment', 'cea'],
    Category.AG_FINTECH: ['fintech', 'insurance', 'credit', 'financial'],
    Category.LIVESTOCK: ['livestock', 'dairy', 'cattle', 'poultry', 'animal', 'veterinar', 'aquaculture', 'fish'],
    Category.FOOD_SAFETY: ['food safety', 'traceab', 'contamina', 'pathogen'],
    Category.AG_BIOCONTROL: ['biocontrol', 'pest', 'biological control', 'insect management'],
    Category.CONNECTIVITY: ['iot', 'connect', 'network', 'telecom'],
}


def classify_from_text(text: str) -> Category:
    text_lower = text.lower()
    for cat, keywords in SNC_CAT_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text_lower):
                return cat
    return Category.UNKNOWN


def import_israelagri(db: Database):
    path = EXPORTS / "israelagri_companies.json"
    if not path.exists():
        print("No israelagri_companies.json found, skipping")
        return 0

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    added, updated, skipped = 0, 0, 0
    for item in data:
        name = item.get("name", "").strip()
        if not name:
            continue

        cat_name = (item.get("category") or "").lower()
        category = ISRAELAGRI_CAT_MAP.get(cat_name, Category.UNKNOWN)

        website = item.get("website") or None
        desc = item.get("full_description") or item.get("excerpt") or None

        company = Company(
            name=name,
            category=category,
            country="Israel",
            status=Status.ACTIVE,
            website=website,
            description=desc,
            sources=["israelagri"],
        )

        slug = to_slug(name)
        existing = db.get_company_by_slug(slug)
        if existing:
            updated += 1
        else:
            added += 1

        db.upsert_company(company)

    print(f"  israelagri: {added} new, {updated} merged, {len(data)} total")
    return added


def import_snc_wayback(db: Database):
    path = EXPORTS / "snc_finder_agrifood.json"
    if not path.exists():
        print("No snc_finder_agrifood.json found, skipping")
        return 0

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    if not data:
        print("  snc_wayback: empty file, skipping")
        return 0

    added, updated = 0, 0
    for item in data:
        name = item.get("name", "").strip()
        if not name:
            continue

        # Classify from tagline + description + about
        text = ' '.join(filter(None, [
            item.get('tagline', ''),
            item.get('description', ''),
            item.get('about', ''),
        ]))
        category = classify_from_text(text)

        website = item.get("website") or None
        desc = item.get("description") or item.get("about") or None
        founded = None
        if item.get("founded_year"):
            try:
                founded = int(item["founded_year"])
            except (ValueError, TypeError):
                pass

        employees = item.get("employees", "")

        company = Company(
            name=name,
            category=category,
            country="Israel",
            founded_year=founded,
            status=Status.ACTIVE,
            website=website,
            description=desc,
            sources=["snc_finder"],
        )

        slug = to_slug(name)
        existing = db.get_company_by_slug(slug)
        if existing:
            updated += 1
        else:
            added += 1

        db.upsert_company(company)

    print(f"  snc_wayback: {added} new, {updated} merged, {len(data)} total")
    return added


def main():
    db = Database(DB_PATH)
    before = db.count_companies()
    print(f"Database before: {before} companies")

    n1 = import_israelagri(db)
    n2 = import_snc_wayback(db)

    after = db.count_companies()
    print(f"\nDatabase after: {after} companies (+{after - before} new)")

    # Show Israel count
    row = db.conn.execute(
        "SELECT COUNT(*) FROM companies WHERE country = 'Israel'"
    ).fetchone()
    print(f"Israeli companies: {row[0]}")

    stats = db.stats()
    print(f"\nBy status: {stats['by_status']}")
    print(f"By category (top 5): {dict(list(stats['by_category'].items())[:5])}")

    db.close()


if __name__ == "__main__":
    main()
