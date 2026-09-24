import 'package:aqone/models/delivery_policy.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:flutter_test/flutter_test.dart';

SosRecord _makeRecord({
  required DeliveryState state,
  int clientTs = 1755248500,
  int? relayedAt,
  int? lastAttemptAt,
  int attempts = 0,
}) {
  return SosRecord(
    localId: 'test-local-id',
    vesselId: 'fisher-001',
    boat: 'Boat 1',
    clientTs: clientTs,
    state: state,
    relayedAt: relayedAt,
    lastAttemptAt: lastAttemptAt,
    attempts: attempts,
  );
}

void main() {
  group('routesDue', () {
    final baseTime = DateTime.utc(2026, 9, 25, 12, 0, 0);

    test('saved gives {pod, direct}', () {
      final record = _makeRecord(state: DeliveryState.saved);
      expect(routesDue(record, baseTime), {SosRoute.pod, SosRoute.direct});
    });

    test('delivered and acknowledged give {}', () {
      final delivered = _makeRecord(state: DeliveryState.delivered);
      expect(routesDue(delivered, baseTime), isEmpty);

      final acknowledged = _makeRecord(state: DeliveryState.acknowledged);
      expect(routesDue(acknowledged, baseTime), isEmpty);
    });

    test('relayed inside the current backoff step gives {}', () {
      // 1 prior attempt (initial attempt, 20s backoff), last attempt was 10s ago
      final record = _makeRecord(
        state: DeliveryState.relayed,
        relayedAt: baseTime.millisecondsSinceEpoch ~/ 1000 - 10,
        lastAttemptAt: baseTime.millisecondsSinceEpoch ~/ 1000 - 10,
        attempts: 1,
      );
      expect(routesDue(record, baseTime), isEmpty);
    });

    test('relayed after 20 s, then 60 s, then 5 min backoff gives {direct}', () {
      final nowSec = baseTime.millisecondsSinceEpoch ~/ 1000;

      // 1 attempt (or 0) -> 20s backoff; 25s elapsed since last attempt
      final r0 = _makeRecord(
        state: DeliveryState.relayed,
        relayedAt: nowSec - 25,
        lastAttemptAt: nowSec - 25,
        attempts: 1,
      );
      expect(routesDue(r0, baseTime), {SosRoute.direct});

      // 2 attempts -> 60s backoff; 50s elapsed (inside backoff -> {})
      final r1Inside = _makeRecord(
        state: DeliveryState.relayed,
        relayedAt: nowSec - 70,
        lastAttemptAt: nowSec - 50,
        attempts: 2,
      );
      expect(routesDue(r1Inside, baseTime), isEmpty);

      // 2 attempts -> 60s backoff; 65s elapsed (after 60s -> {direct})
      final r1 = _makeRecord(
        state: DeliveryState.relayed,
        relayedAt: nowSec - 90,
        lastAttemptAt: nowSec - 65,
        attempts: 2,
      );
      expect(routesDue(r1, baseTime), {SosRoute.direct});

      // 3 attempts -> 5 min (300s) backoff; 200s elapsed (inside backoff -> {})
      final r2Inside = _makeRecord(
        state: DeliveryState.relayed,
        relayedAt: nowSec - 500,
        lastAttemptAt: nowSec - 200,
        attempts: 3,
      );
      expect(routesDue(r2Inside, baseTime), isEmpty);

      // 3 attempts -> 5 min (300s) backoff; 310s elapsed (after 5 min -> {direct})
      final r2 = _makeRecord(
        state: DeliveryState.relayed,
        relayedAt: nowSec - 550,
        lastAttemptAt: nowSec - 310,
        attempts: 3,
      );
      expect(routesDue(r2, baseTime), {SosRoute.direct});
    });

    test('relayed with no delivery 10 min after relayedAt gives {direct, pod}', () {
      final nowSec = baseTime.millisecondsSinceEpoch ~/ 1000;
      // 10 minutes (600s) after relayedAt
      final record = _makeRecord(
        state: DeliveryState.relayed,
        relayedAt: nowSec - 601,
        lastAttemptAt: nowSec - 10, // even if last direct attempt was recent
        attempts: 1,
      );
      expect(routesDue(record, baseTime), {SosRoute.direct, SosRoute.pod});
    });
  });

  group('isStale', () {
    final baseTime = DateTime.utc(2026, 9, 25, 12, 0, 0);
    final nowSec = baseTime.millisecondsSinceEpoch ~/ 1000;

    test('saved and older than 12 h is true', () {
      final record = _makeRecord(
        state: DeliveryState.saved,
        clientTs: nowSec - (12 * 3600 + 60), // 12 hours 1 min ago
      );
      expect(isStale(record, baseTime), isTrue);
    });

    test('relayed or newer is false', () {
      // saved but only 2 hours old
      final savedNewer = _makeRecord(
        state: DeliveryState.saved,
        clientTs: nowSec - (2 * 3600),
      );
      expect(isStale(savedNewer, baseTime), isFalse);

      // relayed even if older than 12 hours
      final relayedOld = _makeRecord(
        state: DeliveryState.relayed,
        clientTs: nowSec - (13 * 3600),
        relayedAt: nowSec - (13 * 3600),
      );
      expect(isStale(relayedOld, baseTime), isFalse);
    });
  });
}
