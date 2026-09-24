import 'dart:convert';

import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'probe_support.dart';

SosRecord _record(String localId, DeliveryState state, {int? seq}) => SosRecord(
      localId: localId,
      vesselId: 'fisher-7f3a',
      boat: 'BG-123',
      clientTs: 1755248500,
      state: state,
      buoyId: seq == null ? null : 'BUOY01',
      seq: seq,
    );

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

  Future<SosRecord> standDownWith(int replyStatus, {String? remoteId}) async {
    final record = _record('standdown-$replyStatus-$remoteId', DeliveryState.relayed);
    await outbox.insert(record);
    if (remoteId != null) {
      await outbox.saveResponder(record.localId, remoteId: remoteId);
    }
    final service = buildService(
      db,
      outbox,
      buoy: unreachableBuoy(),
      backend: backendAnswering((_) async => jsonResponse(replyStatus, {})),
    );
    await service.standDown(record.localId);
    final updated = await outbox.byLocalId(record.localId);
    if (updated == null) {
      throw ProbeBroken('record vanished from the outbox');
    }
    return updated;
  }

  group('[mobile.sos.standdown-intent-treated-resolved]', () {
    test('a stand-down the backend rejected (503) is not shown as resolved',
        () async {
      final updated = await standDownWith(503, remoteId: '7');
      expect(
        updated.isResolved,
        isFalse,
        reason: 'the backend refused the stand-down, yet the handset treats '
            'the incident as resolved and stops the responder flow',
      );
    });

    test('a stand-down never sent (no backend id yet) is not shown as resolved',
        () async {
      final updated = await standDownWith(200);
      expect(
        updated.isResolved,
        isFalse,
        reason: 'nothing reached the backend, yet the handset treats the '
            'incident as resolved',
      );
    });
  });

  test('[mobile.sos.standdown-intent-treated-resolved:control] an accepted '
      'stand-down is resolved', () async {
    final updated = await standDownWith(200, remoteId: '7');
    expect(updated.isResolved, isTrue);
  });

  test('[mobile.sos.buoy-only-reply-unroutable] handset half: the reply to a '
      'buoy-only SOS is delivered', () async {
    final record = _record('buoy-only-local', DeliveryState.relayed, seq: 42);
    await outbox.insert(record);
    final posted = <String>[];
    final recordedLocalIds = <String>{};

    // Mirrors the backend as test_probe_sos.py observes it on real Postgres:
    // /api/sos/reply/{local_id} cannot match a buoy-only row (it never got
    // the local_id); /api/sos/{id}/reply needs a device credential.
    final backend = backendAnswering((request) async {
      final path = request.url.path;
      if (path == '/healthz') return jsonResponse(200, {'status': 'ok'});
      if (path == '/api/sos' && request.method == 'POST') {
        if (request is http.Request) {
          try {
            final body = jsonDecode(request.body) as Map<String, dynamic>;
            final lid = body['local_id'] as String?;
            if (lid != null) recordedLocalIds.add(lid);
          } catch (_) {}
        }
        return jsonResponse(200, {'ok': true});
      }
      if (path.startsWith('/api/sos/ack/')) return jsonResponse(404, {});
      if (request.method == 'POST' && path.contains('/reply')) {
        posted.add(path);
        if (path.startsWith('/api/sos/reply/')) {
          final replyLocalId =
              Uri.decodeComponent(path.substring('/api/sos/reply/'.length));
          if (recordedLocalIds.contains(replyLocalId)) {
            return jsonResponse(200, {'ok': true});
          }
          return jsonResponse(404, {});
        }
        return jsonResponse(401, {});
      }
      return jsonResponse(404, {});
    });
    final buoy = buoyAnswering((request) async {
      if (request.url.path == '/v1/sos/status') {
        return jsonResponse(200, {
          'events': [
            {'id': 55, 'seq': 42, 'delivery_state': 'acknowledged', 'responder_status': 1},
          ],
        });
      }
      return http.Response('', 404);
    });

    final service = buildService(db, outbox, buoy: buoy, backend: backend);
    await service.reconcile();
    if ((await outbox.byLocalId(record.localId))?.remoteId != '55') {
      throw ProbeBroken('reconcile did not learn the event id from the buoy');
    }
    final ok = await service.replyToSos(record.localId, 1);
    expect(
      ok,
      isTrue,
      reason: 'the reply was posted to $posted, a route the backend cannot '
          'match for an SOS that arrived only over the buoy',
    );
  });

  test('[mobile.eta.server-clock-discarded] rescue ETA is measured against '
      'server time, not the phone clock', () async {
    final record = _record('eta-local', DeliveryState.delivered);
    await outbox.insert(record);
    // The phone clock runs 60 minutes ahead of the server. The server says
    // the boat arrives 20 minutes from its own "now".
    final serverNow = DateTime.now().toUtc().subtract(const Duration(minutes: 60));
    final etaAt = serverNow.add(const Duration(minutes: 20));

    final backend = backendAnswering((request) async {
      final path = request.url.path;
      if (path == '/healthz') return jsonResponse(200, {'status': 'ok'});
      if (path == '/api/sos/ack/eta-local') {
        return jsonResponse(200, {
          'vessel_id': 'fisher-7f3a',
          'server_time': serverNow.toIso8601String(),
          'event': {
            'id': 9,
            'local_id': 'eta-local',
            'delivery_state': 'acknowledged',
            'eta_at': etaAt.toIso8601String(),
            'responder_status': 2,
          },
        });
      }
      return jsonResponse(404, {});
    });

    final service = buildService(db, outbox, buoy: unreachableBuoy(), backend: backend);
    await service.reconcile();
    final updated = await outbox.byLocalId(record.localId);
    if (updated?.etaAt == null) {
      throw ProbeBroken('reconcile did not store the ETA');
    }
    expect(
      updated!.etaOverdue,
      isFalse,
      reason: 'the server says 20 minutes remain, but a phone clock 60 '
          'minutes fast shows the rescue as already overdue',
    );
  });
}
