(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var escapeHtml = ns.escapeHtml || function (s) { return s == null ? '' : String(s); };
  var alertBadge = ns.alertBadge || function () { return { cssClass: '', text: '' }; };
  var map = ns.map;
  var formatLatLon = ns.formatLatLon || function () { return 'unknown position'; };
  var flagLabel = ns.flagLabel || function (flag) { return String(flag || ''); };

  const alertData = [];

  let liveAlerts = [];

  function allAlerts() {
    return liveAlerts.concat(alertData);
  }

  function alertIcon(type) {
    const icons = {
      'sos': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      'wave-zone': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12c1.5-2 3.5-3 5.5-3s4 1 5.5 3 3.5 3 5.5 3 4-1 5.5-3"/><path d="M2 7c1.5-2 3.5-3 5.5-3s4 1 5.5 3 3.5 3 5.5 3 4-1 5.5-3"/></svg>`,
      'overdue-vessel': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`,
      'capsizing-risk': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      'forecast-storm': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 19H9a7 7 0 1 1 6.7-9H17.5a4.5 4.5 0 1 1 0 9z"/><path d="M13 11l-2 4h3l-2 4"/></svg>`,
      'storm-surge': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 9c2-3 5-3 7 0s5 3 7 0 5-3 7 0"/><path d="M2 15c2-3 5-3 7 0s5 3 7 0 5-3 7 0"/><path d="M12 2v4"/><path d="M9.5 4.5L12 2l2.5 2.5"/></svg>`,
    };
    const colors = { 'sos': 'icon-red', 'wave-zone': 'icon-yellow', 'overdue-vessel': 'icon-orange', 'capsizing-risk': 'icon-yellow', 'forecast-storm': 'icon-red', 'storm-surge': 'icon-red' };
    return `<div class="alert-icon ${colors[type] || 'icon-yellow'}">${icons[type] || ''}</div>`;
  }

  function alertStatusPill(status, fisherReply) {
    if (fisherReply === 1) {
      return '<span class="alert-status status-danger">Still in Danger</span>';
    }
    const map = { active: 'status-active', acknowledged: 'status-acknowledged', resolved: 'status-resolved' };
    return `<span class="alert-status ${map[status] || ''}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>`;
  }

  function confidenceColor(conf) {
    if (conf >= 80) return '#e74c3c';
    if (conf >= 60) return '#f39c12';
    return '#f1c40f';
  }

  // An SOS shows no confidence score. The other alert types are model
  // output and a percentage is meaningful; a person pressing the button is a
  // fact, and dressing it in a fabricated confidence number would be a lie in
  // the one place on this dashboard where lying costs the most.
  function alertConfidenceRow(a) {
    if (a.type === 'sos' || a.confidence == null) {
      return `<div class="aq-alert-conf">
            <span class="aq-stage-mini">${escapeHtml(a.stage || '')}</span>
          </div>`;
    }
    return `<div class="aq-alert-conf">
            <span class="aq-conf-mini" style="color:${confidenceColor(a.confidence)};">${a.confidence}% conf</span>
            <span class="aq-conf-bar"><span class="aq-conf-fill" style="width:${a.confidence}%;background:${confidenceColor(a.confidence)};"></span></span>
            <span class="aq-stage-mini">${escapeHtml(a.stage || '')}</span>
          </div>`;
  }

  function fisherReportRow(a) {
    var reply = a.fisherReply != null ? a.fisherReply : (a.drawerData && a.drawerData.fisherReply);
    if (reply === 1) {
      return '<div class="alert-fisher-report alert-fisher-danger">Fisher reports: STILL IN DANGER</div>';
    }
    if (reply === 2) {
      return '<div class="alert-fisher-report alert-fisher-safe">Fisher reports: SAFE NOW</div>';
    }
    return '';
  }

  function renderAlerts() {
    const list = document.getElementById('alert-list');
    const rows = allAlerts();
    if (rows.length === 0) {
      list.innerHTML = '<p class="panel-stub-text">No active incidents</p>';
      return;
    }
    list.innerHTML = rows.map((a, i) => `
      <div class="alert-row${(a.isLive || a.provenance === 'unknown') ? ' alert-row-live' : ' alert-row-secondary'}" data-alert-index="${i}" tabindex="0" role="button" aria-label="Incident: ${escapeHtml(a.desc)}">
        ${alertIcon(a.type)}
        <div class="alert-info">
          <div class="alert-desc">${(function () {
            var prov = a.provenance || (a.isLive ? 'real' : (a.isSynthetic ? 'synthetic' : (a.type === 'sos' ? 'unknown' : 'demo')));
            var badge = alertBadge(prov);
            var title = '';
            if (prov === 'synthetic' || prov === 'demo' || (!a.isLive && prov !== 'unknown')) {
              title = ' title="Scripted sample data, not a real incident"';
            } else if (prov === 'unknown') {
              title = ' title="Distress call with unknown provenance"';
            }
            return '<span class="' + badge.cssClass + '"' + title + '>' + badge.text + '</span>';
          })()}${escapeHtml(a.desc)}</div>
          ${a.subtitle ? `<div class="alert-subtitle">${escapeHtml(a.subtitle)}</div>` : ''}
          ${(a.owner || a.phone) ? `<div class="alert-sender"><span>Sender: ${escapeHtml(a.owner || 'Unnamed vessel')}${a.phone ? ' &middot; ' + escapeHtml(a.phone) : ''}</span></div>` : ''}
          ${a.type === 'sos' ? `<div class="alert-trust">${a.drawerData && a.drawerData.vesselVerified ? '<span class="trust-verified">Verified by MDRRMO</span>' : '<span class="trust-neutral">not yet verified</span>'}${a.drawerData && a.drawerData.phoneSetBy === 'anonymous' ? ' <span class="trust-neutral">(unverified number)</span>' : ''}</div>` : (typeof ns.registrationBadgeHtml === 'function' ? `<div class="alert-reg">${ns.registrationBadgeHtml(a.drawerData && a.drawerData.licenseType)}</div>` : '')}
          <div class="alert-meta">${escapeHtml(a.time)} &middot; ${
            a.lat == null || a.lng == null
              ? '<span class="alert-nofix">no GPS fix</span>'
              : escapeHtml(formatLatLon(a.lat, a.lng))
          }${a.etaAt ? ' &middot; <span data-eta-at="' + escapeHtml(a.etaAt) + '"></span>' : ''}</div>
          ${a.lateLabel ? `<span class="alert-flag">${escapeHtml(a.lateLabel)}</span>` : ''}
          ${(a.flags || []).map(function (flag) { return `<span class="alert-flag">${escapeHtml(flagLabel(flag))}</span>`; }).join('')}
          ${a.openCallsForVessel > 1 ? `<span class="alert-flag">${a.openCallsForVessel} calls from this vessel</span>` : ''}
          ${a.delivery ? `<div class="alert-delivery">${escapeHtml(a.delivery)}</div>` : ''}
          ${fisherReportRow(a)}
          ${alertConfidenceRow(a)}
        </div>
        ${alertStatusPill(a.status, a.fisherReply != null ? a.fisherReply : (a.drawerData && a.drawerData.fisherReply))}
      </div>
    `).join('');

    list.querySelectorAll('.alert-row').forEach(row => {
      function activateAlert() {
        var a = rows[row.dataset.alertIndex];
        if (!a) return;
        // An SOS sent without a GPS fix is still a real distress call and must
        // stay clickable. There is simply nowhere to pan the map to.
        if (a.lat != null && a.lng != null) {
          map.setView([a.lat, a.lng], 14, { animate: true, duration: 1 });
        }
        if (a.drawerData && (a.sosEventId != null || a.type === 'sos')) {
          ns.openIncidentDrawer(a.drawerData, (ns.liveSosMarkers && a.sosEventId != null && ns.liveSosMarkers[a.sosEventId]) || null);
        }
      }
      row.addEventListener('click', activateAlert);
      row.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          activateAlert();
        }
      });
    });
  }

  const liveBanner = document.getElementById('live-alert-banner');
  const bannerCountEl = document.getElementById('banner-alert-count');
  const squallCountEl = document.getElementById('banner-squall-count');
  if (squallCountEl) squallCountEl.textContent = 0;

  let activeAlertCount = 0;

  // Recomputes the alert badge and banner after alertData changes.
  //
  // Restored during the DangerzoneFeature merge: the weather-forecast code
  // calls this, but the branch's definition sat in the same block as the
  // removed fish-hotspot system, so taking our side dropped it and left a
  // ReferenceError on that path. This is the branch's logic minus the hotspot
  // parts, reusing the elements resolved just above.
  function syncAlertIndicators() {
    const unackedCount = liveAlerts.filter(function (alert) {
      return alert.status === 'active';
    }).length;
    activeAlertCount = unackedCount;
    const unresolvedCount = liveAlerts.filter(function (alert) {
      return alert.status !== 'resolved';
    }).length;
    const dangerReplyCount = liveAlerts.filter(function (alert) {
      const reply = alert.fisherReply != null ? alert.fisherReply : (alert.drawerData && alert.drawerData.fisherReply);
      return reply === 1 && alert.status !== 'resolved';
    }).length;

    const alertBadge = document.getElementById('badge-alerts');
    const sosStatus = document.getElementById('stats-sos-status');
    if (alertBadge) alertBadge.textContent = unackedCount;
    if (bannerCountEl) bannerCountEl.textContent = unackedCount;
    if (sosStatus) {
      if (unackedCount > 0) {
        sosStatus.textContent = unackedCount === 1 ? '1 UNACKNOWLEDGED SOS' : unackedCount + ' UNACKNOWLEDGED SOS';
        sosStatus.className = 'metric-status metric-status-danger';
      } else if (dangerReplyCount > 0) {
        sosStatus.textContent = 'STILL IN DANGER (' + dangerReplyCount + ' unresolved)';
        sosStatus.className = 'metric-status metric-status-danger';
      } else if (unresolvedCount > 0) {
        sosStatus.textContent = unresolvedCount === 1 ? '1 UNRESOLVED (ACKNOWLEDGED)' : unresolvedCount + ' UNRESOLVED (ACKNOWLEDGED)';
        sosStatus.className = 'metric-status metric-status-caution';
      } else {
        sosStatus.textContent = 'NO UNACKNOWLEDGED SOS';
        sosStatus.className = 'metric-status metric-status-clear';
      }
    }
    if (liveBanner) liveBanner.classList.toggle('has-alerts', unackedCount > 0 || unresolvedCount > 0);
    renderAlerts();
  }

  syncAlertIndicators();

  ns.alertData = alertData;
  ns.liveAlerts = liveAlerts;
  ns.allAlerts = allAlerts;
  ns.alertIcon = alertIcon;
  ns.alertStatusPill = alertStatusPill;
  ns.fisherReportRow = fisherReportRow;
  ns.confidenceColor = confidenceColor;
  ns.alertConfidenceRow = alertConfidenceRow;
  ns.renderAlerts = renderAlerts;
  ns.syncAlertIndicators = syncAlertIndicators;

})(window.AqOneDashboard = window.AqOneDashboard || {});
