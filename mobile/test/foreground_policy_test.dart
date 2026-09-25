import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/foreground_policy.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:flutter_test/flutter_test.dart';

SosRecord _makeRecord({
  required String id,
  required DeliveryState state,
}) {
  return SosRecord(
    localId: id,
    vesselId: 'fisher-001',
    boat: 'Boat 1',
    clientTs: 1755248500,
    state: state,
  );
}

void main() {
  group('shouldRunForeground', () {
    test('returns true while any record is saved', () {
      final records = [
        _makeRecord(id: '1', state: DeliveryState.saved),
      ];
      expect(shouldRunForeground(records), isTrue);
    });

    test('returns true while any record is relayed', () {
      final records = [
        _makeRecord(id: '1', state: DeliveryState.relayed),
      ];
      expect(shouldRunForeground(records), isTrue);
    });

    test('returns true for mixed records containing at least one pending record', () {
      final records = [
        _makeRecord(id: '1', state: DeliveryState.delivered),
        _makeRecord(id: '2', state: DeliveryState.relayed),
        _makeRecord(id: '3', state: DeliveryState.acknowledged),
      ];
      expect(shouldRunForeground(records), isTrue);
    });

    test('returns false once all records are delivered or later', () {
      final records = [
        _makeRecord(id: '1', state: DeliveryState.delivered),
        _makeRecord(id: '2', state: DeliveryState.acknowledged),
      ];
      expect(shouldRunForeground(records), isFalse);
    });

    test('returns false when records list is empty', () {
      expect(shouldRunForeground([]), isFalse);
    });
  });
}
