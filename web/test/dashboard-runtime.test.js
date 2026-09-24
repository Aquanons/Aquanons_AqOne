'use strict';

// node --test web/test/dashboard-runtime.test.js
//
// Runtime regression tests for Phase 1 remediation:
// - F01: HTML sink escaping in actual component renderers (buoy incident feed, sea condition, pin popup)
// - F05: Unsupported broadcast and silent check-in controls are disabled and do not report false success
// - F06: Legacy createAdvisory.html replaces fake localStorage dispatch queue with dashboard redirect
// - F10: System profile renders authenticated identity and does not share origin-wide profile caches between accounts

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const { escapeHtml } = require('../js/dashboard-utils.js');
const profileApi = require('../js/profile.js');

// Minimal DOM Element stub for component rendering tests
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
    src: '',
    _innerHTML: '',
    _textContent: '',
    removeAttribute(name) {
      if (name === 'src') this.src = '';
      else delete this[name];
    },
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
    },
    addEventListener(event, fn) {
      listeners[event] = listeners[event] || [];
      listeners[event].push(fn);
    },
    dispatchEvent(event) {
      const type = typeof event === 'string' ? event : event.type;
      const ev = typeof event === 'string' ? { type: event, target: this } : event;
      (listeners[type] || []).forEach(fn => fn.call(this, ev));
    },
    click() {
      this.dispatchEvent({ type: 'click', target: this });
    },
    closest(selector) {
      return null;
    },
    querySelectorAll() {
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

function createDOMContext(elements = {}, ns = { ready: true }) {
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
    querySelectorAll() { return []; },
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
      const ev = typeof event === 'string' ? { type: event, target: this } : event;
      (docListeners[type] || []).forEach(fn => fn.call(this, ev));
    }
  };
  documentStub.body._ownerDocument = documentStub;
  documentStub.documentElement._ownerDocument = documentStub;
  documentStub.activeElement = documentStub.body;

  for (const [id, el] of Object.entries(elements)) {
    el._ownerDocument = documentStub;
    elMap.set(id, el);
  }

  const windowStub = {
    document: documentStub,
    AqOneDashboardUtils: { escapeHtml },
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
    addEventListener() {},
    removeEventListener() {},
    Date: Date,
    JSON: JSON,
    Number: Number,
    String: String,
    Array: Array,
    Object: Object,
    Math: Math,
    parseFloat: parseFloat,
    parseInt: parseInt,
    AbortController: global.AbortController || AbortController,
    AbortSignal: global.AbortSignal || AbortSignal,
    URLSearchParams: global.URLSearchParams || URLSearchParams,
    fetch: global.fetch || (() => new Promise(() => {}))
  };
  windowStub.window = windowStub;

  return { window: windowStub, document: documentStub };
}

test('Phase 1 - F01: Secure rendering prevents unescaped HTML injection', async (t) => {
  await t.test('incident feed in dashboard-buoy-health.js escapes desc and time', () => {
    const maliciousAlert = {
      desc: '<img src=x onerror="auditProbe()">Boat 12 in distress',
      time: '<script>evil()</script>10:00 AM',
      isLive: true,
      status: 'active',
      type: 'sos',
      lat: 11.7,
      lng: 122.4
    };

    const ns = {
      ready: true,
      OPS_CENTER: [11.7, 122.4],
      OPS_ZOOM: 11,
      shoreStations: [],
      initialBuoys: [],
      vessels: [],
      incidents: [],
      map: { setView() {}, on() {} },
      openPanel() {},
      closePanel() {},
      allAlerts: () => [maliciousAlert],
      alertIcon: () => '<span class="icon"></span>',
      escapeHtml: escapeHtml
    };

    const feedList = createStubElement('div', 'incident-feed-list');
    const { window, document } = createDOMContext({ 'incident-feed-list': feedList }, ns);

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-buoy-health.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.ok(feedList.innerHTML.length > 0, 'feed rendered');
    assert.ok(!feedList.innerHTML.includes('<img src=x onerror="auditProbe()">'), 'raw <img> tag must not be rendered');
    assert.ok(feedList.innerHTML.includes('&lt;img src=x'), 'img tag must be escaped');
    assert.ok(!feedList.innerHTML.includes('<script>evil()</script>'), 'raw <script> tag must not be rendered');
    assert.ok(feedList.innerHTML.includes('&lt;script&gt;evil()&lt;/script&gt;'), 'script tag must be escaped');
  });

  await t.test('resolved feed renders sender reports from /api/sos/recent escaped', async () => {
    const resolvedList = createStubElement('div', 'resolved-feed-list');
    const ns = {
      ready: true,
      OPS_CENTER: [11.7, 122.4],
      OPS_ZOOM: 11,
      shoreStations: [],
      initialBuoys: [],
      vessels: [],
      incidents: [],
      map: { setView() {}, on() {} },
      openPanel() {},
      closePanel() {},
      allAlerts: () => [],
      alertIcon: () => '<span class="icon"></span>',
      escapeHtml: escapeHtml,
      registrationBadgeHtml: (type) => (type && type !== 'none' ? 'Registered Boat' : 'Unregistered Boat'),
      authFetch: () => Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ events: [{
          id: 7,
          vessel_id: 'V007',
          boat: 'Test Boat',
          note: '<img src=x onerror="pwn()">engine failure',
          skipper_name: 'Juan Dela Cruz',
          phone: '+63917',
          license_type: 'boatr',
          fisher_reply: 2,
          created_at: '2026-01-01T00:00:00Z',
          resolved_at: '2026-01-02T00:00:00Z'
        }]})
      })
    };

    const { window, document } = createDOMContext({ 'resolved-feed-list': resolvedList }, ns);
    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-buoy-health.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(code, context);
    await new Promise(r => setTimeout(r, 10));

    assert.ok(resolvedList.innerHTML.includes('Juan Dela Cruz'), 'sender rendered');
    assert.ok(!resolvedList.innerHTML.includes('<img src=x'), 'note must be escaped');
    assert.ok(resolvedList.innerHTML.includes('SAFE NOW'), 'fisher report rendered');
    assert.ok(resolvedList.innerHTML.includes('Registered Boat'), 'registration pill rendered');
  });

  await t.test('sea condition in dashboard-emergency-advisory.js escapes reason and setByName', async () => {
    const seaCurrent = createStubElement('div', 'sea-condition-current');
    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      authFetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
      CURRENT_USER: { id: 'u1', name: 'Operator' },
      showToast() {},
      closePanel() {}
    };
    const fakeAdvisoryService = {
      getAdvisories: () => Promise.resolve([]),
      getAdvisory: () => Promise.resolve(null),
      createAdvisory: () => Promise.resolve(),
      updateAdvisory: () => Promise.resolve(),
      deleteAdvisory: () => Promise.resolve()
    };

    const { window, document } = createDOMContext({ 'sea-condition-current': seaCurrent }, ns);

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-emergency-advisory.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns, AdvisoryService: fakeAdvisoryService }));
    vm.runInContext(code, context);

    assert.equal(typeof ns.renderSeaCondition, 'function', 'renderSeaCondition should be exported');

    ns.renderSeaCondition({
      status: 'Caution — Check Advisories',
      reason: '<img src=x onerror=alert("xss")>High waves',
      set_by_name: '<script>evil()</script>Officer Cruz',
      created_at: new Date().toISOString()
    });

    assert.ok(!seaCurrent.innerHTML.includes('<img src=x'), 'reason must not inject raw <img>');
    assert.ok(seaCurrent.innerHTML.includes('&lt;img src=x'), 'reason must be HTML escaped');
    assert.ok(!seaCurrent.innerHTML.includes('<script>evil()</script>'), 'set_by_name must not inject raw <script>');
    assert.ok(seaCurrent.innerHTML.includes('&lt;script&gt;evil()&lt;/script&gt;'), 'set_by_name must be HTML escaped');
  });

  await t.test('dropLocalPin in dashboard-tools.js escapes CURRENT_USER.name in popup', () => {
    let capturedPopupHtml = null;
    let mapClickHandler = null;
    const fakeL = {
      divIcon: (opts) => opts,
      marker: () => ({
        bindPopup: (html) => { capturedPopupHtml = html; },
        on: () => {},
        openPopup: () => {}
      }),
      layerGroup: () => ({
        addTo: () => ({ clearLayers: () => {}, addLayer: () => {} })
      }),
      polyline: () => ({ addTo: () => {} }),
      polygon: () => ({ addTo: () => {} }),
      circleMarker: () => ({ addTo: () => {} })
    };

    const maliciousUser = { name: '<img src=x onerror=alert(1)>Operator One' };

    const ns = {
      ready: true,
      CURRENT_USER: maliciousUser,
      CURRENT_USER_COLOR: '#0284c7',
      map: {
        on(ev, fn) { if (ev === 'click') mapClickHandler = fn; },
        addLayer() {},
        removeLayer() {}
      },
      tileLayers: {},
      currentBase: {},
      gatewayLayer: {},
      incidentLayer: {},
      buoyLayer: {},
      boundaryLayer: {},
      pinLayer: { addLayer() {}, removeLayer() {} },
      vesselLayer: {},
      coverageLayer: {},
      meshLayer: {},
      squallLayer: {},
      driftLayer: {},
      dangerZoneLayer: {},
      hotspotLayer: {},
      refreshDangerZones() {},
      escapeHtml: escapeHtml
    };

    const { window, document } = createDOMContext({}, ns);

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-tools.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.equal(typeof ns.activatePinMode, 'function', 'activatePinMode should be exported on ns');
    ns.activatePinMode();
    assert.equal(ns.pinModeActive, true, 'pinModeActive should be active');
    assert.ok(typeof mapClickHandler === 'function', 'map click handler should be registered');
    mapClickHandler({ latlng: { lat: 11.71, lng: 122.45 } });

    assert.ok(capturedPopupHtml, 'popup html was generated');
    assert.ok(!capturedPopupHtml.includes('<img src=x'), 'user name must not inject raw <img> tag');
    assert.ok(capturedPopupHtml.includes('&lt;img src=x onerror=alert(1)&gt;Operator One'), 'user name must be escaped');
  });
});

