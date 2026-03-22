from src.models import Category
from src.taxonomy import classify


def test_classify_precision_ag():
    assert classify("drone-based crop monitoring with NDVI analysis") == Category.PRECISION_AG


def test_classify_robotics():
    assert classify("autonomous weeding robot for row crops") == Category.ROBOTICS


def test_classify_biotech():
    assert classify("CRISPR gene editing for nitrogen fixation in crops") == Category.BIOTECH


def test_classify_water():
    assert classify("smart irrigation and soil moisture management") == Category.WATER_IRRIGATION


def test_classify_indoor():
    assert classify("vertical farming in controlled environment agriculture") == Category.INDOOR_CEA


def test_classify_livestock():
    assert classify("dairy cattle monitoring and feed optimization system") == Category.LIVESTOCK


def test_classify_supply_chain():
    assert classify("cold chain traceability for post-harvest produce") == Category.SUPPLY_CHAIN


def test_classify_fintech():
    assert classify("crop insurance and farm lending platform") == Category.AG_FINTECH


def test_classify_food_safety():
    assert classify("rapid pathogen detection for food safety testing") == Category.FOOD_SAFETY


def test_classify_biocontrol():
    assert classify("biological pest management using pheromone-based IPM") == Category.AG_BIOCONTROL


def test_classify_farm_software():
    assert classify("farm management software with crop planning and analytics") == Category.FARM_SOFTWARE


def test_classify_connectivity():
    assert classify("rural broadband IoT infrastructure for agricultural connectivity") == Category.CONNECTIVITY


def test_classify_empty_string():
    assert classify("") == Category.UNKNOWN


def test_classify_unrelated_text():
    assert classify("a social media app for teenagers") == Category.UNKNOWN


def test_classify_picks_strongest_match():
    text = "precision agriculture drone with autonomous robot capabilities and sensor mapping"
    result = classify(text)
    assert result == Category.PRECISION_AG


def test_classify_case_insensitive():
    assert classify("PRECISION AGRICULTURE with DRONE monitoring") == Category.PRECISION_AG
