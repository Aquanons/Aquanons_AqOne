(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var shoreStations = ns.shoreStations;
  var initialBuoys = ns.initialBuoys;
  var _metresBetween = ns._metresBetween;
  var meshLinks = ns.meshLinks;
  var incidents = ns.incidents;
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


  // ===== GATEWAY MARKERS =====
  shoreStations.forEach(s => {
    const marker = L.marker([s.lat, s.lng], { icon: createMarkerIcon('facility') })
      .bindPopup(makePopup(s.name, [
        ['Type', s.type],
        ['Role', s.role],
        ['Status', s.status.charAt(0).toUpperCase() + s.status.slice(1)]
      ], { cls: s.status, text: s.status }));
    gatewayLayer.addLayer(marker);
  });


  // ===== BUOY MARKERS =====
  initialBuoys.forEach(b => {
    var extraRows = b.isGateway
      ? [['Role', 'LoRa gateway — mesh exit to shore']]
      : [];
    var pressureRow = b.pressure != null
      ? [['Pressure', b.pressure.toFixed(1) + ' hPa (' + (b.pressureTrend > 0 ? '+' : '') + b.pressureTrend + ')']]
      : [];
    // These readings (battery, signal, pressure, current) are the fixed
    // sample values in initialBuoys above, not live telemetry from hardware -
    // no buoy in this deployment reports them yet. Rule 4 of
    // docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md bans presenting
    // that as if it were live, so every buoy popup says so explicitly.
    const marker = L.marker([b.lat, b.lng], { icon: createMarkerIcon('buoy') })
      .bindPopup(makePopup(b.name, [
        ['Status', b.status.charAt(0).toUpperCase() + b.status.slice(1)],
        ['Battery', b.battery + '% (simulated)'],
        ['Signal', b.signal + ' (simulated)']
      ].concat(pressureRow, extraRows), { cls: b.status, text: b.status }));
    buoyLayer.addLayer(marker);
  });


  // ===== COVERAGE CIRCLES =====
  // Two layers per buoy. The large LoRa rings overlap into a continuous relay
  // fabric; the small WiFi bubbles inside them show where a phone can actually
  // reach a buoy. Drawing only one radius was misleading either way: LoRa alone
  // implies phones connect from 7 km out, WiFi alone makes the mesh look
  // disconnected.
  var coverageCircles = {};
  initialBuoys.forEach(function (b) {
    // LoRa relay range - drawn first so it sits beneath the WiFi bubble.
    var lora = L.circle([b.lat, b.lng], {
      radius: b.loraRadius || 7000,
      color: '#22d3ee',
      fillColor: '#22d3ee',
      fillOpacity: 0.05,
      weight: 1,
      dashArray: '2 6',
      opacity: 0.35
    }).bindTooltip(b.name + ' — LoRa relay range ' + ((b.loraRadius || 7000) / 1000).toFixed(1) + ' km', { sticky: true });
    coverageLayer.addLayer(lora);

    // WiFi SoftAP bubble - where a phone can hand over an SOS.
    var wifi = L.circle([b.lat, b.lng], {
      radius: b.wifiRadius || 1200,
      color: '#60a5fa',
      fillColor: '#60a5fa',
      fillOpacity: 0.14,
      weight: 1.5,
      dashArray: '6 4',
      opacity: 0.55
    }).bindTooltip(b.name + ' — phone contact range ' + ((b.wifiRadius || 1200) / 1000).toFixed(1) + ' km', { sticky: true });
    coverageLayer.addLayer(wifi);

    // Pulse animation targets the WiFi bubble: it marks a phone check-in.
    coverageCircles[b.name] = wifi;
  });

  function pulseCoverageCircle(buoyName) {
    var c = coverageCircles[buoyName];
    if (!c) return;
    c.setStyle({ weight: 4, opacity: 0.9, fillOpacity: 0.2 });
    setTimeout(function () {
      c.setStyle({ weight: 1.5, opacity: 0.4, fillOpacity: 0.08, dashArray: '6 4' });
    }, 2500);
  }


  // ===== MESH NETWORK =====
  var meshPolylines = [];
  function findNode(name) {
    return initialBuoys.find(function (b) { return b.name === name; }) ||
           shoreStations.find(function (s) { return s.name === name; });
  }

  meshLinks.forEach(function (link) {
    var n1 = findNode(link[0]);
    var n2 = findNode(link[1]);
    if (!n1 || !n2) return;
    // The mesh is the product. Drawn at 1.5px and 45% opacity it was
    // effectively invisible against the basemap, which made a correctly
    // connected array look like scattered unconnected buoys.
    var line = L.polyline([[n1.lat, n1.lng], [n2.lat, n2.lng]], {
      color: '#22d3ee',
      weight: 2.5,
      opacity: 0.85,
      dashArray: '6 6',
      smoothFactor: 1
    });
    line.bindTooltip(
      link[0] + ' ↔ ' + link[1] + ' · ' +
      (_metresBetween(n1.lat, n1.lng, n2.lat, n2.lng) / 1000).toFixed(1) + ' km LoRa link',
      { sticky: true, className: 'drift-incident-label' }
    );
    meshLayer.addLayer(line);
    meshPolylines.push(line);
  });

  var gatewayBuoy = initialBuoys.find(function (b) { return b.isGateway; });
  if (gatewayBuoy) {
    var ringIcon = L.divIcon({
      className: '',
      html: '<div class="gateway-ring"></div>',
      iconSize: [44, 44],
      iconAnchor: [22, 22]
    });
    var ringMarker = L.marker([gatewayBuoy.lat, gatewayBuoy.lng], { icon: ringIcon });
    meshLayer.addLayer(ringMarker);
  }

  var meshPath = [];
  meshLinks.forEach(function (link) {
    var n1 = findNode(link[0]);
    var n2 = findNode(link[1]);
    if (!n1 || !n2) return;
    var steps = 25;
    for (var i = 0; i <= steps; i++) {
      var t = i / steps;
      meshPath.push([
        n1.lat + (n2.lat - n1.lat) * t,
        n1.lng + (n2.lng - n1.lng) * t
      ]);
    }
  });

  var meshDot = L.circleMarker([0, 0], {
    radius: 3.5,
    color: '#99f6e4',
    fillColor: '#22d3ee',
    fillOpacity: 0.9,
    weight: 2,
    opacity: 1
  });
  meshLayer.addLayer(meshDot);
  var dotIdx = 0;
  var meshDotInterval = setInterval(function () {
    if (!map.hasLayer(meshLayer)) return;
    dotIdx = (dotIdx + 1) % meshPath.length;
    meshDot.setLatLng(meshPath[dotIdx]);
  }, 60);


  // ===== INCIDENT MARKERS =====
  const incidentDrawerData = [
    { alertType: 'squall', headerText: 'RETURN NOW — SQUALL NOWCAST',
      vesselId: 'ALL', owner: 'Broadcast \u2014 all vessels in contact range',
      position: 'Approach NE \u2014 arrival est. 14:20', lat: 11.7383, lng: 122.5324,
      buoy: 'Buoy-B / Buoy-C', coverage: 'Alert propagated across LoRa mesh \u2014 waiting at every buoy',
      confidence: 88, stage: 'Squall nowcast \u2014 45 min lead', nextContact: 'Delivered to phones on next contact',
      timerBaseline: 12 * 60 },
  ];

  const incidentMarkers = [];

  incidents.forEach((inc, idx) => {
    const marker = L.marker([inc.lat, inc.lng], { icon: createMarkerIcon('incident') });
    const drawerData = incidentDrawerData[idx];
    if (drawerData) {
      marker.on('click', function () { ns.openIncidentDrawer(drawerData, marker); });
    }
    incidentLayer.addLayer(marker);
    incidentMarkers.push(marker);
  });

  let apiBuoys = [];
  var dangerZoneRequestId = 0;
  var lastDangerZoneResult = null;
  var dangerZoneCacheKey = 'aqone-last-danger-zone-result-new-washington-grid-v2';

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
  ns.incidentDrawerData = incidentDrawerData;
  ns.refreshDangerZones = refreshDangerZones;

})(window.AqOneDashboard = window.AqOneDashboard || {});
