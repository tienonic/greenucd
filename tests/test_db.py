import pytest

from src.db import Database
from src.models import Category, Company, Grant, Status


def test_insert_and_retrieve_company(db):
    c = Company(name="Pivot Bio", category=Category.BIOTECH, hq_state="CA", sources=["test"])
    cid = db.insert_company(c)
    assert cid == 1

    retrieved = db.get_company_by_id(cid)
    assert retrieved.name == "Pivot Bio"
    assert retrieved.category == Category.BIOTECH
    assert retrieved.hq_state == "CA"


def test_get_company_by_slug(db):
    db.insert_company(Company(name="Carbon Robotics, Inc.", sources=["test"]))
    result = db.get_company_by_slug("carbon-robotics")
    assert result is not None
    assert result.name == "Carbon Robotics, Inc."


def test_get_nonexistent_company(db):
    assert db.get_company_by_slug("nope") is None
    assert db.get_company_by_id(999) is None


def test_list_companies_all(db):
    db.insert_company(Company(name="A Corp", category=Category.BIOTECH, sources=["t"]))
    db.insert_company(Company(name="B Corp", category=Category.ROBOTICS, sources=["t"]))
    companies = db.list_companies()
    assert len(companies) == 2
    assert companies[0].name == "A Corp"


def test_list_companies_by_category(db):
    db.insert_company(Company(name="A Corp", category=Category.BIOTECH, sources=["t"]))
    db.insert_company(Company(name="B Corp", category=Category.ROBOTICS, sources=["t"]))
    biotech = db.list_companies(category=Category.BIOTECH)
    assert len(biotech) == 1
    assert biotech[0].name == "A Corp"


def test_list_companies_by_status(db):
    db.insert_company(Company(name="Alive", status=Status.ACTIVE, sources=["t"]))
    db.insert_company(Company(name="Dead", status=Status.DEFUNCT, sources=["t"]))
    active = db.list_companies(status=Status.ACTIVE)
    assert len(active) == 1
    assert active[0].name == "Alive"


def test_count_companies(db):
    assert db.count_companies() == 0
    db.insert_company(Company(name="X", sources=["t"]))
    assert db.count_companies() == 1


def test_upsert_new_company(db):
    c = Company(name="New Co", category=Category.PRECISION_AG, sources=["source1"])
    cid = db.upsert_company(c)
    assert db.count_companies() == 1
    assert db.get_company_by_id(cid).category == Category.PRECISION_AG


def test_upsert_existing_merges_sources(db):
    cid = db.insert_company(Company(name="MergeBot", sources=["s1"]))
    c2 = Company(name="MergeBot", sources=["s2"])
    db.upsert_company(c2)

    result = db.get_company_by_id(cid)
    assert "s1" in result.sources
    assert "s2" in result.sources
    assert db.count_companies() == 1


def test_upsert_doesnt_overwrite_with_unknown(db):
    cid = db.insert_company(Company(
        name="TypedBot", category=Category.BIOTECH, status=Status.ACTIVE, sources=["s1"]
    ))
    db.upsert_company(Company(
        name="TypedBot", category=Category.UNKNOWN, status=Status.UNKNOWN, sources=["s2"]
    ))

    result = db.get_company_by_id(cid)
    assert result.category == Category.BIOTECH
    assert result.status == Status.ACTIVE


def test_upsert_fills_nulls(db):
    cid = db.insert_company(Company(name="PartialBot", sources=["s1"]))
    db.upsert_company(Company(name="PartialBot", hq_city="Berkeley", website="https://example.com", sources=["s2"]))

    result = db.get_company_by_id(cid)
    assert result.hq_city == "Berkeley"
    assert result.website == "https://example.com"


def test_insert_grant(db):
    cid = db.insert_company(Company(name="Grantee", sources=["t"]))
    gid = db.insert_grant(Grant(company_id=cid, agency="USDA", amount_usd=100000))
    assert gid == 1


def test_stats(db):
    db.insert_company(Company(name="A", category=Category.BIOTECH, status=Status.ACTIVE, sources=["t"]))
    db.insert_company(Company(name="B", category=Category.BIOTECH, status=Status.DEFUNCT, sources=["t"]))
    db.insert_company(Company(name="C", category=Category.ROBOTICS, status=Status.ACTIVE, sources=["t"]))

    s = db.stats()
    assert s["total_companies"] == 3
    assert s["by_category"]["BIOTECH"] == 2
    assert s["by_category"]["ROBOTICS"] == 1
    assert s["by_status"]["ACTIVE"] == 2
    assert s["by_status"]["DEFUNCT"] == 1


def test_duplicate_slug_raises(db):
    db.insert_company(Company(name="Same Name", sources=["t"]))
    with pytest.raises(Exception):
        db.insert_company(Company(name="Same Name", sources=["t2"]))
