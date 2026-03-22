"""GrowthList agriculture startups scraper (100 free records)."""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from src.models import Company, FundingRound, Status
from src.scrapers.base import BaseScraper
from src.taxonomy import classify

logger = logging.getLogger(__name__)

URL = "https://growthlist.co/agriculture-startups/"


class GrowthListScraper(BaseScraper):
    name = "growthlist"
    rate_limit_seconds = 1.0

    def scrape(self) -> list[Company]:
        resp = self.fetch(URL)
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table", id=lambda x: x and "footable" in str(x))
        if not table:
            logger.error("GrowthList: footable not found")
            return []

        rows = table.select("tbody tr")
        companies = []
        self._funding_rounds: list[FundingRound] = []

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            name = cells[0].get_text(strip=True)
            website = cells[1].get_text(strip=True) if len(cells) > 1 else None
            industry = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            country = cells[3].get_text(strip=True) if len(cells) > 3 else None
            funding_str = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            round_type = cells[5].get_text(strip=True) if len(cells) > 5 else None
            funding_date = cells[6].get_text(strip=True) if len(cells) > 6 else None

            if not name:
                continue

            category = classify(industry)
            funding_amount = _parse_funding(funding_str)

            companies.append(Company(
                name=name,
                category=category,
                country=country or "US",
                status=Status.UNKNOWN,
                website=f"https://{website}" if website and not website.startswith("http") else website,
                description=industry,
                sources=[self.name],
            ))

            if funding_amount:
                self._funding_rounds.append(FundingRound(
                    company_id=0,
                    round_type=round_type,
                    amount_usd=funding_amount,
                    date=funding_date,
                    investors=name,  # temp: store company name for matching
                    source=self.name,
                ))

        logger.info(f"GrowthList: {len(companies)} companies scraped")
        return companies

    @property
    def funding_rounds(self) -> list[FundingRound]:
        return getattr(self, "_funding_rounds", [])


def _parse_funding(s: str) -> float | None:
    """Parse funding string like '$2,954,273' to float."""
    if not s:
        return None
    cleaned = s.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
