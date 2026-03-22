"""Classify companies by parsing comma-separated industry tags (GrowthList style)."""

from __future__ import annotations

import logging

from src.db import Database
from src.models import Category

logger = logging.getLogger(__name__)

TAG_TO_CATEGORY: dict[str, Category] = {
    "robotics": Category.ROBOTICS,
    "autonomous vehicles": Category.ROBOTICS,
    "automation": Category.ROBOTICS,
    "drone": Category.PRECISION_AG,
    "drones": Category.PRECISION_AG,
    "uav": Category.PRECISION_AG,
    "gps": Category.PRECISION_AG,
    "geospatial": Category.PRECISION_AG,
    "remote sensing": Category.PRECISION_AG,
    "satellite": Category.PRECISION_AG,
    "sensor": Category.PRECISION_AG,
    "sensors": Category.PRECISION_AG,
    "iot": Category.PRECISION_AG,
    "software": Category.FARM_SOFTWARE,
    "saas": Category.FARM_SOFTWARE,
    "b2b software": Category.FARM_SOFTWARE,
    "analytics": Category.FARM_SOFTWARE,
    "data": Category.FARM_SOFTWARE,
    "cloud computing": Category.FARM_SOFTWARE,
    "machine learning": Category.FARM_SOFTWARE,
    "artificial intelligence": Category.FARM_SOFTWARE,
    "ai": Category.FARM_SOFTWARE,
    "biotech": Category.BIOTECH,
    "biotechnology": Category.BIOTECH,
    "biology": Category.BIOTECH,
    "genomics": Category.BIOTECH,
    "genetics": Category.BIOTECH,
    "molecular": Category.BIOTECH,
    "life science": Category.BIOTECH,
    "supply chain": Category.SUPPLY_CHAIN,
    "logistics": Category.SUPPLY_CHAIN,
    "e-commerce": Category.SUPPLY_CHAIN,
    "marketplace": Category.SUPPLY_CHAIN,
    "trading platform": Category.SUPPLY_CHAIN,
    "water": Category.WATER_IRRIGATION,
    "irrigation": Category.WATER_IRRIGATION,
    "hydroponics": Category.INDOOR_CEA,
    "vertical farming": Category.INDOOR_CEA,
    "indoor farming": Category.INDOOR_CEA,
    "controlled environment": Category.INDOOR_CEA,
    "greenhouse": Category.INDOOR_CEA,
    "fintech": Category.AG_FINTECH,
    "finance": Category.AG_FINTECH,
    "insurance": Category.AG_FINTECH,
    "lending": Category.AG_FINTECH,
    "livestock": Category.LIVESTOCK,
    "animal": Category.LIVESTOCK,
    "aquaculture": Category.LIVESTOCK,
    "dairy": Category.LIVESTOCK,
    "poultry": Category.LIVESTOCK,
    "food safety": Category.FOOD_SAFETY,
    "food processing": Category.FOOD_SAFETY,
    "pest": Category.AG_BIOCONTROL,
    "crop protection": Category.AG_BIOCONTROL,
    "connectivity": Category.CONNECTIVITY,
    "telecom": Category.CONNECTIVITY,
    "hardware": Category.PRECISION_AG,
    "environment": Category.PRECISION_AG,
}

# Priority tiers — more specific tags should override generic ones
PRIORITY = {
    Category.ROBOTICS: 10,
    Category.BIOTECH: 9,
    Category.INDOOR_CEA: 9,
    Category.LIVESTOCK: 8,
    Category.AG_BIOCONTROL: 8,
    Category.FOOD_SAFETY: 8,
    Category.WATER_IRRIGATION: 7,
    Category.AG_FINTECH: 7,
    Category.SUPPLY_CHAIN: 6,
    Category.CONNECTIVITY: 6,
    Category.PRECISION_AG: 5,
    Category.FARM_SOFTWARE: 4,  # lowest — AI/Data/Software are generic
}


def classify_tags(tag_string: str) -> Category:
    """Classify a comma-separated tag string into a Category.

    Returns the highest-priority category found, or UNKNOWN.
    """
    if not tag_string:
        return Category.UNKNOWN

    tags = [t.strip().lower() for t in tag_string.split(",")]
    scores: dict[Category, int] = {}

    for tag in tags:
        if tag in TAG_TO_CATEGORY:
            cat = TAG_TO_CATEGORY[tag]
            scores[cat] = scores.get(cat, 0) + PRIORITY.get(cat, 1)

    if not scores:
        return Category.UNKNOWN

    return max(scores, key=scores.get)


def reclassify_with_tags(db: Database):
    """Re-classify UNKNOWN companies using tag-based classification."""
    unknowns = db.conn.execute(
        "SELECT id, name, description FROM companies WHERE category = 'UNKNOWN'"
    ).fetchall()

    logger.info(f"Tag-classifying {len(unknowns)} UNKNOWN companies...")
    reclassified = 0

    for row in unknowns:
        cid, name, desc = row["id"], row["name"], row["description"] or ""

        # Try tag-based classification on description (GrowthList tags)
        cat = classify_tags(desc)

        # If still unknown, try the keyword classifier on name + description
        if cat == Category.UNKNOWN:
            from src.taxonomy import classify
            cat = classify(f"{name} {desc}")

        if cat != Category.UNKNOWN:
            db.conn.execute(
                "UPDATE companies SET category = ? WHERE id = ?",
                (cat.value, cid),
            )
            reclassified += 1

    db.conn.commit()
    logger.info(f"Re-classified {reclassified}/{len(unknowns)} companies")
