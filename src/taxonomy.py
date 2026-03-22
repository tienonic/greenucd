"""Keyword-based classifier for AgTech sub-categories."""

from __future__ import annotations

import re

from src.models import Category

CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.PRECISION_AG: [
        "precision agriculture", "precision ag", "precision farming",
        "drone", "uav", "satellite imagery", "remote sensing",
        "sensor", "field mapping", "crop monitoring", "ndvi",
        "variable rate", "gps guidance", "soil mapping", "geospatial",
        "aerial imaging", "multispectral", "hyperspectral",
    ],
    Category.FARM_SOFTWARE: [
        "farm management", "farm software", "farm erp",
        "farm analytics", "agri marketplace", "farm platform",
        "crop planning", "field records", "agronomic data",
        "farm accounting", "agriculture saas", "grower platform",
    ],
    Category.BIOTECH: [
        "gene editing", "crispr", "biologicals", "biostimulant",
        "crop science", "seed trait", "plant breeding", "genomics",
        "microbiome", "nitrogen fixation", "crop genetics",
        "plant biology", "synthetic biology", "crop improvement",
        "molecular discovery", "crop trait",
    ],
    Category.ROBOTICS: [
        "robot", "autonomous", "harvesting robot", "weeding robot",
        "planting robot", "agricultural automation", "farm automation",
        "autonomous tractor", "robotic", "machine vision",
        "automated harvest", "mechanical weeding",
    ],
    Category.SUPPLY_CHAIN: [
        "supply chain", "traceability", "cold chain", "post-harvest",
        "food logistics", "grain storage", "produce logistics",
        "food distribution", "agricultural commodity", "grain handling",
    ],
    Category.WATER_IRRIGATION: [
        "irrigation", "water management", "water conservation",
        "drip irrigation", "smart irrigation", "water accounting",
        "soil moisture", "water efficiency", "water technology",
        "evapotranspiration",
    ],
    Category.INDOOR_CEA: [
        "indoor farming", "vertical farming", "controlled environment",
        "greenhouse technology", "hydroponics", "aeroponics",
        "indoor agriculture", "cea ", "grow room",
    ],
    Category.AG_FINTECH: [
        "crop insurance", "farm lending", "farm finance",
        "agricultural finance", "ag fintech", "trade finance",
        "produce pay", "farm credit", "agricultural lending",
        "farm loan",
    ],
    Category.LIVESTOCK: [
        "livestock", "dairy", "cattle", "poultry", "animal health",
        "feed optimization", "animal monitoring", "herd management",
        "dairy tech", "swine", "aquaculture", "animal nutrition",
    ],
    Category.FOOD_SAFETY: [
        "food safety", "pathogen detection", "food testing",
        "quality assurance", "food quality", "contamination detection",
        "food inspection", "foodborne", "haccp",
    ],
    Category.AG_BIOCONTROL: [
        "pest management", "biocontrol", "bio-pesticide", "biopesticide",
        "integrated pest", "ipm", "biological control", "crop protection",
        "insect management", "weed management", "herbicide alternative",
        "pheromone",
    ],
    Category.CONNECTIVITY: [
        "rural broadband", "farm connectivity", "agricultural iot",
        "rural internet", "farm network", "field connectivity",
        "agricultural connectivity",
    ],
}

_compiled_patterns: dict[Category, list[re.Pattern]] | None = None


def _get_patterns() -> dict[Category, list[re.Pattern]]:
    global _compiled_patterns
    if _compiled_patterns is None:
        _compiled_patterns = {
            cat: [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]
            for cat, keywords in CATEGORY_KEYWORDS.items()
        }
    return _compiled_patterns


def classify(text: str) -> Category:
    """Classify a text description into an AgTech sub-category.

    Returns the category with the most keyword matches,
    or UNKNOWN if no keywords match.
    """
    if not text:
        return Category.UNKNOWN

    patterns = _get_patterns()
    scores: dict[Category, int] = {}

    for cat, cat_patterns in patterns.items():
        score = sum(1 for p in cat_patterns if p.search(text))
        if score > 0:
            scores[cat] = score

    if not scores:
        return Category.UNKNOWN

    return max(scores, key=scores.get)