test('Phase 1 - F05: Unsupported broadcast and check-in actions cannot claim success', async (t) => {
  await t.test('broadcast and silent check-in buttons are disabled and do not announce delivery', () => {
    const btnBroadcast = createStubElement('button', 'sos-btn-broadcast');
    const btnCheckin = createStubElement('button', 'sos-btn-checkin');
    const broadcastMsg = createStubElement('div', 'sos-broadcast-msg');

    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      authFetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }),
      map: { setView() {} },
      openActivityDrawer() {},
      showToast() {},
      allAlerts: () => [],
      syncAlertIndicators() {}
    };

    const { window, document } = createDOMContext({
      'sos-btn-broadcast': btnBroadcast,
      'sos-btn-checkin': btnCheckin,
      'sos-broadcast-msg': broadcastMsg
    }, ns);

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-incidents.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.equal(btnBroadcast.disabled, true, 'broadcast button must be initialized disabled');
    assert.equal(btnCheckin.disabled, true, 'check-in button must be initialized disabled');

    // Simulate click on broadcast button
    btnBroadcast.click();
    assert.ok(
      !broadcastMsg.textContent.includes('Broadcast sent to 3 nearby vessels'),
      'broadcast must never claim 3 vessels were messaged over LoRa mesh'
    );
    assert.ok(
      broadcastMsg.textContent.includes('unavailable'),
      'broadcast message must honestly state capability is unavailable'
    );

    // Simulate click on check-in button
    btnCheckin.click();
    assert.ok(
      !broadcastMsg.textContent.includes('Silent check-in request queued at surrounding buoys'),
      'check-in must never claim a request was queued at buoys'
    );
    assert.ok(
      broadcastMsg.textContent.includes('unavailable'),
      'check-in message must honestly state capability is unavailable'
    );
  });
});

test('Phase 1 - F06: Standalone advisory URL redirects to dashboard and has no imaginary queue', async (t) => {
  await t.test('html/createAdvisory.html contains dashboard redirect and no localStorage queue', () => {
    const html = fs.readFileSync(path.join(__dirname, '../html/createAdvisory.html'), 'utf8');

    assert.ok(
      !html.includes('aqone_advisories'),
      'createAdvisory.html must not write or reference fake aqone_advisories queue'
    );
    assert.ok(
      !html.includes('index.html'),
      'createAdvisory.html must not contain broken index.html links'
    );
    assert.ok(
      html.includes('dashboard.html'),
      'createAdvisory.html must redirect or link to dashboard.html'
    );
    assert.ok(
      html.includes('window.location.replace') || html.includes('http-equiv="refresh"'),
      'createAdvisory.html must provide automated redirect'
    );
  });
});

test('Phase 1 - F10: Profile displays authenticated session and prevents origin-wide pollution', async (t) => {
  await t.test('renderUserProfile updates identity fields truthfully', () => {
    const headerName = createStubElement('span', 'header-user-name');
    const headerRole = createStubElement('span', 'header-user-role');
    const headerAvatar = createStubElement('div', 'header-user-avatar');
    const cardName = createStubElement('div', 'profile-card-name');
    const cardRole = createStubElement('div', 'profile-card-role');
    const cardAvatar = createStubElement('div', 'profile-card-avatar');
    const pfName = createStubElement('input', 'pf-fullname');
    const pfRole = createStubElement('input', 'pf-role');
    const pfEmail = createStubElement('input', 'pf-email');

    const dom = createDOMContext({
      'header-user-name': headerName,
      'header-user-role': headerRole,
      'header-user-avatar': headerAvatar,
      'profile-card-name': cardName,
      'profile-card-role': cardRole,
      'profile-card-avatar': cardAvatar,
      'pf-fullname': pfName,
      'pf-role': pfRole,
      'pf-email': pfEmail
    });

    global.document = dom.document;

    // Account 1: MDRRMO Officer
    profileApi.renderUserProfile({
      id: 'usr-1',
      name: 'Maria Santos',
      email: 'officer.santos@newwashington.gov.ph',
      role: 'mdrrmo'
    });

    assert.equal(headerName.textContent, 'Maria Santos');
    assert.equal(headerRole.textContent, 'MDRRMO Officer');
    assert.equal(headerAvatar.textContent, 'MS');
    assert.equal(cardName.textContent, 'Maria Santos');
    assert.equal(cardRole.textContent, 'MDRRMO Officer');
    assert.equal(pfName.value, 'Maria Santos');
    assert.equal(pfEmail.value, 'officer.santos@newwashington.gov.ph');

    // Account 2: Administrator in separate session
    profileApi.renderUserProfile({
      id: 'usr-2',
      name: 'Lenard Angelo',
      email: 'admin@aquanons.ph',
      role: 'admin'
    });

    assert.equal(headerName.textContent, 'Lenard Angelo');
    assert.equal(headerRole.textContent, 'Administrator');
    assert.equal(headerAvatar.textContent, 'LA');
    assert.equal(cardName.textContent, 'Lenard Angelo');
    assert.equal(cardRole.textContent, 'Administrator');
    assert.equal(pfName.value, 'Lenard Angelo');
    assert.equal(pfEmail.value, 'admin@aquanons.ph');

    delete global.document;
  });

  await t.test('profile.js does not store or load aqone_profile_data or fake password updates', () => {
    const profileCode = fs.readFileSync(path.join(__dirname, '../js/profile.js'), 'utf8');

    assert.ok(
      !profileCode.includes('aqone_profile_data'),
      'profile.js must not persist or read origin-wide aqone_profile_data'
    );
    assert.ok(
      !profileCode.includes('aqone_user_avatar'),
      'profile.js must not persist or read origin-wide aqone_user_avatar'
    );
    assert.ok(
      !profileCode.includes('Password updated successfully!'),
      'profile.js must not claim password updates succeeded when no backend endpoint exists'
    );
  });

  await t.test('Systemprofile.html contains no unbacked password form or fake save buttons', () => {
    const profileHtml = fs.readFileSync(path.join(__dirname, '../html/Systemprofile.html'), 'utf8');

    assert.ok(
      !profileHtml.includes('btn-save-security'),
      'Systemprofile.html must not contain fake password submit button'
    );
    assert.ok(
      !profileHtml.includes('btn-save-personal'),
      'Systemprofile.html must not contain fake personal info save button'
    );
    assert.ok(
      !profileHtml.includes('btn-edit-avatar'),
      'Systemprofile.html must not contain unsupported change photo button'
    );
  });
});

