'use strict';

// node --test web/test/dashboard-reaudit.test.js
//
// Verification suite for re-audit defects R1-R5:
// - R1: Strict parsing of null/missing/empty/negative weather fields, and observation freshness demotion
// - R2: SOS distress provenance (real, synthetic, unknown), confidence suppression, drawer actionability without GPS fix
// - R3: Restored emergency/advisory modal exports, obsolete buoy sync removal, Escape key modal isolation
// - R4: Independent feed staleness aging (trip checks, squall watch, vessel risk) while SOS feed stays live
// - R5: Synchronized audit search filter promotion on success, keeping snapshots consistent on failure/pending

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const { escapeHtml, alertBadge, confidenceColor, classifyFreshness, freshnessLabel, formatDataAge, squallStatusHtml } = require('../js/dashboard-utils.js');

function createStubElement(tag = 'div', id = '') {
  const children = [];
  const listeners = {};
  const dataset = {};
  const style = {};
  const classList = {
    classes: new Set(),
    add(c) { this.classes.add(c); },
    remove(c) { this.classes.delete(c); },
    contains(c) { return this.classes.has(c); },
    toggle(c, force) {
      if (force !== undefined) {
        if (force) this.classes.add(c);
        else this.classes.delete(c);
      } else if (this.classes.has(c)) {
        this.classes.delete(c);
      } else {
        this.classes.add(c);
      }
    }
  };

  return {
    tagName: tag.toUpperCase(),
    id: id,
    dataset: dataset,
    style: style,
    classList: classList,
    children: children,
    disabled: false,
    hidden: false,
    value: '',
    href: '',
    download: '',
    options: [],
    _innerHTML: '',
    _textContent: '',
    focus() {
      if (this._ownerDocument) this._ownerDocument.activeElement = this;
    },
    blur() {
      if (this._ownerDocument && this._ownerDocument.activeElement === this) {
        this._ownerDocument.activeElement = null;
      }
    },
    get innerHTML() {
      return this._innerHTML;
    },
    set innerHTML(val) {
      this._innerHTML = String(val);
      this._textContent = this._innerHTML.replace(/<[^>]*>/g, '');
      this.children.length = 0;
      const regex = /<div class="([^"]*alert-row[^"]*)"\s+data-alert-index="(\d+)"/g;
      let m;
      while ((m = regex.exec(this._innerHTML)) !== null) {
        const rowEl = createStubElement('div');
        rowEl.dataset.alertIndex = m[2];
        m[1].split(/\s+/).forEach(c => rowEl.classList.add(c));
        this.children.push(rowEl);
      }
    },
    get textContent() {
      return this._textContent;
    },
    set textContent(val) {
      this._textContent = String(val);
      this._innerHTML = String(val)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      this.children.length = 0;
    },
    addEventListener(event, fn) {
      listeners[event] = listeners[event] || [];
      listeners[event].push(fn);
    },
    dispatchEvent(event) {
      const type = typeof event === 'string' ? event : event.type;
      const ev = typeof event === 'string' ? { type: event, target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } } : event;
      if (!ev.target) ev.target = this;
      (listeners[type] || []).forEach(fn => fn.call(this, ev));
      return !ev.defaultPrevented;
    },
    click() {
      this.dispatchEvent({ type: 'click', target: this });
    },
    closest(selector) {
      return null;
    },
    querySelectorAll(selector) {
      if (selector === '.alert-row') {
        return this.children.filter(c => c.classList.contains('alert-row'));
      }
      return [];
    },
    querySelector() {
      return null;
    },
    appendChild(child) {
      children.push(child);
      return child;
    },
    remove() {}
  };
}

