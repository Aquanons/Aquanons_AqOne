import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:aqone/services/backend_client.dart';

class _FakeClient extends http.BaseClient {
  _FakeClient(this._handler);

  final Future<http.StreamedResponse> Function(http.BaseRequest request) _handler;
  int calls = 0;
  http.BaseRequest? lastRequest;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    calls += 1;
    lastRequest = request;
    return _handler(request);
  }
}

Future<http.StreamedResponse> _jsonResponse(
  int statusCode,
  Object body,
) async {
  final bytes = utf8.encode(jsonEncode(body));
  return http.StreamedResponse(
    Stream<List<int>>.value(bytes),
    statusCode,
    headers: const {'content-type': 'application/json'},
  );
}

void main() {
  test('vessel SOS does not hit the backend without a vessel credential', () async {
    final client = _FakeClient((_) => _jsonResponse(200, const <String, Object?>{}));
    final backend = BackendClient(client: client);

    final rows = await backend.vesselSos('V001');

    expect(rows, isEmpty);
    expect(client.calls, 0);
  });

  test('vessel SOS sends the bearer token when present', () async {
    final client = _FakeClient(
      (_) => _jsonResponse(
        200,
        <String, Object?>{
          'events': <Object?>[
            <String, Object?>{
              'id': 9,
              'delivery_state': 'delivered',
            },
          ],
        },
      ),
    );
    final backend = BackendClient(client: client);
    backend.setVesselBearerToken('token-123');

    final rows = await backend.vesselSos('V001');

    expect(rows, hasLength(1));
    expect(
      client.lastRequest?.headers['Authorization'],
      'Bearer token-123',
    );
  });

  test('401 vessel SOS response clears the in-memory credential', () async {
    final client = _FakeClient(
      (_) => _jsonResponse(
        401,
        <String, Object?>{'detail': 'device credential revoked'},
      ),
    );
    final backend = BackendClient(client: client);
    backend.setVesselBearerToken('token-123');

    final rows = await backend.vesselSos('V001');

    expect(rows, isEmpty);
    expect(backend.hasVesselCredential, isFalse);
  });

  test('enrollVesselDevice stores the returned bearer token', () async {
    final client = _FakeClient(
      (_) => _jsonResponse(
        200,
        <String, Object?>{
          'token': 'paired-token',
          'expires_at': '2026-08-17T05:00:00Z',
          'device': <String, Object?>{
            'id': 12,
            'vessel_id': 'V001',
            'label': 'Handset A',
          },
        },
      ),
    );
    final backend = BackendClient(client: client);

    final credential = await backend.enrollVesselDevice(
      vesselId: 'V001',
      pairingCode: 'K7Q4M9PX',
      deviceLabel: 'Handset A',
    );

    expect(credential, isNotNull);
    expect(credential?.token, 'paired-token');
    expect(backend.hasVesselCredential, isTrue);
    expect(
      client.lastRequest?.headers['Content-Type'],
      'application/json',
    );
  });

  test('refresh is attempted on start when a credential exists', () async {
    final client = _FakeClient(
      (_) => _jsonResponse(
        200,
        <String, Object?>{
          'token': 'refreshed-token',
          'expires_at': '2026-08-18T05:00:00Z',
          'device': <String, Object?>{
            'id': 12,
            'vessel_id': 'V001',
            'label': 'Handset A',
          },
        },
      ),
    );
    final backend = BackendClient(client: client);
    backend.setVesselBearerToken('initial-token');

    final refreshed = await backend.refreshVesselCredential();

    expect(refreshed, isNotNull);
    expect(refreshed?.token, 'refreshed-token');
    expect(client.calls, 1);
    expect(client.lastRequest?.url.path, endsWith('/api/vessel-auth/refresh'));
    expect(
      client.lastRequest?.headers['Authorization'],
      'Bearer initial-token',
    );
  });
}

