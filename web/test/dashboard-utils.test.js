'use strict';

// node --test web/test/dashboard-utils.test.js
//
// Covers docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md Phase 3's
// required test surface: escaping, fresh/stale/offline transitions, and
// synthetic/demo badges. Requires web/js/dashboard-utils.js directly (its
// UMD wrapper exports via module.exports under Node), so this exercises the
// exact same code dashboard.html loads in the browser - not a reimplementation.

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  escapeHtml,
  classifyFreshness,
  freshnessLabel,
  alertBadge,
  registrationBadge,
  registrationBadgeHtml,
  formatEta,
  responderStatusHtml,
  caseTypeBadge,
  caseStatusLabel,
  formatDataAge,
  tripCheckRowHtml,
  tripChecksListHtml,
  eligibleForSearchReport,
  squallStatusHtml,
  formatAuditAction,
  auditEventRowHtml,
  auditTimelineHtml
} = require('../js/dashboard-utils.js');

test('escapeHtml', async (t) => {
  await t.test('escapes the five HTML-significant characters', () => {
    assert.equal(
      escapeHtml(`<script>alert('x')</script> & "quoted"`),
      '&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt; &amp; &quot;quoted&quot;'
    );
  });

  await t.test('escapes an SOS note carrying an injected tag, per the plan\'s XSS scenario', () => {
    // The exact shape of the bug this closes: a fisher's free-text note
    // rendered straight into innerHTML by web/js/dashboard.js
    // liveAlertFromEvent()/renderAlerts().
    const note = '<img src=x onerror=alert(1)>';
    const escaped = escapeHtml(note);
    assert.ok(!escaped.includes('<img'));
    assert.equal(escaped, '&lt;img src=x onerror=alert(1)&gt;');
  });

  await t.test('turns null/undefined into an empty string, not the word "null"', () => {
    assert.equal(escapeHtml(null), '');
    assert.equal(escapeHtml(undefined), '');
  });

  await t.test('leaves ordinary text untouched', () => {
    assert.equal(escapeHtml('engine down, taking water'), 'engine down, taking water');
  });

  await t.test('coerces non-string input (e.g. a number) to text first', () => {
    assert.equal(escapeHtml(42), '42');
  });
});

