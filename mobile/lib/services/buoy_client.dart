import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../core/endpoint_guard.dart';
import '../models/advisory.dart';
import '../models/buoy_contact.dart';
import '../models/sos_record.dart';
import 'backend_client.dart' show RemoteSos;

class BuoyUnreachable implements Exception {
  const BuoyUnreachable(this.reason);
  final String reason;
  @override
  String toString() => 'BuoyUnreachable: $reason';
}

class BuoyRejected implements Exception {
  const BuoyRejected(this.statusCode, this.reason);
  final int statusCode;
  final String reason;
  @override
  String toString() => 'BuoyRejected($statusCode): $reason';
}

/// The buoy answered - it is reachable and not rejecting the request - but
/// the body was not a JSON object with the fields we expect. Distinct from
/// [BuoyUnreachable] on purpose: an unreachable buoy and a buoy sending
/// garbage need different handling (retry vs. "something is wrong with this
/// buoy's firmware"), and conflating them was hiding which one was actually
/// happening in the field.
///
/// The firmware caches responder ETA replies in a fixed 320-byte buffer
/// (`char payload[320]` in `.ino`) and can truncate mid-JSON - see
/// `fixtures/week1_contract/eta_acknowledged.json`. This is a real, expected
/// failure mode, not a hypothetical one.
class BuoyInvalidResponse implements Exception {
  const BuoyInvalidResponse(this.reason);
  final String reason;
  @override
  String toString() => 'BuoyInvalidResponse: $reason';
}

/// Turns a raw transport exception into something a fisher (or the
/// "Last attempt" line on the SOS status card - see
/// mobile/lib/ui/widgets/delivery_state_tile.dart) can actually read.
///
/// [BuoyUnreachable.reason] used to be `error.toString()` verbatim, which
/// meant a `SocketException` or `TimeoutException`'s Dart-internal message
/// text ended up on screen. This is the buoy-side counterpart to
/// [BackendClient]'s `_describeNetworkError` - matched on message text
/// rather than exception type for the same reason: `SocketException` /
/// `HandshakeException` live in `dart:io` and this file must stay
/// importable on the web build.
String describeBuoyError(Object error) {
  final text = error.toString();
  if (text.contains('TimeoutException')) {
    return 'no reply from the buoy in time';
  }
  if (text.contains('SocketException') ||
      text.contains('Failed host lookup') ||
      text.contains('ClientException') ||
      text.contains('Connection refused') ||
      text.contains('Network is unreachable')) {
    return 'buoy not in range';
  }
  if (text.contains('HandshakeException') || text.contains('CERTIFICATE')) {
    return "couldn't establish a secure connection to the buoy";
  }
  return 'could not reach the buoy';
}

