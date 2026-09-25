'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { escapeHtml, lateLabel, flagLabel, deliveryLabel } = require('../js/dashboard-utils.js');

function element(id) {
  return { id, hidden: false, textContent: '', classList: { toggle() {}, add() {}, remove() {} } };
}

async function loadFeed(payload) {
  const elements = new Map();
  const tooltips = [];
  const markers = [];
  const document = {
    title: 'AqOne',
    getElementById(id) { if (!elements.has(id)) elements.set(id, element(id)); return elements.get(id); },
    querySelector() { return null; }
  };
  const map = { setView() {} };
  const layer = { addTo() { return this; }, addLayer() {}, removeLayer() {} };
  const ns = {
    ready: true, liveAlerts: [], escapeHtml, formatLatLon: require('../js/dashboard-utils.js').formatLatLon,
    lateLabel, flagLabel, deliveryLabel, classifyFreshness: () => 'live', freshnessLabel: () => 'LIVE',
    authFetch: async (url) => { ns.requestUrl = url; return { ok: true, json: async () => payload }; },
    map, syncAlertIndicators() {}, renderIncidentFeed() {}, refreshOpenDrawer() {}, showToast() {},
    sosAlarm: { sync() {}, notify() {}, start() {} }
  };
  const window = { document, AqOneDashboard: ns, setInterval() { return 1; }, clearInterval() {}, console };
  window.window = window;
  const L = {
    layerGroup: () => layer,
    divIcon: (options) => options,
    marker: (position, options) => {
      const marker = { position, options, bindTooltip(text) { tooltips.push(text); }, setLatLng(p) { this.position = p; }, off() {}, on() {} };
      markers.push(marker);
      return marker;
    }
  };
  const context = vm.createContext({ window, document, AqOneDashboard: ns, L, setInterval() { return 1; }, clearInterval() {}, console, Date, Math, Number, Object, Array, String, isFinite });
  const source = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-live-sos.js'), 'utf8');
  vm.runInContext(source, context);
  await new Promise((resolve) => setTimeout(resolve, 0));
  return { ns, elements, tooltips, markers };
}

test('live SOS feed renders server order, limits, flood state, and edge fields', async () => {
  const events = [
    { id: 'known', vessel_id: 'NW-1', boat: 'Sea Star', latitude: 11.71, longitude: 122.41, created_at: '2026-09-24T10:00:00Z', pressed_at: '2026-09-21T06:00:00Z', is_late: true, flags: ['position_on_land'], open_calls_for_vessel: 2, alt_latitude: 11.7, alt_longitude: 122.4, delivery_path: 'pod', pod_id: 'P-4', is_synthetic: false },
    { id: 'newer', vessel_id: 'NW-2', created_at: '2026-09-24T11:00:00Z', is_synthetic: false }
  ];
  const { ns, elements, tooltips, markers } = await loadFeed({ events, total: 205, flood: { active: true, unknown_vessels_last_minute: 17 } });
  assert.equal(ns.requestUrl, '/api/sos/active?limit=200');
  assert.deepEqual(ns.liveAlerts.map((event) => event.sosEventId), ['known', 'newer']);
  assert.equal(ns.liveAlerts[0].lateLabel.startsWith('LATE - pressed '), true);
  assert.deepEqual(ns.liveAlerts[0].flags, ['position_on_land']);
  assert.equal(ns.liveAlerts[0].openCallsForVessel, 2);
  assert.equal(ns.liveAlerts[0].altLat, 11.7);
  assert.equal(ns.liveAlerts[0].delivery, 'Relayed by pod P-4 - sender not verified');
  assert.ok(tooltips.includes('conflicting position'));
  assert.ok(markers.some((marker) => marker.options && marker.options.icon && marker.options.icon.className === 'live-sos-alt-marker'));
  assert.equal(elements.get('sos-flood-banner').hidden, false);
  assert.equal(elements.get('sos-more-count').textContent, '+203 more');
});
