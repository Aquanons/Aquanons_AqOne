'use strict';

// node --test web/test/dashboard-broadcast-states.test.js
//
// Nearby broadcast controls in the SOS drawer (docs/73 Rev 2, Section 14,
// G4 and G11). Acceptance tests written by the spec author: they drive the
// real dashboard-incidents.js in a VM, so they check behaviour, not source
// text. Do not edit them to make them pass.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const { escapeHtml } = require('../js/dashboard-utils.js');

function createStubElement(tag, id) {
  const listeners = {};
  const classList = {
    classes: new Set(),
    add(c) { this.classes.add(c); },
    remove(c) { this.classes.delete(c); },
    contains(c) { return this.classes.has(c); },
    toggle(c, force) {
      const on = force === undefined ? !this.classes.has(c) : force;
      if (on) this.classes.add(c); else this.classes.delete(c);
    }
  };
  return {
    tagName: tag.toUpperCase(),
    id, dataset: {}, classList, style: {}, children: [], disabled: false, hidden: false,
    value: '', checked: true, className: '',
    _innerHTML: '', _textContent: '',
    addEventListener(event, fn) { (listeners[event] = listeners[event] || []).push(fn); },
    removeEventListener() {},
    dispatchEvent(ev) { (listeners[ev.type] || []).forEach((fn) => fn.call(this, ev)); return true; },
    click() { this.dispatchEvent({ type: 'click', target: this, preventDefault() {} }); },
    appendChild(child) { this.children.push(child); return child; },
    setAttribute() {}, removeAttribute() {}, getAttribute() { return null; },
    closest() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() {}, blur() {},
    get innerHTML() { return this._innerHTML; },
    set innerHTML(v) { this._innerHTML = String(v); this._textContent = this._innerHTML.replace(/<[^>]*>/g, ''); },
    get textContent() { return this._textContent; },
    set textContent(v) { this._textContent = String(v); this._innerHTML = String(v); },
    remove() {}
  };
}

function loadIncidents() {
  const elements = new Map();
  const documentStub = {
    activeElement: null,
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, createStubElement('div', id));
      return elements.get(id);
    },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement(tag) { return createStubElement(tag); },
    body: createStubElement('body'),
    documentElement: createStubElement('html'),
    addEventListener() {}
  };
  const calls = [];
  const ns = {
    ready: true,
    escapeHtml,
    authFetch(url, opts) {
      calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
      return new Promise(() => {});
    },
    map: { setView() {}, flyTo() {} },
    openActivityDrawer() {},
    showToast() {},
    allAlerts: () => [],
    syncAlertIndicators() {},
    loadActiveSos() { return Promise.resolve(); },
    currentUserRole: () => 'mdrrmo',
    responderStatusHtml: () => '',
    formatEta: () => '',
    confidenceColor: () => '#000',
    pulseCoverageCircle() {},
    liveSosLayer: { addLayer() {}, removeLayer() {} }
  };
  const windowStub = {
    document: documentStub,
    AqOneDashboardUtils: { escapeHtml, utf8ByteLength: (s) => Buffer.byteLength(String(s), 'utf8') },
    AqOneDashboard: ns,
    console: { log() {}, warn() {}, error() {} },
    setInterval() { return 1; },
    clearInterval() {},
    setTimeout() { return 1; },
    clearTimeout() {},
    addEventListener() {},
    removeEventListener() {},
    Date, JSON, Number, String, Array, Object, Math, parseInt, parseFloat, encodeURIComponent, Promise
  };
  windowStub.window = windowStub;
  const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-incidents.js'), 'utf8');
  vm.runInContext(code, vm.createContext(Object.assign({}, windowStub, { window: windowStub, document: documentStub, AqOneDashboard: ns })));
  return {
    ns,
    calls,
    button: documentStub.getElementById('sos-btn-broadcast'),
    message: documentStub.getElementById('sos-broadcast-msg')
  };
}

function sos(overrides) {
  return Object.assign({
    alertType: 'sos',
    sosEventId: 41,
    version: 3,
    vesselId: 'V001',
    title: 'SOS',
    lat: 11.7,
    lon: 122.44,
    acknowledgedAt: '2026-09-30T10:00:00Z',
    responderStatus: 2,
    broadcastState: 'off'
  }, overrides);
}

test('an unacknowledged call cannot be broadcast yet', () => {
  const ui = loadIncidents();
  ui.ns.openIncidentDrawer(sos({ acknowledgedAt: null }));
  assert.equal(ui.button.disabled, true);
});

test('an active broadcast says so and offers to stop it', () => {
  const ui = loadIncidents();
  ui.ns.openIncidentDrawer(sos({ broadcastState: 'active' }));
  assert.equal(ui.button.disabled, false, 'the dispatcher must be able to stop an active broadcast');
  assert.equal(ui.button.textContent, 'Stop Nearby Alert');
  assert.match(ui.message.textContent, /Broadcast ACTIVE/, 'opening the drawer must not wipe the broadcast state line');
});

test('stopping posts broadcast_enabled false without touching the ETA', () => {
  const ui = loadIncidents();
  ui.ns.openIncidentDrawer(sos({ broadcastState: 'active' }));
  ui.button.click();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.calls[0].url, '/api/sos/41/acknowledge');
  assert.equal(ui.calls[0].body.broadcast_enabled, false);
  assert.equal(ui.calls[0].body.expected_version, 3);
  assert.equal(ui.calls[0].body.responder_status, 2);
  assert.equal('eta_minutes' in ui.calls[0].body, false);
});

test('a cancelled broadcast is shown as cancelled, not as never sent', () => {
  const ui = loadIncidents();
  ui.ns.openIncidentDrawer(sos({ broadcastState: 'cancelled' }));
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.button.textContent, 'Alert Nearby Vessels');
  assert.match(ui.message.textContent, /Broadcast CANCELLED/);
});

test('acknowledged with no broadcast offers to alert with no state line', () => {
  const ui = loadIncidents();
  ui.ns.openIncidentDrawer(sos({ broadcastState: 'off' }));
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.button.textContent, 'Alert Nearby Vessels');
  assert.equal(ui.message.textContent, '');
  ui.button.click();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.calls[0].body.broadcast_enabled, true);
  assert.equal(ui.calls[0].body.broadcast_radius_km, 10);
  assert.equal('eta_minutes' in ui.calls[0].body, false);
});
