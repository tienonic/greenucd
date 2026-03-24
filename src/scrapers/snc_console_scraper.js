/**
 * SNC Finder Console Scraper
 *
 * Instructions:
 * 1. Open Chrome to: https://finder.startupnationcentral.org/startups/search?alltags=agtech
 * 2. Open DevTools (F12) → Console tab
 * 3. Paste this entire script and press Enter
 * 4. Wait for it to finish — it will download a JSON file
 *
 * The script fetches all agtech/agrifood search pages from within the browser
 * (same-origin, no Cloudflare issues) and extracts company data from the HTML.
 */

(async () => {
  const TAGS = [
    'agtech', 'agriculture', 'foodtech', 'precision-agriculture',
    'food-safety', 'food-waste', 'indoor-farming', 'vertical-farming',
    'greenhouse', 'irrigation', 'aquaculture', 'livestock', 'dairy',
    'alternative-protein', 'crop-protection', 'seeds', 'soil',
    'fertilizer', 'post-harvest', 'urban-farming',
  ];

  const SECTOR_IDS = [
    ['food-land-use', 'kENOo6CntFsUWimInrM3HPxzoF0xu2DqAyz6QoQKnf1H9k3T0x2K8p'],
    ['food-tech', 'v1kI0kRGQPJEvgbgbBqvmhMA1uJyL8xRnPzuj1npR0zDVQ9AcpWQBp'],
    ['farm-equipment', 'mHtoryFWdL28IY7Pf1iYWt3iB1Y6DLFcx3jfEl50XWk1gcEKfNMiF2'],
    ['sustainable-farming', 'ZX0Q21ksVIHp1GQL0HU8PYCtcgOVBw03xw7DXN3hznW5O4AGPQM53L'],
    ['crops', 'agxzfmlsbGlzdHNpdGVyJAsSF0Jhc2VDbGFzc2lmaWNhdGlvbk1vZGVsGICA4Lu1usgLDA'],
    ['food-processing', 'agxzfmlsbGlzdHNpdGVyJAsSF0Jhc2VDbGFzc2lmaWNhdGlvbk1vZGVsGICA4Lv-484JDA'],
    ['novel-food', 'agxzfmlsbGlzdHNpdGVyJAsSF0Jhc2VDbGFzc2lmaWNhdGlvbk1vZGVsGICA4PuayfwJDA'],
    ['agrifood-core', 'agxzfmlsbGlzdHNpdGVyJAsSF0Jhc2VDbGFzc2lmaWNhdGlvbk1vZGVsGICA4PvVnp4JDA'],
  ];

  const allCompanies = new Map(); // slug -> data

  function parseCards(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const cards = doc.querySelectorAll('#main-table-content > div > a[href*="/company_page/"]');
    const results = [];

    for (const card of cards) {
      const href = card.getAttribute('href');
      const slug = href.replace('/company_page/', '').split('?')[0];
      if (!slug || slug.startsWith('--')) continue;

      const nameEl = card.querySelector('.card-title, .company-name, h3, h4, strong');
      const descEl = card.querySelector('.card-description, .company-description, .tagline');
      const sectorEl = card.querySelector('.sector-label, .card-sector');
      const imgEl = card.querySelector('img[src*="storage.googleapis.com"], img[src*="logo"]');

      results.push({
        slug,
        name: nameEl?.textContent?.trim() || slug.replace(/-/g, ' '),
        tagline: descEl?.textContent?.trim() || '',
        sector: sectorEl?.textContent?.trim() || '',
        logo_url: imgEl?.getAttribute('src') || '',
        url: `https://finder.startupnationcentral.org${href}`,
      });
    }
    return results;
  }

  async function fetchSearchPages(baseUrl, label, maxPages = 100) {
    let page = 1;
    let totalCards = 0;

    while (page <= maxPages) {
      const sep = baseUrl.includes('?') ? '&' : '?';
      const url = `${baseUrl}${sep}page=${page}&status=Active`;

      try {
        const resp = await fetch(url);
        if (!resp.ok) break;
        const html = await resp.text();

        // Stop if no results
        if (html.includes('No startups match') || html.includes('0 results')) break;

        const cards = parseCards(html);
        if (cards.length === 0 && page > 1) break;

        for (const c of cards) {
          if (!allCompanies.has(c.slug)) {
            c.sources = [label];
            c.country = 'Israel';
            c.source_name = 'snc_finder';
            allCompanies.set(c.slug, c);
          } else {
            const existing = allCompanies.get(c.slug);
            if (!existing.sources.includes(label)) {
              existing.sources.push(label);
            }
          }
        }

        totalCards += cards.length;
        console.log(`[${label}] page ${page}: ${cards.length} cards (${allCompanies.size} unique total)`);

        // Check for Next button
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const nextBtn = doc.querySelector('a[href*="page="] span');
        const hasNext = [...(doc.querySelectorAll('a[href*="page="]'))].some(
          a => a.textContent.includes('Next')
        );
        if (!hasNext && page > 1) break;

        page++;
        // Small delay to be polite
        await new Promise(r => setTimeout(r, 500));
      } catch (e) {
        console.error(`[${label}] page ${page} error:`, e.message);
        break;
      }
    }
    console.log(`[${label}] done: ${totalCards} cards across ${page - 1} pages`);
  }

  console.log('=== SNC Finder Agrifood Scraper ===');
  console.log(`Searching ${TAGS.length} tags + ${SECTOR_IDS.length} sector IDs...`);

  // Fetch by tags
  for (const tag of TAGS) {
    await fetchSearchPages(
      `https://finder.startupnationcentral.org/startups/search?alltags=${tag}`,
      `tag:${tag}`
    );
  }

  // Fetch by sector IDs
  for (const [label, id] of SECTOR_IDS) {
    await fetchSearchPages(
      `https://finder.startupnationcentral.org/startups/search?coretechnology=${id}`,
      `sector:${label}`
    );
  }

  // Also try the quicksearch API for extra data
  console.log('Trying quicksearch API for enrichment...');
  const enriched = 0;
  for (const [slug, company] of allCompanies) {
    try {
      const resp = await fetch(`/_search?searchname=${encodeURIComponent(company.name)}&withtags=1&itemspertype=4&tagitemspertype=6&external=0`);
      if (resp.ok) {
        const data = await resp.json();
        if (data?.companies?.length) {
          const match = data.companies.find(c => c.urlname === slug || c.name === company.name);
          if (match) {
            company.description = match.description || company.tagline;
            company.entity_id = match.id || '';
            company.logo_url = match.logourl || company.logo_url;
          }
        }
      }
    } catch (e) { /* skip */ }
    // Rate limit
    if (allCompanies.size > 50) {
      await new Promise(r => setTimeout(r, 200));
    }
  }

  // Download as JSON
  const result = [...allCompanies.values()];
  console.log(`\n=== DONE ===`);
  console.log(`Total unique companies: ${result.length}`);
  console.log(`Sources breakdown:`);

  const sourceCounts = {};
  for (const c of result) {
    for (const s of c.sources) {
      sourceCounts[s] = (sourceCounts[s] || 0) + 1;
    }
  }
  console.table(sourceCounts);

  // Trigger download
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'snc_finder_agrifood.json';
  a.click();
  URL.revokeObjectURL(url);

  console.log('JSON file downloaded! Move it to exports/snc_finder_agrifood.json');
})();
