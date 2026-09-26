// Pure helpers extracted from dashboard.js so they can be unit tested with
// `node --test` (see web/test/dashboard-utils.test.js) without a browser or
// a DOM. Loaded as a plain <script> in dashboard.html (attaches
// window.AqOneDashboardUtils, matching the window.AqOneDangerZonePredictor
// convention already used in this codebase) and required directly from
// Node for tests via module.exports.
//
// docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md Phase 3:
//   - escapeHtml(): server-provided SOS text (boat name, note, buoy id) must
//     never be inserted into innerHTML/tooltips/popups unescaped.
//   - classifyFreshness(): the "LIVE" indicator must be driven by the most
//     recent successful /api/sos/active refresh, not a hardcoded label.
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && typeof module.exports === 'object') {
    module.exports = factory();
  } else {
    root.AqOneDashboardUtils = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Escapes text for safe insertion into innerHTML, a Leaflet tooltip/popup,
   * or an HTML attribute value. Pure string replacement rather than the
   * DOM-textNode trick (`div.appendChild(document.createTextNode(str))`)
   * used elsewhere in dashboard.js, so this same function runs identically
   * in the browser and under plain `node --test` with no DOM shim.
   *
   * `null`/`undefined` become an empty string rather than the literal text
   * "null" - a distress call with a missing note must render as no note,
   * not as the word "null".
   */
  function escapeHtml(value) {
    if (value == null) {
      return '';
    }
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatLatLon(latitude, longitude) {
    if (typeof latitude !== 'number' || !isFinite(latitude) || typeof longitude !== 'number' || !isFinite(longitude)) {
      return 'unknown position';
    }
    return Math.abs(latitude).toFixed(4) + '° ' + (latitude < 0 ? 'S' : 'N') + ', ' +
      Math.abs(longitude).toFixed(4) + '° ' + (longitude < 0 ? 'W' : 'E');
  }

  function utf8ByteLength(value) {
    return new TextEncoder().encode(String(value)).length;
  }

  function lateLabel(pressedAt, now) {
    var elapsedHours = Math.max(0, Math.floor(((now == null ? Date.now() : now) - Date.parse(pressedAt)) / 3600000));
    if (!isFinite(elapsedHours)) return 'LATE - pressed time unknown';
    var days = Math.floor(elapsedHours / 24);
    var hours = elapsedHours % 24;
    return 'LATE - pressed ' + (days ? days + ' d ' : '') + hours + ' h ago';
  }

  function flagLabel(flag) {
    return ({
      position_on_land: 'Position on land',
      position_beyond_radio_range: 'Beyond radio range',
      position_jump: 'Position jumped over 20 km',
      many_calls_same_vessel: 'Several calls from this vessel',
      position_conflict: 'Conflicting positions'
    })[flag] || String(flag || '');
  }

  function deliveryLabel(event) {
    if (event && event.delivery_path === 'pod') return 'Relayed by pod ' + (event.pod_id || event.buoy_id || 'unknown') + ' - sender not verified';
    if (event && event.delivery_path === 'direct') return 'Direct internet';
    return 'Delivery path unknown';
  }

  /**
   * Classifies how trustworthy the live feed's "LIVE" claim currently is,
   * based only on when a poll last actually succeeded - never on whether a
   * poll is merely in flight.
   *
   * - 'live': a poll succeeded within the last `staleAfterMs`.
   * - 'stale': the feed has succeeded before, but not recently enough to
   *   trust - the mesh or the browser tab may have hung.
   * - 'offline': either no poll has ever succeeded, or it has been so long
   *   that the on-screen data must be treated as unknown, not "live".
   *
   * Defaults follow the plan's polling cadence
   * (LIVE_SOS_POLL_MS = 3000 in dashboard.js): stale after 3 missed polls,
   * offline after 10.
   */
  function classifyFreshness(lastSuccessMs, nowMs, options) {
    var opts = options || {};
    var pollIntervalMs = opts.pollIntervalMs || 3000;
    var staleAfterMs = opts.staleAfterMs || pollIntervalMs * 3;
    var offlineAfterMs = opts.offlineAfterMs || pollIntervalMs * 10;

    if (lastSuccessMs == null || !isFinite(lastSuccessMs)) {
      return 'offline';
    }
    var age = nowMs - lastSuccessMs;
    if (age < 0) {
      // Clock skew or a bad timestamp - treat as freshly successful rather
      // than crashing the indicator into a negative age.
      return 'live';
    }
    if (age <= staleAfterMs) {
      return 'live';
    }
    if (age <= offlineAfterMs) {
      return 'stale';
    }
    return 'offline';
  }

  /**
   * Human-facing copy for each freshness state, so dashboard.js and the
   * tests share one source of truth for the wording instead of the label
   * drifting from the classification logic.
   */
  var FRESHNESS_LABELS = {
    live: 'LIVE',
    stale: 'STALE',
    offline: 'OFFLINE'
  };

  function freshnessLabel(state) {
    return FRESHNESS_LABELS[state] || FRESHNESS_LABELS.offline;
  }

  /**
   * The badge text/CSS class for one incident-feed row, so a scripted
   * sample row (web/js/dashboard.js `alertData`) can never look like a real
   * distress call (`isLive: true`, sourced from `/api/sos/active`) and vice
   * versa. Pulled out of the render template into a pure function so the
   * live/demo distinction itself - not just the escaping around it - is
   * covered by a test, per Phase 3 of
   * docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md ("synthetic/demo
   * badges").
   */
  function alertBadge(isLive) {
    if (isLive === 'unknown') {
      return { text: 'UNKNOWN', cssClass: 'alert-unknown-badge' };
    }
    if (isLive === true || isLive === 'real' || isLive === 'live') {
      return { text: 'LIVE', cssClass: 'alert-live-badge' };
    }
    return { text: 'DEMO', cssClass: 'alert-demo-badge' };
  }

  function registrationBadge(licenseType) {
    var registered = typeof licenseType === 'string' && licenseType !== '' && licenseType !== 'none';
    return registered
      ? { text: 'Registered Boat', cssClass: 'reg-badge-registered', registered: true }
      : { text: 'Unregistered Boat', cssClass: 'reg-badge-unregistered', registered: false };
  }

  function registrationBadgeHtml(licenseType) {
    var badge = registrationBadge(licenseType);
    var detail = badge.registered ? ' · ' + escapeHtml(String(licenseType).toUpperCase()) : '';
    return '<span class="reg-badge ' + badge.cssClass + '">' + badge.text + detail + '</span>';
  }

  /**
   * Live countdown text for an acknowledged SOS's ETA, honest about an
   * expired one. See docs/13_RESPONDER_LOOP.md: a countdown that reaches
   * zero and stops reads as "nobody is coming", so this never returns
   * `00:00` or a negative number - once `etaAt` has passed it says the
   * rescue is delayed instead.
   *
   * `nowMs` defaults to `Date.now()` but is an explicit parameter so this
   * can be tested without faking the system clock.
   */
  function formatEta(etaAt, nowMs) {
    if (!etaAt) return '';
    var now = nowMs == null ? Date.now() : nowMs;
    var remainingMs = new Date(etaAt).getTime() - now;
    if (!isFinite(remainingMs) || remainingMs <= 0) return 'delayed — still en route';
    var mins = Math.floor(remainingMs / 60000);
    var secs = Math.floor((remainingMs % 60000) / 1000);
    return 'ETA ' + mins + ':' + String(secs).padStart(2, '0');
  }

  /**
   * Builds the incident drawer's responder-status block as an HTML string.
   * Pure - the DOM write (`el.innerHTML = ...`) happens in
   * dashboard-incidents.js, so this runs identically under `node --test`
   * with no DOM.
   *
   * `responderNote` is dispatcher-entered free text
   * (docs/13_RESPONDER_LOOP.md's `responder_note`) and must never reach
   * innerHTML unescaped - see docs/21_WEEK1_CONTRACT_FIXTURES.md's dashboard
   * honesty findings for what an unescaped field already did to this
   * dashboard once.
   */
  function responderStatusHtml(data, nowMs) {
    var d = data || {};
    if (!d.acknowledgedAt) return '';
    var rows = [];
    rows.push(
      '<div class="sos-detail-row"><span class="sos-detail-label">Responder Status</span>' +
      '<span class="sos-detail-value">' + escapeHtml(d.responderStatusLabel || 'Acknowledged') + '</span></div>'
    );
    var etaText = formatEta(d.etaAt, nowMs);
    rows.push(
      '<div class="sos-detail-row"><span class="sos-detail-label">ETA</span>' +
      '<span class="sos-detail-value' + (etaText.indexOf('delayed') === 0 ? ' is-overdue' : '') + '"' +
      (d.etaAt ? ' data-eta-at="' + escapeHtml(d.etaAt) + '"' : '') + '>' +
      escapeHtml(etaText || 'No ETA given') + '</span></div>'
    );
    if (d.responderNote) {
      rows.push(
        '<div class="sos-detail-row"><span class="sos-detail-label">Responder Note</span>' +
        '<span class="sos-detail-value">' + escapeHtml(d.responderNote) + '</span></div>'
      );
    }
    if (d.fisherReply === 1 || d.fisherReply === 2) {
      var replyText = d.fisherReply === 2 ? 'Safe now' : 'Still in danger';
      rows.push(
        '<div class="sos-detail-row"><span class="sos-detail-label">Fisher Reply</span>' +
        '<span class="sos-detail-value' + (d.fisherReply === 1 ? ' sos-fisher-danger' : '') + '">' +
        escapeHtml(replyText) + '</span></div>'
      );
    }
    return rows.join('');
  }

  /**
   * Badge for a trip-anomaly case's case_type (docs/38 Phase 3 / GET
   * /api/ai/anomaly/cases/open). Deliberately not a severity label - the
   * distinction is model confidence (low-confidence cold-start profile vs.
   * an established one), per the acceptance boundary: "Low-confidence
   * results enter a verification queue. High-confidence results request
   * responder attention."
   */
  function caseTypeBadge(caseType) {
    return caseType === 'verification'
      ? { text: 'Verification', cssClass: 'case-type-verification' }
      : { text: 'Responder Attention', cssClass: 'case-type-responder-attention' };
  }

  /**
   * A case's display state from its four independent, persistent action
   * timestamps (docs/38 Phase 3 item 3). Checked most-final-first so a case
   * that has been through more than one action still shows something
   * meaningful; a case an evaluation refresh only just created has none of
   * these set and reads as "Open".
   */
  function caseStatusLabel(caseRow) {
    var c = caseRow || {};
    if (c.resolvedAt) return { text: 'Resolved', cssClass: 'case-status-resolved' };
    if (c.escalatedAt) return { text: 'Escalated', cssClass: 'case-status-escalated' };
    if (c.dismissedAt) return { text: 'Dismissed', cssClass: 'case-status-dismissed' };
    if (c.acknowledgedAt) return { text: 'Acknowledged', cssClass: 'case-status-acknowledged' };
    return { text: 'Open', cssClass: 'case-status-open' };
  }

  /**
   * Human-facing "how old is the trusted data behind this" label, from the
   * API's `data_age_seconds` (docs/38 Phase 2 item 4 / Phase 3 item 4: "last
   * trusted contact/data age" must be visible, not just a raw score). A
   * negative or missing value never claims a fresh age it does not have.
   */
  function formatDataAge(seconds) {
    if (seconds == null || !isFinite(seconds) || seconds < 0) return 'unknown age';
    var totalMinutes = Math.floor(seconds / 60);
    var hours = Math.floor(totalMinutes / 60);
    var minutes = totalMinutes % 60;
    if (hours <= 0) return minutes + 'm old';
    return hours + 'h ' + minutes + 'm old';
  }

  /**
   * One "Trip checks" queue row as an HTML string - pure, like
   * responderStatusHtml, so the same markup is exercised by `node --test`
   * without a DOM. Consumes the API response shape directly
   * (docs/05_PUBLIC_API.md "Trip-anomaly review queue"): snake_case fields,
   * `reasons` as the factor list `score_trip` produces. The dominant factor
   * (highest `contribution`) is shown as *why it was raised*, per docs/38
   * Phase 3 item 4.
   *
   * Action buttons are omitted once the case is resolved (defensive - the
   * API already excludes resolved cases from GET /cases/open, so this
   * should never render a resolved row in practice) and the Acknowledge
   * button disables once already acknowledged, matching the idempotent
   * intent of the action without a second network round trip to discover
   * that.
   */
  function tripCheckRowHtml(caseRow) {
    var c = caseRow || {};
    var typeBadge = caseTypeBadge(c.case_type);
    var statusBadge = caseStatusLabel({
      resolvedAt: c.resolved_at,
      escalatedAt: c.escalated_at,
      dismissedAt: c.dismissed_at,
      acknowledgedAt: c.acknowledged_at
    });
    var reasons = Array.isArray(c.reasons) ? c.reasons : [];
    var topReason = reasons.reduce(function (best, item) {
      var contribution = (item && item.contribution) || 0;
      return (!best || contribution > best.contribution) ? { contribution: contribution, description: item.description } : best;
    }, null);
    var reasonText = (topReason && topReason.description) || 'No reason recorded.';
    var ageText = formatDataAge(c.data_age_seconds);
    var isSynthetic = c.source === 'synthetic';
    var sourcePill = isSynthetic ? { text: 'DEMO', cssClass: 'alert-demo-badge' } : { text: 'LIVE', cssClass: 'alert-live-badge' };
    var scoreText = typeof c.score === 'number' ? Math.round(c.score * 100) + '%' : '—';
    var caseId = escapeHtml(c.id);

    // "View Activity" is always available, even once resolved - it opens the
    // authorized timeline (docs/41 Phase 4), which is a read, not a mutation.
    var actions = '<button class="trip-check-action" data-case-action="activity" data-case-id="' + caseId + '">View Activity</button>';
    if (!c.resolved_at) {
      actions +=
        '<button class="trip-check-action" data-case-action="acknowledge" data-case-id="' + caseId + '"' +
        (c.acknowledged_at ? ' disabled' : '') + '>Acknowledge</button>' +
        '<button class="trip-check-action" data-case-action="dismiss" data-case-id="' + caseId + '">Dismiss</button>' +
        '<button class="trip-check-action" data-case-action="escalate" data-case-id="' + caseId + '">Escalate</button>' +
        '<button class="trip-check-action trip-check-action-resolve" data-case-action="resolve" data-case-id="' + caseId + '">Resolve</button>';
    }

    return (
      '<div class="trip-check-row" data-case-id="' + caseId + '">' +
        '<div class="trip-check-row-header">' +
          '<span class="case-type-badge ' + typeBadge.cssClass + '">' + escapeHtml(typeBadge.text) + '</span>' +
          '<span class="case-status-badge ' + statusBadge.cssClass + '">' + escapeHtml(statusBadge.text) + '</span>' +
          '<span class="' + sourcePill.cssClass + '">' + sourcePill.text + '</span>' +
        '</div>' +
        '<div class="trip-check-row-body">' +
          '<span class="trip-check-vessel">' + escapeHtml(c.vessel_id) + '</span>' +
          '<span class="trip-check-score">Confidence score ' + scoreText + '</span>' +
          '<span class="trip-check-reason">' + escapeHtml(reasonText) + '</span>' +
          '<span class="trip-check-age">Last trusted contact: ' + escapeHtml(ageText) + '</span>' +
        '</div>' +
        '<div class="trip-check-row-actions">' + actions + '</div>' +
      '</div>'
    );
  }

  /**
   * The whole "Trip checks" queue as one HTML string: an honest empty state
   * (never a blank panel that reads as "still loading" or "broken") or the
   * joined rows, newest first as the API already orders them.
   */
  function tripChecksListHtml(cases) {
    if (cases === null) {
      return '<div class="trip-checks-empty trip-checks-unavailable">Trip checks queue unavailable &middot; unable to reach the anomaly detection service.</div>';
    }
    var list = Array.isArray(cases) ? cases : [];
    if (list.length === 0) {
      return '<div class="trip-checks-empty">No trip checks right now - every recent trip is within its expected pattern.</div>';
    }
    return list.map(tripCheckRowHtml).join('');
  }

  var RISK_STATUS_CLASS = { alert: 'status-alert', overdue: 'status-overdue', check_needed: 'status-overdue', watch: 'status-watch', normal: 'status-normal' };
  var RISK_PRIORITY = { alert: 0, overdue: 1, check_needed: 1, watch: 2, normal: 3 };

  function riskRowHtml(row, open) {
    var score = typeof row.score === 'number' ? row.score.toFixed(2) : String(row.score || '--');
    var lastSeen = row.last_contact_at ? new Date(row.last_contact_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '--';
    var status = row.status || 'normal';
    var statusLabel = status === 'check_needed' ? 'CHECK NEEDED' : status.toUpperCase();
    var factors = Array.isArray(row.factors) ? row.factors : [];
    return '' +
      '<details class="ai-risk-item"' + (open ? ' open' : '') + '>' +
        '<summary>' +
          '<div class="ai-risk-main">' +
            '<div class="ai-risk-title">' + escapeHtml(row.vessel_id) + ' · Trip ' + escapeHtml(row.trip_id) +
              (row.source === 'synthetic' ? ' <span class="alert-demo-badge">DEMO</span>' : '') + '</div>' +
            '<div class="ai-risk-meta">Expected buoy ' + escapeHtml(row.expected_next_buoy_id || 'n/a') + ' · Last contact ' + escapeHtml(lastSeen) + '</div>' +
          '</div>' +
          '<div class="ai-risk-score">' + escapeHtml(score) + '<span class="ai-risk-status ' + (RISK_STATUS_CLASS[status] || 'status-normal') + '">' + escapeHtml(statusLabel) + '</span></div>' +
        '</summary>' +
        '<div class="ai-risk-details">' +
          '<div class="ai-factor-list">' + factors.map(function (factor) {
            return '<div class="ai-factor-row">' +
              '<div class="ai-factor-name">' + escapeHtml(factor.code || 'factor') + '</div>' +
              '<div class="ai-factor-value">' + Number(factor.contribution || 0).toFixed(3) + '</div>' +
              '<div class="ai-factor-explainer">' + escapeHtml(factor.description || '') + '</div>' +
            '</div>';
          }).join('') + '</div>' +
        '</div>' +
      '</details>';
  }

  /**
   * The vessel risk feed (GET /api/ai/anomaly/active) as `{html, count}`:
   * pure, so what a responder sees for each freshness and monitoring state
   * is covered by `node --test`. `factors` are docs/05 factor objects.
   */
  function riskFeedHtml(rows, state) {
    var s = state || {};
    var hasRows = Array.isArray(rows) && rows.length > 0;
    // Not monitoring means an empty feed proves nothing (docs/05 E5.7); rows
    // the last evaluation did score are still shown, under the notice.
    var notMonitoring = s.monitoring === 'unavailable'
      ? '<div class="ai-empty-state ai-unavailable-state">Not monitoring - no live contact source</div>'
      : '';
    if (notMonitoring && !hasRows) {
      return { html: notMonitoring, count: '--', attention: '--' };
    }
    if (rows === null || (s.freshness === 'offline' && !hasRows)) {
      return { html: '<div class="ai-empty-state ai-unavailable-state">Vessel risk feed unavailable &middot; unable to reach the anomaly service.</div>', count: '--', attention: '--' };
    }
    if (s.freshness === 'stale' && !hasRows) {
      return { html: '<div class="ai-empty-state ai-unavailable-state">Vessel risk feed is stale &middot; unable to refresh anomaly service.</div>', count: '--', attention: '--' };
    }
    if (!hasRows) {
      return { html: '<div class="ai-empty-state">No active vessel risk rows available.</div>', count: '0', attention: '0' };
    }
    var sorted = rows.slice().sort(function (a, b) {
      var diff = (RISK_PRIORITY[a.status] !== undefined ? RISK_PRIORITY[a.status] : 9) - (RISK_PRIORITY[b.status] !== undefined ? RISK_PRIORITY[b.status] : 9);
      return diff !== 0 ? diff : (b.score || 0) - (a.score || 0);
    });
    var html = sorted.map(function (row, index) { return riskRowHtml(row, index === 0); }).join('');
    if (s.freshness === 'stale' || s.freshness === 'offline') {
      html = '<div class="ai-risk-stale-notice">' +
        '<span class="' + (s.freshness === 'offline' ? 'alert-demo-badge' : 'alert-unknown-badge') + '">FEED ' + (s.freshness === 'offline' ? 'OFFLINE' : 'STALE') + '</span> ' +
        'Vessel risk feed unavailable &middot; showing last-known status</div>' + html;
    }
    var attention = sorted.filter(function (row) { return row.status && row.status !== 'normal'; }).length;
    return { html: notMonitoring + html, count: String(sorted.length), attention: String(attention) };
  }

  // The drift map's stroke colors, shared by the map layers and the legend so
  // a legend chip is always the exact visible color (docs/47).
  var DRIFT_COLORS = {
    contour95: '#ef4444',
    contour75: '#f59e0b',
    contour50: '#facc15',
    track: '#2563eb',
    nextArea: '#38bdf8',
    searched: '#94a3b8'
  };

  function contourBand(mass) {
    return mass >= 0.9 ? '95' : (mass >= 0.7 ? '75' : '50');
  }

  /**
   * The legend rows for exactly the layers dashboard-ai-ops.js draws for a
   * drift payload (docs/71 RND-06): nothing for an insufficient case or a
   * payload without contours.
   */
  function driftLegendItems(payload) {
    var p = payload || {};
    var isRealCase = typeof p.environmental_status === 'string';
    if (isRealCase && p.environmental_status !== 'ok') return [];
    var contours = (p.contours && p.contours.length) ? p.contours : ((p.prediction && p.prediction.contours) || []);
    if (!contours.length) return [];
    var bands = {};
    contours.forEach(function (feature) { bands[contourBand(feature.properties && feature.properties.mass)] = true; });
    var items = ['95', '75', '50'].filter(function (band) { return bands[band]; }).map(function (band) {
      return { key: 'contour' + band, label: band + '% search area', color: DRIFT_COLORS['contour' + band], dashed: band === '95' };
    });
    var origin = p.posterior_grid && p.posterior_grid.origin;
    if (origin && p.search_sectors && p.search_sectors.length) {
      items.push({ key: 'searched', label: 'Searched area', color: DRIFT_COLORS.searched, dashed: true });
    }
    if (isRealCase && p.next_area && p.next_area.bounds) {
      items.push({ key: 'nextArea', label: 'Next area to review', color: DRIFT_COLORS.nextArea, dashed: true });
    }
    if (!isRealCase && p.ground_truth_track && p.ground_truth_track.length) {
      items.push({ key: 'track', label: 'Ground-truth track (synthetic)', color: DRIFT_COLORS.track, dashed: true });
    }
    return items;
  }

  function driftLegendHtml(items) {
    if (!items || !items.length) return '';
    return '<div class="ai-map-key-title">Drift map key</div>' + items.map(function (item) {
      return '<div class="ai-map-key-row">' +
        '<span class="ai-map-chip" style="border-color:' + escapeHtml(item.color) + ';border-style:' + (item.dashed ? 'dashed' : 'solid') + '"></span>' +
        '<span>' + escapeHtml(item.label) + '</span>' +
      '</div>';
    }).join('');
  }

  // The codes app/ai/environment.py can put in a run's insufficiency_reason.
  var INSUFFICIENCY_TEXT = {
    insufficient_field_geometry: 'Fewer than two buoys near the last position reported currents within an hour of it.',
    insufficient_current_coverage: 'Buoy currents cover less than half of the forecast area; the rest would be guesswork.',
    degraded_wind_source: 'Live wind data was unavailable, so the forecast would rest on a fallback wind.'
  };

  function insufficiencyText(code) {
    if (!code) return 'Reason not recorded.';
    return INSUFFICIENCY_TEXT[code] || String(code);
  }

  /**
   * Whether a drift/search case (GET /api/ai/drift/incident/{id}'s payload)
   * may currently accept a search-sector report
   * (docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md
   * Phase 4 item 2: "Disable the action when the case is not confirmed,
   * inputs are insufficient, or it is a demo replay"). Pure decision logic,
   * kept separate from dashboard-ai-ops.js's DOM/Leaflet rendering so it can
   * be unit tested directly.
   *
   * Returns `{ ok: true }` or `{ ok: false, reason: string }` - never a bare
   * boolean, so a caller always has something to show a responder.
   */
  function eligibleForSearchReport(payload) {
    if (!payload || !payload.incident) {
      return { ok: false, reason: 'No eligible case selected.' };
    }
    var incident = payload.incident;
    if (incident.is_synthetic) {
      return { ok: false, reason: 'This is a synthetic replay, not a live case.' };
    }
    if (incident.case_state !== 'confirmed') {
      return { ok: false, reason: 'Case is ' + incident.case_state + ', not confirmed.' };
    }
    if (payload.environmental_status !== 'ok') {
      return { ok: false, reason: 'Environmental inputs are insufficient for this run.' };
    }
    return { ok: true };
  }

  /**
   * Freshness/source/calibration line for the squall panel
   * (docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md Phase 3 item 5),
   * from the unified `GET /api/ai/squall/current` /
   * `GET /api/public/squall` response shape (docs/05_PUBLIC_API.md "Squall
   * nowcast"). Pure, like tripCheckRowHtml - reuses the same LIVE/DEMO
   * badge and data-age string conventions rather than inventing new ones,
   * since both are model-driven AqOne outputs on the same dashboard.
   *
   * `payload.level === 'unknown'` renders a neutral notice with the
   * backend's `status_reason` - this is the "insufficient data" state,
   * deliberately distinct from an empty "no active detections" panel: an
   * alarm that cannot be evaluated must never look the same as "all clear".
   *
   * The LIVE/DEMO badge only renders when `payload.source` is an actual
   * "live" or "synthetic" string from a real backend response. A client-side
   * fallback for a fetch that never reached the backend at all (no `source`
   * field) must not be badged DEMO - that would misrepresent a plain
   * connectivity failure as deliberately-synthetic data.
   */
  function squallStatusHtml(payload) {
    var p = payload || {};
    var ageText = formatDataAge(p.data_age_seconds);
    var calibrationText = p.calibration === 'synthetic'
      ? 'calibrated on simulated data'
      : 'calibrated model';
    var isStaleOrOffline = p.freshness === 'stale' || p.freshness === 'offline';
    var badgeHtml = '';
    if (isStaleOrOffline) {
      badgeHtml =
        '<span class="alert-demo-badge">LAST KNOWN</span>' +
        '<span class="alert-unknown-badge" style="margin-left:4px;">FEED ' + (p.freshness === 'offline' ? 'OFFLINE' : 'STALE') + '</span>';
    } else if (p.source === 'live' || p.source === 'synthetic') {
      var badge = alertBadge(p.source === 'live');
      badgeHtml = '<span class="' + badge.cssClass + '">' + badge.text + '</span>';
    }
    var line =
      '<div class="ai-squall-status-line">' +
        badgeHtml +
        '<span class="ai-squall-status-age">' + escapeHtml(ageText) + '</span>' +
        '<span class="ai-squall-status-calibration">' + escapeHtml(calibrationText) + '</span>' +
      '</div>';
    if (p.level === 'unknown' || isStaleOrOffline || p.status_reason) {
      var reason = p.status_reason || (p.level === 'unknown' ? 'Squall status cannot be confirmed right now.' : '');
      if (reason) {
        line += '<div class="ai-squall-status-reason">' + escapeHtml(reason) + '</div>';
      }
    }
    return line;
  }

  /**
   * Plain-language label for one operations_audit_events `action` code
   * (docs/41_OPERATIONS_CONSOLE_AUDITABILITY_IMPLEMENTATION_PLAN.md Phase 4
   * item 2: "show the authorized timeline in plain language"). Falls back to
   * the raw code itself for anything not in this table, so a future action
   * added on the backend renders as *something* readable rather than a blank
   * row - the whole point of a plain-language label is lost if a missing
   * entry instead hides the event.
   */
  var AUDIT_ACTION_LABELS = {
    'sos.acknowledge': 'Acknowledged SOS',
    'sos.resolve': 'Resolved SOS',
    'anomaly.acknowledge': 'Acknowledged anomaly case',
    'anomaly.dismiss': 'Dismissed anomaly case',
    'anomaly.escalate': 'Escalated anomaly case',
    'anomaly.resolve': 'Resolved anomaly case',
    'drift.open': 'Opened search case',
    'drift.rerun': 'Reran drift prediction',
    'drift.resolve': 'Resolved search case',
    'drift.cancel': 'Cancelled search case',
    'drift.search_sector_report': 'Reported a searched sector',
    'sea_condition.declare': 'Declared sea condition',
    'advisory.create': 'Created advisory',
    'advisory.update': 'Updated advisory',
    'advisory.delete': 'Deleted advisory',
    'advisory.alert': 'Published danger-zone alert',
    'vessel_device.pairing_code_issue': 'Issued device pairing code',
    'vessel_device.revoke': 'Revoked vessel device',
    'auth.login_success': 'Logged in',
    'auth.login_failure': 'Failed login attempt',
    'auth.admin_signup': 'Created operator account',
    'ops.case_view': 'Viewed case timeline',
    'ops.audit_search': 'Searched audit log',
    'ops.audit_export': 'Exported audit log'
  };

  function formatAuditAction(action) {
    return AUDIT_ACTION_LABELS[action] || String(action || 'unknown action');
  }

  /**
   * One row of a case's authorized timeline or the admin audit search
   * (docs/41 Phase 4) as an HTML string - pure, like tripCheckRowHtml, and
   * built from exactly the redacted columns
   * GET /api/ops/cases/.../timeline and GET /api/ops/audit already return
   * (docs/05_PUBLIC_API.md "Operations audit"). `metadata` is a small
   * whitelist of enum/id-only fields by construction on the backend
   * (app/audit.py) - rendered as escaped `key: value` text with no
   * per-action formatting, since nothing in it is free text needing special
   * handling.
   *
   * `event.actor_email` is null for a system/bootstrap event (a failed
   * login, or admin-signup before any operator session exists) - shown as
   * "System" rather than a blank actor, which would read as a rendering
   * bug rather than an honest "no human was signed in yet".
   */
  function auditEventRowHtml(event) {
    var e = event || {};
    var badge = alertBadge(!e.is_demo);
    var actorText = e.actor_email || 'System';
    var metadata = e.metadata && typeof e.metadata === 'object' ? e.metadata : {};
    var metadataText = Object.keys(metadata)
      .map(function (key) { return key + ': ' + metadata[key]; })
      .join(', ');

    return (
      '<div class="audit-event-row">' +
        '<div class="audit-event-row-header">' +
          '<span class="' + badge.cssClass + '">' + badge.text + '</span>' +
          '<span class="audit-event-time">' + escapeHtml(e.occurred_at) + '</span>' +
          '<span class="audit-event-outcome">' + escapeHtml(e.outcome) + '</span>' +
        '</div>' +
        '<div class="audit-event-row-body">' +
          '<span class="audit-event-action">' + escapeHtml(formatAuditAction(e.action)) + '</span>' +
          '<span class="audit-event-actor">' + escapeHtml(actorText) + '</span>' +
          (metadataText ? '<span class="audit-event-metadata">' + escapeHtml(metadataText) + '</span>' : '') +
        '</div>' +
      '</div>'
    );
  }

  /**
   * A case's whole timeline as one HTML string - an honest empty state, not
   * a blank panel indistinguishable from "still loading" (same reasoning as
   * tripChecksListHtml).
   */
  function auditTimelineHtml(events) {
    var list = Array.isArray(events) ? events : [];
    if (list.length === 0) {
      return '<div class="audit-timeline-empty">No recorded activity for this case yet.</div>';
    }
    return list.map(auditEventRowHtml).join('');
  }

  return {
    escapeHtml: escapeHtml,
    formatLatLon: formatLatLon,
    utf8ByteLength: utf8ByteLength,
    lateLabel: lateLabel,
    flagLabel: flagLabel,
    deliveryLabel: deliveryLabel,
    classifyFreshness: classifyFreshness,
    freshnessLabel: freshnessLabel,
    alertBadge: alertBadge,
    registrationBadge: registrationBadge,
    registrationBadgeHtml: registrationBadgeHtml,
    formatEta: formatEta,
    responderStatusHtml: responderStatusHtml,
    caseTypeBadge: caseTypeBadge,
    caseStatusLabel: caseStatusLabel,
    formatDataAge: formatDataAge,
    tripCheckRowHtml: tripCheckRowHtml,
    tripChecksListHtml: tripChecksListHtml,
    riskFeedHtml: riskFeedHtml,
    DRIFT_COLORS: DRIFT_COLORS,
    driftLegendItems: driftLegendItems,
    driftLegendHtml: driftLegendHtml,
    insufficiencyText: insufficiencyText,
    eligibleForSearchReport: eligibleForSearchReport,
    squallStatusHtml: squallStatusHtml,
    formatAuditAction: formatAuditAction,
    auditEventRowHtml: auditEventRowHtml,
    auditTimelineHtml: auditTimelineHtml
  };
});
