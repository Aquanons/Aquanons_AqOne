// Headless-Edge render check for the MDRRMO dashboard (docs/71).
//
// Measures what node --test cannot see - clipped tabs, contrast, legends,
// rendered text - against a running backend, and saves named screenshots.
// Usage and environment: tools/render-check/README.md.

import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const option = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
};

const BASE = process.env.AQONE_BASE || 'http://localhost:8765';
const EMAIL = process.env.AQONE_EMAIL || 'render.check@example.com';
const PASSWORD = process.env.AQONE_PASSWORD || 'rendercheck123';
const DEMO_KEY = process.env.AQONE_DEMO_KEY || 'demo';
const OUT = resolve(option('--out', 'out'));
const REQUIRED = (option('--require', '') || '').split(',').filter(Boolean);
const WIDTHS = [1280, 1440, 1920];

mkdirSync(OUT, { recursive: true });
const results = {};
const record = (id, ok, detail) => {
  results[id] = { ok, detail };
  console.log(`${ok ? 'PASS' : 'FAIL'} ${id} ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`);
};

async function api(path, { method = 'GET', token, body, demo } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (demo) headers['X-Demo-Key'] = DEMO_KEY;
  const res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { json = text; }
  return { status: res.status, json };
}

// --setup: the presenter scenario (demo beats 0-6) and one evaluation, so the
// trip-check queue, the risk feed and a synthetic drift replay have data.
// --live-case: also acknowledge the demo SOS and open a drift case from it,
// for a database seeded with seed_live_currents.sql.
async function setup() {
  const login = await api('/api/login', { method: 'POST', body: { email: EMAIL, password: PASSWORD } });
  if (login.status !== 200) throw new Error(`login failed: ${login.status} ${JSON.stringify(login.json)}`);
  const token = login.json.token || login.json.access_token;
  const start = await api('/api/demo/scenario/squall-fleet/start', { method: 'POST', demo: true });
  if (start.status !== 200) throw new Error(`scenario start: ${start.status} ${JSON.stringify(start.json)}`);
  for (const beat of [1, 2, 3, 4, 5, 6]) {
    const res = await api(`/api/demo/beat/${beat}`, { method: 'POST', demo: true });
    if (res.status !== 200) throw new Error(`beat ${beat}: ${res.status} ${JSON.stringify(res.json)}`);
  }
  await api('/api/ai/anomaly/evaluate', { method: 'POST', token });
  if (flag('--live-case')) {
    const recent = await api('/api/sos/active', { token });
    const sos = (recent.json.events || []).find((event) => event.is_synthetic && event.latitude != null);
    if (!sos) throw new Error('no demo SOS to acknowledge');
    await api(`/api/sos/${sos.id}/acknowledge`, { method: 'POST', token, body: {} });
    const datumAt = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    const opened = await api('/api/ai/drift/cases', {
      method: 'POST', token,
      body: { source_type: 'sos', source_id: sos.id, object_class: 'swamped_banca', forecast_hours: 1, datum_at: datumAt },
    });
    console.log(`live case: ${opened.status} ${JSON.stringify(opened.json).slice(0, 200)}`);
    // The overdue trip's last contact is hours old, so a 24 h case from it
    // cannot pass the environmental gate: the honest insufficient state.
    const open = await api('/api/ai/anomaly/cases/open', { token });
    const trip = (open.json || [])[0];
    if (trip) {
      await api(`/api/ai/anomaly/cases/${trip.id}/escalate`, { method: 'POST', token, body: { reason: 'render check' } });
      const fromTrip = await api('/api/ai/drift/cases', {
        method: 'POST', token, body: { source_type: 'anomaly', source_id: trip.id, object_class: 'swamped_banca' },
      });
      console.log(`insufficient case: ${fromTrip.status} ${JSON.stringify(fromTrip.json).slice(0, 160)}`);
    }
  }
  console.log('setup: scenario, beats 1-6 and an evaluation done');
}

function parseColor(value) {
  const match = String(value).match(/rgba?\(([^)]+)\)/);
  if (!match) return null;
  const parts = match[1].split(',').map((part) => parseFloat(part));
  return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
}