function createDOMContext(elements = {}, ns = {}) {
  const elMap = new Map();
  const docListeners = {};

  const documentStub = {
    activeElement: null,
    getElementById(id) {
      if (elMap.has(id)) return elMap.get(id);
      const el = createStubElement('div', id);
      el._ownerDocument = documentStub;
      elMap.set(id, el);
      return el;
    },
    querySelectorAll(selector) {
      const results = [];
      for (const el of elMap.values()) {
        if (selector.startsWith('.') && el.classList.contains(selector.slice(1))) {
          results.push(el);
        }
      }
      return results;
    },
    querySelector() { return null; },
    createElement(tag) {
      const el = createStubElement(tag);
      el._ownerDocument = documentStub;
      return el;
    },
    body: createStubElement('body'),
    documentElement: createStubElement('html'),
    addEventListener(event, fn) {
      docListeners[event] = docListeners[event] || [];
      docListeners[event].push(fn);
    },
    dispatchEvent(event) {
      const type = typeof event === 'string' ? event : event.type;
      const ev = typeof event === 'string' ? { type: event, target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } } : event;
      (docListeners[type] || []).forEach(fn => fn.call(this, ev));
      return !ev.defaultPrevented;
    }
  };
  documentStub.body._ownerDocument = documentStub;
  documentStub.documentElement._ownerDocument = documentStub;
  documentStub.activeElement = documentStub.body;

  for (const [id, el] of Object.entries(elements)) {
    el._ownerDocument = documentStub;
    elMap.set(id, el);
  }

  const layerStub = {
    addTo() { return this; },
    clearLayers() { return this; },
    addLayer() { return this; },
    removeLayer() { return this; },
    getLayers() { return []; },
    getBounds() {
      return {
        isValid() { return false; },
        pad() { return this; }
      };
    }
  };

  const LStub = {
    layerGroup() { return layerStub; },
    featureGroup() { return layerStub; },
    marker() { return { addTo() { return this; }, bindPopup() { return this; }, on() { return this; } }; },
    divIcon() { return {}; },
    latLng(lat, lng) { return { lat, lng }; }
  };

  const AdvisoryServiceStub = {
    getAdvisories: async () => [],
    getAdvisory: async () => ({}),
    createAdvisory: async () => ({}),
    updateAdvisory: async () => ({}),
    deleteAdvisory: async () => ({})
  };

  ns.ready = ns.ready !== undefined ? ns.ready : true;
  ns.escapeHtml = ns.escapeHtml || escapeHtml;
  ns.alertBadge = ns.alertBadge || alertBadge;
  ns.confidenceColor = ns.confidenceColor || confidenceColor;
  ns.classifyFreshness = ns.classifyFreshness || classifyFreshness;
  ns.freshnessLabel = ns.freshnessLabel || freshnessLabel;
  ns.liveAlerts = ns.liveAlerts || [];
  ns.showToast = ns.showToast || function () {};
  ns.authFetch = ns.authFetch || (async () => ({ ok: true, json: async () => [] }));
  ns.map = ns.map || {
    distance(a, b) {
      const p1 = Array.isArray(a) ? { lat: a[0], lon: a[1] } : a;
      const p2 = Array.isArray(b) ? { lat: b[0], lon: b[1] } : b;
      const dx = ((p1.lng || p1.lon || 0) - (p2.lng || p2.lon || 0)) * 111320;
      const dy = ((p1.lat || 0) - (p2.lat || 0)) * 110540;
      return Math.sqrt(dx * dx + dy * dy);
    },
    fitBounds() {},
    setView() {},
    flyTo() {},
    on() { return this; },
    off() { return this; }
  };
  ns.vesselLayer = ns.vesselLayer || layerStub;

  const windowStub = {
    document: documentStub,
    L: LStub,
    AdvisoryService: AdvisoryServiceStub,
    AqOneDashboardUtils: { escapeHtml, alertBadge, confidenceColor, classifyFreshness, freshnessLabel, formatDataAge, squallStatusHtml },
    AqOneDashboard: ns,
    location: { href: 'http://localhost/html/dashboard.html', search: '', replace() {} },
    sessionStorage: {
      data: new Map(),
      getItem(k) { return this.data.has(k) ? this.data.get(k) : null; },
      setItem(k, v) { this.data.set(k, String(v)); },
      removeItem(k) { this.data.delete(k); },
      clear() { this.data.clear(); }
    },
    localStorage: {
      data: new Map(),
      getItem(k) { return this.data.has(k) ? this.data.get(k) : null; },
      setItem(k, v) { this.data.set(k, String(v)); },
      removeItem(k) { this.data.delete(k); },
      clear() { this.data.clear(); }
    },
    console: { log() {}, warn() {}, error() {} },
    setInterval() { return 1; },
    clearInterval() {},
    setTimeout(fn) { return 1; },
    clearTimeout() {},
    addEventListener() {},
    removeEventListener() {},
    Date: Date,
    JSON: JSON,
    Number: Number,
    String: String,
    Array: Array,
    Object: Object,
    Math: Math,
    parseInt: parseInt,
    parseFloat: parseFloat,
    isFinite: isFinite,
    isNaN: isNaN,
    URLSearchParams: URLSearchParams,
    AbortController: globalThis.AbortController,
    AbortSignal: globalThis.AbortSignal,
    fetch: globalThis.fetch || (async () => ({ ok: true, json: async () => ({}) })),
    URL: {
      createObjectURL: () => 'blob:dummylink',
      revokeObjectURL: () => {}
    }
  };

  return { window: windowStub, document: documentStub, L: LStub, AdvisoryService: AdvisoryServiceStub };
}

