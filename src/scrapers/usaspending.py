"""USASpending.gov scraper for USDA awards to CA companies."""

from __future__ import annotations

import logging

from src.models import Company, Grant, Status
from src.scrapers.base import BaseScraper
from src.taxonomy import classify

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

KEYWORD_BATCHES = [
    ["agriculture technology", "agtech", "precision agriculture"],
    ["crop sensor", "farm management software", "agricultural robotics"],
    ["irrigation technology", "food safety technology", "livestock technology"],
    ["plant science", "biological control", "soil sensor"],
    ["harvest automation", "drone agriculture", "vertical farming"],
    ["crop protection", "seed technology", "agricultural drone"],
    ["farm automation", "smart irrigation", "controlled environment agriculture"],
]

FIELDS = [
    "Award ID", "Recipient Name", "Award Amount", "Award Type",
    "Awarding Agency", "Awarding Sub Agency",
    "Start Date", "End Date", "Description",
    "Place of Performance State Code", "Place of Performance City Name",
]

GOV_INDICATORS = [
    "university", "college", "regents of", "board of trustees",
    "state of california", "county of", "department of",
    "community college", "school district", "agricultural research service",
    "institute of technology", "cal poly corporation",
]


def _is_gov_or_edu(name: str) -> bool:
    lower = name.lower()
    return any(ind in lower for ind in GOV_INDICATORS)


class USASpendingScraper(BaseScraper):
    name = "usaspending"
    rate_limit_seconds = 0.5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.page_size = 100

    def _build_payload(self, keywords: list[str], page: int = 1) -> dict:
        return {
            "filters": {
                "agencies": [{
                    "type": "awarding",
                    "tier": "toptier",
                    "name": "Department of Agriculture",
                }],
                "place_of_performance_locations": [
                    {"country": "USA", "state": "CA"}
                ],
                "award_type_codes": ["02", "03", "04", "05"],
                "time_period": [
                    {"start_date": "2022-01-01", "end_date": "2026-12-31"}
                ],
                "keywords": keywords,
            },
            "fields": FIELDS,
            "limit": self.page_size,
            "page": page,
            "sort": "Award Amount",
            "order": "desc",
        }

    def scrape(self) -> list[Company]:
        companies: dict[str, Company] = {}
        self._grants: list[Grant] = []
        seen_award_ids: set[str] = set()

        for batch in KEYWORD_BATCHES:
            page = 1
            while True:
                payload = self._build_payload(batch, page)
                try:
                    resp = self.fetch(SEARCH_URL, method="POST", json=payload)
                except Exception:
                    logger.error(f"Failed: keywords={batch}, page={page}")
                    break

                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break

                for record in results:
                    award_id = record.get("Award ID", "")
                    if award_id in seen_award_ids:
                        continue
                    seen_award_ids.add(award_id)

                    name = record.get("Recipient Name", "").strip()
                    if not name or _is_gov_or_edu(name):
                        continue

                    description = record.get("Description", "") or ""
                    category = classify(description)

                    if name not in companies:
                        companies[name] = Company(
                            name=name,
                            category=category,
                            hq_city=record.get("Place of Performance City Name"),
                            hq_state="CA",
                            status=Status.UNKNOWN,
                            description=description[:500] if description else None,
                            sources=[self.name],
                        )

                    self._grants.append(Grant(
                        company_id=0,
                        agency="USDA",
                        program=record.get("Awarding Sub Agency"),
                        title=description[:200] if description else None,
                        amount_usd=record.get("Award Amount"),
                        award_date=record.get("Start Date"),
                        end_date=record.get("End Date"),
                        source=self.name,
                    ))

                has_next = data.get("page_metadata", {}).get("hasNext", False)
                if not has_next:
                    break
                page += 1

            logger.info(f"Batch {batch}: {len(companies)} unique companies so far")

        return list(companies.values())

    @property
    def grants(self) -> list[Grant]:
        return getattr(self, "_grants", [])
