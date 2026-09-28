(function () {
  'use strict';

  var TOKEN_KEY = 'aqoneToken';
  var API_BASE = window.location.origin;

  function escapeHtml(val) {
    return String(val == null ? '' : val)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function getToken() {
    return sessionStorage.getItem(TOKEN_KEY) || '';
  }

  if (!getToken()) {
    window.location.replace('login.html');
    return;
  }

  (function applyStoredTheme() {
    var stored = null;
    try {
      stored = localStorage.getItem('aqone-theme') || localStorage.getItem('aqone_dark_mode');
    } catch (e) { stored = null; }
    if (stored === 'dark' || stored === 'true') {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  })();

  var allVessels = [];
  var currentFilter = 'all';

  function wentToSea(v) {
    return v.last_lat != null && v.last_lon != null;
  }

  function seaPill(v) {
    if (v.last_trip_status === 'open') {
      return '<span class="users-pill users-pill-sea">AT SEA</span>';
    }
    if (wentToSea(v)) {
      return '<span class="users-pill users-pill-sea">WENT TO SEA</span>';
    }
    return '<span class="users-pill users-pill-nofix">NO SEA RECORD</span>';
  }

  function fixText(v) {
    if (!wentToSea(v)) return '<span class="users-sub">No GPS fix recorded</span>';
    var lat = Number(v.last_lat).toFixed(4) + '° ' + (Number(v.last_lat) >= 0 ? 'N' : 'S');
    var lon = Number(v.last_lon).toFixed(4) + '° ' + (Number(v.last_lon) >= 0 ? 'E' : 'W');
    var when = '';
    try {
      when = new Date(v.last_fix_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) { when = ''; }
    return escapeHtml(lat + ' · ' + lon) +
      '<br /><span class="users-sub">' + escapeHtml(when) + ' · via ' + escapeHtml(v.last_fix_source || 'unknown') + '</span>';
  }

  function rowHtml(v) {
    var name = v.skipper_name || v.boat_name || v.vessel_id || 'Unidentified vessel';
    var regNo = v.license_number
      ? escapeHtml((v.license_type || '').toUpperCase() + ' ' + v.license_number)
      : '<span class="users-sub">Unregistered</span>';
    var phone = v.phone ? escapeHtml(v.phone) : '<span class="users-sub">—</span>';
    var status = v.handset_active
      ? '<span class="users-pill users-pill-active">ACTIVE</span>'
      : '<span class="users-pill users-pill-inactive">INACTIVE</span>';
    return '<tr>' +
      '<td><span class="users-name">' + escapeHtml(name) + '</span>' +
        '<br /><span class="users-sub">' + escapeHtml(v.boat_name || '') + ' · ' + escapeHtml(v.vessel_id || '') + '</span></td>' +
      '<td>' + regNo + '</td>' +
      '<td>' + phone + '</td>' +
      '<td>' + status + '</td>' +
      '<td>' + seaPill(v) + '</td>' +
      '<td>' + fixText(v) + '</td>' +
    '</tr>';
  }

  function render() {
    var el = document.getElementById('users-list');
    var countEl = document.getElementById('users-count');
    if (!el) return;
    var shown = allVessels.filter(function (v) {
      if (currentFilter === 'active') return v.handset_active;
      if (currentFilter === 'inactive') return !v.handset_active;
      if (currentFilter === 'atsea') return wentToSea(v);
      return true;
    });
    var activeCount = allVessels.filter(function (v) { return v.handset_active; }).length;
    if (countEl) countEl.textContent = allVessels.length + ' total · ' + activeCount + ' active';
    if (shown.length === 0) {
      el.innerHTML = '<p class="panel-stub-text">No users match this filter</p>';
      return;
    }
    el.innerHTML = '<table class="users-table">' +
      '<thead><tr><th>Name</th><th>Registered No.</th><th>Phone</th><th>Status</th><th>Sea</th><th>Last GPS Fix</th></tr></thead>' +
      '<tbody>' + shown.map(rowHtml).join('') + '</tbody></table>';
  }

  document.querySelectorAll('.users-filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.users-filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter') || 'all';
      render();
    });
  });

  fetch(API_BASE + '/api/ops/roster', {
    headers: { Accept: 'application/json', Authorization: 'Bearer ' + getToken() }
  })
    .then(function (res) {
      if (res.status === 401) {
        window.location.replace('login.html');
        throw new Error('Session expired');
      }
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    })
    .then(function (data) {
      allVessels = (data && data.vessels) || [];
      render();
    })
    .catch(function (err) {
      var el = document.getElementById('users-list');
      if (el) el.innerHTML = '<p class="panel-stub-text">Failed to load users: ' + escapeHtml(err.message) + '</p>';
    });
})();
