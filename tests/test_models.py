from src.models import Category, Company, Grant, Status


def test_category_enum_values():
    assert Category.PRECISION_AG.value == "PRECISION_AG"
    assert Category.UNKNOWN.value == "UNKNOWN"
    assert len(Category) == 13


def test_status_enum_values():
    assert Status.ACTIVE.value == "ACTIVE"
    assert Status.DEFUNCT.value == "DEFUNCT"


def test_company_defaults():
    c = Company(name="Test Corp")
    assert c.category == Category.UNKNOWN
    assert c.status == Status.UNKNOWN
    assert c.country == "US"
    assert c.sources == []
    assert c.id is None


def test_company_with_all_fields():
    c = Company(
        name="Pivot Bio",
        category=Category.BIOTECH,
        hq_city="Berkeley",
        hq_state="CA",
        founded_year=2010,
        status=Status.ACTIVE,
        website="https://pivotbio.com",
        sources=["sbir_gov", "crunchbase"],
    )
    assert c.name == "Pivot Bio"
    assert c.category == Category.BIOTECH
    assert len(c.sources) == 2


def test_grant_defaults():
    g = Grant(company_id=1, agency="USDA")
    assert g.company_id == 1
    assert g.agency == "USDA"
    assert g.amount_usd is None
