(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var escapeHtml = ns.escapeHtml;
  var authFetch = ns.authFetch;
  var incidents = ns.incidents;
  var incidentDrawerData = ns.incidentDrawerData;

  // ===== SAR METRICS TAB =====
  // SAR metrics come from the evaluation scripts via /api/ai/metrics. There is
  // deliberately no hardcoded fallback: if the evals have not been run, the tab
  // says so rather than showing numbers nobody has verified.
  function sarRowsFromResults(results) {
    const rows = [];
    const pct = v => (typeof v === 'number' ? (v * 100).toFixed(1) + '%' : '--');
    const num = (v, digits, unit) =>
      typeof v === 'number' ? v.toFixed(digits) + (unit || '') : '--';

    const drift = results.drift;
    if (drift) {
      rows.push({
        label: 'Drift containment rate (95% contour)',
        value: pct(drift.containment_rate),
        target: 'Share of incidents whose true position fell inside the predicted search area'
      });
      rows.push({
        label: 'Search area reduction vs naive baseline',
        value: num(drift.search_area_reduction_factor, 2, 'x'),
        target: 'Against a circle expanding at maximum drift speed'
      });
      rows.push({
        label: 'Drift prediction runtime',
        value: num(drift.prediction_runtime_ms, 0, ' ms'),
        target: '24-hour forecast, Monte Carlo particle model'
      });
      rows.push({
        label: 'Incidents evaluated',
        value: drift.incidents_evaluated != null ? String(drift.incidents_evaluated) : '--',
        target: ''
      });
    }

    const anomaly = results.trip_anomaly;
    if (anomaly) {
      rows.push({
        label: 'Median detection latency',
        value: num(anomaly.median_detection_latency_minutes, 1, ' min'),
        target: 'From last buoy contact to reaching alert status'
      });
      rows.push({
        label: 'False alarm rate',
        value: pct(anomaly.false_alarm_rate),
        target: 'Measured on normal trips \u2014 responder trust is non-negotiable'
      });
      rows.push({
        label: 'Normal trips evaluated',
        value: anomaly.normal_trips_evaluated != null ? String(anomaly.normal_trips_evaluated) : '--',
        target: ''
      });
    }

    const squall = results.squall;
    if (squall) {
      rows.push({
        label: 'Squall mean lead time',
        value: num(squall.mean_lead_time_minutes, 1, ' min'),
        target: 'Warning issued before arrival \u2014 the number that decides whether it helps'
      });
      rows.push({ label: 'Squall precision', value: num(squall.precision, 3), target: '' });
      rows.push({ label: 'Squall recall', value: num(squall.recall, 3), target: '' });
    }

    return rows;
  }

  function renderSarEmpty(message) {
    const list = document.getElementById('sar-list');
    if (list) list.innerHTML = '<div class="ai-empty-state">' + escapeHtml(message) + '</div>';
  }

  function renderSarMetrics(results) {
    const list = document.getElementById('sar-list');
    if (!list) return;
    const rows = sarRowsFromResults(results);
    if (!rows.length) {
      renderSarEmpty('Evaluation results are present but contain no metrics.');
      return;
    }
    list.innerHTML = rows.map(m => `
      <div class="sar-row">
        <div class="sar-label">${m.label}</div>
        <div class="sar-value">${m.value}</div>
        ${m.target ? `<div class="sar-target">${m.target}</div>` : ''}
      </div>
    `).join('');

    const footer = document.querySelector('.sar-footer');
    const calibration =
      (results.drift && results.drift.calibration) ||
      (results.squall && results.squall.calibration) ||
      (results.trip_anomaly && results.trip_anomaly.calibration);
    if (footer && calibration) {
      footer.textContent =
        'Measured by the AqOne evaluation scripts. Models are calibrated on ' +
        calibration + ' observations.';
    }
  }

  function loadSarMetrics() {
    renderSarEmpty('Loading evaluation results\u2026');
    authFetch('/api/ai/metrics')
      .then(function (res) {
        if (res.status === 404) throw new Error('not-run');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(renderSarMetrics)
      .catch(function (err) {
        renderSarEmpty(
          err.message === 'not-run'
            ? 'No evaluation results yet. Run the eval scripts to populate these figures.'
            : 'Unable to load evaluation results.'
        );
      });
  }

  loadSarMetrics();
  document.getElementById('badge-sar').textContent = incidentDrawerData.filter(function (d) { return d.alertType === 'overdue' || d.alertType === 'squall'; }).length;


})(window.AqOneDashboard = window.AqOneDashboard || {});
