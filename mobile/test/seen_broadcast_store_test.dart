// docs/73 Rev 2 G2: a nearby broadcast rings once per phone, not once per
// app run. Acceptance tests written by the spec author; do not edit them to
// make them pass.

import 'dart:io';

import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/seen_broadcast_store.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfiNoIsolate;

  late Directory dir;
  setUp(() async => dir = await Directory.systemTemp.createTemp('aqone_seen_'));
  tearDown(() async => dir.delete(recursive: true));

  test('a seen broadcast stays seen after the app restarts', () async {
    final path = '${dir.path}/aqone.db';

    final first = AppDatabase(overridePath: path);
    final store = SeenBroadcastStore(first);
    expect(await store.markSeen(7), isTrue);
    expect(await store.markSeen(7), isFalse);
    await first.close();

    final second = AppDatabase(overridePath: path);
    final reopened = SeenBroadcastStore(second);
    expect(await reopened.markSeen(7), isFalse);
    expect(await reopened.markSeen(8), isTrue);
    await second.close();
  });

  test('a phone upgrading from database version 15 gains the store', () async {
    final path = '${dir.path}/old.db';
    final old = await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(version: 15, onCreate: (db, _) async {}),
    );
    await old.close();

    final upgraded = AppDatabase(overridePath: path);
    expect(await SeenBroadcastStore(upgraded).markSeen(1), isTrue);
    await upgraded.close();
  });
}