test('Phase 2 - F03 & F04: Module wiring and AI panel integration', async (t) => {
  await t.test('openIncidentDrawer renders scored confidence without ReferenceError', () => {
    const confValue = createStubElement('span', 'sos-confidence-value');
    const confFill = createStubElement('span', 'sos-confidence-fill');
    const confBlock = createStubElement('div', 'sos-conf');
    confValue.closest = (sel) => (sel === '.sos-conf' ? confBlock : null);
    const stageEl = createStubElement('span', 'sos-stage');
    const nextContactEl = createStubElement('span', 'sos-next-contact');
    const timerEl = createStubElement('span', 'sos-timer');
    const drawer = createStubElement('div', 'sos-drawer');

    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      authFetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }),
      confidenceColor: (c) => (c >= 80 ? '#e74c3c' : '#f1c40f'),
      responderStatusHtml: () => '',
      formatEta: () => '',
      showToast() {}
    };

    const elements = {
      'sos-confidence-value': confValue,
      'sos-confidence-fill': confFill,
      'sos-conf': confBlock,
      'sos-stage': stageEl,
      'sos-next-contact': nextContactEl,
      'sos-timer': timerEl,
      'sos-drawer': drawer,
      'sos-drawer-header': createStubElement('div', 'sos-drawer-header'),
      'sos-drawer-title': createStubElement('span', 'sos-drawer-title'),
      'sos-drawer-close': createStubElement('button', 'sos-drawer-close'),
      'sos-btn-zoom': createStubElement('button', 'sos-btn-zoom'),
      'sos-btn-acknowledge': createStubElement('button', 'sos-btn-acknowledge'),
      'sos-btn-resolve': createStubElement('button', 'sos-btn-resolve'),
      'sos-btn-broadcast': createStubElement('button', 'sos-btn-broadcast'),
      'sos-btn-checkin': createStubElement('button', 'sos-btn-checkin'),
      'sos-btn-activity': createStubElement('button', 'sos-btn-activity'),
      'sos-broadcast-msg': createStubElement('div', 'sos-broadcast-msg'),
      'sos-timer-label': createStubElement('span', 'sos-timer-label'),
      'sos-vessel-id': createStubElement('span', 'sos-vessel-id'),
      'sos-owner': createStubElement('span', 'sos-owner'),
      'sos-position': createStubElement('span', 'sos-position'),
      'sos-buoy': createStubElement('span', 'sos-buoy'),
      'sos-coverage': createStubElement('span', 'sos-coverage'),
      'sos-boat': createStubElement('span', 'sos-boat'),
      'sos-vessel-verification': createStubElement('span', 'sos-vessel-verification'),
      'sos-shore-contact': createStubElement('span', 'sos-shore-contact'),
      'sos-contact': createStubElement('span', 'sos-contact'),
      'sos-responder-block': createStubElement('div', 'sos-responder-block')
    };

    const { window, document } = createDOMContext(elements, ns);
    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-incidents.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.equal(typeof ns.openIncidentDrawer, 'function');
    ns.openIncidentDrawer({
      alertType: 'sos',
      id: 'SOS-TEST',
      vesselName: 'Bangka One',
      confidence: 85,
      stage: 'STAGE 2 - alert',
      owner: 'Bangka One',
      skipperName: 'Juan Dela Cruz',
      boat: 'Bangka One',
      license: 'boatr NWB-2026-08412',
      phone: '+639171234567',
      vesselVerified: true,
      shoreContactName: 'Ana',
      shoreContactPhone: '09'
    });

    assert.equal(confValue.textContent, '85%');
    assert.equal(confValue.style.color, '#e74c3c');
    assert.equal(confFill.style.width, '85%');
    assert.equal(confFill.style.background, '#e74c3c');
    assert.equal(elements['sos-owner'].textContent, 'Juan Dela Cruz', 'owner row shows the skipper, not the boat');
    assert.equal(elements['sos-boat'].textContent, 'Bangka One');
    assert.equal(elements['sos-vessel-verification'].textContent, 'Verified by MDRRMO');
    assert.equal(elements['sos-contact'].textContent, '+639171234567');
    assert.equal(elements['sos-shore-contact'].textContent, 'Ana - 09');

    // Without any identity data every row still renders an honest placeholder.
    ns.openIncidentDrawer({ alertType: 'sos', id: 'BLANK-TEST', headerText: 'BLANK' });
    assert.equal(elements['sos-owner'].textContent, 'Unknown');
    assert.equal(elements['sos-boat'].textContent, '—');
    assert.equal(elements['sos-vessel-verification'].textContent, 'not yet verified');
    assert.equal(elements['sos-contact'].textContent, 'Not provided');
  });

  await t.test('populated AI risk rows render without ns._escHtml exception and escape content', () => {
    const riskList = createStubElement('div', 'ai-risk-list');
    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      squallStatusHtml: () => '',
      authFetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }),
      aiStatusClass: () => 'status-watch',
      showToast() {}
    };

    const { window, document } = createDOMContext({ 'ai-risk-list': riskList }, ns);
    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {} }) }),
      featureGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {}, getBounds: () => ({ isValid: () => false }) }) })
    };

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.equal(typeof ns.renderRiskFeed, 'function');
    ns.renderRiskFeed([
      {
        vessel_id: '<img src=x>V-999',
        trip_id: 'TRIP-42',
        expected_next_buoy_id: 'B-02',
        status: 'watch',
        score: 0.75,
        factors: [{ name: 'distance', contribution: 0.35, explanation: 'far from shore' }]
      }
    ]);

    assert.ok(riskList.innerHTML.includes('TRIP-42'), 'risk row was rendered');
    assert.ok(!riskList.innerHTML.includes('<img src=x>'), 'vessel_id must not have raw <img>');
    assert.ok(riskList.innerHTML.includes('&lt;img src=x&gt;V-999'), 'vessel_id was safely escaped');
  });

  await t.test('squall watch handles detection with geometry and calls getBounds on featureGroup', () => {
    let fitBoundsCalled = false;
    let getBoundsCalled = false;
    const fakeBounds = {
      isValid: () => true,
      pad: () => fakeBounds
    };
    const squallFeatureGroup = {
      addTo: () => squallFeatureGroup,
      clearLayers: () => {},
      addLayer: () => {},
      getBounds: () => {
        getBoundsCalled = true;
        return fakeBounds;
      }
    };
    const fakeMap = {
      fitBounds: () => { fitBoundsCalled = true; },
      createPane: () => ({ style: {} }),
      getPane: () => ({ style: {} }),
      on: () => {},
      setView: () => {}
    };
    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {}, getLayers: () => [] }) }),
      featureGroup: () => squallFeatureGroup,
      geoJSON: () => ({ addTo: () => {} }),
      polyline: () => ({ addTo: () => {} })
    };

    const squallSummary = createStubElement('div', 'ai-squall-summary');
    const squallStatus = createStubElement('div', 'ai-squall-status');
    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      authFetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }),
      squallStatusHtml: () => '<span>LIVE</span>',
      map: fakeMap,
      squallLayer: squallFeatureGroup
    };

    const { window, document } = createDOMContext({ 'ai-squall-summary': squallSummary, 'ai-squall-status': squallStatus }, ns);
    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.equal(typeof ns.renderSquallWatch, 'function');
    // Test with active polygon
    ns.renderSquallWatch({
      level: 'warning',
      detections: [{
        as_of: new Date().toISOString(),
        affected_polygon: { type: 'Feature', geometry: { type: 'Polygon', coordinates: [] } }
      }]
    }, []);

    assert.ok(getBoundsCalled, 'getBounds was called on squall featureGroup');
    assert.ok(fitBoundsCalled, 'map.fitBounds was invoked with valid bounds');

    // Test detection without geometry (null polygon) - must not crash
    let noGeomBoundsCalled = false;
    squallFeatureGroup.getBounds = () => {
      noGeomBoundsCalled = true;
      return { isValid: () => false };
    };
    fitBoundsCalled = false;
    ns.renderSquallWatch({
      level: 'advisory',
      detections: [{
        as_of: new Date().toISOString(),
        affected_polygon: null
      }]
    }, []);
    assert.ok(noGeomBoundsCalled, 'getBounds called on empty geometry');
    assert.ok(!fitBoundsCalled, 'fitBounds not called when bounds are invalid');
  });
});

