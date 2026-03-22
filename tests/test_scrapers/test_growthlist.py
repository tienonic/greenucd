"""Tests for GrowthList scraper against fixture."""

from pathlib import Path
from unittest.mock import MagicMock

from src.scrapers.growthlist import GrowthListScraper, _parse_funding

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "growthlist_table.html"


def test_parse_funding():
    assert _parse_funding("$2,954,273") == 2954273.0
    assert _parse_funding("$500,000") == 500000.0
    assert _parse_funding("") is None
    assert _parse_funding("N/A") is None


def test_scrape_extracts_100_companies():
    scraper = GrowthListScraper()

    with open(FIXTURE, encoding="utf-8") as f:
        html = f.read()

    mock_resp = MagicMock()
    mock_resp.text = html
    scraper.fetch = MagicMock(return_value=mock_resp)

    companies = scraper.scrape()
    assert len(companies) == 100

    for c in companies:
        assert c.name
        assert "growthlist" in c.sources


def test_scrape_includes_funding_data():
    scraper = GrowthListScraper()

    with open(FIXTURE, encoding="utf-8") as f:
        html = f.read()

    mock_resp = MagicMock()
    mock_resp.text = html
    scraper.fetch = MagicMock(return_value=mock_resp)

    scraper.scrape()
    rounds = scraper.funding_rounds
    assert len(rounds) > 0
    assert any(r.amount_usd and r.amount_usd > 0 for r in rounds)
