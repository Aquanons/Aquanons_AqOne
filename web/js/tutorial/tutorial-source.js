// The dashboard tutorial's data source (docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md).
//
// Loaded first in dashboard.html. In tutorial mode it replaces window.fetch,
// so every panel runs its real code against responses recorded from the
// backend's presenter scenario (tools/render-check/record_tutorial.mjs) and
// no request leaves the page. Outside tutorial mode it does nothing.
//
// A lesson recording is a list of phases. The first holds the responses the
// dashboard saw when the lesson started; each later phase begins with the
// action (or cue) that produced it, and holds that action's reply and the
// responses seen afterwards. Replaying an action moves to its phase, so the
// panels show what the real backend answered.
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && typeof module.exports === 'object') {
    module.exports = factory();
  } else {
    root.AqOneTutorialSource = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var MODE_KEY = 'aqoneDashboardMode';
  var LESSON_KEY = 'aqoneTutorialLesson';
  var ZONED_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/;
  var LOCAL_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;
  var DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;
  var DAY_MS = 86400000;

  /**
   * Moves every timestamp in a recorded body forward by deltaMs, so "12
   * minutes ago" at recording time still reads 12 minutes ago when the
   * lesson is opened. Zone-less and date-only strings keep their format.
   */
  function shiftTimes(value, deltaMs) {
    if (typeof value === 'string') {
      if (ZONED_TIME.test(value)) return new Date(Date.parse(value) + deltaMs).toISOString();
      if (LOCAL_TIME.test(value)) return new Date(Date.parse(value + 'Z') + deltaMs).toISOString().slice(0, 16);
      if (DATE_ONLY.test(value)) {
        return new Date(Date.parse(value + 'T00:00:00Z') + Math.round(deltaMs / DAY_MS) * DAY_MS).toISOString().slice(0, 10);
      }
      return value;
    }
    if (Array.isArray(value)) return value.map(function (item) { return shiftTimes(item, deltaMs); });
    if (value && typeof value === 'object') {
      var out = {};
      Object.keys(value).forEach(function (key) { out[key] = shiftTimes(value[key], deltaMs); });
      return out;
    }
    return value;
  }

  /** "GET /api/sos/active?limit=200" for this origin, the full URL otherwise. */
  function requestKey(method, url, origin) {
    var parsed = new URL(url, origin + '/');
    var where = parsed.origin === origin ? parsed.pathname + parsed.search : parsed.origin + parsed.pathname + parsed.search;
    return String(method || 'GET').toUpperCase() + ' ' + where;
  }

  function withoutQuery(key) {
    var index = key.indexOf('?');
    return index < 0 ? key : key.slice(0, index);
  }

  function jsonResponse(status, body) {
    return new Response(JSON.stringify(body), { status: status, headers: { 'Content-Type': 'application/json' } });
  }

  function recordedResponse(entry) {
    if (entry.text != null) {
      return new Response(entry.text, { status: entry.status, headers: { 'Content-Type': entry.type || 'text/plain' } });
    }
    return jsonResponse(entry.status, entry.body);
  }

  /**
   * A replaying source over one lesson recording. `options.now` is the clock
   * the recording is shifted to; `options.onRefusal(key)` hears every action
   * the lesson did not record.
   */
  function createSource(recording, options) {
    var opts = options || {};
    var origin = opts.origin || 'http://localhost';
    var delta = (opts.now || Date.now()) - Date.parse(recording.recorded_at);
    var phases = shiftTimes(recording.phases || [], isFinite(delta) ? delta : 0);
    var current = 0;
    var listeners = [];

    function moveTo(index) {
      current = index;
      listeners.forEach(function (fn) { fn(phases[index].label, index); });
    }

    function findGet(key) {
      var bare = withoutQuery(key);
      var i;
      for (i = current; i >= 0; i--) if (phases[i].responses && phases[i].responses[key]) return phases[i].responses[key];
      for (i = current; i >= 0; i--) {
        var match = Object.keys(phases[i].responses || {}).find(function (k) { return withoutQuery(k) === bare; });
        if (match) return phases[i].responses[match];
      }
      for (i = current + 1; i < phases.length; i++) if (phases[i].responses && phases[i].responses[key]) return phases[i].responses[key];
      return null;
    }

    function triggerMatches(phase, key) {
      return phase.trigger && phase.trigger.request === withoutQuery(key);
    }

    function answer(method, url) {
      var key = requestKey(method, url, origin);
      if (key.indexOf('GET ') === 0) {
        var entry = findGet(key);
        return entry ? recordedResponse(entry) : jsonResponse(404, { detail: 'Not part of this tutorial lesson.' });
      }
      var i;
      for (i = current + 1; i < phases.length; i++) {
        if (triggerMatches(phases[i], key)) {
          moveTo(i);
          return recordedResponse(phases[i].trigger.reply);
        }
      }
      for (i = current; i > 0; i--) {
        if (triggerMatches(phases[i], key)) return recordedResponse(phases[i].trigger.reply);
      }
      if (opts.onRefusal) opts.onRefusal(key);
      return jsonResponse(409, { detail: 'This lesson does not practise that action, so nothing was sent.' });
    }

    return {
      fetch: function (input, init) {
        var url = typeof input === 'string' ? input : (input && input.url) || String(input);
        var method = (init && init.method) || (input && input.method) || 'GET';
        return Promise.resolve(answer(method, url));
      },
      cue: function (name) {
        for (var i = current + 1; i < phases.length; i++) {
          if (phases[i].trigger && phases[i].trigger.cue === name) {
            moveTo(i);
            return true;
          }
        }
        return false;
      },
      phase: function () { return phases[current].label; },
      onPhase: function (fn) { listeners.push(fn); }
    };
  }

  /** The tutorial lesson this tab is in, or null in live mode. */
  function activeLesson(storage) {
    try {
      if (storage.getItem(MODE_KEY) !== 'tutorial') return null;
      var lesson = storage.getItem(LESSON_KEY) || '';
      return /^[a-z0-9-]{1,40}$/.test(lesson) ? lesson : null;
    } catch (e) {
      return null;
    }
  }

  return {
    MODE_KEY: MODE_KEY,
    LESSON_KEY: LESSON_KEY,
    shiftTimes: shiftTimes,
    requestKey: requestKey,
    createSource: createSource,
    activeLesson: activeLesson
  };
});

