(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var escapeHtml = ns.escapeHtml;
  var classifyFreshness = ns.classifyFreshness;
  var freshnessLabel = ns.freshnessLabel;
  var authFetch = ns.authFetch;
  var map = ns.map;
  var showToast = ns.showToast;
  var liveAlerts = ns.liveAlerts;

  // ===== LIVE SOS FEED =====
  //
  // The dashboard previously rendered only the hardcoded demo rows above, so a
  // real distress call could sit in the database while the screen showed three
  // fictional vessels. This is the path that makes a pressed button visible.
  //
  // Polling rather than SSE: /api/sos/active already exists and needs no
  // reconnect logic. Three seconds keeps the LGU screen feeling live, and a
  // missed poll self-heals on the next tick.
  const LIVE_SOS_POLL_MS = 3000;
  const liveSosLayer = L.layerGroup().addTo(map);
  const liveSosMarkers = {};
  let liveSosFirstLoad = true;
  let knownSosIds = Object.create(null);


  // ===== FEED FRESHNESS (LIVE / STALE / OFFLINE) =====
  //
  // Previously the "LIVE" badge in the header was static markup - it read
  // LIVE even while loadActiveSos() had been failing silently, and the "Last
  // updated" banner text was an independent 30-second counter with no
  // connection to whether a poll had actually succeeded. Both were fake
  // operational state (Hard Reset rule 4). This tracks the one fact that
  // matters - when a poll last actually succeeded - and both indicators are
  // now driven from it.
  let lastSosSuccessMs = null;
  const syncStatusEl = document.getElementById('sync-status');
  const syncTextEl = document.getElementById('sync-text');
  const bannerTimeEl = document.querySelector('.banner-time');
  const statsFeedStatusEl = document.getElementById('stats-feed-status');

  function updateSyncStatus() {
    const state = classifyFreshness(lastSosSuccessMs, Date.now(), {
      pollIntervalMs: LIVE_SOS_POLL_MS
    });

    if (syncStatusEl) {
      syncStatusEl.classList.toggle('is-stale', state === 'stale');
      syncStatusEl.classList.toggle('is-offline', state === 'offline');
    }
    if (syncTextEl) {
      syncTextEl.textContent = freshnessLabel(state);
    }
    if (statsFeedStatusEl) {
      statsFeedStatusEl.textContent = freshnessLabel(state);
      statsFeedStatusEl.className = 'metric-status metric-status-feed metric-status-' + state;
    }
    if (syncStatusEl) {
      syncStatusEl.title = lastSosSuccessMs == null
        ? 'The live SOS feed has not loaded successfully yet'
        : 'Live SOS feed last refreshed ' + Math.max(0, Math.round((Date.now() - lastSosSuccessMs) / 1000)) + 's ago';
    }
    if (bannerTimeEl) {
      bannerTimeEl.textContent = lastSosSuccessMs == null
        ? 'never'
        : Math.max(0, Math.round((Date.now() - lastSosSuccessMs) / 1000)) + 's ago';
    }
  }

  updateSyncStatus();
  // Ticks independently of the poll interval so STALE/OFFLINE appears
  // promptly even between polls, instead of only updating when a poll
  // happens to run.
  setInterval(updateSyncStatus, 1000);

  function liveSosIcon() {
    return L.divIcon({
      className: 'live-sos-marker',
      html: '<span class="live-sos-pulse"></span><span class="live-sos-core">SOS</span>',
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });
  }

  function relativeTime(iso) {
    const then = new Date(iso).getTime();
    if (!isFinite(then)) return 'unknown time';
    const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
    if (secs < 60) return secs + ' seconds ago';
    const mins = Math.floor(secs / 60);
    if (mins < 60) return mins + (mins === 1 ? ' minute ago' : ' minutes ago');
    const hrs = Math.floor(mins / 60);
    return hrs + (hrs === 1 ? ' hour ' : ' hours ') + (mins % 60) + ' minutes ago';
  }

  // How the SOS reached us, stated plainly. The dispatcher needs to know
  // whether the mesh carried this or whether the handset had signal, because
  // it changes what they can assume about the vessel's situation.
  function deliveryPath(ev) {
    const paths = [];
    if (ev.delivered_via_buoy) paths.push('LoRa mesh' + (ev.buoy_id ? ' via ' + ev.buoy_id : ''));
    if (ev.delivered_direct) paths.push('direct internet');
    if (!paths.length) return 'Path unrecorded';
    return paths.join(' + ');
  }

  function sosPosition(ev) {
    if (typeof ev.latitude !== 'number' || typeof ev.longitude !== 'number') {
      return 'No GPS fix reported';
    }
    return ev.latitude.toFixed(4) + '° N, ' + ev.longitude.toFixed(4) + '° E';
  }

  function liveAlertFromEvent(ev) {
    const boat = ev.boat || ev.vessel_id || 'Unidentified vessel';
    const skipperName = ev.skipper_name || null;
    const hasFix = typeof ev.latitude === 'number' && typeof ev.longitude === 'number';
    const provenance = ev.is_synthetic === false ? 'real' : (ev.is_synthetic === true ? 'synthetic' : 'unknown');
    const isRealLive = provenance === 'real';
    const isSynthetic = provenance === 'synthetic';
    const alert = {
      isLive: isRealLive,
      isSynthetic: isSynthetic,
      provenance: provenance,
      sosEventId: ev.id,
      type: 'sos',
      desc: 'SOS — ' + boat + (ev.note ? ' — “' + ev.note + '”' : ''),
      time: relativeTime(ev.created_at),
      lat: hasFix ? Number(ev.latitude.toFixed(4)) : null,
      lng: hasFix ? Number(ev.longitude.toFixed(4)) : null,
      status: ev.acknowledged_at ? 'acknowledged' : 'active',
      vesselId: ev.vessel_id || null,
      // The declared owner identity from POST /api/vessel-profile, carried on
      // the event itself so the received-call row/toast can name the person
      // who pressed the button, not just the boat id.
      owner: skipperName || boat,
      phone: ev.phone || null,
      confidence: null,
      stage: 'DISTRESS CALL — ' + deliveryPath(ev),
      // Read by dashboard-vessels-alerts.js's [data-eta-at] countdown span.
      etaAt: ev.eta_at || null,
      fisherReply: ev.fisher_reply || null
    };
    alert.drawerData = {
      alertType: 'sos',
      headerText: provenance === 'real'
        ? 'SOS — DISTRESS CALL RECEIVED'
        : (provenance === 'synthetic' ? 'DEMO SOS — SIMULATED DISTRESS CALL' : 'SOS — DISTRESS CALL (PROVENANCE UNKNOWN)'),
      sosEventId: ev.id,
      isSynthetic: isSynthetic,
      provenance: provenance,
      vesselId: ev.vessel_id || 'Unknown',
      // The declared owner identity (POST /api/vessel-profile): person first,
      // boat as fallback until the profile arrives, so the drawer tells the
      // dispatcher who raised the call - not just which boat id did.
      skipperName: ev.skipper_name || null,
      owner: ev.skipper_name || boat || null,
      boat: boat,
      license: (ev.license_type && ev.license_type !== 'none')
        ? (ev.license_number ? ev.license_type + ' ' + ev.license_number : ev.license_type)
        : (ev.license_number || null),
      phone: ev.phone || null,
      position: sosPosition(ev),
      lat: alert.lat,
      lng: alert.lng,
      buoy: ev.buoy_id || 'Not relayed by a buoy',
      coverage: deliveryPath(ev) + (ev.trust_tier ? ' · trust tier ' + ev.trust_tier : ''),
      confidence: null,
      stage: 'DISTRESS CALL — human pressed the button',
      nextContact: ev.note || 'No message attached',
      timerBaseline: Math.max(0, Math.floor((Date.now() - new Date(ev.created_at).getTime()) / 1000)),
      // The responder loop (docs/13_RESPONDER_LOOP.md): what the dispatcher
      // recorded, and how the fisher answered it. acknowledgedAt gates
      // whether the drawer's responder section renders at all.
      acknowledgedAt: ev.acknowledged_at || null,
      etaAt: ev.eta_at || null,
      responderStatus: ev.responder_status || null,
      responderStatusLabel: ev.responder_status_label || null,
      responderNote: ev.responder_note || null,
      fisherReply: ev.fisher_reply || null
    };
    return alert;
  }

  function syncLiveSosMarkers() {
    const seen = Object.create(null);
    liveAlerts.forEach(function (a) {
      if (a.lat == null || a.lng == null) return;
      seen[a.sosEventId] = true;
      let marker = liveSosMarkers[a.sosEventId];
      if (!marker) {
        marker = L.marker([a.lat, a.lng], { icon: liveSosIcon(), zIndexOffset: 1000 });
        // Leaflet renders tooltip content as innerHTML, not textContent - see
        // https://leafletjs.com/reference.html#tooltip. a.desc carries the
        // fisher's own note text, so it must be escaped here too.
        marker.bindTooltip(escapeHtml(a.desc), { direction: 'top', offset: [0, -14] });
        liveSosLayer.addLayer(marker);
        liveSosMarkers[a.sosEventId] = marker;
      } else {
        marker.setLatLng([a.lat, a.lng]);
      }
      marker.off('click');
      marker.on('click', function () { ns.openIncidentDrawer(a.drawerData, marker); });
    });

    // An acknowledged-but-unresolved event stays in /active (Phase 2 of
    // docs/36_MANUAL_SOS_RESPONDER_LOOP_IMPLEMENTATION_PLAN.md) so the
    // dispatcher can see the fisher's reply land on it - only a resolved
    // event actually leaves the feed, and only then must its marker go too.
    Object.keys(liveSosMarkers).forEach(function (id) {
      if (!seen[id]) {
        liveSosLayer.removeLayer(liveSosMarkers[id]);
        delete liveSosMarkers[id];
      }
    });
  }

  let activeSosReqSeq = 0;
  let lastAcceptedSosSeq = 0;

  function loadActiveSos() {
    const seq = ++activeSosReqSeq;
    return authFetch('/api/sos/active')
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || !Array.isArray(data.events)) {
          throw new Error('Malformed SOS feed payload');
        }
        const mapped = data.events.map(liveAlertFromEvent);

        // Discard responses that were superseded by a newer accepted response
        if (seq < lastAcceptedSosSeq) {
          return;
        }
        lastAcceptedSosSeq = seq;

        liveAlerts.splice(0, liveAlerts.length);
        Array.prototype.push.apply(liveAlerts, mapped);

        const events = data.events;
        // Announce genuinely new calls, but never on the first load - a
        // dispatcher opening the dashboard should not be hit with a klaxon for
        // events they already handled before the page refreshed.
        if (!liveSosFirstLoad) {
          // The klaxon mirrors the toast gating: it rings only for calls that
          // arrive while the dashboard is open, never on the first load for
          // events handled before the page refreshed. sync() then keeps it
          // ringing until every call in the feed has been acknowledged.
          if (ns.sosAlarm) ns.sosAlarm.sync(events);
          events.forEach(function (ev) {
            if (!knownSosIds[ev.id]) {
              if (ns.sosAlarm && !(ev.acknowledged_at != null || ev.status === 'acknowledged')) {
                ns.sosAlarm.start();
              }
              showToast(
                'SOS received',
                (ev.skipper_name ? ev.skipper_name + ' · ' : '') +
                  (ev.boat || ev.vessel_id || 'A vessel') + ' · ' + sosPosition(ev),
                true
              );
            }
          });
        }
        knownSosIds = Object.create(null);
        events.forEach(function (ev) { knownSosIds[ev.id] = true; });
        liveSosFirstLoad = false;

        // The one fact updateSyncStatus() needs: this poll actually
        // succeeded, right now. Everything the LIVE/STALE/OFFLINE indicator
        // shows is derived from this single timestamp.
        lastSosSuccessMs = Date.now();
        updateSyncStatus();

        syncLiveSosMarkers();
        ns.syncAlertIndicators();
        ns.renderIncidentFeed();
        // If the open drawer is one of these events, this is what surfaces a
        // fisher's STILL_IN_DANGER / SAFE_NOW reply without the dispatcher
        // having to close and reopen it.
        if (ns.refreshOpenDrawer) ns.refreshOpenDrawer();
      })
      .catch(function (err) {
        // A failed poll must not blank the list. The last known set of live
        // alerts stays on screen rather than a distress call silently
        // vanishing because one request timed out. It must, however, be
        // visible in the sync indicator - updateSyncStatus() will move to
        // STALE/OFFLINE on its own once enough time has passed without a
        // fresh lastSosSuccessMs, which this call makes immediate instead of
        // waiting up to a second for the next tick.
        if (seq < lastAcceptedSosSeq) return;
        console.warn('[AqOne] Live SOS poll failed:', err.message);
        updateSyncStatus();
      });
  }

  loadActiveSos();
  setInterval(loadActiveSos, LIVE_SOS_POLL_MS);

  ns.liveSosLayer = liveSosLayer;
  ns.liveSosMarkers = liveSosMarkers;
  ns.updateSyncStatus = updateSyncStatus;
  ns.liveAlertFromEvent = liveAlertFromEvent;
  ns.loadActiveSos = loadActiveSos;

})(window.AqOneDashboard = window.AqOneDashboard || {});
