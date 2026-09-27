// Records the dashboard tutorial's lessons (docs/72).
//
// Drives the real dashboard in headless Edge against a disposable backend
// running the presenter scenario, does each lesson's actions through the UI,
// and saves every API response the dashboard saw as web/data/tutorial/<id>.json.
// The tutorial replays these files, so lessons show what the real backend
// answered instead of hand-written samples. Setup: tools/render-check/README.md.

import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const option = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
};

const BASE = process.env.AQONE_BASE || 'http://localhost:8765';
const DEMO_KEY = process.env.AQONE_DEMO_KEY || 'demo';
const SETUP_KEY = process.env.AQONE_SETUP_KEY || 'setup';
const EMAIL = 'duty.officer@example.com';
const PASSWORD = 'tutorial-recording-only';
const OUT = resolve(option('--out', '../../web/data/tutorial'));
const SETTLE_MS = 9000;

// Never replayed: session plumbing and the presenter's own controls.
const SKIPPED = [/^\/api\/token\//, /^\/api\/login/, /^\/api\/demo\/(?!weather\/)/];

async function api(path, { method = 'GET', token, body, demo } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (demo) headers['X-Demo-Key'] = DEMO_KEY;
  const res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { json = text; }
  if (res.status >= 400) throw new Error(`${method} ${path}: ${res.status} ${text.slice(0, 200)}`);
  return json;
}

async function login() {
  try {
    await api('/api/admin-signup', {
      method: 'POST', body: { setup_key: SETUP_KEY, email: EMAIL, password: PASSWORD, full_name: 'Duty Officer' }
    });
  } catch (error) {
    if (!String(error.message).includes('409')) console.log('signup:', error.message);
  }
  const session = await api('/api/login', { method: 'POST', body: { email: EMAIL, password: PASSWORD } });
  return { token: session.token || session.access_token, user: session.user };
}

// One lesson's recording: phases of responses, each after an action or cue.
function recorder() {
  const phases = [{ label: 'start', responses: {} }];
  const pending = new Set();
  return {
    phases,
    cue(name) { phases.push({ label: name, trigger: { cue: name }, responses: {} }); },
    async take(response) {
      const url = new URL(response.url());
      const local = url.origin === BASE;
      if (local && (!url.pathname.startsWith('/api/') || SKIPPED.some((re) => re.test(url.pathname)))) return;
      if (!local && !url.hostname.endsWith('open-meteo.com')) return;
      const method = response.request().method();
      const key = `${method} ${local ? url.pathname + url.search : url.origin + url.pathname + url.search}`;
      const job = (async () => {
        let entry;
        const type = response.headers()['content-type'] || '';
        const text = await response.text().catch(() => null);
        if (text == null) return;
        if (type.includes('json')) {
          try { entry = { status: response.status(), body: JSON.parse(text) }; } catch { entry = { status: response.status(), text, type }; }
        } else {
          entry = { status: response.status(), text, type };
        }
        if (method === 'GET') {
          phases[phases.length - 1].responses[key] = entry;
        } else {
          phases.push({ label: key.split('?')[0], trigger: { request: key.split('?')[0], reply: entry }, responses: {} });
        }
      })();
      pending.add(job);
      await job;
      pending.delete(job);
    },
    async flush() { await Promise.all([...pending]); }
  };
}

const LESSONS = [
  {
    id: 'console',
    async prepare() {
      await api('/api/demo/scenario/squall-fleet/start', { method: 'POST', demo: true });
    },
    async act(page) {
      await page.click('#rail-btn-buoy');
      await page.waitForTimeout(1500);
    }
  },
  {
    id: 'squall',
    async prepare() {
      await api('/api/demo/beat/1', { method: 'POST', demo: true });
      await api('/api/demo/beat/2', { method: 'POST', demo: true });
    },
    async act(page) {
      await page.click('#danger-zone-refresh').catch(() => {});
      await page.waitForTimeout(3000);
    }
  },
  {
    id: 'warn',
    async prepare() {
      await api('/api/demo/beat/3', { method: 'POST', demo: true });
    },
    async act(page) {
      await page.click('#rail-btn-advisories');
      await page.waitForTimeout(2000);
      await page.click('#advisory-panel-close').catch(() => {});
      await page.click('.sea-condition-btn.btn-danger');
      await page.fill('#sea-condition-reason', 'Squall front approaching from the west');
      page.once('dialog', (dialog) => dialog.accept());
      await page.click('#sea-condition-set-btn');
      await page.waitForTimeout(3000);
    }
  },
  {
    id: 'trip-checks',
    async prepare(ctx) {
      await api('/api/demo/beat/4', { method: 'POST', demo: true });
      await api('/api/ai/anomaly/evaluate', { method: 'POST', token: ctx.token });
    },
    async act(page) {
      await page.click('.stats-tab[data-tab="vessels"]');
      await page.waitForTimeout(1200);
      await page.click('.stats-tab[data-tab="tripchecks"]');
      await page.waitForSelector('#trip-checks-list [data-case-action="acknowledge"]', { timeout: 20000 });
      await page.click('#trip-checks-list [data-case-action="activity"]');
      await page.waitForTimeout(1500);
      await page.click('#activity-drawer-close');
      await page.click('#trip-checks-list [data-case-action="acknowledge"]');
      await page.waitForTimeout(2500);
      page.once('dialog', (dialog) => dialog.accept('No contact for three hours and a squall is due'));
      await page.click('#trip-checks-list [data-case-action="escalate"]');
      await page.waitForTimeout(3000);
    }
  },
  {
    id: 'sos',
    async act(page, rec) {
      await page.waitForTimeout(2000);
      rec.cue('sos-arrives');
      await api('/api/demo/beat/5', { method: 'POST', demo: true });
      await page.waitForSelector('.live-sos-marker', { timeout: 20000 });
      await page.waitForTimeout(4000);
      await page.click('.stats-tab[data-tab="alerts"]');
      await page.click('#alert-list .alert-row');
      await page.waitForTimeout(1200);
      await page.click('#sos-btn-activity');
      await page.waitForTimeout(1500);
      await page.click('#activity-drawer-close');
      await page.click('#sos-btn-acknowledge');
      await page.selectOption('#ack-status', { index: 1 });
      await page.fill('#ack-eta', '25');
      await page.fill('#ack-note', 'Rescue boat leaving now');
      await page.click('#ack-btn-confirm');
      await page.waitForTimeout(4000);
    }
  },
  {
    id: 'drift',
    async act(page) {
      await page.click('.stats-tab[data-tab="alerts"]');
      await page.click('#alert-list .alert-row');
      await page.waitForSelector('#sos-btn-open-drift:not([hidden])', { timeout: 20000 });
      await page.click('#sos-btn-open-drift');
      await page.selectOption('#drift-open-class', 'person_in_water').catch(() => {});
      await page.click('#drift-open-confirm');
      await page.waitForSelector('#ai-drift-search [data-action="start-search"]', { timeout: 60000 });
      await page.click('#sos-drawer-close').catch(() => {});
      await page.waitForTimeout(2000);
      await page.click('#ai-drift-search [data-action="start-search"]');
      const box = await page.locator('#map').boundingBox();
      await page.mouse.click(box.x + box.width * 0.45, box.y + box.height * 0.42);
      await page.waitForTimeout(400);
      await page.mouse.click(box.x + box.width * 0.55, box.y + box.height * 0.58);
      await page.waitForSelector('#ai-drift-search [data-action="submit-search"]', { timeout: 10000 });
      await page.click('#ai-drift-search [data-action="submit-search"]');
      await page.waitForTimeout(6000);
      await page.click('#ai-drift-search [data-action="rerun-case"]');
      await page.waitForTimeout(8000);
    }
  },
  {
    id: 'close-out',
    async act(page) {
      await page.click('.stats-tab[data-tab="alerts"]');
      await page.click('#alert-list .alert-row');
      await page.waitForTimeout(1200);
      await page.click('#sos-btn-resolve');
      await page.check('input[name="resolve-reason"][value="rescued"]');
      await page.click('#resolve-btn-confirm');
      await page.waitForTimeout(4000);
      await page.click('.stats-tab[data-tab="sar"]');
      await page.waitForTimeout(2000);
    }
  }
];

async function main() {
  mkdirSync(OUT, { recursive: true });
  const session = await login();
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const only = option('--only', null);
  try {
    for (const lesson of LESSONS) {
      if (lesson.prepare) await lesson.prepare(session);
      if (only && only !== lesson.id) continue;
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      await context.addInitScript(([token, user]) => {
        sessionStorage.setItem('aqoneToken', token);
        sessionStorage.setItem('aqoneUser', JSON.stringify(user));
        window.AQONE_WEATHER_BASE = '/api/demo/weather/forecast';
        window.AQONE_MARINE_BASE = '/api/demo/weather/marine';
      }, [session.token, session.user]);
      // The live squall routes read live readings only; the scenario's are
      // served by the demo router, under the path the dashboard requests.
      await context.route(/\/api\/ai\/squall\/(current|buoy\/[^/?]+)/, async (route) => {
        const path = new URL(route.request().url()).pathname.replace('/api/ai/squall/current', '/api/demo/squall')
          .replace('/api/ai/squall/buoy/', '/api/demo/squall/buoy/');
        const res = await fetch(BASE + path, { headers: { 'X-Demo-Key': DEMO_KEY } });
        await route.fulfill({ status: res.status, contentType: 'application/json', body: await res.text() });
      });
      // The open-case form has no horizon field, and the story's SOS was
      // pressed three hours before it arrived: a 24 h run from then is mostly
      // unobserved future and fails the current-coverage gate. Four hours
      // keeps the run observed and its forecast open past the recording.
      await context.route(/\/api\/ai\/drift\/cases$/, async (route) => {
        const request = route.request();
        if (request.method() !== 'POST') return route.continue();
        const body = Object.assign(JSON.parse(request.postData() || '{}'), { forecast_hours: 4 });
        await route.continue({ postData: JSON.stringify(body) });
      });
      const page = await context.newPage();
      const rec = recorder();
      page.on('response', (response) => { rec.take(response); });
      page.on('pageerror', (error) => console.log(`[${lesson.id}] pageerror: ${error.message}`));
      const recordedAt = new Date().toISOString();
      await page.goto(`${BASE}/html/dashboard.html`);
      await page.waitForTimeout(SETTLE_MS);
      await lesson.act(page, rec);
      await page.waitForTimeout(2000);
      await rec.flush();
      await context.close();
      const file = join(OUT, `${lesson.id}.json`);
      writeFileSync(file, JSON.stringify({ lesson: lesson.id, recorded_at: recordedAt, phases: rec.phases }) + '\n');
      const counts = rec.phases.map((phase) => `${phase.label}:${Object.keys(phase.responses).length}`).join(' ');
      console.log(`${lesson.id}: ${counts}`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
