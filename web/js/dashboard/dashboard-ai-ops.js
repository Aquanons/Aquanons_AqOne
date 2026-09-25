(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var authFetch = ns.authFetch;
  var incidents = ns.incidents;
  var map = ns.map;
  var showToast = ns.showToast || function () {};
  var escapeHtml = ns.escapeHtml;

  // ===== AI OPERATIONS =====
  var aiContoursLayer = ns.driftLayer || (typeof L !== 'undefined' && typeof L.layerGroup === 'function' ? L.layerGroup().addTo(map) : null);
  var aiSquallLayer = (ns.squallLayer && typeof ns.squallLayer.getBounds === 'function')
    ? ns.squallLayer
    : (typeof L !== 'undefined' && typeof L.featureGroup === 'function' ? L.featureGroup().addTo(map) : (typeof L !== 'undefined' && typeof L.layerGroup === 'function' ? L.layerGroup().addTo(map) : null));
  var aiRefreshTimer = null;
  var aiFreshnessTimer = null;

  // Responder-approved detection-method presets (docs/40 Phase 3 item 2,
  // docs/05_PUBLIC_API.md). Mirrors app/api/drift.py DETECTION_METHOD_LABELS
  // - the UI only ever submits one of these named presets, never a raw
  // probability.
  var DETECTION_METHODS = [
    { value: 'poor', label: 'Poor visibility / air search only (0.3)' },
    { value: 'moderate', label: 'Daylight surface vessel search (0.6)' },
    { value: 'good', label: 'Good conditions, multi-asset close pattern (0.9)' }
  ];

  // The current drift payload (whatever loadDriftIncidentDetail last
  // rendered) and the in-progress "mark a searched sector" interaction -
  // two native map clicks pick opposite corners, no drawing-library
  // dependency (docs/40 Phase 4 item 2).
  var currentDriftPayload = null;
  var aiDrawLayer = L.layerGroup().addTo(map);
  var sectorDraw = { active: false, corner1: null, bounds: null };

  var aiColors = {
    contour95: '#ef4444',
    contour75: '#f59e0b',
    contour50: '#facc15',
    track: '#2563eb',
    squall: '#22c55e',
    nextArea: '#38bdf8'
  };

  var AI_FETCH_TIMEOUT_MS = 25000;

  function aiFetchJson(path, options) {
    var opts = options || {};
    var signal = opts.signal || (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
      ? AbortSignal.timeout(AI_FETCH_TIMEOUT_MS)
      : undefined);
    return authFetch(path, Object.assign({}, opts, signal ? { signal: signal } : {}))
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      });
  }

  function aiStatusClass(status) {
    var map = { alert: 'status-alert', overdue: 'status-overdue', watch: 'status-watch', normal: 'status-normal' };
    return map[status] || 'status-normal';
  }

  function aiRiskPriority(status) {
    return ({ alert: 0, overdue: 1, watch: 2, normal: 3 })[status] ?? 9;
  }

  function clearAiDriftLayers() {
    aiContoursLayer.clearLayers();
    updateAiMapKey();
  }

  function clearAiSquallLayers() {
    aiSquallLayer.clearLayers();
    updateAiMapKey();
  }

  function updateAiMapKey() {
    var key = document.getElementById('ai-map-key');
    if (!key) return;
    key.style.display = 'none';
  }

  // Banner count and header badge follow the backend's own `level`/
  // `return_now` (docs/05_PUBLIC_API.md "Squall nowcast") rather than
  // re-deriving an alarm condition from raw probabilities client-side -
  // the same rule the mobile client follows (SquallWatch never re-derives
  // return_now either), so the dashboard and the handset can never disagree
  // about whether a squall is happening.
  function updateSquallBanner(payload) {
    var level = payload && payload.level;
    var isReturnNow = level === 'return_now';

    var countEl = document.getElementById('banner-squall-count');
    if (countEl) countEl.textContent = isReturnNow ? '1' : '0';

    var squallStatusEl = document.getElementById('stats-squall-status');
    if (squallStatusEl) {
      squallStatusEl.textContent = isReturnNow ? 'RETURN NOW' : (level === 'watch' ? 'WATCH' : (level === 'unknown' ? 'UNKNOWN' : 'MONITORING'));
      squallStatusEl.className = 'metric-status metric-status-watch' + (isReturnNow ? ' metric-status-danger' : '');
    }

    var statusEl = document.getElementById('squall-status');
    if (!statusEl) return;
    statusEl.classList.remove('squall-watch', 'squall-return', 'squall-unknown');
    if (isReturnNow) {
      statusEl.textContent = 'RETURN NOW';
      statusEl.classList.add('squall-return');
    } else if (level === 'watch') {
      statusEl.textContent = 'WATCH';
      statusEl.classList.add('squall-watch');
    } else if (level === 'unknown') {
      statusEl.textContent = 'UNKNOWN';
      statusEl.classList.add('squall-unknown');
    } else {
      statusEl.textContent = 'MONITORING';
    }
  }

  function ageLimitText(seconds) {
    if (typeof seconds !== 'number') return null;
    return Math.round(seconds / 60) + 'min';
  }

  function drawSearchedSectors(sectors, origin) {
    if (!origin || !sectors || !sectors.length) return;
    var mPerDegLat = 110574.0;
    var mPerDegLon = 111320.0 * Math.cos(origin.lat * Math.PI / 180);
    sectors.forEach(function (sector) {
      var south = origin.lat + sector.y_min_m / mPerDegLat;
      var north = origin.lat + sector.y_max_m / mPerDegLat;
      var west = origin.lon + sector.x_min_m / mPerDegLon;
      var east = origin.lon + sector.x_max_m / mPerDegLon;
      var box = L.rectangle([[south, west], [north, east]], {
        pane: 'aiContoursPane',
        color: '#94a3b8',
        weight: 1.5,
        opacity: 0.9,
        fillColor: '#64748b',
        fillOpacity: 0.22,
        dashArray: '4 4'
      }).addTo(aiContoursLayer);
      var pod = typeof sector.detection_probability === 'number'
        ? Math.round(sector.detection_probability * 100) + '% detection probability'
        : 'searched';
      // Audit trail (docs/40 Phase 4 item 3): method/reporter/time are only
      // present on a Phase 3 protected report - a legacy/demo sector has none.
      var when = sector.searched_at ? new Date(sector.searched_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : null;
      var tooltip = 'Searched — ' + pod +
        (sector.method_label ? '<br>' + escapeHtml(sector.method_label) : '') +
        (sector.reported_by ? '<br>Reported by ' + escapeHtml(sector.reported_by) : '') +
        (when ? '<br>' + when : '') +
        (sector.notes ? '<br>"' + escapeHtml(sector.notes) + '"' : '');
      box.bindTooltip(tooltip, { sticky: true, direction: 'center', className: 'drift-incident-label' });
    });
  }

  function drawNextArea(nextArea) {
    if (!nextArea || !nextArea.bounds) return;
    var b = nextArea.bounds;
    L.rectangle([[b.south, b.west], [b.north, b.east]], {
      pane: 'aiContoursPane',
      color: aiColors.nextArea,
      weight: 2.5,
      opacity: 0.95,
      fill: false,
      dashArray: '3 6'
    }).addTo(aiContoursLayer).bindTooltip(
      nextArea.label + ' — ' + Math.round((nextArea.remaining_mass || 0) * 100) + '% of remaining probability',
      { sticky: true, direction: 'center', className: 'drift-incident-label' }
    );
  }

  function renderDriftContours(payload) {
    cancelSectorDraw();
    clearAiDriftLayers();
    currentDriftPayload = payload;
    var incident = payload && payload.incident;
    var metaEl = document.getElementById('ai-drift-meta');
    var isRealCase = payload && typeof payload.environmental_status === 'string';

    if (isRealCase) {
      renderRealCaseDrift(payload, incident, metaEl);
    } else {
      renderLegacyDrift(payload, incident, metaEl);
    }

    renderSearchControls(payload);
    updateAiMapKey();
  }

  // A real, responder-opened case (docs/40 Phases 1-3): reads the stored
  // run exactly as GET returned it - never recomputes, never fabricates a
  // contour when the environmental inputs were insufficient.
  function renderRealCaseDrift(payload, incident, metaEl) {
    var isOk = payload.environmental_status === 'ok';
    var contourBounds = L.latLngBounds([]);

    if (isOk && payload.contours && payload.contours.length) {
      payload.contours.forEach(function (feature) {
        var mass = feature.properties && feature.properties.mass;
        var contourLabel = mass >= 0.9 ? '95% search area' : (mass >= 0.7 ? '75% search area' : '50% search area');
        var color = mass >= 0.9 ? aiColors.contour95 : (mass >= 0.7 ? aiColors.contour75 : aiColors.contour50);
        var layer = L.geoJSON(feature, {
          pane: 'aiContoursPane',
          style: function () {
            return {
              color: color, weight: mass >= 0.9 ? 3 : 2.25, opacity: 0.95, fillColor: color,
              fillOpacity: mass >= 0.9 ? 0.12 : (mass >= 0.7 ? 0.10 : 0.08), dashArray: mass >= 0.9 ? '2 4' : ''
            };
          },
          onEachFeature: function (feat, lyr) {
            lyr.bindTooltip(
              contourLabel + (incident ? ' · case #' + incident.id + ' · run ' + payload.run_number : ''),
              { sticky: true, direction: 'center', className: 'drift-incident-label' }
            );
          }
        });
        layer.addTo(aiContoursLayer);
        contourBounds.extend(layer.getBounds());
      });
      var origin = payload.posterior_grid && payload.posterior_grid.origin;
      drawSearchedSectors(payload.search_sectors, origin);
      drawNextArea(payload.next_area);
    }

    if (contourBounds.isValid()) {
      map.fitBounds(contourBounds.pad(0.12), { animate: true, duration: 0.9, maxZoom: 14 });
    } else if (incident) {
      map.setView([incident.last_contact_lat, incident.last_contact_lon], 13, { animate: true });
    }

    if (!metaEl || !incident) return;

    var incidentTime = incident.last_contact_at ? new Date(incident.last_contact_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '--';
    var computedAt = payload.computed_at ? new Date(payload.computed_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '--';
    var bits = [];

    if (isOk && payload.prediction && payload.prediction.object_class) {
      bits.push('Drift class: <strong>' + escapeHtml(String(payload.prediction.object_class).replace(/_/g, ' ')) + '</strong>');
    }
    if (typeof payload.observation_fraction === 'number') {
      var pct = Math.round(payload.observation_fraction * 100);
      bits.push(pct > 0
        ? 'Currents: <strong>' + pct + '% from buoy observations</strong>'
        : 'Currents: <strong>simulated</strong> (no buoy observations yet)');
    }
    if (isOk && payload.prediction && payload.prediction.wind_source) {
      bits.push('Wind: ' + escapeHtml(payload.prediction.wind_source) +
        (payload.prediction.degraded ? ' <span class="drift-degraded">(degraded — live wind unavailable)</span>' : ''));
    }
    bits.push('Nearby buoys: <strong>' + (payload.nearby_buoy_count || 0) + '</strong>' +
      ' (max age ' + (ageLimitText(payload.current_max_age_seconds) || 'n/a') +
      ', wind max age ' + (ageLimitText(payload.max_wind_age_seconds) || 'n/a') + ')');
    if (isOk && payload.search_sectors && payload.search_sectors.length) {
      bits.push('<strong>' + payload.search_sectors.length + '</strong> sector' + (payload.search_sectors.length === 1 ? '' : 's') +
        ' searched — contours show the updated posterior');
    }

    var statusLine = isOk
      ? 'Snapshot computed ' + computedAt + ' · run ' + payload.run_number
      : '<span class="ai-insufficient-badge">INSUFFICIENT ENVIRONMENTAL DATA</span><br>' +
        'Reason: ' + escapeHtml(payload.insufficiency_reason || 'unknown') + ' · run ' + payload.run_number;

    metaEl.innerHTML =
      '<strong>Case #' + incident.id + '</strong> · Vessel ' + escapeHtml(incident.vessel_id) +
      ' · <span class="ai-case-state">' + escapeHtml(incident.case_state) + '</span><br>' +
      'Last contact: ' + incidentTime + ' · source: ' + escapeHtml(incident.source_type) + '<br>' +
      statusLine + '<br>' +
      (bits.length ? bits.join(' · ') : '') +
      '<br><button type="button" class="action-btn ai-drift-activity-btn" id="ai-drift-activity-btn">View Activity</button>';

    // Rebound after every innerHTML rewrite, same as the rest of this
    // render function - a read, not a mutation, so it stays available
    // regardless of case_state (docs/41 Phase 4).
    var activityBtn = document.getElementById('ai-drift-activity-btn');
    if (activityBtn && ns.openActivityDrawer) {
      activityBtn.addEventListener('click', function () {
        ns.openActivityDrawer('drift_incident', incident.id, 'Drift/Search Case Activity');
      });
    }
  }

  // The simulator/demo scenario engine path (docs/40 Phase 1 item 4): no
  // stored run exists, so this keeps the pre-Phase-2 recompute-on-read
  // rendering unchanged.
  function renderLegacyDrift(payload, incident, metaEl) {
    var prediction = payload && payload.prediction;
    var track = (payload && payload.ground_truth_track) || [];

    var contours = (payload && payload.contours && payload.contours.length)
      ? payload.contours
      : (prediction && prediction.contours);

    if (!contours || !contours.length) {
      if (metaEl) metaEl.textContent = 'No drift contours available for the selected incident.';
      return;
    }

    var contourBounds = L.latLngBounds([]);

    contours.forEach(function (feature) {
      var mass = feature.properties && feature.properties.mass;
      var contourLabel = mass >= 0.9 ? '95% search area' : (mass >= 0.7 ? '75% search area' : '50% search area');
      var color = mass >= 0.9 ? aiColors.contour95 : (mass >= 0.7 ? aiColors.contour75 : aiColors.contour50);
      var layer = L.geoJSON(feature, {
        pane: 'aiContoursPane',
        style: function () {
          return {
            color: color,
            weight: mass >= 0.9 ? 3 : 2.25,
            opacity: 0.95,
            fillColor: color,
            fillOpacity: mass >= 0.9 ? 0.12 : (mass >= 0.7 ? 0.10 : 0.08),
            dashArray: mass >= 0.9 ? '2 4' : ''
          };
        },
        onEachFeature: function (feat, lyr) {
          // The incident id is named in the tooltip so a large red polygon can
          // never be mistaken for a live emergency. These are replayed
          // synthetic incidents; the map should say so where someone hovers.
          lyr.bindTooltip(
            contourLabel +
            (incident ? ' · replayed incident #' + incident.id + (incident.is_synthetic ? ' (synthetic)' : '') : ''),
            {
              sticky: true,
              direction: 'center',
              className: 'drift-incident-label'
            }
          );
        }
      });
      layer.addTo(aiContoursLayer);
      contourBounds.extend(layer.getBounds());
    });

    if (track.length) {
      var trackLatLngs = track.map(function (point) {
        return [point.lat, point.lon];
      });
      var trackLine = L.polyline(trackLatLngs, {
        pane: 'aiTrackPane',
        color: aiColors.track,
        weight: 4,
        opacity: 0.95,
        dashArray: '10 8',
        lineCap: 'round'
      }).addTo(aiContoursLayer);
      trackLine.bindTooltip('Ground truth track', {
        sticky: true,
        direction: 'top',
        className: 'squall-track-label'
      });
      contourBounds.extend(trackLine.getBounds());
    }

    // Sector bounds arrive in metres relative to the posterior grid's origin.
    var grid = payload && payload.posterior_grid;
    drawSearchedSectors(payload && payload.search_sectors, grid && grid.origin);

    if (contourBounds.isValid()) {
      map.fitBounds(contourBounds.pad(0.12), { animate: true, duration: 0.9, maxZoom: 14 });
    }

    if (metaEl && incident) {
      var incidentTime = incident.last_contact_at ? new Date(incident.last_contact_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '--';
      var bits = [];

      if (prediction && prediction.object_class) {
        bits.push('Drift class: <strong>' + escapeHtml(String(prediction.object_class).replace(/_/g, ' ')) + '</strong>');
      }
      if (typeof payload.observation_fraction === 'number') {
        var pct = Math.round(payload.observation_fraction * 100);
        bits.push(
          pct > 0
            ? 'Currents: <strong>' + pct + '% from buoy observations</strong>'
            : 'Currents: <strong>simulated</strong> (no buoy observations yet)'
        );
      }
      if (prediction && prediction.wind_source) {
        bits.push('Wind: ' + escapeHtml(prediction.wind_source) +
          (prediction.degraded ? ' <span class="drift-degraded">(degraded — live wind unavailable)</span>' : ''));
      }
      var searched = (payload && payload.search_sectors) || [];
      if (searched.length) {
        bits.push('<strong>' + searched.length + '</strong> sector' + (searched.length === 1 ? '' : 's') +
          ' searched — contours show the updated posterior');
      }

      metaEl.innerHTML =
        (incident.is_synthetic
          ? '<span class="drift-replay-badge">REPLAY — SYNTHETIC INCIDENT</span><br>'
          : '') +
        '<strong>Incident #' + incident.id + '</strong> · Vessel ' + escapeHtml(incident.vessel_id) + '<br>' +
        'Last contact: ' + incidentTime + ' · ' + escapeHtml(incident.abnormal_reason || 'unknown') + '<br>' +
        (bits.length ? bits.join(' · ') + '<br>' : '') +
        // The backend only ever includes ground_truth_track on a synthetic
        // incident's payload (app/api/drift.py) - this line must not claim a
        // real case has one.
        (incident.is_synthetic ? 'Track labeled as ground truth for synthetic evaluation.' : '');
    }
  }

  // ===== SEARCH-SECTOR REPORTING (docs/40 Phase 4) =====
  //
  // The smallest possible map interaction: two native Leaflet clicks pick
  // opposite corners of a rectangle, a responder picks an approved
  // detection-method preset, reviews a plain-text confirmation, and submits.
  // No drawing-library dependency, no second map.

  // Pure decision logic lives in dashboard-utils.js so it can be unit
  // tested directly (web/test/dashboard-utils.test.js) without a DOM.
  var eligibleForSearchReport = (ns.dashboardUtils && ns.dashboardUtils.eligibleForSearchReport) ||
    function () { return { ok: false, reason: 'unavailable' }; };

  function renderSearchControls(payload) {
    var container = document.getElementById('ai-drift-search');
    if (!container) return;

    if (sectorDraw.active || sectorDraw.bounds) {
      return; // an interaction is in progress - leave its own UI alone.
    }

    var eligibility = eligibleForSearchReport(payload);
    if (!eligibility.ok) {
      container.innerHTML = '<div class="ai-search-disabled-note">Search reporting unavailable — ' + escapeHtml(eligibility.reason) + '</div>';
      return;
    }

    container.innerHTML =
      '<button type="button" class="ai-drift-search-btn" data-action="start-search">Mark a searched area</button>';
  }

  function cancelSectorDraw() {
    // A pending map.once() handler only unregisters itself by firing - if
    // the responder cancels between the two corner clicks (or before the
    // first), it would otherwise sit bound forever waiting for a click that
    // is no longer meaningful. Removing both by reference is a safe no-op
    // when they were never registered or already fired.
    map.off('click', onFirstCorner);
    map.off('click', onSecondCorner);
    aiDrawLayer.clearLayers();
    sectorDraw.active = false;
    sectorDraw.corner1 = null;
    sectorDraw.bounds = null;
    var driftSelect = document.getElementById('ai-drift-select');
    if (driftSelect) driftSelect.disabled = false;
    renderSearchControls(currentDriftPayload);
  }

  function startSectorDraw() {
    if (!currentDriftPayload || !currentDriftPayload.incident) return;
    var eligibility = eligibleForSearchReport(currentDriftPayload);
    if (!eligibility.ok) return;

    aiDrawLayer.clearLayers();
    sectorDraw.active = true;
    sectorDraw.corner1 = null;
    sectorDraw.bounds = null;
    var driftSelect = document.getElementById('ai-drift-select');
    if (driftSelect) driftSelect.disabled = true;

    var container = document.getElementById('ai-drift-search');
    if (container) {
      container.innerHTML =
        '<div class="ai-search-disabled-note">Click the first corner of the searched area on the map…</div>' +
        '<button type="button" class="ai-drift-search-btn ai-drift-search-btn-cancel" data-action="cancel-search">Cancel</button>';
    }

    map.once('click', onFirstCorner);
  }

  function onFirstCorner(e) {
    if (!sectorDraw.active) return;
    sectorDraw.corner1 = e.latlng;
    var container = document.getElementById('ai-drift-search');
    if (container) {
      var note = container.querySelector('.ai-search-disabled-note');
      if (note) note.textContent = 'Click the second, opposite corner…';
    }
    map.once('click', onSecondCorner);
  }

  function onSecondCorner(e) {
    if (!sectorDraw.active || !sectorDraw.corner1) return;
    var c1 = sectorDraw.corner1;
    var c2 = e.latlng;
    var bounds = {
      south: Math.min(c1.lat, c2.lat),
      north: Math.max(c1.lat, c2.lat),
      west: Math.min(c1.lng, c2.lng),
      east: Math.max(c1.lng, c2.lng)
    };
    sectorDraw.active = false;
    sectorDraw.bounds = bounds;

    aiDrawLayer.clearLayers();
    L.rectangle([[bounds.south, bounds.west], [bounds.north, bounds.east]], {
      pane: 'aiContoursPane',
      color: '#38bdf8',
      weight: 2,
      dashArray: '5 5',
      fillOpacity: 0.15
    }).addTo(aiDrawLayer);

    renderConfirmPanel(bounds);
  }

  function renderConfirmPanel(bounds) {
    var container = document.getElementById('ai-drift-search');
    if (!container) return;

    var methodOptions = DETECTION_METHODS.map(function (m) {
      return '<option value="' + m.value + '">' + escapeHtml(m.label) + '</option>';
    }).join('');

    container.innerHTML =
      '<div class="ai-drift-confirm">' +
        '<div class="ai-drift-confirm-bounds">Searched area: ' +
          bounds.south.toFixed(4) + ', ' + bounds.west.toFixed(4) + ' → ' +
          bounds.north.toFixed(4) + ', ' + bounds.east.toFixed(4) +
        '</div>' +
        '<label class="ai-drift-confirm-label">Search method / visibility' +
          '<select id="ai-search-method">' + methodOptions + '</select>' +
        '</label>' +
        '<label class="ai-drift-confirm-label">Notes (optional)' +
          '<textarea id="ai-search-notes" maxlength="280" rows="2" placeholder="e.g. surface pattern, calm seas"></textarea>' +
        '</label>' +
        '<div class="ai-drift-confirm-actions">' +
          '<button type="button" class="ai-drift-search-btn" data-action="submit-search">Submit report</button>' +
          '<button type="button" class="ai-drift-search-btn ai-drift-search-btn-cancel" data-action="cancel-search">Cancel</button>' +
        '</div>' +
      '</div>';
  }

  function makeIdempotencyKey() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID();
    return 'sector-' + Date.now() + '-' + Math.random().toString(36).slice(2);
  }

  function submitSectorReport() {
    if (!sectorDraw.bounds || !currentDriftPayload || !currentDriftPayload.incident) return;
    var incidentId = currentDriftPayload.incident.id;
    var runNumber = currentDriftPayload.run_number;
    var methodSelect = document.getElementById('ai-search-method');
    var notesEl = document.getElementById('ai-search-notes');
    var submitBtn = document.querySelector('#ai-drift-search [data-action="submit-search"]');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Submitting…'; }

    var body = {
      run_number: runNumber,
      south: sectorDraw.bounds.south,
      west: sectorDraw.bounds.west,
      north: sectorDraw.bounds.north,
      east: sectorDraw.bounds.east,
      method: methodSelect ? methodSelect.value : 'moderate',
      idempotency_key: makeIdempotencyKey()
    };
    var notes = notesEl && notesEl.value.trim();
    if (notes) body.notes = notes;

    authFetch('/api/ai/drift/incident/' + encodeURIComponent(incidentId) + '/searched', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (res) {
      if (!res.ok) return res.json().catch(function () { return {}; }).then(function (err) {
        throw new Error(err.detail || ('HTTP ' + res.status));
      });
      return res.json();
    }).then(function () {
      showToast('Search recorded', 'The posterior and next-area recommendation have been updated.', false);
      cancelSectorDraw();
      loadDriftIncidentDetail(incidentId);
    }).catch(function (err) {
      showToast('Search report failed', err.message, true);
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Submit report'; }
    });
  }

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-action]');
    if (!button) return;
    var container = button.closest('#ai-drift-search');
    if (!container) return;
    var action = button.getAttribute('data-action');
    if (action === 'start-search') startSectorDraw();
    else if (action === 'cancel-search') cancelSectorDraw();
    else if (action === 'submit-search') submitSectorReport();
  });

  function renderDriftIncidentList(items) {
    var select = document.getElementById('ai-drift-select');
    if (!select) return;
    select.innerHTML = '';
    if (!items || !items.length) {
      select.innerHTML = '<option value="">No incidents available</option>';
      var emptyMeta = document.getElementById('ai-drift-meta');
      if (emptyMeta) emptyMeta.textContent = 'No drift incidents were returned by the backend.';
      clearAiDriftLayers();
      return;
    }

    items.forEach(function (item, index) {
      var option = document.createElement('option');
      option.value = String(item.id);
      option.textContent = 'Incident #' + item.id + ' · ' + item.vessel_id + ' · ' + (item.abnormal_reason || 'unknown');
      if (index === 0) option.selected = true;
      select.appendChild(option);
    });
  }

  function anomalyRows(payload) {
    if (Array.isArray(payload)) return payload;
    if (!payload || typeof payload !== 'object') return [];
    return payload.cases || payload.rows || payload.events || payload.items || [];
  }

  let lastRiskMonitoring = 'active';
  let lastRiskMonitoringReason = null;

  function renderRiskFeed(rows, freshness, monitoring, monitoringReason) {
    var list = document.getElementById('ai-risk-list');
    var count = document.getElementById('ai-risk-count');
    if (!list) return;
    if (monitoring === 'unavailable') {
      list.innerHTML = '<div class="ai-empty-state ai-unavailable-state">Not monitoring - no live contact source</div>';
      list.title = monitoringReason || '';
      if (count) count.textContent = '--';
      return;
    }
    if (rows === null || (freshness === 'offline' && (!rows || !rows.length))) {
      list.innerHTML = '<div class="ai-empty-state ai-unavailable-state">Vessel risk feed unavailable &middot; unable to reach the anomaly service.</div>';
      if (count) count.textContent = '--';
      return;
    }
    if (freshness === 'stale' && (!rows || !rows.length)) {
      list.innerHTML = '<div class="ai-empty-state ai-unavailable-state">Vessel risk feed is stale &middot; unable to refresh anomaly service.</div>';
      if (count) count.textContent = '--';
      return;
    }
    if (!rows || !rows.length) {
      list.innerHTML = '<div class="ai-empty-state">No active vessel risk rows available.</div>';
      if (count) count.textContent = '0';
      return;
    }

    var sorted = rows.slice().sort(function (a, b) {
      var diff = aiRiskPriority(a.status) - aiRiskPriority(b.status);
      if (diff !== 0) return diff;
      return (b.score || 0) - (a.score || 0);
    });

    if (count) count.textContent = String(sorted.length);

    var rowsHtml = sorted.map(function (row, index) {
      var score = typeof row.score === 'number' ? row.score.toFixed(2) : String(row.score || '--');
      var lastSeen = row.last_contact_at ? new Date(row.last_contact_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '--';
      var expectedBuoy = row.expected_next_buoy_id || 'n/a';
      var statusLabel = row.status === 'check_needed' ? 'CHECK NEEDED' : (row.status || 'normal').toUpperCase();
      var factors = Array.isArray(row.factors) ? row.factors : [];
      return '' +
        '<details class="ai-risk-item"' + (index === 0 ? ' open' : '') + '>' +
          '<summary>' +
            '<div class="ai-risk-main">' +
              '<div class="ai-risk-title">' + escapeHtml(row.vessel_id) + ' · Trip ' + escapeHtml(row.trip_id) + '</div>' +
              '<div class="ai-risk-meta">Expected buoy ' + escapeHtml(expectedBuoy) + ' · Last contact ' + escapeHtml(lastSeen) + '</div>' +
            '</div>' +
            '<div class="ai-risk-score">' + score + '<span class="ai-risk-status ' + aiStatusClass(row.status) + '">' + statusLabel + '</span></div>' +
          '</summary>' +
          '<div class="ai-risk-details">' +
            '<div class="ai-factor-list">' + factors.map(function (factor) {
              return '<div class="ai-factor-row">' +
                '<div class="ai-factor-name">' + escapeHtml(factor.name || 'factor') + '</div>' +
                '<div class="ai-factor-value">' + Number(factor.contribution || 0).toFixed(3) + '</div>' +
                '<div class="ai-factor-explainer">' + escapeHtml(factor.explanation || '') + '</div>' +
              '</div>';
            }).join('') + '</div>' +
          '</div>' +
        '</details>';
    }).join('');

    if (freshness === 'stale' || freshness === 'offline') {
      var notice = '<div class="ai-risk-stale-notice" style="padding:6px 8px;margin-bottom:6px;background:rgba(239,68,68,0.1);border-left:3px solid #ef4444;font-size:11px;color:var(--text-secondary);">' +
        '<span class="' + (freshness === 'offline' ? 'alert-demo-badge' : 'alert-unknown-badge') + '">FEED ' + (freshness === 'offline' ? 'OFFLINE' : 'STALE') + '</span> ' +
        'Vessel risk feed unavailable &middot; showing last-known status' +
      '</div>';
      rowsHtml = notice + rowsHtml;
    }
    list.innerHTML = rowsHtml;
  }

  function renderSquallChart(traceSeries) {
    var chart = document.getElementById('ai-trace-chart');
    var legend = document.getElementById('ai-trace-legend');
    if (!chart || !legend) return;
    if (!traceSeries || !traceSeries.length) {
      legend.innerHTML = '';
      chart.innerHTML = '<div class="ai-empty-state">Pressure trace unavailable.</div>';
      return;
    }

    var minPressure = Infinity;
    var maxPressure = -Infinity;
    var maxPoints = 0;
    traceSeries.forEach(function (series) {
      series.points.forEach(function (point) {
        minPressure = Math.min(minPressure, point.pressure_hpa);
        maxPressure = Math.max(maxPressure, point.pressure_hpa);
      });
      maxPoints = Math.max(maxPoints, series.points.length);
    });
    if (!isFinite(minPressure) || !isFinite(maxPressure) || maxPoints < 2) {
      legend.innerHTML = '';
      chart.innerHTML = '<div class="ai-empty-state">Pressure trace unavailable.</div>';
      return;
    }
    var pad = Math.max(0.8, (maxPressure - minPressure) * 0.2);
    minPressure -= pad;
    maxPressure += pad;

    var width = 320;
    var height = 120;
    var innerWidth = 282;
    var innerHeight = 78;
    var left = 20;
    var top = 16;

    function projectX(index, total) {
      return left + (total <= 1 ? innerWidth / 2 : (index / (total - 1)) * innerWidth);
    }

    function projectY(value) {
      return top + (maxPressure - value) / (maxPressure - minPressure) * innerHeight;
    }

    var svg = [
      '<svg viewBox="0 0 ' + width + ' ' + height + '" role="img" aria-label="Pressure trace chart">',
      '<line class="ai-trace-axis" x1="20" y1="16" x2="20" y2="94"></line>',
      '<line class="ai-trace-axis" x1="20" y1="94" x2="302" y2="94"></line>'
    ];

    var ticks = [minPressure, (minPressure + maxPressure) / 2, maxPressure];
    ticks.forEach(function (tick) {
      var y = projectY(tick);
      svg.push('<line class="ai-trace-axis" x1="20" y1="' + y.toFixed(1) + '" x2="302" y2="' + y.toFixed(1) + '" stroke-dasharray="3 4"></line>');
      svg.push('<text x="6" y="' + (y + 3).toFixed(1) + '" fill="currentColor" font-size="9">' + tick.toFixed(1) + '</text>');
    });

    traceSeries.forEach(function (series, seriesIndex) {
      var color = series.color;
      var points = series.points;
      var path = points.map(function (point, index) {
        return (index === 0 ? 'M' : 'L') + projectX(index, points.length).toFixed(1) + ',' + projectY(point.pressure_hpa).toFixed(1);
      }).join(' ');
      svg.push('<path class="ai-trace-line" d="' + path + '" stroke="' + color + '"></path>');
      svg.push('<circle cx="' + projectX(points.length - 1, points.length).toFixed(1) + '" cy="' + projectY(points[points.length - 1].pressure_hpa).toFixed(1) + '" r="2.8" fill="' + color + '"></circle>');
      if (seriesIndex === 0) {
        svg.push('<text x="24" y="10" fill="currentColor" font-size="9">hPa</text>');
      }
    });

    svg.push('</svg>');
    chart.innerHTML = svg.join('');

    legend.innerHTML = traceSeries.map(function (series) {
      return '<div class="ai-trace-legend-item"><span class="ai-trace-swatch" style="background:' + series.color + '"></span><span>' + escapeHtml(series.label) + '</span></div>';
    }).join('');
    updateSquallLegendVisibility();
  }

  function updateSquallLegendVisibility() {
    var legend = document.getElementById('ai-trace-legend');
    if (!legend) return;
    var hasContent = legend.children.length > 0;
    legend.style.display = hasContent ? '' : 'none';
  }

  function renderSquallWatch(payload, traceSeries, options) {
    var opts = options || {};
    var summary = document.getElementById('ai-squall-summary');
    var statusHost = document.getElementById('ai-squall-status');
    if (!summary) return;

    var p = payload || {};
    var detections = Array.isArray(p.detections) ? p.detections : [];
    if (statusHost) statusHost.innerHTML = typeof ns.squallStatusHtml === 'function' ? ns.squallStatusHtml(p) : '';
    updateSquallBanner(p);

    // `unknown` is the neutral insufficient-data state (docs/39 Phase 2/3) -
    // deliberately distinct from "no active detections": an alarm that
    // cannot be evaluated must never look the same as "all clear".
    if (p.level === 'unknown') {
      clearAiSquallLayers();
      summary.innerHTML = '<div class="ai-empty-state">Squall status cannot be confirmed right now.</div>';
      renderSquallChart([]);
      updateAiMapKey();
      return;
    }

    if (!detections.length) {
      clearAiSquallLayers();
      summary.innerHTML = '<div class="ai-empty-state">No active squall detections at the moment.</div>';
      renderSquallChart([]);
      updateAiMapKey();
      return;
    }

    var detection = detections[0];
    var arrival = Array.isArray(detection.arrival_by_buoy) ? detection.arrival_by_buoy : [];
    var asOf = detection.as_of ? new Date(detection.as_of).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '--';
    summary.innerHTML =
      '<div class="ai-squall-meta-row"><span>Probability</span><strong>' + (Number(detection.probability || 0) * 100).toFixed(0) + '%</strong></div>' +
      '<div class="ai-squall-meta-row"><span>Confidence</span><strong>' + (Number(detection.confidence || 0) * 100).toFixed(0) + '%</strong></div>' +
      '<div class="ai-squall-meta-row"><span>Bearing</span><strong>' + Number((detection.propagation && detection.propagation.bearing_deg) || 0).toFixed(0) + '°</strong></div>' +
      '<div class="ai-squall-meta-row"><span>As of</span><strong>' + ns.escapeHtml(asOf) + '</strong></div>' +
      '<div class="ai-squall-meta-row"><span>Arrival window</span><strong>' + (arrival.length ? ns.escapeHtml(String(arrival[0].arrival_minutes)) + ' min first arrival' : 'n/a') + '</strong></div>';

    renderSquallChart(traceSeries);
    updateAiMapKey();

    if (opts.freshnessOnly) {
      return;
    }

    clearAiSquallLayers();

    var polygon = detection.affected_polygon;
    if (polygon && polygon.geometry) {
      L.geoJSON(polygon, {
        pane: 'aiSquallPane',
        style: function () {
          return {
            color: aiColors.squall,
            weight: 3,
            fillColor: aiColors.squall,
            fillOpacity: 0.10,
            dashArray: '6 6'
          };
        },
        onEachFeature: function (feat, lyr) {
          lyr.bindTooltip('Squall watch polygon', {
            sticky: true,
            direction: 'center',
            className: 'drift-incident-label'
          });
        }
      }).addTo(aiSquallLayer);
    }

    var bounds = aiSquallLayer.getBounds();
    if (!sectorDraw.active && !sectorDraw.bounds && !aiContoursLayer.getLayers().length && bounds.isValid()) {
      map.fitBounds(bounds.pad(0.15), { animate: true, duration: 0.9, maxZoom: 14 });
    }
  }

  function loadDriftIncidentDetail(incidentId) {
    if (!incidentId) {
      clearAiDriftLayers();
      return Promise.resolve();
    }
    return aiFetchJson('/api/ai/drift/incident/' + encodeURIComponent(incidentId) + '?forecast_hours=24')
      .then(function (payload) {
        renderDriftContours(payload);
        if (payload && payload.clock_suspect) {
          var metaEl = document.getElementById('ai-drift-meta');
          if (metaEl) metaEl.innerHTML += '<br><span class="ai-clock-suspect">Client clock looked inaccurate; this estimate uses server time.</span>';
        }
      })
      .catch(function (err) {
        console.warn('[AqOne] Drift incident load failed:', err.message);
        var metaEl = document.getElementById('ai-drift-meta');
        if (metaEl) metaEl.textContent = 'Unable to load the drift map right now.';
        clearAiDriftLayers();
      });
  }

  let lastRiskSuccessMs = null;
  let lastKnownRiskRows = null;
  let lastSquallSuccessMs = null;
  let lastKnownSquallPayload = null;
  let lastKnownSquallTrace = [];

  function loadSquallTrace(payload) {
    lastSquallSuccessMs = Date.now();
    lastKnownSquallPayload = payload;
    var detection = payload && payload.detections && payload.detections[0];
    var arrival = detection && detection.arrival_by_buoy ? detection.arrival_by_buoy.slice(0, 3) : [];
    if (!arrival.length) {
      lastKnownSquallTrace = [];
      renderSquallWatch(payload, []);
      return Promise.resolve();
    }

    return Promise.all(arrival.map(function (item, index) {
      return aiFetchJson('/api/ai/squall/buoy/' + encodeURIComponent(item.buoy_id))
        .then(function (detail) {
          return {
            label: detail.buoy.id,
            color: ['#2563eb', '#ef4444', '#f59e0b'][index % 3],
            points: detail.trace || []
          };
        })
        .catch(function () {
          return {
            label: item.buoy_id,
            color: ['#2563eb', '#ef4444', '#f59e0b'][index % 3],
            points: []
          };
        });
    })).then(function (series) {
      lastKnownSquallTrace = series.filter(function (item) { return item.points.length; });
      renderSquallWatch(payload, lastKnownSquallTrace);
    });
  }

  function updateAIFreshness() {
    var classify = ns.classifyFreshness || (window.AqOneDashboardUtils && window.AqOneDashboardUtils.classifyFreshness);
    var now = Date.now();

    var riskFreshness = typeof classify === 'function' ? classify(lastRiskSuccessMs, now, {
      pollIntervalMs: 60000,
      staleAfterMs: 180000,
      offlineAfterMs: 360000
    }) : 'offline';
    if (riskFreshness === 'stale' || riskFreshness === 'offline') {
      if (!lastKnownRiskRows || !lastKnownRiskRows.length) {
        renderRiskFeed(null, riskFreshness, lastRiskMonitoring, lastRiskMonitoringReason);
      } else {
        renderRiskFeed(lastKnownRiskRows, riskFreshness, lastRiskMonitoring, lastRiskMonitoringReason);
      }
    }

    var squallFreshness = typeof classify === 'function' ? classify(lastSquallSuccessMs, now, {
      pollIntervalMs: 60000,
      staleAfterMs: 180000,
      offlineAfterMs: 360000
    }) : 'offline';
    if (squallFreshness === 'stale' || squallFreshness === 'offline') {
      if (!lastKnownSquallPayload || !lastKnownSquallPayload.detections || !lastKnownSquallPayload.detections.length) {
        renderSquallWatch({
          level: 'unknown',
          detections: [],
          freshness: squallFreshness,
          status_reason: 'Squall service unavailable · connection lost'
        }, [], { freshnessOnly: true });
        updateSquallLegendVisibility();
      } else {
        var elapsedSec = Math.max(0, Math.floor((now - (lastSquallSuccessMs || now)) / 1000));
        var agedPayload = Object.assign({}, lastKnownSquallPayload, {
          data_age_seconds: (lastKnownSquallPayload.data_age_seconds || 0) + elapsedSec,
          freshness: squallFreshness,
          status_reason: (lastKnownSquallPayload.status_reason ? lastKnownSquallPayload.status_reason + ' · ' : '') + (squallFreshness === 'offline' ? 'Service offline (showing last-known detection)' : 'Feed stale (showing last-known detection)')
        });
        renderSquallWatch(agedPayload, lastKnownSquallTrace || [], { freshnessOnly: true });
      }
    }
  }

  function pollAIOperations() {
    updateAIFreshness();

    aiFetchJson('/api/ai/anomaly/active')
      .then(function (payload) {
        lastRiskSuccessMs = Date.now();
        lastKnownRiskRows = anomalyRows(payload);
        lastRiskMonitoring = payload && payload.monitoring || 'active';
        lastRiskMonitoringReason = payload && payload.monitoring_reason || null;
        renderRiskFeed(lastKnownRiskRows, 'live', lastRiskMonitoring, lastRiskMonitoringReason);
      })
      .catch(function (err) {
        console.warn('[AqOne] Vessel risk poll failed, checking freshness:', err.message);
        updateAIFreshness();
      });

    // A transient poll failure leaves the squall panel with its last-known
    // state if a real detection existed, but advances its age and labels it;
    // expired calm data must not read as current lower-risk guidance.
    aiFetchJson('/api/ai/squall/current')
      .then(loadSquallTrace)
      .then(updateSquallLegendVisibility)
      .catch(function (err) {
        console.warn('[AqOne] Squall poll failed, checking freshness:', err.message);
        updateAIFreshness();
      });

    // Never yank the map out from under a responder mid-draw or
    // mid-confirmation (docs/40 Phase 4 item 2).
    if (sectorDraw.active || sectorDraw.bounds) return;
    var currentSelect = document.getElementById('ai-drift-select');
    if (currentSelect && currentSelect.value) loadDriftIncidentDetail(currentSelect.value);
  }

  function initAIOperations() {
    var driftSelect = document.getElementById('ai-drift-select');
    var driftMeta = document.getElementById('ai-drift-meta');
    var aiRiskList = document.getElementById('ai-risk-list');
    var aiSquallSummary = document.getElementById('ai-squall-summary');

    if (driftMeta) driftMeta.textContent = 'Fetching live incidents...';
    if (aiRiskList) aiRiskList.innerHTML = '<div class="ai-empty-state">Loading vessel risk feed...</div>';
    if (aiSquallSummary) aiSquallSummary.innerHTML = '<div class="ai-empty-state">Loading squall watch...</div>';

    Promise.allSettled([
      aiFetchJson('/api/ai/anomaly/active'),
      aiFetchJson('/api/ai/drift/incidents'),
      aiFetchJson('/api/ai/squall/current')
    ]).then(function (results) {
      var riskResult = results[0];
      var incidentsResult = results[1];
      var squallResult = results[2];

      if (riskResult.status === 'fulfilled') {
        lastRiskSuccessMs = Date.now();
        lastKnownRiskRows = anomalyRows(riskResult.value);
        lastRiskMonitoring = riskResult.value && riskResult.value.monitoring || 'active';
        lastRiskMonitoringReason = riskResult.value && riskResult.value.monitoring_reason || null;
        renderRiskFeed(lastKnownRiskRows, 'live', lastRiskMonitoring, lastRiskMonitoringReason);
      } else {
        renderRiskFeed(null, 'offline');
      }

      if (incidentsResult.status === 'fulfilled') {
        renderDriftIncidentList(incidentsResult.value || []);
      } else {
        renderDriftIncidentList([]);
      }

      var selectedIncidentId = driftSelect && driftSelect.value;
      var incidentPromise = selectedIncidentId ? loadDriftIncidentDetail(selectedIncidentId) : Promise.resolve();
      if (!selectedIncidentId && driftSelect && driftSelect.options.length) {
        selectedIncidentId = driftSelect.options[0].value;
        driftSelect.value = selectedIncidentId;
        incidentPromise = loadDriftIncidentDetail(selectedIncidentId);
      }

      if (driftSelect) {
        driftSelect.addEventListener('change', function () {
          loadDriftIncidentDetail(driftSelect.value);
        });
      }

      if (squallResult.status === 'fulfilled') {
        return loadSquallTrace(squallResult.value || { detections: [] }).then(updateSquallLegendVisibility);
      }
      // Never seen any data yet - an honest "can't confirm" beats leaving
      // the "Loading..." placeholder up forever, but it must not claim
      // "no active detections" either (docs/39 Phase 3 item 4).
      renderSquallWatch({ level: 'unknown', detections: [], status_reason: 'unable to reach the squall service' }, []);
      updateSquallLegendVisibility();
      return incidentPromise;
    }).catch(function (err) {
      console.warn('[AqOne] AI init failed:', err && err.message);
      renderRiskFeed(null, 'offline');
      renderDriftIncidentList([]);
      clearAiDriftLayers();
      renderSquallWatch({ level: 'unknown', detections: [], status_reason: 'unable to reach the squall service' }, []);
      updateSquallLegendVisibility();
    });

    if (aiRefreshTimer) clearInterval(aiRefreshTimer);
    aiRefreshTimer = setInterval(pollAIOperations, 60000);
    if (aiRefreshTimer && typeof aiRefreshTimer.unref === 'function') {
      aiRefreshTimer.unref();
    }
    if (aiFreshnessTimer) clearInterval(aiFreshnessTimer);
    aiFreshnessTimer = setInterval(updateAIFreshness, 15000);
    if (aiFreshnessTimer && typeof aiFreshnessTimer.unref === 'function') {
      aiFreshnessTimer.unref();
    }
  }

  initAIOperations();


  // ===== EXIT LOADING =====
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('load', function () {
      setTimeout(function () {
        var overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.add('hidden');
      }, 800);
    });
  }

  ns.aiContoursLayer = aiContoursLayer;
  ns.aiSquallLayer = aiSquallLayer;
  ns.aiDrawLayer = aiDrawLayer;
  ns.squallLayer = aiSquallLayer;
  ns.driftLayer = aiContoursLayer;
  ns.escapeHtml = escapeHtml;
  ns._escHtml = escapeHtml;
  ns.renderRiskFeed = renderRiskFeed;
  ns.renderSquallWatch = renderSquallWatch;
  ns.pollAIOperations = pollAIOperations;
  ns.sectorDraw = sectorDraw;

})(window.AqOneDashboard = window.AqOneDashboard || {});