test('classifyFreshness', async (t) => {
  const POLL_MS = 3000; // matches LIVE_SOS_POLL_MS in web/js/dashboard.js

  await t.test('is offline before any poll has ever succeeded', () => {
    assert.equal(classifyFreshness(null, Date.now(), { pollIntervalMs: POLL_MS }), 'offline');
    assert.equal(classifyFreshness(undefined, Date.now(), { pollIntervalMs: POLL_MS }), 'offline');
  });

  await t.test('is live immediately after a successful poll', () => {
    const now = 1_000_000;
    assert.equal(classifyFreshness(now, now, { pollIntervalMs: POLL_MS }), 'live');
  });

  await t.test('stays live within the stale threshold (3 missed polls)', () => {
    const now = 1_000_000;
    const lastSuccess = now - POLL_MS * 2;
    assert.equal(classifyFreshness(lastSuccess, now, { pollIntervalMs: POLL_MS }), 'live');
  });

  await t.test('becomes stale after missing several polls, before offline', () => {
    const now = 1_000_000;
    const lastSuccess = now - POLL_MS * 5;
    assert.equal(classifyFreshness(lastSuccess, now, { pollIntervalMs: POLL_MS }), 'stale');
  });

  await t.test('becomes offline once far too much time has passed', () => {
    const now = 1_000_000;
    const lastSuccess = now - POLL_MS * 20;
    assert.equal(classifyFreshness(lastSuccess, now, { pollIntervalMs: POLL_MS }), 'offline');
  });

  await t.test('transitions live -> stale -> offline as time passes with no new success', () => {
    const lastSuccess = 0;
    const pollOpts = { pollIntervalMs: POLL_MS };
    assert.equal(classifyFreshness(lastSuccess, 0, pollOpts), 'live');
    assert.equal(classifyFreshness(lastSuccess, POLL_MS * 3, pollOpts), 'live');
    assert.equal(classifyFreshness(lastSuccess, POLL_MS * 5, pollOpts), 'stale');
    // offlineAfterMs defaults to pollIntervalMs * 10 and the boundary itself
    // is still "stale" (age <= offlineAfterMs); one tick past it is offline.
    assert.equal(classifyFreshness(lastSuccess, POLL_MS * 10 + 1, pollOpts), 'offline');
  });

  await t.test('a fresh success immediately pulls the state back to live from offline', () => {
    const pollOpts = { pollIntervalMs: POLL_MS };
    // Was offline (no success in a long time)...
    assert.equal(classifyFreshness(0, POLL_MS * 20, pollOpts), 'offline');
    // ...then a poll succeeds "now" - must read live again, not stay offline.
    const now = POLL_MS * 20;
    assert.equal(classifyFreshness(now, now, pollOpts), 'live');
  });

  await t.test('does not crash on clock skew (lastSuccess after now)', () => {
    const now = 1000;
    assert.equal(classifyFreshness(now + 5000, now, { pollIntervalMs: POLL_MS }), 'live');
  });

  await t.test('respects custom thresholds when given', () => {
    const now = 100000;
    const opts = { pollIntervalMs: POLL_MS, staleAfterMs: 1000, offlineAfterMs: 2000 };
    assert.equal(classifyFreshness(now - 500, now, opts), 'live');
    assert.equal(classifyFreshness(now - 1500, now, opts), 'stale');
    assert.equal(classifyFreshness(now - 3000, now, opts), 'offline');
  });
});

test('freshnessLabel', () => {
  assert.equal(freshnessLabel('live'), 'LIVE');
  assert.equal(freshnessLabel('stale'), 'STALE');
  assert.equal(freshnessLabel('offline'), 'OFFLINE');
  // An unrecognised state must fail safe to the most cautious label, never
  // silently claim LIVE.
  assert.equal(freshnessLabel('nonsense'), 'OFFLINE');
  assert.equal(freshnessLabel(undefined), 'OFFLINE');
});

test('alertBadge (synthetic/demo vs. live incident-feed badges)', async (t) => {
  await t.test('a real SOS event gets the LIVE badge', () => {
    const badge = alertBadge(true);
    assert.equal(badge.text, 'LIVE');
    assert.equal(badge.cssClass, 'alert-live-badge');
  });

  await t.test('a scripted/sample row gets the DEMO badge, never LIVE', () => {
    const badge = alertBadge(false);
    assert.equal(badge.text, 'DEMO');
    assert.equal(badge.cssClass, 'alert-demo-badge');
    assert.notEqual(badge.text, 'LIVE');
  });

  await t.test('undefined isLive (e.g. a malformed row) is treated as demo, not live', () => {
    // Fail-safe direction matters: an ambiguous row must never default to
    // looking like a real distress call.
    const badge = alertBadge(undefined);
    assert.equal(badge.text, 'DEMO');
  });
});

test('registrationBadge (registered vs. unregistered boat)', async (t) => {
  await t.test('a declared license type gets the green registered badge', () => {
    for (const type of ['boatr', 'fishr', 'cfvgl', 'motorized']) {
      const badge = registrationBadge(type);
      assert.equal(badge.text, 'Registered Boat');
      assert.equal(badge.cssClass, 'reg-badge-registered');
    }
  });

  await t.test('missing, empty, or none reads unregistered, never registered', () => {
    for (const type of [null, undefined, '', 'none']) {
      const badge = registrationBadge(type);
      assert.equal(badge.text, 'Unregistered Boat');
      assert.equal(badge.cssClass, 'reg-badge-unregistered');
    }
  });

  await t.test('badge HTML names the registration type and escapes it', () => {
    const html = registrationBadgeHtml('boatr');
    assert.ok(html.includes('Registered Boat'), 'badge text rendered');
    assert.ok(html.includes('BOATR'), 'license type named');
    assert.ok(!html.includes('<img'), 'no raw markup from the type value');
    const evil = registrationBadgeHtml('boatr"><img src=x>');
    assert.ok(!evil.includes('<img src=x>'), 'type value is escaped');
  });
});