// Browser start-up: in tutorial mode, swap window.fetch before any other
// dashboard script runs. The real fetch stays reachable for the lesson file
// and the coach's real-SOS check, and nothing else.
(function () {
  'use strict';
  if (typeof window === 'undefined' || !window.AqOneTutorialSource) return;
  var api = window.AqOneTutorialSource;
  var lesson = api.activeLesson(window.sessionStorage);
  if (!lesson) {
    window.AqOneTutorial = { active: false };
    return;
  }
  var realFetch = window.fetch.bind(window);
  var refusalListeners = [];
  var ready = realFetch('../data/tutorial/' + lesson + '.json', { cache: 'no-cache' })
    .then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    })
    .then(function (recording) {
      return api.createSource(recording, {
        origin: window.location.origin,
        onRefusal: function (key) { refusalListeners.forEach(function (fn) { fn(key); }); }
      });
    });

  // The danger-zone scan labels weather from a /demo/ base as DEMO, and the
  // recording captured the scenario's weather under these paths.
  window.AQONE_WEATHER_BASE = '/api/demo/weather/forecast';
  window.AQONE_MARINE_BASE = '/api/demo/weather/marine';
  window.fetch = function (input, init) {
    return ready.then(function (source) {
      return source.fetch(input, init);
    }, function () {
      return new Response(JSON.stringify({ detail: 'Tutorial data could not be loaded.' }), {
        status: 503, headers: { 'Content-Type': 'application/json' }
      });
    });
  };
  window.AqOneTutorial = {
    active: true,
    lesson: lesson,
    ready: ready,
    realFetch: realFetch,
    onRefusal: function (fn) { refusalListeners.push(fn); }
  };
})();