test('Phase 2 - F11 & F14: Secondary UI wiring and real session behavior', async (t) => {
  await t.test('squall and drift layer toggles control actual AI groups', () => {
    let squallAdded = false, squallRemoved = false;
    let driftAdded = false, driftRemoved = false;
    let drawAdded = false, drawRemoved = false;

    const mockAiSquallLayer = {
      addTo() { squallAdded = true; squallRemoved = false; },
      remove() {}
    };
    const mockAiContoursLayer = {
      addTo() { driftAdded = true; driftRemoved = false; },
      remove() {}
    };
    const mockAiDrawLayer = {
      addTo() { drawAdded = true; drawRemoved = false; },
      remove() {}
    };

    const mockMap = {
      hasLayer: (l) => {
        if (l === mockAiSquallLayer) return squallAdded;
        if (l === mockAiContoursLayer) return driftAdded;
        if (l === mockAiDrawLayer) return drawAdded;
        return true;
      },
      removeLayer(l) {
        if (l === mockAiSquallLayer) { squallRemoved = true; squallAdded = false; }
        if (l === mockAiContoursLayer) { driftRemoved = true; driftAdded = false; }
        if (l === mockAiDrawLayer) { drawRemoved = true; drawAdded = false; }
      },
      on() {}
    };

    const toggleSquall = createStubElement('input', 'toggle-squall');
    toggleSquall.checked = true;
    const toggleDrift = createStubElement('input', 'toggle-drift');
    toggleDrift.checked = true;

    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {} }) }),
      featureGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {} }) })
    };

    const ns = {
      ready: true,
      map: mockMap,
      aiSquallLayer: mockAiSquallLayer,
      aiContoursLayer: mockAiContoursLayer,
      aiDrawLayer: mockAiDrawLayer,
      pinLayer: { addLayer() {}, removeLayer() {} }
    };

    const { window, document } = createDOMContext({
      'toggle-squall': toggleSquall,
      'toggle-drift': toggleDrift
    }, ns);

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-tools.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    // Initial state: simulated added
    squallAdded = true;
    driftAdded = true;
    drawAdded = true;

    // Toggle squall off
    toggleSquall.checked = false;
    toggleSquall.dispatchEvent('change');
    assert.ok(squallRemoved, 'aiSquallLayer was removed when toggle unchecked');

    // Toggle squall on
    toggleSquall.checked = true;
    toggleSquall.dispatchEvent('change');
    assert.ok(squallAdded, 'aiSquallLayer was re-added when toggle checked');

    // Toggle drift off
    toggleDrift.checked = false;
    toggleDrift.dispatchEvent('change');
    assert.ok(driftRemoved, 'aiContoursLayer was removed when toggle unchecked');
    assert.ok(drawRemoved, 'aiDrawLayer was removed when toggle unchecked');
  });

  await t.test('btn-export has exactly one working handler and does not reference undefined facilities', () => {
    const profilePillCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-profile-pill.js'), 'utf8');
    assert.ok(!profilePillCode.includes('facilities.length'), 'dashboard-profile-pill.js must not contain duplicate broken export handler');
    assert.ok(!profilePillCode.includes("getElementById('btn-export')"), 'btn-export handler must not be duplicated in profile pill');
    assert.ok(!profilePillCode.includes('aqone-dashboard-export.json'), 'duplicate export json must not be in profile pill');

    const buoyHealthCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-buoy-health.js'), 'utf8');
    assert.ok(buoyHealthCode.includes('btn-export'), 'dashboard-buoy-health.js preserves functioning export handler');
    assert.ok(buoyHealthCode.includes('aqone-sar-console-export.json'), 'dashboard-buoy-health.js exports console JSON');
  });

  await t.test('overdue vessel (priority 0) sorts first before in-coverage and out-of-coverage', () => {
    const vesselList = createStubElement('div', 'vessel-list');
    const fakeMarker = {
      addTo: () => fakeMarker,
      bindPopup: () => fakeMarker,
      on: () => fakeMarker,
      openPopup: () => fakeMarker
    };
    const fakeL = {
      divIcon: () => ({}),
      marker: () => fakeMarker,
      layerGroup: () => ({ addLayer: () => {} })
    };

    const ns = {
      ready: true,
      map: { on() {}, setView() {} },
      vesselLayer: { addLayer() {} },
      createOverdueIcon: () => ({}),
      createMarkerIcon: () => ({}),
      makePopup: () => '',
      allAlerts: () => [],
      alertBadge: () => ({ cssClass: '', text: '' })
    };

    const { window, document } = createDOMContext({
      'vessel-list': vesselList,
      'alert-list': createStubElement('div', 'alert-list')
    }, ns);
    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-vessels-alerts.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.equal(typeof ns.renderVessels, 'function');
    ns.renderVessels('all');

    // Check row order in HTML
    const html = vesselList.innerHTML;
    const overduePos = html.indexOf('vessel-overdue');
    assert.ok(overduePos !== -1, 'overdue vessel row rendered');
    const firstRowEnd = html.indexOf('</div>\n      </div>');
    assert.ok(overduePos < firstRowEnd, 'overdue vessel must be the very first row in vessel list');
  });

  await t.test('script.js preserves password spaces and clears demo state upon real login', async () => {
    const script = require('../js/script.js');
    let postedData = null;

    global.fetch = async (url, options) => {
      postedData = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({ token: 'REAL-TOKEN', user: { id: 'u1', name: 'Officer' } })
      };
    };

    const emailEl = createStubElement('input', 'email');
    emailEl.value = '  officer@mdrrmo.gov.ph  ';
    const passEl = createStubElement('input', 'password');
    passEl.value = '  secret Pass 123  ';

    const testSessionStorage = {
      data: new Map([['aqoneDemoBypassActive', '1']]),
      getItem(k) { return this.data.get(k); },
      setItem(k, v) { this.data.set(k, String(v)); },
      removeItem(k) { this.data.delete(k); }
    };

    global.document = {
      getElementById(id) {
        if (id === 'email') return emailEl;
        if (id === 'password') return passEl;
        return null;
      }
    };
    global.sessionStorage = testSessionStorage;
    global.window = { location: { href: '' } };

    await script.handleLogin({ preventDefault() {} });

    assert.equal(postedData.email, 'officer@mdrrmo.gov.ph', 'email is trimmed');
    assert.equal(postedData.password, '  secret Pass 123  ', 'password spaces must be preserved');
    assert.equal(testSessionStorage.getItem('aqoneDemoBypassActive'), undefined, 'demo bypass flag was removed on real login');
    assert.equal(testSessionStorage.getItem('aqoneToken'), 'REAL-TOKEN', 'real token set');
  });

  await t.test('dashboard-core.js clearSession removes aqoneDemoBypassActive', () => {
    const coreCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-core.js'), 'utf8');
    assert.ok(
      coreCode.includes("sessionStorage.removeItem('aqoneDemoBypassActive');"),
      'clearSession must remove aqoneDemoBypassActive'
    );
  });
});

