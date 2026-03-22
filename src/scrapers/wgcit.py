"""Western Growers Center for Innovation & Technology scraper."""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from src.models import Company, Status
from src.scrapers.base import BaseScraper
from src.taxonomy import classify

logger = logging.getLogger(__name__)

BASE_URL = "https://wginnovation.com/startups/"
MAX_PAGES = 10


class WGCITScraper(BaseScraper):
    name = "wgcit"
    rate_limit_seconds = 1.0

    def scrape(self) -> list[Company]:
        companies = []

        for page_num in range(1, MAX_PAGES + 1):
            url = f"{BASE_URL}?page-number={page_num}"
            try:
                resp = self.fetch(url)
            except Exception:
                logger.warning(f"Failed to fetch WGCIT page {page_num}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            h3_tags = soup.find_all("h3")

            if not h3_tags:
                break

            found_any = False
            for h3 in h3_tags:
                name = h3.get_text(strip=True)
                if not name or len(name) < 2:
                    continue

                # Get description from nearby paragraph
                description = ""
                parent = h3.find_parent()
                if parent:
                    p = parent.find_next("p")
                    if p:
                        description = p.get_text(strip=True)

                # Get founder from h4
                h4 = h3.find_next("h4")
                founder = h4.get_text(strip=True) if h4 else None

                category = classify(f"{name} {description}")

                companies.append(Company(
                    name=name,
                    category=category,
                    hq_city="Salinas",
                    hq_state="CA",
                    status=Status.UNKNOWN,
                    description=description[:500] if description else None,
                    sources=[self.name],
                ))
                found_any = True

            if not found_any:
                break

            logger.info(f"WGCIT page {page_num}: {len(companies)} companies total")

        return companies
