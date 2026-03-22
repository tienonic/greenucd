"""Tests for World Agri-Tech scraper against fixture."""

from pathlib import Path
from unittest.mock import MagicMock

from src.scrapers.world_agritech import WorldAgriTechScraper

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "world_agritech.html"


def test_scrape_extracts_companies():
    scraper = WorldAgriTechScraper()

    with open(FIXTURE, encoding="utf-8") as f:
        html = f.read()

    mock_resp = MagicMock()
    mock_resp.text = html
    scraper.fetch = MagicMock(return_value=mock_resp)

    companies = scraper.scrape()
    assert len(companies) > 30  # expect ~97 JSON-LD blocks

    names = [c.name for c in companies]
    # Known companies from our research
    assert any("Ancient Organics" in n for n in names)
    assert any("Invasive Species" in n for n in names)


def test_scrape_has_websites():
    scraper = WorldAgriTechScraper()

    with open(FIXTURE, encoding="utf-8") as f:
        html = f.read()

    mock_resp = MagicMock()
    mock_resp.text = html
    scraper.fetch = MagicMock(return_value=mock_resp)

    companies = scraper.scrape()
    with_websites = [c for c in companies if c.website]
    assert len(with_websites) > 0


def test_all_companies_sourced():
    scraper = WorldAgriTechScraper()

    with open(FIXTURE, encoding="utf-8") as f:
        html = f.read()

    mock_resp = MagicMock()
    mock_resp.text = html
    scraper.fetch = MagicMock(return_value=mock_resp)

    for c in scraper.scrape():
        assert "world_agritech" in c.sources