function luminance({ r, g, b }) {
  const channel = (value) => {
    const v = value / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function over(top, bottom) {
  const a = top.a;
  return { r: top.r * a + bottom.r * (1 - a), g: top.g * a + bottom.g * (1 - a), b: top.b * a + bottom.b * (1 - a), a: 1 };
}

function contrast(foreground, layers) {
  // layers: background colors from the element outwards.
  let base = { r: 255, g: 255, b: 255, a: 1 };
  const parsed = layers.map(parseColor).filter(Boolean);
  const opaque = parsed.findIndex((color) => color.a >= 1);
  const stack = opaque >= 0 ? parsed.slice(0, opaque + 1) : parsed;
  for (const color of stack.reverse()) base = color.a >= 1 ? color : over(color, base);
  const fg = over(parseColor(foreground), base);
  const [hi, lo] = [luminance(fg), luminance(base)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

async function colorsOf(page, selector) {
  return page.$eval(selector, (el) => {
    const layers = [];
    for (let node = el; node; node = node.parentElement) layers.push(getComputedStyle(node).backgroundColor);
    return { color: getComputedStyle(el).color, layers, text: el.textContent.trim() };
  });
}

async function pageApi(page, path) {
  return page.evaluate(async (p) => {
    const res = await fetch(p, { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('aqoneToken') } });
    return res.ok ? res.json() : { status: res.status };
  }, path);
}

async function main() {
  if (flag('--setup')) await setup();

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleErrors = [];
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  page.on('pageerror', (error) => consoleErrors.push('pageerror: ' + error.message));
  page.on('response', (response) => {
    if (response.status() >= 500) consoleErrors.push(`HTTP ${response.status()} ${response.url()}`);
  });

  await page.goto(`${BASE}/html/login.html`);
  await page.fill('#email', EMAIL);
  await page.fill('#password', PASSWORD);
  await page.click('.operations-login-action');
  await page.waitForURL(/dashboard/, { timeout: 20000 });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: join(OUT, 'dashboard-1440.png') });

  // RND-01: every stats tab inside the visible tab bar.
  const tabFindings = [];
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForTimeout(400);
    const boxes = await page.$$eval('.stats-tab', (tabs) => {
      const bar = tabs[0].parentElement.getBoundingClientRect();
      let clip = tabs[0].parentElement;
      while (clip && getComputedStyle(clip).overflow === 'visible') clip = clip.parentElement;
      const clipBox = (clip || document.body).getBoundingClientRect();
      return tabs.map((tab) => {
        const box = tab.getBoundingClientRect();
        const inside = box.left >= Math.max(bar.left, clipBox.left) - 0.5 && box.right <= Math.min(bar.right, clipBox.right) + 0.5;
        return { tab: tab.dataset.tab, inside, left: Math.round(box.left), right: Math.round(box.right) };
      });
    });
    const outside = boxes.filter((box) => !box.inside);
    tabFindings.push({ width, outside: outside.map((box) => box.tab) });
    const tabBar = await page.$('.stats-tab');
    await (await tabBar.evaluateHandle((el) => el.parentElement)).asElement().screenshot({ path: join(OUT, `tabs-${width}.png`) });
  }
  record('RND-01', tabFindings.every((finding) => finding.outside.length === 0), tabFindings);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(400);

  // RND-02: trip-check rows name a reason.
  const tripTab = await page.$('.stats-tab[data-tab="tripchecks"]');
  const tripBox = await tripTab.boundingBox();
  if (tripBox && tripBox.x + tripBox.width <= 1440) await page.mouse.click(tripBox.x + tripBox.width / 2, tripBox.y + tripBox.height / 2);
  else await tripTab.evaluate((el) => el.click());
  await page.waitForTimeout(800);
  const tripText = await page.$eval('#trip-checks-list', (el) => el.innerText);
  const cases = await pageApi(page, '/api/ai/anomaly/cases/open');
  const tripPanel = await page.$('#tab-tripchecks');
  await (await tripPanel.evaluateHandle((el) => el.closest('.panel-card') || el)).asElement().screenshot({ path: join(OUT, 'trip-checks.png') });
  if (Array.isArray(cases) && cases.length) {
    record('RND-02', !tripText.includes('No reason recorded'), tripText.split('\n').slice(0, 6).join(' | '));
  } else {
    record('RND-02', false, 'no open trip check to inspect - run with --setup');
  }

  // RND-03 and RND-04: the Vessels tab shows real risk rows and no sample vessels.
  await page.click('.stats-tab[data-tab="vessels"]');
  await page.waitForTimeout(800);
  const active = await pageApi(page, '/api/ai/anomaly/active');
  const vesselsText = await page.$eval('#tab-vessels', (el) => el.innerText);
  const vesselsPanel = await page.$('#tab-vessels');
  await (await vesselsPanel.evaluateHandle((el) => el.closest('.panel-card') || el)).asElement().screenshot({ path: join(OUT, 'vessels.png') });
  const rows = (active && active.rows) || [];
  if (rows.length) {
    record('RND-03', rows.every((row) => vesselsText.includes(row.vessel_id)), `rows ${rows.map((row) => row.vessel_id).join(',')}; monitoring ${active.monitoring}`);
  } else {
    record('RND-03', false, 'no risk rows to inspect - run with --setup');
  }
  const overdueMarkers = await page.$$eval('.overdue-marker-dot', (dots) => dots.length);
  const sampleNames = ['San Pedro', 'Maria Gracia', 'Sta. Maria', 'V-002', 'V-005'].filter((name) => vesselsText.includes(name));
  record('RND-04', overdueMarkers === 0 && sampleNames.length === 0, { overdueMarkers, sampleNames });

  // Drift cases: every case in the selector, map and card.
  const incidents = await pageApi(page, '/api/ai/drift/incidents');
  const map = await page.$('.leaflet-container');
  const card = await page.$('#drift-card');
  const drift = [];
  for (const incident of (Array.isArray(incidents) ? incidents : []).slice(0, 12)) {
    await page.selectOption('#ai-drift-select', String(incident.id));
    await page.waitForTimeout(3500);
    await map.screenshot({ path: join(OUT, `drift-map-${incident.id}.png`) });
    await card.scrollIntoViewIfNeeded();
    await card.screenshot({ path: join(OUT, `drift-card-${incident.id}.png`) });
    const meta = await page.$eval('#ai-drift-meta', (el) => el.innerText);
    const paths = await page.$$eval('.leaflet-aiContours-pane path', (els) => els.length);
    const legendRows = await page.$$eval('#ai-map-key .ai-map-key-row', (els) => els.filter((el) => el.offsetParent !== null).length).catch(() => 0);
    const legendVisible = await page.$eval('#ai-map-key', (el) => el.offsetParent !== null).catch(() => false);
    drift.push({ id: incident.id, synthetic: incident.is_synthetic, source: incident.source_type, paths, legendVisible, legendRows, meta: meta.replace(/\n/g, ' | ') });
  }
  writeFileSync(join(OUT, 'drift.json'), JSON.stringify(drift, null, 2));
  const drawn = drift.filter((entry) => entry.paths > 0);
  record('RND-06', drawn.length > 0 && drawn.every((entry) => entry.legendVisible && entry.legendRows > 0)
    && drift.filter((entry) => entry.paths === 0).every((entry) => !entry.legendVisible),
  drift.map((entry) => `${entry.id}:${entry.paths}p/${entry.legendRows}r`).join(' '));
  record('RND-11a', drift.length > 0 && drift.every((entry) => !/insufficient_[a-z_]+/.test(entry.meta)), drift.map((entry) => entry.meta.slice(0, 80)).join(' || '));

  // RND-05: the replay badge is readable in both themes.
  const synthetic = drift.find((entry) => entry.synthetic);
  if (synthetic) {
    await page.selectOption('#ai-drift-select', String(synthetic.id));
    await page.waitForTimeout(3500);
    const ratios = {};
    for (const theme of ['light', 'dark']) {
      await page.evaluate((t) => {
        if (t === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
        else document.documentElement.removeAttribute('data-theme');
      }, theme);
      await page.waitForTimeout(300);
      const colors = await colorsOf(page, '.drift-replay-badge');
      ratios[theme] = Math.round(contrast(colors.color, colors.layers) * 100) / 100;
      await card.screenshot({ path: join(OUT, `replay-badge-${theme}.png`) });
    }
    await page.evaluate(() => document.documentElement.removeAttribute('data-theme'));
    record('RND-05', ratios.light >= 4.5 && ratios.dark >= 4.5, ratios);

    // RND-07: nested, distinct rings and the replay horizon.
    const payload = await pageApi(page, `/api/ai/drift/incident/${synthetic.id}?forecast_hours=24`);
    const rings = (payload.contours || []).map((contour) => JSON.stringify(contour.geometry.coordinates));
    const track = payload.ground_truth_track || [];
    const expectedHours = track.length > 1 ? (track.length - 1) * 0.5 : null;
    record('RND-07', rings.length === 3 && new Set(rings).size === 3 && payload.forecast_hours === expectedHours,
      { distinctRings: new Set(rings).size, forecast_hours: payload.forecast_hours, expectedHours });
  } else {
    record('RND-05', false, 'no synthetic replay in the selector');
    record('RND-07', false, 'no synthetic replay in the selector');
  }

  // RND-10: an escalated trip check offers "Open drift case".
  await page.click('.stats-tab[data-tab="tripchecks"]').catch(() => {});
  await page.waitForTimeout(500);
  const openButtons = await page.$$eval('[data-case-action="open-drift"]', (els) => els.length).catch(() => 0);
  record('RND-10', openButtons > 0, `open-drift buttons: ${openButtons}`);

  record('console', consoleErrors.length === 0, consoleErrors.slice(0, 8));
  writeFileSync(join(OUT, 'report.json'), JSON.stringify(results, null, 2));
  await browser.close();

  const failed = REQUIRED.filter((id) => !(results[id] && results[id].ok));
  if (failed.length) {
    console.error(`required checks failed: ${failed.join(', ')}`);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
