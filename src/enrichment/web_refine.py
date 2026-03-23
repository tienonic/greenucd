"""Web-based company enrichment pipeline.

Generates prioritized batches of companies needing enrichment,
builds prompts for parallel research agents, and imports results.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.db import Database
from src.dedup import to_slug
from src.models import Category, FundingRound

logger = logging.getLogger(__name__)

CATEGORIES_LIST = [c.value for c in Category if c != Category.UNKNOWN]


def get_enrichment_queue(db: Database, limit: int | None = None) -> list[dict]:
    """Query UNKNOWN companies prioritized for web research.

    Priority: agtech-specific sources first (world_agritech, thrive, wgcit,
    growthlist, nifa), then nsf_sbir only if description mentions ag terms.
    NSF SBIR companies without ag terms are excluded — they are likely
    non-agtech false positives from broad scraper queries.
    """
    rows = db.conn.execute("""
        SELECT c.id, c.name, c.slug, c.description, c.website,
               c.hq_state, c.source, c.category, c.founded_year,
               (SELECT g.abstract FROM grants g
                WHERE g.company_id = c.id AND g.abstract IS NOT NULL
                LIMIT 1) as grant_abstract
        FROM companies c
        WHERE c.category = 'UNKNOWN'
        AND NOT (
            c.source = 'nsf_sbir'
            AND (c.description IS NULL OR (
                c.description NOT LIKE '%agricult%'
                AND c.description NOT LIKE '%crop%'
                AND c.description NOT LIKE '%farm%'
                AND c.description NOT LIKE '%soil%'
                AND c.description NOT LIKE '%food%'
                AND c.description NOT LIKE '%livestock%'
                AND c.description NOT LIKE '%irrigation%'
                AND c.description NOT LIKE '%seed%'
                AND c.description NOT LIKE '%harvest%'
                AND c.description NOT LIKE '%pest%'
                AND c.description NOT LIKE '%fertil%'
                AND c.description NOT LIKE '%plant growth%'
                AND c.description NOT LIKE '%agri%'
            ))
        )
        ORDER BY
            (CASE
                WHEN c.source LIKE '%world_agritech%' THEN 10
                WHEN c.source LIKE '%thrive%' THEN 9
                WHEN c.source LIKE '%wgcit%' THEN 8
                WHEN c.source LIKE '%growthlist%' THEN 7
                WHEN c.source LIKE '%nifa%' THEN 6
                WHEN c.source LIKE '%sec_edgar%' THEN 5
                WHEN c.source LIKE '%sbir%' THEN 4
                ELSE 3
            END) +
            (CASE WHEN c.hq_state = 'CA' THEN 2 ELSE 0 END) +
            (CASE WHEN c.website IS NOT NULL THEN 1 ELSE 0 END)
        DESC
    """).fetchall()

    companies = []
    for r in rows:
        companies.append({
            "id": r["id"],
            "name": r["name"],
            "slug": r["slug"],
            "description": r["description"],
            "website": r["website"],
            "hq_state": r["hq_state"],
            "source": r["source"],
            "grant_abstract": r["grant_abstract"],
            "founded_year": r["founded_year"],
        })

    if limit:
        companies = companies[:limit]

    return companies


def make_batches(companies: list[dict], batch_size: int = 25) -> list[list[dict]]:
    """Split company list into batches."""
    return [companies[i:i + batch_size] for i in range(0, len(companies), batch_size)]


def build_agent_prompt(batch: list[dict], batch_id: int) -> str:
    """Build a research prompt for one batch of companies."""
    company_lines = []
    for c in batch:
        context_parts = [f"Name: {c['name']}"]
        if c["slug"]:
            context_parts.append(f"Slug: {c['slug']}")
        if c["website"]:
            context_parts.append(f"Website: {c['website']}")
        if c["hq_state"]:
            context_parts.append(f"State: {c['hq_state']}")
        if c["source"]:
            context_parts.append(f"Sources: {c['source']}")
        if c["description"] and len(c["description"]) > 20:
            desc = c["description"][:200]
            context_parts.append(f"Description: {desc}")
        elif c["grant_abstract"]:
            abstract = c["grant_abstract"][:200]
            context_parts.append(f"Grant abstract: {abstract}")
        company_lines.append("\n".join(f"  {p}" for p in context_parts))

    companies_block = "\n\n".join(
        f"### Company {i+1}\n{line}"
        for i, line in enumerate(company_lines)
    )

    categories_str = ", ".join(CATEGORIES_LIST)

    return f"""You are a research agent. Your task is to find accurate, up-to-date information
about the following {len(batch)} agriculture technology companies.

