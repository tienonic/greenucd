"""
Targeted Wayback fetch for ~359 agrifood SNC Finder company pages.
Fetches archived pages (no login/Cloudflare needed), extracts data locally.
"""
import asyncio
import aiohttp
import json
import re
import time
from pathlib import Path

SLUGS_FILE = Path(__file__).parent.parent.parent / "exports" / "snc_agrifood_slugs.txt"
OUTPUT = Path(__file__).parent.parent.parent / "exports" / "snc_finder_agrifood.json"
CONCURRENCY = 3  # archive.org rate limits aggressively
CDX = "https://web.archive.org/cdx/search/cdx"
WB = "https://web.archive.org/web"


def extract(html: str, slug: str) -> dict | None:
    """Extract company data from archived SNC page HTML."""
    if not html or len(html) < 5000:
        return None

    # Name + tagline from <title>
    t = re.search(r'<title>([^<]+)</title>', html)
    if not t or 'Wayback' in t.group(1):
        return None
    parts = t.group(1).split(' - ', 1)
    name = parts[0].strip()
    tagline = parts[1].split('|')[0].strip() if len(parts) > 1 else ''
    if not name or name == 'Startup Nation Finder':
        return None

    # Meta description
    d = re.search(r'<meta name="description" content="([^"]*)"', html)
    desc = d.group(1) if d else ''

    # About
    a = re.search(r'id="about"[^>]*>(.*?)</div>', html, re.DOTALL)
    about = re.sub(r'<[^>]+>', '', a.group(1)).strip()[:1000] if a else ''

    # Employees
    e = re.search(r'Employees\s*</h4>.*?font-size:\s*1\.8rem[^>]*>\s*([^<]+)', html, re.DOTALL)
    employees = e.group(1).strip() if e else ''

    # Website
    w = re.search(r'id="social-links-website"[^>]*href="([^"]+)"', html)
    website = w.group(1) if w else ''

    # Funding rounds
    rounds = []
    for m in re.finditer(
        r'font-weight:\s*700[^>]*>\s*([A-Za-z][A-Za-z &]+?)\s*</span>'
        r'.*?lifecycle-item-amount(?:-mobile)?[^>]*>\s*([^<]+)',
        html, re.DOTALL
    ):
        rt, amt = m.group(1).strip(), m.group(2).strip()
        if rt not in ('Founded',) and amt:
            rounds.append({"type": rt, "amount": amt})

    # Founded year
    fy = re.search(r'font-weight:\s*700[^>]*>\s*Founded\s*</span>.*?(\d{4})', html, re.DOTALL)
    founded = fy.group(1) if fy else ''

    # Entity ID
    eid = re.search(r'var entityid = "([^"]+)"', html)

    # Tags
    tags = [t.strip() for t in re.findall(r'tag-item-text[^>]*>([^<]+)', html) if t.strip()]

    return {
        "name": name, "slug": slug, "tagline": tagline,
        "description": desc[:500], "about": about,
        "employees": employees, "website": website,
        "founded_year": founded, "funding_rounds": rounds,
        "tags": tags[:20],
        "entity_id": eid.group(1) if eid else '',
        "country": "Israel", "source_name": "snc_finder",
    }


async def fetch_with_retry(session, url, max_retries=3, timeout=20):
    """Fetch URL with retry on 429."""
    for attempt in range(max_retries):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                if r.status == 429:
                    wait = 10 * (attempt + 1)
                    print(f"    429 rate limit, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                return r.status, await r.text()
        except Exception:
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
    return 0, ''


async def fetch_one(session, slug, sem, stats):
    async with sem:
        await asyncio.sleep(0.5)  # rate limit: ~2 req/s

        # Get best timestamp
        status, text = await fetch_with_retry(
            session,
            f"{CDX}?url=finder.startupnationcentral.org/company_page/{slug}"
            f"&output=json&limit=-1&fl=timestamp,statuscode"
        )
        if status != 200 or not text:
            stats['cdx_fail'] += 1
            return None

        try:
            data = json.loads(text)
        except Exception:
            stats['cdx_fail'] += 1
            return None

        ts = None
        for row in reversed(data[1:]):
            if row[1] == '200':
                ts = row[0]
                break
        if not ts:
            stats['no_snapshot'] += 1
            return None

        await asyncio.sleep(0.5)

        # Fetch archived page
        status, html = await fetch_with_retry(
            session,
            f"{WB}/{ts}id_/https://finder.startupnationcentral.org/company_page/{slug}",
            timeout=30
        )
        if status != 200 or not html:
            stats['fetch_fail'] += 1
            return None

        company = extract(html, slug)
        if company:
            stats['ok'] += 1
        else:
            stats['parse_fail'] += 1
        return company


async def main():
    slugs = SLUGS_FILE.read_text().strip().splitlines()
    print(f"Fetching {len(slugs)} agrifood slugs from Wayback (concurrency={CONCURRENCY})")

    stats = {'ok': 0, 'no_snapshot': 0, 'cdx_fail': 0, 'fetch_fail': 0, 'parse_fail': 0}
    sem = asyncio.Semaphore(CONCURRENCY)
    companies = []

    conn = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [fetch_one(session, s, sem, stats) for s in slugs]
        start = time.time()
        done = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                companies.append(result)
            done += 1
            if done % 50 == 0:
                elapsed = time.time() - start
                print(f"  {done}/{len(slugs)} | {stats['ok']} ok | "
                      f"{elapsed:.0f}s | {done/elapsed:.1f}/s")

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s")
    print(f"OK: {stats['ok']} | No snapshot: {stats['no_snapshot']} | "
          f"CDX fail: {stats['cdx_fail']} | Fetch fail: {stats['fetch_fail']} | "
          f"Parse fail: {stats['parse_fail']}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(companies)} companies to {OUTPUT}")


if __name__ == '__main__':
    asyncio.run(main())
