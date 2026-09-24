'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('ops status displays stale gateway, missing SMS setup, and near database expiry', async () => {
  const values = new Map();
  const document = { getElementById(id) { if (!values.has(id)) values.set(id, { textContent: '', className: '', hidden: false }); return values.get(id); } };
  let status = { gateway_stale: false, gateway_last_poll_at: '2026-09-24T10:00:00Z', sms_configured: true, db_days_left: 8 };
  const ns = { ready: true, authFetch: async () => ({ ok: true, json: async () => status }) };
  const window = { document, AqOneDashboard: ns };
  const source = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ops-status.js'), 'utf8');
  vm.runInNewContext(source, { window, document, setInterval() {}, Number });
  await ns.pollOpsStatus();
  status = { gateway_stale: true, gateway_last_poll_at: null, sms_configured: false, db_days_left: 7, db_expires_at: '2026-10-01T00:00:00Z' };
  await ns.pollOpsStatus();
  assert.equal(values.get('ops-gateway-status').className, 'ops-gateway-stale');
  assert.equal(values.get('ops-sms-banner').textContent, 'SMS escalation not configured');
  assert.equal(values.get('ops-sms-banner').hidden, false);
  assert.match(values.get('ops-db-banner').textContent, /expires in 7 days/);
  assert.equal(values.get('ops-db-banner').hidden, false);
});

test('session refresh follows the frozen operator-session contract', () => {
  const core = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-core.js'), 'utf8');
  assert.match(core, /\/api\/token\/refresh/);
  assert.match(core, /24 \* 3600000/);
  assert.match(core, /3600000/);
  assert.match(core, /visibilityState === 'hidden'/);
});

test('AI operations surface unavailable monitoring, check-needed, and suspect clocks', () => {
  const source = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-ai-ops.js'), 'utf8');
  assert.match(source, /Not monitoring - no live contact source/);
  assert.match(source, /CHECK NEEDED/);
  assert.match(source, /payload\.clock_suspect/);
});
