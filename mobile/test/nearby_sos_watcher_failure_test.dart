// A dropped signal at sea is not "no emergencies": the watcher keeps the last
// nearby calls and the alarm until the feed answers again (review of
// 2026-10-01 on fix/reconcile-2026-09-30).

import 'dart:io';

import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/seen_broadcast_store.dart';
import 'package:aqone/models/nearby_sos.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/nearby_alarm.dart';
import 'package:aqone/services/nearby_sos_watcher.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class _CountingAlarm implements NearbyAlarm {
  int stops = 0;

  @override
  Future<void> stop() async => stops += 1;

  @override
  dynamic noSuchMethod(Invocation invocation) => Future<void>.value();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfiNoIsolate;

  test('an unreachable feed keeps the last calls and does not stop the alarm', () async {
    final dir = await Directory.systemTemp.createTemp('aqone_watch_fail_');
    final db = AppDatabase(overridePath: '${dir.path}/aqone.db');
    final alarm = _CountingAlarm();
    var reachable = true;
    final watcher = NearbySosWatcher(
      fetch: (lat, lon) async {
        if (!reachable) throw StateError('no signal');
        return const <NearbySos>[
          NearbySos(broadcastId: 1, sosEventId: 10, centerLat: 11.70, centerLon: 122.44, distanceKm: 2.3),
        ];
      },
      position: () async => const Fix(lat: 11.71, lon: 122.45),
      seen: SeenBroadcastStore(db),
      alarm: alarm,
      notify: (_) async {},
    );

    await watcher.poll();
    reachable = false;
    await watcher.poll();

    expect(watcher.items.value.map((n) => n.broadcastId), <int>[1]);
    expect(alarm.stops, 0);

    watcher.dispose();
    await db.close();
    await dir.delete(recursive: true);
  });
}
