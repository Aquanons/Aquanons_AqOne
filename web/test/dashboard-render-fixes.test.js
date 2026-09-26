'use strict';

// node --test web/test/dashboard-render-fixes.test.js
//
// docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md: the pure
// renderers behind the Trip Checks tab, the vessel risk feed and the drift
// card, exercised without a DOM.

const test = require('node:test');
const assert = require('node:assert/strict');

const fs = require('node:fs');
const path = require('node:path');
const { tripCheckRowHtml, riskFeedHtml, driftLegendItems, driftLegendHtml, insufficiencyText, DRIFT_COLORS } = require('../js/dashboard-utils.js');

// The docs/05 "Factor object" example.
const OVERDUE = { code: 'overdue', value: 1.0, weight: 0.85, contribution: 0.85, description: 'Late beyond the expected-contact window.' };
const WEATHER = { code: 'weather', value: 0.2, weight: 0.02, contribution: 0.004, description: 'Adverse weather at the last known position/time.' };

function riskRow(overrides) {
  return Object.assign({
    vessel_id: 'V001', trip_id: 'T1', score: 0.98, status: 'alert', factors: [WEATHER, OVERDUE],
    expected_next_buoy_id: 'B06', last_contact_at: '2026-09-26T11:08:00Z', source: 'live'
  }, overrides);
}

test('RND-02: a trip check names its largest factor', () => {
  const html = tripCheckRowHtml({ id: 1, vessel_id: 'V001', case_type: 'responder_attention', score: 0.98, reasons: [WEATHER, OVERDUE], source: 'live' });
  assert.ok(html.includes('Late beyond the expected-contact window.'));
  assert.ok(!html.includes('No reason recorded'));
});

test('RND-02: the risk feed prints each factor code and description', () => {
  const { html, count } = riskFeedHtml([riskRow()], { freshness: 'live', monitoring: 'active' });
  assert.equal(count, '1');
  assert.ok(html.includes('>overdue<'));
  assert.ok(html.includes('Late beyond the expected-contact window.'));
  assert.ok(html.includes('>weather<'));
});

test('the risk feed escapes server text', () => {
  const { html } = riskFeedHtml([riskRow({ vessel_id: '<img src=x>', factors: [{ code: 'x', contribution: 1, description: '<b>' }] })], { freshness: 'live', monitoring: 'active' });
  assert.ok(!html.includes('<img src=x>'));
  assert.ok(!html.includes('<b>'));
});

test('the risk feed orders by status then score, check_needed with the urgent rows', () => {
  const { html } = riskFeedHtml([
    riskRow({ vessel_id: 'NORMAL', status: 'normal', score: 0.1 }),
    riskRow({ vessel_id: 'CHECK', status: 'check_needed', score: 0.5 }),
    riskRow({ vessel_id: 'ALERT', status: 'alert', score: 0.9 })
  ], { freshness: 'live', monitoring: 'active' });
  assert.ok(html.indexOf('ALERT') < html.indexOf('CHECK'));
  assert.ok(html.indexOf('CHECK') < html.indexOf('NORMAL'));
  assert.ok(html.includes('CHECK NEEDED'));
});

test('an unreachable feed says so rather than looking calm', () => {
  assert.ok(riskFeedHtml(null, { freshness: 'offline' }).html.includes('unavailable'));
  assert.equal(riskFeedHtml([], { freshness: 'live', monitoring: 'active' }).count, '0');
});

test('RND-03: while not monitoring, scored rows still show under the notice', () => {
  const { html, count } = riskFeedHtml([riskRow({ source: 'synthetic' })], { freshness: 'live', monitoring: 'unavailable' });
  assert.ok(html.includes('Not monitoring - no live contact source'));
  assert.ok(html.includes('V001'));
  assert.ok(html.indexOf('Not monitoring') < html.indexOf('V001'));
  assert.equal(count, '1');
});

test('RND-03: with no rows, not monitoring shows the notice alone', () => {
  const { html, count } = riskFeedHtml([], { freshness: 'live', monitoring: 'unavailable' });
  assert.ok(html.includes('Not monitoring - no live contact source'));
  assert.ok(!html.includes('ai-risk-item'));
  assert.equal(count, '--');
});

