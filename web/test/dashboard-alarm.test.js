'use strict';

// node --test web/test/dashboard-alarm.test.js
//
// The SOS klaxon: dashboard-live-sos.js must ring the alarm only for a
// distress call that arrives while the dashboard is open (never on first
// load), and dashboard-alarm.js must keep ringing until every call in the
// feed is acknowledged, then stop.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const { escapeHtml } = require('../js/dashboard-utils.js');

function createStubElement(tag, id) {
  const children = [];
  const listeners = {};
  const dataset = {};
  const classList = {
    classes: new Set(),
    add(c) { this.classes.add(c); },
    remove(c) { this.classes.delete(c); },
    contains(c) { return this.classes.has(c); },
    toggle(c) { if (this.classes.has(c)) this.classes.delete(c); else this.classes.add(c); }
  };
  return {
    tagName: tag.toUpperCase(),
    id, dataset, classList, style: {}, children, disabled: false, hidden: false,
    _innerHTML: '', _textContent: '',
    addEventListener(event, fn) { (listeners[event] = listeners[event] || []).push(fn); },
    removeEventListener() {},
    dispatchEvent(event) { (listeners[event] = listeners[event] || []).forEach((fn) => fn({ type: event })); return true; },
    appendChild(child) { children.push(child); return child; },
    get innerHTML() { return this._innerHTML; },
    set innerHTML(v) { this._innerHTML = String(v); this._textContent = this._innerHTML.replace(/<[^>]*>/g, ''); },
    get textContent() { return this._textContent; },
    set textContent(v) { this._textContent = String(v); this._innerHTML = String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); },
    remove() {}
  };
}

function createDOMContext(elements = {}, ns = { ready: true }) {
  const elMap = new Map();
  const windowListeners = {};
  const intervals = [];
  const documentStub = {
    title: 'AqOne Dashboard',
    activeElement: null,
    getElementById(id) {
      if (!elMap.has(id)) { elMap.set(id, createStubElement('div', id)); }
      return elMap.get(id);
    },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement(tag) { return createStubElement(tag); },
    body: createStubElement('body'),
    documentElement: createStubElement('html'),
    addEventListener(event, fn) { (windowListeners[event] = windowListeners[event] || []).push(fn); }
  };
  for (const [key, el] of Object.entries(elements)) {
    elMap.set(key, el);
  }
  const windowStub = {
    document: documentStub,
    intervalCalls: intervals,
    AqOneDashboardUtils: { escapeHtml },
    AqOneDashboard: ns,
    console: { log() {}, warn() {}, error() {} },
    setInterval(fn) { intervals.push(fn); return intervals.length; },
    clearInterval() {},
    setTimeout(fn) { return 1; },
    addEventListener(event, fn) { (windowListeners[event] = windowListeners[event] || []).push(fn); },
    dispatchEvent(event) { (windowListeners[event] = windowListeners[event] || []).forEach((fn) => fn({ type: event })); return true; },
    removeEventListener() {},
    Date, JSON, Number, String, Array, Object, Math
  };
  windowStub.window = windowStub;
  return { window: windowStub, document: documentStub, intervals };
}

function loadAlarm(ns, opts) {
  opts = opts || {};
  const { window, document } = createDOMContext(opts.elements || {}, ns);
  const fakeWindow = Object.assign({}, window);
  if (opts.Notification) fakeWindow.Notification = opts.Notification;
  if (opts.AudioContext === null) {
    delete fakeWindow.AudioContext;
  } else if (typeof opts.AudioContext === 'function') {
    fakeWindow.AudioContext = opts.AudioContext;
  }
  const context = vm.createContext(Object.assign({}, fakeWindow, {
    window: fakeWindow, document, AqOneDashboard: ns
  }));
  const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-alarm.js'), 'utf8');
  vm.runInContext(code, context);
  return context;
}

