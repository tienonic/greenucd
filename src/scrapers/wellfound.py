"""Wellfound (AngelList) agriculture companies scraper.

Uses browser-use CLI since pages are JS-rendered.
"""

from __future__ import annotations

import json
import logging
import time

from bs4 import BeautifulSoup

from src.models import Company, Status
from src.scrapers.base import BaseScraper
from src.scrapers.browser_base import BrowserUseMixin
from src.taxonomy import classify

logger = logging.getLogger(__name__)

URLS = [
    "https://wellfound.com/startups/l/california/agriculture",
    "https://wellfound.com/startups/industry/agriculture",
]


class WellfoundScraper(BaseScraper, BrowserUseMixin):
    name = "wellfound"
    rate_limit_seconds = 2.0

    def scrape(self) -> list[Company]:
        companies: dict[str, Company] = {}

        for base_url in URLS:
            self._scrape_paginated(base_url, companies)

        self.browser_close()
        return list(companies.values())

    def _scrape_paginated(self, base_url: str, companies: dict[str, Company]):
        """Scrape paginated Wellfound listings."""
        for page in range(1, 20):
            url = f"{base_url}?page={page}" if page > 1 else base_url

            if not self.browser_open(url):
                logger.warning(f"Failed to open {url}")
                break

            time.sleep(3)  # let JS render

            # Extract company data via JavaScript
            js_extract = """
            JSON.stringify(
                Array.from(document.querySelectorAll('[data-test="StartupResult"], .styles_component__Ey28J, [class*="StartupResult"]'))
                    .map(el => ({
                        name: (el.querySelector('h2, [class*="name"]') || {}).textContent?.trim() || '',
                        description: (el.querySelector('[class*="pitch"], [class*="description"], p') || {}).textContent?.trim() || '',
                        url: (el.querySelector('a[href*="/company/"]') || {}).href || '',
                    }))
                    .filter(c => c.name.length > 0)
            )
            """
            result = self.browser_eval(js_extract)

            try:
                entries = json.loads(result.strip()) if result.strip() else []
            except (json.JSONDecodeError, ValueError):
                # Fallback: parse HTML
                html = self.browser_get_html()
                entries = self._extract_from_html(html) if html else []

            if not entries:
                logger.info(f"No results on page {page}, stopping")
                break

            for entry in entries:
                name = entry.get("name", "").strip()
                if not name or name in companies:
                    continue

                description = entry.get("description", "") or ""
                category = classify(f"{name} {description}")
                website_url = entry.get("url", "")

                companies[name] = Company(
                    name=name,
                    category=category,
                    hq_state="CA",
                    status=Status.UNKNOWN,
                    description=description[:500] if description else None,
                    sources=[self.name],
                )

            logger.info(f"Wellfound {base_url} page {page}: {len(entries)} entries, {len(companies)} total")
            time.sleep(1)

    def _extract_from_html(self, html: str) -> list[dict]:
        """Fallback HTML parsing for company cards."""
        soup = BeautifulSoup(html, "lxml")
        entries = []

        for card in soup.select("[data-test='StartupResult'], [class*='StartupResult']"):
            name_el = card.select_one("h2, [class*='name']")
            desc_el = card.select_one("[class*='pitch'], [class*='description'], p")

            if name_el:
                entries.append({
                    "name": name_el.get_text(strip=True),
                    "description": desc_el.get_text(strip=True) if desc_el else "",
                })

        return entries