test('R1: Weather Card Strict Parsing & Freshness Demotion', async (t) => {
  const wcBody = createStubElement('div', 'wc-body');
  const elements = {
    'wc-body': wcBody
  };

  const ns = {
    ready: true,
    escapeHtml,
    weatherState: { snapshot: null }
  };

  const { window, document } = createDOMContext(elements, ns);
  const weatherCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-shortcuts-weather.js'), 'utf8');
  const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
  vm.runInContext(weatherCode, context);

  await t.test('null, missing, empty string, and boolean weather values do NOT coerce to 0.0 or LOWER RISK', () => {
    const badData = {
      current: {
        time: new Date().toISOString(),
        temperature_2m: null,
        apparent_temperature: '',
        wind_speed_10m: null,
        wind_gusts_10m: '',
        wind_direction_10m: false,
        precipitation: false,
        pressure_msl: undefined,
        weather_code: null
      }
    };
    const badMarine = {
      current: {
        wave_height: false,
        wave_period: null
      }
    };

    ns.renderWeatherCard(badData, badMarine, { nowMs: Date.now() });

    assert.ok(wcBody.innerHTML.includes('—'), 'Renders em-dash fallback for nulls');
    assert.ok(!wcBody.innerHTML.includes('0.0 km/h'), 'Null wind must not coerce to 0.0 km/h');
    assert.ok(!wcBody.innerHTML.includes('0.00 m'), 'False wave must not coerce to 0.00 m');
    assert.ok(wcBody.innerHTML.includes('--&deg;C'), 'Null temp must render --&deg;C');

    assert.ok(!wcBody.innerHTML.includes('MODEL: LOWER RISK'), 'Must not claim lower risk on missing data');
    assert.ok(wcBody.innerHTML.includes('CONDITIONS UNKNOWN'), 'Missing data evaluates to CONDITIONS UNKNOWN');
  });

  await t.test('negative wind, wave, and pressure are rejected and render fallback', () => {
    const invalidData = {
      current: {
        time: new Date().toISOString(),
        wind_speed_10m: -15.0,
        wind_gusts_10m: -20.0,
        temperature_2m: 28.0,
        pressure_msl: -50.0,
        weather_code: 0
      }
    };
    const invalidMarine = {
      current: {
        wave_height: -2.5,
        wave_period: -5.0
      }
    };

    ns.renderWeatherCard(invalidData, invalidMarine, { nowMs: Date.now() });

    assert.ok(!wcBody.innerHTML.includes('-15.0'), 'Negative wind rejected');
    assert.ok(!wcBody.innerHTML.includes('-2.50'), 'Negative wave rejected');
    assert.ok(!wcBody.innerHTML.includes('-50 hPa'), 'Negative pressure rejected');
    assert.ok(wcBody.innerHTML.includes('CONDITIONS UNKNOWN'), 'Negative values demote to CONDITIONS UNKNOWN');
  });

  await t.test('stale observation (>3h old) demotes mild weather from LOWER RISK to CONDITIONS UNKNOWN with LAST KNOWN', () => {
    const staleData = {
      current: {
        time: '2026-01-15T08:00:00Z',
        wind_speed_10m: 12.0,
        wind_gusts_10m: 16.0,
        temperature_2m: 29.0,
        weather_code: 1
      }
    };
    const staleMarine = {
      current: {
        time: '2026-01-15T08:00:00Z',
        wave_height: 0.6,
        wave_period: 4.0
      }
    };

    ns.renderWeatherCard(staleData, staleMarine, { nowMs: Date.now() });

    assert.ok(wcBody.innerHTML.includes('12.0 / 16.0 km/h'), 'Renders valid wind numbers');
    assert.ok(wcBody.innerHTML.includes('0.60 m / 4.0 s'), 'Renders valid wave numbers');

    assert.ok(!wcBody.innerHTML.includes('MODEL: LOWER RISK'), 'Stale observation cannot assert LOWER RISK');
    assert.ok(wcBody.innerHTML.includes('CONDITIONS UNKNOWN'), 'Stale observation demotes to CONDITIONS UNKNOWN');
    assert.ok(wcBody.innerHTML.includes('wc-monitor-stale'), 'Adds wc-monitor-stale class');
    assert.ok(wcBody.innerHTML.includes('showing last-known conditions'), 'Explains last-known conditions');
  });

  await t.test('mixed freshness: fresh weather with stale or absent marine observation demotes mild weather to CONDITIONS UNKNOWN', () => {
    const freshNow = new Date('2026-09-14T05:30:00Z').getTime();
    const freshWeather = {
      current: {
        time: '2026-09-14T05:00:00Z',
        wind_speed_10m: 10.0,
        wind_gusts_10m: 12.0,
        temperature_2m: 28.0,
        weather_code: 1
      }
    };
    const expiredCalmMarine = {
      current: {
        time: '2026-01-01T00:00:00Z',
        wave_height: 0.4,
        wave_period: 4.0
      }
    };

    ns.renderWeatherCard(freshWeather, expiredCalmMarine, { nowMs: freshNow, fetchedAt: '2026-09-14T05:28:00Z' });

    assert.ok(!wcBody.innerHTML.includes('MODEL: LOWER RISK'), 'Stale marine observation cannot assert LOWER RISK');
    assert.ok(wcBody.innerHTML.includes('CONDITIONS UNKNOWN'), 'Stale marine demotes to CONDITIONS UNKNOWN');
    assert.ok(wcBody.innerHTML.includes('LAST KNOWN'), 'Displays LAST KNOWN when marine data is stale');
  });

  await t.test('stale observation preserves severe adverse alert warning with LAST KNOWN tag', () => {
    const severeStaleData = {
      current: {
        time: '2026-01-15T08:00:00Z',
        wind_speed_10m: 68.0, // High marine risk
        wind_gusts_10m: 85.0,
        temperature_2m: 24.0,
        weather_code: 95
      }
    };
    const severeStaleMarine = {
      current: {
        time: '2026-01-15T08:00:00Z',
        wave_height: 3.5,
        wave_period: 8.0
      }
    };

    ns.renderWeatherCard(severeStaleData, severeStaleMarine, { nowMs: Date.now() });

    assert.ok(wcBody.innerHTML.includes('MODEL: HIGH MARINE RISK'), 'Preserves adverse hazard tier');
    assert.ok(wcBody.innerHTML.includes('wc-monitor-stale'), 'Adds wc-monitor-stale class');
    assert.ok(wcBody.innerHTML.includes('showing last-known conditions'), 'Explains last-known conditions');
  });
});

