(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var utils = ns.dashboardUtils || window.AqOneDashboardUtils;
  var opsBoundary = ns.opsBoundary;
  var map = ns.map;
  var gatewayLayer = ns.gatewayLayer;
  var incidentLayer = ns.incidentLayer;
  var buoyLayer = ns.buoyLayer;
  var boundaryLayer = ns.boundaryLayer;
  var pinLayer = ns.pinLayer;
  var vesselLayer = ns.vesselLayer;
  var coverageLayer = ns.coverageLayer;
  var meshLayer = ns.meshLayer;
  var squallLayer = ns.squallLayer;
  var driftLayer = ns.driftLayer;
  var dangerZoneLayer = ns.dangerZoneLayer;
  var escapeHtml = ns.escapeHtml || (window.AqOneDashboardUtils && window.AqOneDashboardUtils.escapeHtml) || function (val) {
    return String(val == null ? '' : val)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  };

  // ===== MARKER CREATION =====
  function createMarkerIcon(type) {
    // Vessels are slate, not green.
    //
    // Every other colour here encodes a status - blue facility, red incident,
    // purple buoy, and green for "safe" throughout the rest of the dashboard.
    // A vessel is an entity, not a verdict, and painting it green made boats
    // indistinguishable from the safe-route layer. Slate reads as neutral and
    // keeps green meaning only one thing.
    const colors = { facility: '#3498db', incident: '#e74c3c', buoy: '#9b59b6', vessel: '#334155' };
    const color = colors[type] || '#3498db';
    return L.divIcon({
      className: 'custom-marker',
      html: `<div class="marker-pin marker-${type}" style="background:${color}">
        <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5">
          ${type === 'facility'
            ? '<path d="M3 21h18M5 21V7l7-4 7 4v14"/><path d="M9 21v-6h6v6"/>'
            : type === 'incident'
            ? '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
            : type === 'vessel'
            ? '<path d="M2 20l2-1h16l2 1"/><path d="M4 20V14l8-6 8 6v6"/><path d="M12 8V4m-4 0h8"/>'
            : '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41"/>'
          }
        </svg>
      </div>`,
      iconSize: [32, 42],
      iconAnchor: [16, 42],
      popupAnchor: [0, -44]
    });
  }

  function makePopup(title, rows, badge) {
    let html = `<div class="popup-title">${escapeHtml(title)}</div>`;
    rows.forEach(([label, val]) => {
      html += `<div class="popup-row"><span>${escapeHtml(label)}</span><span>${escapeHtml(val)}</span></div>`;
    });
    if (badge) {
      html += `<div style="margin-top:6px"><span class="popup-badge badge-${escapeHtml(badge.cls)}">${escapeHtml(badge.text)}</span></div>`;
    }
    return html;
  }


  // ===== BUOY NETWORK =====
  // Everything drawn here comes from GET /api/public/buoys. A buoy with no
  // recorded position is listed in the Buoy Network panel but never placed.
  var network = { buoys: [], stations: [], loadedAt: null, failed: false };
  var networkListeners = [];
  var coverageCircles = {};
  var meshPath = [];
  var meshDot = L.circleMarker([0, 0], {
    radius: 3.5,
    color: '#99f6e4',
    fillColor: '#22d3ee',
    fillOpacity: 0.9,
    weight: 2,
    opacity: 1
  });

  function km(metres) {
    return metres == null ? 'not recorded' : (metres / 1000).toFixed(1) + ' km';
  }

  function buoyBadge(b) {
    if (b.isSynthetic) return { cls: 'warning', text: 'DEMO' };
    if (b.status === 'active') return { cls: 'active', text: 'active' };
    return { cls: 'warning', text: b.status === 'silent' ? 'silent' : 'never heard' };
  }

  function drawNetwork() {
    gatewayLayer.clearLayers();
    buoyLayer.clearLayers();
    coverageLayer.clearLayers();
    meshLayer.clearLayers();
    coverageCircles = {};
    meshPath = [];
    var now = Date.now();

    network.stations.forEach(function (s) {
      gatewayLayer.addLayer(L.marker([s.lat, s.lng], { icon: createMarkerIcon('facility') })
        .bindPopup(makePopup(s.name, [['Type', s.type], ['Role', s.role]])));
    });

    network.buoys.forEach(function (b) {
      if (b.lat == null) return;
      var rows = [
        ['Status', utils.buoyHeardText(b, now)],
        ['Phone range', km(b.wifiRadius)],
        ['LoRa range', km(b.loraRadius)]
      ];
      if (b.isGateway) rows.push(['Role', 'LoRa gateway - mesh exit to shore']);
      buoyLayer.addLayer(L.marker([b.lat, b.lng], { icon: createMarkerIcon('buoy') })
        .bindPopup(makePopup(b.name, rows, buoyBadge(b))));

      // The large LoRa rings overlap into the relay fabric; the small WiFi
      // bubbles inside them are where a phone can actually hand over an SOS.
      if (b.loraRadius != null) {
        coverageLayer.addLayer(L.circle([b.lat, b.lng], {
          radius: b.loraRadius,
          color: '#22d3ee',
          fillColor: '#22d3ee',
          fillOpacity: 0.05,
          weight: 1,
          dashArray: '2 6',
          opacity: 0.35
        }).bindTooltip(b.name + ' - LoRa relay range ' + km(b.loraRadius), { sticky: true }));
      }
      if (b.wifiRadius != null) {
        var wifi = L.circle([b.lat, b.lng], {
          radius: b.wifiRadius,
          color: '#60a5fa',
          fillColor: '#60a5fa',
          fillOpacity: 0.14,
          weight: 1.5,
          dashArray: '6 4',
          opacity: 0.55
        }).bindTooltip(b.name + ' - phone contact range ' + km(b.wifiRadius), { sticky: true });
        coverageLayer.addLayer(wifi);
        coverageCircles[b.id] = wifi;
        coverageCircles[b.name] = wifi;
      }
      if (b.isGateway) {
        meshLayer.addLayer(L.marker([b.lat, b.lng], {
          icon: L.divIcon({ className: '', html: '<div class="gateway-ring"></div>', iconSize: [44, 44], iconAnchor: [22, 22] })
        }));
      }
    });

    utils.meshLinksFor(network.buoys, network.stations).forEach(function (link) {
      var a = link[0], b = link[1];
      meshLayer.addLayer(L.polyline([[a.lat, a.lng], [b.lat, b.lng]], {
        color: '#22d3ee',
        weight: 2.5,
        opacity: 0.85,
        dashArray: '6 6',
        smoothFactor: 1
      }).bindTooltip(
        a.name + ' ↔ ' + b.name + ' · ' + km(utils.metresBetween(a.lat, a.lng, b.lat, b.lng)) + ' LoRa link',
        { sticky: true, className: 'drift-incident-label' }
      ));
      for (var i = 0; i <= 25; i++) {
        meshPath.push([a.lat + (b.lat - a.lat) * i / 25, a.lng + (b.lng - a.lng) * i / 25]);
      }
    });
    if (meshPath.length) meshLayer.addLayer(meshDot);
  }

  function pulseCoverageCircle(buoyKey) {
    var c = coverageCircles[buoyKey];
    if (!c) return;
    c.setStyle({ weight: 4, opacity: 0.9, fillOpacity: 0.2 });
    setTimeout(function () {
      c.setStyle({ weight: 1.5, opacity: 0.55, fillOpacity: 0.14, dashArray: '6 4' });
    }, 2500);
  }

  var dotIdx = 0;
  setInterval(function () {
    if (!meshPath.length || !map.hasLayer(meshLayer)) return;
    dotIdx = (dotIdx + 1) % meshPath.length;
    meshDot.setLatLng(meshPath[dotIdx]);
  }, 60);

  function loadNetwork() {
    return ns.authFetch('/api/public/buoys')
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (payload) {
        var next = utils.networkFromPublicBuoys(payload);
        network.buoys = next.buoys;
        network.stations = next.stations;
        network.loadedAt = Date.now();
        network.failed = false;
      })
      .catch(function (err) {
        network.failed = true;
        console.warn('[AqOne] Buoy network unavailable:', err.message);
      })
      .then(function () {
        drawNetwork();
        networkListeners.forEach(function (fn) { fn(network); });
      });
  }

  ns.network = network;
  ns.onNetworkChange = function (fn) { networkListeners.push(fn); };
  ns.loadNetwork = loadNetwork;
  loadNetwork();
  setInterval(loadNetwork, 60000);

  let apiBuoys = [];
  var dangerZoneRequestId = 0;
  var lastDangerZoneResult = null;
  var dangerZoneCacheKey = 'aqone-last-danger-zone-result-new-washington-grid-v2' +
    (window.AqOneTutorial && window.AqOneTutorial.active ? '-tutorial' : '');

  function readCachedDangerZoneResult() {
    try {
      var cached = JSON.parse(localStorage.getItem(dangerZoneCacheKey));
      return cached && Array.isArray(cached.predictions) ? cached : null;
    } catch (error) {
      return null;
    }
  }

  function cacheDangerZoneResult(result) {
    try {
      localStorage.setItem(dangerZoneCacheKey, JSON.stringify(result));
    } catch (error) {
      console.warn('[AqOne] Could not cache the latest danger-zone scan');
    }
  }

  function renderDangerZones(result) {
    var predictions = result.predictions;
    var alertPredictions = predictions.filter(function (prediction) {
      return prediction.level !== 'low';
    });

    dangerZoneLayer.clearLayers();
    var firstPredictionMarker = null;
    predictions.forEach(function (prediction) {
      var circle = L.circle([prediction.lat, prediction.lng], {
        radius: prediction.radius,
        color: prediction.color,
        fillColor: prediction.color,
        fillOpacity: prediction.level === 'danger' ? 0.2 : prediction.level === 'watch' ? 0.12 : 0.05,
        opacity: prediction.level === 'low' ? 0.55 : 0.95,
        weight: prediction.level === 'danger' ? 3 : prediction.level === 'watch' ? 2 : 1.5,
        dashArray: prediction.level === 'danger' ? null : prediction.level === 'watch' ? '7 5' : '4 7',
        className: 'danger-zone-circle danger-zone-circle-' + prediction.level
      });
      var icon = L.divIcon({
        className: '',
        html: '<div class="danger-zone-map-icon danger-zone-map-icon-' + prediction.level + '">' +
          '<span>' + (prediction.level === 'low' ? '&check;' : '!') + '</span><i></i></div>',
        iconSize: [36, 36],
        iconAnchor: [18, 18]
      });
      var marker = L.marker([prediction.lat, prediction.lng], {
        icon: icon,
        interactive: true,
        zIndexOffset: 700
      });
      var reasons = prediction.reasons.map(escapeHtml).join(' &middot; ');
      var popup = '<div class="popup-title" style="color:' + prediction.color + ';">' +
        escapeHtml(prediction.label) + ' Zone</div>' +
        '<div class="popup-row"><span>Area</span><span>' + escapeHtml(prediction.name) + '</span></div>' +
        '<div class="popup-row"><span>Coordinates</span><span>' + prediction.lat.toFixed(3) + '\u00b0, ' + prediction.lng.toFixed(3) + '\u00b0</span></div>' +
        '<div class="popup-row"><span>Hazard probability</span><span style="font-weight:800;color:' + prediction.color + ';">' + prediction.score + '%</span></div>' +
        '<div class="popup-row"><span>Model probability</span><span>' + prediction.modelProbability + '%</span></div>' +
        '<div class="popup-row"><span>Live wind / gust</span><span>' + Number(prediction.features.wind_speed_10m).toFixed(1) + ' / ' + Number(prediction.features.wind_gusts_10m).toFixed(1) + ' km/h</span></div>' +
        '<div class="popup-row"><span>Live wave / period</span><span>' + Number(prediction.features.wave_height).toFixed(2) + ' m / ' + Number(prediction.features.wave_period).toFixed(1) + ' s</span></div>' +
        '<div class="popup-row"><span>GEBCO depth</span><span>' + prediction.depthM.toFixed(0) + ' m</span></div>' +
        '<div class="popup-row"><span>Radius</span><span>' + (prediction.radius / 1000).toFixed(1) + ' km</span></div>' +
        '<div class="popup-row"><span>Warning trigger</span><span>' + escapeHtml(prediction.trigger) + '</span></div>' +
        '<div class="popup-divider"></div>' +
        '<div style="font-size:11px;line-height:1.45;color:#d1d5db;">' + reasons + '</div>' +
        '<div style="margin-top:7px;font-size:10px;color:#9ca3af;">' + escapeHtml(prediction.source) + '<br>' +
        escapeHtml(result.modelType) + ' · ' + escapeHtml(result.modelVersion) + '<br>' +
        '2025 holdout F1: ' + Number(result.metrics.f1).toFixed(3) + ' · ' + escapeHtml(result.buoySource) + '</div>' +
        '<div style="margin-top:7px"><span class="popup-badge badge-danger">EXPERIMENTAL · NOT FOR NAVIGATION</span></div>';

      circle.bindPopup(popup);
      marker.bindPopup(popup);
      circle.bindTooltip(escapeHtml(prediction.name) + ' · ' + prediction.score + '%', {
        direction: 'top',
        sticky: true
      });
      dangerZoneLayer.addLayer(circle);
      dangerZoneLayer.addLayer(marker);
      if (!firstPredictionMarker) firstPredictionMarker = marker;
    });

    if (firstPredictionMarker && new URLSearchParams(window.location.search).get('previewDangerZone') === '1') {
      firstPredictionMarker.openPopup();
    }

    var statusText = document.getElementById('danger-zone-status-text');
    if (statusText) {
      var dangerCount = alertPredictions.filter(function (prediction) {
        return prediction.level === 'danger';
      }).length;
      var watchCount = alertPredictions.length - dangerCount;
      var updatedAt = new Date(result.fetchedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      statusText.textContent = dangerCount + ' danger · ' + watchCount + ' watch · ' + predictions.length + ' zones · Live ' + updatedAt;
    }
    if (statusText) {
      var scanUpdatedAt = new Date(result.fetchedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      var scanProvenance = result.is_synthetic ? 'DEMO ' : 'Live ';
      statusText.textContent = result.dangerCount + ' danger · ' + result.watchCount + ' watch · ' +
        result.scannedCount + ' near-shore cells scanned · strongest ' + result.strongestProbability + '% · ' + scanProvenance + scanUpdatedAt;
    }
  }

  async function refreshDangerZones() {
    var statusText = document.getElementById('danger-zone-status-text');
    var statusCard = document.getElementById('danger-zone-status');
    var refreshButton = document.getElementById('danger-zone-refresh');
    var requestId = ++dangerZoneRequestId;
    if (!lastDangerZoneResult) lastDangerZoneResult = readCachedDangerZoneResult();
    if (lastDangerZoneResult) {
      renderDangerZones(lastDangerZoneResult);
    } else {
      dangerZoneLayer.clearLayers();
    }
    if (statusText) statusText.textContent = lastDangerZoneResult ?
      'Refreshing live data \u00b7 Existing real-data zones remain visible' :
      'Loading live weather and marine observations...';
    if (statusCard) statusCard.classList.remove('danger-zone-status-error');
    if (refreshButton) refreshButton.classList.add('is-refreshing');
    try {
      var result = await window.AqOneDangerZonePredictor.predictLive(apiBuoys);
      if (requestId !== dangerZoneRequestId) return;
      lastDangerZoneResult = result;
      cacheDangerZoneResult(result);
      renderDangerZones(result);
    } catch (error) {
      if (requestId !== dangerZoneRequestId) return;
      if (lastDangerZoneResult) {
        renderDangerZones(lastDangerZoneResult);
        if (statusText) statusText.textContent = 'Live refresh unavailable \u00b7 Showing last successful real-data scan';
        if (statusCard) statusCard.classList.add('danger-zone-status-error');
        console.warn('[AqOne] Danger-zone refresh unavailable:', error.message);
        return;
      }
      dangerZoneLayer.clearLayers();
      if (statusText) statusText.textContent = 'Live data unavailable · No hazard zones shown';
      if (statusCard) statusCard.classList.add('danger-zone-status-error');
      console.warn('[AqOne] Danger-zone model unavailable:', error.message);
    } finally {
      if (requestId === dangerZoneRequestId && refreshButton) {
        refreshButton.classList.remove('is-refreshing');
      }
    }
  }


  // ===== BOUNDARY =====
  const boundaryPoly = L.polygon(opsBoundary, {
    color: '#2ecc71',
    weight: 2.5,
    fillColor: '#2ecc71',
    fillOpacity: 0.06,
    dashArray: '8 6',
    className: 'ops-boundary'
  }).bindTooltip('Municipal Waters \u2014 Aqone Coverage Area', { permanent: true, direction: 'center', className: 'boundary-tooltip' });
  boundaryLayer.addLayer(boundaryPoly);

  // ===== OFFLINE MAP FALLBACK =====
  // The basemap tiles come from the internet. Without them the map would be a
  // grey box, so it switches to the service-area outline drawn as water on a
  // plain land colour, and says so (docs/72).
  var tileLoads = 0;
  var tileErrors = 0;
  var offlineNote = null;
  function showOfflineMap() {
    var container = map.getContainer();
    if (container.classList.contains('map-tiles-offline')) return;
    container.classList.add('map-tiles-offline');
    boundaryPoly.setStyle({ fillColor: '#7cb7e8', fillOpacity: 0.55 });
    offlineNote = L.control({ position: 'topright' });
    offlineNote.onAdd = function () {
      var note = L.DomUtil.create('div', 'map-offline-note');
      note.textContent = 'Map tiles unavailable - showing the service-area outline';
      return note;
    };
    offlineNote.addTo(map);
  }
  function hideOfflineMap() {
    var container = map.getContainer();
    if (!container.classList.contains('map-tiles-offline')) return;
    container.classList.remove('map-tiles-offline');
    boundaryPoly.setStyle({ fillColor: '#2ecc71', fillOpacity: 0.06 });
    if (offlineNote) offlineNote.remove();
  }
  Object.keys(ns.tileLayers || {}).forEach(function (name) {
    ns.tileLayers[name].on('tileload', function () {
      tileLoads++;
      hideOfflineMap();
    });
    ns.tileLayers[name].on('tileerror', function () {
      tileErrors++;
      if (tileLoads === 0 && tileErrors >= 4) showOfflineMap();
    });
  });
  if (typeof navigator !== 'undefined' && navigator.onLine === false) showOfflineMap();

  // Add layers to map (checked toggles by default)
  gatewayLayer.addTo(map);
  incidentLayer.addTo(map);
  pinLayer.addTo(map);
  squallLayer.addTo(map);
  driftLayer.addTo(map);
  boundaryLayer.addTo(map);
  refreshDangerZones();

  ns.createMarkerIcon = createMarkerIcon;
  ns.makePopup = makePopup;
  ns.pulseCoverageCircle = pulseCoverageCircle;
  ns.refreshDangerZones = refreshDangerZones;

})(window.AqOneDashboard = window.AqOneDashboard || {});
