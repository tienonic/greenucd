"""World Agri-Tech Innovation Summit startup scraper."""

from __future__ import annotations

import json
import logging

from bs4 import BeautifulSoup

from src.models import Company, Status
from src.scrapers.base import BaseScraper
from src.taxonomy import classify

logger = logging.getLogger(__name__)

URL = "https://worldagritechusa.com/start-ups"


class WorldAgriTechScraper(BaseScraper):
    name = "world_agritech"
    rate_limit_seconds = 1.0

    def scrape(self) -> list[Company]:
        resp = self.fetch(URL)
        soup = BeautifulSoup(resp.text, "lxml")

        companies = []
        seen_names: set[str] = set()

        # Extract from JSON-LD Organization blocks
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            if isinstance(data, dict) and data.get("@type") == "Organization":
                name = data.get("name", "").strip()
                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                url = data.get("url", "")
                description = data.get("description", "")
                category = classify(f"{name} {description}")

                companies.append(Company(
                    name=name,
                    category=category,
                    status=Status.UNKNOWN,
                    website=url if url else None,
                    description=description[:500] if description else None,
                    sources=[self.name],
                ))

        logger.info(f"World Agri-Tech: {len(companies)} companies from JSON-LD")
        return companies