test('Phase 3 - Safety data freshness, numerical validation, and demo provenance', async (t) => {
  await t.test('classifySafety and renderWeatherCard enforce numerical validation, adverse codes, and stale demotion', () => {
    const wcBody = createStubElement('div', 'wc-body');
    const forecastBody = createStubElement('div', 'forecast-body');
    const rainfallCard = createStubElement('div', 'rainfall-card');
    const ns = {
      ready: true,
      escapeHtml: escapeHtml
    };

    const { window, document } = createDOMContext({
      'wc-body': wcBody,
      'forecast-body': forecastBody,
      'rainfall-card': rainfallCard
    }, ns);

    // Weather thresholds and tiers
    const weatherCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-shortcuts-weather.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(weatherCode, context);

    assert.equal(typeof ns.classifySafety, 'function');
    assert.equal(typeof ns.renderWeatherCard, 'function');

    // 1. Missing or null inputs cannot certify lower risk
    assert.equal(ns.classifySafety(null, null).cls, 'wc-safety-unknown', 'null wind and waves must return unknown');
    assert.equal(ns.classifySafety(12, null).cls, 'wc-safety-unknown', 'missing wave cannot certify lower risk');
    assert.equal(ns.classifySafety(null, 0.4).cls, 'wc-safety-unknown', 'missing wind cannot certify lower risk');

    // 2. Negative inputs are rejected
    assert.equal(ns.classifySafety(-5, 0.4).cls, 'wc-safety-unknown', 'negative wind must be rejected');
    assert.equal(ns.classifySafety(12, -0.5).cls, 'wc-safety-unknown', 'negative wave must be rejected');

    // 3. Known adverse thunderstorm code >= 95 preserves caution even with missing observations
    assert.equal(ns.classifySafety(null, null, 95).cls, 'wc-safety-caution', 'thunderstorm code 95 must trigger caution even if wind/wave missing');
    assert.equal(ns.classifySafety(10, 0.3, 96).cls, 'wc-safety-caution', 'thunderstorm code 96 must override otherwise calm wind/wave');

    // 4. Valid inputs evaluate correctly
    assert.equal(ns.classifySafety(10, 0.4, 0).cls, 'wc-safety-safe', 'calm conditions return safe');
    assert.equal(ns.classifySafety(25, 0.4, 0).cls, 'wc-safety-caution', 'wind >= 20 km/h returns caution');
    assert.equal(ns.classifySafety(45, 0.4, 0).cls, 'wc-safety-advisory', 'wind >= 40 km/h returns advisory');
    assert.equal(ns.classifySafety(10, 3.2, 0).cls, 'wc-safety-danger', 'waves >= 3.0 m returns danger');

    // 5. renderWeatherCard handles missing wavePeriod without crashing
    assert.doesNotThrow(() => {
      ns.renderWeatherCard(
        { current: { temperature_2m: 28, apparent_temperature: 30, wind_speed_10m: 12, wind_gusts_10m: 15, weather_code: 1, time: new Date().toISOString() } },
        { current: { wave_height: 0.8, wave_period: null } },
        { stale: false }
      );
    }, 'renderWeatherCard must not crash when wave_period is null');
    assert.ok(wcBody.innerHTML.includes('0.80 m') && wcBody.innerHTML.includes('\u2014'), 'wave height is rendered with placeholder for period');

    // 6. Stale cache downgrades safe condition to unknown
    ns.renderWeatherCard(
      { current: { temperature_2m: 28, apparent_temperature: 30, wind_speed_10m: 10, wind_gusts_10m: 12, weather_code: 0, time: new Date().toISOString() } },
      { current: { wave_height: 0.5, wave_period: 6.0 } },
      { stale: true }
    );
    assert.ok(wcBody.innerHTML.includes('CONDITIONS UNKNOWN'), 'stale cache must downgrade safe tier to unknown');
    assert.ok(wcBody.innerHTML.includes('LAST KNOWN'), 'stale cache must display LAST KNOWN banner');
  });

  await t.test('dangerZonePredictor strictly validates features and scopes overrides to demo session', () => {
    const modelCode = fs.readFileSync(path.join(__dirname, '../js/dangerZoneModel.js'), 'utf8');
    const predictorCode = fs.readFileSync(path.join(__dirname, '../js/dangerZonePredictor.js'), 'utf8');

    const testSessionStorage = {
      data: new Map(),
      getItem(k) { return this.data.get(k); },
      setItem(k, v) { this.data.set(k, String(v)); },
      removeItem(k) { this.data.delete(k); }
    };
    const testLocalStorage = {
      data: new Map([['AQONE_WEATHER_BASE', 'http://malicious.origin/weather']]),
      getItem(k) { return this.data.get(k); }
    };

    const windowStub = {
      sessionStorage: testSessionStorage,
      localStorage: testLocalStorage,
      URLSearchParams: global.URLSearchParams,
      Date: Date,
      Math: Math,
      Number: Number,
      String: String,
      Array: Array,
      Object: Object
    };
    windowStub.window = windowStub;

    const context = vm.createContext(windowStub);
    vm.runInContext(modelCode, context);
    vm.runInContext(predictorCode, context);

    const predictor = windowStub.AqOneDangerZonePredictor;
    assert.equal(typeof predictor.predictProbability, 'function');

    // 1. Missing feature throws
    assert.throws(() => {
      predictor.predictProbability({ wave_height: 1.0 });
    }, /Missing live feature/, 'predictProbability must throw on missing feature');

    // 2. Null / non-finite feature throws
    assert.throws(() => {
      predictor.predictProbability({
        wave_height: null,
        wave_period: 6,
        wind_speed_10m: 15,
        wind_gusts_10m: 20,
        pressure_msl: 1012,
        precipitation: 0,
        depth_m: 10,
        distance_to_shore_km: 2,
        month_sin: 0,
        month_cos: 1
      });
    }, /Missing live feature/, 'predictProbability must throw on null feature');

    // 3. Negative wave height throws
    assert.throws(() => {
      predictor.predictProbability({
        wind_speed_10m: 15,
        wind_gusts_10m: 20,
        precipitation: 0,
        weather_code: 0,
        wave_height: -1.0,
        wave_period: 6,
        depth_m: 10,
        month_sin: 0,
        month_cos: 1
      });
    }, /Physically invalid negative feature/, 'predictProbability must throw on negative wave height');

    // 4. Valid inputs produce numeric probability in [0, 1]
    const validProb = predictor.predictProbability({
      wind_speed_10m: 18,
      wind_gusts_10m: 25,
      precipitation: 0.5,
      weather_code: 0,
      wave_height: 1.2,
      wave_period: 6.5,
      depth_m: 12,
      month_sin: 0,
      month_cos: 1
    });
    assert.equal(typeof validProb, 'number');
    assert.ok(validProb >= 0 && validProb <= 1, 'probability must be within [0, 1]');
  });

  await t.test('liveAlertFromEvent correctly assigns isLive and isSynthetic provenance', () => {
    const utils = require('../js/dashboard-utils.js');
    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      authFetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }),
      liveSosMarkers: {},
      allAlerts: () => [],
      classifyFreshness: utils.classifyFreshness,
      freshnessLabel: utils.freshnessLabel
    };

    const { window, document } = createDOMContext({
      'sync-indicator': createStubElement('span', 'sync-indicator'),
      'sync-text': createStubElement('span', 'sync-text'),
      'banner-live-time': createStubElement('span', 'banner-live-time')
    }, ns);

    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {} }) }),
      divIcon: () => ({})
    };

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-live-sos.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    assert.equal(typeof ns.liveAlertFromEvent, 'function');

    // Real event: is_synthetic === false
    const realAlert = ns.liveAlertFromEvent({
      id: 'real-sos-1',
      boat: 'Elena Real',
      latitude: 11.71,
      longitude: 122.42,
      created_at: new Date().toISOString(),
      is_synthetic: false,
      skipper_name: 'Juan Dela Cruz',
      license_type: 'boatr',
      license_number: 'NWB-2026-08412',
      phone: '+639171234567'
    });
    assert.equal(realAlert.isLive, true, 'is_synthetic: false must be marked isLive: true');
    assert.equal(realAlert.isSynthetic, false);
    assert.equal(realAlert.sosEventId, 'real-sos-1');
    assert.equal(realAlert.drawerData.headerText, 'SOS — DISTRESS CALL RECEIVED');
    assert.equal(realAlert.drawerData.skipperName, 'Juan Dela Cruz');
    assert.equal(realAlert.drawerData.owner, 'Juan Dela Cruz', 'owner must be the skipper once a profile is on file');
    assert.equal(realAlert.drawerData.boat, 'Elena Real');
    assert.equal(realAlert.drawerData.license, undefined, 'license text must not be turned into a trust display');
    assert.equal(realAlert.drawerData.phone, '+639171234567');

    // Synthetic event: is_synthetic === true
    const demoAlert = ns.liveAlertFromEvent({
      id: 'demo-sos-2',
      boat: 'Scripted Demo Boat',
      latitude: 11.71,
      longitude: 122.42,
      created_at: new Date().toISOString(),
      is_synthetic: true
    });
    assert.equal(demoAlert.isLive, false, 'is_synthetic: true must be marked isLive: false');
    assert.equal(demoAlert.isSynthetic, true);
    assert.equal(demoAlert.sosEventId, 'demo-sos-2', 'real backend ID must be preserved on synthetic row');
    assert.equal(demoAlert.drawerData.headerText, 'DEMO SOS — SIMULATED DISTRESS CALL');
    assert.equal(demoAlert.drawerData.skipperName, null);
    assert.equal(demoAlert.drawerData.owner, null, 'owner stays null without a profile instead of impersonating the boat');
    assert.equal(demoAlert.drawerData.boat, 'Scripted Demo Boat');
    assert.equal(demoAlert.drawerData.license, undefined, 'license is not part of the dashboard trust display');
    assert.equal(demoAlert.drawerData.phone, null);

    // Missing provenance: is_synthetic undefined
    const unknownAlert = ns.liveAlertFromEvent({
      id: 'legacy-sos-3',
      boat: 'Legacy Boat',
      latitude: 11.71,
      longitude: 122.42,
      created_at: new Date().toISOString()
    });
    assert.equal(unknownAlert.isLive, false, 'missing provenance must default to unverified (not real LIVE)');
    assert.equal(unknownAlert.sosEventId, 'legacy-sos-3');
  });

  await t.test('SOS summary text avoids ALL CLEAR when active or unresolved SOS exists, and highlights STILL_IN_DANGER', () => {
    const sosStatusEl = createStubElement('span', 'stats-sos-status');
    const badgeAlerts = createStubElement('span', 'badge-alerts');
    const bannerCount = createStubElement('span', 'banner-alert-count');
    const alertList = createStubElement('div', 'alert-list');
    const liveBanner = createStubElement('div', 'live-alert-banner');

    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      allAlerts: () => [],
      map: { on() {}, setView() {}, addLayer() {} },
      vesselLayer: { addLayer() {}, removeLayer() {} },
      createOverdueIcon: () => ({}),
      createMarkerIcon: () => ({}),
      makePopup: () => '',
      vesselStatusBadge: () => ({ text: '', cls: '' }),
      alertBadge: () => ({ text: '', cssClass: '' })
    };

    const { window, document } = createDOMContext({
      'stats-sos-status': sosStatusEl,
      'badge-alerts': badgeAlerts,
      'banner-alert-count': bannerCount,
      'alert-list': alertList,
      'live-alert-banner': liveBanner,
      'vessel-filters': createStubElement('div', 'vessel-filters'),
      'vessel-list': createStubElement('div', 'vessel-list'),
      'badge-vessels': createStubElement('span', 'badge-vessels')
    }, ns);

    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ addLayer: () => {} }) }),
      marker: () => ({ addTo: () => ({}), bindPopup: () => ({}), on: () => ({}) })
    };

    const code = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-vessels-alerts.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(code, context);

    // Initial state: no live alerts -> NO UNACKNOWLEDGED SOS (never ALL CLEAR)
    assert.equal(sosStatusEl.textContent, 'NO UNACKNOWLEDGED SOS', 'no alerts must display NO UNACKNOWLEDGED SOS');

    // Case 1: Active unacknowledged SOS
    ns.liveAlerts.length = 0;
    ns.liveAlerts.push({ status: 'active', desc: 'SOS 1', isLive: true });
    ns.syncAlertIndicators();
    assert.equal(sosStatusEl.textContent, '1 UNACKNOWLEDGED SOS');
    assert.equal(sosStatusEl.className, 'metric-status metric-status-danger');

    // Case 2: Acknowledged but unresolved SOS
    ns.liveAlerts.length = 0;
    ns.liveAlerts.push({ status: 'acknowledged', desc: 'SOS 1', isLive: true });
    ns.syncAlertIndicators();
    assert.equal(sosStatusEl.textContent, '1 UNRESOLVED (ACKNOWLEDGED)');
    assert.equal(sosStatusEl.className, 'metric-status metric-status-caution');

    // Case 3: Acknowledged SOS with fisher reply 1 (STILL_IN_DANGER)
    ns.liveAlerts.length = 0;
    ns.liveAlerts.push({ status: 'acknowledged', fisherReply: 1, desc: 'SOS 1', isLive: true });
    ns.syncAlertIndicators();
    assert.equal(sosStatusEl.textContent, 'STILL IN DANGER (1 unresolved)');
    assert.equal(sosStatusEl.className, 'metric-status metric-status-danger');

    // Check alertStatusPill with fisherReply 1
    const pillHtml = ns.alertStatusPill('acknowledged', 1);
    assert.ok(pillHtml.includes('Still in Danger'), 'pill must show Still in Danger');
    assert.ok(pillHtml.includes('status-danger'), 'pill must have status-danger class');
  });

  await t.test('trip checks and risk feed distinguish unavailable service from empty data', () => {
    const utils = require('../js/dashboard-utils.js');

    // 1. tripChecksListHtml
    const unavailableHtml = utils.tripChecksListHtml(null);
    assert.ok(unavailableHtml.includes('trip-checks-unavailable'), 'null cases must render unavailable notice');
    assert.ok(unavailableHtml.includes('unable to reach the anomaly detection service'));

    const emptyHtml = utils.tripChecksListHtml([]);
    assert.ok(!emptyHtml.includes('trip-checks-unavailable'), 'empty array must not render unavailable');
    assert.ok(emptyHtml.includes('No trip checks right now'));

    // 2. renderRiskFeed in dashboard-ai-ops.js
    const riskList = createStubElement('div', 'ai-risk-list');
    const riskCount = createStubElement('span', 'ai-risk-count');
    const ns = {
      ready: true,
      escapeHtml: escapeHtml,
      authFetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }),
      squallStatusHtml: () => '',
      aiStatusClass: () => 'status-normal'
    };

    const { window, document } = createDOMContext({
      'ai-risk-list': riskList,
      'ai-risk-count': riskCount
    }, ns);

    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {} }) }),
      featureGroup: () => ({ addTo: () => ({ clearLayers: () => {}, addLayer: () => {}, getBounds: () => ({ isValid: () => false }) }) })
    };

    const aiOpsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(aiOpsCode, context);

    // Render null -> unavailable
    ns.renderRiskFeed(null);
    assert.ok(riskList.innerHTML.includes('ai-unavailable-state'), 'null rows must render ai-unavailable-state');
    assert.equal(riskCount.textContent, '--', 'count must be -- when service is unavailable');

    // Render empty array -> 0 active rows
    ns.renderRiskFeed([]);
    assert.ok(!riskList.innerHTML.includes('ai-unavailable-state'), 'empty rows must not render unavailable state');
    assert.equal(riskCount.textContent, '0', 'count must be 0 when feed is empty');
  });

  await t.test('compact incident feed and buoy network render DEMO badges and honest offline baseline', () => {
    const feedList = createStubElement('div', 'incident-feed-list');
    const ns = {
      ready: true,
      OPS_CENTER: [11.7, 122.4],
      OPS_ZOOM: 11,
      shoreStations: [],
      initialBuoys: [],
      vessels: [],
      incidents: [],
      map: { setView() {}, on() {} },
      openPanel() {},
      closePanel() {},
      allAlerts: () => [
        { desc: 'Sample Incident', time: '10m ago', isLive: false, type: 'sos', lat: 11.7, lng: 122.4 }
      ],
      alertIcon: () => '<span class="icon"></span>',
      escapeHtml: escapeHtml
    };

    const { window, document } = createDOMContext({ 'incident-feed-list': feedList }, ns);
    const buoyHealthCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-buoy-health.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(buoyHealthCode, context);

    // Verify DEMO badge rendered on sample row
    assert.ok(feedList.innerHTML.includes('alert-demo-badge'), 'sample alert must render DEMO badge');
    assert.ok(feedList.innerHTML.includes('DEMO'), 'badge text must be DEMO');

    // Verify buoy baseline text in dashboard.html and buoy-health.js
    const dashboardHtml = fs.readFileSync(path.join(__dirname, '../html/dashboard.html'), 'utf8');
    assert.ok(
      dashboardHtml.includes('Sample buoy network baseline (unpolled offline data)'),
      'dashboard.html must contain honest baseline label instead of fake Last synced ticker'
    );
    assert.ok(
      buoyHealthCode.includes('Sample buoy network baseline (unpolled offline data)'),
      'dashboard-buoy-health.js must contain honest baseline label'
    );
  });
});

