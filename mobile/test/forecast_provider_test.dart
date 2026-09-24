// AqOneForecastProvider is the seam documented on the class itself: try the
// backend's fused endpoint, fall back to Open-Meteo with no handset release
// required. DailyOutlook.parseAqOneList's parsing rules are already pinned
// in daily_outlook_test.dart; this file pins the provider's precedence and
// fallback decision, which parser tests alone cannot cover.
import 'dart:convert';

import 'package:aqone/models/daily_outlook.dart';
import 'package:aqone/models/forecast_outlook.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/forecast_provider.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class _FakeProvider implements ForecastProvider {
  _FakeProvider(this.result, {this.outlookResult});

  final List<DailyOutlook>? result;
  final ForecastOutlook? outlookResult;
  bool called = false;

  @override
  Future<ForecastOutlook?> outlook({
    required double lat,
    required double lon,
    String? municipality,
    int days = 7,
  }) async {
    called = true;
    if (outlookResult != null) return outlookResult;
    if (result != null) {
      return ForecastOutlook(
        days: result!,
        hours: const <HourlyInterval>[],
        fetchedAt: DateTime(2026, 8, 16),
        source: 'fake',
      );
    }
    return null;
  }
}

void main() {
  group('AqOneForecastProvider', () {
    test('prefers the backend fused forecast when it answers with days', () async {
      final fallback = _FakeProvider(null);
      final backend = BackendClient(
        client: MockClient((request) async => http.Response(
              jsonEncode(<String, Object?>{
                'source': 'backend',
                'generated_at': '2026-08-16T04:00:00Z',
                'days': <Object?>[
                  <String, Object?>{'date': '2026-08-16', 'weather_code': 95},
                ],
                'hours': <Object?>[
                  <String, Object?>{
                    'time': '2026-08-16T04:00:00Z',
                    'weather_code': 95,
                    'wind_kph': 25.0,
                    'wave_m': 1.8,
                  },
                ],
              }),
              200,
            )),
      );
      final provider = AqOneForecastProvider(backend: backend, fallback: fallback);

      final outlook = await provider.outlook(lat: 11.68, lon: 122.41, days: 7);
      expect(outlook, isNotNull);
      expect(outlook!.days.single.weatherCode, 95);
      expect(outlook.hours.single.windKph, 25.0);
      expect(outlook.hours.single.waveM, 1.8);
      expect(outlook.source, 'backend');
      expect(fallback.called, isFalse);
    });

    test('fuses fallback hourly intervals when backend omits hours', () async {
      final fallbackOutlook = ForecastOutlook(
        days: <DailyOutlook>[
          DailyOutlook(
            date: DateTime(2026, 8, 16),
            weatherCode: 95,
            risk: RiskAssessment.unknown,
          ),
        ],
        hours: <HourlyInterval>[
          HourlyInterval(
            time: DateTime.utc(2026, 8, 16, 4),
            weatherCode: 95,
            windKph: 20.0,
            gustKph: 35.0,
            waveM: 1.5,
          ),
        ],
        fetchedAt: DateTime(2026, 8, 16),
        source: 'fallback',
      );
      final fallback = _FakeProvider(null, outlookResult: fallbackOutlook);
      final backend = BackendClient(
        client: MockClient((request) async => http.Response(
              jsonEncode(<String, Object?>{
                'source': 'backend',
                'generated_at': '2026-08-16T04:00:00Z',
                'days': <Object?>[
                  <String, Object?>{'date': '2026-08-16', 'weather_code': 95},
                ],
              }),
              200,
            )),
      );
      final provider = AqOneForecastProvider(backend: backend, fallback: fallback);

      final outlook = await provider.outlook(lat: 11.68, lon: 122.41, days: 7);
      expect(outlook, isNotNull);
      expect(outlook!.hours.length, 1);
      expect(outlook.hours.single.gustKph, 35.0);
      expect(fallback.called, isTrue);
    });

    test('falls back when the backend returns a non-200 status', () async {
      final fallback = _FakeProvider(<DailyOutlook>[
        DailyOutlook(
          date: DateTime(2026, 8, 16),
          weatherCode: 3,
          risk: RiskAssessment.unknown,
        ),
      ]);
      final backend = BackendClient(
        client: MockClient((request) async => http.Response('', 502)),
      );
      final provider = AqOneForecastProvider(backend: backend, fallback: fallback);

      final result = await provider.outlook(lat: 11.68, lon: 122.41, days: 7);

      expect(fallback.called, isTrue);
      expect(result, isNotNull);
      expect(result!.days.single.weatherCode, 3);
    });

    test('falls back when the backend returns an empty days list', () async {
      final fallback = _FakeProvider(<DailyOutlook>[]);
      final backend = BackendClient(
        client: MockClient((request) async => http.Response(
              jsonEncode(<String, Object?>{
                'source': 'open-meteo',
                'generated_at': '2026-08-16T04:00:00Z',
                'days': <Object?>[],
              }),
              200,
            )),
      );
      final provider = AqOneForecastProvider(backend: backend, fallback: fallback);

      await provider.outlook(lat: 11.68, lon: 122.41, days: 7);

      expect(fallback.called, isTrue);
    });

    test('falls back on a malformed backend body rather than throwing', () async {
      final fallback = _FakeProvider(<DailyOutlook>[]);
      final backend = BackendClient(
        client: MockClient((request) async => http.Response('not json', 200)),
      );
      final provider = AqOneForecastProvider(backend: backend, fallback: fallback);

      await provider.outlook(lat: 11.68, lon: 122.41, days: 7);

      expect(fallback.called, isTrue);
    });

    test('coarsens outgoing coordinates to 1 decimal place', () async {
      final List<Uri> requestedUris = <Uri>[];
      final backend = BackendClient(
        client: MockClient((request) async {
          requestedUris.add(request.url);
          return http.Response(
            jsonEncode(<String, Object?>{
              'source': 'backend',
              'generated_at': '2026-08-16T04:00:00Z',
              'days': <Object?>[
                <String, Object?>{'date': '2026-08-16', 'weather_code': 95},
              ],
              'hours': <Object?>[
                <String, Object?>{
                  'time': '2026-08-16T04:00:00Z',
                  'weather_code': 95,
                  'wind_kph': 25.0,
                  'wave_m': 1.8,
                },
              ],
            }),
            200,
          );
        }),
      );
      final provider = AqOneForecastProvider(
        backend: backend,
        fallback: _FakeProvider(null),
      );

      await provider.outlook(lat: 11.6050, lon: 122.3125, days: 7);

      expect(requestedUris, isNotEmpty);
      for (final uri in requestedUris) {
        expect(uri.queryParameters['lat'], '11.6');
        expect(uri.queryParameters['lon'], '122.3');
      }
    });
  });

  group('OpenMeteoForecastProvider', () {
    test('coarsens outgoing coordinates to 1 decimal place', () async {
      final List<Uri> requestedUris = <Uri>[];
      final client = MockClient((request) async {
        requestedUris.add(request.url);
        return http.Response(
          jsonEncode(<String, Object?>{
            'hourly': <String, Object?>{
              'time': <String>['2026-08-16T04:00'],
              'wave_height': <double>[1.2],
            },
            'daily': <String, Object?>{
              'time': <String>['2026-08-16'],
              'weather_code': <int>[1],
            },
          }),
          200,
        );
      });

      final provider = OpenMeteoForecastProvider(client: client);
      await provider.outlook(lat: 11.6050, lon: 122.3125, days: 1);

      expect(requestedUris, isNotEmpty);
      for (final uri in requestedUris) {
        expect(uri.queryParameters['latitude'], '11.6');
        expect(uri.queryParameters['longitude'], '122.3');
      }
    });

    test('fetches atmospheric and marine hourly forecasts', () async {
      final client = MockClient((request) async {
        if (request.url.host.contains('marine')) {
          return http.Response(
            jsonEncode(<String, Object?>{
              'hourly': <String, Object?>{
                'time': <String>['2026-08-16T04:00'],
                'wave_height': <double>[1.2],
              },
            }),
            200,
          );
        }
        return http.Response(
          jsonEncode(<String, Object?>{
            'daily': <String, Object?>{
              'time': <String>['2026-08-16'],
              'weather_code': <int>[1],
              'temperature_2m_max': <double>[31.0],
              'temperature_2m_min': <double>[25.0],
              'wind_speed_10m_max': <double>[15.0],
              'wind_gusts_10m_max': <double>[22.0],
              'precipitation_sum': <double>[0.0],
            },
            'hourly': <String, Object?>{
              'time': <String>['2026-08-16T04:00'],
              'weather_code': <int>[1],
              'temperature_2m': <double>[28.0],
              'wind_speed_10m': <double>[12.0],
              'wind_gusts_10m': <double>[18.0],
              'precipitation': <double>[0.0],
            },
          }),
          200,
        );
      });

      final provider = OpenMeteoForecastProvider(client: client);
      final outlook = await provider.outlook(lat: 11.68, lon: 122.41, days: 1);

      expect(outlook, isNotNull);
      expect(outlook!.days.length, 1);
      expect(outlook.days.single.waveM, 1.2);
      expect(outlook.hours.length, 1);
      expect(outlook.hours.single.tempC, 28.0);
      expect(outlook.hours.single.waveM, 1.2);
      expect(outlook.source, 'open-meteo-fallback');
    });
  });
}
