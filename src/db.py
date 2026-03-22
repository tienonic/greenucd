"""SQLite database setup and CRUD operations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.models import Category, Company, FundingRound, Grant, Patent, SourceRecord, Status

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    category TEXT NOT NULL DEFAULT 'UNKNOWN',
    hq_city TEXT,
    hq_state TEXT,
    state_of_incorporation TEXT,
    country TEXT DEFAULT 'US',
    founded_year INTEGER,
    status TEXT DEFAULT 'UNKNOWN',
    website TEXT,
    website_live BOOLEAN,
    last_verified_date TEXT,
    description TEXT,
    source TEXT NOT NULL,
    crunchbase_url TEXT,
    linkedin_url TEXT
);

CREATE TABLE IF NOT EXISTS funding_rounds (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    round_type TEXT,
    amount_usd REAL,
    date TEXT,
    investors TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS grants (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    agency TEXT,
    program TEXT,
    title TEXT,
    amount_usd REAL,
    award_date TEXT,
    end_date TEXT,
    abstract TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS patents (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    patent_number TEXT,
    title TEXT,
    filing_date TEXT,
    grant_date TEXT,
    cpc_codes TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS source_records (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    source_name TEXT,
    source_url TEXT,
    raw_data TEXT,
    scraped_date TEXT
);
"""


def _sanitize(val: str | None) -> str | None:
    """Strip control characters and null bytes from text before storage."""
    if val is None:
        return None
    return val.replace("\x00", "").replace("\r", "").strip()


class Database:
    def __init__(self, path: str | Path | None = None):
        if path is None:
            self.conn = sqlite3.connect(":memory:")
        else:
            self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    def insert_company(self, company: Company) -> int:
        from src.dedup import to_slug
        slug = to_slug(company.name)
        source_str = "|".join(company.sources) if company.sources else ""
        cur = self.conn.execute(
            """INSERT INTO companies
               (name, slug, category, hq_city, hq_state, state_of_incorporation,
                country, founded_year, status, website, website_live,
                last_verified_date, description, source, crunchbase_url, linkedin_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_sanitize(company.name), slug, company.category.value,
             _sanitize(company.hq_city), _sanitize(company.hq_state),
             _sanitize(company.state_of_incorporation), _sanitize(company.country),
             company.founded_year, company.status.value, _sanitize(company.website),
             company.website_live, company.last_verified_date,
             _sanitize(company.description),
             source_str, _sanitize(company.crunchbase_url),
             _sanitize(company.linkedin_url)),
        )
        self.conn.commit()
        return cur.lastrowid

    def upsert_company(self, company: Company) -> int:
        """Insert or update a company. Matches on slug. Merges sources."""
        from src.dedup import to_slug
        slug = to_slug(company.name)
        existing = self.get_company_by_slug(slug)
        if existing is None:
            return self.insert_company(company)

        merged_sources = set(existing.sources)
        merged_sources.update(company.sources)

        self.conn.execute(
            """UPDATE companies SET
               category = CASE WHEN ? != 'UNKNOWN' THEN ? ELSE category END,
               hq_city = COALESCE(?, hq_city),
               hq_state = COALESCE(?, hq_state),
               state_of_incorporation = COALESCE(?, state_of_incorporation),
               founded_year = COALESCE(?, founded_year),
               status = CASE WHEN ? != 'UNKNOWN' THEN ? ELSE status END,
               website = COALESCE(?, website),
               description = COALESCE(?, description),
               source = ?,
               crunchbase_url = COALESCE(?, crunchbase_url),
               linkedin_url = COALESCE(?, linkedin_url)
               WHERE slug = ?""",
            (company.category.value, company.category.value,
             company.hq_city, company.hq_state, company.state_of_incorporation,
             company.founded_year,
             company.status.value, company.status.value,
             company.website, company.description,
             "|".join(sorted(merged_sources)),
             company.crunchbase_url, company.linkedin_url,
             slug),
        )
        self.conn.commit()
        return existing.id

    def get_company_by_slug(self, slug: str) -> Company | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE slug = ?", (slug,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_company(row)

    def get_company_by_id(self, company_id: int) -> Company | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_company(row)

    def list_companies(
        self,
        category: Category | None = None,
        status: Status | None = None,
    ) -> list[Company]:
        query = "SELECT * FROM companies WHERE 1=1"
        params: list = []
        if category is not None:
            query += " AND category = ?"
            params.append(category.value)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY name"
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_company(r) for r in rows]

    def count_companies(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM companies").fetchone()
        return row[0]

    def insert_grant(self, grant: Grant) -> int:
        cur = self.conn.execute(
            """INSERT INTO grants
               (company_id, agency, program, title, amount_usd,
                award_date, end_date, abstract, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (grant.company_id, grant.agency, grant.program, grant.title,
             grant.amount_usd, grant.award_date, grant.end_date,
             grant.abstract, grant.source),
        )
        self.conn.commit()
        return cur.lastrowid

    def insert_funding_round(self, funding: FundingRound) -> int:
        cur = self.conn.execute(
            """INSERT INTO funding_rounds
               (company_id, round_type, amount_usd, date, investors, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (funding.company_id, funding.round_type, funding.amount_usd,
             funding.date, funding.investors, funding.source),
        )
        self.conn.commit()
        return cur.lastrowid

    def insert_source_record(self, record: SourceRecord) -> int:
        cur = self.conn.execute(
            """INSERT INTO source_records
               (company_id, source_name, source_url, raw_data, scraped_date)
               VALUES (?, ?, ?, ?, ?)""",
            (record.company_id, record.source_name, record.source_url,
             record.raw_data, record.scraped_date),
        )
        self.conn.commit()
        return cur.lastrowid

    def stats(self) -> dict:
        """Return summary statistics."""
        total = self.count_companies()
        by_category = {}
        for row in self.conn.execute(
            "SELECT category, COUNT(*) as cnt FROM companies GROUP BY category ORDER BY cnt DESC"
        ):
            by_category[row["category"]] = row["cnt"]
        by_status = {}
        for row in self.conn.execute(
            "SELECT status, COUNT(*) as cnt FROM companies GROUP BY status ORDER BY cnt DESC"
        ):
            by_status[row["status"]] = row["cnt"]
        return {
            "total_companies": total,
            "by_category": by_category,
            "by_status": by_status,
        }

    def _row_to_company(self, row: sqlite3.Row) -> Company:
        sources = row["source"].split("|") if row["source"] else []
        return Company(
            id=row["id"],
            name=row["name"],
            category=Category(row["category"]),
            hq_city=row["hq_city"],
            hq_state=row["hq_state"],
            state_of_incorporation=row["state_of_incorporation"],
            country=row["country"] or "US",
            founded_year=row["founded_year"],
            status=Status(row["status"]),
            website=row["website"],
            website_live=bool(row["website_live"]) if row["website_live"] is not None else None,
            last_verified_date=row["last_verified_date"],
            description=row["description"],
            sources=sources,
            crunchbase_url=row["crunchbase_url"],
            linkedin_url=row["linkedin_url"],
        )