test('Phase 4 - Incident actions, audit reads, and keyboard stabilization', async (t) => {
  await t.test('loadActiveSos ordering: older poll resolving late does not overwrite newer state or freshness', async () => {
    let callCount = 0;
    let resolveFirst;
    let resolveSecond;
    const promise1 = new Promise((resolve) => { resolveFirst = resolve; });
    const promise2 = new Promise((resolve) => { resolveSecond = resolve; });

    const liveAlerts = [];
    const syncStatusEl = createStubElement('div', 'sync-status');
    const syncTextEl = createStubElement('span', 'sync-text');
    const bannerTimeEl = createStubElement('span');
    bannerTimeEl.className = 'banner-time';
    const statsFeedStatusEl = createStubElement('span', 'stats-feed-status');

    const ns = {
      ready: true,
      liveAlerts: liveAlerts,
      escapeHtml: escapeHtml,
      classifyFreshness: () => 'live',
      freshnessLabel: () => 'LIVE',
      authFetch: () => {
        callCount++;
        if (callCount === 1) return promise1;
        return promise2;
      },
      map: { setView() {} },
      showToast() {},
      syncAlertIndicators() {},
      renderIncidentFeed() {},
      refreshOpenDrawer() {}
    };

    const { window, document } = createDOMContext({
      'sync-status': syncStatusEl,
      'sync-text': syncTextEl,
      'stats-feed-status': statsFeedStatusEl
    }, ns);
    document.querySelector = (sel) => (sel === '.banner-time' ? bannerTimeEl : null);

    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ addLayer: () => {}, removeLayer: () => {} }) }),
      divIcon: () => ({}),
      marker: () => ({ bindTooltip: () => {}, off: () => {}, on: () => {}, setLatLng: () => {} })
    };

    const liveSosCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-live-sos.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(liveSosCode, context);

    // Call 1 was initiated by script load.
    // Now trigger Call 2.
    const poll2 = ns.loadActiveSos();

    // Resolve Call 2 first with newer event SOS-2
    resolveSecond({
      ok: true,
      json: () => Promise.resolve({
        events: [{
          id: 'SOS-2',
          boat: 'Newer Vessel',
          latitude: 11.7,
          longitude: 122.4,
          created_at: new Date().toISOString(),
          is_synthetic: false
        }]
      })
    });
    await poll2;

    assert.equal(ns.liveAlerts.length, 1);
    assert.equal(ns.liveAlerts[0].sosEventId, 'SOS-2');
    assert.equal(syncTextEl.textContent, 'LIVE');

    // Wait a brief tick to ensure Date.now() advances if called again
    await new Promise(r => setTimeout(r, 10));

    // Resolve Call 1 with older event SOS-1
    resolveFirst({
      ok: true,
      json: () => Promise.resolve({
        events: [{
          id: 'SOS-1',
          boat: 'Older Vessel',
          latitude: 11.6,
          longitude: 122.3,
          created_at: new Date(Date.now() - 60000).toISOString(),
          is_synthetic: false
        }]
      })
    });
    // Wait for promise chain to settle
    await new Promise(r => setTimeout(r, 10));

    // Must NOT have overwritten SOS-2
    assert.equal(ns.liveAlerts.length, 1);
    assert.equal(ns.liveAlerts[0].sosEventId, 'SOS-2', 'Newer accepted state must not be overwritten by older response');
    assert.equal(syncTextEl.textContent, 'LIVE');
  });

  await t.test('loadActiveSos rejects malformed payloads and preserves last-known live alerts', async () => {
    const liveAlerts = [
      { sosEventId: 'SOS-RETAINED', desc: 'Retained SOS', time: '1m ago', isLive: true }
    ];
    const ns = {
      ready: true,
      liveAlerts: liveAlerts,
      escapeHtml: escapeHtml,
      classifyFreshness: () => 'live',
      freshnessLabel: () => 'LIVE',
      authFetch: () => Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ missing_events: true }) // Not an array!
      }),
      map: { setView() {} },
      showToast() {},
      syncAlertIndicators() {},
      renderIncidentFeed() {},
      refreshOpenDrawer() {}
    };

    const { window, document } = createDOMContext({}, ns);
    const fakeL = {
      layerGroup: () => ({ addTo: () => ({ addLayer: () => {}, removeLayer: () => {} }) }),
      divIcon: () => ({}),
      marker: () => ({ bindTooltip: () => {}, off: () => {}, on: () => {}, setLatLng: () => {} })
    };

    const liveSosCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-live-sos.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, L: fakeL, AqOneDashboard: ns }));
    vm.runInContext(liveSosCode, context);

    await new Promise(r => setTimeout(r, 10));

    // liveAlerts must still contain SOS-RETAINED and not be emptied
    assert.equal(ns.liveAlerts.length, 1);
    assert.equal(ns.liveAlerts[0].sosEventId, 'SOS-RETAINED');
  });

  await t.test('refreshOpenDrawer retires drawer when incident leaves authoritative active list', () => {
    const drawer = createStubElement('div', 'sos-drawer');
    drawer.classList.add('open');
    const ackOverlay = createStubElement('div', 'ack-modal-overlay');
    ackOverlay.hidden = false;

    let toastTitle = '';
    const ns = {
      ready: true,
      allAlerts: () => [], // Empty active feed!
      showToast: (title) => { toastTitle = title; },
      responderStatusHtml: () => '',
      formatEta: () => '',
      confidenceColor: () => '#e74c3c'
    };

    const elements = {
      'sos-drawer': drawer,
      'sos-drawer-header': createStubElement('div', 'sos-drawer-header'),
      'sos-drawer-title': createStubElement('span', 'sos-drawer-title'),
      'sos-drawer-close': createStubElement('button', 'sos-drawer-close'),
      'sos-timer': createStubElement('span', 'sos-timer'),
      'sos-timer-label': createStubElement('span', 'sos-timer-label'),
      'sos-vessel-id': createStubElement('span', 'sos-vessel-id'),
      'sos-owner': createStubElement('span', 'sos-owner'),
      'sos-position': createStubElement('span', 'sos-position'),
      'sos-buoy': createStubElement('span', 'sos-buoy'),
      'sos-coverage': createStubElement('span', 'sos-coverage'),
      'sos-stage': createStubElement('span', 'sos-stage'),
      'sos-next-contact': createStubElement('span', 'sos-next-contact'),
      'sos-confidence-value': createStubElement('span', 'sos-confidence-value'),
      'sos-confidence-fill': createStubElement('span', 'sos-confidence-fill'),
      'sos-btn-zoom': createStubElement('button', 'sos-btn-zoom'),
      'sos-btn-acknowledge': createStubElement('button', 'sos-btn-acknowledge'),
      'sos-btn-resolve': createStubElement('button', 'sos-btn-resolve'),
      'sos-btn-broadcast': createStubElement('button', 'sos-btn-broadcast'),
      'sos-btn-checkin': createStubElement('button', 'sos-btn-checkin'),
      'sos-btn-activity': createStubElement('button', 'sos-btn-activity'),
      'sos-broadcast-msg': createStubElement('div', 'sos-broadcast-msg'),
      'sos-responder-block': createStubElement('div', 'sos-responder-block'),
      'ack-modal-overlay': ackOverlay,
      'ack-modal-vessel': createStubElement('p', 'ack-modal-vessel'),
      'ack-status': createStubElement('select', 'ack-status'),
      'ack-eta': createStubElement('input', 'ack-eta'),
      'ack-note': createStubElement('input', 'ack-note'),
      'ack-btn-confirm': createStubElement('button', 'ack-btn-confirm'),
      'ack-btn-cancel': createStubElement('button', 'ack-btn-cancel'),
      'ack-modal-close': createStubElement('button', 'ack-modal-close')
    };

    const { window, document } = createDOMContext(elements, ns);
    const incidentsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-incidents.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(incidentsCode, context);

    // Open drawer with SOS-A
    ns.openIncidentDrawer({ alertType: 'sos', sosEventId: 'SOS-A', headerText: 'SOS A' }, null);
    assert.ok(drawer.classList.contains('open'));

    // Feed refreshes, SOS-A is missing from allAlerts()
    ns.refreshOpenDrawer();

    assert.equal(drawer.classList.contains('open'), false, 'Drawer must be closed when event leaves feed');
    assert.equal(ackOverlay.hidden, true, 'Ack modal must close when incident is retired');
    assert.equal(toastTitle, 'Incident closed');
  });

  await t.test('ack modal captures target and prevents background case switching', async () => {
    const drawer = createStubElement('div', 'sos-drawer');
    drawer.classList.add('open');
    const ackOverlay = createStubElement('div', 'ack-modal-overlay');
    ackOverlay.hidden = true;
    const ackVessel = createStubElement('p', 'ack-modal-vessel');
    const ackConfirmBtn = createStubElement('button', 'ack-btn-confirm');
    const ackEta = createStubElement('input', 'ack-eta');
    ackEta.value = '25';
    const ackStatus = createStubElement('select', 'ack-status');
    ackStatus.value = '2';
    const ackNote = createStubElement('input', 'ack-note');
    ackNote.value = 'On our way';

    let requestedUrl = '';
    let requestBody = null;
    const ns = {
      ready: true,
      allAlerts: () => [],
      authFetch: (url, opts) => {
        requestedUrl = url;
        requestBody = opts && JSON.parse(opts.body);
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) });
      },
      loadActiveSos: () => Promise.resolve(),
      showToast: () => {},
      responderStatusHtml: () => '',
      formatEta: () => '',
      confidenceColor: () => '#e74c3c'
    };

    const elements = {
      'sos-drawer': drawer,
      'sos-drawer-header': createStubElement('div', 'sos-drawer-header'),
      'sos-drawer-title': createStubElement('span', 'sos-drawer-title'),
      'sos-drawer-close': createStubElement('button', 'sos-drawer-close'),
      'sos-timer': createStubElement('span', 'sos-timer'),
      'sos-timer-label': createStubElement('span', 'sos-timer-label'),
      'sos-vessel-id': createStubElement('span', 'sos-vessel-id'),
      'sos-owner': createStubElement('span', 'sos-owner'),
      'sos-position': createStubElement('span', 'sos-position'),
      'sos-buoy': createStubElement('span', 'sos-buoy'),
      'sos-coverage': createStubElement('span', 'sos-coverage'),
      'sos-stage': createStubElement('span', 'sos-stage'),
      'sos-next-contact': createStubElement('span', 'sos-next-contact'),
      'sos-confidence-value': createStubElement('span', 'sos-confidence-value'),
      'sos-confidence-fill': createStubElement('span', 'sos-confidence-fill'),
      'sos-btn-zoom': createStubElement('button', 'sos-btn-zoom'),
      'sos-btn-acknowledge': createStubElement('button', 'sos-btn-acknowledge'),
      'sos-btn-resolve': createStubElement('button', 'sos-btn-resolve'),
      'sos-btn-broadcast': createStubElement('button', 'sos-btn-broadcast'),
      'sos-btn-checkin': createStubElement('button', 'sos-btn-checkin'),
      'sos-btn-activity': createStubElement('button', 'sos-btn-activity'),
      'sos-broadcast-msg': createStubElement('div', 'sos-broadcast-msg'),
      'sos-responder-block': createStubElement('div', 'sos-responder-block'),
      'ack-modal-overlay': ackOverlay,
      'ack-modal-vessel': ackVessel,
      'ack-status': ackStatus,
      'ack-eta': ackEta,
      'ack-note': ackNote,
      'ack-btn-confirm': ackConfirmBtn,
      'ack-btn-cancel': createStubElement('button', 'ack-btn-cancel'),
      'ack-modal-close': createStubElement('button', 'ack-modal-close')
    };

    const { window, document } = createDOMContext(elements, ns);
    const incidentsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-incidents.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(incidentsCode, context);

    // Open drawer with Case A
    ns.openIncidentDrawer({
      alertType: 'sos',
      sosEventId: 'CASE-A',
      headerText: 'Case A',
      desc: 'Bangka Alpha',
      vesselId: 'V-001'
    }, null);

    // Open acknowledgment modal
    ns.openAckModal();
    assert.equal(ackOverlay.hidden, false);
    assert.equal(ackVessel.textContent, 'Bangka Alpha');
    ackEta.value = '25';
    ackNote.value = 'On our way';

    // Attempt background switch to Case B while modal is open
    ns.openIncidentDrawer({
      alertType: 'sos',
      sosEventId: 'CASE-B',
      headerText: 'Case B',
      desc: 'Bangka Beta',
      vesselId: 'V-002'
    }, null);

    // Submit acknowledgment - must still be locked to Case A
    ackConfirmBtn.click();
    await new Promise(r => setTimeout(r, 10));

    assert.equal(requestedUrl, '/api/sos/CASE-A/acknowledge', 'Acknowledge request must target original Case A');
    assert.equal(requestBody.eta_minutes, 25);
    assert.equal(requestBody.responder_note, 'On our way');
    assert.equal(ackOverlay.hidden, true, 'Ack modal must close on success');
  });

  await t.test('keyboard shortcuts ignore editable elements and follow Escape priority', () => {
    let fullscreenClicked = false;
    const fullscreenBtn = createStubElement('button', 'btn-fullscreen');
    fullscreenBtn.click = () => { fullscreenClicked = true; };

    const drawer = createStubElement('div', 'sos-drawer');
    const ackOverlay = createStubElement('div', 'ack-modal-overlay');
    ackOverlay.hidden = false; // Ack modal is open on top

    const triggerBtn = createStubElement('button', 'ack-trigger-btn');
    const noteTextarea = createStubElement('textarea', 'note-textarea');

    const ns = {
      ready: true,
      ackOverlay: ackOverlay,
      closeAckModal: () => {
        ackOverlay.hidden = true;
        if (triggerBtn) triggerBtn.focus();
      },
      closeSOSDrawer: () => { drawer.classList.remove('open'); },
      sosDrawer: drawer,
      updateStats: () => {}
    };

    const elements = {
      'btn-fullscreen': fullscreenBtn,
      'sos-drawer': drawer,
      'ack-modal-overlay': ackOverlay,
      'note-textarea': noteTextarea
    };

    const { window, document } = createDOMContext(elements, ns);
    const shortcutsCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-shortcuts-weather.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(shortcutsCode, context);

    // 1. Typing in editable element does not trigger single-letter shortcuts
    document.activeElement = noteTextarea;
    document.dispatchEvent({ type: 'keydown', key: 'f' });
    document.dispatchEvent({ type: 'keydown', key: 'b' });
    document.dispatchEvent({ type: 'keydown', key: 'p' });
    document.dispatchEvent({ type: 'keydown', key: 'm' });
    assert.equal(fullscreenClicked, false, 'Typing f in textarea must not click fullscreen');

    // 2. Escape priority: Ack modal is open on top of SOS drawer
    drawer.classList.add('open');
    ackOverlay.hidden = false;
    document.activeElement = triggerBtn;

    // Press Escape once: closes ackOverlay first, drawer remains open
    document.dispatchEvent({ type: 'keydown', key: 'Escape', preventDefault() {} });
    assert.equal(ackOverlay.hidden, true, 'First Escape must close the topmost modal');
    assert.equal(drawer.classList.contains('open'), true, 'First Escape must keep the underlying drawer open');
    assert.equal(document.activeElement, triggerBtn, 'Focus must return to trigger element');

    // Press Escape second time: closes SOS drawer
    document.dispatchEvent({ type: 'keydown', key: 'Escape', preventDefault() {} });
    assert.equal(drawer.classList.contains('open'), false, 'Second Escape must close the drawer');
  });

  await t.test('audit filters snapshot on submit: pagination and export preserve applied filters', async () => {
    let capturedQueries = [];
    const emailInput = createStubElement('input', 'audit-filter-actor-email');
    emailInput.value = 'initial@example.com';
    const actionInput = createStubElement('input', 'audit-filter-action');
    actionInput.value = 'sos.acknowledge';
    const resourceTypeSelect = createStubElement('select', 'audit-filter-resource-type');
    resourceTypeSelect.value = 'sos_event';
    const resultsEl = createStubElement('div', 'audit-results');
    const appliedEl = createStubElement('div', 'audit-applied-filters');
    const loadMoreBtn = createStubElement('button', 'audit-load-more-btn');

    const ns = {
      ready: true,
      CURRENT_USER: { role: 'admin' },
      auditTimelineHtml: () => '<div>timeline</div>',
      authFetch: (url) => {
        capturedQueries.push(url);
        if (url.includes('/export')) {
          return Promise.resolve({
            ok: true,
            blob: () => Promise.resolve({})
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            events: [{ id: 1 }],
            next_cursor: 'cursor-abc',
            applied_filters: { actor_email: 'initial@example.com' }
          })
        });
      },
      showToast: () => {}
    };

    const elements = {
      'audit-filter-actor-email': emailInput,
      'audit-filter-action': actionInput,
      'audit-filter-resource-type': resourceTypeSelect,
      'audit-filter-date-from': createStubElement('input', 'audit-filter-date-from'),
      'audit-filter-date-to': createStubElement('input', 'audit-filter-date-to'),
      'audit-results': resultsEl,
      'audit-applied-filters': appliedEl,
      'audit-load-more-btn': loadMoreBtn,
      'audit-error': createStubElement('div', 'audit-error')
    };

    const { window, document } = createDOMContext(elements, ns);
    const auditCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-operations-audit.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(auditCode, context);

    // Initial search submission
    await ns.renderAuditPanel();
    assert.ok(capturedQueries[0].includes('actor_email=initial%40example.com'));

    // Now operator mutates the email input without submitting the form
    emailInput.value = 'unsubmitted@example.com';

    // Operator clicks "Load more"
    loadMoreBtn.click();
    await new Promise(r => setTimeout(r, 10));

    // Pagination request must still use snapshotted 'initial@example.com', NOT 'unsubmitted@example.com'
    assert.ok(capturedQueries[1].includes('actor_email=initial%40example.com'), 'Pagination must use snapshotted applied filters');
    assert.ok(!capturedQueries[1].includes('unsubmitted'), 'Pagination must not use unsubmitted form values');
    assert.ok(capturedQueries[1].includes('cursor=cursor-abc'));
  });

  await t.test('audit and case timeline drop out-of-order obsolete responses', async () => {
    let resolveCaseA;
    let resolveCaseB;
    const pCaseA = new Promise(r => resolveCaseA = r);
    const pCaseB = new Promise(r => resolveCaseB = r);

    let timelineCallCount = 0;
    const drawerTitle = createStubElement('span', 'activity-drawer-title');
    const drawerContent = createStubElement('div', 'activity-drawer-content');
    const activityDrawer = createStubElement('div', 'activity-drawer');

    const ns = {
      ready: true,
      CURRENT_USER: { role: 'admin' },
      auditTimelineHtml: (events) => (events && events[0] ? events[0].title : ''),
      authFetch: () => {
        timelineCallCount++;
        if (timelineCallCount === 1) return pCaseA;
        return pCaseB;
      }
    };

    const elements = {
      'activity-drawer': activityDrawer,
      'activity-drawer-title': drawerTitle,
      'activity-drawer-content': drawerContent,
      'activity-drawer-unavailable': createStubElement('div', 'activity-drawer-unavailable'),
      'activity-drawer-close': createStubElement('button', 'activity-drawer-close')
    };

    const { window, document } = createDOMContext(elements, ns);
    const auditCode = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-operations-audit.js'), 'utf8');
    const context = vm.createContext(Object.assign({}, window, { window, document, AqOneDashboard: ns }));
    vm.runInContext(auditCode, context);

    // Operator opens Case A
    ns.openActivityDrawer('sos_event', 'CASE-A', 'Case A Activity');
    assert.equal(drawerTitle.textContent, 'Case A Activity');

    // Operator quickly switches to Case B before Case A responds
    ns.openActivityDrawer('sos_event', 'CASE-B', 'Case B Activity');
    assert.equal(drawerTitle.textContent, 'Case B Activity');

    // Case A resolves late
    resolveCaseA({
      ok: true,
      json: () => Promise.resolve({ events: [{ title: 'CASE A TIMELINE' }] })
    });
    await new Promise(r => setTimeout(r, 10));

    // Case A's response must NOT have replaced Case B's loading state or title!
    assert.equal(drawerTitle.textContent, 'Case B Activity');
    assert.ok(!drawerContent.innerHTML.includes('CASE A TIMELINE'), 'Obsolete Case A response must be dropped');

    // Case B resolves
    resolveCaseB({
      ok: true,
      json: () => Promise.resolve({ events: [{ title: 'CASE B TIMELINE' }] })
    });
    await new Promise(r => setTimeout(r, 10));

    assert.equal(drawerTitle.textContent, 'Case B Activity');
    assert.ok(drawerContent.innerHTML.includes('CASE B TIMELINE'), 'Case B timeline must be rendered');
  });
});
