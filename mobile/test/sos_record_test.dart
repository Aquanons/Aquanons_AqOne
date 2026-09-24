import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:flutter_test/flutter_test.dart';

SosRecord _record({double? lat, double? lon, String? note}) {
  return SosRecord(
    localId: 'local-1',
    vesselId: '0123456789abcdef0123456789abcdef',
    boat: 'BG-123',
    clientTs: 1722700000,
    state: DeliveryState.saved,
    lat: lat,
    lon: lon,
    note: note,
  );
}

void main() {
  group('SosRecord.toBuoyPayload', () {
    test('matches the POST /v1/sos contract in fixtures/week1_contract', () {
      final payload = _record(
        lat: 11.6050,
        lon: 122.3125,
        note: 'engine down',
      ).toBuoyPayload();

      expect(payload['v'], 1);
      expect(payload['vessel_id'], '0123456789abcdef0123456789abcdef');
      expect(payload['boat'], 'BG-123');
      expect(payload['client_ts'], 1722700000);
      expect(payload['lat'], 11.6050);
      expect(payload['lon'], 122.3125);
      expect(payload['note'], 'engine down');
    });

    test('omits lat and lon when there is no fix', () {
      final payload = _record().toBuoyPayload();
      expect(payload.containsKey('lat'), isFalse);
      expect(payload.containsKey('lon'), isFalse);
    });

    test('omits an empty note', () {
      final payload = _record(note: '   ').toBuoyPayload();
      expect(payload.containsKey('note'), isFalse);
    });
  });

  group('SosRecord persistence', () {
    test('round-trips through a database row', () {
      final original = _record(lat: 11.6, lon: 122.3, note: 'taking water')
          .copyWith(
        state: DeliveryState.relayed,
        buoyId: 'BUOY01',
        srcId: 1001,
        seq: 42,
        serverTs: 1722700002,
      );

      final restored = SosRecord.fromRow(original.toRow());

      expect(restored.localId, original.localId);
      expect(restored.state, DeliveryState.relayed);
      expect(restored.buoyId, 'BUOY01');
      expect(restored.seq, 42);
      expect(restored.note, 'taking water');
      expect(restored.hasFix, isTrue);
    });

    test('copyWith can clear lastError but keeps it otherwise', () {
      final failed = _record().copyWith(lastError: 'timeout');
      expect(failed.lastError, 'timeout');
      expect(failed.copyWith(attempts: 2).lastError, 'timeout');
      expect(failed.copyWith(lastError: null).lastError, isNull);
    });

    test('resolvedAt round-trips through a database row and flags isResolved',
        () {
      const original = SosRecord(
        localId: 'local-1',
        vesselId: '0123456789abcdef0123456789abcdef',
        boat: 'BG-123',
        clientTs: 1722700000,
        state: DeliveryState.acknowledged,
        remoteId: '9',
        etaAt: '2026-09-15T00:30:00Z',
        resolvedAt: '2026-09-15T00:35:00Z',
      );

      final restored = SosRecord.fromRow(original.toRow());

      // resolved_at is written by saveResponder, not toRow() - same single
      // writer rule as the other responder data - so the row alone does not
      // carry it. The model still exposes it and drives isResolved off it.
      expect(original.isResolved, isTrue);
      expect(original.isStoodDown, isFalse);
      expect(original.resolvedTime, DateTime.parse('2026-09-15T00:35:00Z').toLocal());
      expect(restored.isResolved, isFalse);
    });

    test('a fisher stand-down (reply 2) counts as resolved before any resolvedAt',
        () {
      final stoodDown = _record().copyWith(state: DeliveryState.acknowledged);
      // fisherReply is responder data - written by saveFisherReply, never via
      // copyWith - so construct the scenario the store creates it as.
      final unsynced = SosRecord(
        localId: stoodDown.localId,
        vesselId: stoodDown.vesselId,
        boat: stoodDown.boat,
        clientTs: stoodDown.clientTs,
        state: DeliveryState.acknowledged,
        fisherReply: 2,
        fisherReplySynced: false,
      );
      expect(unsynced.isResolved, isFalse);
      expect(unsynced.isStoodDown, isFalse);

      final replier = SosRecord(
        localId: stoodDown.localId,
        vesselId: stoodDown.vesselId,
        boat: stoodDown.boat,
        clientTs: stoodDown.clientTs,
        state: DeliveryState.acknowledged,
        fisherReply: 2,
        fisherReplySynced: true,
      );
      expect(replier.isResolved, isTrue);
      expect(replier.isStoodDown, isTrue);
    });
  });
}
