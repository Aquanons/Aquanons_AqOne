import 'dart:convert';

import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class _FakeBackendClient extends http.BaseClient {
  _FakeBackendClient(this._handler);

  final Future<http.StreamedResponse> Function(http.BaseRequest request)
      _handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) =>
      _handler(request);
}

Future<http.StreamedResponse> _direct(int statusCode) async {
  return http.StreamedResponse(
    Stream<List<int>>.value(utf8.encode('{}')),
    statusCode,
  );
}

SosRecord _record(String localId) {
  return SosRecord(
    localId: localId,
    vesselId: 'fisher-7f3a',
    boat: 'BG-123',
    clientTs: 1755248500,
    state: DeliveryState.saved,
  );
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late AppDatabase db;
  late OutboxStore outbox;

  setUp(() {
    db = AppDatabase(overridePath: inMemoryDatabasePath);
    outbox = OutboxStore(db);
  });

  tearDown(() async {
    await db.close();
  });

  SosService buildService({
    required BuoyClient buoy,
    required BackendClient backend,
  }) {
    return SosService(
      outbox: outbox,
      identity: IdentityStore(db),
      buoy: buoy,
      backend: backend,
      location: LocationService(),
    );
  }

  test('direct-only success advances the record to delivered', () async {
    final record = _record('local-direct-only');
    await outbox.insert(record);

    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        throw const FormatException('no buoy in range');
      }),
    );
    final backend = BackendClient(
      client: _FakeBackendClient((_) => _direct(200)),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.retryPending();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.state, DeliveryState.delivered);
    expect(updated.buoyId, isNull);
  });

  test('buoy-only success advances the record to relayed with buoy metadata',
      () async {
    final record = _record('local-buoy-only');
    await outbox.insert(record);

    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        return http.Response(
          jsonEncode(<String, Object?>{
            'accepted': true,
            'buoy_id': 'BUOY01',
            'seq': 42,
            'server_ts': 172963201,
          }),
          200,
        );
      }),
    );
    final backend = BackendClient(
      client: _FakeBackendClient((_) async {
        throw Exception('no internet connection');
      }),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.retryPending();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.state, DeliveryState.relayed);
    expect(updated.buoyId, 'BUOY01');
    expect(updated.seq, 42);
  });

  test(
      'both routes succeeding finishes at delivered without losing buoy metadata',
      () async {
    final record = _record('local-both-succeed');
    await outbox.insert(record);

    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        return http.Response(
          jsonEncode(<String, Object?>{
            'accepted': true,
            'buoy_id': 'BUOY01',
            'seq': 42,
            'server_ts': 172963201,
          }),
          200,
        );
      }),
    );
    final backend = BackendClient(
      client: _FakeBackendClient((_) => _direct(200)),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.retryPending();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.state, DeliveryState.delivered);
    // The direct success must not have wiped out what the buoy already
    // recorded - see SosService._attemptRelay()'s doc comment.
    expect(updated.buoyId, 'BUOY01');
    expect(updated.seq, 42);
  });

  test('both routes failing leaves the record at saved with a useful reason',
      () async {
    final record = _record('local-both-fail');
    await outbox.insert(record);

    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        throw const FormatException('unreachable');
      }),
    );
    final backend = BackendClient(
      client: _FakeBackendClient((_) async {
        throw Exception('no internet connection');
      }),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.retryPending();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.state, DeliveryState.saved);
    expect(updated.attempts, greaterThan(0));
    expect(updated.lastError, isNotNull);
    expect(updated.lastError, isNotEmpty);
  });

  test('un-enrolled handset reads its own ack by local_id over the direct path',
      () async {
    final record = _record('local-ack');
    await outbox.insert(record);
    await outbox.advance(record.localId, DeliveryState.delivered);

    final serverNow = DateTime.now().toUtc();
    final etaAt = serverNow
        .add(const Duration(minutes: 20))
        .toIso8601String();

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') {
          return _direct(200);
        }
        if (request.url.path == '/api/sos/ack/local-ack') {
          return http.StreamedResponse(
            Stream<List<int>>.value(utf8.encode(jsonEncode(<String, Object?>{
              'vessel_id': 'fisher-7f3a',
              'server_time': serverNow.toIso8601String(),
              'event': <String, Object?>{
                'id': 7,
                'local_id': 'local-ack',
                'seq': null,
                'client_ts': 1755248500,
                'delivery_state': 'acknowledged',
                'acknowledged_at': '2026-09-15T00:05:00Z',
                'acked_by': 'ranger@example.com',
                'eta_at': etaAt,
                'responder_status': 2,
                'responder_status_label': 'Rescue boat on the way',
                'responder_note': 'On the way',
                'fisher_reply': null,
                'resolved_at': null,
              },
            }))),
            200,
          );
        }
        throw Exception('unexpected ${request.url.path}');
      }),
    );
    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        throw const FormatException('no buoy in range');
      }),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.reconcile();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.state, DeliveryState.acknowledged);
    expect(updated.etaAt, isNotNull);
    expect(updated.etaOverdue, isFalse);
    expect(updated.responderStatus, 2);
    expect(updated.responderNote, 'On the way');
    // The fisher's reply needs the backend id, which was previously only ever
    // learned through the credentialed vessel feed.
    expect(updated.remoteId, '7');
  });

  test(
      'an ack read-back that reports resolved_at stores it and closes the incident',
      () async {
    final record = _record('local-resolved');
    await outbox.insert(record);
    await outbox.advance(record.localId, DeliveryState.acknowledged);

    const resolvedAt = '2026-09-15T00:35:00Z';
    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') {
          return _direct(200);
        }
        if (request.url.path == '/api/sos/ack/local-resolved') {
          return http.StreamedResponse(
            Stream<List<int>>.value(utf8.encode(jsonEncode(<String, Object?>{
              'vessel_id': 'fisher-7f3a',
              'server_time': '2026-09-15T00:36:00Z',
              'event': <String, Object?>{
                'id': 8,
                'local_id': 'local-resolved',
                'seq': null,
                'client_ts': 1755248500,
                'delivery_state': 'acknowledged',
                'acknowledged_at': '2026-09-15T00:05:00Z',
                'acked_by': 'ranger@example.com',
                'eta_at': '2026-09-15T00:30:00Z',
                'responder_status': 2,
                'responder_status_label': 'Rescue boat on the way',
                'responder_note': null,
                'fisher_reply': null,
                'resolved_at': resolvedAt,
              },
            }))),
            200,
          );
        }
        throw Exception('unexpected ${request.url.path}');
      }),
    );
    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        throw const FormatException('no buoy in range');
      }),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.reconcile();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.resolvedAt, resolvedAt);
    expect(updated.isResolved, isTrue);
    expect(updated.isStoodDown, isFalse);
  });

  test('a 404 from the ack read-back leaves the delivered record untouched',
      () async {
    final record = _record('local-pending');
    await outbox.insert(record);
    await outbox.advance(record.localId, DeliveryState.delivered);

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') {
          return _direct(200);
        }
        if (request.url.path == '/api/sos/ack/local-pending') {
          return http.StreamedResponse(
            Stream<List<int>>.value(
              utf8.encode(jsonEncode(<String, Object?>{'detail': 'no such SOS event'})),
            ),
            404,
          );
        }
        throw Exception('unexpected ${request.url.path}');
      }),
    );
    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        throw const FormatException('no buoy in range');
      }),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.reconcile();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.state, DeliveryState.delivered);
    expect(updated.etaAt, isNull);
    expect(updated.remoteId, isNull);
  });

  test('a direct SOS success re-pushes the vessel profile', () async {
    final identityStore = IdentityStore(db);
    await identityStore.ensure(
      boat: 'BG-123',
      skipperName: 'Jade N. Salvador',
      phone: '+639950588358',
    );
    final record = _record('local-profile-repush');
    await outbox.insert(record);

    final profileBodies = <String>[];
    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path.endsWith('/api/vessel-profile') &&
            request is http.Request) {
          profileBodies.add(request.body);
        }
        return _direct(200);
      }),
    );
    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        throw const FormatException('no buoy in range');
      }),
    );

    final service = SosService(
      outbox: outbox,
      identity: identityStore,
      buoy: buoy,
      backend: backend,
      location: LocationService(),
    );
    await service.retryPending();

    final deadline = DateTime.now().add(const Duration(seconds: 5));
    while (profileBodies.isEmpty && DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(const Duration(milliseconds: 20));
    }
    expect(profileBodies, hasLength(1));
    expect(profileBodies.single, contains('Jade N. Salvador'));
  });

  // The ack read-back for [localId], as GET /api/sos/ack/{local_id} returns it.
  http.StreamedResponse ackEnvelope(
    String localId, {
    required String serverTime,
    String? etaAt,
    int? fisherReply,
  }) {
    return http.StreamedResponse(
      Stream<List<int>>.value(utf8.encode(jsonEncode(<String, Object?>{
        'vessel_id': 'fisher-7f3a',
        'server_time': serverTime,
        'event': <String, Object?>{
          'id': 7,
          'local_id': localId,
          'seq': null,
          'client_ts': 1755248500,
          'delivery_state': 'acknowledged',
          'acknowledged_at': '2026-09-15T00:05:00Z',
          'acked_by': 'ranger@example.com',
          'eta_at': etaAt,
          'responder_status': 2,
          'responder_status_label': 'Rescue boat on the way',
          'responder_note': 'On the way',
          'fisher_reply': fisherReply,
          'resolved_at': null,
        },
      }))),
      200,
    );
  }

  BuoyClient noBuoy() => BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async {
          throw const FormatException('no buoy in range');
        }),
      );

  test(
      'SEC-20 review: a failed stand-down stays pending when the backend '
      'only has the earlier "still in danger" reply', () async {
    final record = _record('local-reply-mismatch');
    await outbox.insert(record);
    await outbox.advance(record.localId, DeliveryState.acknowledged);
    await outbox.saveResponder(record.localId, remoteId: '7');
    await outbox.saveFisherReply(record.localId, 1, synced: true);

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') {
          return _direct(200);
        }
        if (request.url.path == '/api/sos/ack/local-reply-mismatch') {
          return ackEnvelope(
            'local-reply-mismatch',
            serverTime: DateTime.now().toUtc().toIso8601String(),
            fisherReply: 1,
          );
        }
        // The stand-down itself (and its SEC-21 re-post) never gets through.
        return _direct(503);
      }),
    );

    final service = buildService(buoy: noBuoy(), backend: backend);
    await service.standDown(record.localId);
    await service.reconcile();

    final updated = await outbox.byLocalId(record.localId);
    expect(updated!.fisherReply, 2);
    expect(
      updated.fisherReplySynced,
      isFalse,
      reason: 'the backend still reports reply 1, so the stand-down (reply 2) '
          'has not reached it',
    );
    expect(updated.isStoodDown, isFalse);
  });

  test(
      'SEC-22 review: an unchanged ETA is not rewritten on every reconcile '
      'tick', () async {
    final record = _record('local-eta-stable');
    await outbox.insert(record);
    await outbox.advance(record.localId, DeliveryState.delivered);

    final serverNow = DateTime.now().toUtc();
    final etaAt = serverNow.add(const Duration(minutes: 20)).toIso8601String();

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') {
          return _direct(200);
        }
        if (request.url.path == '/api/sos/ack/local-eta-stable') {
          return ackEnvelope(
            'local-eta-stable',
            serverTime: serverNow.toIso8601String(),
            etaAt: etaAt,
          );
        }
        throw Exception('unexpected ${request.url.path}');
      }),
    );

    final service = buildService(buoy: noBuoy(), backend: backend);
    await service.reconcile();
    final first = await outbox.byLocalId(record.localId);

    var changes = 0;
    final sub = service.changes.listen((_) => changes++);
    await Future<void>.delayed(const Duration(milliseconds: 5));
    await service.reconcile();
    await Future<void>.delayed(Duration.zero);
    await sub.cancel();
    final second = await outbox.byLocalId(record.localId);

    expect(first!.etaAt, isNotNull);
    expect(
      second!.etaAt,
      first.etaAt,
      reason: 'the backend answered with the same eta_at, so the stored '
          'device-clock ETA must not move',
    );
    expect(changes, 0, reason: 'an identical answer is not a change');
  });
}
