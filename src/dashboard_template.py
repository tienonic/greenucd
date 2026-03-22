"""Generate interactive treemap dashboard HTML."""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>California AgTech Companies</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0a0a0a; color: #e0e0e0; overflow: hidden; }

/* Header */
.header { padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; }
.header h1 { font-size: 1.3rem; font-weight: 600; }
.header h1 span { color: #4ade80; }
.controls { display: flex; gap: 10px; align-items: center; }
.controls label { font-size: 0.8rem; color: #888; }
.controls select { background: #1a1a1a; color: #e0e0e0; border: 1px solid #333; border-radius: 6px; padding: 5px 10px; font-size: 0.8rem; cursor: pointer; }

/* Stats bar */
.stats-bar { display: flex; gap: 20px; padding: 10px 24px; background: #111; border-bottom: 1px solid #222; }
.stat { text-align: center; }
.stat .value { font-size: 1.3rem; font-weight: 700; color: #fff; }
.stat .label { font-size: 0.7rem; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }

/* Filter bar */
.filter-bar { display: flex; gap: 16px; align-items: center; padding: 10px 24px; background: #0d0d0d; border-bottom: 1px solid #222; flex-wrap: wrap; }
.filter-group { display: flex; align-items: center; gap: 6px; }
.filter-group label { font-size: 0.75rem; color: #666; white-space: nowrap; }
.filter-group select, .filter-group input[type=range] { background: #1a1a1a; color: #e0e0e0; border: 1px solid #333; border-radius: 5px; padding: 4px 8px; font-size: 0.8rem; }
.filter-group input[type=range] { width: 140px; accent-color: #4ade80; }
.filter-val { font-size: 0.8rem; color: #4ade80; min-width: 60px; }

/* Year tabs */
.year-tabs { display: flex; gap: 2px; }
.year-tab { padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; cursor: pointer; background: #1a1a1a; border: 1px solid #333; }
.year-tab.active { background: #4ade80; color: #000; border-color: #4ade80; font-weight: 600; }
.year-tab:hover:not(.active) { background: #222; }

/* Main layout */
.main { display: flex; height: calc(100vh - 155px); }
.treemap-container { flex: 1; padding: 12px; position: relative; }
#treemap { width: 100%; height: 100%; }
.no-data-msg { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); color: #555; font-size: 1.1rem; }

/* Sidebar */
.sidebar { width: 340px; border-left: 1px solid #222; display: flex; flex-direction: column; overflow: hidden; }
.sidebar-top { padding: 12px; border-bottom: 1px solid #222; }
.search-box { width: 100%; background: #1a1a1a; border: 1px solid #333; border-radius: 6px; padding: 7px 10px; color: #e0e0e0; font-size: 0.8rem; }
.legend { padding: 8px 12px; border-bottom: 1px solid #1a1a1a; max-height: 160px; overflow-y: auto; }
.legend h3 { font-size: 0.75rem; margin-bottom: 6px; color: #555; text-transform: uppercase; letter-spacing: 0.05em; }
.legend-item { display: flex; align-items: center; gap: 6px; padding: 2px 0; font-size: 0.75rem; }
.legend-swatch { width: 12px; height: 12px; border-radius: 2px; flex-shrink: 0; }
.company-list-header { padding: 8px 12px; font-size: 0.75rem; color: #555; text-transform: uppercase; border-bottom: 1px solid #1a1a1a; }
.company-list { flex: 1; overflow-y: auto; padding: 0 12px; }
.company-item { padding: 8px 0; border-bottom: 1px solid #111; cursor: pointer; }
.company-item:hover { background: #111; margin: 0 -12px; padding-left: 12px; padding-right: 12px; }
.company-item .name { font-weight: 500; font-size: 0.85rem; }
.company-item .meta { color: #666; font-size: 0.7rem; margin-top: 2px; }
.company-item .funding-badge { display: inline-block; background: #1a3a1a; color: #4ade80; font-size: 0.7rem; padding: 1px 6px; border-radius: 3px; }
.company-item.dead .name { color: #f87171; text-decoration: line-through; }
.company-item .wayback-link { color: #60a5fa; font-size: 0.7rem; text-decoration: none; }
.company-item .wayback-link:hover { text-decoration: underline; }

/* Tooltip */
.tooltip { position: absolute; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 12px; font-size: 0.8rem; pointer-events: none; z-index: 100; max-width: 300px; box-shadow: 0 4px 20px rgba(0,0,0,0.6); }
.tooltip .tt-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 6px; }
.tooltip .tt-row { display: flex; justify-content: space-between; gap: 12px; padding: 2px 0; }
.tooltip .tt-label { color: #888; }
.tooltip .tt-dead { color: #f87171; font-size: 0.75rem; margin-top: 6px; }
.tooltip .tt-rounds { margin-top: 6px; font-size: 0.75rem; color: #888; }
</style>
</head>
<body>

<div class="header">
  <h1>California <span>AgTech</span> Companies</h1>
  <div class="controls">
    <label>Color by:</label>
    <select id="colorVar">
      <option value="category">Sector</option>
      <option value="status">Website Status</option>
      <option value="country">Country</option>
      <option value="funding">Funding Amount</option>
      <option value="richness">Data Richness</option>
    </select>
  </div>
</div>

<div class="stats-bar">
  <div class="stat"><div class="value" id="stat-total">0</div><div class="label">Companies</div></div>
  <div class="stat"><div class="value" id="stat-funding">$0</div><div class="label">Total Funding</div></div>
  <div class="stat"><div class="value" id="stat-live" style="color:#4ade80">0</div><div class="label">Live</div></div>
  <div class="stat"><div class="value" id="stat-dead" style="color:#f87171">0</div><div class="label">Dead</div></div>
  <div class="stat"><div class="value" id="stat-classified">0</div><div class="label">Classified</div></div>
  <div class="stat"><div class="value" id="stat-filtered" style="color:#fbbf24">0</div><div class="label">Showing</div></div>
</div>

<div class="filter-bar">
  <div class="filter-group">
    <label>Max Funding:</label>
    <input type="range" id="fundingSlider" min="0" max="21" step="1" value="21">
    <span class="filter-val" id="fundingLabel">All</span>
  </div>
  <div class="filter-group">
    <label>Sector:</label>
    <select id="sectorFilter"><option value="ALL">All Sectors</option></select>
  </div>
  <div class="filter-group">
    <label>Classification:</label>
    <select id="classFilter">
      <option value="ALL">All</option>
      <option value="CLASSIFIED">Classified Only</option>
      <option value="UNKNOWN">Unknown Only</option>
    </select>
  </div>
  <div class="filter-group">
    <label>Status:</label>
    <select id="statusFilter">
      <option value="ALL">All</option>
      <option value="LIVE">Live</option>
      <option value="DEAD">Dead</option>
      <option value="UNKNOWN">Unknown</option>
    </select>
  </div>
  <div class="filter-group">
    <label>Year:</label>
    <div class="year-tabs" id="yearTabs">
      <div class="year-tab active" data-year="ALL">All</div>
      <div class="year-tab" data-year="2022">2022</div>
      <div class="year-tab" data-year="2023">2023</div>
      <div class="year-tab" data-year="2024">2024</div>
      <div class="year-tab" data-year="2025">2025</div>
      <div class="year-tab" data-year="2026">2026</div>
    </div>
  </div>
</div>

<div class="main">
  <div class="treemap-container">
    <div id="treemap"></div>
    <div class="no-data-msg" id="noData" style="display:none">No companies match current filters</div>
  </div>
  <div class="sidebar">
    <div class="sidebar-top">
      <input type="text" class="search-box" id="search" placeholder="Search companies...">
    </div>
    <div class="legend" id="legend"></div>
    <div class="company-list-header">Companies (<span id="list-count">0</span>)</div>
    <div class="company-list" id="company-list"></div>
  </div>
</div>

<div class="tooltip" id="tooltip" style="display:none"></div>

<script>
const DATA = __DATA_PLACEHOLDER__;

const CATEGORY_COLORS = {
  PRECISION_AG:'#3b82f6', FARM_SOFTWARE:'#8b5cf6', BIOTECH:'#10b981',
  ROBOTICS:'#f59e0b', SUPPLY_CHAIN:'#ec4899', WATER_IRRIGATION:'#06b6d4',
  INDOOR_CEA:'#84cc16', AG_FINTECH:'#f97316', LIVESTOCK:'#a855f7',
  FOOD_SAFETY:'#ef4444', AG_BIOCONTROL:'#14b8a6', CONNECTIVITY:'#6366f1',
  UNKNOWN:'#444',
};
const CATEGORY_LABELS = {
  PRECISION_AG:'Precision Ag', FARM_SOFTWARE:'Farm Software', BIOTECH:'Biotech',
  ROBOTICS:'Robotics', SUPPLY_CHAIN:'Supply Chain', WATER_IRRIGATION:'Water/Irrigation',
  INDOOR_CEA:'Indoor/CEA', AG_FINTECH:'AgFintech', LIVESTOCK:'Livestock',
  FOOD_SAFETY:'Food Safety', AG_BIOCONTROL:'Biocontrol', CONNECTIVITY:'Connectivity',
  UNKNOWN:'Unclassified',
};
const STATUS_COLORS = { LIVE:'#4ade80', DEAD:'#f87171', UNKNOWN:'#555' };
const COUNTRY_COLORS = d3.scaleOrdinal(d3.schemeTableau10);

function fundingColor(v) {
  if (!v || v <= 0) return '#333';
  const t = d3.scaleLog().domain([1000, 50000000]).range([0.2, 1]).clamp(true)(v);
  return d3.interpolateGreens(0.3 + t * 0.7);
}
function richnessColor(v) { return d3.interpolateBlues(d3.scaleLinear().domain([0,6]).range([0.15,1]).clamp(true)(v)); }
function getColor(d, mode) {
  switch(mode) {
    case 'category': return CATEGORY_COLORS[d.category]||'#444';
    case 'status': return STATUS_COLORS[d.status]||'#555';
    case 'country': return COUNTRY_COLORS(d.country);
    case 'funding': return fundingColor(d.funding);
    case 'richness': return richnessColor(d.data_richness);
    default: return '#444';
  }
}

// --- Security: HTML escape all untrusted data before rendering ---
const ESC_MAP = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
function esc(s) { return s ? String(s).replace(/[&<>"']/g, c => ESC_MAP[c]) : ''; }
function safeUrl(u) {
  if (!u) return null;
  try { const p = new URL(u); return ['http:','https:'].includes(p.protocol) ? p.href : null; }
  catch { return null; }
}

// Funding slider steps (logarithmic)
const FUNDING_STEPS = [0,1e3,5e3,1e4,2.5e4,5e4,1e5,2.5e5,5e5,1e6,2.5e6,5e6,1e7,2.5e7,5e7,1e8,2.5e8,5e8,1e9,2.5e9,5e9,Infinity];
function fundingStepLabel(i) {
  if (i >= FUNDING_STEPS.length - 1) return 'All';
  const v = FUNDING_STEPS[i];
  if (v === 0) return '$0';
  if (v >= 1e9) return '$' + (v/1e9) + 'B';
  if (v >= 1e6) return '$' + (v/1e6) + 'M';
  if (v >= 1e3) return '$' + (v/1e3) + 'K';
  return '$' + v;
}

// Populate sector filter
const cats = [...new Set(DATA.companies.map(c => c.category))].sort();
const sectorSel = document.getElementById('sectorFilter');
cats.forEach(c => {
  const opt = document.createElement('option');
  opt.value = c; opt.textContent = CATEGORY_LABELS[c] || c;
  sectorSel.appendChild(opt);
});

// State
let currentColorMode = 'category';
let filters = { maxFunding: Infinity, sector: 'ALL', classification: 'ALL', status: 'ALL', year: 'ALL', search: '' };

function getFiltered() {
  return DATA.companies.filter(c => {
    if (filters.maxFunding !== Infinity && (c.funding || 0) > filters.maxFunding) return false;
    if (filters.sector !== 'ALL' && c.category !== filters.sector) return false;
    if (filters.classification === 'CLASSIFIED' && c.category === 'UNKNOWN') return false;
    if (filters.classification === 'UNKNOWN' && c.category !== 'UNKNOWN') return false;
    if (filters.status !== 'ALL' && c.status !== filters.status) return false;
    if (filters.year !== 'ALL') {
      const hasRoundInYear = (c.funding_rounds || []).some(r => r.date && r.date.includes(filters.year));
      if (!hasRoundInYear) return false;
    }
    if (filters.search) {
      const s = filters.search.toLowerCase();
      if (!c.name.toLowerCase().includes(s) && !(c.description||'').toLowerCase().includes(s)) return false;
    }
    return true;
  });
}

function updateStats(filtered) {
  const total = filtered.length;
  const funding = filtered.reduce((s,c) => s + (c.funding||0), 0);
  const live = filtered.filter(c => c.status==='LIVE').length;
  const dead = filtered.filter(c => c.status==='DEAD').length;
  const classified = filtered.filter(c => c.category!=='UNKNOWN').length;
  document.getElementById('stat-total').textContent = DATA.companies.length;
  document.getElementById('stat-funding').textContent = '$' + (funding/1e6).toFixed(1) + 'M';
  document.getElementById('stat-live').textContent = live;
  document.getElementById('stat-dead').textContent = dead;
  document.getElementById('stat-classified').textContent = classified;
  document.getElementById('stat-filtered').textContent = total;
}

const container = document.getElementById('treemap');
const tooltip = document.getElementById('tooltip');
const noData = document.getElementById('noData');

function renderTreemap(filtered) {
  container.querySelectorAll('svg').forEach(s => s.remove());
  if (filtered.length === 0) { noData.style.display = 'block'; return; }
  noData.style.display = 'none';

  const w = container.clientWidth, h = container.clientHeight;
  const groups = {};
  filtered.forEach(c => { (groups[c.category] = groups[c.category] || []).push(c); });

  const hierarchy = {
    name: 'root',
    children: Object.entries(groups).map(([cat, cos]) => ({
      name: cat,
      children: cos.map(c => ({ name: c.name, value: Math.max(c.funding || 1, 1), ...c })),
    })),
  };

  const root = d3.hierarchy(hierarchy).sum(d => d.value || 0).sort((a,b) => b.value - a.value);
  d3.treemap().size([w, h]).padding(2).paddingTop(18).round(true)(root);

  const svg = d3.select('#treemap').append('svg').attr('width', w).attr('height', h);

  const grps = svg.selectAll('.group').data(root.children || []).join('g');
  grps.append('rect')
    .attr('x', d=>d.x0).attr('y', d=>d.y0)
    .attr('width', d=>d.x1-d.x0).attr('height', d=>d.y1-d.y0)
    .attr('fill','none').attr('stroke','#333');
  grps.append('text')
    .attr('x', d=>d.x0+4).attr('y', d=>d.y0+13)
    .text(d => CATEGORY_LABELS[d.data.name]||d.data.name)
    .attr('fill','#666').attr('font-size','10px').attr('font-weight','600');

  const leaves = svg.selectAll('.leaf').data(root.leaves()).join('g')
    .attr('transform', d=>`translate(${d.x0},${d.y0})`);

  leaves.append('rect')
    .attr('width', d=>Math.max(d.x1-d.x0,0)).attr('height', d=>Math.max(d.y1-d.y0,0))
    .attr('fill', d=>getColor(d.data, currentColorMode))
    .attr('rx',2).attr('stroke','#0a0a0a').attr('stroke-width',0.5)
    .style('cursor','pointer')
    .on('mousemove', (e,d) => showTooltip(e, d.data))
    .on('mouseleave', () => { tooltip.style.display='none'; })
    .on('click', (e,d) => {
      const url = d.data.status === 'DEAD' ? safeUrl(d.data.wayback_url) : safeUrl(d.data.website);
      if (url) window.open(url, '_blank', 'noopener');
    });

  leaves.append('text').attr('x',3).attr('y',11)
    .text(d => { const w=d.x1-d.x0; if(w<35) return ''; const m=Math.floor(w/5.5); return d.data.name.length>m ? d.data.name.slice(0,m-1)+'...' : d.data.name; })
    .attr('font-size','8px').attr('fill','#fff').style('pointer-events','none')
    .style('text-shadow','0 1px 2px rgba(0,0,0,0.8)');
}

function showTooltip(event, d) {
  const fmt = v => v ? '$' + v.toLocaleString() : 'N/A';
  let roundsHtml = '';
  if (d.funding_rounds && d.funding_rounds.length) {
    roundsHtml = '<div class="tt-rounds"><b>Rounds:</b><br>' +
      d.funding_rounds.map(r => `${esc(r.type||'?')}: ${fmt(r.amount)} (${esc(r.date||'?')})`).join('<br>') + '</div>';
  }
  let deadHtml = '';
  if (d.status === 'DEAD') {
    const wbUrl = safeUrl(d.wayback_url);
    deadHtml = '<div class="tt-dead">Website is down' + (wbUrl ? ' &mdash; <a href="'+esc(wbUrl)+'" target="_blank" rel="noopener noreferrer" style="color:#60a5fa">View on Wayback Machine</a>' : '') + '</div>';
  }
  tooltip.innerHTML = `
    <div class="tt-name">${esc(d.name)}</div>
    <div class="tt-row"><span class="tt-label">Sector</span><span>${esc(CATEGORY_LABELS[d.category]||d.category)}</span></div>
    <div class="tt-row"><span class="tt-label">Country</span><span>${esc(d.country)}</span></div>
    <div class="tt-row"><span class="tt-label">Status</span><span style="color:${STATUS_COLORS[d.status]||'#888'}">${esc(d.status)}</span></div>
    <div class="tt-row"><span class="tt-label">Total Funding</span><span>${fmt(d.funding)}</span></div>
    ${d.description ? '<div style="margin-top:6px;color:#888;font-size:0.7rem">'+esc(d.description)+'</div>' : ''}
    ${roundsHtml}${deadHtml}
  `;
  tooltip.style.display = 'block';
  tooltip.style.left = Math.min(event.pageX+12, window.innerWidth-320) + 'px';
  tooltip.style.top = Math.min(event.pageY-10, window.innerHeight-200) + 'px';
}

function renderLegend(filtered) {
  const el = document.getElementById('legend');
  el.innerHTML = '<h3>Legend</h3>';
  if (currentColorMode === 'category') {
    const counts = {};
    filtered.forEach(c => { counts[c.category] = (counts[c.category]||0) + 1; });
    Object.entries(CATEGORY_COLORS).forEach(([k,c]) => {
      if (!counts[k]) return;
      el.innerHTML += `<div class="legend-item"><div class="legend-swatch" style="background:${c}"></div>${CATEGORY_LABELS[k]||k} (${counts[k]})</div>`;
    });
  } else if (currentColorMode === 'status') {
    Object.entries(STATUS_COLORS).forEach(([k,c]) => {
      const n = filtered.filter(d=>d.status===k).length;
      if (!n) return;
      el.innerHTML += `<div class="legend-item"><div class="legend-swatch" style="background:${c}"></div>${k} (${n})</div>`;
    });
  } else if (currentColorMode === 'funding') {
    el.innerHTML += '<div class="legend-item"><div class="legend-swatch" style="background:#333"></div>No data</div>';
    el.innerHTML += '<div class="legend-item"><div class="legend-swatch" style="background:'+d3.interpolateGreens(0.4)+'"></div>Low</div>';
    el.innerHTML += '<div class="legend-item"><div class="legend-swatch" style="background:'+d3.interpolateGreens(0.8)+'"></div>High</div>';
  } else if (currentColorMode === 'richness') {
    el.innerHTML += '<div class="legend-item"><div class="legend-swatch" style="background:'+d3.interpolateBlues(0.15)+'"></div>Sparse</div>';
    el.innerHTML += '<div class="legend-item"><div class="legend-swatch" style="background:'+d3.interpolateBlues(0.9)+'"></div>Rich</div>';
  } else if (currentColorMode === 'country') {
    const counts = {};
    filtered.forEach(c => { counts[c.country] = (counts[c.country]||0)+1; });
    Object.entries(counts).sort((a,b)=>b[1]-a[1]).slice(0,10).forEach(([k,n]) => {
      el.innerHTML += `<div class="legend-item"><div class="legend-swatch" style="background:${COUNTRY_COLORS(k)}"></div>${esc(k)} (${n})</div>`;
    });
  }
}

function renderList(filtered) {
  const el = document.getElementById('company-list');
  const sorted = [...filtered].sort((a,b) => (b.funding||0) - (a.funding||0));
  document.getElementById('list-count').textContent = sorted.length;

  el.innerHTML = '';
  sorted.slice(0, 200).forEach(c => {
    const isDead = c.status === 'DEAD';
    const div = document.createElement('div');
    div.className = 'company-item' + (isDead ? ' dead' : '');

    // Safe click handler — validate URL protocol before opening
    const siteUrl = safeUrl(c.website);
    if (siteUrl && !isDead) {
      div.style.cursor = 'pointer';
      div.addEventListener('click', () => window.open(siteUrl, '_blank', 'noopener'));
    }

    const fundBadge = c.funding ? ` <span class="funding-badge">$${(c.funding/1e6).toFixed(1)}M</span>` : '';
    const nameDiv = document.createElement('div');
    nameDiv.className = 'name';
    nameDiv.textContent = c.name;
    if (fundBadge) nameDiv.insertAdjacentHTML('beforeend', fundBadge);

    const metaDiv = document.createElement('div');
    metaDiv.className = 'meta';
    let metaText = `${CATEGORY_LABELS[c.category]||c.category} \u00b7 ${c.country} \u00b7 ${c.status}`;
    metaDiv.textContent = metaText;

    if (isDead && c.wayback_url) {
      const wbUrl = safeUrl(c.wayback_url);
      if (wbUrl) {
        const wbLink = document.createElement('a');
        wbLink.className = 'wayback-link';
        wbLink.href = wbUrl;
        wbLink.target = '_blank';
        wbLink.rel = 'noopener noreferrer';
        wbLink.textContent = ' Wayback';
        metaDiv.appendChild(wbLink);
      }
    }

    div.appendChild(nameDiv);
    div.appendChild(metaDiv);
    el.appendChild(div);
  });
}

function refresh() {
  const filtered = getFiltered();
  updateStats(filtered);
  renderTreemap(filtered);
  renderLegend(filtered);
  renderList(filtered);
}

// Events
document.getElementById('colorVar').addEventListener('change', e => { currentColorMode = e.target.value; refresh(); });
document.getElementById('sectorFilter').addEventListener('change', e => { filters.sector = e.target.value; refresh(); });
document.getElementById('classFilter').addEventListener('change', e => { filters.classification = e.target.value; refresh(); });
document.getElementById('statusFilter').addEventListener('change', e => { filters.status = e.target.value; refresh(); });
document.getElementById('search').addEventListener('input', e => { filters.search = e.target.value; refresh(); });

document.getElementById('fundingSlider').addEventListener('input', e => {
  const idx = parseInt(e.target.value);
  filters.maxFunding = FUNDING_STEPS[idx];
  document.getElementById('fundingLabel').textContent = fundingStepLabel(idx);
  refresh();
});

document.querySelectorAll('.year-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.year-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    filters.year = tab.dataset.year;
    refresh();
  });
});

window.addEventListener('resize', refresh);
refresh();
</script>
</body>
</html>"""


def render_dashboard(data: dict, output_path: Path):
    """Write the dashboard HTML with embedded data."""
    data_json = json.dumps(data, ensure_ascii=False)
    html = TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)
    output_path.write_text(html, encoding="utf-8")