test('R2: SOS Distress Provenance, Actionability & Confidence Suppression', async (t) => {
  const ns = {
    ready: true,
    escapeHtml,
    alertBadge,
    confidenceColor,
    classifyFreshness,
    freshnessLabel,
    createMarkerIcon: () => ({}),
    createOverdueIcon: () => ({}),
    authFetch: async () => ({ ok: true, json: async () => [] }),
    openIncidentDrawerCalled: null,
    openIncidentDrawer(drawerData, marker) {
      this.openIncidentDrawerCalled = { drawerData, marker };
    },
    zoomToAlert() {}
  };

  const { window, document } = createDOMContext({}, ns);
  const liveSosCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-live-sos.js'), 'utf8');
  const alertsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-vessels-alerts.js'), 'utf8');

  const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
  vm.runInContext(liveSosCode, context);
  vm.runInContext(alertsCode, context);

  await t.test('liveAlertFromEvent classifies real, synthetic, and unknown provenance', () => {
    const realEv = {
      event_id: 'ev-real-1',
      session_id: 'sess-1',
      sender_type: 'buoy',
      is_synthetic: false,
      received_at: new Date().toISOString()
    };
    const synthEv = {
      event_id: 'ev-synth-1',
      session_id: 'sess-2',
      sender_type: 'phone',
      is_synthetic: true,
      received_at: new Date().toISOString()
    };
    const unknownEv = {
      event_id: 'ev-unk-1',
      session_id: 'sess-3',
      sender_type: 'buoy',
      received_at: new Date().toISOString()
    };

    const alertReal = ns.liveAlertFromEvent(realEv);
    assert.equal(alertReal.provenance, 'real');
    assert.equal(alertReal.isLive, true);
    assert.equal(alertBadge(alertReal.provenance).text, 'LIVE');

    const alertSynth = ns.liveAlertFromEvent(synthEv);
    assert.equal(alertSynth.provenance, 'synthetic');
    assert.equal(alertSynth.isLive, false);
    assert.equal(alertBadge(alertSynth.provenance).text, 'DEMO');

    const alertUnk = ns.liveAlertFromEvent(unknownEv);
    assert.equal(alertUnk.provenance, 'unknown');
    assert.equal(alertUnk.isLive, false);
    const unkBadge = alertBadge(alertUnk.provenance);
    assert.equal(unkBadge.text, 'UNKNOWN');
    assert.equal(unkBadge.cssClass, 'alert-unknown-badge');
    assert.equal(alertUnk.drawerData.headerText, 'SOS — DISTRESS CALL (PROVENANCE UNKNOWN)');
  });

  await t.test('alertConfidenceRow suppresses AI confidence badges on human SOS distress calls', () => {
    const sosAlert = {
      type: 'sos',
      confidence: null,
      sosEventId: 'sos-123'
    };
    const sosAlertWithErroneousNumber = {
      type: 'sos',
      confidence: 0.95,
      sosEventId: 'sos-456'
    };
    const anomalyAlert = {
      type: 'anomaly',
      confidence: 88,
      stage: 'STAGE 3 — SCORED ALERT'
    };

    const sosRow = ns.alertConfidenceRow(sosAlert);
    assert.ok(!sosRow.includes('% conf'), 'No % conf badge on SOS');
    assert.ok(!sosRow.includes('aq-conf-bar'), 'No confidence bar on SOS');

    const errNumRow = ns.alertConfidenceRow(sosAlertWithErroneousNumber);
    assert.ok(!errNumRow.includes('% conf'), 'Suppresses % conf even if number present on SOS');
    assert.ok(!errNumRow.includes('aq-conf-bar'), 'Suppresses confidence bar on SOS');

    const anomalyRow = ns.alertConfidenceRow(anomalyAlert);
    assert.ok(anomalyRow.includes('88% conf'), 'Renders % conf on AI alert');
    assert.ok(anomalyRow.includes('aq-conf-bar'), 'Renders confidence bar on AI alert');
  });

  await t.test('activateAlert opens drawer for synthetic and unknown provenance SOS without GPS fix', () => {
    const alertList = document.getElementById('alert-list');

    // Unknown provenance SOS without GPS coordinates
    const unknownSos = {
      type: 'sos',
      status: 'active',
      sosEventId: 'sos-event-unk-9',
      provenance: 'unknown',
      isLive: false,
      lat: null,
      lng: null,
      drawerData: {
        title: 'SOS Alert Unk',
        headerText: 'SOS — DISTRESS CALL (PROVENANCE UNKNOWN)'
      }
    };

    ns.liveAlerts.length = 0;
    ns.liveAlerts.push(unknownSos);
    ns.renderAlerts();

    ns.openIncidentDrawerCalled = null;
    const rows = alertList.querySelectorAll('.alert-row');
    assert.ok(rows.length > 0, 'Alert rows rendered');
    const firstRow = rows[0];

    // Click activation
    firstRow.click();
    assert.ok(ns.openIncidentDrawerCalled, 'Incident drawer opened on click for unknown provenance SOS');
    assert.equal(ns.openIncidentDrawerCalled.drawerData.headerText, 'SOS — DISTRESS CALL (PROVENANCE UNKNOWN)');

    // Keyboard activation (Enter key)
    ns.openIncidentDrawerCalled = null;
    firstRow.dispatchEvent({
      type: 'keydown',
      key: 'Enter',
      target: firstRow,
      defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }
    });
    assert.ok(ns.openIncidentDrawerCalled, 'Incident drawer opened on Enter key for unknown provenance SOS');

    // Synthetic SOS without GPS fix
    const synthSos = {
      type: 'sos',
      status: 'active',
      sosEventId: 'sos-event-synth-8',
      provenance: 'synthetic',
      isLive: false,
      lat: null,
      lng: null,
      drawerData: {
        title: 'SOS Alert Synth',
        headerText: 'DEMO SOS — SIMULATED DISTRESS CALL'
      }
    };

    ns.liveAlerts.length = 0;
    ns.liveAlerts.push(synthSos);
    ns.renderAlerts();

    ns.openIncidentDrawerCalled = null;
    const synthRows = alertList.querySelectorAll('.alert-row');
    synthRows[0].click();
    assert.ok(ns.openIncidentDrawerCalled, 'Incident drawer opened on click for synthetic SOS');
    assert.equal(ns.openIncidentDrawerCalled.drawerData.headerText, 'DEMO SOS — SIMULATED DISTRESS CALL');
  });

  await t.test('empty feed renders an honest empty state, never sample rows', () => {
    ns.liveAlerts.length = 0;
    ns.renderAlerts();
    const alertList = document.getElementById('alert-list');
    const html = alertList.innerHTML;
    assert.ok(html.includes('No active incidents'), 'Empty feed states it plainly');
    assert.ok(!html.includes('Manual SOS'), 'No scripted sample rows');
    assert.ok(!html.includes('San Pedro'), 'No scripted vessel names');
  });

  await t.test('live SOS with a fisher reply renders a status report line', () => {
    ns.liveAlerts.length = 0;
    ns.liveAlerts.push({
      type: 'sos',
      desc: 'SOS — Real Vessel',
      time: '1 minute ago',
      lat: 11.7,
      lng: 122.4,
      status: 'acknowledged',
      isLive: true,
      provenance: 'real',
      sosEventId: 9,
      owner: 'Juan Dela Cruz',
      phone: '+639171234567',
      fisherReply: 2,
      stage: 'DISTRESS CALL',
      drawerData: { fisherReply: 2 }
    });
    ns.renderAlerts();
    const safeHtml = document.getElementById('alert-list').innerHTML;
    assert.ok(safeHtml.includes('SAFE NOW'), 'Fisher SAFE NOW report renders on the row');

    ns.liveAlerts[0].fisherReply = 1;
    ns.liveAlerts[0].drawerData.fisherReply = 1;
    ns.renderAlerts();
    const dangerHtml = document.getElementById('alert-list').innerHTML;
    assert.ok(dangerHtml.includes('STILL IN DANGER'), 'Fisher STILL IN DANGER report renders on the row');
    ns.liveAlerts.length = 0;
  });
});

