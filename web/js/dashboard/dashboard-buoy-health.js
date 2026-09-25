(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var OPS_CENTER = ns.OPS_CENTER;
  var OPS_ZOOM = ns.OPS_ZOOM;
  var shoreStations = ns.shoreStations;
  var initialBuoys = ns.initialBuoys;
  var vessels = ns.vessels;
  var incidents = ns.incidents;
  var map = ns.map;
  var openPanel = ns.openPanel;
  var closePanel = ns.closePanel;
  var allAlerts = ns.allAlerts;
  var alertIcon = ns.alertIcon;
  var escapeHtml = ns.escapeHtml || (window.AqOneDashboardUtils && window.AqOneDashboardUtils.escapeHtml) || function (val) {
    return String(val == null ? '' : val)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  };

  // ===== RESOLVED INCIDENTS =====
  function resolvedRowHtml(ev) {
    var name = ev.skipper_name || ev.boat || ev.vessel_id || 'Unidentified vessel';
    var sender = (ev.skipper_name || ev.phone)
      ? '<div class="incident-feed-sender"><span>Sender: ' + escapeHtml(ev.skipper_name || 'Unnamed vessel') +
        (ev.phone ? ' \u00b7 ' + escapeHtml(ev.phone) : '') + '</span></div>'
      : '';
    var reply = ev.fisher_reply;
    var reportHtml = reply === 1
      ? '<div class="alert-fisher-report alert-fisher-danger">Fisher reports: STILL IN DANGER</div>'
      : (reply === 2
        ? '<div class="alert-fisher-report alert-fisher-safe">Fisher reports: SAFE NOW</div>'
        : '');
    var regHtml = (typeof ns.registrationBadgeHtml === 'function')
      ? '<div class="incident-feed-reg">' + ns.registrationBadgeHtml(ev.license_type) + '</div>'
      : '';
    var when = ev.resolved_at || ev.created_at || '';
    return '<div class="incident-feed-row incident-feed-resolved">' +
      '<div class="incident-feed-info">' +
        '<div class="incident-feed-desc">' + escapeHtml(name) +
          (ev.note ? ' — “' + escapeHtml(ev.note) + '”' : '') + '</div>' +
        sender +
        reportHtml +
        regHtml +
        '<div class="incident-feed-meta">Resolved ' + escapeHtml(when) + '</div>' +
        '<button class="incident-feed-reopen" data-event-id="' + ev.id + '">Reopen</button>' +
      '</div>' +
    '</div>';
  }

  function renderResolvedFeed(events) {
    var el = document.getElementById('resolved-feed-list');
    if (!el) return;
    var list = Array.isArray(events) ? events : [];
    if (list.length === 0) {
      el.innerHTML = '<p class="panel-stub-text">No resolved incidents yet</p>';
      return;
    }
    el.innerHTML = list.map(resolvedRowHtml).join('');
    el.querySelectorAll('.incident-feed-reopen').forEach(function (btn) {
      btn.addEventListener('click', function (event) {
        event.stopPropagation();
        reopenIncident(btn.getAttribute('data-event-id'));
      });
    });
  }

  function reopenIncident(eventId) {
    if (typeof ns.authFetch !== 'function') return Promise.resolve();
    return ns.authFetch('/api/sos/' + encodeURIComponent(eventId) + '/reopen', {
      method: 'POST'
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function () {
        if (typeof ns.loadActiveSos === 'function') ns.loadActiveSos();
        return loadResolvedSos();
      })
      .catch(function (err) {
        console.warn('[AqOne] Reopen not delivered:', err.message);
      });
  }

  function loadResolvedSos() {
    if (typeof ns.authFetch !== 'function') return Promise.resolve();
    return ns.authFetch('/api/sos/recent')
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        renderResolvedFeed(data && data.events);
      })
      .catch(function (err) {
        console.warn('[AqOne] Resolved SOS poll failed:', err.message);
      });
  }

  // ===== INCIDENT FEED =====
  function renderIncidentFeed() {
    var el = document.getElementById('incident-feed-list');
    if (!el) return;
    var active = allAlerts().filter(function (a) { return a.status !== 'resolved'; });
    if (active.length === 0) {
      el.innerHTML = '<p class="panel-stub-text">No active incidents</p>';
      return;
    }
    var shown = active.slice(0, 4);
    el.innerHTML = shown.map(function (a, i) {
      var badge = typeof ns.alertBadge === 'function' ? ns.alertBadge(a.isLive) : (a.isLive ? { cssClass: 'alert-live-badge', text: 'LIVE' } : { cssClass: 'alert-demo-badge', text: 'DEMO' });
      var titleAttr = a.isLive ? '' : ' title="Scripted sample data, not a real incident"';
      var badgeHtml = '<span class="' + badge.cssClass + '"' + titleAttr + '>' + badge.text + '</span>';
      var reply = a.fisherReply != null ? a.fisherReply : (a.drawerData && a.drawerData.fisherReply);
      var reportHtml = reply === 1
        ? '<div class="alert-fisher-report alert-fisher-danger">Fisher reports: STILL IN DANGER</div>'
        : (reply === 2
          ? '<div class="alert-fisher-report alert-fisher-safe">Fisher reports: SAFE NOW</div>'
          : '');
      var regHtml = (typeof ns.registrationBadgeHtml === 'function')
        ? '<div class="incident-feed-reg">' + ns.registrationBadgeHtml(a.drawerData && a.drawerData.licenseType) + '</div>'
        : '';
      return '<div class="incident-feed-row' + (a.isLive ? ' incident-feed-live' : '') +
        '" data-idx="' + i + '">' +
        alertIcon(a.type) +
        '<div class="incident-feed-info">' +
          '<div class="incident-feed-desc">' + badgeHtml + escapeHtml(a.desc) + '</div>' +
          ((a.owner || a.phone)
            ? '<div class="incident-feed-sender"><span>Sender: ' + escapeHtml(a.owner || 'Unnamed vessel') +
              (a.phone ? ' \u00b7 ' + escapeHtml(a.phone) : '') + '</span></div>'
            : '') +
          reportHtml +
          regHtml +
          '<div class="incident-feed-meta">' + escapeHtml(a.time) + '</div>' +
        '</div>' +
      '</div>';
    }).join('');
    el.querySelectorAll('.incident-feed-row').forEach(function (row) {
      row.addEventListener('click', function () {
        // Indexes into the filtered list that was actually rendered. This
        // previously indexed the unfiltered array, so a click could pan to a
        // different incident than the one clicked.
        var a = shown[row.dataset.idx];
        if (!a) return;
        if (a.lat != null && a.lng != null) {
          map.setView([a.lat, a.lng], 14, { animate: true, duration: 1 });
        }
        if (a.drawerData && (a.sosEventId != null || a.type === 'sos') && typeof ns.openIncidentDrawer === 'function') {
          ns.openIncidentDrawer(a.drawerData, (ns.liveSosMarkers && a.sosEventId != null && ns.liveSosMarkers[a.sosEventId]) || null);
        }
      });
    });
  }
  renderIncidentFeed();
  loadResolvedSos();
  if (typeof setInterval === 'function') {
    setInterval(loadResolvedSos, 10000);
  }


  // ===== BUOY HEALTH MONITOR =====
  const buoyMonitorData = initialBuoys.map(function (b) {
    return {
      id: b.id, name: b.name, status: b.status === 'active' ? 'online' : (b.status === 'danger' ? 'offline' : 'online'),
      severity: b.pressureTrend != null && b.pressureTrend <= -2.5 ? 'Pressure drop \u2014 squall watch' : 'Nominal',
      battery: b.battery, lastSignal: b.status === 'danger' ? '2 hours ago' : '1 minute ago',
      lat: b.lat, lng: b.lng,
      pressure: b.pressure, pressureTrend: b.pressureTrend,
      current: b.current, currentDir: b.currentDir,
      dotClass: b.status === 'active' ? 'dot-green' : (b.status === 'danger' ? 'dot-gray' : 'dot-yellow')
    };
  });

  const buoyRailBtn     = document.getElementById('rail-btn-buoy');
  const buoyRailBadge   = document.getElementById('buoy-rail-badge');
  const buoyDrawerBadge = document.getElementById('buoy-drawer-badge');
  const buoyListEl      = document.getElementById('buoy-list');
  const buoyFooter      = document.getElementById('buoy-drawer-footer');

  let buoySyncTime = Date.now();

  var buoyOnlineCount = buoyMonitorData.filter(function (b) { return b.status === 'online'; }).length;
  var buoyTotal = buoyMonitorData.length;
  if (buoyRailBadge) buoyRailBadge.textContent = buoyOnlineCount + '/' + buoyTotal;
  if (buoyDrawerBadge) buoyDrawerBadge.textContent = buoyOnlineCount + '/' + buoyTotal + ' Online';
  if (buoyOnlineCount < buoyTotal) {
    if (buoyRailBadge) buoyRailBadge.classList.add('badge-amber');
    if (buoyDrawerBadge) buoyDrawerBadge.classList.add('badge-amber');
  }

  function renderBuoyList() {
    buoyListEl.innerHTML = buoyMonitorData.map(function (b) {
      var offlineClass = b.status === 'offline' ? ' buoy-offline' : '';
      var batteryClass = b.battery < 20 ? ' low' : '';
      var batteryIcon = b.battery < 20
        ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
        : '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="7" width="12" height="14" rx="2"/><path d="M10 7V5a2 2 0 0 1 4 0v2"/></svg>';

      var pressureText = b.pressure != null
        ? b.pressure.toFixed(1) + ' hPa' + (b.pressureTrend != null ? ' (' + (b.pressureTrend > 0 ? '+' : '') + b.pressureTrend + '/30m)' : '')
        : 'n/a';

      return '<div class="buoy-row' + offlineClass + '" data-lat="' + b.lat + '" data-lng="' + b.lng + '" data-id="' + b.id + '">' +
        '<div class="buoy-row-top">' +
          '<span class="buoy-row-name">' + escapeHtml(b.name) + '</span>' +
          '<span class="buoy-status-dot ' + b.dotClass + '"></span>' +
        '</div>' +
        '<div class="buoy-row-severity">' + escapeHtml(b.severity) + '</div>' +
        '<div class="buoy-row-meta">' +
          '<span class="buoy-row-battery' + batteryClass + '">' + batteryIcon + ' ' + b.battery + '%</span>' +
          '<span class="buoy-row-signal">' + pressureText + '</span>' +
        '</div>' +
        '<div class="buoy-row-meta">' +
          '<span class="buoy-row-signal">Current: ' + escapeHtml(b.current || 'n/a') + ' ' + escapeHtml(b.currentDir || '') + '</span>' +
          '<span class="buoy-row-signal">' + escapeHtml(b.lastSignal) + '</span>' +
        '</div>' +
      '</div>';
    }).join('');

    buoyListEl.querySelectorAll('.buoy-row').forEach(function (row) {
      row.addEventListener('click', function () {
        var lat = parseFloat(row.dataset.lat);
        var lng = parseFloat(row.dataset.lng);
        map.setView([lat, lng], 13);
        console.log('[AqOne] Buoy selected:', row.dataset.id);
      });
    });
  }

  function renderBuoyHealthCard() {
    var online = buoyMonitorData.filter(function (b) { return b.status === 'online'; }).length;
    var total = buoyMonitorData.length;
    document.getElementById('buoy-health-badge').textContent = online + '/' + total;

    var list = document.getElementById('buoy-health-list');
    list.innerHTML = buoyMonitorData.map(function (b) {
      var dotColor = b.status === 'online' ? '#2ecc71' : '#e74c3c';
      var offlineTag = b.status === 'offline'
        ? ' <span class="bh-offline-tag">Offline, last seen ' + escapeHtml(b.lastSignal) + '</span>'
        : '';
      var pressTag = b.pressure != null
        ? ' <span class="bh-press" style="color:' + (b.pressureTrend <= -2.5 ? '#e67e22' : 'inherit') + ';">' + b.pressure.toFixed(1) + ' hPa</span>'
        : '';
      return '<div class="bh-row' + (b.status === 'offline' ? ' bh-offline' : '') + '" data-lat="' + b.lat + '" data-lng="' + b.lng + '">' +
        '<span class="bh-dot" style="background:' + dotColor + ';"></span>' +
        '<span class="bh-name">' + escapeHtml(b.name) + '</span>' +
        '<span class="bh-battery">' + b.battery + '%</span>' +
        pressTag +
        offlineTag +
      '</div>';
    }).join('');

    list.querySelectorAll('.bh-row').forEach(function (row) {
      row.addEventListener('click', function () {
        map.setView([parseFloat(row.dataset.lat), parseFloat(row.dataset.lng)], 14, { animate: true, duration: 1 });
      });
    });
  }

  function renderBuoyHealth() {
    var sourceBuoys = buoyMonitorData;
    var activeCount = sourceBuoys.filter(function (b) { return b.status === 'online'; }).length;
    var totalCount = sourceBuoys.length;
    var countText = activeCount + '/' + totalCount + ' Online';

    var badgeCount = document.getElementById('buoy-health-badge');
    if (badgeCount) badgeCount.textContent = countText;
    buoyRailBadge.textContent = activeCount + '/' + totalCount;
    buoyDrawerBadge.textContent = countText;

    if (activeCount < totalCount) {
      buoyRailBadge.classList.add('badge-amber');
      buoyDrawerBadge.classList.add('badge-amber');
    } else {
      buoyRailBadge.classList.remove('badge-amber');
      buoyDrawerBadge.classList.remove('badge-amber');
    }
  }

  renderBuoyList();
  renderBuoyHealthCard();
  renderBuoyHealth();

  document.getElementById('buoy-health-header').addEventListener('click', function (e) {
    if (e.target.closest('#buoy-health-toggle')) return;
    openPanel('buoys');
  });
  document.getElementById('buoy-health-toggle').addEventListener('click', function (e) {
    e.stopPropagation();
    openPanel('buoys');
  });

  if (buoyFooter) {
    buoyFooter.textContent = 'Sample buoy network baseline (unpolled offline data)';
  }


  // ===== VIEWPORT-BASED STATS =====
  function updateStats() {
    const bounds = map.getBounds();
    let buoysInView = 0;
    let vesselsInView = 0;
    let incidentsInView = 0;

    initialBuoys.forEach(b => { if (bounds.contains([b.lat, b.lng])) buoysInView++; });
    vessels.forEach(v => { if (bounds.contains([v.lat, v.lng])) vesselsInView++; });
    incidents.forEach(i => { if (bounds.contains([i.lat, i.lng])) incidentsInView++; });

    document.getElementById('stat-buoys').textContent = Math.max(4, buoysInView) + '/' + initialBuoys.length;
    document.getElementById('stat-coverage').textContent = (68 + buoysInView * 4) + '%';
    document.getElementById('stat-vessels').textContent = (38 + vesselsInView * 3);
    document.getElementById('stat-leadtime').textContent = '45 min';
    document.getElementById('stat-alerts').textContent = incidentsInView;
  }

  map.on('moveend', updateStats);
  map.on('zoomend', updateStats);


  // ===== COORDINATES =====
  function formatCoord(val, pos, neg) {
    const abs = Math.abs(val);
    const deg = Math.floor(abs);
    const min = ((abs - deg) * 60).toFixed(3);
    return deg + '\u00B0 ' + min + '\u2032 ' + (val >= 0 ? pos : neg);
  }

  map.on('mousemove', function (e) {
    document.getElementById('coords-lat').textContent = formatCoord(e.latlng.lat, 'N', 'S');
    document.getElementById('coords-lng').textContent = formatCoord(e.latlng.lng, 'E', 'W');
  });

  map.on('zoomend', function () {
    document.getElementById('coords-zoom').textContent = 'Zoom: ' + map.getZoom();
  });


  // ===== HOME / RECENTER =====
  const compassWidget = document.getElementById('compass-widget');

  compassWidget.addEventListener('click', function () {
    map.setView(OPS_CENTER, OPS_ZOOM);
  });


  // ===== FULLSCREEN =====
  document.getElementById('btn-fullscreen').addEventListener('click', function () {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  });


  // ===== CENTER ON REGION =====
  document.getElementById('btn-center-aklan').addEventListener('click', function () {
    map.setView(OPS_CENTER, OPS_ZOOM, { animate: true, duration: 1 });
    if (ns.activePanel) closePanel();
  });


  // ===== EXPORT =====
  document.getElementById('btn-export').addEventListener('click', function () {
    const data = {
      center: map.getCenter(),
      zoom: map.getZoom(),
      gateways: shoreStations.length,
      buoys: initialBuoys.length,
      incidents: incidents.length,
      timestamp: new Date().toISOString()
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'aqone-sar-console-export.json';
    a.click();
    URL.revokeObjectURL(url);
  });

  ns.renderIncidentFeed = renderIncidentFeed;
  ns.renderResolvedFeed = renderResolvedFeed;
  ns.loadResolvedSos = loadResolvedSos;
  ns.reopenIncident = reopenIncident;
  ns.updateStats = updateStats;

})(window.AqOneDashboard = window.AqOneDashboard || {});
