from src.dedup import domain_from_url, is_likely_match, normalize_name, to_slug


def test_normalize_strips_inc():
    assert normalize_name("Pivot Bio, Inc.") == "pivot bio"


def test_normalize_strips_llc():
    assert normalize_name("FarmWise LLC") == "farmwise"


def test_normalize_strips_technologies():
    assert normalize_name("Fieldin Technologies") == "fieldin"


def test_normalize_strips_corp():
    assert normalize_name("Sound Agriculture Corp") == "sound agriculture"


def test_normalize_strips_multiple_suffixes():
    assert normalize_name("AgTech Solutions, Inc.") == "agtech"


def test_normalize_collapses_whitespace():
    assert normalize_name("  Carbon   Robotics  ") == "carbon robotics"


def test_normalize_removes_punctuation():
    assert normalize_name("Ag-Tools & Co.") == "agtools"


def test_to_slug():
    assert to_slug("Pivot Bio, Inc.") == "pivot-bio"
    assert to_slug("Carbon Robotics") == "carbon-robotics"
    assert to_slug("FarmWise LLC") == "farmwise"


def test_domain_from_url():
    assert domain_from_url("https://www.pivotbio.com/about") == "pivotbio.com"
    assert domain_from_url("http://farmwise.io") == "farmwise.io"
    assert domain_from_url("pivotbio.com") == "pivotbio.com"


def test_domain_from_url_empty():
    assert domain_from_url("") is None
    assert domain_from_url(None) is None


def test_is_likely_match_exact():
    assert is_likely_match("Pivot Bio", "Pivot Bio") is True


def test_is_likely_match_with_suffix():
    assert is_likely_match("Pivot Bio, Inc.", "Pivot Bio") is True


def test_is_likely_match_different():
    assert is_likely_match("Pivot Bio", "Carbon Robotics") is False


def test_is_likely_match_close_names():
    assert is_likely_match("FarmWise", "Farmwise Labs") is True


def test_is_likely_match_completely_different():
    assert is_likely_match("Google", "Apple") is False
