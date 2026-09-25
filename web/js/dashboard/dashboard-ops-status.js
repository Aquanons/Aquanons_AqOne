(function (ns) {
  'use strict';
  if (!ns.ready) return;

  var gateway = document.getElementById('ops-gateway-status');
  var smsBanner = document.getElementById('ops-sms-banner');
  var dbBanner = document.getElementById('ops-db-banner');

  function renderStatus(status) {
    var stale = status.gateway_stale === true;
    if (gateway) {
      gateway.textContent = stale
        ? 'Gateway stale - last heard ' + (status.gateway_last_poll_at || 'never')
        : 'Gateway online - last heard ' + (status.gateway_last_poll_at || 'unknown');
      gateway.className = stale ? 'ops-gateway-stale' : 'ops-gateway-live';
    }
    if (smsBanner) {
      smsBanner.hidden = status.sms_configured !== false;
      smsBanner.textContent = 'SMS escalation not configured';
    }
    if (dbBanner) {
      var days = status.db_days_left;
      dbBanner.hidden = !Number.isFinite(days) || days > 7;
      dbBanner.textContent = dbBanner.hidden ? '' : 'Database expires in ' + days + ' days (' + (status.db_expires_at || 'date unknown') + '). Back up or renew it.';
    }
  }

  function pollOpsStatus() {
    return ns.authFetch('/api/ops/status').then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }).then(renderStatus).catch(function () {
      if (gateway) {
        gateway.textContent = 'Gateway status unavailable';
        gateway.className = 'ops-gateway-stale';
      }
    });
  }

  pollOpsStatus();
  setInterval(pollOpsStatus, 60000);
  ns.pollOpsStatus = pollOpsStatus;
})(window.AqOneDashboard = window.AqOneDashboard || {});