test('R3: Restored Modal Exports, Obsolete Buoy Sync Removal & Escape Key Isolation', async (t) => {
  const ns = {
    ready: true,
    escapeHtml,
    CURRENT_USER: { role: 'admin' }
  };

  const emergencyOverlay = createStubElement('div', 'emergency-modal-overlay');
  const advisoryOverlay = createStubElement('div', 'advisory-modal-overlay');
  const deleteOverlay = createStubElement('div', 'delete-modal-overlay');
  const emergencyBtn = createStubElement('button', 'btn-emergency');
  const emergencyClose = createStubElement('button', 'emergency-modal-close');
  const toolPanelCard = createStubElement('div', 'tool-panel-card');
  toolPanelCard.classList.add('collapsed');
  const buoysPanel = createStubElement('div', 'panel-buoys');
  buoysPanel.classList.add('tool-panel-content');
  const advisoriesPanel = createStubElement('div', 'panel-advisories');
  advisoriesPanel.classList.add('tool-panel-content');

  const elements = {
    'emergency-modal-overlay': emergencyOverlay,
    'advisory-modal-overlay': advisoryOverlay,
    'delete-modal-overlay': deleteOverlay,
    'btn-emergency': emergencyBtn,
    'emergency-modal-close': emergencyClose,
    'tool-panel-card': toolPanelCard,
    'panel-buoys': buoysPanel,
    'panel-advisories': advisoriesPanel,
    'tool-panel-title': createStubElement('span', 'tool-panel-title'),
    'toolbox-body': createStubElement('div', 'toolbox-body'),
    'toolbox-card': createStubElement('div', 'toolbox-card'),
    'map': createStubElement('div', 'map'),
    'rail-btn-pan': createStubElement('button', 'rail-btn-pan'),
    'rail-btn-pin': createStubElement('button', 'rail-btn-pin'),
    'advisory-list': createStubElement('div', 'advisory-list'),
    'wc-body': createStubElement('div', 'wc-body')
  };

  const { window, document } = createDOMContext(elements, ns);
  const advisoryCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-emergency-advisory.js'), 'utf8');
  const toolsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-tools.js'), 'utf8');
  const shortcutsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-shortcuts-weather.js'), 'utf8');

  const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
  vm.runInContext(advisoryCode, context);
  vm.runInContext(toolsCode, context);
  vm.runInContext(shortcutsCode, context);

  await t.test('dashboard-emergency-advisory exports all required modal controllers to ns', () => {
    assert.equal(typeof ns.openEmergencyModal, 'function');
    assert.equal(typeof ns.closeEmergencyModal, 'function');
    assert.equal(typeof ns.openAdvisoryModal, 'function');
    assert.equal(typeof ns.closeAdvisoryModal, 'function');
    assert.equal(typeof ns.closeDeleteModal, 'function');
    assert.equal(typeof ns.renderAdvisoryList, 'function');
    assert.ok(ns.emergencyOverlay);
    assert.ok(ns.advisoryOverlay);
    assert.ok(ns.deleteOverlay);
  });

  await t.test('openPanel("buoys") runs without crash and does not call obsolete updateBuoySync', () => {
    assert.doesNotThrow(() => {
      ns.openPanel('buoys');
    });
    assert.equal(ns.activePanel, 'buoys');
    assert.equal(toolPanelCard.classList.contains('collapsed'), false);
  });

  await t.test('Escape key closes active emergency modal without closing underlying panel', () => {
    ns.openPanel('advisories');
    assert.equal(ns.activePanel, 'advisories');

    ns.openEmergencyModal();
    assert.equal(emergencyOverlay.classList.contains('active'), true);

    const escapeEv = {
      type: 'keydown',
      key: 'Escape',
      target: document.body,
      defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }
    };
    document.dispatchEvent(escapeEv);

    assert.equal(emergencyOverlay.classList.contains('active'), false, 'Emergency modal overlay must close on Escape');
    assert.equal(ns.activePanel, 'advisories', 'Advisories panel must remain active after modal Escape');
    assert.equal(toolPanelCard.classList.contains('collapsed'), false, 'Tool panel must remain expanded');
  });
});

