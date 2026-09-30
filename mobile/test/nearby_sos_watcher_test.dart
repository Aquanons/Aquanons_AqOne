// docs/73 Rev 2 G2 and G3: nearby broadcasts are watched app-wide by the
// shell, not only once the At sea screen has been opened, and each broadcast
// rings and notifies once per phone. Acceptance tests written by the spec
// author; do not edit them to make them pass.

import 'dart:io';

import 'package:aqone/core/config.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/seen_broadcast_store.dart';
import 'package:aqone/models/nearby_sos.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/nearby_alarm.dart';
import 'package:aqone/services/nearby_sos_watcher.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

// `implements`, not `extends`: constructing a real NearbyAlarm creates an
// AudioPlayer, whose platform channel fails outside a device.
class _CountingAlarm implements NearbyAlarm {
  int starts = 0;
  int stops = 0;

  @override
  Future<void> start() async => starts += 1;

  @override
  Future<void> stop() async => stops += 1;

  @override
  dynamic noSuchMethod(Invocation invocation) => Future<void>.value();
}

NearbySos _item(int id, {double km = 2.34}) => NearbySos(
      broadcastId: id,
      sosEventId: id * 10,
      centerLat: 11.70,
      centerLon: 122.44,
      distanceKm: km,
      radiusKm: 10,
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfiNoIsolate;

  late Directory dir;
  late AppDatabase db;
  setUp(() async {
    dir = await Directory.systemTemp.createTemp('aqone_watch_');
    db = AppDatabase(overridePath: '${dir.path}/aqone.db');
  });
  tearDown(() async {
    await db.close();
    await dir.delete(recursive: true);
  });

  NearbySosWatcher watcher({
    required List<NearbySos> Function() feed,
    required _CountingAlarm alarm,
    required List<int> notified,
    Fix? fix = const Fix(lat: 11.71, lon: 122.45),
    List<List<double>>? asked,
  }) {
    return NearbySosWatcher(
      fetch: (lat, lon) async {
        asked?.add(<double>[lat, lon]);
        return feed();
      },
      position: () async => fix,
      seen: SeenBroadcastStore(db),
      alarm: alarm,
      notify: (item) async => notified.add(item.broadcastId),
    );
  }

  test('a new broadcast rings and notifies once, and is published', () async {
    final alarm = _CountingAlarm();
    final notified = <int>[];
    final w = watcher(feed: () => <NearbySos>[_item(1)], alarm: alarm, notified: notified);
    final sightings = <int>[];
    final sub = w.firstSightings.listen((n) => sightings.add(n.broadcastId));

    await w.poll();
    await w.poll();
    await Future<void>.delayed(Duration.zero);

    expect(w.items.value.map((n) => n.broadcastId), <int>[1]);
    expect(w.hasFix, isTrue);
    expect(alarm.starts, 1);
    expect(notified, <int>[1]);
    expect(sightings, <int>[1]);
    await sub.cancel();
    w.dispose();
  });

  test('a broadcast already seen before a restart does not ring again', () async {
    final notified = <int>[];
    final before = watcher(feed: () => <NearbySos>[_item(1)], alarm: _CountingAlarm(), notified: notified);
    await before.poll();
    before.dispose();

    final alarm = _CountingAlarm();
    final after = watcher(feed: () => <NearbySos>[_item(1)], alarm: alarm, notified: notified);
    await after.poll();

    expect(after.items.value.length, 1, reason: 'still shown, just not rung again');
    expect(alarm.starts, 0);
    expect(notified, <int>[1]);
    after.dispose();
  });

  test('when every broadcast ends the list clears and the alarm stops', () async {
    final alarm = _CountingAlarm();
    var rows = <NearbySos>[_item(1)];
    final w = watcher(feed: () => rows, alarm: alarm, notified: <int>[]);
    await w.poll();
    rows = <NearbySos>[];
    await w.poll();

    expect(w.items.value, isEmpty);
    expect(alarm.stops, greaterThanOrEqualTo(1));
    w.dispose();
  });

  test('without a GPS fix it asks around the default map centre and says so', () async {
    final asked = <List<double>>[];
    final w = watcher(
      feed: () => <NearbySos>[_item(1)],
      alarm: _CountingAlarm(),
      notified: <int>[],
      fix: null,
      asked: asked,
    );
    await w.poll();

    expect(asked.single, <double>[AqOneConfig.defaultMapLat, AqOneConfig.defaultMapLon]);
    expect(w.hasFix, isFalse);
    expect(w.items.value.length, 1, reason: 'no fix must never hide an emergency');
    w.dispose();
  });

  test('silence stops the alarm but keeps the broadcast listed', () async {
    final alarm = _CountingAlarm();
    final w = watcher(feed: () => <NearbySos>[_item(1)], alarm: alarm, notified: <int>[]);
    await w.poll();
    await w.silence();

    expect(alarm.stops, 1);
    expect(w.items.value.length, 1);
    w.dispose();
  });
}
