import 'dart:convert';

import 'package:aqone/data/forecast_cache.dart';
import 'package:aqone/models/daily_outlook.dart';
import 'package:aqone/models/forecast_outlook.dart';
import 'package:aqone/models/sea_condition.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  group('ForecastCache', () {
    const cache = ForecastCache();

    test('saves and loads v2 ForecastOutlook record', () async {
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final outlook = ForecastOutlook(
        days: <DailyOutlook>[
          DailyOutlook(
            date: today,
            weatherCode: 1,
            tempMax: 30.0,
            tempMin: 24.0,
            risk: const RiskAssessment(
              level: RiskLevel.safe,
              source: RiskSource.backend,
            ),
          ),
          DailyOutlook(
            date: today.add(const Duration(days: 1)),
            weatherCode: 2,
            risk: const RiskAssessment(
              level: RiskLevel.caution,
              source: RiskSource.backend,
            ),
          ),
        ],
        hours: <HourlyInterval>[
          HourlyInterval(
            time: today.add(const Duration(hours: 6)),
            weatherCode: 1,
            tempC: 26.0,
            windKph: 15.0,
            waveM: 0.8,
          ),
        ],
        fetchedAt: now.subtract(const Duration(minutes: 5)),
        source: 'backend',
        latitude: 11.68,
        longitude: 122.41,
      );

      await cache.saveOutlook(outlook);

      final loaded = await cache.load();
      expect(loaded, isNotNull);
      expect(loaded!.days.length, 2);
      expect(loaded.fetchedAt, outlook.fetchedAt);
      expect(loaded.outlook, isNotNull);
      expect(loaded.outlook!.hours.length, 1);
      expect(loaded.outlook!.hours.single.tempC, 26.0);
      expect(loaded.outlook!.hours.single.windKph, 15.0);
      expect(loaded.outlook!.hours.single.waveM, 0.8);
      expect(loaded.outlook!.source, 'backend');

      final loadedOutlook = (await cache.load())?.outlook;
      expect(loadedOutlook, isNotNull);
      expect(loadedOutlook!.hours.length, 1);
    });

    test('falls back to legacy v1 keys when v2 key is absent', () async {
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final fetchedAt = now.subtract(const Duration(minutes: 10));

      final legacyDays = <Map<String, Object?>>[
        <String, Object?>{
          'date': today.toIso8601String(),
          'weather_code': 3,
          'max_temp_c': 29.0,
          'min_temp_c': 23.0,
          'risk_level': 1,
        },
      ];

      SharedPreferences.setMockInitialValues(<String, Object>{
        'forecast_days_v1': jsonEncode(legacyDays),
        'forecast_fetched_at_v1': fetchedAt.toIso8601String(),
      });

      final loaded = await cache.load();
      expect(loaded, isNotNull);
      expect(loaded!.days.length, 1);
      expect(loaded.days.single.weatherCode, 3);
      expect(loaded.fetchedAt, fetchedAt);
      expect(loaded.outlook, isNotNull);
      expect(loaded.outlook!.hours, isEmpty);
      expect(loaded.outlook!.source, 'cache_v1');
    });

    test('rejects cached entries older than 12 hours', () async {
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final expiredAt = now.subtract(const Duration(hours: 13));

      final outlook = ForecastOutlook(
        days: <DailyOutlook>[
          DailyOutlook(
            date: today,
            weatherCode: 1,
            risk: const RiskAssessment(
              level: RiskLevel.safe,
              source: RiskSource.backend,
            ),
          ),
        ],
        hours: const <HourlyInterval>[],
        fetchedAt: expiredAt,
      );

      SharedPreferences.setMockInitialValues(<String, Object>{
        'forecast_record_v2': jsonEncode(outlook.toCacheJson()),
      });

      final loaded = await cache.load();
      expect(loaded, isNull);
    });

    test('rejects future timestamps beyond 1 minute skew threshold', () async {
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final futureAt = now.add(const Duration(minutes: 5));

      final outlook = ForecastOutlook(
        days: <DailyOutlook>[
          DailyOutlook(
            date: today,
            weatherCode: 1,
            risk: const RiskAssessment(
              level: RiskLevel.safe,
              source: RiskSource.backend,
            ),
          ),
        ],
        hours: const <HourlyInterval>[],
        fetchedAt: futureAt,
      );

      SharedPreferences.setMockInitialValues(<String, Object>{
        'forecast_record_v2': jsonEncode(outlook.toCacheJson()),
      });

      final loaded = await cache.load();
      expect(loaded, isNull);
    });

    test('recovers gracefully from corrupted JSON payload', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        'forecast_record_v2': '{bad-json',
        'forecast_days_v1': 'not-json',
        'forecast_fetched_at_v1': DateTime.now().toIso8601String(),
      });

      final loaded = await cache.load();
      expect(loaded, isNull);
    });

    test('drops past days so first chip is today or later', () async {
      final now = DateTime.now();
      final yesterday = DateTime(now.year, now.month, now.day)
          .subtract(const Duration(days: 1));
      final today = DateTime(now.year, now.month, now.day);

      final outlook = ForecastOutlook(
        days: <DailyOutlook>[
          DailyOutlook(
            date: yesterday,
            weatherCode: 95,
            risk: const RiskAssessment(
              level: RiskLevel.caution,
              source: RiskSource.backend,
            ),
          ),
          DailyOutlook(
            date: today,
            weatherCode: 1,
            risk: const RiskAssessment(
              level: RiskLevel.safe,
              source: RiskSource.backend,
            ),
          ),
        ],
        hours: const <HourlyInterval>[],
        fetchedAt: now.subtract(const Duration(minutes: 2)),
      );

      await cache.saveOutlook(outlook);
      final loaded = await cache.load();

      expect(loaded, isNotNull);
      expect(loaded!.days.length, 1);
      expect(loaded.days.single.date, today);
    });
  });

  group('SeaCondition timestamp provenance', () {
    test('preserves explicit fetchedAt timestamp when loaded from cache', () {
      final cachedTime = DateTime.now().subtract(const Duration(minutes: 15));
      final json = <String, Object?>{
        'status': 'normal',
        'reason': 'Calm waters',
      };

      final condition = SeaCondition.tryParse(json, fetchedAt: cachedTime);
      expect(condition, isNotNull);
      expect(condition!.fetchedAt, cachedTime);
      expect(condition.isStale(threshold: const Duration(minutes: 10)), isTrue);
    });

    test('defaults fetchedAt to now when not explicitly passed', () {
      final json = <String, Object?>{
        'status': 'normal',
      };

      final condition = SeaCondition.tryParse(json);
      expect(condition, isNotNull);
      expect(condition!.isStale(threshold: const Duration(minutes: 1)), isFalse);
    });

    test('reads set_by_label when present without exposing operator account', () {
      final json = <String, Object?>{
        'status': 'safe',
        'reason': 'Calm sea',
        'set_by_label': 'MDRRMO Officer Juan',
      };

      final condition = SeaCondition.tryParse(json);
      expect(condition, isNotNull);
      expect(condition!.setByName, 'MDRRMO Officer Juan');
    });

    test('falls back to set_by_name when set_by_label is absent', () {
      final json = <String, Object?>{
        'status': 'safe',
        'reason': 'Calm sea',
        'set_by_name': 'Legacy MDRRMO',
      };

      final condition = SeaCondition.tryParse(json);
      expect(condition, isNotNull);
      expect(condition!.setByName, 'Legacy MDRRMO');
    });
  });
}