For each company, use WebSearch to search for it and find:
1. **Website URL** — the company's official website
2. **Description** — 1-2 sentences describing what the company does (from their website or a credible source, NOT from SBIR boilerplate)
3. **Category** — classify into one of: {categories_str}
4. **Founded year** — when the company was founded
5. **Funding** — any known funding rounds or total raised
6. **Status** — ACTIVE if the company is operating, DEFUNCT if shut down

## Search strategy
- Search: "[company name]" agriculture OR agtech
- If found, visit the company website for description and about page
- Search: "[company name]" "raised" OR "funding" OR "series" for funding info
- If no results, try the company name alone

## Rules
- Only output UNKNOWN category if you genuinely cannot determine what the company does
- Do NOT guess funding amounts — only report what you explicitly find with a source
- Skip SBIR boilerplate ("The broader impact/commercial potential...") when writing descriptions
- If a company appears to not exist or has no web presence, set status to "DEFUNCT" and confidence to "low"
- Be concise in descriptions — focus on what the company actually does/makes

## Output format
Write results as a JSON array to: exports/refine_results/batch_{batch_id:02d}.json

Each element:
```json
{{
  "name": "Company Name",
  "slug": "company-slug",
  "website": "https://example.com",
  "description": "What the company does in 1-2 sentences.",
  "category": "BIOTECH",
  "status": "ACTIVE",
  "founded_year": 2019,
  "funding_summary": "$5M Series A (2021)",
  "funding_amount_usd": 5000000,
  "sources": ["https://source-url.com"],
  "confidence": "high"
}}
```

Confidence levels: "high" (found company website + details), "medium" (found some info), "low" (minimal/uncertain).

## Companies to research

{companies_block}
"""


def import_results(db: Database, json_path: str | Path, dry_run: bool = False) -> dict:
    """Import a JSON results file and apply enrichment to the DB.

    Returns summary dict with counts.
    """
    path = Path(json_path)
    if path.is_dir():
        return import_results_from_dir(db, path, dry_run)

    with open(path, encoding="utf-8") as f:
        results = json.load(f)

    if not isinstance(results, list):
        results = [results]

    stats = {"total": len(results), "updated": 0, "skipped": 0, "not_found": 0, "fields": {}}

    for result in results:
        slug = result.get("slug") or to_slug(result.get("name", ""))
        if not slug:
            stats["skipped"] += 1
            continue

        # Skip low-confidence category assignments
        fields = dict(result)
        if fields.get("confidence") == "low" and "category" in fields:
            fields.pop("category", None)

        updated_fields = db.apply_web_enrichment(slug, fields)

        if updated_fields is None or len(updated_fields) == 0:
            # Try fallback slug from name
            if slug != to_slug(result.get("name", "")):
                fallback_slug = to_slug(result["name"])
                updated_fields = db.apply_web_enrichment(fallback_slug, fields)

        if updated_fields:
            stats["updated"] += 1
            for f in updated_fields:
                stats["fields"][f] = stats["fields"].get(f, 0) + 1
            logger.info(f"  Updated {result.get('name')}: {', '.join(updated_fields)}")

            # Handle funding
            if not dry_run and result.get("funding_amount_usd"):
                company = db.get_company_by_slug(slug)
                if company:
                    existing = db.conn.execute(
                        "SELECT COUNT(*) FROM funding_rounds WHERE company_id = ?",
                        (company.id,),
                    ).fetchone()[0]
                    if existing == 0:
                        db.insert_funding_round(FundingRound(
                            company_id=company.id,
                            round_type="total_raised",
                            amount_usd=result["funding_amount_usd"],
                            date=None,
                            investors=None,
                            source="web_research",
                        ))
        else:
            company = db.get_company_by_slug(slug)
            if company is None:
                stats["not_found"] += 1
                logger.warning(f"  Not found: {result.get('name')} (slug: {slug})")
            else:
                stats["skipped"] += 1

    return stats


def import_results_from_dir(db: Database, dir_path: str | Path, dry_run: bool = False) -> dict:
    """Import all JSON files from a results directory."""
    dir_path = Path(dir_path)
    totals = {"total": 0, "updated": 0, "skipped": 0, "not_found": 0, "fields": {}}

    for json_file in sorted(dir_path.glob("*.json")):
        logger.info(f"Importing {json_file.name}...")
        stats = import_results(db, json_file, dry_run)
        totals["total"] += stats["total"]
        totals["updated"] += stats["updated"]
        totals["skipped"] += stats["skipped"]
        totals["not_found"] += stats["not_found"]
        for f, count in stats.get("fields", {}).items():
            totals["fields"][f] = totals["fields"].get(f, 0) + count

    return totals
