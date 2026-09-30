// The vessel-profile 409 rule stays (docs/05, Len 2026-09-30), so the handset
// must stop swallowing the rejection and tell the fisher to pair the phone.
// Acceptance tests written by the spec author; do not edit them to make them
// pass.

import 'dart:convert';

import 'package:aqone/data/identity_store.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

BackendClient _backend(Future<http.Response> Function(http.Request) handler) =>
    BackendClient(client: MockClient(handler));

const _identity = VesselIdentity(vesselId: '0123456789abcdef0123456789abcdef', boat: 'NW-001');

void main() {
  test('a stored profile is accepted', () async {
    final result = await _backend((_) async => http.Response(jsonEncode({'vessel_id': 'x'}), 200))
        .registerVesselProfile(_identity);
    expect(result, ProfilePushResult.accepted);
  });

  test('a 409 overwrite refusal means the phone must be paired', () async {
    final result = await _backend((_) async => http.Response('{"detail":"x"}', 409))
        .registerVesselProfile(_identity);
    expect(result, ProfilePushResult.needsPairing);
  });

  test('a 401 from a vessel with a paired device also means pairing', () async {
    final result = await _backend((_) async => http.Response('{"detail":"x"}', 401))
        .registerVesselProfile(_identity);
    expect(result, ProfilePushResult.needsPairing);
  });

  test('a server error or no network is a plain failure', () async {
    expect(
      await _backend((_) async => http.Response('oops', 500)).registerVesselProfile(_identity),
      ProfilePushResult.failed,
    );
    expect(
      await _backend((_) async => throw const SocketLikeException()).registerVesselProfile(_identity),
      ProfilePushResult.failed,
    );
  });
}

class SocketLikeException implements Exception {
  const SocketLikeException();
}