// A Web Audio context that starts suspended (the state a browser creates
// before the user has interacted with the page) and only releases on
// ctx.resume() issued from inside a user gesture - matching the autoplay
// policy a real browser enforces. Lets the tests exercise the
// unlock-on-gesture path.
function createSuspendedAudioContext() {
  let latest = null;
  let inGesture = false;
  function FakeAudioContext() {
    this.state = 'suspended';
    this.currentTime = 0;
    this.destination = {};
    this.resumed = 0;
    this.oscillators = 0;
    latest = this;
  }
  FakeAudioContext.prototype.resume = function () {
    this.resumed++;
    if (inGesture) return Promise.resolve().then(() => { this.state = 'running'; return this.state; });
    return Promise.resolve(this.state);
  };
  FakeAudioContext.prototype.createOscillator = function () {
    this.oscillators++;
    return { type: '', frequency: { value: 0, setValueAtTime() {} }, connect() {}, start() {}, disconnect() { } };
  };
  FakeAudioContext.prototype.createGain = function () {
    return { gain: { value: 0 }, connect() {}, disconnect() {} };
  };
  return {
    FakeAudioContext,
    latest: () => latest,
    dispatchGesture(context, eventName) {
      inGesture = true;
      try { context.window.dispatchEvent(eventName); } finally { inGesture = false; }
    }
  };
}

test('dashboard-alarm: module registers sosAlarm and hasUnacknowledgedSos', () => {
  const ns = { ready: true };
  loadAlarm(ns);
  assert.equal(typeof ns.sosAlarm, 'object');
  assert.equal(typeof ns.sosAlarm.start, 'function');
  assert.equal(typeof ns.sosAlarm.stop, 'function');
  assert.equal(typeof ns.sosAlarm.sync, 'function');
  assert.equal(typeof ns.sosAlarm.notify, 'function');
  assert.equal(typeof ns.hasUnacknowledgedSos, 'function');
});

test('dashboard-alarm: hasUnacknowledgedSos truth table', () => {
  const ns = { ready: true };
  loadAlarm(ns);

  assert.equal(ns.hasUnacknowledgedSos(null), false);
  assert.equal(ns.hasUnacknowledgedSos([]), false);
  assert.equal(ns.hasUnacknowledgedSos([null]), false);

  assert.equal(
    ns.hasUnacknowledgedSos([{ id: 'S1' }]),
    true,
    'a call with no acknowledgement is unacknowledged'
  );
  assert.equal(
    ns.hasUnacknowledgedSos([{ id: 'S1', acknowledged_at: null }]),
    true,
    'explicit null acknowledged_at is still unacknowledged'
  );
  assert.equal(
    ns.hasUnacknowledgedSos([{ id: 'S1', acknowledged_at: '2026-09-16T00:00:00Z' }]),
    false,
    'acknowledged_at set means acknowledged'
  );
  assert.equal(
    ns.hasUnacknowledgedSos([{ id: 'S1', status: 'acknowledged' }]),
    false,
    'status acknowledged means acknowledged'
  );
  assert.equal(
    ns.hasUnacknowledgedSos([{ id: 'S1', acknowledged_at: '2026-09-16T00:00:00Z' }, { id: 'S2' }]),
    true,
    'one unacknowledged call among acknowledged ones keeps the alarm on'
  );
});

test('dashboard-alarm: first load rings only when an event is unacknowledged', () => {
  const ns = { ready: true };
  loadAlarm(ns, { AudioContext: null });

  assert.equal(ns.sosAlarm.isRunning(), false, 'no alarm before any SOS');

  ns.sosAlarm.sync([{ id: 'S1' }]);
  assert.equal(ns.sosAlarm.isRunning(), true, 'first load rings for a waiting call');

  ns.sosAlarm.sync([{ id: 'S1', acknowledged_at: '2026-09-16T00:00:00Z' }]);
  assert.equal(ns.sosAlarm.isRunning(), false, 'first load stays silent when every call is acknowledged');

  ns.sosAlarm.start();
  ns.sosAlarm.stop();
  assert.equal(ns.sosAlarm.isRunning(), false, 'explicit stop works');
  assert.equal(ns.sosAlarm.isRunning(), false, 'stop is idempotent');
});

test('dashboard-alarm: start/stop are idempotent and tolerate no AudioContext', () => {
  const ns = { ready: true };
  loadAlarm(ns, { audioDisabled: true });

  ns.sosAlarm.start();
  ns.sosAlarm.start();
  assert.equal(ns.sosAlarm.isRunning(), true);
  ns.sosAlarm.stop();
  assert.equal(ns.sosAlarm.isRunning(), false);
});

