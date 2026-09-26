import 'package:aqone/core/config.dart';
import 'package:aqone/models/daily_outlook.dart';
import 'package:aqone/models/weather_snapshot.dart';
import 'package:aqone/services/safety_score.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('DailyOutlook.parseOpenMeteoList', () {
    test('parses a well-formed daily block', () {
      final List<DailyOutlook>? days = DailyOutlook.parseOpenMeteoList(
        <String, Object?>{
          'daily': <String, Object?>{
            'time': <String>['2026-08-16', '2026-08-17'],
            'weather_code': <int>[95, 0],
            'temperature_2m_max': <double>[31.2, 33.0],
            'temperature_2m_min': <double>[25.8, 26.1],
            'wind_speed_10m_max': <double>[24, 11],
            'wind_gusts_10m_max': <double>[41, 18],
            'precipitation_sum': <double>[18.4, 0],
          },
        },
      );

      expect(days, isNotNull);
      expect(days!.length, 2);
      expect(days.first.weatherCode, 95);
      expect(days.first.gustKph, 41);
      expect(days.first.condition, WeatherCondition.thunderstorm);
      // Open-Meteo has no opinion on whether a banca should sail.
      expect(days.first.risk.level, RiskLevel.unknown);
    });

    test('returns null rather than an empty strip on a malformed payload', () {
      expect(DailyOutlook.parseOpenMeteoList(<String, Object?>{}), isNull);
      expect(DailyOutlook.parseOpenMeteoList('nonsense'), isNull);
      expect(
        DailyOutlook.parseOpenMeteoList(<String, Object?>{
          'daily': <String, Object?>{'time': <String>[]},
        }),
        isNull,
      );
    });

    test('survives a series shorter than the time axis', () {
      // Open-Meteo occasionally truncates a variable. Missing values must come
      // back null, never zero - a 0.0 gust reads as flat calm.
      final List<DailyOutlook>? days = DailyOutlook.parseOpenMeteoList(
        <String, Object?>{
          'daily': <String, Object?>{
            'time': <String>['2026-08-16', '2026-08-17'],
            'weather_code': <int>[3],
            'wind_gusts_10m_max': <double>[12],
          },
        },
      );

      expect(days!.length, 2);
      expect(days[1].gustKph, isNull);
      expect(days[1].tempMax, isNull);
    });
  });

  group('DailyOutlook.parseAqOneList', () {
    test('parses the fused contract including the risk block', () {
      final List<DailyOutlook>? days = DailyOutlook.parseAqOneList(
        <String, Object?>{
          'source': 'aqone-fusion',
          'days': <Object?>[
            <String, Object?>{
              'date': '2026-08-16',
              'weather_code': 95,
              'temp_max': 31.2,
              'wind_kph': 24,
              'gust_kph': 41,
              'wave_m': 2.1,
              'risk': <String, Object?>{
                'level': 'danger',
                'score': 0.81,
                'reason': 'Gusts 41 km/h, 2.1 m swell at Buoy B',
                'inputs': <String>['buoy:buoy-b', 'open-meteo'],
              },
            },
          ],
        },
      );

      expect(days!.length, 1);
      final DailyOutlook day = days.first;
      expect(day.risk.level, RiskLevel.danger);
      expect(day.risk.source, RiskSource.backend);
      expect(day.waveM, 2.1);
      // Buoy telemetry counts as sea state, so the card must not claim the
      // verdict was reached without it.
      expect(day.risk.missingSeaState, isFalse);
    });

    test('a day with risk:null is left for the device to score', () {
      // This is the case that lets the backend serve weather before the
      // fusion model exists, without the client regressing.
      final List<DailyOutlook>? days = DailyOutlook.parseAqOneList(
        <String, Object?>{
          'days': <Object?>[
            <String, Object?>{
              'date': '2026-08-16',
              'weather_code': 0,
              'gust_kph': 8,
              'risk': null,
            },
          ],
        },
      );

      expect(days!.first.risk.level, RiskLevel.unknown);

      final DailyOutlook scored = SafetyScore.applyTo(days.first);
      expect(scored.risk.level, RiskLevel.safe);
      expect(scored.risk.source, RiskSource.device);
    });

    test('a backend verdict is never overwritten by the device heuristic', () {
      final DailyOutlook day = DailyOutlook(
        date: DateTime(2026, 8, 16),
        weatherCode: 0,
        gustKph: 5,
        risk: const RiskAssessment(
          level: RiskLevel.danger,
          source: RiskSource.backend,
          reason: 'Buoy B reports 3 m swell',
          inputs: <String>['buoy:buoy-b'],
        ),
      );

      // Clear skies and light wind: the heuristic would say safe. The server
      // has measured sea state and outranks it.
      expect(SafetyScore.applyTo(day).risk.level, RiskLevel.danger);
    });
  });

  group('DailyOutlook.parseMarineDailyMax', () {
    test('keys the daily maximum by date', () {
      final Map<DateTime, double> byDay = DailyOutlook.parseMarineDailyMax(
        <String, Object?>{
          'hourly': <String, Object?>{
            'time': <String>[
              '2026-08-16T00:00',
              '2026-08-16T06:00',
              '2026-08-17T00:00',
            ],
            'wave_height': <double>[1.1, 2.4, 0.6],
          },
        },
      );

      expect(byDay[DateTime(2026, 8, 16)], 2.4);
      expect(byDay[DateTime(2026, 8, 17)], 0.6);
    });

    test('skips nulls instead of reading them as flat calm', () {
      // Nearshore cells the wave model does not cover come back null. Treating
      // those as 0.0 would paint a dangerous day green.
      final Map<DateTime, double> byDay = DailyOutlook.parseMarineDailyMax(
        <String, Object?>{
          'hourly': <String, Object?>{
            'time': <String>['2026-08-16T00:00', '2026-08-16T06:00'],
            'wave_height': <Object?>[null, null],
          },
        },
      );

      expect(byDay, isEmpty);
    });
  });

  group('cache round trip', () {
    test('preserves the verdict, its source and its inputs', () {
      final DailyOutlook original = DailyOutlook(
        date: DateTime(2026, 8, 16),
        weatherCode: 82,
        tempMax: 30,
        tempMin: 25,
        gustKph: 55,
        waveM: 2.8,
        risk: const RiskAssessment(
          level: RiskLevel.danger,
          source: RiskSource.backend,
          score: 0.9,
          reason: 'Violent showers',
          inputs: <String>['buoy:buoy-a'],
        ),
      );

      final DailyOutlook? restored =
          DailyOutlook.fromCacheJson(original.toCacheJson());

      expect(restored, isNotNull);
      expect(restored!.date, original.date);
      expect(restored.waveM, 2.8);
      expect(restored.risk.level, RiskLevel.danger);
      expect(restored.risk.source, RiskSource.backend);
      expect(restored.risk.inputs, <String>['buoy:buoy-a']);
    });
  });

  group('WeatherCondition.fromCode', () {
    test('gives storms, rain and drizzle distinct icons', () {
      // The whole point of widening the buckets: a stormy Thursday must not
      // look like a drizzly Tuesday in the strip.
      final WeatherCondition drizzle = WeatherCondition.fromCode(53);
      final WeatherCondition rain = WeatherCondition.fromCode(63);
      final WeatherCondition storm = WeatherCondition.fromCode(95);
      final WeatherCondition severe = WeatherCondition.fromCode(99);

      expect(drizzle, WeatherCondition.drizzle);
      expect(rain, WeatherCondition.rainy);
      expect(storm, WeatherCondition.thunderstorm);
      expect(severe, WeatherCondition.severeThunderstorm);

      final Set<Object> icons = <Object>{
        drizzle.icon,
        rain.icon,
        storm.icon,
        severe.icon,
      };
      expect(icons.length, 4, reason: 'each bucket needs its own glyph');
    });

    test('maps clear, cloudy and overcast apart', () {
      expect(WeatherCondition.fromCode(0), WeatherCondition.sunny);
      expect(WeatherCondition.fromCode(2), WeatherCondition.partlyCloudy);
      expect(WeatherCondition.fromCode(3), WeatherCondition.overcast);
      expect(WeatherCondition.fromCode(45), WeatherCondition.foggy);
    });

    test('tryFromCode returns null on negative or unrecognized codes', () {
      expect(WeatherCondition.tryFromCode(-1), isNull);
      expect(WeatherCondition.tryFromCode(999), isNull);
      expect(WeatherCondition.tryFromCode(null), isNull);
      expect(WeatherCondition.tryFromCode(95), WeatherCondition.thunderstorm);
    });
  });

  group('SafetyScore thresholds', () {
    DailyOutlook day({
      int code = 0,
      double? gust,
      double? wave,
      double? precip,
    }) {
      return DailyOutlook(
        date: DateTime(2026, 8, 16),
        weatherCode: code,
        gustKph: gust,
        waveM: wave,
        precipMm: precip,
        risk: RiskAssessment.unknown,
      );
    }

    test('calm day scores safe', () {
      expect(SafetyScore.assess(day(gust: 10, wave: 0.4)).level, RiskLevel.safe);
    });

    test('gust boundaries', () {
      expect(
        SafetyScore.assess(day(gust: AqOneConfig.cautionGustKph - 0.1)).level,
        RiskLevel.safe,
      );
      expect(
        SafetyScore.assess(day(gust: AqOneConfig.cautionGustKph)).level,
        RiskLevel.caution,
      );
      expect(
        SafetyScore.assess(day(gust: AqOneConfig.dangerGustKph)).level,
        RiskLevel.danger,
      );
    });

    test('wave boundaries', () {
      expect(
        SafetyScore.assess(day(gust: 5, wave: AqOneConfig.cautionWaveM)).level,
        RiskLevel.caution,
      );
      expect(
        SafetyScore.assess(day(gust: 5, wave: AqOneConfig.dangerWaveM)).level,
        RiskLevel.danger,
      );
    });

    test('a thunderstorm is dangerous even in light wind', () {
      // The old wind-only rule called this safe, which was the bug worth
      // fixing: squalls arrive before the mean wind does.
      expect(SafetyScore.assess(day(code: 95, gust: 8)).level, RiskLevel.danger);
    });

    test('fog is no longer treated as safe', () {
      expect(
        SafetyScore.assess(day(code: 45, gust: 5)).level,
        RiskLevel.caution,
      );
    });

    test('the worst input wins', () {
      final RiskAssessment risk =
          SafetyScore.assess(day(gust: 12, wave: 3.0, precip: 1));
      expect(risk.level, RiskLevel.danger);
      expect(risk.factors.map((f) => f.kind), contains(RiskFactorKind.swell));
    });

    test('no usable inputs yields unknown, not green', () {
      expect(SafetyScore.assess(day()).level, RiskLevel.unknown);
    });

    test('a thunderstorm without numeric wind/wave preserves danger evidence', () {
      final RiskAssessment risk = SafetyScore.assess(day(code: 95));
      expect(risk.level, RiskLevel.danger);
      expect(
        risk.factors.map((f) => f.kind),
        contains(RiskFactorKind.thunderstorm),
      );
    });

    test('a verdict without wave data admits the gap', () {
      final RiskAssessment risk = SafetyScore.assess(day(gust: 12));
      expect(risk.level, RiskLevel.safe);
      expect(risk.missingSeaState, isTrue);

      final RiskAssessment withWave =
          SafetyScore.assess(day(gust: 12, wave: 0.5));
      expect(withWave.missingSeaState, isFalse);
    });
  });
}
