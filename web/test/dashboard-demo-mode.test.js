'use strict';

// node --test web/test/dashboard-demo-mode.test.js
//
// docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md: the live dashboard shows
// only what the backend reports, and sample data lives only in the tutorial.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const {
  networkFromPublicBuoys, meshLinksFor, phoneCoverageFraction, buoyHeardText
} = require('../js/dashboard-utils.js');

const NOW = Date.parse('2026-09-27T08:00:00Z');

function buoy(overrides) {
  return Object.assign({
    id: 'B01', name: 'Buoy 01', latitude: 11.67, longitude: 122.46,
    coverage_radius_meters: 1300, lora_radius_meters: 7000, is_gateway_linked: true,
    is_synthetic: true, last_heard_at: '2026-09-27T07:55:00Z', status: 'active'
  }, overrides);
}

test('the network keeps an unplaced buoy listed but never places it', () => {
  const network = networkFromPublicBuoys({
    buoys: [buoy(), buoy({ id: 'BUOY01', name: 'BUOY01', latitude: null, longitude: null, coverage_radius_meters: null, status: 'unknown' })],
    shore_stations: [{ name: 'Dumaguit Port', lat: 11.67, lon: 122.41, type: 'Port Facility', role: 'Shore gateway' }]
  });
  assert.equal(network.buoys.length, 2);
  assert.deepEqual([network.buoys[1].lat, network.buoys[1].lng, network.buoys[1].wifiRadius], [null, null, null]);
  assert.equal(network.buoys[0].isSynthetic, true);
  assert.deepEqual(network.stations[0], { name: 'Dumaguit Port', lat: 11.67, lng: 122.41, type: 'Port Facility', role: 'Shore gateway' });
  assert.deepEqual(networkFromPublicBuoys(null), { buoys: [], stations: [] });
});

test('mesh links follow the LoRa ranges of placed buoys only', () => {
  const { buoys, stations } = networkFromPublicBuoys({
    buoys: [buoy(), buoy({ id: 'B02', latitude: 11.70, longitude: 122.46 }), buoy({ id: 'far', latitude: 12.5, longitude: 123.5 }),
      buoy({ id: 'unplaced', latitude: null, longitude: null })],
    shore_stations: [{ name: 'Hall', lat: 11.66, lon: 122.43 }]
  });
  const names = meshLinksFor(buoys, stations).map(([a, b]) => (a.id || a.name) + '-' + (b.id || b.name));
  assert.deepEqual(names, ['B01-B02', 'B01-Hall', 'B02-Hall']);
});

test('phone coverage is measured from the buoys, not invented', () => {
  const ring = [[11.60, 122.40], [11.60, 122.50], [11.70, 122.50], [11.70, 122.40], [11.60, 122.40]];
  assert.equal(phoneCoverageFraction(ring, []), null);
  const { buoys } = networkFromPublicBuoys({ buoys: [buoy({ latitude: 11.65, longitude: 122.45, coverage_radius_meters: 1000 })] });
  const share = phoneCoverageFraction(ring, buoys);
  // A 1 km circle in an 11 x 11 km square is about 2.6% of it.
  assert.ok(share > 0.015 && share < 0.04, String(share));
});

test('a buoy says when it was last heard', () => {
  assert.equal(buoyHeardText({ status: 'active', lastHeardAt: '2026-09-27T07:55:00Z' }, NOW), 'Heard 5 min ago');
  assert.equal(buoyHeardText({ status: 'silent', lastHeardAt: '2026-09-27T05:00:00Z' }, NOW), 'Silent, last heard 3 h ago');
  assert.equal(buoyHeardText({ status: 'unknown', lastHeardAt: null }, NOW), 'Never heard');
});

test('DEMO-07: the live dashboard source carries no sample network or figures', () => {
  const files = ['html/dashboard.html', 'js/dashboard/dashboard-core.js', 'js/dashboard/dashboard-markers.js',
    'js/dashboard/dashboard-buoy-health.js', 'js/dashboard/dashboard-sar.js'];
  const banned = ['Buoy Alpha', 'Buoy Echo', 'Squall Watch', 'Math.max(4', "'45 min'", '(68 +', 'Displaying sample data',
    'Sample buoy network', 'sample data for demonstration', 'initialBuoys', 'incidentDrawerData', '(simulated)'];
  for (const file of files) {
    const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    for (const text of banned) assert.ok(!source.includes(text), `${file} still contains ${text}`);
  }
});

// ===== Tutorial source =====

const tutorial = require('../js/tutorial/tutorial-source.js');