test('formatEta', async (t) => {
  await t.test('is empty when there is no ETA yet', () => {
    assert.equal(formatEta(null), '');
    assert.equal(formatEta(undefined), '');
  });

  await t.test('an expired ETA renders an honest delayed message, never 00:00 or negative', () => {
    const now = Date.parse('2026-08-16T09:00:00Z');
    const oneMinuteAgo = '2026-08-16T08:59:00Z';
    const text = formatEta(oneMinuteAgo, now);
    assert.equal(text, 'delayed — still en route');
    assert.ok(!text.includes('00:00'));
    assert.ok(!text.includes('-'));
  });

  await t.test('an ETA at the exact current moment counts as expired, not 00:00', () => {
    const now = Date.parse('2026-08-16T09:00:00Z');
    assert.equal(formatEta('2026-08-16T09:00:00Z', now), 'delayed — still en route');
  });

  await t.test('a future ETA renders a countdown', () => {
    const now = Date.parse('2026-08-16T09:00:00Z');
    assert.equal(formatEta('2026-08-16T09:05:30Z', now), 'ETA 5:30');
  });
});

test('responderStatusHtml', async (t) => {
  await t.test('is empty for an SOS that has not been acknowledged yet', () => {
    assert.equal(responderStatusHtml({ acknowledgedAt: null }), '');
  });

  await t.test('server-supplied responder note text is escaped, never passed through raw', () => {
    const now = Date.parse('2026-08-16T09:00:00Z');
    const html = responderStatusHtml({
      acknowledgedAt: '2026-08-16T08:50:00Z',
      etaAt: '2026-08-16T09:20:00Z',
      responderStatusLabel: 'Rescue boat on the way',
      responderNote: '<script>alert(1)</script>'
    }, now);
    assert.ok(!html.includes('<script>'));
    assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
  });

  await t.test('an expired ETA shows the honest delayed wording, not a stale countdown', () => {
    const now = Date.parse('2026-08-16T09:00:00Z');
    const html = responderStatusHtml({
      acknowledgedAt: '2026-08-16T08:00:00Z',
      etaAt: '2026-08-16T08:30:00Z',
      responderStatusLabel: 'Delayed - still coming'
    }, now);
    assert.ok(html.includes('delayed — still en route'));
    assert.ok(html.includes('is-overdue'));
  });

  await t.test('the fisher\'s STILL_IN_DANGER reply is shown distinctly from SAFE_NOW', () => {
    const stillInDanger = responderStatusHtml({ acknowledgedAt: '2026-08-16T08:00:00Z', fisherReply: 1 });
    const safeNow = responderStatusHtml({ acknowledgedAt: '2026-08-16T08:00:00Z', fisherReply: 2 });
    assert.ok(stillInDanger.includes('Still in danger'));
    assert.ok(stillInDanger.includes('sos-fisher-danger'));
    assert.ok(safeNow.includes('Safe now'));
    assert.ok(!safeNow.includes('sos-fisher-danger'));
  });

  await t.test('omits the fisher-reply and note rows when there is nothing to show', () => {
    const html = responderStatusHtml({ acknowledgedAt: '2026-08-16T08:00:00Z' });
    assert.ok(!html.includes('Fisher Reply'));
    assert.ok(!html.includes('Responder Note'));
  });
});

// docs/38_AUTOMATIC_DISTRESS_DETECTION_IMPLEMENTATION_PLAN.md Phase 3: the
// "Trip checks" queue, GET /api/ai/anomaly/cases/open.

