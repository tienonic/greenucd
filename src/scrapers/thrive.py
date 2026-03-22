"""THRIVE Agrifood scrapers — Top 50 + Alumni.

Uses browser-use CLI for Cloudflare-protected pages.
Falls back to requests if browser-use is unavailable.
"""

from __future__ import annotations

import logging
import time

from bs4 import BeautifulSoup

from src.models import Company, Status
from src.scrapers.base import BaseScraper
from src.scrapers.browser_base import BrowserUseMixin
from src.taxonomy import classify

logger = logging.getLogger(__name__)

TOP50_URLS = [
    "https://thriveagrifood.com/top-50-agtech-2026/",
    "https://thriveagrifood.com/top-50-agtech-2025/",
    "https://thriveagrifood.com/top-50-agtech-2024/",
    "https://thriveagrifood.com/top-50-agtech-2023/",
    "https://thriveagrifood.com/top-50-foodtech-2026/",
    "https://thriveagrifood.com/top-50-foodtech-2025/",
]

ALUMNI_URL = "https://thriveagrifood.com/alumni/"

SKIP_NAMES = {
    "thrive", "svg ventures", "agrifood", "top 50", "logo",
    "thrive agrifood", "menu", "search", "close",
}


def _is_valid_company_name(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 80:
        return False
    if name.lower() in SKIP_NAMES:
        return False
    if any(skip in name.lower() for skip in SKIP_NAMES):
        return False
    return True


def _extract_companies_from_html(html: str, source_name: str) -> list[Company]:
    """Extract company names from rendered HTML using multiple strategies."""
    soup = BeautifulSoup(html, "lxml")
    companies = []
    seen: set[str] = set()

    # Strategy 1: img alt text inside anchor tags
    for a in soup.find_all("a", href=True):
        img = a.find("img", alt=True)
        if not img:
            continue
        name = img["alt"].strip()
        if not _is_valid_company_name(name) or name in seen:
            continue
        seen.add(name)

        href = a.get("href", "")
        website = href if href.startswith("http") and "thriveagrifood" not in href else None

        companies.append(Company(
            name=name,
            category=classify(name),
            status=Status.UNKNOWN,
            website=website,
            sources=[source_name],
        ))

    # Strategy 2: h3/h4 tags
    for tag in soup.find_all(["h3", "h4"]):
        name = tag.get_text(strip=True)
        if not _is_valid_company_name(name) or name in seen:
            continue
        seen.add(name)

        a = tag.find("a", href=True)
        website = None
        if a:
            href = a.get("href", "")
            if href.startswith("http") and "thriveagrifood" not in href:
                website = href

        companies.append(Company(
            name=name,
            category=classify(name),
            status=Status.UNKNOWN,
            website=website,
            sources=[source_name],
        ))

    # Strategy 3: JetEngine listing grid items (Alumni page)
    for item in soup.select(".jet-listing-grid__item"):
        name_el = item.select_one("h2, h3, .jet-listing-dynamic-field__content")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not _is_valid_company_name(name) or name in seen:
            continue
        seen.add(name)

        a = item.find("a", href=True)
        website = None
        if a:
            href = a.get("href", "")
            if href.startswith("http") and "thriveagrifood" not in href:
                website = href

        # Check for location
        location_el = item.select_one("[data-field='location'], .jet-listing-dynamic-field")
        location = location_el.get_text(strip=True) if location_el else None

        companies.append(Company(
            name=name,
            category=classify(name),
            status=Status.UNKNOWN,
            website=website,
            sources=[source_name],
        ))

    return companies


class ThriveTop50Scraper(BaseScraper, BrowserUseMixin):
    name = "thrive_top50"
    rate_limit_seconds = 2.0

    def scrape(self) -> list[Company]:
        companies: dict[str, Company] = {}

        for url in TOP50_URLS:
            html = self._fetch_page(url)
            if not html or len(html) < 500:
                logger.warning(f"No content for {url}")
                continue

            page_companies = _extract_companies_from_html(html, self.name)
            for c in page_companies:
                if c.name not in companies:
                    companies[c.name] = c

            logger.info(f"THRIVE Top50 {url}: {len(page_companies)} companies")

        self.browser_close()
        return list(companies.values())

    def _fetch_page(self, url: str) -> str | None:
        """Try browser-use first (handles Cloudflare), fall back to requests."""
        try:
            if self.browser_open(url):
                time.sleep(2)  # let Cloudflare challenge resolve
                html = self.browser_get_html()
                if html and len(html) > 500:
                    return html
        except Exception as e:
            logger.debug(f"browser-use failed for {url}: {e}")

        # Fallback to requests
        try:
            resp = self.fetch(url)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
        except Exception:
            pass

        return None


class ThriveAlumniScraper(BaseScraper, BrowserUseMixin):
    name = "thrive_alumni"
    rate_limit_seconds = 2.0

    def scrape(self) -> list[Company]:
        companies: dict[str, Company] = {}

        if not self.browser_open(ALUMNI_URL):
            logger.error("Failed to open THRIVE Alumni page")
            return []

        time.sleep(3)  # let Cloudflare + page load

        # Scroll and click "load more" to get all alumni
        max_loads = 25
        for i in range(max_loads):
            html = self.browser_get_html()
            current_count = len(_extract_companies_from_html(html or "", self.name))

            # Try clicking a load-more button
            state = self.browser_state()
            load_more_clicked = False

            if "load more" in state.lower() or "load-more" in state.lower():
                # Find and click the load more button by evaluating JS
                self.browser_eval(
                    "document.querySelector('.jet-listing-grid__loader, "
                    "[data-nav=\"load_more\"] button, "
                    ".jet-smart-listing__load-more')?.click()"
                )
                load_more_clicked = True
                time.sleep(2)

            if not load_more_clicked:
                # Try scrolling to trigger lazy load
                self.browser_scroll_down(2000)
                time.sleep(1)

            new_html = self.browser_get_html()
            new_count = len(_extract_companies_from_html(new_html or "", self.name))

            if new_count <= current_count and i > 2:
                logger.info(f"No new companies after load {i+1}, stopping")
                break

            logger.debug(f"Load {i+1}: {new_count} companies")

        # Final extraction
        final_html = self.browser_get_html()
        if final_html:
            for c in _extract_companies_from_html(final_html, self.name):
                if c.name not in companies:
                    companies[c.name] = c

        self.browser_close()
        logger.info(f"THRIVE Alumni: {len(companies)} companies total")
        return list(companies.values())
