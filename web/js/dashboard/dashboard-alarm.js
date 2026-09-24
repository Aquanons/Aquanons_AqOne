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
    } catch (e) {
      ctx = null;
    }
  }

  // Build the two-tone siren into an already-running context. Preferring to
  // create the oscillator only once the context can actually be heard avoids
  // starting an oscillator inside a suspended context, which would otherwise
  // silently do nothing and lock the alarm into a "ringing" state that never
  // makes a sound.
  function buildOscillator() {
    if (!ctx || ctx.state !== 'running' || osc) return;
    try {
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

  // Browsers block sound until the user has interacted with the page. A
  // context created before any gesture (e.g. the SOS arrived while nobody had
  // clicked yet) starts suspended. Every gesture retries resume() so the
  // klaxon builds the moment the context is unblocked - by browser policy it
  // cannot ring before then. Not `{ once: true }`: a suspended context may
  // need more than one interaction before it is released.
  function unlock() {
    if (!AC) return;
    prime();
    if (!ctx) return;
    if (ctx.state === 'suspended' && ctx.resume) {
      try { ctx.resume(); } catch (e) {}
    }
    if (running && ctx.state === 'running') {
      buildOscillator();
    }
  }

  if (window && window.addEventListener) {
    ['pointerdown', 'keydown', 'touchstart'].forEach(function (eventName) {
      window.addEventListener(eventName, unlock, { passive: true });
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
      if (ctx.state === 'suspended' && ctx.resume) {
        try { ctx.resume(); } catch (e) {}
        return;
      }
      buildOscillator();
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
  // starts on its own: starting is driven by a freshly-seen SOS id, or once
  // per tab session for calls already waiting when the dashboard opened
  // (dashboard-live-sos.js), so a plain reload does not re-ring.
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