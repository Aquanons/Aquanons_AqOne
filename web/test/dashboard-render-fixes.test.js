'use strict';

// node --test web/test/dashboard-render-fixes.test.js
//
// docs/71_DASHBOARD_DRIFT_TRIP_RENDER_FIXES_IMPLEMENTATION_PLAN.md: the pure
// renderers behind the Trip Checks tab, the vessel risk feed and the drift
// card, exercised without a DOM.

const test = require('node:test');
const assert = require('node:assert/strict');

const { tripCheckRowHtml, riskFeedHtml } = require('../js/dashboard-utils.js');

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
  const fs = require('node:fs');
  const path = require('node:path');
  const files = ['js/dashboard/dashboard-vessels-alerts.js', 'js/dashboard/dashboard-core.js', 'js/dashboard/dashboard-markers.js', 'html/dashboard.html'];
  for (const file of files) {
    const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    for (const name of ['San Pedro', 'Maria Gracia', 'Sta. Maria', 'Birhen sa Regla', 'Sto. Nino', 'V-002', 'V-005', 'vessel-filters']) {
      assert.ok(!source.includes(name), `${file} still contains ${name}`);
    }
  }
});
