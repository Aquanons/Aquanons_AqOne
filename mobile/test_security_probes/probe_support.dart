// Shared fakes for the security-audit probes (docs/security-audit/PROBES.md).
//
// Every probe asserts the SAFE behaviour. In `flutter test --reporter json`:
//   result "failure" (a failed expect) -> finding CONFIRMED
//   result "success"                   -> finding REFUTED
//   result "error" (any other throw)   -> INCONCLUSIVE, the probe broke
// Test names start with "[finding-id]" so the report can map them.

import 'dart:convert';

import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class FakeHttp extends http.BaseClient {
  FakeHttp(this._handler);

  final Future<http.Response> Function(http.BaseRequest request) _handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final response = await _handler(request);
    return http.StreamedResponse(
      Stream<List<int>>.value(response.bodyBytes),
      response.statusCode,
    );
  }
}

http.Response jsonResponse(int status, Object body) =>
    http.Response(jsonEncode(body), status);

BuoyClient unreachableBuoy() => BuoyClient(
      baseUrl: 'http://192.168.4.1',
      client: MockClient((_) async => throw const FormatException('no buoy')),
    );

BuoyClient buoyAnswering(Future<http.Response> Function(http.Request) handler) =>
    BuoyClient(baseUrl: 'http://192.168.4.1', client: MockClient(handler));

BackendClient backendAnswering(
  Future<http.Response> Function(http.BaseRequest request) handler,
) =>
    BackendClient(client: FakeHttp(handler));

SosService buildService(
  AppDatabase db,
  OutboxStore outbox, {
  required BuoyClient buoy,
  required BackendClient backend,
}) =>
    SosService(
      outbox: outbox,
      identity: IdentityStore(db),
      buoy: buoy,
      backend: backend,
      location: LocationService(),
    );

/// Thrown when the probe could not reach the behaviour under test, so the
/// run reports "error" (INCONCLUSIVE) instead of a failed expectation.
class ProbeBroken implements Exception {
  ProbeBroken(this.message);

  final String message;

  @override
  String toString() => 'ProbeBroken: $message';
}
