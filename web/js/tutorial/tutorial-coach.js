// The dashboard tutorial's coach (docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md):
// the banner and watermark that say this is not live, the lesson steps, and
// the lesson menu. Loaded last in dashboard.html; does nothing in live mode.
(function (ns) {
  'use strict';
  var tutorial = window.AqOneTutorial;
  var lessons = window.AqOneTutorialLessons;
  var sourceApi = window.AqOneTutorialSource;
  if (!tutorial || !tutorial.active || !lessons || !sourceApi) return;

  var PROGRESS_KEY = 'aqoneTutorialProgress';
  var REAL_SOS_POLL_MS = 20000;
  var escapeHtml = ns.escapeHtml || function (value) { return String(value == null ? '' : value); };

  var lessonIndex = Math.max(0, lessons.findIndex(function (l) { return l.id === tutorial.lesson; }));
  var lesson = lessons[lessonIndex];
  var stepIndex = 0;
  var source = null;
  var hidden = false;
  var advanceTimer = null;

  document.body.classList.add('tutorial-mode');

  function readProgress() {
    try { return JSON.parse(localStorage.getItem(PROGRESS_KEY) || '{}') || {}; } catch (e) { return {}; }
  }

  function markDone(id) {
    var progress = readProgress();
    progress[id] = true;
    try { localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress)); } catch (e) { /* per-viewer convenience only */ }
  }

  function el(tag, className, html) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (html != null) node.innerHTML = html;
    return node;
  }

  // ===== BANNER AND WATERMARK =====
  var banner = document.querySelector('.demo-data-banner') || document.body.appendChild(el('div', 'demo-data-banner'));
  banner.classList.add('tutorial-banner');
  banner.innerHTML =
    '<span class="tutorial-banner-tag">TUTORIAL</span>' +
    '<span class="tutorial-banner-text">Sample data from a practice scenario. Nothing here is live and nothing you do is sent.</span>' +
    '<button type="button" class="tutorial-banner-btn" id="tutorial-lessons-btn">Lessons</button>' +
    '<button type="button" class="tutorial-banner-btn tutorial-banner-exit" id="tutorial-exit-btn">Exit tutorial</button>';
  document.body.appendChild(el('div', 'tutorial-watermark')).setAttribute('aria-hidden', 'true');

  var realSosBar = el('div', 'tutorial-real-sos');
  realSosBar.setAttribute('role', 'alert');
  realSosBar.hidden = true;
  document.body.appendChild(realSosBar);

  function exitTutorial() {
    try {
      sessionStorage.removeItem(sourceApi.MODE_KEY);
      sessionStorage.removeItem(sourceApi.LESSON_KEY);
    } catch (e) { /* storage unavailable: the reload still leaves the tutorial */ }
    window.location.replace(realToken() ? 'dashboard.html' : 'login.html');
  }

  function openLesson(id) {
    try { sessionStorage.setItem(sourceApi.LESSON_KEY, id); } catch (e) { return; }
    window.location.reload();
  }

  document.getElementById('tutorial-exit-btn').addEventListener('click', exitTutorial);
  document.getElementById('tutorial-lessons-btn').addEventListener('click', function () { showMenu(true); });

  // ===== REAL SOS WHILE IN THE TUTORIAL =====
  // A signed-in responder can open the tutorial from the profile page. The
  // practice data must never hide a real call, so the real feed is still read
  // (read-only, through the real fetch) and a waiting call is announced.
  function realToken() {
    try { return sessionStorage.getItem('aqoneToken') || ''; } catch (e) { return ''; }
  }

  function checkRealSos() {
    var token = realToken();
    if (!token) return;
    tutorial.realFetch('/api/sos/active?limit=200', { headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' } })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        var waiting = data && Array.isArray(data.events) ? data.events.filter(function (ev) {
          return ev.is_synthetic !== true && !ev.acknowledged_at;
        }).length : 0;
        realSosBar.hidden = waiting === 0;
        if (waiting) {
          realSosBar.innerHTML = '<strong>' + (waiting === 1 ? 'A real SOS is waiting.' : waiting + ' real SOS calls are waiting.') +
            '</strong> Leave the tutorial to respond. <button type="button">Exit tutorial</button>';
          realSosBar.querySelector('button').addEventListener('click', exitTutorial);
        }
      })
      .catch(function () { /* the next poll tries again */ });
  }
  checkRealSos();
  setInterval(checkRealSos, REAL_SOS_POLL_MS);

  // ===== SPOTLIGHT AND COACH CARD =====
  var ring = document.body.appendChild(el('div', 'tutorial-ring'));
  ring.hidden = true;
  var card = document.body.appendChild(el('section', 'tutorial-card'));
  card.setAttribute('aria-live', 'polite');
  var pill = document.body.appendChild(el('button', 'tutorial-pill'));
  pill.type = 'button';
  pill.hidden = true;
  pill.addEventListener('click', function () { setHidden(false); });

  function target() {
    var step = lesson.steps[stepIndex];
    if (!step || !step.target) return null;
    var node = document.querySelector(step.target);
    if (!node) return null;
    var rect = node.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 ? rect : null;
  }

  // A dashboard modal (acknowledge, resolve, open drift case) is where the
  // learner is working: the spotlight steps back and the card waits beneath it.
  var MODALS = '.ack-modal-overlay:not([hidden]), .emergency-modal-overlay.active, .advisory-modal-overlay.active';

  function place() {
    if (hidden) return;
    var behind = !!document.querySelector(MODALS);
    card.classList.toggle('tutorial-card-behind', behind);
    if (behind) {
      ring.hidden = true;
      return;
    }
    var rect = target();
    var margin = 14;
    var minTop = banner.getBoundingClientRect().bottom + 8;
    var vw = window.innerWidth, vh = window.innerHeight;
    var cw = card.offsetWidth, ch = card.offsetHeight;
    if (!rect) {
      ring.hidden = true;
      card.style.left = Math.max(margin, (vw - cw) / 2) + 'px';
      card.style.top = Math.max(minTop, (vh - ch) / 2) + 'px';
      return;
    }
    ring.hidden = false;
    ring.style.left = (rect.left - 6) + 'px';
    ring.style.top = (rect.top - 6) + 'px';
    ring.style.width = (rect.width + 12) + 'px';
    ring.style.height = (rect.height + 12) + 'px';
    var spots = [
      { left: rect.right + margin, top: rect.top, fits: rect.right + margin + cw < vw },
      { left: rect.left - margin - cw, top: rect.top, fits: rect.left - margin - cw > 0 },
      { left: rect.left, top: rect.bottom + margin, fits: rect.bottom + margin + ch < vh },
      { left: rect.left, top: rect.top - margin - ch, fits: rect.top - margin - ch > minTop }
    ];
    var spot = spots.find(function (s) { return s.fits; }) || { left: vw - cw - margin, top: vh - ch - margin };
    card.style.left = Math.min(Math.max(margin, spot.left), vw - cw - margin) + 'px';
    card.style.top = Math.max(minTop, Math.min(spot.top, vh - ch - margin)) + 'px';
  }

  function runBefore(step) {
    (step.before || []).forEach(function (action) {
      if (action.unless && document.querySelector(action.unless)) return;
      var selector = action.tab ? '.stats-tab[data-tab="' + action.tab + '"]' : action.click;
      var node = selector && document.querySelector(selector);
      if (node) node.click();
    });
  }

  function waiting() {
    var step = lesson.steps[stepIndex];
    return !!(step && step.waitFor && source && !new RegExp(step.waitFor).test(source.phase()));
  }

  function render() {
    var step = lesson.steps[stepIndex];
    var last = stepIndex === lesson.steps.length - 1;
    var holding = waiting();
    card.innerHTML =
      '<div class="tutorial-card-meta">Lesson ' + (lessonIndex + 1) + ' of ' + lessons.length + ' &middot; ' + escapeHtml(lesson.title) +
        '<button type="button" class="tutorial-card-hide" data-coach="hide" title="Hide the steps and explore">Hide</button></div>' +
      '<h2 class="tutorial-card-title">' + escapeHtml(step.title) + '</h2>' +
      '<p class="tutorial-card-body">' + escapeHtml(step.body) + '</p>' +
      (holding ? '<p class="tutorial-card-waiting">Try it now. The lesson continues when you do.</p>' : '') +
      '<div class="tutorial-card-actions">' +
        '<span class="tutorial-card-count">Step ' + (stepIndex + 1) + ' of ' + lesson.steps.length + '</span>' +
        (stepIndex > 0 ? '<button type="button" class="tutorial-btn" data-coach="back">Back</button>' : '') +
        (holding ? '<button type="button" class="tutorial-btn" data-coach="next">Skip step</button>'
          : '<button type="button" class="tutorial-btn tutorial-btn-primary" data-coach="next">' + (last ? 'Finish lesson' : 'Next') + '</button>') +
      '</div>';
    place();
  }

  function showStep(index) {
    clearTimeout(advanceTimer);
    stepIndex = Math.max(0, Math.min(index, lesson.steps.length - 1));
    var step = lesson.steps[stepIndex];
    runBefore(step);
    if (step.cue && source) {
      advanceTimer = setTimeout(function () {
        source.cue(step.cue);
        if (ns.loadActiveSos) ns.loadActiveSos();
      }, 2500);
    }
    render();
    setTimeout(function () {
      var node = step.target && document.querySelector(step.target);
      if (node && typeof node.scrollIntoView === 'function') node.scrollIntoView({ block: 'nearest' });
      place();
    }, 350);
  }

  function finishLesson() {
    markDone(lesson.id);
    var next = lessons[lessonIndex + 1];
    ring.hidden = true;
    card.innerHTML =
      '<div class="tutorial-card-meta">Lesson ' + (lessonIndex + 1) + ' of ' + lessons.length + ' &middot; done</div>' +
      '<h2 class="tutorial-card-title">' + escapeHtml(lesson.title) + ': done</h2>' +
      '<p class="tutorial-card-body">' + (next
        ? 'Keep exploring this lesson\'s data, go on to the next lesson, or pick any other.'
        : 'That was the last lesson. Pick any lesson again, or exit to the live console.') + '</p>' +
      '<div class="tutorial-card-actions">' +
        '<button type="button" class="tutorial-btn" data-coach="menu">All lessons</button>' +
        (next ? '<button type="button" class="tutorial-btn tutorial-btn-primary" data-coach="lesson" data-id="' + next.id + '">Next: ' + escapeHtml(next.title) + '</button>'
          : '<button type="button" class="tutorial-btn tutorial-btn-primary" data-coach="exit">Exit tutorial</button>') +
      '</div>';
    place();
  }

  function setHidden(value) {
    hidden = value;
    card.hidden = value;
    ring.hidden = value || !target();
    pill.hidden = !value;
    pill.textContent = 'Tutorial: ' + lesson.title + ' - show steps';
    if (!value) place();
  }

  card.addEventListener('click', function (event) {
    var button = event.target.closest('[data-coach]');
    if (!button) return;
    var action = button.getAttribute('data-coach');
    if (action === 'next') {
      if (stepIndex === lesson.steps.length - 1) finishLesson(); else showStep(stepIndex + 1);
    } else if (action === 'back') {
      showStep(stepIndex - 1);
    } else if (action === 'hide') {
      setHidden(true);
    } else if (action === 'menu') {
      showMenu(true);
    } else if (action === 'lesson') {
      openLesson(button.getAttribute('data-id'));
    } else if (action === 'exit') {
      exitTutorial();
    }
  });

  window.addEventListener('resize', place);
  setInterval(place, 300);

  // ===== LESSON MENU =====
  var menu = document.body.appendChild(el('div', 'tutorial-menu-overlay'));
  menu.hidden = true;
  menu.addEventListener('click', function (event) {
    if (event.target === menu || event.target.closest('[data-menu="close"]')) return showMenu(false);
    var pick = event.target.closest('[data-lesson]');
    if (pick) openLesson(pick.getAttribute('data-lesson'));
  });

  function showMenu(open) {
    if (open) {
      var progress = readProgress();
      menu.innerHTML =
        '<div class="tutorial-menu" role="dialog" aria-modal="true" aria-label="Tutorial lessons">' +
          '<div class="tutorial-menu-header"><h2>Lessons</h2><button type="button" class="tutorial-menu-close" data-menu="close" aria-label="Close">&times;</button></div>' +
          '<p class="tutorial-menu-intro">Each lesson opens on its own practice data, so you can start anywhere.</p>' +
          '<ol class="tutorial-menu-list">' + lessons.map(function (l, i) {
            return '<li><button type="button" class="tutorial-menu-item' + (l.id === lesson.id ? ' is-current' : '') + '" data-lesson="' + l.id + '">' +
              '<span class="tutorial-menu-num">' + (progress[l.id] ? '&#10003;' : i + 1) + '</span>' +
              '<span class="tutorial-menu-text"><strong>' + escapeHtml(l.title) + '</strong><span>' + escapeHtml(l.summary) + '</span></span>' +
              '<span class="tutorial-menu-min">' + l.minutes + ' min</span>' +
            '</button></li>';
          }).join('') + '</ol>' +
        '</div>';
    }
    menu.hidden = !open;
  }

  // ===== START =====
  tutorial.onRefusal(function () {
    if (ns.showToast) ns.showToast('Not part of this lesson', 'Nothing was sent. Pick the lesson that practises it from Lessons.', false);
  });

  render();
  tutorial.ready.then(function (s) {
    source = s;
    source.onPhase(function () {
      var step = lesson.steps[stepIndex];
      if (step && step.waitFor && new RegExp(step.waitFor).test(source.phase())) {
        render();
        advanceTimer = setTimeout(function () { showStep(stepIndex + 1); }, 1800);
      }
    });
    showStep(0);
  }, function () {
    card.innerHTML = '<h2 class="tutorial-card-title">The tutorial could not load</h2>' +
      '<p class="tutorial-card-body">Its practice data did not download. Check the connection and reload, or exit the tutorial.</p>' +
      '<div class="tutorial-card-actions"><button type="button" class="tutorial-btn tutorial-btn-primary" data-coach="exit">Exit tutorial</button></div>';
    place();
  });
})(window.AqOneDashboard = window.AqOneDashboard || {});
