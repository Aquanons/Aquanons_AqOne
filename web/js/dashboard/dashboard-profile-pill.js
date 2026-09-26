(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var initialBuoys = ns.initialBuoys;
  var incidents = ns.incidents;
  var map = ns.map;
  var showToast = ns.showToast;
  var btnFinish = ns.btnFinish;
  var btnClear = ns.btnClear;

  // ===== USER PROFILE PILL =====
  var userProfilePill = document.getElementById('user-profile');
  if (userProfilePill) {
    userProfilePill.style.cursor = 'pointer';
    userProfilePill.addEventListener('click', function () {
      window.location.href = 'Systemprofile.html';
    });
  }

  // ===== EXIT LOADING =====
  function hideLoadingOverlay() {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(hideLoadingOverlay, 300);
  } else {
    window.addEventListener('load', function () {
      setTimeout(hideLoadingOverlay, 300);
    });
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(hideLoadingOverlay, 300);
    });
  }
  setTimeout(hideLoadingOverlay, 1500);


  // ===== THEME TOGGLE (shared with profile.html) =====
  // Reads BOTH storage keys used by profile.js ('aqone_dark_mode') and
  // the dashboard's own key ('aqone-theme') so dark mode persists across pages.
  (function () {
    var STORAGE_KEY = 'aqone-theme';
    var PROFILE_KEY = 'aqone_dark_mode';
    var root = document.documentElement;

    function applyTheme(theme) {
      if (theme === 'dark') {
        root.setAttribute('data-theme', 'dark');
      } else {
        root.removeAttribute('data-theme');
      }
      var darkToggle = document.getElementById('pref-dark-toggle');
      if (darkToggle) darkToggle.checked = theme === 'dark';
    }

    function resolveTheme() {
      var ownKey = localStorage.getItem(STORAGE_KEY);
      if (ownKey) return ownKey;
      var profileDark = localStorage.getItem(PROFILE_KEY);
      if (profileDark === 'true') return 'dark';
      return 'light';
    }

    applyTheme(resolveTheme());

    window.addEventListener('storage', function (e) {
      if (e.key === PROFILE_KEY) {
        var next = e.newValue === 'true' ? 'dark' : 'light';
        applyTheme(next);
        localStorage.setItem(STORAGE_KEY, next);
      }
    });

    var themeBtn = document.getElementById('btn-theme');
    if (themeBtn) {
      themeBtn.addEventListener('click', function () {
        var isDark = root.getAttribute('data-theme') === 'dark';
        var next = isDark ? 'light' : 'dark';
        applyTheme(next);
        localStorage.setItem(STORAGE_KEY, next);
        localStorage.setItem(PROFILE_KEY, next === 'dark' ? 'true' : 'false');
      });
    }

    var prefDarkToggle = document.getElementById('pref-dark-toggle');
    if (prefDarkToggle) {
      prefDarkToggle.addEventListener('change', function () {
        var next = prefDarkToggle.checked ? 'dark' : 'light';
        applyTheme(next);
        localStorage.setItem(STORAGE_KEY, next);
        localStorage.setItem(PROFILE_KEY, next === 'dark' ? 'true' : 'false');
      });
    }
  })();


  // ===== LANGUAGE TRANSLATIONS (EN / AKL) =====
  (function () {
    var DASHBOARD_TRANSLATIONS = {
      en: {
        subTitle: "SOS Operations Console",
        layerStreets: "Streets",
        layerSatellite: "Satellite",
        layerHybrid: "Hybrid",
        searchPlaceholder: "Search vessels, zones, coordinates...",
        userName: "New Washington, Aklan<br>MDRRMO Duty Officer",
        railLayers: "Layers",
        railPan: "Pan",
        railPin: "Pin",
        railMeasure: "Measure",
        railBuoys: "BUOYS",
        railEmergency: "EMERGENCY",
        railAdvisories: "Advisories",
        lblIncidents: "Incident Reports",
        lblBuoyStations: "Buoy Stations",
        lblUserPins: "User Pins",
        lblCoverage: "Buoy Coverage Zones",
        lblMesh: "Mesh Network",
        btnExport: "Export Map Snapshot",
        btnCenterAklan: "Center on Aklan",
        measureHint: "Click the map to add points. Double-click to finish.",
        btnFinish: "Finish",
        btnClear: "Clear",
        hdrBuoyMonitor: "Buoy Health Monitor",
        hdrAdvisories: "Maritime Advisories",
        subAdvisories: "Create and manage official government advisories.",
        btnCreateAdv: "Create Advisory",
        wcTitle: "Current Conditions",
        hdrSeaStatus: "Sea Condition Status",
        btnSeaSafe: "Safe to Go Out",
        btnSeaCaution: "Caution — Check Advisories",
        btnSeaDanger: "Not Advised",
        lblReason: "Reason (optional)",
        phReason: "e.g. Small craft advisory in effect...",
        btnSetStatus: "Set Status",
        hdrForecast: "7-Day Forecast",
        stubForecast: "Forecast data coming soon",
        hdrRainfall: "Rainfall Timeline",
        stubRainfall: "Rainfall data coming soon",
        emTitle: "Emergency Contacts",
        emSubtitle: "Quick access for MDRRMO responders",
      },
      akl: {
        subTitle: "SOS Operations Console",
        layerStreets: "Mga Dalan",
        layerSatellite: "Satélite",
        layerHybrid: "Pagsagol",
        searchPlaceholder: "Mag-sapsap it sakayan, rehiyon, coordinates...",
        userName: "New Washington, Aklan<br>Tagadumala it MDRRMO",
        railLayers: "Mga Han-ay",
        railPan: "I-duhol",
        railPin: "Tandaan",
        railMeasure: "Sukdon",
        railBuoys: "MGA BUOYS",
        railEmergency: "EMERHENSIYA",
        railAdvisories: "Mga Pasidaan",
        lblIncidents: "Ulat it Insidente",
        lblBuoyStations: "Estasyon it Buoy",
        lblUserPins: "Mga Tanda sang Tawo",
        lblCoverage: "Rehiyon sang Sakop it Buoy",
        lblMesh: "Network sa Mesh",
        btnExport: "I-export ang Datos sang Mapa",
        btnCenterAklan: "I-sentro sa Aklan",
        measureHint: "I-klick ang mapa para magdugang it punto. Double-click para matapos.",
        btnFinish: "Tapuson",
        btnClear: "Panason",
        hdrBuoyMonitor: "Kauswagan sang Buoy",
        hdrAdvisories: "Mga Pasidaan sa Baybayon",
        subAdvisories: "Maghimo ag magdumala sang opisyal nga mga pasidaan sang gobyerno.",
        btnCreateAdv: "Maghimo it Pasidaan",
        wcTitle: "Kasamtangan nga Panahon",
        hdrSeaStatus: "Sitwasyon sa Baybayon",
        btnSeaSafe: "Ewas nga Maglayag",
        btnSeaCaution: "Maghalong — Basaha ang Pasidaan",
        btnSeaDanger: "Indi Ginarekomendar",
        lblReason: "Rason (opsyonal)",
        phReason: "hal. Pasidaan sa gamay nga sakayan...",
        btnSetStatus: "I-set ang Sitwasyon",
        hdrForecast: "Pasidaan sa 7-Ka Adlaw",
        stubForecast: "Maga-abot pa ang datos sa panahon",
        hdrRainfall: "Oras sang Ulan",
        stubRainfall: "Maga-abot pa ang datos sang ulan",
        emTitle: "Mga Kontaktuhon sa Emerhensiya",
        emSubtitle: "Mabilis nga pagkuha para sa mga tagatubag sang MDRRMO",
      }
    };

    function applyLanguage(lang) {
      if (lang !== 'akl') lang = 'en';
      localStorage.setItem('aqone_lang', lang);
      var dict = DASHBOARD_TRANSLATIONS[lang];

      var btnEn = document.getElementById('dash-lang-en');
      var btnAkl = document.getElementById('dash-lang-akl');
      if (btnEn && btnAkl) {
        if (lang === 'akl') {
          btnEn.classList.remove('active');
          btnAkl.classList.add('active');
        } else {
          btnAkl.classList.remove('active');
          btnEn.classList.add('active');
        }
      }

      var setText = function (selector, key) {
        var el = document.querySelector(selector);
        if (el && dict[key]) el.innerHTML = dict[key];
      };

      setText('.top-subtitle', 'subTitle');
      setText('[data-layer="streets"] span', 'layerStreets');
      setText('[data-layer="satellite"] span', 'layerSatellite');
      setText('[data-layer="hybrid"] span', 'layerHybrid');

      var searchInput = document.querySelector('.search-input');
      if (searchInput && dict.searchPlaceholder) searchInput.placeholder = dict.searchPlaceholder;

      setText('.user-name', 'userName');
      setText('#rail-btn-layers .rail-label', 'railLayers');
      setText('#rail-btn-pan .rail-label', 'railPan');
      setText('#rail-btn-pin .rail-label', 'railPin');
      setText('#rail-btn-measure .rail-label', 'railMeasure');
      setText('#rail-btn-buoy .rail-label', 'railBuoys');
      setText('#btn-emergency .rail-label', 'railEmergency');
      setText('#rail-btn-advisories .rail-label', 'railAdvisories');

      setText('#toggle-incidents + .toggle-label', 'lblIncidents');
      setText('#toggle-buoys + .toggle-label', 'lblBuoyStations');
      setText('#toggle-pins + .toggle-label', 'lblUserPins');
      setText('#toggle-coverage + .toggle-label', 'lblCoverage');
      setText('#toggle-mesh + .toggle-label', 'lblMesh');

      setText('#btn-export', 'btnExport');
      setText('#btn-center-aklan', 'btnCenterAklan');
      setText('.measure-hint', 'measureHint');
      setText('#btn-measure-finish', 'btnFinish');
      setText('#btn-measure-clear', 'btnClear');

      setText('.buoy-drawer-title', 'hdrBuoyMonitor');
      setText('.advisory-drawer-title', 'hdrAdvisories');
      setText('.advisory-drawer-desc', 'subAdvisories');
      setText('#btn-create-advisory', 'btnCreateAdv');

      setText('.wc-title', 'wcTitle');
      setText('#sea-condition-card .panel-card-header span', 'hdrSeaStatus');
      setText('.sea-condition-btn.btn-safe', 'btnSeaSafe');
      setText('.sea-condition-btn.btn-caution', 'btnSeaCaution');
      setText('.sea-condition-btn.btn-danger', 'btnSeaDanger');
      setText('label[for="sea-condition-reason"]', 'lblReason');
      var seaInput = document.getElementById('sea-condition-reason');
      if (seaInput && dict.phReason) seaInput.placeholder = dict.phReason;
      setText('#sea-condition-set-btn', 'btnSetStatus');

      setText('#forecast-card .panel-card-header span', 'hdrForecast');
      setText('#forecast-body .panel-stub-text', 'stubForecast');
      setText('#rainfall-card .panel-card-header span', 'hdrRainfall');
      setText('#rainfall-body .panel-stub-text', 'stubRainfall');
      setText('.emergency-modal-title', 'emTitle');
      setText('.emergency-modal-subtitle', 'emSubtitle');
    }

    var btnEn = document.getElementById('dash-lang-en');
    var btnAkl = document.getElementById('dash-lang-akl');
    if (btnEn) btnEn.addEventListener('click', function () { applyLanguage('en'); });
    if (btnAkl) btnAkl.addEventListener('click', function () { applyLanguage('akl'); });

    var prefLangSelect = document.getElementById('pref-lang-select');
    if (prefLangSelect) {
      prefLangSelect.addEventListener('change', function (e) {
        applyLanguage(e.target.value);
      });
    }

    window.addEventListener('storage', function (e) {
      if (e.key === 'aqone_lang') applyLanguage(e.newValue);
    });

    var savedLang = localStorage.getItem('aqone_lang') || 'en';
    applyLanguage(savedLang);
  })();

})(window.AqOneDashboard = window.AqOneDashboard || {});
