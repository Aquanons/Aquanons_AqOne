(function (ns) {
  'use strict';
  if (!ns.ready) return;

  // Dashboard SOS alarm: a two-tone siren synthesized with the Web Audio API,
  // so the handset is not the only place a distress call makes noise. No audio
  // asset is needed - the browser generates the tone - which keeps the alarm
  // working on any deployment that serves dashboard.js, including one over a
  // gateway with no space for media files.
  var AC = window.AudioContext || window.webkitAudioContext;
  var ctx = null;
  var osc = null;
  var gain = null;
  var timer = null;
  var running = false;

  var LOW_HZ = 700;
  var HIGH_HZ = 950;
  var TOGGLE_MS = 600;
  var VOLUME = 0.25;

  // A new event rings the alarm ONLY while it is unacknowledged. An
  // acknowledged-but-unresolved call stays in /active (the dispatcher can
  // still see the fisher's reply land on it) but must stop sounding the
  // klaxon - the dispatcher has heard it once.
  function hasUnacknowledgedSos(events) {
    if (!Array.isArray(events)) return false;
    return events.some(function (ev) {
      if (!ev) return false;
      var acknowledged = ev.acknowledged_at != null || ev.status === 'acknowledged';
      return !acknowledged;
    });
  }

  function prime() {
    if (!AC || ctx) return;
    try {
      ctx = new AC();
      if (ctx.resume) ctx.resume();
    } catch (e) {
      ctx = null;
    }
  }

  // Browsers block sound until the user has interacted with the page. The
  // dashboard is driven by clicks by definition (opening the console, the
  // drawer, ack), so the first gesture primes the context; the alarm itself
  // also tries resume() lazily, which resolves on the next interaction.
  if (window && window.addEventListener) {
    var unlock = function () { prime(); };
    ['pointerdown', 'keydown', 'touchstart'].forEach(function (eventName) {
      window.addEventListener(eventName, unlock, { once: true, passive: true });
    });
  }

  function start() {
    if (running) return;
    running = true;
    if (!AC || !ctx) {
      prime();
      if (!ctx) return;
    }
    try {
      if (ctx.state === 'suspended' && ctx.resume) ctx.resume();
      if (osc) return;
      osc = ctx.createOscillator();
      osc.type = 'square';
      osc.frequency.value = LOW_HZ;
      gain = ctx.createGain();
      gain.gain.value = VOLUME;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      timer = setInterval(function () {
        if (!osc) return;
        try {
          osc.frequency.setValueAtTime(
            osc.frequency.value === LOW_HZ ? HIGH_HZ : LOW_HZ,
            ctx.currentTime
          );
        } catch (e) {}
      }, TOGGLE_MS);
    } catch (e) {
      running = false;
    }
  }

  function stop() {
    running = false;
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (osc) {
      try { osc.stop(); } catch (e) {}
      try { osc.disconnect(); } catch (e) {}
      osc = null;
    }
    if (gain) {
      try { gain.disconnect(); } catch (e) {}
      gain = null;
    }
  }

  // Stops the siren once the live feed holds no unacknowledged call. It never
  // starts on its own: starting is driven by a freshly-seen SOS id in
  // dashboard-live-sos.js, so events that were already on screen when the
  // dashboard opened do not get a klaxon.
  function sync(events) {
    if (!hasUnacknowledgedSos(events)) {
      stop();
    }
  }

  ns.hasUnacknowledgedSos = hasUnacknowledgedSos;
  ns.sosAlarm = {
    start: start,
    stop: stop,
    sync: sync,
    prime: prime,
    isRunning: function () { return running; }
  };
})(window.AqOneDashboard = window.AqOneDashboard || {});