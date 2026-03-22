"""Company name normalization and deduplication."""

from __future__ import annotations

import re
from urllib.parse import urlparse

STRIP_SUFFIXES = re.compile(
    r",?\s*\b(inc\.?|llc\.?|corp\.?|corporation|ltd\.?|limited|co\.?|"
    r"company|incorporated|lp\.?|plc\.?|gmbh|s\.?a\.?|"
    r"technologies|technology|tech|labs?|systems?|solutions?|"
    r"ventures?|group|holdings?|enterprises?)\b\.?",
    re.IGNORECASE,
)
WHITESPACE = re.compile(r"\s+")
NON_ALNUM = re.compile(r"[^a-z0-9\s]")


def normalize_name(name: str) -> str:
    """Normalize a company name for comparison.

    Strips legal suffixes, punctuation, collapses whitespace, lowercases.
    """
    result = STRIP_SUFFIXES.sub("", name)
    result = NON_ALNUM.sub("", result.lower())
    result = WHITESPACE.sub(" ", result).strip()
    return result


def to_slug(name: str) -> str:
    """Convert a company name to a URL-safe slug."""
    normalized = normalize_name(name)
    return re.sub(r"\s+", "-", normalized)


def domain_from_url(url: str) -> str | None:
    """Extract the base domain from a URL, stripping www prefix."""
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.hostname
        if domain and domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return None


def is_likely_match(name_a: str, name_b: str, threshold: float = 0.85) -> bool:
    """Check if two company names likely refer to the same entity.

    Uses normalized Levenshtein ratio.
    """
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)

    if norm_a == norm_b:
        return True

    ratio = _levenshtein_ratio(norm_a, norm_b)
    return ratio >= threshold


def _levenshtein_ratio(s: str, t: str) -> float:
    """Compute Levenshtein similarity ratio between two strings."""
    if not s and not t:
        return 1.0
    max_len = max(len(s), len(t))
    if max_len == 0:
        return 1.0
    distance = _levenshtein_distance(s, t)
    return 1.0 - (distance / max_len)


def _levenshtein_distance(s: str, t: str) -> int:
    """Compute Levenshtein edit distance."""
    if len(s) < len(t):
        return _levenshtein_distance(t, s)
    if len(t) == 0:
        return len(s)

    prev_row = list(range(len(t) + 1))
    for i, sc in enumerate(s):
        curr_row = [i + 1]
        for j, tc in enumerate(t):
            cost = 0 if sc == tc else 1
            curr_row.append(min(
                curr_row[j] + 1,
                prev_row[j + 1] + 1,
                prev_row[j] + cost,
            ))
        prev_row = curr_row

    return prev_row[-1]