test('caseTypeBadge', async (t) => {
  await t.test('low-confidence cases read Verification, never a severity word', () => {
    const badge = caseTypeBadge('verification');
    assert.equal(badge.text, 'Verification');
    assert.equal(badge.cssClass, 'case-type-verification');
  });

  await t.test('high-confidence cases read Responder Attention', () => {
    const badge = caseTypeBadge('responder_attention');
    assert.equal(badge.text, 'Responder Attention');
    assert.equal(badge.cssClass, 'case-type-responder-attention');
  });
});

test('caseStatusLabel', async (t) => {
  await t.test('a freshly created case with no action yet reads Open', () => {
    assert.equal(caseStatusLabel({}).text, 'Open');
  });

  await t.test('shows the most-final action set, resolved beating everything else', () => {
    assert.equal(caseStatusLabel({ acknowledgedAt: '2026-08-16T08:00:00Z' }).text, 'Acknowledged');
    assert.equal(caseStatusLabel({ dismissedAt: '2026-08-16T08:00:00Z' }).text, 'Dismissed');
    assert.equal(caseStatusLabel({ escalatedAt: '2026-08-16T08:00:00Z' }).text, 'Escalated');
    assert.equal(
      caseStatusLabel({ acknowledgedAt: '2026-08-16T08:00:00Z', resolvedAt: '2026-08-16T09:00:00Z' }).text,
      'Resolved'
    );
  });
});

test('formatDataAge', async (t) => {
  await t.test('shows minutes only for anything under an hour', () => {
    assert.equal(formatDataAge(600), '10m old');
  });

  await t.test('shows hours and minutes past an hour', () => {
    assert.equal(formatDataAge(7500), '2h 5m old');
  });

  await t.test('never claims a fresh age for missing or invalid data', () => {
    assert.equal(formatDataAge(null), 'unknown age');
    assert.equal(formatDataAge(undefined), 'unknown age');
    assert.equal(formatDataAge(-5), 'unknown age');
  });
});

