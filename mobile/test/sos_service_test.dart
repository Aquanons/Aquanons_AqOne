import 'dart:convert';

import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/models/delivery_policy.dart';
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
    String? resolvedAt,
    String? resolutionCode,
    String? reopenedAt,
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
          'resolved_at': resolvedAt,
          'resolution_code': resolutionCode,
          'reopened_at': reopenedAt,
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

  test('relayed record retries direct until delivered', () async {
    final record = _record('local-relay-retry');
    await outbox.insert(record);

    var buoyCalls = 0;
    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        buoyCalls++;
        return http.Response(
          jsonEncode(<String, Object?>{
            'accepted': true,
            'buoy_id': 'BUOY01',
            'seq': 10,
            'server_ts': 172963201,
          }),
          200,
        );
      }),
    );

    var backendAttempts = 0;
    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/api/sos') {
          backendAttempts++;
          if (backendAttempts == 1) {
            throw Exception('no internet connection');
          }
          return _direct(200);
        }
        return _direct(200);
      }),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.retryPending();

    var current = await outbox.byLocalId(record.localId);
    expect(current!.state, DeliveryState.relayed);
    expect(buoyCalls, 1);
    expect(backendAttempts, 1);

    // Advance time past the 20s direct backoff for attempt 1
    final dbInstance = await db.database;
    final past = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000 - 25;
    await dbInstance.rawUpdate(
      'UPDATE outbox SET last_attempt_at = ?, relayed_at = ? WHERE local_id = ?',
      <Object?>[past, past, record.localId],
    );

    await service.retryPending();

    current = await outbox.byLocalId(record.localId);
    expect(current!.state, DeliveryState.delivered);
    expect(backendAttempts, 2);
  });

  test('delivered record is never retried', () async {
    final record = _record('local-delivered');
    await outbox.insert(record);
    await outbox.advance(record.localId, DeliveryState.delivered);

    var buoyCalls = 0;
    var backendCalls = 0;
    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((_) async {
        buoyCalls++;
        return http.Response('{}', 200);
      }),
    );
    final backend = BackendClient(
      client: _FakeBackendClient((_) async {
        backendCalls++;
        return _direct(200);
      }),
    );

    final service = buildService(buoy: buoy, backend: backend);
    await service.retryPending();

    expect(buoyCalls, 0);
    expect(backendCalls, 0);
  });

  test('stale unsent record is reported, not dropped', () async {
    final staleRecord = SosRecord(
      localId: 'stale-1',
      vesselId: 'fisher-7f3a',
      boat: 'BG-123',
      clientTs:
          DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000 - (13 * 3600),
      state: DeliveryState.saved,
    );
    await outbox.insert(staleRecord);

    final service = buildService(
      buoy: noBuoy(),
      backend: BackendClient(client: _FakeBackendClient((_) => _direct(200))),
    );
    final history = await service.history();
    expect(history.any((r) => r.localId == 'stale-1'), isTrue);
    expect(isStale(staleRecord, DateTime.now()), isTrue);
  });

  test('raiseSos assigns a 32-bit nonce and sends it on both routes', () async {
    final identityStore = IdentityStore(db);
    await identityStore.ensure(boat: 'Sea Breeze', skipperName: 'Pedro');
    Map<String, dynamic>? buoyPayload;
    Map<String, dynamic>? backendPayload;

    final buoy = BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((request) async {
        buoyPayload = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'accepted': true, 'seq': 1}), 200);
      }),
    );

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/api/sos') {
          final bodyBytes = await request.finalize().toBytes();
          backendPayload = jsonDecode(utf8.decode(bodyBytes)) as Map<String, dynamic>;
        }
        return _direct(200);
      }),
    );

    final service = SosService(
      outbox: outbox,
      identity: identityStore,
      buoy: buoy,
      backend: backend,
      location: LocationService(),
    );

    final record = await service.raiseSos();
    expect(record.nonce, isNotNull);
    expect(record.nonce!, greaterThanOrEqualTo(0));
    expect(record.nonce!, lessThanOrEqualTo(0xFFFFFFFF));

    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(buoyPayload?['nonce'], record.nonce);
    expect(backendPayload?['nonce'], record.nonce);
  });

  test('same seq, different nonce matches the right record', () async {
    final identityStore = IdentityStore(db);
    await identityStore.ensure(boat: 'Sea Breeze', skipperName: 'Pedro');

    const r1 = SosRecord(
      localId: 'loc-1',
      vesselId: 'fisher-7f3a',
      boat: 'Sea Breeze',
      clientTs: 1000,
      state: DeliveryState.relayed,
      seq: 10,
      nonce: 111,
    );
    const r2 = SosRecord(
      localId: 'loc-2',
      vesselId: 'fisher-7f3a',
      boat: 'Sea Breeze',
      clientTs: 2000,
      state: DeliveryState.relayed,
      seq: 10,
      nonce: 222,
    );
    await outbox.insert(r1);
    await outbox.insert(r2);

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') return _direct(200);
        if (request.url.path == '/api/sos/vessel/fisher-7f3a') {
          return http.StreamedResponse(
            Stream.value(utf8.encode(jsonEncode({
              'vessel_id': 'fisher-7f3a',
              'server_time': '2026-09-24T12:00:00Z',
              'events': [
                {
                  'id': 99,
                  'seq': 10,
                  'nonce': 222,
                  'delivery_state': 'delivered',
                }
              ]
            }))),
            200,
          );
        }
        return _direct(200);
      }),
    )..setVesselBearerToken('test-token');

    final service = SosService(
      outbox: outbox,
      identity: identityStore,
      buoy: noBuoy(),
      backend: backend,
      location: LocationService(),
    );

    await service.reconcile();

    final updated1 = await outbox.byLocalId('loc-1');
    final updated2 = await outbox.byLocalId('loc-2');
    expect(updated1?.state, DeliveryState.relayed);
    expect(updated2?.state, DeliveryState.delivered);
  });

  test('match order is localId, then nonce, then seq', () async {
    final identityStore = IdentityStore(db);
    await identityStore.ensure(boat: 'Sea Breeze', skipperName: 'Pedro');

    const r1 = SosRecord(
      localId: 'loc-1',
      vesselId: 'fisher-7f3a',
      boat: 'Sea Breeze',
      clientTs: 1000,
      state: DeliveryState.relayed,
      seq: 1,
      nonce: 100,
    );
    const r2 = SosRecord(
      localId: 'loc-2',
      vesselId: 'fisher-7f3a',
      boat: 'Sea Breeze',
      clientTs: 2000,
      state: DeliveryState.relayed,
      seq: 2,
      nonce: 200,
    );
    const r3 = SosRecord(
      localId: 'loc-3',
      vesselId: 'fisher-7f3a',
      boat: 'Sea Breeze',
      clientTs: 3000,
      state: DeliveryState.relayed,
      seq: 3,
      nonce: 300,
    );
    await outbox.insert(r1);
    await outbox.insert(r2);
    await outbox.insert(r3);

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') return _direct(200);
        if (request.url.path == '/api/sos/vessel/fisher-7f3a') {
          return http.StreamedResponse(
            Stream.value(utf8.encode(jsonEncode({
              'vessel_id': 'fisher-7f3a',
              'server_time': '2026-09-24T12:00:00Z',
              'events': [
                {
                  'id': 1,
                  'local_id': 'loc-1',
                  'nonce': 200,
                  'seq': 3,
                  'delivery_state': 'delivered',
                }
              ]
            }))),
            200,
          );
        }
        return _direct(200);
      }),
    )..setVesselBearerToken('test-token');

    final service = SosService(
      outbox: outbox,
      identity: identityStore,
      buoy: noBuoy(),
      backend: backend,
      location: LocationService(),
    );

    await service.reconcile();

    final updated1 = await outbox.byLocalId('loc-1');
    final updated2 = await outbox.byLocalId('loc-2');
    final updated3 = await outbox.byLocalId('loc-3');
    expect(updated1?.state, DeliveryState.delivered);
    expect(updated2?.state, DeliveryState.relayed);
    expect(updated3?.state, DeliveryState.relayed);
  });

  test('late fix re-posts same nonce with position', () async {
    final identityStore = IdentityStore(db);
    await identityStore.ensure(boat: 'Sea Breeze', skipperName: 'Pedro');

    final sentPayloads = <Map<String, dynamic>>[];
    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/api/sos') {
          final bytes = await request.finalize().toBytes();
          sentPayloads.add(jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>);
        }
        return _direct(200);
      }),
    );

    final fakeLocation = _FakeLocationService(
      fixQueue: [
        null,
        const Fix(lat: 11.58, lon: 122.75),
      ],
    );

    final service = SosService(
      outbox: outbox,
      identity: identityStore,
      buoy: noBuoy(),
      backend: backend,
      location: fakeLocation,
      lateFixPollInterval: const Duration(milliseconds: 10),
      lateFixTimeout: const Duration(milliseconds: 200),
    );

    final record = await service.raiseSos();
    expect(record.lat, isNull);

    await Future<void>.delayed(const Duration(milliseconds: 100));

    final updated = await outbox.byLocalId(record.localId);
    expect(updated?.lat, 11.58);
    expect(updated?.lon, 122.75);
    expect(updated?.nonce, record.nonce);

    expect(sentPayloads.length, greaterThanOrEqualTo(2));
    expect(sentPayloads.last['nonce'], record.nonce);
    expect(sentPayloads.last['lat'], 11.58);
    expect(sentPayloads.last['lon'], 122.75);
  });

  test('no fix after 5 minutes sends nothing more', () async {
    final identityStore = IdentityStore(db);
    await identityStore.ensure(boat: 'Sea Breeze', skipperName: 'Pedro');

    final sentPayloads = <Map<String, dynamic>>[];
    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/api/sos') {
          final bytes = await request.finalize().toBytes();
          sentPayloads.add(jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>);
        }
        return _direct(200);
      }),
    );

    final fakeLocation = _FakeLocationService(fixQueue: [null]);

    final service = SosService(
      outbox: outbox,
      identity: identityStore,
      buoy: noBuoy(),
      backend: backend,
      location: fakeLocation,
      lateFixPollInterval: const Duration(milliseconds: 10),
      lateFixTimeout: const Duration(milliseconds: 50),
    );

    final record = await service.raiseSos();
    await Future<void>.delayed(const Duration(milliseconds: 100));

    final updated = await outbox.byLocalId(record.localId);
    expect(updated?.lat, isNull);
    expect(sentPayloads.length, 1);
  });

  test('closed record keeps reconciling for 2 hours to catch a reopen', () async {
    final record = _record('local-reconcile-window');
    await outbox.insert(record);
    await outbox.advance(record.localId, DeliveryState.delivered);

    final resolvedTime = DateTime.now().toUtc().subtract(const Duration(minutes: 30));
    final resolvedIso = resolvedTime.toIso8601String();

    var currentRemote = ackEnvelope(
      'local-reconcile-window',
      serverTime: DateTime.now().toUtc().toIso8601String(),
      resolvedAt: resolvedIso,
    );

    final backend = BackendClient(
      client: _FakeBackendClient((request) async {
        if (request.url.path == '/healthz') {
          return _direct(200);
        }
        if (request.url.path == '/api/sos/ack/local-reconcile-window') {
          return currentRemote;
        }
        throw Exception('unexpected ${request.url.path}');
      }),
    );

    final service = buildService(buoy: noBuoy(), backend: backend);
    await service.reconcile();

    var updated = await outbox.byLocalId(record.localId);
    expect(updated!.resolvedAt, isNotNull);
    expect(updated.isResolved, isTrue);

    // 30 min since resolved: record should still be in awaitingReconcile
    final awaiting30m = await outbox.awaitingReconcile(
      excludedIds: service.closedIncidents,
    );
    expect(awaiting30m.any((r) => r.localId == record.localId), isTrue);

    // Reopened event arrives!
    final reopenedIso = DateTime.now().toUtc().toIso8601String();
    currentRemote = ackEnvelope(
      'local-reconcile-window',
      serverTime: DateTime.now().toUtc().toIso8601String(),
      reopenedAt: reopenedIso,
    );

    await service.reconcile();
    updated = await outbox.byLocalId(record.localId);
    expect(updated!.resolvedAt, isNull, reason: 'reopen clears resolved_at');
    expect(updated.isResolved, isFalse);

    // Now resolve with a timestamp > 2 hours ago
    final oldResolvedTime = DateTime.now().toUtc().subtract(const Duration(hours: 3));
    currentRemote = ackEnvelope(
      'local-reconcile-window',
      serverTime: DateTime.now().toUtc().toIso8601String(),
      resolvedAt: oldResolvedTime.toIso8601String(),
    );

    await service.reconcile();
    updated = await outbox.byLocalId(record.localId);
    expect(updated!.resolvedAt, isNotNull);

    // After 2 hours, record is excluded
    final awaitingOld = await outbox.awaitingReconcile(
      excludedIds: service.closedIncidents,
    );
    expect(awaitingOld.any((r) => r.localId == record.localId), isFalse);
  });
}

class _FakeLocationService extends LocationService {
  _FakeLocationService({this.fixQueue = const []});
  final List<Fix?> fixQueue;
  int _callCount = 0;

  @override
  Future<Fix?> currentFix() async {
    if (_callCount < fixQueue.length) {
      return fixQueue[_callCount++];
    }
    return null;
  }
}