const ORIGIN = 'https://aqone.example';
function recording() {
  return {
    recorded_at: '2026-09-27T06:00:00Z',
    phases: [
      {
        label: 'start',
        responses: {
          'GET /api/sos/active?limit=200': { status: 200, body: { events: [] } },
          'GET /api/ai/drift/cases': { status: 200, body: [{ id: 3, opened_at: '2026-09-27T05:48:00+00:00' }] }
        }
      },
      {
        label: 'sos-arrives',
        trigger: { cue: 'sos-arrives' },
        responses: { 'GET /api/sos/active?limit=200': { status: 200, body: { events: [{ id: 12, acknowledged_at: null }] } } }
      },
      {
        label: 'acknowledged',
        trigger: { request: 'POST /api/sos/12/acknowledge', reply: { status: 200, body: { id: 12, version: 2 } } },
        responses: {
          'GET /api/sos/active?limit=200': { status: 200, body: { events: [{ id: 12, acknowledged_at: '2026-09-27T06:01:00Z' }] } },
          'GET /api/ai/drift/cases/3': { status: 200, body: { id: 3 } }
        }
      }
    ]
  };
}

async function json(promise) {
  const res = await promise;
  return { status: res.status, body: await res.json() };
}

test('DEMO-06: recorded times move to the moment the lesson opens', () => {
  const delta = 2 * 3600 * 1000;
  const shifted = tutorial.shiftTimes({
    a: '2026-09-27T06:00:00Z', b: '2026-09-27T05:48:00.5+00:00', c: '2026-09-27T06:00', d: '2026-09-26', e: 'not a time', f: [5]
  }, delta);
  assert.equal(shifted.a, '2026-09-27T08:00:00.000Z');
  assert.equal(shifted.b, '2026-09-27T07:48:00.500Z');
  assert.equal(shifted.c, '2026-09-27T08:00');
  assert.equal(shifted.d, '2026-09-26');
  assert.equal(shifted.e, 'not a time');
  assert.deepEqual(shifted.f, [5]);
});

test('the source answers what the dashboard asked, from the current phase', async () => {
  const source = tutorial.createSource(recording(), { origin: ORIGIN, now: Date.parse('2026-09-27T08:00:00Z') });
  assert.deepEqual((await json(source.fetch('/api/sos/active?limit=200'))).body, { events: [] });
  assert.deepEqual((await json(source.fetch(ORIGIN + '/api/sos/active?limit=50'))).body, { events: [] }, 'same path, other query');
  const cases = await json(source.fetch('/api/ai/drift/cases'));
  assert.equal(cases.body[0].opened_at, '2026-09-27T07:48:00.000Z');
  assert.equal((await json(source.fetch('/api/unknown'))).status, 404);
});

test('a cue and an action move the lesson forward; unrecorded actions are refused', async () => {
  const refused = [];
  const source = tutorial.createSource(recording(), { origin: ORIGIN, onRefusal: (key) => refused.push(key) });
  assert.equal(source.cue('sos-arrives'), true);
  assert.equal((await json(source.fetch('/api/sos/active?limit=200'))).body.events[0].acknowledged_at, null);

  const ack = await json(source.fetch('/api/sos/12/acknowledge', { method: 'POST', body: '{}' }));
  assert.deepEqual(ack, { status: 200, body: { id: 12, version: 2 } });
  assert.equal(source.phase(), 'acknowledged');
  assert.ok((await json(source.fetch('/api/sos/active?limit=200'))).body.events[0].acknowledged_at);

  const resolve = await json(source.fetch('/api/sos/12/resolve', { method: 'POST' }));
  assert.equal(resolve.status, 409);
  assert.deepEqual(refused, ['POST /api/sos/12/resolve']);
  assert.equal(source.cue('sos-arrives'), false, 'a cue never moves back');
});

test('a detail recorded after an action is still served before it', async () => {
  const source = tutorial.createSource(recording(), { origin: ORIGIN });
  assert.deepEqual((await json(source.fetch('/api/ai/drift/cases/3'))).body, { id: 3 });
});

test('DEMO-01: only the tab session switches the tutorial on, never a URL', () => {
  const store = (entries) => ({ getItem: (key) => (key in entries ? entries[key] : null) });
  assert.equal(tutorial.activeLesson(store({})), null);
  assert.equal(tutorial.activeLesson(store({ aqoneDashboardMode: 'tutorial', aqoneTutorialLesson: 'sos' })), 'sos');
  assert.equal(tutorial.activeLesson(store({ aqoneDashboardMode: 'tutorial', aqoneTutorialLesson: '../secrets' })), null);
  const source = fs.readFileSync(path.join(__dirname, '../js/tutorial/tutorial-source.js'), 'utf8');
  assert.ok(!/location\.(search|hash)|URLSearchParams/.test(source), 'the mode must not be read from the URL');
});

// ===== Lessons and recordings =====

