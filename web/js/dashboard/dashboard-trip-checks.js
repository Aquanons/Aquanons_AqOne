(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var authFetch = ns.authFetch;
  var showToast = ns.showToast;
  var tripChecksListHtml = ns.tripChecksListHtml;

  // ===== TRIP CHECKS (docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md Phase 3) =====
  //
  // A separate queue from the SOS "Alerts" tab on purpose - a trip check is a
  // confidence-scored review candidate from routine buoy contact, never an
  // SOS and never an automatic dispatch. Reuses the exact fetch/poll/action
  // idiom dashboard-live-sos.js and dashboard-incidents.js already use for
  // the SOS feed, per the plan's "reuse the current fetch helpers and action
  // pattern; do not build WebSockets or a second dashboard".
  const TRIP_CHECKS_POLL_MS = 15000;

  const tripChecksListEl = document.getElementById('trip-checks-list');
  const tripChecksBadgeEl = document.getElementById('badge-tripchecks');

  let loadedOnce = false;
  let lastTripChecksSuccessMs = null;
  let lastKnownCases = null;

  function renderTripChecks(cases, freshness) {
    if (freshness === 'offline' && (!cases || cases.length === 0)) {
      if (tripChecksListEl) tripChecksListEl.innerHTML = '<div class="trip-checks-empty trip-checks-unavailable"><span class="alert-demo-badge">FEED OFFLINE</span> Trip checks queue unavailable &middot; unable to reach the anomaly detection service.</div>';
      if (tripChecksBadgeEl) tripChecksBadgeEl.textContent = '--';
      return;
    }
    if (freshness === 'stale' && (!cases || cases.length === 0)) {
      if (tripChecksListEl) tripChecksListEl.innerHTML = '<div class="trip-checks-empty trip-checks-stale"><span class="alert-demo-badge">FEED STALE</span> Trip checks feed is stale &middot; unable to verify recent trip patterns.</div>';
      if (tripChecksBadgeEl) tripChecksBadgeEl.textContent = '--';
      return;
    }

    if (cases && cases.length > 0 && (freshness === 'stale' || freshness === 'offline')) {
      var staleNotice = '<div class="trip-checks-stale-banner" style="padding:6px 8px;margin-bottom:6px;background:rgba(239,68,68,0.1);border-left:3px solid #ef4444;font-size:11px;color:var(--text-secondary);">' +
        '<span class="alert-demo-badge">FEED ' + (freshness === 'offline' ? 'OFFLINE' : 'STALE') + '</span> Showing last-known trip checks &middot; anomaly service unreachable</div>';
      if (tripChecksListEl) tripChecksListEl.innerHTML = staleNotice + tripChecksListHtml(cases);
      if (tripChecksBadgeEl) tripChecksBadgeEl.textContent = cases.length;
      return;
    }

    if (tripChecksListEl) tripChecksListEl.innerHTML = tripChecksListHtml(cases);
    if (tripChecksBadgeEl) tripChecksBadgeEl.textContent = Array.isArray(cases) ? cases.length : '--';
  }

  var TRIP_CHECK_TIMEOUT_MS = 25000;

  function updateTripChecksFreshness() {
    if (!loadedOnce) {
      renderTripChecks(null, 'offline');
      return;
    }
    var classify = ns.classifyFreshness || (window.AqOneDashboardUtils && window.AqOneDashboardUtils.classifyFreshness);
    var freshness = typeof classify === 'function' ? classify(lastTripChecksSuccessMs, Date.now(), {
      pollIntervalMs: TRIP_CHECKS_POLL_MS,
      staleAfterMs: 45000,
      offlineAfterMs: 90000
    }) : 'offline';
    if (freshness === 'stale' || freshness === 'offline') {
      renderTripChecks(lastKnownCases, freshness);
    }
  }

  function loadOpenCases() {
    updateTripChecksFreshness();

    var signal = typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
      ? AbortSignal.timeout(TRIP_CHECK_TIMEOUT_MS)
      : undefined;

    return authFetch('/api/ai/anomaly/cases/open', signal ? { signal: signal } : undefined)
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (cases) {
        loadedOnce = true;
        lastTripChecksSuccessMs = Date.now();
        lastKnownCases = Array.isArray(cases) ? cases : [];
        renderTripChecks(lastKnownCases, 'live');
      })
      .catch(function (err) {
        console.warn('[AqOne] Trip checks poll failed:', err);
        updateTripChecksFreshness();
      });
  }

  function postCaseAction(caseId, action, body) {
    return authFetch('/api/ai/anomaly/cases/' + encodeURIComponent(caseId) + '/' + action, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined
    }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    });
  }

  const ACTION_LABELS = {
    acknowledge: 'Acknowledge',
    dismiss: 'Dismiss',
    escalate: 'Escalate',
    resolve: 'Resolve'
  };

  if (tripChecksListEl) {
    tripChecksListEl.addEventListener('click', function (event) {
      const button = event.target.closest('[data-case-action]');
      if (!button || button.disabled) return;
      const action = button.getAttribute('data-case-action');
      const caseId = button.getAttribute('data-case-id');
      if (!action || !caseId) return;

      // A read, not a mutation - opens the case's authorized timeline
      // (docs/41 Phase 4) rather than POSTing to a nonexistent action route.
      if (action === 'activity') {
        if (ns.openActivityDrawer) ns.openActivityDrawer('anomaly_case', caseId, 'Anomaly Case Activity');
        return;
      }

      let body = null;
      if (action === 'dismiss' || action === 'escalate') {
        const reason = window.prompt(ACTION_LABELS[action] + ' - reason:');
        if (reason == null) return; // cancelled
        const trimmed = reason.trim();
        if (!trimmed) {
          showToast('Reason required', ACTION_LABELS[action] + ' needs a short reason.', true);
          return;
        }
        body = { reason: trimmed };
      }

      button.disabled = true;
      postCaseAction(caseId, action, body)
        // Re-poll rather than mutate locally, matching dashboard-incidents.js -
        // the server's own row, not a guessed one, and it must still be there
        // after a reload.
        .then(function () { return loadOpenCases(); })
        .catch(function (err) {
          showToast('Not delivered', 'The trip check is unchanged until this succeeds.', true);
          console.warn('[AqOne] Trip check action failed:', err);
        })
        .finally(function () {
          button.disabled = false;
        });
    });
  }

  loadOpenCases();
  setInterval(loadOpenCases, TRIP_CHECKS_POLL_MS);
  setInterval(updateTripChecksFreshness, 10000);

  ns.loadOpenCases = loadOpenCases;

})(window.AqOneDashboard = window.AqOneDashboard || {});