test('dashboard-alarm: suspended context rings after an asynchronous gesture resume', async () => {
  const ns = { ready: true };
  const { FakeAudioContext, latest, dispatchGesture } = createSuspendedAudioContext();
  const context = loadAlarm(ns, { AudioContext: FakeAudioContext });

  // First SOS arrives before the dispatcher has ever clicked: the context is
  // created suspended (browsers block sound until a gesture), so no oscillator
  // is built and nothing rings yet.
  ns.sosAlarm.start();
  const ctx = latest();
  assert.equal(ctx.state, 'suspended', 'context created suspended pre-gesture');
  assert.equal(ctx.oscillators, 0, 'must not start a silent oscillator into a suspended context');
  assert.equal(ns.sosAlarm.isRunning(), true, 'alarm is armed');

  // The first real gesture releases the context and rings the siren.
  dispatchGesture(context, 'pointerdown');
  assert.ok(ctx.resumed >= 1, 'a user gesture resumes the context');
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.state, 'running');
  assert.ok(ctx.oscillators >= 1, 'unlock builds the oscillator once running');
  assert.equal(ns.sosAlarm.isRunning(), true);

  // Acknowledging stops the siren.
  ns.sosAlarm.sync([{ id: 'S1', acknowledged_at: '2026-09-16T00:00:00Z' }]);
  assert.equal(ns.sosAlarm.isRunning(), false, 'ack stops the siren');
});

test('dashboard-alarm: start/stop still work when the context is suspended', () => {
  const ns = { ready: true };
  const { FakeAudioContext, latest } = createSuspendedAudioContext();
  loadAlarm(ns, { AudioContext: FakeAudioContext });

  ns.sosAlarm.start();
  const ctx = latest();
  assert.equal(ns.sosAlarm.isRunning(), true, 'armed while blocked');
  assert.equal(ctx.state, 'suspended', 'still blocked until a gesture');

  // start() twice is idempotent even mid-suspend.
  ns.sosAlarm.start();
  assert.equal(ns.sosAlarm.isRunning(), true);
  assert.equal(ctx.oscillators, 0, 'idempotent start does not double-build');

  ns.sosAlarm.stop();
  assert.equal(ns.sosAlarm.isRunning(), false, 'ack/resolve stops even while suspended');
});

test('dashboard-live-sos: rings on a new unacknowledged SOS and stops once acknowledged', async () => {
  const events = {};
  const toasts = [];
  const ns = {
    ready: true,
    liveAlerts: [],
    escapeHtml,
    classifyFreshness: () => 'live',
    freshnessLabel: () => 'LIVE',
    authFetch: () => new Promise((resolve) => events.next = resolve),
    map: { setView() {} },
    syncAlertIndicators() {},
    renderIncidentFeed() {},
    refreshOpenDrawer() {},
    showToast(...args) { toasts.push(args); }
  };

  const sosAlarmStub = {
    starts: 0,
    stops: 0,
    running: false,
    start() { if (!this.running) this.starts++; this.running = true; },
    stop() { if (this.running) this.stops++; this.running = false; },
    notify() {},
    sync(eventList) {
      const allAcknowledged = Array.isArray(eventList) && eventList.every((ev) =>
        ev.acknowledged_at != null || ev.status === 'acknowledged'
      );
      if (allAcknowledged) this.stop(); else this.start();
    }
  };
  ns.sosAlarm = sosAlarmStub;

  const { window, document } = createDOMContext({}, ns);
  const fakeL = {
    layerGroup: () => ({ addTo: () => ({ addLayer: () => {}, removeLayer: () => {} }) }),
    divIcon: () => ({}),
    marker: () => ({ bindTooltip: () => {}, off: () => {}, on: () => {}, setLatLng: () => {} })
  };
  const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-live-sos.js'), 'utf8');
  const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
  vm.runInContext(code, context);

  // Poll 1: first load, an already-acknowledged call is already in the feed.
  // First load must neither toast nor ring.
  const now = new Date().toISOString();
  events.next({ ok: true, json: () => Promise.resolve({
    events: [{ id: 'OLD', boat: 'Old Boat', created_at: now, acknowledged_at: now, is_synthetic: false }]
  }) });
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(sosAlarmStub.starts, 0, 'first load must not klaxon for existing calls');
  assert.equal(sosAlarmStub.stops, 0, 'first load must not touch the alarm state');

  // Poll 2: a brand-new, unacknowledged SOS arrives -> must ring.
  const poll2 = ns.loadActiveSos();
  await new Promise((r) => setTimeout(r, 0));
  events.next({ ok: true, json: () => Promise.resolve({
    events: [
      { id: 'OLD', boat: 'Old Boat', created_at: now, acknowledged_at: now, is_synthetic: false },
      { id: 'NEW', boat: 'New Vessel', created_at: now, is_synthetic: false }
    ]
  }) });
  await poll2;
  assert.equal(sosAlarmStub.starts, 1, 'a new unacknowledged SOS must ring the alarm');

  // Poll 3: the dispatcher acknowledged it -> alarm must stop.
  const poll3 = ns.loadActiveSos();
  await new Promise((r) => setTimeout(r, 0));
  events.next({ ok: true, json: () => Promise.resolve({
    events: [
      { id: 'OLD', boat: 'Old Boat', created_at: now, acknowledged_at: now, is_synthetic: false },
      { id: 'NEW', boat: 'New Vessel', created_at: now, acknowledged_at: now, is_synthetic: false }
    ]
  }) });
  await poll3;
  assert.equal(sosAlarmStub.starts, 1, 'no re-ring for an already-seen call');
  assert.equal(sosAlarmStub.stops, 1, 'acknowledging every call stops the siren');

  const poll4 = ns.loadActiveSos();
  await new Promise((r) => setTimeout(r, 0));
  events.next({ ok: true, json: () => Promise.resolve({
    events: [
      { id: 'OLD', boat: 'Old Boat', created_at: now, acknowledged_at: now, is_synthetic: false },
      { id: 'NEW', vessel_id: 'NW-1', boat: 'Sea Star', created_at: now, reopened_at: new Date(Date.now() + 1000).toISOString(), is_synthetic: false }
    ]
  }) });
  await poll4;
  assert.equal(sosAlarmStub.starts, 2, 'reopened incident rings again');
  assert.equal(toasts.length, 2, 'reopened incident is announced as new');
});