const lessons = require('../js/tutorial/tutorial-lessons.js');
const WEB = path.join(__dirname, '..');
const dashboardHtml = fs.readFileSync(path.join(WEB, 'html/dashboard.html'), 'utf8');
const dashboardJs = fs.readdirSync(path.join(WEB, 'js/dashboard'))
  .map((file) => fs.readFileSync(path.join(WEB, 'js/dashboard', file), 'utf8')).join('\n') +
  fs.readFileSync(path.join(WEB, 'js/dashboard-utils.js'), 'utf8');

function recordingOf(id) {
  return JSON.parse(fs.readFileSync(path.join(WEB, 'data/tutorial', id + '.json'), 'utf8'));
}

// The first #id or .class of a selector must exist in the page or be drawn by
// its scripts, or a step would highlight nothing.
function anchorExists(selector) {
  const anchor = selector.match(/[#.][A-Za-z][\w-]*/)[0];
  return anchor[0] === '#'
    ? dashboardHtml.includes(`id="${anchor.slice(1)}"`)
    : dashboardHtml.includes(anchor.slice(1)) || dashboardJs.includes(anchor.slice(1));
}

test('every lesson has a recording, and every step points at something real', () => {
  assert.equal(new Set(lessons.map((l) => l.id)).size, lessons.length);
  for (const lesson of lessons) {
    const recording = recordingOf(lesson.id);
    assert.ok(Date.parse(recording.recorded_at), `${lesson.id}: recorded_at`);
    const labels = recording.phases.map((phase) => phase.label);
    assert.equal(labels[0], 'start');
    for (const step of lesson.steps) {
      if (step.target) assert.ok(anchorExists(step.target), `${lesson.id}: ${step.target}`);
      for (const action of step.before || []) {
        const selector = action.click || `.stats-tab[data-tab="${action.tab}"]`;
        assert.ok(anchorExists(selector), `${lesson.id}: before ${selector}`);
        if (action.tab) assert.ok(dashboardHtml.includes(`data-tab="${action.tab}"`), `${lesson.id}: tab ${action.tab}`);
      }
      // DEMO-05: an action the lesson asks for was recorded, so it replays.
      if (step.waitFor) assert.ok(labels.some((label) => new RegExp(step.waitFor).test(label)), `${lesson.id}: ${step.waitFor} in ${labels}`);
      if (step.cue) assert.ok(recording.phases.some((phase) => phase.trigger && phase.trigger.cue === step.cue), `${lesson.id}: cue ${step.cue}`);
    }
  }
});

test('DEMO-04: the recordings fill every panel the lessons talk about', () => {
  const seen = new Set();
  for (const lesson of lessons) {
    for (const phase of recordingOf(lesson.id).phases) {
      Object.keys(phase.responses).forEach((key) => seen.add(key.split('?')[0]));
    }
  }
  for (const route of ['GET /api/sos/active', 'GET /api/sos/recent', 'GET /api/public/buoys', 'GET /api/ai/squall/current',
    'GET /api/ai/anomaly/active', 'GET /api/ai/anomaly/cases/open', 'GET /api/ai/drift/incidents', 'GET /api/sea-condition',
    'GET /api/advisories', 'GET /api/ops/status', 'GET /api/ai/metrics', 'GET /api/public/hotspots', 'GET /api/demo/weather/forecast']) {
    assert.ok(seen.has(route), `no recording answers ${route}`);
  }
});

test('DEMO-08: recordings carry no real contact details', () => {
  for (const lesson of lessons) {
    const text = fs.readFileSync(path.join(WEB, 'data/tutorial', lesson.id + '.json'), 'utf8');
    for (const email of text.match(/[\w.+-]+@[\w-]+(\.[\w-]+)+/g) || []) {
      assert.match(email, /@example\.(com|org)$/, `${lesson.id}: ${email}`);
    }
    assert.ok(!/(\+63|\b09)\d{9}\b/.test(text), `${lesson.id}: a phone number`);
  }
});

test('DEMO-02 and DEMO-03: the data source loads first and the watermark covers everything', () => {
  const firstScript = dashboardHtml.match(/<script src="([^"]+)"/)[1];
  assert.equal(firstScript, '../js/tutorial/tutorial-source.js');
  const css = fs.readFileSync(path.join(WEB, 'css/tutorial.css'), 'utf8');
  const watermark = css.match(/\.tutorial-watermark \{([^}]*)\}/)[1];
  assert.match(watermark, /pointer-events: none/);
  const top = Number(watermark.match(/z-index: (\d+)/)[1]);
  const dashboardCss = fs.readFileSync(path.join(WEB, 'css/dashboard.css'), 'utf8');
  const highest = Math.max(...(dashboardCss.match(/z-index: \d+/g) || []).map((z) => Number(z.slice(9))));
  assert.ok(top > highest, `watermark z-index ${top} must exceed the dashboard's ${highest}`);
});