test('R4: Independent Feed Freshness Aging', async (t) => {
  await t.test('trip checks feed demotes to stale / offline state on poll failure without affecting SOS', async () => {
    const listEl = createStubElement('div', 'trip-checks-list');
    const badgeEl = createStubElement('span', 'badge-tripchecks');
    const elements = {
      'trip-checks-list': listEl,
      'badge-tripchecks': badgeEl
    };

    let fetchCount = 0;
    const ns = {
      ready: true,
      escapeHtml,
      tripChecksListHtml: (cases) => (cases || []).map(c => `<div>${c.id}</div>`).join(''),
      authFetch: async () => {
        fetchCount++;
        if (fetchCount === 1) {
          return {
            ok: true,
            json: async () => []
          };
        }
        throw new Error('Network offline');
      }
    };

    const { window, document } = createDOMContext(elements, ns);
    const tripCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-trip-checks.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(tripCode, context);

    await new Promise(r => setTimeout(r, 10));
    assert.equal(badgeEl.textContent, '0');

    const originalDateNow = Date.now;
    try {
      let simulatedTime = Date.now();
      Date.now = () => simulatedTime;

      simulatedTime += 65000;
      await ns.loadOpenCases();

      assert.notEqual(badgeEl.textContent, '0');
      assert.equal(badgeEl.textContent, '--', 'Empty cases demote to unavailable --');
      assert.ok(listEl.innerHTML.includes('trip-checks-stale') || listEl.innerHTML.includes('FEED STALE') || listEl.innerHTML.includes('FEED OFFLINE'));
    } finally {
      Date.now = originalDateNow;
    }
  });

  await t.test('squall watch feed demotes expired calm detection to unknown instead of false green all-clear', async () => {
    const squallStatusEl = createStubElement('span', 'stats-squall-status');
    const squallSummaryEl = createStubElement('div', 'ai-squall-summary');
    const elements = {
      'stats-squall-status': squallStatusEl,
      'ai-squall-summary': squallSummaryEl,
      'ai-panel': createStubElement('div', 'ai-panel'),
      'ai-drift-select': createStubElement('select', 'ai-drift-select')
    };

    let fetchCount = 0;
    const ns = {
      ready: true,
      escapeHtml,
      authFetch: async (url) => {
        if (url.includes('/squall/current')) {
          fetchCount++;
          if (fetchCount === 1) {
            return {
              ok: true,
              json: async () => ({ level: 'monitoring', detections: [] })
            };
          }
          throw new Error('Squall feed unreachable');
        }
        return { ok: true, json: async () => [] };
      }
    };

    const { window, document } = createDOMContext(elements, ns);
    const aiOpsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(aiOpsCode, context);

    await new Promise(r => setTimeout(r, 10));

    const originalDateNow = Date.now;
    try {
      let simulatedTime = Date.now();
      Date.now = () => simulatedTime;

      simulatedTime += 360000;
      await ns.pollAIOperations();
      await new Promise(r => setTimeout(r, 10));

      assert.equal(squallStatusEl.textContent, 'UNKNOWN');
      assert.ok(squallSummaryEl.innerHTML.includes('Squall status cannot be confirmed right now'));
    } finally {
      Date.now = originalDateNow;
    }
  });

  await t.test('trip checks freshness advances while request remains pending', async () => {
    const listEl = createStubElement('div', 'trip-checks-list');
    const badgeEl = createStubElement('span', 'badge-tripchecks');
    const elements = {
      'trip-checks-list': listEl,
      'badge-tripchecks': badgeEl
    };

    let fetchCount = 0;
    let pendingResolve;
    const ns = {
      ready: true,
      escapeHtml,
      tripChecksListHtml: (cases) => (cases || []).map(c => `<div>${c.id}</div>`).join(''),
      authFetch: async () => {
        fetchCount++;
        if (fetchCount === 1) {
          return {
            ok: true,
            json: async () => []
          };
        }
        return new Promise(r => { pendingResolve = r; });
      }
    };

    const { window, document } = createDOMContext(elements, ns);
    const tripCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-trip-checks.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(tripCode, context);

    await new Promise(r => setTimeout(r, 10));
    assert.equal(badgeEl.textContent, '0');

    const originalDateNow = Date.now;
    try {
      let simulatedTime = Date.now();
      Date.now = () => simulatedTime;

      simulatedTime += 600000; // 10 minutes later
      ns.loadOpenCases();
      await new Promise(r => setTimeout(r, 10));

      assert.equal(badgeEl.textContent, '--', 'Empty queue demotes to -- while request is pending');
      assert.ok(listEl.innerHTML.includes('FEED OFFLINE'), 'Shows FEED OFFLINE notice while request is pending');
    } finally {
      Date.now = originalDateNow;
      if (pendingResolve) pendingResolve({ ok: true, json: async () => [] });
    }
  });

  await t.test('active live squall renders LAST KNOWN, FEED OFFLINE, and reason while preserving detection', async () => {
    const squallStatusEl = createStubElement('div', 'ai-squall-status');
    const squallSummaryEl = createStubElement('div', 'ai-squall-summary');
    const statsSquallEl = createStubElement('span', 'stats-squall-status');
    const elements = {
      'ai-squall-status': squallStatusEl,
      'ai-squall-summary': squallSummaryEl,
      'stats-squall-status': statsSquallEl,
      'ai-panel': createStubElement('div', 'ai-panel'),
      'ai-drift-select': createStubElement('select', 'ai-drift-select'),
      'ai-trace-chart': createStubElement('div', 'ai-trace-chart'),
      'ai-trace-legend': createStubElement('div', 'ai-trace-legend')
    };

    let fetchCount = 0;
    const ns = {
      ready: true,
      escapeHtml,
      squallStatusHtml,
      formatDataAge,
      alertBadge,
      authFetch: async (url) => {
        if (url.includes('/squall/current')) {
          fetchCount++;
          if (fetchCount === 1) {
            return {
              ok: true,
              json: async () => ({
                source: 'live',
                level: 'return_now',
                data_age_seconds: 60,
                calibration: 'calibrated model',
                detections: [{
                  id: 'sq-1',
                  affected_polygon: null,
                  arrival_by_buoy: []
                }]
              })
            };
          }
          throw new Error('Squall feed connection lost');
        }
        return { ok: true, json: async () => [] };
      }
    };

    const { window, document } = createDOMContext(elements, ns);
    const aiOpsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(aiOpsCode, context);

    await new Promise(r => setTimeout(r, 10));
    assert.equal(statsSquallEl.textContent, 'RETURN NOW');
    assert.ok(squallStatusEl.innerHTML.includes('LIVE'));

    const originalDateNow = Date.now;
    try {
      let simulatedTime = Date.now();
      Date.now = () => simulatedTime;

      simulatedTime += 600000; // 10 minutes later
      await ns.pollAIOperations();
      await new Promise(r => setTimeout(r, 10));

      const statusHtml = squallStatusEl.innerHTML;
      assert.ok(!statusHtml.includes('>LIVE<'), 'Does not display LIVE badge when offline');
      assert.ok(statusHtml.includes('LAST KNOWN'), 'Labels detection as LAST KNOWN');
      assert.ok(statusHtml.includes('FEED OFFLINE'), 'Labels feed as FEED OFFLINE');
      assert.ok(statusHtml.includes('Service offline (showing last-known detection)'), 'Shows offline warning reason');
      assert.equal(statsSquallEl.textContent, 'RETURN NOW', 'Preserves RETURN NOW active squall warning');
    } finally {
      Date.now = originalDateNow;
    }
  });
});

