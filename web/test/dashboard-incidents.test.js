'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { utf8ByteLength } = require('../js/dashboard-utils.js');

const html = fs.readFileSync(path.join(__dirname, '../html/dashboard.html'), 'utf8');
const incidents = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-incidents.js'), 'utf8');
const core = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-core.js'), 'utf8');

test('resolve needs a reason and confirmation', () => {
  for (const code of ['rescued', 'safe_confirmed', 'stood_down_by_fisher', 'duplicate', 'closed_unconfirmed']) {
    assert.match(html, new RegExp('value="' + code + '"'));
  }
  assert.match(html, /id="resolve-btn-confirm" disabled/);
  assert.match(incidents, /reason_code: selected\.value, expected_version: target\.version/);
});

test('resolve offers a time-limited undo that posts reopen', () => {
  assert.match(core, /action \? 10000 : 4000/);
  assert.match(incidents, /label: 'Undo'/);
  assert.match(incidents, /\/reopen/);
});

test('ack defaults to no ETA and includes the quick choices and preview', () => {
  assert.match(html, /id="ack-eta" type="number"[^>]*value=""/);
  for (const minutes of ['15', '30', '45', '60', '90', '120']) assert.match(html, new RegExp('data-eta="' + minutes + '"'));
  assert.match(html, /id="ack-eta-preview"/);
  assert.match(incidents, /eta_minutes: etaMinutes/);
});

test('ack note is limited by UTF-8 bytes and carries the opened version', () => {
  assert.equal(utf8ByteLength('ñ'), 2);
  assert.match(incidents, /utf8ByteLength\(note\) > 40/);
  assert.match(incidents, /expected_version: target\.version/);
  assert.match(html, /id="ack-note-count"/);
});

test('409 displays the current answer and waits for another confirmation', () => {
  assert.match(incidents, /responder_status_label/);
  assert.match(incidents, /Confirm again/);
  assert.match(incidents, /ackTargetData\.version = current\.version/);
});

test('vessel confirmation is restricted to responder roles and posts the vessel id', () => {
  assert.match(incidents, /\['mdrrmo', 'lgu', 'admin'\]/);
  assert.match(incidents, /\/api\/vessels\/.*\/confirm/);
});

test('Escape can close the resolve dialog', () => {
  const shortcuts = fs.readFileSync(path.join(__dirname, '../js/dashboard/dashboard-shortcuts-weather.js'), 'utf8');
  assert.match(shortcuts, /ns\.closeResolveModal/);
  assert.match(incidents, /ns\.resolveOverlay = resolveOverlay;/);
  assert.match(incidents, /ns\.closeResolveModal = closeResolveModal;/);
});
