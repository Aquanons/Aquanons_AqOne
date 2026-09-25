// Uses the Phase 0 contract fixtures in fixtures/week1_contract/ (see
// docs/21_WEEK1_CONTRACT_FIXTURES.md) as the single source of truth for what
// the buoy firmware actually sends, rather than re-typing JSON bodies here
// that could drift from the fixtures.
import 'dart:convert';
import 'dart:io';

import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> _fixture(String name) {
  final file = File('../fixtures/week1_contract/$name');
  return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
}

SosRecord _record() {
  return const SosRecord(
    localId: 'local-1',
    vesselId: 'fisher-7f3a',
    boat: 'BG-123',
    clientTs: 1755248500,
    state: DeliveryState.saved,
  );
}

void main() {
  group('BuoyClient.handoff', () {
    test('parses an accepted SOS per fixtures/week1_contract/accepted_sos.json',
        () async {
      final fixture = _fixture('accepted_sos.json');
      final body = fixture['response']['body'] as Map<String, dynamic>;

      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async {
          expect(request.url.toString(), 'http://192.168.4.1/v1/sos');
          return http.Response(jsonEncode(body), 200);
        }),
      );

      final ack = await client.handoff(_record());

      expect(ack.accepted, isTrue);
      // buoy_id is the firmware's string constant, not a number - the whole
      // point of this fixture (see docs/21_WEEK1_CONTRACT_FIXTURES.md).
      expect(ack.buoyId, 'BUOY01');
      expect(ack.seq, 42);
    });

    test('throws BuoyRejected(503) on a full queue per fixtures/week1_contract/queue_full.json',
        () async {
      final fixture = _fixture('queue_full.json');
      final response = fixture['response'] as Map<String, dynamic>;
      final status = response['status'] as int;
      final body = response['body'] as Map<String, dynamic>;

      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient(
          (request) async => http.Response(jsonEncode(body), status),
        ),
      );

      await expectLater(
        client.handoff(_record()),
        throwsA(
          isA<BuoyRejected>()
              .having((e) => e.statusCode, 'statusCode', 503)
              .having((e) => e.reason, 'reason', 'buoy queue full'),
        ),
      );
    });

    test('throws BuoyUnreachable when the buoy cannot be reached (fixtures/week1_contract/buoy_offline.json)',
        () async {
      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async {
          throw const SocketException('No route to host');
        }),
      );

      await expectLater(
        client.handoff(_record()),
        throwsA(isA<BuoyUnreachable>()),
      );
    });

    test('throws BuoyInvalidResponse on a body the firmware truncated mid-JSON',
        () async {
      // The firmware caches responder replies in a fixed 320-byte buffer and
      // serves whatever is in it verbatim - a response longer than that is
      // truncated mid-JSON (see fixtures/week1_contract/eta_acknowledged.json
      // "_notes"). handoff() must report this distinctly from "unreachable"
      // so the fisher and a field debugger are not told a buoy that answered
      // is out of range.
      const truncated = '{"accepted": true, "buoy_id": "BUOY01", "se';

      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async => http.Response(truncated, 200)),
      );

      await expectLater(
        client.handoff(_record()),
        throwsA(isA<BuoyInvalidResponse>()),
      );
    });

    test('throws BuoyRejected when the buoy says accepted:false', () async {
      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient(
          (request) async => http.Response(
            jsonEncode(<String, Object?>{'accepted': false}),
            200,
          ),
        ),
      );

      await expectLater(
        client.handoff(_record()),
        throwsA(isA<BuoyRejected>()),
      );
    });
  });

  group('BuoyClient.status', () {
    test('parses the real firmware GET /v1/status shape honestly', () async {
      // No batt/mesh fields - the firmware does not send them
      // (docs/21_WEEK1_CONTRACT_FIXTURES.md). A test that expected them would
      // be testing an imaginary contract.
      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient(
          (request) async => http.Response(
            jsonEncode(<String, Object?>{
              'buoy_id': 'BUOY01',
              'uplink': false,
              'queue_depth': 2,
              'clients': 1,
              'uptime_s': 4213,
            }),
            200,
          ),
        ),
      );

      final status = await client.status();

      expect(status.buoyId, 'BUOY01');
      expect(status.uplink, isFalse);
      expect(status.queueDepth, 2);
      expect(status.clients, 1);
    });

    test('throws BuoyRejected on a non-200 status', () async {
      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient(
          (request) async => http.Response('Internal Server Error', 500),
        ),
      );

      await expectLater(client.status(), throwsA(isA<BuoyRejected>()));
    });
  });

  // These four scenarios are exactly what Phase 2 of
  // docs/20_WEEK_1_DASHBOARD_FLUTTER_IMPLEMENTATION_PLAN.md requires: cloud
  // unavailable + buoy ETA, no events, malformed buoy response, delayed ETA.
  // This is what an offline handset (no cellular, buoy in range) actually
  // receives when SosService.reconcile() falls back to
  // BuoyClient.sosStatus() - see mobile/lib/services/sos_service.dart.
  group('BuoyClient.sosStatus (offline reconcile via buoy)', () {
    test(
        'parses a responder ETA per fixtures/week1_contract/eta_acknowledged.json',
        () async {
      final fixture = _fixture('eta_acknowledged.json');
      final body = fixture['response']['body'] as Map<String, dynamic>;

      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async {
          expect(
            request.url.toString(),
            'http://192.168.4.1/v1/sos/status?vessel_id=fisher-7f3a',
          );
          return http.Response(jsonEncode(body), 200);
        }),
      );

      final events = await client.sosStatus('fisher-7f3a');

      expect(events, hasLength(1));
      final event = events.single;
      expect(event.id, '118');
      expect(event.etaAt, '2026-08-15T09:40:00+00:00');
      expect(event.responderStatus, 2);
      expect(event.responderStatusLabel, 'Rescue boat on the way');
      expect(event.deliveryState, DeliveryState.acknowledged);
    });

    test('returns no events per fixtures/week1_contract/no_eta.json',
        () async {
      final fixture = _fixture('no_eta.json');
      final body = fixture['response']['body'] as Map<String, dynamic>;

      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient(
          (request) async => http.Response(jsonEncode(body), 200),
        ),
      );

      expect(await client.sosStatus('fisher-7f3a'), isEmpty);
    });

    test(
        'throws BuoyInvalidResponse on a body truncated by the firmware\'s '
        '320-byte cache (fixtures/week1_contract/eta_acknowledged.json _notes)',
        () async {
      // A real 320-byte cutoff of a well-formed eta_acknowledged.json body -
      // not a hypothetical string. The client must tell this apart from
      // "buoy unreachable."
      const truncated = '{"vessel_id": "fisher-7f3a", "server_time": '
          '"2026-08-15T09:12:44.120000+00:00", "events": [{"id": 118, '
          '"local_id": "a3f9c2e1-88d1-4b0a-9d4e-2f6a7b0c9e11", "seq": 42, '
          '"client_ts": 1755248500, "delivery_state": "ackno';

      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async => http.Response(truncated, 200)),
      );

      await expectLater(
        client.sosStatus('fisher-7f3a'),
        throwsA(isA<BuoyInvalidResponse>()),
      );
    });

    test('carries a delayed responder status (5 = DELAYED) through intact',
        () async {
      // responder_status enum from backend/app/api/sos.py:
      // 1 received, 2 dispatched, 3 coast guard, 4 nearest vessel, 5 delayed.
      // ResponderEtaDialog's countdown must still receive an eta_at even when
      // the responder has marked themselves delayed, so it can show "Delayed
      // - still on the way" instead of a silent countdown to zero.
      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient(
          (request) async => http.Response(
            jsonEncode(<String, Object?>{
              'vessel_id': 'fisher-7f3a',
              'server_time': '2026-08-15T09:12:44+00:00',
              'events': <Object?>[
                <String, Object?>{
                  'id': 118,
                  'local_id': 'a3f9c2e1-88d1-4b0a-9d4e-2f6a7b0c9e11',
                  'seq': 42,
                  'client_ts': 1755248500,
                  'delivery_state': 'acknowledged',
                  'acknowledged_at': '2026-08-15T09:10:02+00:00',
                  'acked_by': 'dispatcher_maria',
                  'eta_at': '2026-08-15T08:40:00+00:00',
                  'responder_status': 5,
                  'responder_status_label': 'Delayed - still coming',
                  'responder_note': 'Rough seas, running behind',
                  'fisher_reply': null,
                  'resolved_at': null,
                },
              ],
            }),
            200,
          ),
        ),
      );

      final events = await client.sosStatus('fisher-7f3a');

      expect(events.single.responderStatus, 5);
      expect(events.single.responderStatusLabel, 'Delayed - still coming');
      expect(events.single.etaAt, '2026-08-15T08:40:00+00:00');
    });

    test('malformed UTF-8 body does not throw', () async {
      final client = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async {
          return http.Response.bytes(
            const [0xFF, 0xFE, 0xFD],
            200,
          );
        }),
      );

      await expectLater(
        client.status(),
        throwsA(isA<BuoyInvalidResponse>()),
      );
    });
  });
}