test('dashboard-alarm: feed polls do not restart title flashing for the same waiting SOS', () => {
  const ns = { ready: true };
  const context = loadAlarm(ns, { AudioContext: null });
  const { document, intervalCalls: intervals } = context;
  const event = { id: 'S1', vessel_id: 'NW-1' };
  ns.sosAlarm.sync([event]);
  const firstTitle = document.title;
  const firstTimerCount = intervals.length;
  ns.sosAlarm.sync([event]);
  assert.equal(intervals.length, firstTimerCount, 'the three-second poll reuses the title timer');
  assert.equal(document.title, firstTitle, 'polling does not pin the title to the SOS text');
  ns.sosAlarm.sync([{ id: 'S1', acknowledged_at: '2026-09-24T00:00:00Z' }]);
  assert.equal(document.title, 'AqOne Dashboard', 'acknowledgement restores the page title');
});

test('dashboard-alarm: banner stays until a user gesture resumes audio', async () => {
  const banner = createStubElement('div', 'alarm-sound-banner');
  const ns = { ready: true };
  const { FakeAudioContext, latest, dispatchGesture } = createSuspendedAudioContext();
  const context = loadAlarm(ns, { AudioContext: FakeAudioContext, elements: { 'alarm-sound-banner': banner } });
  assert.equal(banner.hidden, false);
  assert.match(banner.textContent, /Alarm sound is OFF - click to enable/);
  dispatchGesture(context, 'pointerdown');
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(latest().state, 'running');
  assert.equal(banner.hidden, true);
});

test('dashboard-alarm: granted notification permission announces a new call', () => {
  const made = [];
  function Notification(title, options) { made.push({ title, options }); }
  Notification.permission = 'granted';
  const ns = { ready: true };
  const context = loadAlarm(ns, { Notification });
  ns.sosAlarm.notify({ id: 'SOS-7', vessel_id: 'NW-7', boat: 'Sea Star' });
  assert.equal(made.length, 1);
  assert.equal(made[0].title, 'SOS - NW-7');
  assert.equal(made[0].options.body, '"Sea Star"');
  assert.match(context.document.title, /SOS - NW-7/);
});

test('dashboard-alarm: notification permission is requested only from the banner click', () => {
  let requests = 0;
  function Notification() {}
  Notification.permission = 'default';
  Notification.requestPermission = () => { requests++; return Promise.resolve('granted'); };
  const banner = createStubElement('button', 'alarm-sound-banner');
  const ns = { ready: true };
  loadAlarm(ns, { Notification, elements: { 'alarm-sound-banner': banner }, AudioContext: null });
  assert.equal(requests, 0, 'permission is never requested on load');
  banner.dispatchEvent('click');
  assert.equal(requests, 1, 'banner click requests permission');
});
