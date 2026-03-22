"""Wayback Machine CDX API for detecting defunct companies."""

from __future__ import annotations

import logging

import requests

from src.db import Database
from src.dedup import domain_from_url
from src.models import Status

logger = logging.getLogger(__name__)

CDX_URL = "https://web.archive.org/cdx/search/cdx"


def check_wayback(db: Database):
    """Check Wayback Machine for each company's domain.

    Companies with captures but no live website are likely defunct.
    """
    companies = db.list_companies()
    companies_with_urls = [c for c in companies if c.website]

    logger.info(f"Checking Wayback Machine for {len(companies_with_urls)} domains...")
    session = requests.Session()
    session.headers["User-Agent"] = "AgTechCAScraper/0.1 (research)"

    for company in companies_with_urls:
        domain = domain_from_url(company.website)
        if not domain:
            continue

        try:
            resp = session.get(
                CDX_URL,
                params={
                    "url": f"{domain}/*",
                    "output": "json",
                    "fl": "timestamp,statuscode",
                    "filter": "statuscode:200",
                    "collapse": "timestamp:6",
                    "limit": 50,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                continue

            data = resp.json()
            if len(data) <= 1:
                continue

            captures = data[1:]
            first_capture = captures[0][0][:4] if captures else None
            last_capture = captures[-1][0][:4] if captures else None

            if company.website_live is False and last_capture:
                last_year = int(last_capture)
                if last_year < 2025:
                    db.conn.execute(
                        "UPDATE companies SET status = ? WHERE id = ?",
                        (Status.DEFUNCT.value, company.id),
                    )
                    logger.info(f"  {company.name}: DEFUNCT (last capture {last_capture})")

        except Exception as e:
            logger.debug(f"  Wayback check failed for {domain}: {e}")

    db.conn.commit()
    logger.info("Wayback check complete")
