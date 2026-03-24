"""
Parse downloaded SNC Finder HTML files to extract company data.
Run after snc_download_html.py has saved HTML files to exports/snc_html/.
"""
import json
import re
from pathlib import Path

HTML_DIR = Path(__file__).parent.parent.parent / "exports" / "snc_html"
OUTPUT_FILE = Path(__file__).parent.parent.parent / "exports" / "snc_finder_agrifood.json"


def extract_companies_from_search_page(html: str) -> list[dict]:
    """Extract company cards from a search results page."""
    companies = []

    # Each card is an <a> with href="/company_page/{slug}" containing company info
    # Pattern: <a href="/company_page/slug" ...> card content </a>
    cards = re.findall(
        r'<a\s+[^>]*href="(/company_page/([^"]+))"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    for full_url, slug, card_html in cards:
        if slug.startswith('--') or slug.startswith('0,'):
            continue  # CSS artifacts

        company = {"slug": slug, "url": f"https://finder.startupnationcentral.org{full_url}"}

        # Name
        name_m = re.search(r'class="[^"]*company-name[^"]*"[^>]*>([^<]+)', card_html)
        if not name_m:
            name_m = re.search(r'class="[^"]*card-title[^"]*"[^>]*>([^<]+)', card_html)
        if not name_m:
            # Try any bold/heading text
            name_m = re.search(r'<(?:h[2-4]|strong|b)[^>]*>([^<]{2,50})<', card_html)
        company["name"] = name_m.group(1).strip() if name_m else slug.replace('-', ' ').title()

        # Description/tagline
        desc_m = re.search(r'class="[^"]*(?:description|tagline|subtitle)[^"]*"[^>]*>([^<]+)', card_html)
        company["tagline"] = desc_m.group(1).strip() if desc_m else ""

        # Tags in card
        card_tags = re.findall(r'class="[^"]*tag[^"]*"[^>]*>([^<]+)', card_html)
        company["tags"] = [t.strip() for t in card_tags if t.strip() and len(t.strip()) < 50]

        # Logo
        logo_m = re.search(r'<img[^>]*src="([^"]*(?:logo|image)[^"]*)"', card_html, re.IGNORECASE)
        if not logo_m:
            logo_m = re.search(r'<img[^>]*src="(https://storage\.googleapis\.com/[^"]+)"', card_html)
        company["logo_url"] = logo_m.group(1) if logo_m else ""

        # Sector
        sector_m = re.search(r'class="[^"]*sector[^"]*"[^>]*>([^<]+)', card_html)
        company["sector"] = sector_m.group(1).strip() if sector_m else ""

        companies.append(company)

    return companies


def main():
    html_files = sorted(HTML_DIR.glob("*.html"))
    if not html_files:
        print(f"No HTML files found in {HTML_DIR}")
        print("Run snc_download_html.py first.")
        return

    print(f"Found {len(html_files)} HTML files in {HTML_DIR}")

    all_companies = {}  # slug -> company dict (dedup)

    for f in html_files:
        html = f.read_text(encoding="utf-8")
        companies = extract_companies_from_search_page(html)
        source = f.stem  # e.g. "tag_agtech_page1"

        for c in companies:
            slug = c["slug"]
            if slug in all_companies:
                # Merge tags
                existing = all_companies[slug]
                existing["tags"] = list(set(existing.get("tags", []) + c.get("tags", [])))
                existing.setdefault("sources", []).append(source)
            else:
                c["sources"] = [source]
                c["country"] = "Israel"
                c["source_name"] = "snc_finder"
                all_companies[slug] = c

        print(f"  {f.name}: {len(companies)} cards, {len(all_companies)} unique total")

    # Convert to list
    result = list(all_companies.values())
    print(f"\nTotal unique companies: {len(result)}")

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
