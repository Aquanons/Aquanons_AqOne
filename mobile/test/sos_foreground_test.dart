import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_foreground.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  test('SosForeground evaluates outbox records on service changes', () async {
    final db = AppDatabase(overridePath: inMemoryDatabasePath);
    final outbox = OutboxStore(db);
    final identity = IdentityStore(db);
    final sosService = SosService(
      outbox: outbox,
      identity: identity,
      buoy: BuoyClient(),
      backend: BackendClient(),
      location: LocationService(),
    );

    final foreground = SosForeground(
      outbox: outbox,
      sosService: sosService,
      titleResolver: () => 'Test Title',
      bodyResolver: () => 'Test Body',
    );

    foreground.startListening();

    // With empty outbox, evaluate completes without error
    await foreground.evaluate();

    // Insert a pending record
    await outbox.insert(
      const SosRecord(
        localId: 'fg-1',
        vesselId: 'v-1',
        boat: 'B-1',
        clientTs: 1000,
        state: DeliveryState.saved,
      ),
    );

    // evaluate handles saved record cleanly
    await foreground.evaluate();

    // Advance to delivered
    await outbox.advance('fg-1', DeliveryState.delivered);

    // evaluate handles delivered record cleanly
    await foreground.evaluate();

    foreground.dispose();
    sosService.dispose();
  });
}
