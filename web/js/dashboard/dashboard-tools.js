(function (ns) {
  'use strict';
  if (!ns.ready) return;
  var CURRENT_USER = ns.CURRENT_USER;
  var CURRENT_USER_COLOR = ns.CURRENT_USER_COLOR;
  var escapeHtml = ns.escapeHtml;
  var map = ns.map;
  var tileLayers = ns.tileLayers;
  var currentBase = ns.currentBase;
  var gatewayLayer = ns.gatewayLayer;
  var incidentLayer = ns.incidentLayer;
  var buoyLayer = ns.buoyLayer;
  var boundaryLayer = ns.boundaryLayer;
  var pinLayer = ns.pinLayer;
  var vesselLayer = ns.vesselLayer;
  var coverageLayer = ns.coverageLayer;
  var meshLayer = ns.meshLayer;
  var squallLayer = ns.squallLayer;
  var driftLayer = ns.driftLayer;
  var dangerZoneLayer = ns.dangerZoneLayer;
  var hotspotLayer = ns.hotspotLayer;
  var refreshDangerZones = ns.refreshDangerZones;

  // ===== PIN TOOL (local-only, no backend dependency) =====
  let pinModeActive = false;
  let panModeActive = true;
  const pinBtn = document.getElementById('rail-btn-pin');
  const panBtn  = document.getElementById('rail-btn-pan');
  const mapEl  = document.getElementById('map');

  const pinMarkers = {};


  function createPinIcon(color) {
    return L.divIcon({
      className: 'user-pin-marker',
      html: `<div class="user-pin-dot" style="background:${color}"></div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9],
      popupAnchor: [0, -12]
    });
  }

  function dropLocalPin(latlng) {
    const id = 'local-' + Date.now();
    const color = CURRENT_USER_COLOR;
    const createdAt = Date.now();
    const userName = (CURRENT_USER && CURRENT_USER.name) ? CURRENT_USER.name : 'User';
    const popupHtml =
      `<div class="popup-title">
        <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${color};vertical-align:middle;margin-right:6px;border:2px solid rgba(255,255,255,0.7);"></span>${escapeHtml(userName)}
      </div>
      <div class="popup-row"><span>Pinned</span><span>just now</span></div>
      <div class="popup-row"><span>Lat</span><span>${latlng.lat.toFixed(5)}</span></div>
      <div class="popup-row"><span>Lng</span><span>${latlng.lng.toFixed(5)}</span></div>
      <div class="pin-popup-footer" id="pin-footer-${id}">
        <button class="pin-delete-btn" data-pin-id="${id}" data-action="delete-init">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14H6L5 6"/>
            <path d="M10 11v6"/><path d="M14 11v6"/>
            <path d="M9 6V4h6v2"/>
          </svg>
          Delete
        </button>
      </div>`;

    const marker = L.marker([latlng.lat, latlng.lng], { icon: createPinIcon(color) });
    marker.bindPopup(popupHtml);

    marker.on('popupopen', function () {
      const container = marker.getPopup().getElement();
      if (!container) return;
      container.addEventListener('click', function handleLocalDelete(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const footer = container.querySelector(`#pin-footer-${id}`);
        if (btn.dataset.action === 'delete-init') {
          footer.innerHTML =
            `<div class="pin-confirm-row">
               <span class="pin-confirm-label">Delete this pin?</span>
               <button class="pin-confirm-yes" data-action="delete-confirm">Yes</button>
               <button class="pin-confirm-no"  data-action="delete-cancel">No</button>
             </div>`;
          marker.getPopup().update();
        }
        if (btn.dataset.action === 'delete-confirm') {
          pinLayer.removeLayer(marker);
          delete pinMarkers[id];
        }
        if (btn.dataset.action === 'delete-cancel') {
          footer.innerHTML =
            `<button class="pin-delete-btn" data-pin-id="${id}" data-action="delete-init">Delete</button>`;
          marker.getPopup().update();
        }
      });
    });

    pinLayer.addLayer(marker);
    pinMarkers[id] = marker;
    marker.openPopup();
    void createdAt;
    return marker;
  }

  function activatePinMode() {
    pinModeActive = true;
    pinBtn.classList.add('pin-mode-active');
    mapEl.classList.add('pin-mode');
    deactivatePanMode();
    if (activePanel) closePanel();
  }

  function deactivatePinMode() {
    pinModeActive = false;
    pinBtn.classList.remove('pin-mode-active');
    mapEl.classList.remove('pin-mode');
  }

  function activatePanMode() {
    panModeActive = true;
    panBtn.classList.add('active');
  }

  function deactivatePanMode() {
    panModeActive = false;
    panBtn.classList.remove('active');
  }


  // ===== MEASURE TOOL =====
  const MEASURE_COLOR   = '#2ecc71';
  const MEASURE_PREVIEW = 'rgba(46,204,113,0.55)';

  function haversineKm(a, b) {
    return map.distance(a, b) / 1000;
  }

  function fmtKm(km) { return km.toFixed(3) + ' km'; }

  let measureActive   = false;
  let measureFinished = false;
  const measurePts    = [];
  const measureLayer  = L.layerGroup().addTo(map);

  let mPolyline   = null;
  let mPreview    = null;
  let mTooltips   = [];
  let mVertices   = [];

  const measureBtn  = document.getElementById('rail-btn-measure');
  const measureHud  = document.getElementById('measure-hud');
  const hudTotal    = document.getElementById('measure-hud-total');
  const panelTotal  = document.getElementById('measure-total');
  const panelCount  = document.getElementById('measure-point-count');
  const btnFinish   = document.getElementById('btn-measure-finish');
  const btnClear    = document.getElementById('btn-measure-clear');

  let mDblClickGuard = false;

  function measureUpdateUI() {
    const n   = measurePts.length;
    let total = 0;
    for (let i = 1; i < n; i++) total += haversineKm(measurePts[i - 1], measurePts[i]);
    const fmt = fmtKm(total);

    panelTotal.textContent = fmt;
    hudTotal.textContent   = fmt;
    panelCount.textContent = n + (n === 1 ? ' pt' : ' pts');

    btnFinish.disabled = n < 2 || measureFinished;
    btnClear.disabled  = n === 0;
  }

  function measureAddVertexMarker(latlng, isFirst) {
    const icon = L.divIcon({
      className: '',
      html: `<div class="measure-vertex${isFirst ? ' measure-vertex-first' : ''}"></div>`,
      iconSize: [10, 10],
      iconAnchor: [5, 5]
    });
    const m = L.marker(latlng, { icon, interactive: false, zIndexOffset: 500 });
    measureLayer.addLayer(m);
    mVertices.push(m);
  }

  function measureAddSegmentLabel(a, b, distKm) {
    const mid = L.latLng((a.lat + b.lat) / 2, (a.lng + b.lng) / 2);
    const tt  = L.tooltip({
      permanent: true,
      direction: 'center',
      offset: [0, 0],
      className: 'measure-label',
      interactive: false
    })
      .setLatLng(mid)
      .setContent(fmtKm(distKm))
      .addTo(map);
    mTooltips.push(tt);
  }

  function measureRedrawPolyline() {
    if (mPolyline) { measureLayer.removeLayer(mPolyline); mPolyline = null; }
    if (measurePts.length < 2) return;
    mPolyline = L.polyline(measurePts, {
      color: MEASURE_COLOR,
      weight: 3,
      opacity: 0.9,
      dashArray: measureFinished ? null : '8 5',
      lineCap: 'round',
      lineJoin: 'round'
    });
    measureLayer.addLayer(mPolyline);
  }

  function measureClearLabels() {
    mTooltips.forEach(t => map.removeLayer(t));
    mTooltips = [];
  }

  function measureClearVertices() {
    mVertices.forEach(m => measureLayer.removeLayer(m));
    mVertices = [];
  }

  function measureRebuildLabels() {
    measureClearLabels();
    for (let i = 1; i < measurePts.length; i++) {
      measureAddSegmentLabel(measurePts[i - 1], measurePts[i], haversineKm(measurePts[i - 1], measurePts[i]));
    }
  }

  function measureAddPoint(latlng) {
    if (measureFinished) return;
    const isFirst = measurePts.length === 0;
    measurePts.push(latlng);
    measureAddVertexMarker(latlng, isFirst);
    if (measurePts.length >= 2) {
      measureRebuildLabels();
    }
    measureRedrawPolyline();
    measureUpdateUI();
  }

  function measureClearPreview() {
    if (mPreview) { measureLayer.removeLayer(mPreview); mPreview = null; }
  }

  function measureUpdatePreview(latlng) {
    if (!measureActive || measureFinished || measurePts.length === 0) { measureClearPreview(); return; }
    const last = measurePts[measurePts.length - 1];
    measureClearPreview();
    mPreview = L.polyline([last, latlng], {
      color: MEASURE_PREVIEW,
      weight: 2,
      dashArray: '5 6',
      interactive: false
    });
    measureLayer.addLayer(mPreview);
  }

  function measureClearAll() {
    measurePts.length = 0;
    measureFinished   = false;
    measureClearPreview();
    measureClearLabels();
    measureClearVertices();
    if (mPolyline) { measureLayer.removeLayer(mPolyline); mPolyline = null; }
    measureUpdateUI();
  }

  function measureFinish() {
    if (measurePts.length < 2 || measureFinished) return;
    measureFinished = true;
    measureClearPreview();
    measureRedrawPolyline();
    measureUpdateUI();
    map.off('mousemove', onMeasureMouseMove);
  }

  function activateMeasureMode() {
    measureActive = true;
    measureFinished = false;
    measureBtn.classList.add('measure-mode-active');
    mapEl.classList.add('measure-mode');
    measureHud.classList.add('visible');
    deactivatePanMode();
    map.on('mousemove', onMeasureMouseMove);
    measureUpdateUI();
  }

  function deactivateMeasureMode() {
    measureActive = false;
    measureBtn.classList.remove('measure-mode-active');
    mapEl.classList.remove('measure-mode');
    measureHud.classList.remove('visible');
    measureClearPreview();
    map.off('mousemove', onMeasureMouseMove);
  }

  function onMeasureMouseMove(e) {
    measureUpdatePreview(e.latlng);
  }

  btnFinish.addEventListener('click', measureFinish);
  btnClear.addEventListener('click', () => {
    measureClearAll();
    if (measureActive) {
      map.on('mousemove', onMeasureMouseMove);
    }
  });


  // ===== LAYER SWITCHER =====
  function switchLayer(name) {
    if (currentBase === name) return;
    map.removeLayer(tileLayers[currentBase]);
    if (currentBase === 'hybrid') map.removeLayer(tileLayers.hybridLabels);
    tileLayers[name].addTo(map);
    if (name === 'hybrid') tileLayers.hybridLabels.addTo(map);
    currentBase = name;
    document.querySelectorAll('.layer-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.layer === name);
    });
  }

  document.querySelectorAll('.layer-btn').forEach(btn => {
    btn.addEventListener('click', () => switchLayer(btn.dataset.layer));
  });


  // ===== RAIL PANEL SYSTEM =====
  const toolPanelCard  = document.getElementById('tool-panel-card');
  const toolPanelTitle = document.getElementById('tool-panel-title');
  const railBtns       = document.querySelectorAll('.rail-btn');
  const panelContents  = document.querySelectorAll('.rail-panel-content');
  const panelCloseBtns = document.querySelectorAll('.rail-panel-close');

  let activePanel = null;


  // ===== TOOLBOX SCROLL OVERFLOW =====
  (function initToolboxScroll() {
    var toolboxBody = document.querySelector('.toolbox-body');
    var toolboxCard = document.querySelector('.toolbox-card');
    if (!toolboxBody || !toolboxCard) return;

    function checkOverflow() {
      var hasOverflow = toolboxBody.scrollWidth > toolboxBody.clientWidth + 2;
      toolboxCard.classList.toggle('has-overflow', hasOverflow);
    }

    function updateFade() {
      var atEnd = toolboxBody.scrollLeft + toolboxBody.clientWidth >= toolboxBody.scrollWidth - 4;
      toolboxCard.classList.toggle('has-overflow', !atEnd && toolboxBody.scrollWidth > toolboxBody.clientWidth + 2);
    }

    toolboxBody.addEventListener('scroll', updateFade, { passive: true });
    toolboxBody.addEventListener('wheel', function (e) {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();
        toolboxBody.scrollLeft += e.deltaY;
      }
    }, { passive: false });
    window.addEventListener('resize', checkOverflow);
    checkOverflow();
  })();

  const PANEL_TITLES = { layers: 'Operational Layers', measure: 'Measure Distance', buoys: 'Buoy Network Health', advisories: 'Maritime Advisories', audit: 'Global Audit Log' };
  const RAIL_ACTIVE_PANELS = ['layers', 'buoys', 'advisories', 'audit'];

  function openPanel(panelId) {
    panelContents.forEach(el => el.classList.toggle('active', el.id === 'panel-' + panelId));
    railBtns.forEach(btn => {
      if (RAIL_ACTIVE_PANELS.indexOf(btn.dataset.panel) !== -1) {
        btn.classList.toggle('active', btn.dataset.panel === panelId);
      }
    });
    toolPanelTitle.textContent = PANEL_TITLES[panelId] || 'Tool Panel';
    toolPanelCard.classList.remove('collapsed');
    activePanel = panelId;
    if (panelId === 'advisories' && typeof ns.renderAdvisoryList === 'function') ns.renderAdvisoryList();
    if (panelId === 'audit' && typeof ns.renderAuditPanel === 'function') ns.renderAuditPanel();
  }

  function closePanel() {
    toolPanelCard.classList.add('collapsed');
    railBtns.forEach(btn => {
      if (RAIL_ACTIVE_PANELS.indexOf(btn.dataset.panel) !== -1) btn.classList.remove('active');
    });
    if (panModeActive) panBtn.classList.add('active');
    panelContents.forEach(el => el.classList.remove('active'));
    activePanel = null;
  }

  railBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const panelId = btn.dataset.panel;

      if (panelId === 'pan') {
        if (!panModeActive) {
          if (pinModeActive) { deactivatePinMode(); }
          if (measureActive) {
            deactivateMeasureMode();
            measureClearAll();
            if (activePanel === 'measure') closePanel();
          }
          activatePanMode();
        }
        return;
      }

      if (panelId === 'pin') {
        if (pinModeActive) {
          deactivatePinMode();
          activatePanMode();
        } else {
          if (measureActive) {
            deactivateMeasureMode();
            measureClearAll();
            if (activePanel === 'measure') closePanel();
          }
          activatePinMode();
        }
        return;
      }

      if (panelId === 'measure') {
        if (activePanel === 'measure') {
          closePanel();
          deactivateMeasureMode();
          measureClearAll();
          activatePanMode();
        } else {
          if (pinModeActive) { deactivatePinMode(); }
          openPanel('measure');
          activateMeasureMode();
        }
        return;
      }

      if (!panelId) return;

      if (activePanel === panelId) {
        closePanel();
      } else {
        openPanel(panelId);
      }
    });
  });

  panelCloseBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      if (activePanel === 'measure') { deactivateMeasureMode(); activatePanMode(); }
      closePanel();
    });
  });

  // Map click
  map.on('click', function (e) {
    if (mDblClickGuard) return;
    if (pinModeActive) {
      dropLocalPin(e.latlng);
      deactivatePinMode();
      activatePanMode();
    } else if (measureActive && !measureFinished) {
      measureAddPoint(e.latlng);
    } else if (activePanel && !measureActive) {
      closePanel();
    }
  });

  map.on('dblclick', function (e) {
    if (!measureActive || measureFinished) return;
    mDblClickGuard = true;
    setTimeout(() => { mDblClickGuard = false; }, 300);
    measureFinish();
    L.DomEvent.stopPropagation(e);
  });


  // ===== TOGGLE LAYERS =====
  function toggleLayer(checkboxId, getLayer) {
    const el = document.getElementById(checkboxId);
    if (!el) return;
    el.addEventListener('change', function () {
      var target = (typeof getLayer === 'function') ? getLayer() : getLayer;
      var layers = Array.isArray(target) ? target : [target];
      for (var i = 0; i < layers.length; i++) {
        var layer = layers[i];
        if (!layer) continue;
        if (this.checked) {
          if (typeof map.hasLayer === 'function' ? !map.hasLayer(layer) : true) {
            layer.addTo(map);
          }
        } else {
          if (typeof map.hasLayer === 'function' ? map.hasLayer(layer) : true) {
            map.removeLayer(layer);
          }
        }
      }
    });
  }

  toggleLayer('toggle-gateways',  gatewayLayer);
  toggleLayer('toggle-vessels',   vesselLayer);
  toggleLayer('toggle-incidents', incidentLayer);
  toggleLayer('toggle-danger-zones', dangerZoneLayer);
  toggleLayer('toggle-buoys',     buoyLayer);
  toggleLayer('toggle-coverage',  coverageLayer);
  toggleLayer('toggle-mesh',      meshLayer);
  toggleLayer('toggle-squall',    function () { return ns.aiSquallLayer || squallLayer; });
  toggleLayer('toggle-drift',     function () { return [ns.aiContoursLayer || driftLayer, ns.aiDrawLayer]; });
  toggleLayer('toggle-boundary',  boundaryLayer);
  toggleLayer('toggle-pins',      pinLayer);
  toggleLayer('toggle-hotspots', hotspotLayer);

  var dangerZoneRefresh = document.getElementById('danger-zone-refresh');
  if (dangerZoneRefresh) {
    dangerZoneRefresh.addEventListener('click', function () {
      refreshDangerZones();
    });
  }

  Object.defineProperties(ns, {
    pinModeActive: { get: function () { return pinModeActive; } },
    panModeActive: { get: function () { return panModeActive; } },
    measureActive: { get: function () { return measureActive; } },
    activePanel: { get: function () { return activePanel; } }
  });
  ns.activatePinMode = activatePinMode;
  ns.deactivatePinMode = deactivatePinMode;
  ns.activatePanMode = activatePanMode;
  ns.activateMeasureMode = activateMeasureMode;
  ns.deactivateMeasureMode = deactivateMeasureMode;
  ns.measureClearAll = measureClearAll;
  ns.openPanel = openPanel;
  ns.closePanel = closePanel;

})(window.AqOneDashboard = window.AqOneDashboard || {});
