"""Tests for USASpending scraper using fixture data."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models import Category, Status
from src.scrapers.usaspending import USASpendingScraper, _is_gov_or_edu

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "usaspending_response.json"


@pytest.fixture
def fixture_data():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture
def mock_scraper(fixture_data):
    """Scraper that returns fixture data instead of hitting the API."""
    scraper = USASpendingScraper()
    mock_resp = MagicMock()
    mock_resp.json.return_value = fixture_data
    mock_resp.status_code = 200
    scraper.fetch = MagicMock(return_value=mock_resp)
    return scraper


def test_is_gov_or_edu():
    assert _is_gov_or_edu("UNIVERSITY OF CALIFORNIA, DAVIS") is True
    assert _is_gov_or_edu("REGENTS OF THE UNIVERSITY OF CALIFORNIA") is True
    assert _is_gov_or_edu("DEPARTMENT OF EDUCATION CALIFORNIA") is True
    assert _is_gov_or_edu("CAL POLY CORPORATION") is True
    assert _is_gov_or_edu("VERDANT ROBOTICS, INC.") is False
    assert _is_gov_or_edu("OGIVE TECHNOLOGY") is False


def test_scrape_returns_companies(mock_scraper):
    companies = mock_scraper.scrape()
    assert isinstance(companies, list)
    for c in companies:
        assert c.name
        assert c.hq_state == "CA"
        assert "usaspending" in c.sources


def test_scrape_filters_universities(mock_scraper):
    companies = mock_scraper.scrape()
    names = [c.name for c in companies]
    for name in names:
        assert not _is_gov_or_edu(name), f"University/gov should be filtered: {name}"


def test_scrape_assigns_categories(mock_scraper):
    companies = mock_scraper.scrape()
    for c in companies:
        assert isinstance(c.category, Category)


def test_scrape_collects_grants(mock_scraper):
    mock_scraper.scrape()
    grants = mock_scraper.grants
    assert isinstance(grants, list)
    for g in grants:
        assert g.agency == "USDA"
        assert g.source == "usaspending"


def test_scrape_deduplicates_by_name(fixture_data):
    """If same company appears twice, should only appear once in results."""
    dup_record = {
        "Award ID": "UNIQUE-999",
        "Recipient Name": "VERDANT ROBOTICS, INC.",
        "Award Amount": 100000,
        "Award Type": "04",
        "Awarding Agency": "Department of Agriculture",
        "Awarding Sub Agency": "NIFA",
        "Start Date": "2024-01-01",
        "End Date": "2024-12-31",
        "Description": "Agricultural robotics precision agriculture",
        "Place of Performance State Code": "CA",
        "Place of Performance City Name": "DAVIS",
    }
    fixture_data["results"].append(dup_record)

    scraper = USASpendingScraper()
    mock_resp = MagicMock()
    mock_resp.json.return_value = fixture_data
    scraper.fetch = MagicMock(return_value=mock_resp)

    companies = scraper.scrape()
    verdant_count = sum(1 for c in companies if "VERDANT" in c.name.upper())
    assert verdant_count <= 1