test('tripCheckRowHtml / tripChecksListHtml', async (t) => {
  await t.test('an empty queue reads as an honest empty state, not a blank panel', () => {
    const html = tripChecksListHtml([]);
    assert.ok(html.includes('No trip checks'));
  });

  await t.test('renders a verification (low-confidence) item with its type and reason', () => {
    const html = tripChecksListHtml([{
      id: 42,
      vessel_id: 'NW-001',
      trip_id: 'trip-current',
      case_type: 'verification',
      score: 0.42,
      status: 'watch',
      reasons: [{ code: 'overdue', contribution: 0.3, description: 'Late beyond the expected-contact window.' }],
      source: 'live',
      data_age_seconds: 3600,
      acknowledged_at: null,
      dismissed_at: null,
      escalated_at: null,
      resolved_at: null
    }]);
    assert.ok(html.includes('Verification'));
    assert.ok(html.includes('case-type-verification'));
    assert.ok(html.includes('NW-001'));
    assert.ok(html.includes('Late beyond the expected-contact window.'));
    assert.ok(html.includes('42%'));
    assert.ok(html.includes('data-case-action="acknowledge"'));
    assert.ok(html.includes('data-case-id="42"'));
  });

  await t.test('renders a responder-attention (high-confidence) item distinctly', () => {
    const html = tripChecksListHtml([{
      id: 7,
      vessel_id: 'NW-002',
      trip_id: 'trip-current',
      case_type: 'responder_attention',
      score: 0.88,
      status: 'alert',
      reasons: [{ code: 'overdue', contribution: 0.8, description: 'Late beyond the expected-contact window.' }],
      source: 'live',
      data_age_seconds: 9000,
      acknowledged_at: null,
      dismissed_at: null,
      escalated_at: null,
      resolved_at: null
    }]);
    assert.ok(html.includes('Responder Attention'));
    assert.ok(html.includes('case-type-responder-attention'));
    assert.ok(!html.includes('Verification'));
  });

  await t.test('the dominant (highest-contribution) factor is shown as the reason', () => {
    const html = tripCheckRowHtml({
      id: 1,
      vessel_id: 'NW-003',
      case_type: 'responder_attention',
      score: 0.7,
      reasons: [
        { code: 'weather', contribution: 0.02, description: 'Adverse weather at the last known position/time.' },
        { code: 'overdue', contribution: 0.6, description: 'Late beyond the expected-contact window.' }
      ],
      source: 'live',
      data_age_seconds: 60
    });
    assert.ok(html.includes('Late beyond the expected-contact window.'));
    assert.ok(!html.includes('Adverse weather'));
  });

  await t.test('a synthetic/demo case is labelled DEMO, never LIVE', () => {
    const html = tripCheckRowHtml({
      id: 2, vessel_id: 'NW-004', case_type: 'verification', score: 0.4, reasons: [], source: 'synthetic', data_age_seconds: 120
    });
    assert.ok(html.includes('DEMO'));
    assert.ok(!html.includes('>LIVE<'));
  });

  await t.test('the acknowledge button disables once already acknowledged, not re-sent blindly', () => {
    const html = tripCheckRowHtml({
      id: 3, vessel_id: 'NW-005', case_type: 'verification', score: 0.4, reasons: [], source: 'live',
      data_age_seconds: 60, acknowledged_at: '2026-08-16T08:00:00Z'
    });
    assert.match(html, /data-case-action="acknowledge"[^>]*disabled/);
  });

  await t.test('vessel id and reason text are escaped, never passed through raw', () => {
    const html = tripCheckRowHtml({
      id: 4,
      vessel_id: '<script>alert(1)</script>',
      case_type: 'verification',
      score: 0.4,
      reasons: [{ code: 'x', contribution: 1, description: '<img src=x onerror=alert(1)>' }],
      source: 'live',
      data_age_seconds: 60
    });
    assert.ok(!html.includes('<script>alert'));
    assert.ok(!html.includes('<img src=x'));
    assert.ok(html.includes('&lt;script&gt;'));
  });

  await t.test('a resolved case (defensive - the API already excludes these) shows no mutating action buttons, only View Activity', () => {
    const html = tripCheckRowHtml({
      id: 5, vessel_id: 'NW-006', case_type: 'verification', score: 0.4, reasons: [], source: 'live',
      data_age_seconds: 60, resolved_at: '2026-08-16T09:00:00Z'
    });
    assert.ok(!html.includes('data-case-action="acknowledge"'));
    assert.ok(!html.includes('data-case-action="dismiss"'));
    assert.ok(!html.includes('data-case-action="escalate"'));
    assert.ok(!html.includes('data-case-action="resolve"'));
    // Viewing the (redacted) authorized timeline is a read, not a mutation,
    // so it stays available even once resolved (docs/41 Phase 4).
    assert.ok(html.includes('data-case-action="activity"'));
  });
});

