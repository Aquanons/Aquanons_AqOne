'use strict';

// node --test web/test/dashboard-demo-mode.test.js
//
// docs/72_DASHBOARD_DEMO_MODE_IMPLEMENTATION_PLAN.md: the live dashboard shows
// only what the backend reports, and sample data lives only in the tutorial.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const {
  networkFromPublicBuoys, meshLinksFor, phoneCoverageFraction, buoyHeardText
} = require('../js/dashboard-utils.js');

const NOW = Date.parse('2026-09-27T08:00:00Z');

function buoy(overrides) {
  return Object.assign({
    id: 'B01', name: 'Buoy 01', latitude: 11.67, longitude: 122.46,
    coverage_radius_meters: 1300, lora_radius_meters: 7000, is_gateway_linked: true,
    is_synthetic: true, last_heard_at: '2026-09-27T07:55:00Z', status: 'active'
  }, overrides);
}

test('the network keeps an unplaced buoy listed but never places it', () => {
  const network = networkFromPublicBuoys({
    buoys: [buoy(), buoy({ id: 'BUOY01', name: 'BUOY01', latitude: null, longitude: null, coverage_radius_meters: null, status: 'unknown' })],
    shore_stations: [{ name: 'Dumaguit Port', lat: 11.67, lon: 122.41, type: 'Port Facility', role: 'Shore gateway' }]
  });
  assert.equal(network.buoys.length, 2);
  assert.deepEqual([network.buoys[1].lat, network.buoys[1].lng, network.buoys[1].wifiRadius], [null, null, null]);
  assert.equal(network.buoys[0].isSynthetic, true);
  assert.deepEqual(network.stations[0], { name: 'Dumaguit Port', lat: 11.67, lng: 122.41, type: 'Port Facility', role: 'Shore gateway' });
  assert.deepEqual(networkFromPublicBuoys(null), { buoys: [], stations: [] });
});

test('mesh links follow the LoRa ranges of placed buoys only', () => {
  const { buoys, stations } = networkFromPublicBuoys({
    buoys: [buoy(), buoy({ id: 'B02', latitude: 11.70, longitude: 122.46 }), buoy({ id: 'far', latitude: 12.5, longitude: 123.5 }),
      buoy({ id: 'unplaced', latitude: null, longitude: null })],
    shore_stations: [{ name: 'Hall', lat: 11.66, lon: 122.43 }]
  });
  const names = meshLinksFor(buoys, stations).map(([a, b]) => (a.id || a.name) + '-' + (b.id || b.name));
  assert.deepEqual(names, ['B01-B02', 'B01-Hall', 'B02-Hall']);
});

test('phone coverage is measured from the buoys, not invented', () => {
  const ring = [[11.60, 122.40], [11.60, 122.50], [11.70, 122.50], [11.70, 122.40], [11.60, 122.40]];
  assert.equal(phoneCoverageFraction(ring, []), null);
  const { buoys } = networkFromPublicBuoys({ buoys: [buoy({ latitude: 11.65, longitude: 122.45, coverage_radius_meters: 1000 })] });
  const share = phoneCoverageFraction(ring, buoys);
  // A 1 km circle in an 11 x 11 km square is about 2.6% of it.
  assert.ok(share > 0.015 && share < 0.04, String(share));
});

test('a buoy says when it was last heard', () => {
  assert.equal(buoyHeardText({ status: 'active', lastHeardAt: '2026-09-27T07:55:00Z' }, NOW), 'Heard 5 min ago');
  assert.equal(buoyHeardText({ status: 'silent', lastHeardAt: '2026-09-27T05:00:00Z' }, NOW), 'Silent, last heard 3 h ago');
  assert.equal(buoyHeardText({ status: 'unknown', lastHeardAt: null }, NOW), 'Never heard');
});

test('DEMO-07: the live dashboard source carries no sample network or figures', () => {
  const files = ['html/dashboard.html', 'js/dashboard/dashboard-core.js', 'js/dashboard/dashboard-markers.js',
    'js/dashboard/dashboard-buoy-health.js', 'js/dashboard/dashboard-sar.js'];
  const banned = ['Buoy Alpha', 'Buoy Echo', 'Squall Watch', 'Math.max(4', "'45 min'", '(68 +', 'Displaying sample data',
    'Sample buoy network', 'sample data for demonstration', 'initialBuoys', 'incidentDrawerData', '(simulated)'];
  for (const file of files) {
    const source = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    for (const text of banned) assert.ok(!source.includes(text), `${file} still contains ${text}`);
  }
});