test('RND-03: a synthetic row carries the DEMO badge and a live row does not', () => {
  const state = { freshness: 'live', monitoring: 'active' };
  assert.ok(riskFeedHtml([riskRow({ source: 'synthetic' })], state).html.includes('<span class="alert-demo-badge">DEMO</span>'));
  assert.ok(!riskFeedHtml([riskRow({ source: 'live' })], state).html.includes('alert-demo-badge'));
});

test('RND-04: the Vessels badge counts rows that are not normal', () => {
  const { attention } = riskFeedHtml([
    riskRow({ status: 'alert' }), riskRow({ status: 'check_needed' }), riskRow({ status: 'normal' })
  ], { freshness: 'live', monitoring: 'active' });
  assert.equal(attention, '2');
  assert.equal(riskFeedHtml(null, { freshness: 'offline' }).attention, '--');
});

test('RND-04: no sample vessel ships in the dashboard source', () => {
  const files = ['js/dashboard/dashboard-vessels-alerts.js', 'js/dashboard/dashboard-core.js', 'js/dashboard/dashboard-markers.js', 'html/dashboard.html'];
  for (const file of files) {
    const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    for (const name of ['San Pedro', 'Maria Gracia', 'Sta. Maria', 'Birhen sa Regla', 'Sto. Nino', 'V-002', 'V-005', 'vessel-filters']) {
      assert.ok(!source.includes(name), `${file} still contains ${name}`);
    }
  }
});

function ring(mass) {
  return { type: 'Feature', properties: { mass: mass }, geometry: { type: 'Polygon', coordinates: [[[122.5, 11.7], [122.6, 11.7], [122.6, 11.8], [122.5, 11.7]]] } };
}
const ORIGIN = { origin: { lat: 11.7, lon: 122.5 } };

test('RND-06: an ok case lists its rings and the next area, in the map colors', () => {
  const items = driftLegendItems({
    environmental_status: 'ok', contours: [ring(0.5), ring(0.75), ring(0.95)],
    posterior_grid: ORIGIN, next_area: { bounds: { south: 1, west: 1, north: 2, east: 2 } }, search_sectors: []
  });
  assert.deepEqual(items.map((item) => item.key), ['contour95', 'contour75', 'contour50', 'nextArea']);
  assert.equal(items[0].color, DRIFT_COLORS.contour95);
  assert.equal(items[3].color, DRIFT_COLORS.nextArea);
});

test('RND-06: a synthetic replay adds its ground-truth track, and sectors add the searched area', () => {
  const items = driftLegendItems({
    contours: [ring(0.95)], posterior_grid: ORIGIN,
    ground_truth_track: [{ lat: 11.7, lon: 122.5 }, { lat: 11.71, lon: 122.51 }],
    search_sectors: [{ x_min_m: 0, x_max_m: 1, y_min_m: 0, y_max_m: 1 }]
  });
  assert.deepEqual(items.map((item) => item.key), ['contour95', 'searched', 'track']);
});

test('RND-06: an insufficient case or no contours has no legend', () => {
  assert.deepEqual(driftLegendItems({ environmental_status: 'insufficient_environmental_data', contours: [] }), []);
  assert.deepEqual(driftLegendItems(null), []);
  assert.equal(driftLegendHtml([]), '');
});

test('RND-06: the legend html escapes labels and draws each chip in its color', () => {
  const html = driftLegendHtml([{ key: 'contour95', label: '95% search area', color: '#ef4444', dashed: true }]);
  assert.ok(html.includes('95% search area'));
  assert.ok(html.includes('border-color:#ef4444'));
  assert.ok(html.includes('dashed'));
});

test('RND-11: every insufficiency code the backend emits reads as a sentence', () => {
  const source = fs.readFileSync(path.join(__dirname, '../../backend/app/ai/environment.py'), 'utf8');
  const codes = [...source.matchAll(/^(?:INSUFFICIENT|DEGRADED)_[A-Z_]+ = '([a-z_]+)'/gm)].map((match) => match[1]);
  assert.ok(codes.length >= 3);
  for (const code of codes) {
    const text = insufficiencyText(code);
    assert.notEqual(text, code, code);
    assert.ok(/^[A-Z].*\.$/.test(text), text);
  }
  assert.equal(insufficiencyText('something_new'), 'something_new');
  assert.equal(insufficiencyText(null), 'Reason not recorded.');
});

test('RND-11: the drift card prints the sentence, not the code', () => {
  const source = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
  assert.ok(source.includes('insufficiencyText(payload.insufficiency_reason)'));
});
