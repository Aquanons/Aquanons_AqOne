import 'delivery_state.dart';
import 'sos_record.dart';

/// Pure policy determining whether a foreground service should run to keep SOS delivery alive.
///
/// True while any record is `saved` or `relayed`.
/// False once all records are `delivered` or later (or if records is empty).
bool shouldRunForeground(Iterable<SosRecord> records) {
  return records.any(
    (record) =>
        record.state == DeliveryState.saved ||
        record.state == DeliveryState.relayed,
  );
}