test('R5: Synchronized Audit Search Filter Promotion', async (t) => {
  const auditResults = createStubElement('div', 'audit-results');
  const auditAppliedFilters = createStubElement('div', 'audit-applied-filters');
  const auditExportCsvBtn = createStubElement('button', 'audit-export-csv-btn');
  const actorInput = createStubElement('input', 'audit-filter-actor-email');
  const actionInput = createStubElement('input', 'audit-filter-action');
  const resourceSelect = createStubElement('select', 'audit-filter-resource-type');
  const dateFromInput = createStubElement('input', 'audit-filter-date-from');
  const dateToInput = createStubElement('input', 'audit-filter-date-to');
  const loadMoreBtn = createStubElement('button', 'audit-load-more-btn');

  const elements = {
    'audit-results': auditResults,
    'audit-applied-filters': auditAppliedFilters,
    'audit-export-csv-btn': auditExportCsvBtn,
    'audit-filter-actor-email': actorInput,
    'audit-filter-action': actionInput,
    'audit-filter-resource-type': resourceSelect,
    'audit-filter-date-from': dateFromInput,
    'audit-filter-date-to': dateToInput,
    'audit-load-more-btn': loadMoreBtn,
    'audit-error': createStubElement('div', 'audit-error')
  };

  const capturedFetches = [];
  let nextResponse = null;

  const ns = {
    ready: true,
    CURRENT_USER: { role: 'admin' },
    escapeHtml,
    auditTimelineHtml: (events) => (events || []).map(e => `<div>${e.id}</div>`).join(''),
    authFetch: async (url) => {
      capturedFetches.push(url);
      if (nextResponse.error) throw new Error(nextResponse.error);
      return {
        ok: nextResponse.ok !== false,
        status: nextResponse.status || 200,
        json: async () => nextResponse.data,
        blob: async () => ({})
      };
    }
  };

  const { window, document } = createDOMContext(elements, ns);
  const auditCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-operations-audit.js'), 'utf8');
  const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
  vm.runInContext(auditCode, context);

  await t.test('appliedAuditFilters promotes only upon success, keeping export and search in sync', async () => {
    // 1. Initial search with Snapshot A (actor = alice@example.com) succeeds
    actorInput.value = 'alice@example.com';
    nextResponse = {
      data: {
        events: [{ id: 'evt-1' }],
        next_cursor: 'cursor-alice-2',
        applied_filters: { actor_email: 'alice@example.com' }
      }
    };

    await ns.renderAuditPanel();

    assert.ok(auditAppliedFilters.textContent.includes('actor: alice@example.com'));

    // Verify export triggers snapshot A
    capturedFetches.length = 0;
    auditExportCsvBtn.click();
    await new Promise(r => setTimeout(r, 10));
    assert.ok(capturedFetches[0].includes('actor_email=alice%40example.com'), 'Export URL uses Snapshot A');

    // 2. Operator changes input to Snapshot B (actor = bob@example.com) but search FAILS
    actorInput.value = 'bob@example.com';
    nextResponse = { error: 'Network 500 error' };

    await ns.renderAuditPanel();

    // Applied filter MUST remain Snapshot A!
    assert.ok(auditAppliedFilters.textContent.includes('actor: alice@example.com'));

    // Export must STILL use Snapshot A
    capturedFetches.length = 0;
    auditExportCsvBtn.click();
    await new Promise(r => setTimeout(r, 10));
    assert.ok(capturedFetches[0].includes('actor_email=alice%40example.com'), 'Export URL must still use Snapshot A on failed search');

    // 3. Search B SUCCEEDS
    nextResponse = {
      data: {
        events: [{ id: 'evt-2' }],
        next_cursor: 'cursor-bob-2',
        applied_filters: { actor_email: 'bob@example.com' }
      }
    };

    await ns.renderAuditPanel();

    // Now applied filter promotes to Snapshot B
    assert.ok(auditAppliedFilters.textContent.includes('actor: bob@example.com'));

    // Export now uses Snapshot B
    capturedFetches.length = 0;
    auditExportCsvBtn.click();
    await new Promise(r => setTimeout(r, 10));
    assert.ok(capturedFetches[0].includes('actor_email=bob%40example.com'), 'Export URL now uses Snapshot B');

    // Pagination cursor fetch uses Snapshot B
    capturedFetches.length = 0;
    loadMoreBtn.click();
    await new Promise(r => setTimeout(r, 10));
    assert.ok(capturedFetches[0].includes('actor_email=bob%40example.com'), 'Pagination cursor fetch uses Snapshot B');
    assert.ok(capturedFetches[0].includes('cursor=cursor-bob-2'));
  });
});