// docs/40_DRIFT_PREDICTION_SEARCH_RETASKING_IMPLEMENTATION_PLAN.md Phase 4
// item 2: "Disable the action when the case is not confirmed, inputs are
// insufficient, or it is a demo replay." This is the exact decision
// dashboard-ai-ops.js's "Mark a searched area" button is gated on.
test('eligibleForSearchReport', async (t) => {
  const okPayload = {
    incident: { id: 1, is_synthetic: false, case_state: 'confirmed' },
    environmental_status: 'ok'
  };

  await t.test('a real, confirmed case with sufficient inputs is eligible', () => {
    assert.deepEqual(eligibleForSearchReport(okPayload), { ok: true });
  });

  await t.test('no case selected is not eligible', () => {
    assert.equal(eligibleForSearchReport(null).ok, false);
    assert.equal(eligibleForSearchReport({}).ok, false);
  });

  await t.test('a synthetic/demo replay is not eligible', () => {
    const result = eligibleForSearchReport({
      incident: { id: 9, is_synthetic: true, case_state: 'confirmed' },
      environmental_status: 'ok'
    });
    assert.equal(result.ok, false);
    assert.match(result.reason, /synthetic replay/);
  });

  await t.test('a resolved or cancelled case is not eligible', () => {
    const resolved = eligibleForSearchReport({
      incident: { id: 1, is_synthetic: false, case_state: 'resolved' },
      environmental_status: 'ok'
    });
    assert.equal(resolved.ok, false);
    assert.match(resolved.reason, /resolved/);

    const cancelled = eligibleForSearchReport({
      incident: { id: 1, is_synthetic: false, case_state: 'cancelled' },
      environmental_status: 'ok'
    });
    assert.equal(cancelled.ok, false);
  });

  await t.test('insufficient environmental data is not eligible', () => {
    const result = eligibleForSearchReport({
      incident: { id: 1, is_synthetic: false, case_state: 'confirmed' },
      environmental_status: 'insufficient_environmental_data'
    });
    assert.equal(result.ok, false);
    assert.match(result.reason, /insufficient/);
  });
});

// docs/39_SQUALL_NOWCASTING_IMPLEMENTATION_PLAN.md Phase 3 item 5: freshness/
// source/calibration line and a neutral insufficient-data state for the
// dashboard squall panel, from the unified GET /api/ai/squall/current /
// GET /api/public/squall response shape (docs/05_PUBLIC_API.md).
test('squallStatusHtml', async (t) => {
  await t.test('a live, quality-passing response is labelled LIVE with an age string, no reason', () => {
    const html = squallStatusHtml({
      source: 'live', calibration: 'synthetic', level: 'clear', data_age_seconds: 180
    });
    assert.ok(html.includes('LIVE'));
    assert.ok(!html.includes('DEMO'));
    assert.ok(html.includes('3m old'));
    assert.ok(html.includes('calibrated on simulated data'));
    assert.ok(!html.includes('ai-squall-status-reason'));
  });

  await t.test('a synthetic response is labelled DEMO, never LIVE', () => {
    const html = squallStatusHtml({ source: 'synthetic', level: 'return_now', data_age_seconds: 30 });
    assert.ok(html.includes('DEMO'));
    assert.ok(!html.includes('>LIVE<'));
  });

  await t.test('an unknown level shows the backend status_reason as a neutral notice', () => {
    const html = squallStatusHtml({
      source: 'live',
      level: 'unknown',
      data_age_seconds: null,
      status_reason: 'only 1 of 3 required buoys have fresh, gap-free, in-range readings'
    });
    assert.ok(html.includes('ai-squall-status-reason'));
    assert.ok(html.includes('only 1 of 3 required buoys'));
    assert.ok(html.includes('unknown age'));
  });

  await t.test('an unknown level with no reason still shows a neutral fallback, not a blank line', () => {
    const html = squallStatusHtml({ source: 'live', level: 'unknown', data_age_seconds: null, status_reason: null });
    assert.ok(html.includes('cannot be confirmed right now'));
  });

  await t.test('a client-side fetch-failure fallback with no source is not badged DEMO or LIVE', () => {
    // The exact shape initAIOperations() renders when the backend was never
    // reached at all (dashboard-ai-ops.js) - found via a live browser check
    // showing this incorrectly read as "DEMO", misrepresenting a plain
    // connectivity failure as deliberately-synthetic data.
    const html = squallStatusHtml({
      level: 'unknown', detections: [], status_reason: 'unable to reach the squall service'
    });
    assert.ok(!html.includes('DEMO'));
    assert.ok(!html.includes('>LIVE<'));
    assert.ok(html.includes('unable to reach the squall service'));
  });

  await t.test('status_reason text is escaped, never passed through raw', () => {
    const html = squallStatusHtml({
      source: 'live', level: 'unknown', status_reason: '<img src=x onerror=alert(1)>'
    });
    assert.ok(!html.includes('<img src=x'));
    assert.ok(html.includes('&lt;img'));
  });
});

