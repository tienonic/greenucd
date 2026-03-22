"""SBIR.gov Awards and Firms API scraper."""

from __future__ import annotations

import logging

from src.models import Company, Grant, Status
from src.scrapers.base import BaseScraper
from src.taxonomy import classify

logger = logging.getLogger(__name__)

AWARDS_URL = "https://api.www.sbir.gov/public/api/awards"
FIRMS_URL = "https://api.www.sbir.gov/public/api/firm"

AG_AGENCIES = ["USDA"]
AG_KEYWORDS_FOR_OTHER_AGENCIES = [
    "agriculture", "crop", "farm", "irrigation", "precision ag",
    "food safety", "livestock", "plant science", "soil",
]


class SBIRScraper(BaseScraper):
    name = "sbir"
    rate_limit_seconds = 1.0
    max_retries = 2

    def scrape(self) -> list[Company]:
        companies: dict[str, Company] = {}
        self._grants: list[Grant] = []

        # Phase 1: USDA awards in CA
        self._scrape_awards(companies, agency="USDA", state="CA")

        # Phase 2: DOE awards in CA with ag keywords
        self._scrape_awards(companies, agency="DOE", state="CA", require_ag_keywords=True)

        # Phase 3: NSF awards in CA with ag keywords
        self._scrape_awards(companies, agency="NSF", state="CA", require_ag_keywords=True)

        return list(companies.values())

    def _scrape_awards(
        self,
        companies: dict[str, Company],
        agency: str,
        state: str,
        require_ag_keywords: bool = False,
    ):
        start = 0
        batch_size = 100

        while True:
            params = {
                "agency": agency,
                "state": state,
                "rows": batch_size,
                "start": start,
            }
            try:
                resp = self.fetch(AWARDS_URL, params=params)
            except Exception as e:
                logger.error(f"SBIR awards fetch failed (agency={agency}): {e}")
                return

            data = resp.json()
            if not isinstance(data, list) or not data:
                break

            for record in data:
                firm = record.get("firm", "").strip()
                if not firm:
                    continue

                abstract = record.get("abstract", "") or ""
                keywords = record.get("research_area_keywords", "") or ""
                title = record.get("award_title", "") or ""
                combined_text = f"{title} {abstract} {keywords}"

                if require_ag_keywords:
                    lower_text = combined_text.lower()
                    if not any(kw in lower_text for kw in AG_KEYWORDS_FOR_OTHER_AGENCIES):
                        continue

                category = classify(combined_text)

                if firm not in companies:
                    companies[firm] = Company(
                        name=firm,
                        category=category,
                        hq_city=record.get("city"),
                        hq_state=record.get("state"),
                        status=Status.UNKNOWN,
                        website=record.get("company_url"),
                        description=abstract[:500] if abstract else title[:500],
                        sources=[self.name],
                    )

                self._grants.append(Grant(
                    company_id=0,
                    agency=agency,
                    program=f"SBIR {record.get('phase', '')} {record.get('program', '')}".strip(),
                    title=title[:200],
                    amount_usd=record.get("award_amount"),
                    award_date=record.get("proposal_award_date"),
                    end_date=record.get("contract_end_date"),
                    abstract=abstract[:500],
                    source=self.name,
                ))

            if len(data) < batch_size:
                break
            start += batch_size

        logger.info(f"SBIR {agency}/{state}: {len(companies)} total companies")

    @property
    def grants(self) -> list[Grant]:
        return getattr(self, "_grants", [])
