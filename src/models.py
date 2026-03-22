"""Data models for the AgTech CA scraper."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Category(str, Enum):
    PRECISION_AG = "PRECISION_AG"
    FARM_SOFTWARE = "FARM_SOFTWARE"
    BIOTECH = "BIOTECH"
    ROBOTICS = "ROBOTICS"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    WATER_IRRIGATION = "WATER_IRRIGATION"
    INDOOR_CEA = "INDOOR_CEA"
    AG_FINTECH = "AG_FINTECH"
    LIVESTOCK = "LIVESTOCK"
    FOOD_SAFETY = "FOOD_SAFETY"
    AG_BIOCONTROL = "AG_BIOCONTROL"
    CONNECTIVITY = "CONNECTIVITY"
    UNKNOWN = "UNKNOWN"


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    ACQUIRED = "ACQUIRED"
    DEFUNCT = "DEFUNCT"
    UNKNOWN = "UNKNOWN"


@dataclass
class Company:
    name: str
    category: Category = Category.UNKNOWN
    hq_city: str | None = None
    hq_state: str | None = None
    state_of_incorporation: str | None = None
    country: str = "US"
    founded_year: int | None = None
    status: Status = Status.UNKNOWN
    website: str | None = None
    website_live: bool | None = None
    last_verified_date: str | None = None
    description: str | None = None
    sources: list[str] = field(default_factory=list)
    crunchbase_url: str | None = None
    linkedin_url: str | None = None
    id: int | None = None


@dataclass
class FundingRound:
    company_id: int
    round_type: str | None = None
    amount_usd: float | None = None
    date: str | None = None
    investors: str | None = None
    source: str | None = None
    id: int | None = None


@dataclass
class Grant:
    company_id: int
    agency: str | None = None
    program: str | None = None
    title: str | None = None
    amount_usd: float | None = None
    award_date: str | None = None
    end_date: str | None = None
    abstract: str | None = None
    source: str | None = None
    id: int | None = None


@dataclass
class Patent:
    company_id: int
    patent_number: str | None = None
    title: str | None = None
    filing_date: str | None = None
    grant_date: str | None = None
    cpc_codes: str | None = None
    source: str | None = None
    id: int | None = None


@dataclass
class SourceRecord:
    company_id: int
    source_name: str
    source_url: str | None = None
    raw_data: str | None = None
    scraped_date: str | None = None
    id: int | None = None
