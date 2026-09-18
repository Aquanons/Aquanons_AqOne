(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var showToast = ns.showToast;
  var activatePinMode = ns.activatePinMode;
  var deactivatePinMode = ns.deactivatePinMode;
  var activatePanMode = ns.activatePanMode;
  var measureClearAll = ns.measureClearAll;
  var activateMeasureMode = ns.activateMeasureMode;
  var deactivateMeasureMode = ns.deactivateMeasureMode;
  var openPanel = ns.openPanel;
  var closePanel = ns.closePanel;
  var sosDrawer = ns.sosDrawer;
  var closeSOSDrawer = ns.closeSOSDrawer;
  var updateStats = typeof ns.updateStats === 'function' ? ns.updateStats : function () {};
  var alertData = Array.isArray(ns.alertData) ? ns.alertData : [];

  function isEditable(el) {
    if (!el) return false;
    var tag = (el.tagName || '').toUpperCase();
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || !!el.isContentEditable;
  }

  // ===== KEYBOARD SHORTCUTS =====
  document.addEventListener('keydown', function (e) {
    var activeEl = document.activeElement;
    var inEditable = isEditable(activeEl);

    if (e.key === 'Escape') {
      // 1. Topmost dialogs / modals
      if (ns.ackOverlay && ns.ackOverlay.hidden === false) {
        if (typeof ns.closeAckModal === 'function') ns.closeAckModal();
        else ns.ackOverlay.hidden = true;
        e.preventDefault();
        return;
      }
      if (ns.emergencyOverlay && ns.emergencyOverlay.classList.contains('active')) {
        ns.closeEmergencyModal();
        e.preventDefault();
        return;
      }
      if (ns.advisoryOverlay && ns.advisoryOverlay.classList.contains('active')) {
        ns.closeAdvisoryModal();
        e.preventDefault();
        return;
      }
      if (ns.deleteOverlay && ns.deleteOverlay.classList.contains('active')) {
        ns.closeDeleteModal();
        e.preventDefault();
        return;
      }
      // 2. Case activity drawer
      if (ns.activityDrawer && ns.activityDrawer.classList.contains('open')) {
        if (typeof ns.closeActivityDrawer === 'function') ns.closeActivityDrawer();
        e.preventDefault();
        return;
      }
      // 3. SOS drawer
      if (sosDrawer && sosDrawer.classList.contains('open')) {
        closeSOSDrawer();
        e.preventDefault();
        return;
      }
      // 4. Pin / measure modes & panels
      if (ns.pinModeActive) { deactivatePinMode(); activatePanMode(); e.preventDefault(); return; }
      if (ns.measureActive) { deactivateMeasureMode(); measureClearAll(); closePanel(); activatePanMode(); e.preventDefault(); return; }
      if (ns.activePanel) { closePanel(); e.preventDefault(); return; }
      return;
    }

    if (inEditable) return;

    var hasOpenModal = (ns.ackOverlay && ns.ackOverlay.hidden === false) ||
      (ns.emergencyOverlay && ns.emergencyOverlay.classList.contains('active')) ||
      (ns.advisoryOverlay && ns.advisoryOverlay.classList.contains('active')) ||
      (ns.deleteOverlay && ns.deleteOverlay.classList.contains('active'));
    if (hasOpenModal) return;

    if (e.ctrlKey || e.metaKey || e.altKey) return;

    if (e.key === 'f') {
      var fsBtn = document.getElementById('btn-fullscreen');
      if (fsBtn) fsBtn.click();
    } else if (e.key === 'b') {
      if (ns.activePanel === 'layers') { closePanel(); } else { openPanel('layers'); }
    } else if (e.key === 'h') {
      if (!ns.panModeActive) {
        if (ns.pinModeActive) { deactivatePinMode(); }
        if (ns.measureActive) { deactivateMeasureMode(); measureClearAll(); if (ns.activePanel === 'measure') closePanel(); }
        activatePanMode();
      }
    } else if (e.key === 'p') {
      if (ns.pinModeActive) { deactivatePinMode(); activatePanMode(); } else {
        if (ns.measureActive) { deactivateMeasureMode(); measureClearAll(); if (ns.activePanel === 'measure') closePanel(); }
        activatePinMode();
      }
    } else if (e.key === 'm') {
      if (ns.measureActive) { deactivateMeasureMode(); measureClearAll(); closePanel(); activatePanMode(); }
      else { if (ns.pinModeActive) { deactivatePinMode(); } openPanel('measure'); activateMeasureMode(); }
    }
  });

  ns.isEditable = isEditable;

  updateStats();


  // ===== WEATHER =====
  var wcBody = document.getElementById('wc-body');
  const WConditions_INTERVAL_MS = 300000;
  const WEATHER_CACHE_KEY = 'aqone-live-weather-new-washington-v2';

  var SAFETY_THRESHOLDS = {
    safe:     { windMax: 20, waveMax: 1.0 },
    caution:  { windMax: 40, waveMax: 2.0 },
    advisory: { windMax: 60, waveMax: 3.0 }
  };

  var SAFETY_TIERS = {
    safe:     { label: 'MODEL: LOWER RISK',          cls: 'wc-safety-safe',     color: '#2ecc71' },
    caution:  { label: 'MODEL: CAUTION',             cls: 'wc-safety-caution',  color: '#f1c40f' },
    advisory: { label: 'MODEL: SMALL CRAFT CAUTION', cls: 'wc-safety-advisory', color: '#e67e22' },
    danger:   { label: 'MODEL: HIGH MARINE RISK',    cls: 'wc-safety-danger',   color: '#e74c3c' },
    unknown:  { label: 'CONDITIONS UNKNOWN',     cls: 'wc-safety-unknown',  color: '#7f8c8d' }
  };

  function classifySafety(windKmh, waveM, weatherCode) {
    var hasWind = typeof windKmh === 'number' && Number.isFinite(windKmh) && windKmh >= 0;
    var hasWave = typeof waveM === 'number' && Number.isFinite(waveM) && waveM >= 0;
    var isThunderstorm = typeof weatherCode === 'number' && weatherCode >= 95;
    var t = SAFETY_THRESHOLDS;

    var w = hasWind ? windKmh : 0;
    var h = hasWave ? waveM : 0;

    // Highest severity condition first
    if ((hasWind && w >= t.advisory.windMax) || (hasWave && h >= t.advisory.waveMax)) {
      return SAFETY_TIERS.danger;
    }
    if ((hasWind && w >= t.caution.windMax) || (hasWave && h >= t.caution.waveMax)) {
      return SAFETY_TIERS.advisory;
    }
    if ((hasWind && w >= t.safe.windMax) || (hasWave && h >= t.safe.waveMax) || isThunderstorm) {
      return SAFETY_TIERS.caution;
    }

    // If neither wind nor wave is complete, missing inputs cannot certify lower risk
    if (!hasWind || !hasWave) {
      return SAFETY_TIERS.unknown;
    }

    return SAFETY_TIERS.safe;
  }

  function degToCompass(deg) {
    var dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
    return dirs[Math.round(deg / 22.5) % 16];
  }

  var WMO_MAP = {
    0:  { label: 'Clear Sky',        cls: '' },
    1:  { label: 'Mainly Clear',     cls: '' },
    2:  { label: 'Partly Cloudy',    cls: '' },
    3:  { label: 'Overcast',         cls: 'wc-icon-cloud' },
    45: { label: 'Foggy',            cls: 'wc-icon-fog' },
    48: { label: 'Rime Fog',         cls: 'wc-icon-fog' },
    51: { label: 'Light Drizzle',    cls: 'wc-icon-rain' },
    53: { label: 'Moderate Drizzle', cls: 'wc-icon-rain' },
    55: { label: 'Dense Drizzle',    cls: 'wc-icon-rain' },
    56: { label: 'Light Freezing Drizzle', cls: 'wc-icon-rain' },
    57: { label: 'Dense Freezing Drizzle', cls: 'wc-icon-rain' },
    61: { label: 'Slight Rain',      cls: 'wc-icon-rain' },
    63: { label: 'Moderate Rain',    cls: 'wc-icon-rain' },
    65: { label: 'Heavy Rain',       cls: 'wc-icon-rain' },
    66: { label: 'Light Freezing Rain',  cls: 'wc-icon-rain' },
    67: { label: 'Heavy Freezing Rain',  cls: 'wc-icon-rain' },
    71: { label: 'Slight Snow',      cls: 'wc-icon-snow' },
    73: { label: 'Moderate Snow',    cls: 'wc-icon-snow' },
    75: { label: 'Heavy Snow',       cls: 'wc-icon-snow' },
    77: { label: 'Snow Grains',      cls: 'wc-icon-snow' },
    80: { label: 'Slight Rain Showers',  cls: 'wc-icon-rain' },
    81: { label: 'Moderate Rain Showers', cls: 'wc-icon-rain' },
    82: { label: 'Violent Rain Showers',  cls: 'wc-icon-rain' },
    85: { label: 'Slight Snow Showers',   cls: 'wc-icon-snow' },
    86: { label: 'Heavy Snow Showers',    cls: 'wc-icon-snow' },
    95: { label: 'Thunderstorm',     cls: 'wc-icon-storm' },
    96: { label: 'Thunderstorm with Hail', cls: 'wc-icon-storm' },
    99: { label: 'Thunderstorm with Heavy Hail', cls: 'wc-icon-storm' }
  };

  function wmoIcon(code) {
    var m = WMO_MAP[code];
    if (!m) return { svg: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>', cls: 'wc-icon-cloud' };
    var svg = '';
    if (m.cls === 'wc-icon-storm') {
      svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>';
    } else if (m.cls === 'wc-icon-rain') {
      svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/><path d="M8 18l-1 4"/><path d="M12 18l-1 4"/><path d="M16 18l-1 4"/></svg>';
    } else if (m.cls === 'wc-icon-snow') {
      svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/><path d="M8 18v2"/><path d="M12 18v2"/><path d="M16 18v2"/></svg>';
    } else if (m.cls === 'wc-icon-fog') {
      svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>';
    } else {
      svg = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
    }
    return { svg: svg, cls: m.cls };
  }

  function safetyBadgeHTML(tier) {
    return '<div class="wc-safety-badge ' + tier.cls + '" style="border-color:' + tier.color + '40;color:' + tier.color + ';">' +
      '<span class="wc-safety-dot" style="background:' + tier.color + ';"></span>' +
      tier.label +
    '</div>';
  }

  function parseStrictFinite(val) {
    if (typeof val === 'number') {
      return Number.isFinite(val) ? val : null;
    }
    if (typeof val === 'string' && val.trim() !== '') {
      var n = Number(val);
      return Number.isFinite(n) ? n : null;
    }
    return null;
  }

  function parseStrictNonNegative(val) {
    var n = parseStrictFinite(val);
    return (n !== null && n >= 0) ? n : null;
  }

  function renderWeatherCard(data, marineData, meta) {
    var current = (data && data.current) || {};
    var marineCurrent = (marineData && marineData.current) || {};
    var code = parseStrictFinite(current.weather_code);
    var icon = wmoIcon(code);
    var rawTemp = parseStrictFinite(current.temperature_2m);
    var temp = rawTemp !== null ? Math.round(rawTemp) : '--';
    var rawFeels = parseStrictFinite(current.apparent_temperature);
    var feelsLike = rawFeels !== null ? Math.round(rawFeels) : '--';
    var windKmh = parseStrictNonNegative(current.wind_speed_10m);
    var gustKmh = parseStrictNonNegative(current.wind_gusts_10m);
    var maxWind = (windKmh !== null && gustKmh !== null) ? Math.max(windKmh, gustKmh) : (windKmh !== null ? windKmh : gustKmh);
    var rawDir = parseStrictFinite(current.wind_direction_10m);
    var windDir = rawDir !== null ? degToCompass(rawDir) : '';
    var waveM = parseStrictNonNegative(marineCurrent.wave_height);
    var wavePeriod = parseStrictNonNegative(marineCurrent.wave_period);
    var pressure = parseStrictNonNegative(current.pressure_msl);
    var seaLevel = parseStrictFinite(marineCurrent.sea_level_height_msl);
    var condText = (code !== null && WMO_MAP[code]) ? WMO_MAP[code].label : 'Unknown';
    var safety = classifySafety(maxWind, waveM, code);
    var monitorAlerts = meta && Array.isArray(meta.alerts) ? meta.alerts : [];

    var WEATHER_MAX_OBS_AGE_MS = 3 * 3600 * 1000;
    var WEATHER_FETCH_STALE_MS = 15 * 60 * 1000;
    var stale = Boolean(meta && meta.stale);
    var nowMs = (meta && typeof meta.nowMs === 'number') ? meta.nowMs : Date.now();

    function isObsFresh(t) {
      if (!t) return false;
      var ms = new Date(t).getTime();
      if (!isFinite(ms)) return false;
      var ageMs = nowMs - ms;
      return isFinite(ageMs) && ageMs <= WEATHER_MAX_OBS_AGE_MS && ageMs >= -600000;
    }

    if (!stale) {
      if (!isObsFresh(current.time) || !isObsFresh(marineCurrent.time)) {
        stale = true;
      }
    }

    if (!stale && meta && meta.fetchedAt) {
      var fetchAgeMs = nowMs - new Date(meta.fetchedAt).getTime();
      if (!isFinite(fetchAgeMs) || fetchAgeMs > WEATHER_FETCH_STALE_MS) {
        stale = true;
      }
    }

    if (stale && safety.cls === 'wc-safety-safe') {
      safety = SAFETY_TIERS.unknown;
    }
    var monitorClass = monitorAlerts.length ? 'wc-monitor-danger' : stale ? 'wc-monitor-stale' : 'wc-monitor-safe';
    var monitorText = monitorAlerts.length ?
      monitorAlerts.length + ' incoming severe-weather risk' + (monitorAlerts.length === 1 ? '' : 's') + ' detected' :
      stale ? 'Live monitor paused \u00b7 showing last-known conditions' :
      (waveM === null || windKmh === null) ? 'Monitor active \u00b7 partial observation data' :
      '72-hour monitor \u00b7 no severe thresholds detected';
    var observedAt = current.time ? new Date(current.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';

    var windVal = '\u2014';
    if (windKmh !== null && gustKmh !== null) {
      windVal = windKmh.toFixed(1) + ' / ' + gustKmh.toFixed(1) + ' km/h' + (windDir ? ' ' + windDir : '');
    } else if (windKmh !== null) {
      windVal = windKmh.toFixed(1) + ' km/h' + (windDir ? ' ' + windDir : '');
    } else if (gustKmh !== null) {
      windVal = 'Gusts ' + gustKmh.toFixed(1) + ' km/h' + (windDir ? ' ' + windDir : '');
    }

    var waveVal = '\u2014';
    if (waveM !== null && wavePeriod !== null) {
      waveVal = waveM.toFixed(2) + ' m / ' + wavePeriod.toFixed(1) + ' s';
    } else if (waveM !== null) {
      waveVal = waveM.toFixed(2) + ' m / \u2014';
    } else if (wavePeriod !== null) {
      waveVal = '\u2014 / ' + wavePeriod.toFixed(1) + ' s';
    }

    var rawHum = parseStrictFinite(current.relative_humidity_2m);
    var humidityVal = (rawHum !== null && rawHum >= 0) ? rawHum + '%' : '\u2014';
    var rawRain = parseStrictNonNegative(current.precipitation);
    var rainVal = rawRain !== null ? rawRain.toFixed(1) + ' mm' : '\u2014';

    wcBody.innerHTML =
      safetyBadgeHTML(safety) +
      '<div class="wc-live-strip"><span class="wc-live-dot ' + (stale ? 'is-stale' : '') + '"></span>' +
        (stale ? 'LAST KNOWN' : 'LIVE MODEL') + ' \u00b7 Updated ' + observedAt + '</div>' +
      '<div class="wc-main">' +
        '<div class="wc-icon ' + icon.cls + '">' + icon.svg + '</div>' +
        '<div class="wc-temp-group">' +
          '<div class="wc-temp">' + temp + '&deg;C</div>' +
          '<div class="wc-condition">' + condText + ' \u00b7 Feels ' + feelsLike + '&deg;</div>' +
        '</div>' +
      '</div>' +
      '<div class="wc-details">' +
        '<div class="wc-detail">' +
          '<span>Wind</span><span class="wc-detail-val">' + windVal + '</span>' +
        '</div>' +
        '<div class="wc-detail">' +
          '<span>Waves</span><span class="wc-detail-val">' + waveVal + '</span>' +
        '</div>' +
        '<div class="wc-detail">' +
          '<span>Humidity</span><span class="wc-detail-val">' + humidityVal + '</span>' +
        '</div>' +
        '<div class="wc-detail">' +
          '<span>Pressure</span><span class="wc-detail-val">' + (pressure !== null ? pressure.toFixed(0) + ' hPa' : '\u2014') + '</span>' +
        '</div>' +
        '<div class="wc-detail">' +
          '<span>Sea level</span><span class="wc-detail-val">' + (seaLevel !== null ? seaLevel.toFixed(2) + ' m MSL' : '\u2014') + '</span>' +
        '</div>' +
        '<div class="wc-detail">' +
          '<span>Rain now</span><span class="wc-detail-val">' + rainVal + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="wc-forecast-monitor ' + monitorClass + '">' + monitorText + '</div>' +
      '<div class="wc-source-row"><span>Open-Meteo weather + marine</span>' +
        '<a href="https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin" target="_blank" rel="noopener">Verify PAGASA</a></div>';
  }

  function renderForecast(daily) {
    var body = document.getElementById('forecast-body');
    var days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    var html = '<div class="forecast-grid" style="display:flex;gap:4px;">';
    for (var i = 0; i < daily.time.length; i++) {
      var d = new Date(daily.time[i] + 'T12:00:00');
      var dayName = days[d.getDay()];
      var icon = wmoIcon(daily.weather_code[i]);
      var max = Math.round(daily.temperature_2m_max[i]);
      var min = Math.round(daily.temperature_2m_min[i]);
      html += '<div class="forecast-day" style="flex:1;text-align:center;padding:6px 2px;background:rgba(255,255,255,0.04);border-radius:6px;">' +
        '<div style="font-size:10px;font-weight:700;color:var(--text-secondary);margin-bottom:4px;">' + dayName + '</div>' +
        '<div class="' + icon.cls + '" style="color:var(--text-dim);margin-bottom:4px;">' + icon.svg + '</div>' +
        '<div style="font-size:11px;font-weight:700;">' + max + '&deg;</div>' +
        '<div style="font-size:10px;color:var(--text-dim);">' + min + '&deg;</div>' +
      '</div>';
    }
    html += '</div>';
    body.innerHTML = html;
  }

  function renderRainfall(daily) {
    var body = document.getElementById('rainfall-body');
    var days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    var html = '<div class="rainfall-grid" style="display:flex;gap:6px;align-items:flex-end;">';
    var maxPrecip = 1;
    for (var i = 0; i < daily.time.length; i++) {
      if (daily.precipitation_sum[i] > maxPrecip) maxPrecip = daily.precipitation_sum[i];
    }
    for (var i = 0; i < daily.time.length; i++) {
      var d = new Date(daily.time[i] + 'T12:00:00');
      var dayName = days[d.getDay()];
      var precip = daily.precipitation_sum[i] || 0;
      var barH = Math.max(4, (precip / maxPrecip) * 50);
      html += '<div class="rainfall-day" style="flex:1;text-align:center;">' +
        '<div style="font-size:10px;color:var(--text-secondary);margin-bottom:2px;">' + precip.toFixed(1) + '</div>' +
        '<div style="height:54px;display:flex;align-items:flex-end;justify-content:center;">' +
          '<div style="width:100%;max-width:20px;height:' + barH + 'px;background:var(--primary);border-radius:3px 3px 0 0;transition:height 0.3s;"></div>' +
        '</div>' +
        '<div style="font-size:9px;font-weight:600;color:var(--text-dim);margin-top:2px;">' + dayName + '</div>' +
      '</div>';
    }
    html += '</div>';
    body.innerHTML = html;
  }

  function fetchLiveJson(url) {
    var controller = new AbortController();
    var timeout = setTimeout(function () { controller.abort(); }, 25000);
    return fetch(url, { signal: controller.signal })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .finally(function () { clearTimeout(timeout); });
  }

  function readWeatherCache() {
    try {
      var cached = JSON.parse(localStorage.getItem(WEATHER_CACHE_KEY));
      return cached && cached.weather ? cached : null;
    } catch (error) {
      return null;
    }
  }

  function writeWeatherCache(snapshot) {
    try {
      localStorage.setItem(WEATHER_CACHE_KEY, JSON.stringify(snapshot));
    } catch (error) {
      console.warn('[AqOne] Could not cache live weather conditions');
    }
  }

  function forecastTimeLabel(value) {
    var time = new Date(value);
    return time.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function buildForecastAlerts(weatherData, marineData) {
    var weather = weatherData.hourly || {};
    var marine = marineData && marineData.hourly ? marineData.hourly : {};
    var marineIndexes = {};
    (marine.time || []).forEach(function (time, index) { marineIndexes[time] = index; });
    var stormCandidate = null;
    var surgeCandidate = null;

    (weather.time || []).slice(0, 72).some(function (time, index) {
      var gust = Number(weather.wind_gusts_10m[index] || 0);
      var wind = Number(weather.wind_speed_10m[index] || 0);
      var direction = Number(weather.wind_direction_10m[index] || 0);
      var rain = Number(weather.precipitation[index] || 0);
      var pressure = Number(weather.pressure_msl[index] || 1013);
      var code = Number(weather.weather_code[index] || 0);
      var marineIndex = marineIndexes[time];
      var wave = marineIndex == null ? 0 : Number(marine.wave_height[marineIndex] || 0);
      var seaLevel = marineIndex == null ? 0 : Number(marine.sea_level_height_msl[marineIndex] || 0);
      var invertedBarometer = marineIndex == null ? 0 : Number(marine.invert_barometer_height[marineIndex] || 0);
      var onshoreWind = direction >= 315 || direction <= 90;

      if (!stormCandidate && (gust >= 89 || (gust >= 63 && pressure <= 1000) || (code >= 95 && gust >= 40))) {
        stormCandidate = { time: time, gust: gust, wind: wind, rain: rain, pressure: pressure, code: code };
      }
      if (!surgeCandidate && onshoreWind && wave >= 1.8 && gust >= 40 &&
          (seaLevel >= 0.55 || invertedBarometer >= 0.12 || pressure <= 1000)) {
        surgeCandidate = { time: time, gust: gust, wave: wave, seaLevel: seaLevel, pressure: pressure };
      }
      return Boolean(stormCandidate && surgeCandidate);
    });

    var alerts = [];
    if (stormCandidate) {
      alerts.push({
        type: 'forecast-storm',
        desc: 'Forecast model flag: possible incoming tropical-cyclone or severe-storm conditions. Gusts ' +
          stormCandidate.gust.toFixed(0) + ' km/h, pressure ' + stormCandidate.pressure.toFixed(0) +
          ' hPa. Verify the latest PAGASA bulletin.',
        time: 'Forecast ' + forecastTimeLabel(stormCandidate.time),
        lat: 11.6845,
        lng: 122.4475,
        status: 'active',
        vesselId: null,
        source: 'forecast-monitor'
      });
    }
    if (surgeCandidate) {
      alerts.push({
        type: 'storm-surge',
        desc: 'Forecast model flag: possible storm-surge risk near New Washington. Sea level ' +
          surgeCandidate.seaLevel.toFixed(2) + ' m MSL, waves ' + surgeCandidate.wave.toFixed(1) +
          ' m, gusts ' + surgeCandidate.gust.toFixed(0) + ' km/h. Verify PAGASA storm-surge warnings.',
        time: 'Forecast ' + forecastTimeLabel(surgeCandidate.time),
        lat: 11.6845,
        lng: 122.4475,
        status: 'active',
        vesselId: null,
        source: 'forecast-monitor'
      });
    }
    return alerts;
  }

  function replaceForecastAlerts(forecastAlerts) {
    var list = Array.isArray(alertData) ? alertData : [];
    for (var index = list.length - 1; index >= 0; index--) {
      if (list[index].source === 'forecast-monitor') list.splice(index, 1);
    }
    for (var alertIndex = forecastAlerts.length - 1; alertIndex >= 0; alertIndex--) {
      list.unshift(forecastAlerts[alertIndex]);
    }
    if (typeof ns.syncAlertIndicators === 'function') {
      ns.syncAlertIndicators();
    }

    var signature = forecastAlerts.map(function (alert) { return alert.type + ':' + alert.time; }).join('|');
    var previousSignature = localStorage.getItem('aqone-forecast-alert-signature') || '';
    if (signature && signature !== previousSignature && typeof showToast === 'function') {
      showToast('Proactive Weather Alert', forecastAlerts[0].desc, true);
    }
    localStorage.setItem('aqone-forecast-alert-signature', signature);
  }

  function displayWeatherSnapshot(snapshot, stale, alerts) {
    renderWeatherCard(snapshot.weather, snapshot.marine, {
      stale: stale,
      alerts: alerts || [],
      fetchedAt: snapshot.fetchedAt
    });
    if (snapshot.weather && snapshot.weather.daily) {
      renderForecast(snapshot.weather.daily);
      renderRainfall(snapshot.weather.daily);
    }
  }

  function fetchWeatherData() {
    var url = 'https://api.open-meteo.com/v1/forecast?latitude=11.6845&longitude=122.4475' +
      '&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m' +
      '&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,weather_code,pressure_msl' +
      '&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum&forecast_days=7&forecast_hours=72&timezone=Asia%2FManila';
    var marineUrl = 'https://marine-api.open-meteo.com/v1/marine?latitude=11.6845&longitude=122.4475' +
      '&current=wave_height,wave_period,sea_level_height_msl' +
      '&hourly=wave_height,wave_period,sea_level_height_msl,invert_barometer_height&forecast_hours=72&timezone=Asia%2FManila';

    Promise.allSettled([fetchLiveJson(url), fetchLiveJson(marineUrl)])
      .then(function (results) {
        if (results[0].status !== 'fulfilled') throw results[0].reason;
        var snapshot = {
          weather: results[0].value,
          marine: results[1].status === 'fulfilled' ? results[1].value : null,
          fetchedAt: new Date().toISOString()
        };
        var forecastAlerts = buildForecastAlerts(snapshot.weather, snapshot.marine);
        writeWeatherCache(snapshot);
        replaceForecastAlerts(forecastAlerts);
        displayWeatherSnapshot(snapshot, false, forecastAlerts);
      })
      .catch(function (error) {
        var cached = readWeatherCache();
        if (cached) {
          var list = Array.isArray(alertData) ? alertData : [];
          var existingAlerts = list.filter(function (alert) { return alert.source === 'forecast-monitor'; });
          displayWeatherSnapshot(cached, true, existingAlerts);
        } else {
          wcBody.innerHTML = '<div class="wc-error">Live weather unavailable. Check connection and PAGASA advisories.</div>';
          document.getElementById('forecast-body').innerHTML = '<p class="panel-stub-text">Forecast data unavailable</p>';
          document.getElementById('rainfall-body').innerHTML = '<p class="panel-stub-text">Rainfall data unavailable</p>';
        }
        console.warn('[AqOne] Live weather monitor unavailable:', error.message);
      });
  }

  fetchWeatherData();
  setInterval(fetchWeatherData, WConditions_INTERVAL_MS);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) fetchWeatherData();
  });

  ns.classifySafety = classifySafety;
  ns.renderWeatherCard = renderWeatherCard;

})(window.AqOneDashboard = window.AqOneDashboard || {});