test('formatAuditAction', async (t) => {
  await t.test('maps a known action code to a plain-language label', () => {
    assert.equal(formatAuditAction('sos.acknowledge'), 'Acknowledged SOS');
    assert.equal(formatAuditAction('advisory.delete'), 'Deleted advisory');
  });

  await t.test('falls back to the raw code for an unknown action, never a blank label', () => {
    assert.equal(formatAuditAction('some.future.action'), 'some.future.action');
  });

  await t.test('a missing action still renders something rather than throwing', () => {
    assert.equal(formatAuditAction(undefined), 'unknown action');
  });
});

test('auditEventRowHtml', async (t) => {
  await t.test('renders time, actor, plain-language action, and outcome', () => {
    const html = auditEventRowHtml({
      occurred_at: '2026-08-30T10:00:00Z',
      actor_email: 'ranger@example.com',
      action: 'sos.resolve',
      outcome: 'updated',
      is_demo: false,
      metadata: {}
    });
    assert.ok(html.includes('2026-08-30T10:00:00Z'));
    assert.ok(html.includes('ranger@example.com'));
    assert.ok(html.includes('Resolved SOS'));
    assert.ok(html.includes('updated'));
  });

  await t.test('a null actor_email renders as "System", not blank', () => {
    const html = auditEventRowHtml({
      occurred_at: '2026-08-30T10:00:00Z', actor_email: null,
      action: 'auth.login_failure', outcome: 'failure', is_demo: false, metadata: {}
    });
    assert.ok(html.includes('System'));
  });

  await t.test('is_demo true renders the DEMO badge, false renders LIVE', () => {
    const demoHtml = auditEventRowHtml({ action: 'sos.resolve', outcome: 'updated', is_demo: true, metadata: {} });
    const liveHtml = auditEventRowHtml({ action: 'sos.resolve', outcome: 'updated', is_demo: false, metadata: {} });
    assert.ok(demoHtml.includes('alert-demo-badge'));
    assert.ok(demoHtml.includes('>DEMO<'));
    assert.ok(liveHtml.includes('alert-live-badge'));
    assert.ok(liveHtml.includes('>LIVE<'));
  });

  await t.test('metadata renders as escaped key: value text', () => {
    const html = auditEventRowHtml({
      action: 'sea_condition.declare', outcome: 'created', is_demo: false,
      metadata: { status: 'Not Advised' }
    });
    assert.ok(html.includes('status: Not Advised'));
  });

  await t.test('a malicious actor_email or metadata value is escaped, never passed through raw', () => {
    const html = auditEventRowHtml({
      actor_email: '<img src=x onerror=alert(1)>',
      action: 'sos.resolve', outcome: 'updated', is_demo: false,
      metadata: { note: '<script>alert(2)</script>' }
    });
    assert.ok(!html.includes('<img src=x'));
    assert.ok(!html.includes('<script>'));
    assert.ok(html.includes('&lt;img'));
    assert.ok(html.includes('&lt;script&gt;'));
  });
});

test('auditTimelineHtml', async (t) => {
  await t.test('an empty list renders an honest empty state, not a blank panel', () => {
    const html = auditTimelineHtml([]);
    assert.ok(html.includes('No recorded activity'));
  });

  await t.test('joins one row per event', () => {
    const html = auditTimelineHtml([
      { action: 'sos.acknowledge', outcome: 'applied', is_demo: false, metadata: {} },
      { action: 'sos.resolve', outcome: 'updated', is_demo: false, metadata: {} }
    ]);
    assert.ok(html.includes('Acknowledged SOS'));
    assert.ok(html.includes('Resolved SOS'));
  });
});
