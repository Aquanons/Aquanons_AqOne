(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var OPS_CENTER = ns.OPS_CENTER;
  var OPS_ZOOM = ns.OPS_ZOOM;
  var utils = ns.dashboardUtils || window.AqOneDashboardUtils;
  var formatLatLon = ns.formatLatLon || function () { return 'unknown position'; };
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
  var resolvedAll = [];
  var resolvedExpanded = false;
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
    var whenMs = Date.parse(ev.resolved_at || ev.created_at || '');
    var when = isFinite(whenMs)
      ? new Date(whenMs).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
      : 'at an unknown time';
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
    resolvedAll = Array.isArray(events) ? events : [];
    renderResolvedVisible();
  }

  function renderResolvedVisible() {
    var el = document.getElementById('resolved-feed-list');
    if (!el) return;
    var toggle = document.getElementById('resolved-view-toggle');
    if (resolvedAll.length === 0) {
      el.innerHTML = '<p class="panel-stub-text">No resolved incidents yet</p>';
      if (toggle) toggle.hidden = true;
      return;
    }
    var visible = resolvedExpanded ? resolvedAll : resolvedAll.slice(0, 5);
    el.innerHTML = visible.map(resolvedRowHtml).join('');
    el.querySelectorAll('.incident-feed-reopen').forEach(function (btn) {
      btn.addEventListener('click', function (event) {
        event.stopPropagation();
        reopenIncident(btn.getAttribute('data-event-id'));
      });
    });
    if (toggle) {
      toggle.hidden = resolvedAll.length <= 5;
      toggle.textContent = resolvedExpanded ? 'Show less' : 'View all (' + resolvedAll.length + ')';
      toggle.title = resolvedExpanded ? 'Show fewer resolved incidents' : 'View all resolved incidents';
    }
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
    updateStats();
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
  var resolvedToggle = document.getElementById('resolved-view-toggle');
  if (resolvedToggle) {
    resolvedToggle.addEventListener('click', function () {
      resolvedExpanded = !resolvedExpanded;
      renderResolvedVisible();
    });
  }
  if (typeof setInterval === 'function') {
    setInterval(loadResolvedSos, 10000);
  }


  // ===== BUOY NETWORK PANEL =====
  // Reads the network dashboard-markers.js loads from GET /api/public/buoys.
  // A buoy is "active" when the backend heard it within the last hour.
  const buoyRailBadge   = document.getElementById('buoy-rail-badge');
  const buoyDrawerBadge = document.getElementById('buoy-drawer-badge');
  const buoyListEl      = document.getElementById('buoy-list');
  const buoyFooter      = document.getElementById('buoy-drawer-footer');
  var phoneCoverage = null;

  function currentNetwork() {
    return ns.network || { buoys: [], stations: [], loadedAt: null, failed: false };
  }

  function buoyCounts(net) {
    var active = net.buoys.filter(function (b) { return b.status === 'active'; }).length;
    return { active: active, total: net.buoys.length, text: net.loadedAt ? active + '/' + net.buoys.length : '--' };
  }

  function buoyNameHtml(b) {
    return (b.isSynthetic ? '<span class="alert-demo-badge">DEMO</span>' : '') + escapeHtml(b.name);
  }

  function buoyRowHtml(b, now) {
    var placed = b.lat != null;
    var dot = b.status === 'active' ? 'dot-green' : (b.status === 'silent' ? 'dot-yellow' : 'dot-gray');
    return '<div class="buoy-row' + (b.status === 'active' ? '' : ' buoy-offline') + '"' +
      (placed ? ' data-lat="' + b.lat + '" data-lng="' + b.lng + '"' : '') + ' data-id="' + escapeHtml(b.id) + '">' +
      '<div class="buoy-row-top">' +
        '<span class="buoy-row-name">' + buoyNameHtml(b) + '</span>' +
        '<span class="buoy-status-dot ' + dot + '"></span>' +
      '</div>' +
      '<div class="buoy-row-severity">' + escapeHtml(utils.buoyHeardText(b, now)) + '</div>' +
      '<div class="buoy-row-meta">' +
        '<span class="buoy-row-signal">' + escapeHtml(placed ? formatLatLon(b.lat, b.lng) : 'Position not recorded') + '</span>' +
        (b.isGateway ? '<span class="buoy-row-signal">Gateway link</span>' : '') +
      '</div>' +
    '</div>';
  }

  function panToRow(row, zoom) {
    if (!row.dataset.lat) return;
    map.setView([parseFloat(row.dataset.lat), parseFloat(row.dataset.lng)], zoom, { animate: true, duration: 1 });
  }

  function renderBuoyNetwork() {
    var net = currentNetwork();
    var now = Date.now();
    var counts = buoyCounts(net);
    var degraded = counts.active < counts.total;
    if (buoyRailBadge) {
      buoyRailBadge.textContent = counts.text;
      buoyRailBadge.classList.toggle('badge-amber', degraded);
    }
    if (buoyDrawerBadge) {
      buoyDrawerBadge.textContent = counts.text + ' active';
      buoyDrawerBadge.classList.toggle('badge-amber', degraded);
    }
    var healthBadge = document.getElementById('buoy-health-badge');
    if (healthBadge) healthBadge.textContent = counts.text;

    var empty = '<p class="panel-stub-text">' +
      (net.failed ? 'Buoy network unavailable' : (net.loadedAt ? 'No buoys registered' : 'Loading buoy network...')) + '</p>';
    if (buoyListEl) {
      buoyListEl.innerHTML = counts.total ? net.buoys.map(function (b) { return buoyRowHtml(b, now); }).join('') : empty;
      buoyListEl.querySelectorAll('.buoy-row').forEach(function (row) {
        row.addEventListener('click', function () { panToRow(row, 13); });
      });
    }
    var healthList = document.getElementById('buoy-health-list');
    if (healthList) {
      healthList.innerHTML = counts.total ? net.buoys.map(function (b) {
        return '<div class="bh-row' + (b.status === 'active' ? '' : ' bh-offline') + '"' +
          (b.lat != null ? ' data-lat="' + b.lat + '" data-lng="' + b.lng + '"' : '') + '>' +
          '<span class="bh-dot" style="background:' + (b.status === 'active' ? '#2ecc71' : '#e74c3c') + ';"></span>' +
          '<span class="bh-name">' + buoyNameHtml(b) + '</span>' +
          '<span class="bh-offline-tag">' + escapeHtml(utils.buoyHeardText(b, now)) + '</span>' +
        '</div>';
      }).join('') : empty;
      healthList.querySelectorAll('.bh-row').forEach(function (row) {
        row.addEventListener('click', function () { panToRow(row, 14); });
      });
    }
    if (buoyFooter) {
      buoyFooter.textContent = net.loadedAt
        ? 'Registered buoys, checked ' + new Date(net.loadedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : (net.failed ? 'Buoy network unavailable' : 'Loading buoy network...');
    }
    phoneCoverage = utils.phoneCoverageFraction(ns.opsBoundary, net.buoys);
    updateStats();
  }

  document.getElementById('buoy-health-header').addEventListener('click', function (e) {
    if (e.target.closest('#buoy-health-toggle')) return;
    openPanel('buoys');
  });
  document.getElementById('buoy-health-toggle').addEventListener('click', function (e) {
    e.stopPropagation();
    openPanel('buoys');
  });


  // ===== LIVE OVERVIEW FIGURES =====
  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function updateStats() {
    var counts = buoyCounts(currentNetwork());
    setText('stat-buoys', counts.total ? counts.text : '--');
    setText('stat-coverage', phoneCoverage == null ? '--' : Math.round(phoneCoverage * 100) + '%');
    setText('stat-alerts', String(allAlerts().filter(function (a) { return a.status !== 'resolved'; }).length));
  }

  if (typeof ns.onNetworkChange === 'function') ns.onNetworkChange(renderBuoyNetwork);
  renderBuoyNetwork();


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
    var net = currentNetwork();
    const data = {
      center: map.getCenter(),
      zoom: map.getZoom(),
      gateways: net.stations.length,
      buoys: net.buoys.length,
      active_alerts: allAlerts().filter(function (a) { return a.status !== 'resolved'; }).length,
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
