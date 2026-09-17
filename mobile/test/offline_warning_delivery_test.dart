import 'dart:convert';
import 'dart:io';

import 'package:aqone/data/welcome_advisory.dart';
import 'package:aqone/models/advisory.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('W10: Handset Advisory model parsing and expiry guarantees', () {
    test('instant-based expiry must expire at that instant, not remain active until midnight', () {
      final now = DateTime.now();
      final precisePast = now.subtract(const Duration(minutes: 10)).toIso8601String();

      // Precise expiry 10 minutes ago should be expired right now
      final advisory = Advisory.tryParse(<String, Object?>{
        'id': 50,
        'title': 'High Wind Event',
        'priority': 'Warning',
        'municipality': 'New Washington',
        'description': 'Gusts exceeding 45 kph',
        'source': 'MDRRMO',
        'revision': 1,
        'publish_date': now.subtract(const Duration(hours: 1)).toIso8601String(),
        'expiration_date': precisePast,
      });
      expect(advisory, isNotNull);
      expect(advisory!.id, 50);
      expect(advisory.source, 'MDRRMO');
      expect(advisory.revision, 1);
      expect(
        advisory.isActive,
        isFalse,
        reason: 'Instant-based expiry must honor exact instant, not stay active until midnight',
      );
    });

    test('missing expiration date must be bounded and not silently immortal forever', () {
      final now = DateTime.now();
      // An advisory published 30 days ago with no expiration date
      final oldAdvisory = Advisory.tryParse(<String, Object?>{
        'title': 'Old Storm Notice',
        'priority': 'Warning',
        'municipality': 'All',
        'description': 'Old typhoon notice',
        'publish_date': now.subtract(const Duration(days: 30)).toIso8601String(),
        'expiration_date': null,
      });
      expect(oldAdvisory, isNotNull);
      expect(
        oldAdvisory!.isActive,
        isFalse,
        reason: 'Missing expiry must be bounded by retention policy (max 48h), not silently immortal',
      );
    });

    test('corrupted non-map payload returns null and malformed list string throws FormatException', () {
      expect(Advisory.tryParse('not a map'), isNull);
      expect(Advisory.tryParse(<String, Object?>{}), isNull);
      expect(Advisory.tryParse(<String, Object?>{'title': '   '}), isNull);
      // Malformed json string to parseList must throw, not return an empty "clear" list
      expect(() => Advisory.parseList('this is corrupt not json'), throwsFormatException);
    });
  });

  group('W1: Offline warning delivery via buoy WiFi fallback', () {
    test('VentureFeeds falls back to BuoyClient when backend is unreachable', () async {
      final futureDate = DateTime.now().add(const Duration(days: 1)).toIso8601String();
      final buoyData = {
        'advisories': [
          {
            'id': 42,
            'title': 'Gale Warning',
            'priority': 'Warning',
            'municipality': 'New Washington',
            'description': 'Rough seas expected over eastern seaboard.',
            'source': 'MDRRMO',
            'revision': 1,
            'publish_date': '2026-09-15T00:00:00Z',
            'expiration_date': futureDate,
          }
        ]
      };

      final backend = BackendClient(
        client: MockClient((request) async => http.Response('Server Error', 500)),
      );

      final buoy = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async {
          expect(request.url.path, '/v1/warnings');
          return http.Response(jsonEncode(buoyData), 200);
        }),
      );

      final feeds = VentureFeeds(
        backend: backend,
        buoy: buoy,
      );

      final result = await feeds.advisories();
      expect(result, isNotNull);
      expect(result!.any((a) => a.id == 42 && a.title == 'Gale Warning' && a.source == 'MDRRMO'), isTrue);
      expect(result.last, same(WelcomeAdvisory.instance));
    });
  });

  group('W8: Honest disconnection and reconnection lifecycle', () {
    test('returns null when disconnected from both; receives warning upon reconnecting to buoy WiFi', () async {
      bool buoyInRange = false;
      final futureDate = DateTime.now().add(const Duration(days: 1)).toIso8601String();

      final backend = BackendClient(
        client: MockClient((request) async => throw const SocketException('No cellular data')),
      );

      final buoy = BuoyClient(
        baseUrl: 'http://192.168.4.1',
        client: MockClient((request) async {
          if (!buoyInRange) {
            throw const SocketException('No buoy WiFi in range');
          }
          return http.Response(
            jsonEncode({
              'advisories': [
                {
                  'id': 88,
                  'title': 'Squall Warning',
                  'priority': 'Emergency',
                  'municipality': 'All',
                  'description': 'Rapidly descending front',
                  'source': 'MDRRMO',
                  'publish_date': '2026-09-15T00:00:00Z',
                  'expiration_date': futureDate,
                }
              ]
            }),
            200,
          );
        }),
      );

      final feeds = VentureFeeds(
        backend: backend,
        buoy: buoy,
      );

      // Phase A: Offline, no buoy WiFi -> returns null
      final offlineResult = await feeds.advisories();
      expect(offlineResult, isNull, reason: 'Must not claim delivery when completely disconnected');

      // Phase B: Enters buoy range
      buoyInRange = true;
      final connectedResult = await feeds.advisories();
      expect(connectedResult, isNotNull);
      expect(connectedResult!.any((a) => a.id == 88 && a.title == 'Squall Warning'), isTrue);
    });
  });

  group('W9: Research squall downlink vs authored advisory distinction', () {
    test('research signal retains its uncalibrated/research identity and is not marked official', () {
      final futureDate = DateTime.now().add(const Duration(hours: 2)).toIso8601String();
      final researchNotice = Advisory.tryParse({
        'id': 999,
        'title': 'Pressure Pattern Squall Signal',
        'priority': 'Warning',
        'municipality': 'All',
        'description': 'Experimental squall signature detected by microbarometer array.',
        'source': 'AqOne Research',
        'publish_date': DateTime.now().toIso8601String(),
        'expiration_date': futureDate,
        'is_official': false,
      });

      expect(researchNotice, isNotNull);
      expect(researchNotice!.source, 'AqOne Research');
      expect(researchNotice.isOfficial, isFalse, reason: 'Research signal must never pass as official MDRRMO instruction');
    });
  });
}
