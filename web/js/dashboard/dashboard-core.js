(function (ns) {
  'use strict';

  ns.ready = false;


  // Failsafe: never leave the operator staring at the loading spinner.
  //
  // The overlay is hidden near the end of this script, so any uncaught error
  // above that point froze the dashboard behind "Loading buoy network data..."
  // with no indication of what went wrong. Registered first, before anything
  // that can throw, so a future breakage degrades to a visible dashboard plus a
  // console error rather than a dead screen.
  window.addEventListener('error', function (event) {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
    console.error('[AqOne] Dashboard init failed:', event.message, 'at', event.filename + ':' + event.lineno);
  });
  // ===== SHARED HELPERS (web/js/dashboard-utils.js) =====
  // Loaded before this script in dashboard.html. The inline fallback below
  // only runs if that tag failed to load - degrading to "still escapes text
  // and still reports itself offline" rather than throwing ReferenceErrors
  // through every call site that follows.
  var dashboardUtils = window.AqOneDashboardUtils || {
    escapeHtml: function (value) {
      if (value == null) return '';
      return String(value)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },
    classifyFreshness: function () { return 'offline'; },
    freshnessLabel: function (state) { return (state || 'offline').toUpperCase(); }
  };
  var escapeHtml = dashboardUtils.escapeHtml;
  var classifyFreshness = dashboardUtils.classifyFreshness;
  var freshnessLabel = dashboardUtils.freshnessLabel;
  var alertBadge = dashboardUtils.alertBadge || function (isLive) {
    if (isLive === 'unknown') return { text: 'UNKNOWN', cssClass: 'alert-unknown-badge' };
    return (isLive === true || isLive === 'real' || isLive === 'live')
      ? { text: 'LIVE', cssClass: 'alert-live-badge' }
      : { text: 'DEMO', cssClass: 'alert-demo-badge' };
  };
  var formatEta = dashboardUtils.formatEta || function () { return ''; };
  var utf8ByteLength = dashboardUtils.utf8ByteLength;
  var lateLabel = dashboardUtils.lateLabel;
  var flagLabel = dashboardUtils.flagLabel;
  var deliveryLabel = dashboardUtils.deliveryLabel;
  var responderStatusHtml = dashboardUtils.responderStatusHtml || function () { return ''; };
  var registrationBadgeHtml = dashboardUtils.registrationBadgeHtml || function () { return ''; };
  var tripChecksListHtml = dashboardUtils.tripChecksListHtml || function () { return ''; };
  var squallStatusHtml = dashboardUtils.squallStatusHtml || function () { return ''; };
  var auditTimelineHtml = dashboardUtils.auditTimelineHtml || function () { return ''; };


  // ===== CONFIG =====
  // New Washington, Aklan municipal centre (PhilAtlas: 11.6473 N, 122.4356 E).
  // Zoom 11 framed the whole province; 12 frames the municipality and its
  // waters, which is the actual service area.
  const OPS_CENTER = [11.6473, 122.4356];
  const OPS_ZOOM = 12;

  const TILES = {
    streets: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      attr: '&copy; Esri, HERE, Garmin, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), (c) OpenStreetMap contributors, and the GIS User Community'
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attr: '&copy; Esri, Maxar, Earthstar Geographics'
    },
    hybrid: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attr: '&copy; Esri, Maxar, Earthstar Geographics',
      labels: 'https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png',
      labelsAttr: '&copy; CartoDB'
    }
  };

  const PIN_POLL_INTERVAL_MS = 15000;


  // ===== API + AUTH =====
  // API_BASE was previously referenced but never declared in this file - the
  // one in advisoryService.js is scoped inside its IIFE, so every fetch here
  // threw a ReferenceError. The dashboard is served from the same origin as
  // the API, so this is simply the current origin.
  const API_BASE = window.location.origin;

  const TOKEN_KEY = 'aqoneToken';
  const USER_KEY = 'aqoneUser';
  const LOGIN_URL = 'login.html';

  function getToken() {
    return sessionStorage.getItem(TOKEN_KEY) || '';
  }

  function clearSession() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    sessionStorage.removeItem('aqoneDemoBypassActive');
  }

  function redirectToLogin() {
    clearSession();
    window.location.replace(LOGIN_URL);
  }

  // Every API route except the auth endpoints requires a bearer token. A 401
  // means the token is missing, expired or invalid - in all three cases the
  // operator needs to log in again, so bounce rather than rendering an empty
  // dashboard that looks like a backend outage.
  function authFetch(path, options) {
    const opts = options || {};
    const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});
    const token = getToken();
    if (token) headers.Authorization = 'Bearer ' + token;

    return fetch(API_BASE + path, Object.assign({}, opts, { headers: headers }))
      .then(function (res) {
        if (res.status === 401 && sessionStorage.getItem('aqoneDemoBypassActive') !== '1') {
          redirectToLogin();
          throw new Error('Session expired');
        }
        return res;
      });
  }

  function tokenExpiry(token) {
    try {
      var payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(window.atob(payload)).exp * 1000;
    } catch (e) {
      return null;
    }
  }

  // Guard: no token means never logged in, so do not even start the panels.
  // The tutorial (docs/72) needs no account: it never reaches the API.
  var inTutorial = !!(window.AqOneTutorial && window.AqOneTutorial.active);
  if (!getToken() && !inTutorial) {
    redirectToLogin();
    return;
  }


  // ===== CURRENT USER =====
  // Populated at login. Falls back to the token-less placeholder only if the
  // stored record is unreadable, so attribution on sea-condition entries is a
  // real account rather than a hardcoded name.
  const CURRENT_USER = (function () {
    try {
      const stored = JSON.parse(sessionStorage.getItem(USER_KEY) || 'null');
      if (stored && stored.id) return stored;
    } catch (err) {
      /* fall through */
    }
    return { id: 'unknown', name: 'Operator' };
  })();


  // ===== USER COLOR HASH =====
  const PIN_PALETTE = [
    '#00bcd4', '#e91e63', '#ff9800', '#8bc34a', '#673ab7',
    '#009688', '#ff5722', '#3f51b5', '#cddc39', '#f06292',
  ];

  function hashUserId(id) {
    let h = 5381;
    for (let i = 0; i < id.length; i++) {
      h = ((h << 5) + h) ^ id.charCodeAt(i);
      h = h >>> 0;
    }
    return PIN_PALETTE[h % PIN_PALETTE.length];
  }

  const CURRENT_USER_COLOR = hashUserId(CURRENT_USER.id);


  // ===== SERVICE AREA =====
  // Service area = New Washington municipal waters. Mirrors WATER_POLYGON in
  // backend/app/geo.py. The previous ring spanned the whole province, from
  // Boracay in the west to Batan in the east.
  const opsBoundary = [
    [11.6703, 122.4157], [11.6177, 122.4380], [11.5902, 122.4914],
    [11.5911, 122.6286], [11.6330, 122.6721], [11.6813, 122.6355],
    [11.7414, 122.5924], [11.7731, 122.5408], [11.7662, 122.4574],
    [11.7223, 122.4061], [11.6703, 122.4157]
  ];


  // ===== MAP INIT =====
  const map = L.map('map', {
    center: OPS_CENTER,
    zoom: OPS_ZOOM,
    zoomControl: true,
    attributionControl: true,
    maxBounds: [[5, 115], [25, 130]],
    minZoom: 5,
    maxZoom: 18
  });

  const tileLayers = {
    streets: L.tileLayer(TILES.streets.url, { attribution: TILES.streets.attr, maxZoom: 18 }),
    satellite: L.tileLayer(TILES.satellite.url, { attribution: TILES.satellite.attr, maxZoom: 18 }),
    hybrid: L.tileLayer(TILES.hybrid.url, { attribution: TILES.hybrid.attr, maxZoom: 18 }),
    hybridLabels: L.tileLayer(TILES.hybrid.labels, { attribution: TILES.hybrid.labelsAttr, maxZoom: 18, pane: 'shadowPane' })
  };

  let currentBase = 'streets';
  tileLayers.streets.addTo(map);


  // ===== LAYER GROUPS =====
  const gatewayLayer   = L.layerGroup();
  const incidentLayer  = L.layerGroup();
  const buoyLayer      = L.layerGroup();
  const boundaryLayer  = L.layerGroup();
  const pinLayer       = L.layerGroup();
  const vesselLayer    = L.layerGroup();
  const coverageLayer  = L.layerGroup();
  const meshLayer      = L.layerGroup();
  const squallLayer    = (typeof L !== 'undefined' && typeof L.featureGroup === 'function') ? L.featureGroup() : L.layerGroup();
  const driftLayer     = L.layerGroup();
  const hotspotLayer   = L.layerGroup();

  map.createPane('aiContoursPane');
  map.getPane('aiContoursPane').style.zIndex = 430;
  map.createPane('aiTrackPane');
  map.getPane('aiTrackPane').style.zIndex = 440;
  map.createPane('aiSquallPane');
  map.getPane('aiSquallPane').style.zIndex = 450;
  const dangerZoneLayer = L.layerGroup();


   // ===== TOAST =====
   function showToast(title, msg, isError, action) {
     var container = document.getElementById('toast-container');
     var toast = document.createElement('div');
     toast.className = 'toast';
     if (isError) toast.classList.add('toast-error');
     // title/msg can carry server-provided SOS text (boat name, position) -
     // see the loadActiveSos() call site - so both must be escaped.
     toast.innerHTML = '<div class="toast-title">' + escapeHtml(title) + '</div><div class="toast-msg">' + escapeHtml(msg) + '</div>';
     if (action && action.label && action.onClick) {
       var button = document.createElement('button');
       button.type = 'button';
       button.textContent = action.label;
       button.addEventListener('click', function () {
         action.onClick();
         if (toast.parentNode) toast.parentNode.removeChild(toast);
       });
       toast.appendChild(button);
     }
     container.appendChild(toast);
     setTimeout(function () {
       toast.classList.add('toast-leave');
       setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 300);
     }, action ? 10000 : 4000);
   }


  ns.ready = true;
  ns.dashboardUtils = dashboardUtils;
  ns.escapeHtml = escapeHtml;
  ns.formatLatLon = dashboardUtils.formatLatLon;
  ns.classifyFreshness = classifyFreshness;
  ns.freshnessLabel = freshnessLabel;
  ns.alertBadge = alertBadge;
  ns.formatEta = formatEta;
  ns.utf8ByteLength = utf8ByteLength;
  ns.lateLabel = lateLabel;
  ns.flagLabel = flagLabel;
  ns.deliveryLabel = deliveryLabel;
  var sessionExpiryBanner = document.getElementById('session-expiry-banner');
  var refreshAttemptExpiry = null;
  function refreshSessionIfNeeded() {
    if (document.visibilityState === 'hidden') return;
    var token = getToken();
    var expiresAt = tokenExpiry(token);
    if (!expiresAt) return;
    var remaining = expiresAt - Date.now();
    if (sessionExpiryBanner) {
      sessionExpiryBanner.hidden = remaining > 3600000;
      sessionExpiryBanner.textContent = remaining <= 0
        ? 'Session expired - sign in again.'
        : 'Session expires soon at ' + new Date(expiresAt).toLocaleTimeString() + '. Keep this page open to refresh it.';
    }
    if (remaining <= 0 || remaining > 24 * 3600000 || refreshAttemptExpiry === expiresAt) return;
    refreshAttemptExpiry = expiresAt;
    authFetch('/api/token/refresh', { method: 'POST' }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }).then(function (result) {
      var freshToken = result.token || result.access_token;
      if (freshToken) {
        sessionStorage.setItem(TOKEN_KEY, freshToken);
        refreshAttemptExpiry = null;
        refreshSessionIfNeeded();
      }
    }).catch(function () {});
  }
  refreshSessionIfNeeded();
  setInterval(refreshSessionIfNeeded, 60000);
  document.addEventListener('visibilitychange', refreshSessionIfNeeded);
  ns.refreshSessionIfNeeded = refreshSessionIfNeeded;
  ns.responderStatusHtml = responderStatusHtml;
  ns.registrationBadgeHtml = registrationBadgeHtml;
  ns.tripChecksListHtml = tripChecksListHtml;
  ns.squallStatusHtml = squallStatusHtml;
  ns.auditTimelineHtml = auditTimelineHtml;
  ns.OPS_CENTER = OPS_CENTER;
  ns.OPS_ZOOM = OPS_ZOOM;
  ns.API_BASE = API_BASE;
  ns.authFetch = authFetch;
  ns.CURRENT_USER = CURRENT_USER;
  ns.CURRENT_USER_COLOR = CURRENT_USER_COLOR;
  ns.opsBoundary = opsBoundary;
  ns.map = map;
  ns.tileLayers = tileLayers;
  ns.currentBase = currentBase;
  ns.gatewayLayer = gatewayLayer;
  ns.incidentLayer = incidentLayer;
  ns.buoyLayer = buoyLayer;
  ns.boundaryLayer = boundaryLayer;
  ns.pinLayer = pinLayer;
  ns.vesselLayer = vesselLayer;
  ns.coverageLayer = coverageLayer;
  ns.meshLayer = meshLayer;
  ns.squallLayer = squallLayer;
  ns.driftLayer = driftLayer;
  ns.dangerZoneLayer = dangerZoneLayer;
  ns.hotspotLayer = hotspotLayer;
  ns.showToast = showToast;

})(window.AqOneDashboard = window.AqOneDashboard || {});
