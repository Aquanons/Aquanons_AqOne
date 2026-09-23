(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var authFetch = ns.authFetch;
  var incidents = ns.incidents;
  var map = ns.map;
  var incidentLayer = ns.incidentLayer;
  var showToast = ns.showToast;
  var pulseCoverageCircle = ns.pulseCoverageCircle;
  var liveSosLayer = ns.liveSosLayer;
  var loadActiveSos = ns.loadActiveSos;
  var allAlerts = ns.allAlerts;
  var syncAlertIndicators = ns.syncAlertIndicators;
  var responderStatusHtml = ns.responderStatusHtml;
  var formatEta = ns.formatEta;
  var confidenceColor = ns.confidenceColor;

  // ===== INCIDENT DRAWER (scored alert / escalation ladder) =====
  const sosDrawer          = document.getElementById('sos-drawer');
  const sosDrawerHeader    = document.getElementById('sos-drawer-header');
  const sosDrawerTitle     = document.getElementById('sos-drawer-title');
  const sosDrawerClose     = document.getElementById('sos-drawer-close');
  const sosTimerEl         = document.getElementById('sos-timer');
  const sosBtnZoom         = document.getElementById('sos-btn-zoom');
  const sosBtnAcknowledge  = document.getElementById('sos-btn-acknowledge');
  const sosBtnResolve      = document.getElementById('sos-btn-resolve');
  const sosBtnBroadcast    = document.getElementById('sos-btn-broadcast');
  const sosBtnCheckin      = document.getElementById('sos-btn-checkin');
  const sosBtnActivity     = document.getElementById('sos-btn-activity');
  const sosBroadcastMsg    = document.getElementById('sos-broadcast-msg');
  const ackOverlay         = document.getElementById('ack-modal-overlay');
  if (ackOverlay) {
    ackOverlay.hidden = true;
  }

  let sosTimerInterval  = null;
  let sosAlertStartTime = null;
  let currentDrawerMarker  = null;
  let currentDrawerData    = null;

  function isAckModalOpen() {
    return !!(ackOverlay && ackOverlay.hidden === false);
  }

  function openIncidentDrawer(data, marker) {
    if (isAckModalOpen()) {
      // Prevent background case switching while acknowledgment modal is open
      return;
    }
    currentDrawerData   = data;
    currentDrawerMarker = marker;

    sosDrawerHeader.className = 'sos-drawer-header';
    if (data.alertType === 'sos')        sosDrawerHeader.classList.add('type-sos');
    else if (data.alertType === 'wave')  sosDrawerHeader.classList.add('type-wave');
    else if (data.alertType === 'capsizing') sosDrawerHeader.classList.add('type-capsizing');
    else if (data.alertType === 'overdue') sosDrawerHeader.classList.add('type-overdue');
    else if (data.alertType === 'squall') sosDrawerHeader.classList.add('type-squall');
    sosDrawerTitle.textContent = data.headerText;

    var regBadgeEl = document.getElementById('sos-registration-badge');
    if (regBadgeEl && typeof ns.registrationBadgeHtml === 'function') {
      regBadgeEl.innerHTML = ns.registrationBadgeHtml(data.licenseType);
    }

    var timerLabel = document.getElementById('sos-timer-label');
    if (data.alertType === 'overdue') {
      timerLabel.textContent = 'Time Since Last Contact';
    } else {
      timerLabel.textContent = 'Time Since Alert';
    }

    document.getElementById('sos-vessel-id').textContent = data.vesselId;
    document.getElementById('sos-owner').textContent     = data.skipperName || data.owner || 'Unknown';
    document.getElementById('sos-boat').textContent      = data.boat || '—';
    document.getElementById('sos-registration').textContent = data.license || 'Not declared';
    document.getElementById('sos-contact').textContent      = data.phone || 'Not provided';
    document.getElementById('sos-position').textContent  = data.position;
    document.getElementById('sos-buoy').textContent      = data.buoy;
    document.getElementById('sos-coverage').textContent  = data.coverage;

    // confidence + escalation
    //
    // A real SOS carries no confidence score and must not be shown with one.
    // The old code coerced a missing score to 0, which would have rendered a
    // human distress call as "0% confidence" - the most damaging possible
    // misreading on this screen. Null hides the meter instead.
    var confValueEl = document.getElementById('sos-confidence-value');
    var fill = document.getElementById('sos-confidence-fill');
    var confBlock = confValueEl ? confValueEl.closest('.sos-conf') : null;
    if (data.confidence == null) {
      if (confValueEl) confValueEl.textContent = 'Not scored';
      if (confValueEl) confValueEl.style.color = 'var(--text-muted, #94a3b8)';
      if (fill) fill.style.width = '0%';
      if (confBlock) confBlock.classList.add('is-unscored');
    } else {
      var conf = data.confidence;
      if (confBlock) confBlock.classList.remove('is-unscored');
      if (confValueEl) {
        confValueEl.textContent = conf + '%';
        confValueEl.style.color = confidenceColor(conf);
      }
      if (fill) {
        fill.style.width = conf + '%';
        fill.style.background = confidenceColor(conf);
      }
    }
    var stageEl = document.getElementById('sos-stage');
    stageEl.textContent = data.stage || 'Stage 1 \u2014 silent check-in';
    stageEl.className = 'aq-stage-badge';
    if (data.stage && data.stage.indexOf('STAGE 3') !== -1) stageEl.classList.add('stage-dispatch');
    else if (data.stage && data.stage.indexOf('STAGE 2') !== -1) stageEl.classList.add('stage-alert');
    else if (data.stage && data.stage.indexOf('SQUALL') !== -1) stageEl.classList.add('stage-squall');
    else stageEl.classList.add('stage-checkin');
    document.getElementById('sos-next-contact').textContent = data.nextContact || 'N/A';

    var baselineMs = data.timerBaseline ? data.timerBaseline * 1000 : 0;
    sosAlertStartTime = Date.now() - baselineMs;
    if (sosTimerInterval) clearInterval(sosTimerInterval);
    sosTimerInterval = setInterval(sosTickTimer, 1000);
    sosTickTimer();

    // Reflects the confirmed backend state, not just "a modal was submitted" -
    // reopening (or the periodic refresh) after a real acknowledgement must
    // not offer to acknowledge it again.
    if (data.acknowledgedAt) {
      sosBtnAcknowledge.disabled = true;
      sosBtnAcknowledge.textContent = 'Acknowledged';
    } else {
      sosBtnAcknowledge.disabled = false;
      sosBtnAcknowledge.textContent = 'Acknowledge';
    }
    renderResponderSection(data);
    sosBroadcastMsg.textContent = '';

    sosDrawer.classList.add('open');

    if (data.alertType === 'overdue' && data.buoy) {
      var buoyName = data.buoy.split(' ')[0];
      pulseCoverageCircle(buoyName);
    }
  }

  function closeSOSDrawer() {
    sosDrawer.classList.remove('open');
    if (sosTimerInterval) { clearInterval(sosTimerInterval); sosTimerInterval = null; }
    currentDrawerMarker = null;
    currentDrawerData   = null;
  }

  // Renders the responder-status/ETA/note/fisher-reply block from the
  // server's own data (never a browser-guessed state) - see
  // responderStatusHtml() in web/js/dashboard-utils.js for the pure part.
  function renderResponderSection(data) {
    var el = document.getElementById('sos-responder-block');
    if (!el) return;
    el.innerHTML = responderStatusHtml(data);
  }

  // Called after every successful /api/sos/active poll (dashboard-live-
  // sos.js) so an open drawer picks up a fisher's STILL_IN_DANGER / SAFE_NOW
  // reply, a status change, or a corrected ETA without the dispatcher having
  // to close and reopen it.
  function refreshOpenDrawer() {
    if (!currentDrawerData || currentDrawerData.alertType !== 'sos' || currentDrawerData.sosEventId == null) {
      return;
    }
    var updated = allAlerts().find(function (a) {
      return a.sosEventId === currentDrawerData.sosEventId;
    });
    if (!updated || !updated.drawerData) {
      // Event left the authoritative active list (e.g. resolved in another session)
      closeSOSDrawer();
      if (isAckModalOpen()) closeAckModal();
      showToast('Incident closed', 'This distress call has been resolved or closed.', false);
      return;
    }
    currentDrawerData = updated.drawerData;
    if (currentDrawerData.acknowledgedAt) {
      sosBtnAcknowledge.disabled = true;
      sosBtnAcknowledge.textContent = 'Acknowledged';
    } else {
      sosBtnAcknowledge.disabled = false;
      sosBtnAcknowledge.textContent = 'Acknowledge';
    }
    renderResponderSection(currentDrawerData);
  }

  function sosTickTimer() {
    if (!sosAlertStartTime) return;
    const elapsed = Math.floor((Date.now() - sosAlertStartTime) / 1000);
    const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const ss = String(elapsed % 60).padStart(2, '0');
    sosTimerEl.textContent = mm + ':' + ss;
  }

  sosDrawerClose.addEventListener('click', closeSOSDrawer);

  sosBtnZoom.addEventListener('click', function () {
    if (currentDrawerMarker) {
      map.setView(currentDrawerMarker.getLatLng(), 14);
    }
  });


  // ===== ACKNOWLEDGE WITH ETA =====
  //
  // Acknowledging is no longer a bare flag. The dispatcher tells the fisherman
  // what is happening and roughly when help arrives, which is the difference
  // between "someone saw my SOS" and "I know whether to stay with the boat".
  //
  // Minutes are collected here; the backend converts to an absolute arrival
  // time so the handset's countdown stays correct however slow delivery is.
  const ackVesselEl = document.getElementById('ack-modal-vessel');
  const ackStatusEl = document.getElementById('ack-status');
  const ackEtaEl = document.getElementById('ack-eta');
  const ackNoteEl = document.getElementById('ack-note');
  const ackConfirmBtn = document.getElementById('ack-btn-confirm');

  let ackTriggerEl = null;
  let ackTargetData = null;

  function closeAckModal() {
    if (ackOverlay) ackOverlay.hidden = true;
    ackTargetData = null;
    if (ackTriggerEl && typeof ackTriggerEl.focus === 'function') {
      try { ackTriggerEl.focus(); } catch (e) {}
      ackTriggerEl = null;
    }
  }

  function openAckModal() {
    if (!ackOverlay) return;
    ackTriggerEl = document.activeElement;
    ackTargetData = currentDrawerData ? Object.assign({}, currentDrawerData) : null;
    const label = ackTargetData
      ? (ackTargetData.desc || ackTargetData.vesselId || 'Distress call')
      : 'Distress call';
    if (ackVesselEl) ackVesselEl.textContent = label;
    ackOverlay.hidden = false;
    if (ackEtaEl) {
      ackEtaEl.focus();
    } else if (ackStatusEl) {
      ackStatusEl.focus();
    }
  }

  // Quick picks and the free-entry field stay in step with each other.
  const ackQuick = document.getElementById('ack-eta-quick');
  if (ackQuick) {
    ackQuick.addEventListener('click', function (event) {
      const chip = event.target.closest('.ack-eta-chip');
      if (!chip) return;
      ackQuick.querySelectorAll('.ack-eta-chip').forEach(function (b) {
        b.classList.remove('is-selected');
      });
      chip.classList.add('is-selected');
      if (ackEtaEl) ackEtaEl.value = chip.dataset.eta;
    });
  }
  if (ackEtaEl) {
    ackEtaEl.addEventListener('input', function () {
      if (!ackQuick) return;
      ackQuick.querySelectorAll('.ack-eta-chip').forEach(function (b) {
        b.classList.toggle('is-selected', b.dataset.eta === ackEtaEl.value);
      });
    });
  }

  // Focus containment inside acknowledgment dialog
  if (ackOverlay) {
    ackOverlay.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      var focusableSelector = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
      var focusable = Array.prototype.slice.call(ackOverlay.querySelectorAll(focusableSelector)).filter(function (el) {
        return el.offsetParent !== null || el.offsetWidth > 0 || el.offsetHeight > 0 || !el.hidden;
      });
      if (!focusable.length) return;
      var firstEl = focusable[0];
      var lastEl = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === firstEl || !ackOverlay.contains(document.activeElement)) {
          e.preventDefault();
          lastEl.focus();
        }
      } else {
        if (document.activeElement === lastEl || !ackOverlay.contains(document.activeElement)) {
          e.preventDefault();
          firstEl.focus();
        }
      }
    });
  }

  ['ack-modal-close', 'ack-btn-cancel'].forEach(function (id) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', closeAckModal);
  });
  if (ackOverlay) {
    ackOverlay.addEventListener('click', function (event) {
      if (event.target === ackOverlay) closeAckModal();
    });
  }

  sosBtnAcknowledge.addEventListener('click', openAckModal);

  if (ackConfirmBtn) {
    ackConfirmBtn.addEventListener('click', function () {
      const etaMinutes = Math.max(1, Math.min(720, parseInt(ackEtaEl && ackEtaEl.value, 10) || 20));
      const status = parseInt(ackStatusEl && ackStatusEl.value, 10) || 1;
      const note = (ackNoteEl && ackNoteEl.value.trim()) || null;
      const target = ackTargetData || currentDrawerData;
      const eventId = target && target.sosEventId;

      ackConfirmBtn.disabled = true;

      // Demo rows in alertData have no sosEventId and no backend acknowledge
      // endpoint to confirm against - they keep the previous local-only
      // behaviour rather than sitting in a permanent "pending" state.
      if (!eventId) {
        sosBtnAcknowledge.disabled = true;
        sosBtnAcknowledge.textContent = 'Acknowledged';
        if (currentDrawerData && (!target || currentDrawerData.vesselId === target.vesselId)) {
          currentDrawerData.etaAt = new Date(Date.now() + etaMinutes * 60000).toISOString();
          currentDrawerData.responderStatus = status;
          const row = allAlerts().find(function (a) {
            return a.vesselId === currentDrawerData.vesselId ||
                   (a.lat === currentDrawerData.lat && a.lng === currentDrawerData.lng);
          });
          if (row) {
            row.status = 'acknowledged';
            row.etaAt = currentDrawerData.etaAt;
            syncAlertIndicators();
          }
        }
        closeAckModal();
        ackConfirmBtn.disabled = false;
        return;
      }

      // A real incident waits for the server's answer before presenting
      // itself as acknowledged - a distress console that shows "Acknowledged"
      // when the request actually failed is worse than one that looks busy
      // for a moment.
      sosBtnAcknowledge.disabled = true;
      sosBtnAcknowledge.textContent = 'Acknowledging…';

      authFetch('/api/sos/' + encodeURIComponent(eventId) + '/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          eta_minutes: etaMinutes,
          responder_status: status,
          responder_note: note
        })
      })
        .then(function (res) {
          if (!res.ok) {
            var httpErr = new Error('HTTP ' + res.status);
            httpErr.status = res.status;
            throw httpErr;
          }
          return res.json();
        })
        .then(function () {
          closeAckModal();
          // The server's own row, not a guessed one - re-fetching also
          // refreshes the open drawer via refreshOpenDrawer().
          return loadActiveSos();
        })
        .catch(function (err) {
          console.warn('[AqOne] Acknowledgement not delivered:', err.message);
          // 403 is a distinct, honest reason from a network/server failure -
          // docs/41 Phase 4 "render server 403 errors clearly".
          if (err.status === 403) {
            showToast('Not permitted', "You don't have permission to acknowledge this incident.", true);
          } else {
            showToast('Not delivered', 'The fisherman may not have received the ETA.', true);
          }
          // Roll back only if the drawer is still showing THIS event
          if (currentDrawerData && currentDrawerData.sosEventId === eventId) {
            sosBtnAcknowledge.disabled = !!currentDrawerData.acknowledgedAt;
            sosBtnAcknowledge.textContent = currentDrawerData.acknowledgedAt ? 'Acknowledged' : 'Acknowledge';
          }
        })
        .finally(function () {
          ackConfirmBtn.disabled = false;
        });
    });
  }

  // Live countdown on acknowledged incidents, driven by the pure formatEta()
  // in web/js/dashboard-utils.js. Never renders a negative number: once the
  // promised time passes it says the rescue is delayed, because a countdown
  // expiring into silence reads as "nobody is coming". Ticks every
  // [data-eta-at] element on the page, which covers both the alert-list row
  // (dashboard-vessels-alerts.js) and the drawer's responder block above.
  setInterval(function () {
    document.querySelectorAll('[data-eta-at]').forEach(function (el) {
      var text = formatEta(el.dataset.etaAt);
      el.textContent = text;
      el.classList.toggle('is-overdue', text.indexOf('delayed') === 0);
    });
  }, 1000);

  sosBtnResolve.addEventListener('click', function () {
    const target = currentDrawerData ? Object.assign({}, currentDrawerData) : null;
    const eventId = target && target.sosEventId;

    // A demo row has no backend incident to resolve - keep the previous
    // local-only behaviour for it.
    if (!eventId) {
      if (currentDrawerMarker) {
        incidentLayer.removeLayer(currentDrawerMarker);
        liveSosLayer.removeLayer(currentDrawerMarker);
      }
      if (currentDrawerData && (!target || currentDrawerData.vesselId === target.vesselId)) {
        const row = allAlerts().find(function (a) {
          return a.vesselId === currentDrawerData.vesselId ||
                 (a.lat === currentDrawerData.lat && a.lng === currentDrawerData.lng);
        });
        if (row) { row.status = 'resolved'; syncAlertIndicators(); }
        closeSOSDrawer();
      }
      return;
    }

    // Waits for the server to confirm resolution before touching the map or
    // the drawer - removing the marker optimistically and then failing left
    // a resolved-looking incident that the backend still considered active.
    sosBtnResolve.disabled = true;
    authFetch('/api/sos/' + encodeURIComponent(eventId) + '/resolve', {
      method: 'POST'
    })
      .then(function (res) {
        if (!res.ok) {
          var httpErr = new Error('HTTP ' + res.status);
          httpErr.status = res.status;
          throw httpErr;
        }
        // Only close drawer if it is STILL showing the resolved event
        if (currentDrawerData && currentDrawerData.sosEventId === eventId) {
          closeSOSDrawer();
        }
        // The event has actually left storage server-side now, so let the
        // next active-feed refresh remove its marker/row rather than
        // guessing which one to remove client-side.
        return loadActiveSos();
      })
      .catch(function (err) {
        console.warn('[AqOne] Resolve not delivered:', err.message);
        if (err.status === 403) {
          showToast('Not permitted', "You don't have permission to resolve this incident.", true);
        } else {
          showToast('Not delivered', 'The incident is still active until this succeeds.', true);
        }
      })
      .finally(function () {
        sosBtnResolve.disabled = false;
      });
  });

  if (sosBtnBroadcast) {
    sosBtnBroadcast.disabled = true;
    sosBtnBroadcast.addEventListener('click', function () {
      if (sosBroadcastMsg) {
        sosBroadcastMsg.textContent = 'Broadcast unavailable: LoRa downlink to vessels is not supported.';
      }
    });
  }

  if (sosBtnCheckin) {
    sosBtnCheckin.disabled = true;
    sosBtnCheckin.addEventListener('click', function () {
      if (sosBroadcastMsg) {
        sosBroadcastMsg.textContent = 'Silent check-in unavailable: LoRa downlink to vessels is not supported.';
      }
    });
  }

  // A demo row has no backend sos_event to have an audit trail for
  // (docs/41 Phase 4) - same "no real incident behind this" guard as the
  // acknowledge/resolve handlers above.
  if (sosBtnActivity) {
    sosBtnActivity.addEventListener('click', function () {
      var eventId = currentDrawerData && currentDrawerData.sosEventId;
      if (!eventId || !ns.openActivityDrawer) return;
      ns.openActivityDrawer('sos_event', eventId, 'SOS Case Activity');
    });
  }

  ns.sosDrawer = sosDrawer;
  ns.openIncidentDrawer = openIncidentDrawer;
  ns.closeSOSDrawer = closeSOSDrawer;
  ns.ackOverlay = ackOverlay;
  ns.closeAckModal = closeAckModal;
  ns.openAckModal = openAckModal;
  ns.refreshOpenDrawer = refreshOpenDrawer;
  ns.confidenceColor = ns.confidenceColor || confidenceColor;

})(window.AqOneDashboard = window.AqOneDashboard || {});
