"""Tests for WGCIT scraper against fixture."""

from pathlib import Path
from unittest.mock import MagicMock

from src.models import Category
from src.scrapers.wgcit import WGCITScraper

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "wgcit_page1.html"


def test_scrape_extracts_companies():
    scraper = WGCITScraper()

    with open(FIXTURE, encoding="utf-8") as f:
        html = f.read()

    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.status_code = 200

    empty_resp = MagicMock()
    empty_resp.text = "<html><body></body></html>"
    empty_resp.status_code = 200

    call_count = 0
    def mock_fetch(url, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp if call_count == 1 else empty_resp

    scraper.fetch = mock_fetch

    companies = scraper.scrape()
    assert len(companies) >= 3
    names = [c.name for c in companies]
    assert any("Nexus" in n or "Robotics" in n for n in names)


def test_scrape_sets_salinas_hq():
    scraper = WGCITScraper()

    with open(FIXTURE, encoding="utf-8") as f:
        html = f.read()

    mock_resp = MagicMock()
    mock_resp.text = html
    empty_resp = MagicMock()
    empty_resp.text = "<html></html>"

    call_count = 0
    def mock_fetch(url, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp if call_count == 1 else empty_resp

    scraper.fetch = mock_fetch
    companies = scraper.scrape()

    for c in companies:
        assert c.hq_city == "Salinas"
        assert c.hq_state == "CA"
        assert "wgcit" in c.sources