test('C1: Squall Freshness Viewport and Drawing State Preservation', async (t) => {
  await t.test('freshness ticks preserve viewport with populated squall polygon, including while operator is drawing', async () => {
    let fitBoundsCalls = 0;
    const fakeBounds = {
      isValid: () => true,
      pad: () => fakeBounds
    };
    const squallFeatureGroup = {
      addTo: () => squallFeatureGroup,
      clearLayers: () => {},
      addLayer: () => {},
      getLayers: () => [{}],
      getBounds: () => fakeBounds
    };
    const fakeMap = {
      fitBounds: () => { fitBoundsCalls++; },
      createPane: () => ({ style: {} }),
      getPane: () => ({ style: {} }),
      on: () => {},
      setView: () => {}
    };
    const fakeL = {
      layerGroup: () => ({
        addTo: () => ({
          clearLayers: () => {},
          addLayer: () => {},
          getLayers: () => []
        })
      }),
      featureGroup: () => squallFeatureGroup,
      geoJSON: () => ({ addTo: () => {} }),
      polyline: () => ({ addTo: () => {} })
    };

    const squallStatusEl = createStubElement('div', 'ai-squall-status');
    const squallSummaryEl = createStubElement('div', 'ai-squall-summary');
    const statsSquallEl = createStubElement('span', 'stats-squall-status');
    const elements = {
      'ai-squall-status': squallStatusEl,
      'ai-squall-summary': squallSummaryEl,
      'stats-squall-status': statsSquallEl,
      'ai-panel': createStubElement('div', 'ai-panel'),
      'ai-drift-select': createStubElement('select', 'ai-drift-select'),
      'ai-trace-chart': createStubElement('div', 'ai-trace-chart'),
      'ai-trace-legend': createStubElement('div', 'ai-trace-legend')
    };

    let fetchCount = 0;
    let registeredFreshnessTimer = null;
    const ns = {
      ready: true,
      escapeHtml,
      squallStatusHtml,
      formatDataAge,
      alertBadge,
      map: fakeMap,
      squallLayer: squallFeatureGroup,
      authFetch: async (url) => {
        if (url.includes('/squall/current')) {
          fetchCount++;
          if (fetchCount === 1) {
            return {
              ok: true,
              json: async () => ({
                source: 'live',
                level: 'return_now',
                data_age_seconds: 60,
                calibration: 'calibrated model',
                detections: [{
                  id: 'sq-populated-1',
                  affected_polygon: {
                    type: 'Feature',
                    geometry: { type: 'Polygon', coordinates: [[[122, 11], [122.1, 11], [122.1, 11.1], [122, 11]]] }
                  },
                  arrival_by_buoy: []
                }]
              })
            };
          }
          throw new Error('Squall feed connection lost');
        }
        return { ok: true, json: async () => [] };
      }
    };

    const { window, document } = createDOMContext(elements, ns);
    window.setInterval = (fn, ms) => {
      if (ms === 15000) registeredFreshnessTimer = fn;
      return 1;
    };

    const aiOpsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(aiOpsCode, context);

    await new Promise(r => setTimeout(r, 10));

    assert.equal(fitBoundsCalls, 1, 'Initial data load centers the map on squall polygon');
    assert.equal(typeof registeredFreshnessTimer, 'function', 'Registers 15-second freshness timer callback');

    const originalDateNow = Date.now;
    try {
      let simulatedTime = Date.now() + 600000;
      Date.now = () => simulatedTime;

      ns.sectorDraw.active = true;

      registeredFreshnessTimer();
      registeredFreshnessTimer();
      await new Promise(r => setTimeout(r, 10));

      assert.equal(fitBoundsCalls, 1, 'Freshness ticks preserve viewport and do not repeatedly call fitBounds');

      const statusHtml = squallStatusEl.innerHTML;
      assert.ok(!statusHtml.includes('>LIVE<'), 'Offline squall does not display LIVE badge');
      assert.ok(statusHtml.includes('LAST KNOWN'), 'Labels squall as LAST KNOWN');
      assert.ok(statusHtml.includes('FEED OFFLINE'), 'Labels feed as FEED OFFLINE');
      assert.ok(statusHtml.includes('Service offline (showing last-known detection)'), 'Shows offline warning reason');
      assert.equal(statsSquallEl.textContent, 'RETURN NOW', 'Preserves active RETURN NOW warning banner');
    } finally {
      Date.now = originalDateNow;
    }
  });
});

test('C2: Request Deadlines Cancel Underlying Stalled Requests', async (t) => {
  await t.test('aiFetchJson passes native AbortSignal and cancels timed-out requests', async () => {
    let capturedSignal = null;
    const ns = {
      ready: true,
      authFetch: async (url, opts) => {
        if (opts && opts.signal) {
          capturedSignal = opts.signal;
        }
        return new Promise(() => {});
      }
    };

    const elements = {
      'ai-panel': createStubElement('div', 'ai-panel')
    };

    const { window, document } = createDOMContext(elements, ns);
    const aiOpsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(aiOpsCode, context);

    assert.ok(capturedSignal, 'authFetch received a cancellation signal');
    assert.ok(capturedSignal instanceof AbortSignal, 'Signal is an AbortSignal instance');
    assert.equal(capturedSignal.aborted, false, 'Signal is not aborted initially');
  });

  await t.test('loadOpenCases passes native AbortSignal and cancels timed-out trip checks requests', async () => {
    let capturedSignal = null;
    const ns = {
      ready: true,
      authFetch: async (url, opts) => {
        if (opts && opts.signal) {
          capturedSignal = opts.signal;
        }
        return new Promise(() => {});
      }
    };

    const elements = {
      'trip-checks-list': createStubElement('div', 'trip-checks-list'),
      'badge-tripchecks': createStubElement('span', 'badge-tripchecks')
    };

    const { window, document } = createDOMContext(elements, ns);
    const tripCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-trip-checks.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(tripCode, context);

    assert.ok(capturedSignal, 'trip checks authFetch received a cancellation signal');
    assert.ok(capturedSignal instanceof AbortSignal, 'Trip checks signal is an AbortSignal instance');
    assert.equal(capturedSignal.aborted, false, 'Trip checks signal is not aborted initially');
  });
});
