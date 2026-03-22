"""Check if company websites are still live."""

from __future__ import annotations

import logging
from datetime import date

import httpx

from src.db import Database
from src.dedup import domain_from_url

logger = logging.getLogger(__name__)


async def check_websites(db: Database, timeout: float = 10.0):
    """Check all companies with websites, update website_live status."""
    companies = db.list_companies()
    companies_with_urls = [c for c in companies if c.website]

    logger.info(f"Checking {len(companies_with_urls)} company websites...")
    today = date.today().isoformat()

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "AgTechCAScraper/0.1 (research)"},
    ) as client:
        for company in companies_with_urls:
            url = company.website
            if not url.startswith("http"):
                url = f"https://{url}"

            try:
                resp = await client.head(url)
                is_live = resp.status_code < 400
            except Exception:
                is_live = False

            db.conn.execute(
                "UPDATE companies SET website_live = ?, last_verified_date = ? WHERE id = ?",
                (is_live, today, company.id),
            )

            status_str = "LIVE" if is_live else "DEAD"
            logger.debug(f"  {company.name}: {status_str} ({url})")

    db.conn.commit()
    logger.info("Website check complete")