class BuoyClient {
  BuoyClient({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? AqOneConfig.buoyBaseUrl {
    EndpointGuard.requireBuoyBase(_baseUrl, label: 'BuoyClient baseUrl');
  }

  final http.Client _client;
  final String _baseUrl;

  Future<BuoyStatus> status() async {
    final uri = EndpointGuard.buoy(_baseUrl, '/v1/status');
    http.Response response;
    try {
      response = await _send(_request('GET', uri)).timeout(AqOneConfig.buoyTimeout);
    } catch (error) {
      throw BuoyUnreachable(describeBuoyError(error));
    }

    if (response.statusCode != 200) {
      throw BuoyRejected(response.statusCode, 'status query failed');
    }
    return _decode(
      utf8.decode(response.bodyBytes, allowMalformed: true),
      BuoyStatus.fromJson,
    );
  }

  Future<BuoyAck> handoff(SosRecord record) async {
    final uri = EndpointGuard.buoy(_baseUrl, '/v1/sos');
    http.Response response;
    try {
      response = await _send(
        _request(
          'POST',
          uri,
          headers: const <String, String>{
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: jsonEncode(record.toBuoyPayload()),
        ),
      )
          .timeout(AqOneConfig.buoyTimeout);
    } catch (error) {
      throw BuoyUnreachable(describeBuoyError(error));
    }

    if (response.statusCode == 503) {
      throw const BuoyRejected(503, 'buoy queue full');
    }
    if (response.statusCode != 200) {
      throw BuoyRejected(response.statusCode, 'unexpected buoy response');
    }

    final ack = _decode(
      utf8.decode(response.bodyBytes, allowMalformed: true),
      BuoyAck.fromJson,
    );
    if (!ack.accepted) {
      throw const BuoyRejected(200, 'buoy did not accept the SOS');
    }
    return ack;
  }

  /// `GET /v1/sos/status?vessel_id=<id>` - what an offline handset (no
  /// cellular, buoy in range) polls to learn whether a responder has
  /// acknowledged and set an ETA.
  ///
  /// The firmware does not compute this itself: it polls
  /// `GET /api/sos/vessel/{vessel_id}` on the backend on the buoy's behalf
  /// and serves that response body back verbatim (see
  /// docs/21_WEEK1_CONTRACT_FIXTURES.md), so the shape is identical to
  /// [RemoteSos] via [BackendClient.vesselSos] and reuses the same
  /// [RemoteSos.fromJson] rather than a second, possibly-drifting parser.
  ///
  /// The firmware caches this reply in a fixed 320-byte buffer and can
  /// truncate it mid-JSON - a malformed body here is an expected failure
  /// mode, not a hypothetical one, hence [BuoyInvalidResponse] rather than a
  /// crash.
  Future<List<RemoteSos>> sosStatus(String vesselId) async {
    final uri = EndpointGuard.buoy(
      _baseUrl,
      '/v1/sos/status?vessel_id=${Uri.encodeComponent(vesselId)}',
    );
    http.Response response;
    try {
      response = await _send(_request('GET', uri)).timeout(AqOneConfig.buoyTimeout);
    } catch (error) {
      throw BuoyUnreachable(describeBuoyError(error));
    }

    if (response.statusCode != 200) {
      throw BuoyRejected(response.statusCode, 'sos status query failed');
    }
    return _decodeEvents(utf8.decode(response.bodyBytes, allowMalformed: true));
  }

  /// `GET /v1/warnings` - what an offline handset polls to retrieve active
  /// weather warnings and safety advisories downlinked to the buoy over LoRa.
  Future<List<Advisory>> warnings() async {
    final uri = EndpointGuard.buoy(_baseUrl, '/v1/warnings');
    http.Response response;
    try {
      response = await _send(_request('GET', uri)).timeout(AqOneConfig.buoyTimeout);
    } catch (error) {
      throw BuoyUnreachable(describeBuoyError(error));
    }

    if (response.statusCode != 200) {
      throw BuoyRejected(response.statusCode, 'warnings query failed');
    }
    return _decodeWarnings(utf8.decode(response.bodyBytes, allowMalformed: true));
  }

  List<Advisory> _decodeWarnings(String body) {
    final Object? decoded;
    try {
      decoded = jsonDecode(body);
    } catch (_) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
    try {
      return Advisory.parseList(decoded);
    } catch (_) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
  }

  List<RemoteSos> _decodeEvents(String body) {
    final Object? decoded;
    try {
      decoded = jsonDecode(body);
    } catch (_) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
    if (decoded is! Map<String, dynamic>) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
    final events = decoded['events'];
    if (events is! List) {
      // `{"events": []}` - no events at all - is the documented shape for
      // "not tracking this vessel yet." Anything without a list-typed
      // `events` key is a shape this client does not understand.
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
    final serverTime = decoded['server_time'] as String?;
    try {
      return events
          .whereType<Map<String, dynamic>>()
          .map((row) => RemoteSos.fromJson(row, envelopeServerTime: serverTime))
          .toList(growable: false);
    } catch (_) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
  }

  /// Parses a 200 response body. A malformed or truncated body is a real
  /// buoy-firmware failure mode (see [BuoyInvalidResponse]), not a transport
  /// failure, so it must not be reported to the fisher as "no buoy nearby."
  T _decode<T>(String body, T Function(Map<String, dynamic>) fromJson) {
    final Object? decoded;
    try {
      decoded = jsonDecode(body);
    } catch (_) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
    if (decoded is! Map<String, dynamic>) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
    try {
      return fromJson(decoded);
    } catch (_) {
      throw const BuoyInvalidResponse('buoy sent an unreadable reply');
    }
  }

  http.Request _request(
    String method,
    Uri uri, {
    Map<String, String>? headers,
    String? body,
  }) {
    final request = http.Request(method, uri)
      ..followRedirects = false
      ..maxRedirects = 0;
    if (headers != null) {
      request.headers.addAll(headers);
    }
    if (body != null) {
      request.body = body;
    }
    return request;
  }

  Future<http.Response> _send(http.Request request) async {
    final streamed = await _client.send(request);
    return http.Response.fromStream(streamed);
  }

  void close() => _client.close();
}
