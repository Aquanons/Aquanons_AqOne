(function (ns) {
  'use strict';
  if (!ns.ready) return;

  // ===== STATS PANEL =====
  const statsWidget = document.getElementById('stats-widget');
  const statsMinimizeBtn = document.getElementById('stats-minimize');
  const statsBody = document.getElementById('stats-body');
  let statsMinimized = false;

  if (statsMinimizeBtn) {
    statsMinimizeBtn.addEventListener('click', () => {
      statsMinimized = !statsMinimized;
      if (statsWidget) statsWidget.classList.toggle('minimized', statsMinimized);
      statsMinimizeBtn.innerHTML = statsMinimized ? '+' : '&minus;';
    });
  }

  // Active alerts card click
  const statAlertsCard = document.querySelector('.stat-card.stat-alerts');
  if (statAlertsCard) {
    statAlertsCard.style.cursor = 'pointer';
    statAlertsCard.addEventListener('click', function() {
      statsTabs.forEach(t => t.classList.remove('active'));
      tabContents.forEach(tc => tc.classList.remove('active'));
      const alertsTab = document.querySelector('.stats-tab[data-tab="alerts"]');
      const alertsTabContent = document.getElementById('tab-alerts');
      if (alertsTab) alertsTab.classList.add('active');
      if (alertsTabContent) alertsTabContent.classList.add('active');
      if (statsMinimized && statsWidget) { statsMinimized = false; statsWidget.classList.remove('minimized'); if (statsMinimizeBtn) statsMinimizeBtn.innerHTML = '&minus;'; }
    });
  }


  // ===== LEGEND =====
  const legendCard = document.querySelector('.map-legend');
  const legendToggle = document.getElementById('legend-toggle');
  let legendCollapsed = false;

  if (legendToggle) {
    legendToggle.addEventListener('click', () => {
      legendCollapsed = !legendCollapsed;
      if (legendCard) legendCard.classList.toggle('collapsed', legendCollapsed);
      legendToggle.innerHTML = legendCollapsed ? '+' : '&minus;';
    });
  }


  // ===== TAB SWITCHING =====
  const statsTabs = document.querySelectorAll('.stats-tab');
  const tabContents = document.querySelectorAll('.tab-content');

  statsTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      statsTabs.forEach(t => t.classList.remove('active'));
      tabContents.forEach(tc => tc.classList.remove('active'));
      tab.classList.add('active');
      const targetContent = document.getElementById('tab-' + tab.dataset.tab);
      if (targetContent) targetContent.classList.add('active');
    });
  });


})(window.AqOneDashboard = window.AqOneDashboard || {});
