import 'daily_outlook.dart';
import 'weather_snapshot.dart';

/// An hourly forecast interval carrying atmospheric and marine predictions.
class HourlyInterval {
  const HourlyInterval({
    required this.time,
    this.weatherCode,
    this.tempC,
    this.windKph,
    this.gustKph,
    this.precipMm,
    this.waveM,
  });

  final DateTime time;
  final int? weatherCode;
  final double? tempC;
  final double? windKph;
  final double? gustKph;
  final double? precipMm;
  final double? waveM;

  WeatherCondition? get condition =>
      weatherCode != null ? WeatherCondition.tryFromCode(weatherCode) : null;

  Map<String, Object?> toCacheJson() => <String, Object?>{
        'time': time.toIso8601String(),
        'weather_code': weatherCode,
        'temp_c': tempC,
        'wind_kph': windKph,
        'gust_kph': gustKph,
        'precip_mm': precipMm,
        'wave_m': waveM,
      };

  static HourlyInterval? fromCacheJson(Object? raw) {
    if (raw is! Map) return null;
    final timeStr = raw['time'];
    if (timeStr is! String) return null;
    final time = DateTime.tryParse(timeStr);
    if (time == null) return null;

    return HourlyInterval(
      time: time,
      weatherCode: _int(raw['weather_code']),
      tempC: _double(raw['temp_c']),
      windKph: _nonnegativeDouble(raw['wind_kph']),
      gustKph: _nonnegativeDouble(raw['gust_kph']),
      precipMm: _nonnegativeDouble(raw['precip_mm']),
      waveM: _nonnegativeDouble(raw['wave_m']),
    );
  }

  static double? _nonnegativeDouble(Object? value) {
    if (value is num) {
      final double d = value.toDouble();
      return (d.isFinite && d >= 0) ? d : null;
    }
    return null;
  }

  static double? _double(Object? value) {
    if (value is num) {
      final double d = value.toDouble();
      return d.isFinite ? d : null;
    }
    return null;
  }

  static int? _int(Object? value) => value is num ? value.toInt() : null;
}

/// The complete forecast dataset holding daily outlooks, hourly intervals,
/// retrieval time, and provenance metadata.
class ForecastOutlook {
  const ForecastOutlook({
    required this.days,
    required this.hours,
    required this.fetchedAt,
    this.generatedAt,
    this.latitude,
    this.longitude,
    this.requestedLatitude,
    this.requestedLongitude,
    this.issueTime,
    this.timezone,
    this.timezoneAbbreviation,
    this.utcOffsetSeconds,
    this.source = 'backend',
    this.units = const <String, String>{},
    this.marineSampleLat,
    this.marineSampleLon,
  });

  final List<DailyOutlook> days;
  final List<HourlyInterval> hours;
  final DateTime fetchedAt;
  final DateTime? generatedAt;
  final double? latitude;
  final double? longitude;
  final double? requestedLatitude;
  final double? requestedLongitude;
  final DateTime? issueTime;
  final String? timezone;
  final String? timezoneAbbreviation;
  final int? utcOffsetSeconds;
  final String source;
  final Map<String, String> units;
  final double? marineSampleLat;
  final double? marineSampleLon;

  bool get hasHourly => hours.isNotEmpty;

  ForecastOutlook copyWith({
    List<DailyOutlook>? days,
    List<HourlyInterval>? hours,
    DateTime? fetchedAt,
    DateTime? generatedAt,
    double? latitude,
    double? longitude,
    double? requestedLatitude,
    double? requestedLongitude,
    DateTime? issueTime,
    String? timezone,
    String? timezoneAbbreviation,
    int? utcOffsetSeconds,
    String? source,
    Map<String, String>? units,
    double? marineSampleLat,
    double? marineSampleLon,
  }) =>
      ForecastOutlook(
        days: days ?? this.days,
        hours: hours ?? this.hours,
        fetchedAt: fetchedAt ?? this.fetchedAt,
        generatedAt: generatedAt ?? this.generatedAt,
        latitude: latitude ?? this.latitude,
        longitude: longitude ?? this.longitude,
        requestedLatitude: requestedLatitude ?? this.requestedLatitude,
        requestedLongitude: requestedLongitude ?? this.requestedLongitude,
        issueTime: issueTime ?? this.issueTime,
        timezone: timezone ?? this.timezone,
        timezoneAbbreviation:
            timezoneAbbreviation ?? this.timezoneAbbreviation,
        utcOffsetSeconds: utcOffsetSeconds ?? this.utcOffsetSeconds,
        source: source ?? this.source,
        units: units ?? this.units,
        marineSampleLat: marineSampleLat ?? this.marineSampleLat,
        marineSampleLon: marineSampleLon ?? this.marineSampleLon,
      );

  Map<String, Object?> toCacheJson() => <String, Object?>{
        'version': 2,
        'fetched_at': fetchedAt.toIso8601String(),
        'generated_at': generatedAt?.toIso8601String(),
        'latitude': latitude,
        'longitude': longitude,
        'requested_latitude': requestedLatitude,
        'requested_longitude': requestedLongitude,
        'issue_time': issueTime?.toIso8601String(),
        'timezone': timezone,
        'timezone_abbreviation': timezoneAbbreviation,
        'utc_offset_seconds': utcOffsetSeconds,
        'source': source,
        'units': units,
        'marine_sample_lat': marineSampleLat,
        'marine_sample_lon': marineSampleLon,
        'days': days.map((d) => d.toCacheJson()).toList(growable: false),
        'hours': hours.map((h) => h.toCacheJson()).toList(growable: false),
      };

  static ForecastOutlook? fromCacheJson(Object? raw) {
    if (raw is! Map) return null;
    final fetchedAtStr = raw['fetched_at'];
    if (fetchedAtStr is! String) return null;
    final fetchedAt = DateTime.tryParse(fetchedAtStr);
    if (fetchedAt == null) return null;

    final daysRaw = raw['days'];
    final List<DailyOutlook> days = <DailyOutlook>[];
    if (daysRaw is List) {
      for (final item in daysRaw) {
        final d = DailyOutlook.fromCacheJson(item);
        if (d != null) days.add(d);
      }
    }

    final hoursRaw = raw['hours'];
    final Map<DateTime, HourlyInterval> hoursMap = <DateTime, HourlyInterval>{};
    if (hoursRaw is List) {
      for (final item in hoursRaw) {
        final h = HourlyInterval.fromCacheJson(item);
        if (h != null) mergeInterval(hoursMap, h);
      }
    }
    final hours = hoursMap.values.toList()..sort((a, b) => a.time.compareTo(b.time));

    final unitsRaw = raw['units'];
    final Map<String, String> units = <String, String>{};
    if (unitsRaw is Map) {
      for (final entry in unitsRaw.entries) {
        if (entry.key is String && entry.value is String) {
          units[entry.key as String] = entry.value as String;
        }
      }
    }

    final genStr = raw['generated_at'];
    final issueStr = raw['issue_time'];

    return ForecastOutlook(
      days: days,
      hours: hours,
      fetchedAt: fetchedAt,
      generatedAt: genStr is String ? DateTime.tryParse(genStr) : null,
      latitude: _double(raw['latitude']),
      longitude: _double(raw['longitude']),
      requestedLatitude: _double(raw['requested_latitude']),
      requestedLongitude: _double(raw['requested_longitude']),
      issueTime: issueStr is String ? DateTime.tryParse(issueStr) : null,
      timezone: raw['timezone'] is String ? raw['timezone'] as String : null,
      timezoneAbbreviation: raw['timezone_abbreviation'] is String
          ? raw['timezone_abbreviation'] as String
          : null,
      utcOffsetSeconds: _int(raw['utc_offset_seconds']),
      source: raw['source'] is String ? raw['source'] as String : 'cache',
      units: units,
      marineSampleLat: _double(raw['marine_sample_lat']),
      marineSampleLon: _double(raw['marine_sample_lon']),
    );
  }

  /// Parses the AqOne `/api/public/forecast` response payload.
  static ForecastOutlook? parseBackend(
    Object? decoded, {
    required DateTime fetchedAt,
    String source = 'backend',
  }) {
    if (decoded is! Map) return null;

    final days = DailyOutlook.parseAqOneList(decoded);
    if (days == null) return null;

    final offset = _int(decoded['utc_offset_seconds']);
    final Map<DateTime, HourlyInterval> hoursMap = <DateTime, HourlyInterval>{};
    final rawHours = decoded['hours'];
    if (rawHours is List) {
      for (final item in rawHours) {
        if (item is Map) {
          final timeStr = item['time'];
          if (timeStr is String) {
            final time = parseForecastTime(timeStr, offset);
            if (time != null) {
              mergeInterval(
                hoursMap,
                HourlyInterval(
                  time: time,
                  weatherCode: _int(item['weather_code']),
                  tempC: _double(item['temp_c']),
                  windKph: _nonnegativeDouble(item['wind_kph']),
                  gustKph: _nonnegativeDouble(item['gust_kph']),
                  precipMm: _nonnegativeDouble(item['precip_mm']),
                  waveM: _nonnegativeDouble(item['wave_m']),
                ),
              );
            }
          }
        }
      }
    }
    final hours = hoursMap.values.toList()..sort((a, b) => a.time.compareTo(b.time));

    final rawUnits = decoded['units'];
    final units = <String, String>{};
    if (rawUnits is Map) {
      for (final e in rawUnits.entries) {
        if (e.key is String && e.value is String) {
          units[e.key as String] = e.value as String;
        }
      }
    }

    final genStr = decoded['generated_at'];
    final issueStr = decoded['model_issue_time'] ?? decoded['issue_time'];
    final backendSource =
        decoded['source'] is String ? decoded['source'] as String : source;

    return ForecastOutlook(
      days: days,
      hours: hours,
      fetchedAt: fetchedAt,
      generatedAt: genStr is String ? DateTime.tryParse(genStr) : null,
      latitude: _double(decoded['latitude']),
      longitude: _double(decoded['longitude']),
      requestedLatitude: _double(decoded['requested_latitude']),
      requestedLongitude: _double(decoded['requested_longitude']),
      issueTime: issueStr is String ? DateTime.tryParse(issueStr) : null,
      timezone: decoded['timezone'] is String ? decoded['timezone'] as String : null,
      timezoneAbbreviation: decoded['timezone_abbreviation'] is String
          ? decoded['timezone_abbreviation'] as String
          : null,
      utcOffsetSeconds: offset,
      source: backendSource,
      units: units,
    );
  }

  /// Parses direct Open-Meteo atmospheric and marine payloads (used in fallback).
  static ForecastOutlook? parseOpenMeteo({
    required Object? atmo,
    required Object? marine,
    required DateTime fetchedAt,
    double? lat,
    double? lon,
    double? marineLat,
    double? marineLon,
    String source = 'open-meteo-fallback',
  }) {
    if (atmo is! Map) return null;
    final List<DailyOutlook>? outlook = DailyOutlook.parseOpenMeteoList(atmo);
    if (outlook == null) return null;

    final Map<DateTime, double> wavesByDay =
        DailyOutlook.parseMarineDailyMax(marine);

    final days = outlook.map((day) {
      final key = DateTime(day.date.year, day.date.month, day.date.day);
      final wave = wavesByDay[key];
      return wave == null ? day : day.copyWith(waveM: wave);
    }).toList(growable: false);

    final offset = _int(atmo['utc_offset_seconds']);

    // Parse hourly marine wave heights by parsed timestamp
    final marineWavesByTime = <DateTime, double>{};
    if (marine is Map) {
      final hourly = marine['hourly'];
      if (hourly is Map) {
        final mTimes = hourly['time'];
        final mWaves = hourly['wave_height'];
        if (mTimes is List && mWaves is List) {
          final count =
              mTimes.length < mWaves.length ? mTimes.length : mWaves.length;
          final marineOffset = _int(marine['utc_offset_seconds']) ?? offset;
          for (int i = 0; i < count; i++) {
            final tStr = mTimes[i];
            final w = _nonnegativeDouble(mWaves[i]);
            if (tStr is String && w != null) {
              final t = parseForecastTime(tStr, marineOffset);
              if (t != null) {
                marineWavesByTime[t] = maxNullable(marineWavesByTime[t], w)!;
              }
            }
          }
        }
      }
    }

    // Parse hourly atmospheric series and join with marine conservatively
    final Map<DateTime, HourlyInterval> hoursMap = <DateTime, HourlyInterval>{};
    final hourly = atmo['hourly'];
    if (hourly is Map) {
      final aTimes = hourly['time'];
      if (aTimes is List) {
        final codes = hourly['weather_code'];
        final temps = hourly['temperature_2m'];
        final winds = hourly['wind_speed_10m'];
        final gusts = hourly['wind_gusts_10m'];
        final precips = hourly['precipitation'];

        for (int i = 0; i < aTimes.length; i++) {
          final tStr = aTimes[i];
          if (tStr is! String) continue;
          final time = parseForecastTime(tStr, offset);
          if (time == null) continue;

          final wave = marineWavesByTime[time];
          mergeInterval(
            hoursMap,
            HourlyInterval(
              time: time,
              weatherCode: _int(_at(codes, i)),
              tempC: _double(_at(temps, i)),
              windKph: _nonnegativeDouble(_at(winds, i)),
              gustKph: _nonnegativeDouble(_at(gusts, i)),
              precipMm: _nonnegativeDouble(_at(precips, i)),
              waveM: wave,
            ),
          );
        }
      }
    }
    final hours = hoursMap.values.toList()..sort((a, b) => a.time.compareTo(b.time));

    return ForecastOutlook(
      days: days,
      hours: hours,
      fetchedAt: fetchedAt,
      generatedAt: fetchedAt,
      latitude: _double(atmo['latitude']) ?? lat,
      longitude: _double(atmo['longitude']) ?? lon,
      requestedLatitude: lat,
      requestedLongitude: lon,
      issueTime: null,
      timezone: atmo['timezone'] is String ? atmo['timezone'] as String : null,
      timezoneAbbreviation: atmo['timezone_abbreviation'] is String
          ? atmo['timezone_abbreviation'] as String
          : null,
      utcOffsetSeconds: offset,
      source: source,
      marineSampleLat: marineLat,
      marineSampleLon: marineLon,
    );
  }

  /// Parses a timestamp string using declared utcOffsetSeconds if no zone offset is present.
  static DateTime? parseForecastTime(String timeStr, int? utcOffsetSeconds) {
    if (timeStr.endsWith('Z') ||
        timeStr.contains('+') ||
        (timeStr.length > 10 && timeStr.substring(10).contains('-'))) {
      return DateTime.tryParse(timeStr)?.toUtc();
    }
    final normalized = timeStr.replaceFirst(' ', 'T');
    final dtUtc = DateTime.tryParse('${normalized}Z');
    if (dtUtc == null) return null;
    if (utcOffsetSeconds != null) {
      return dtUtc.subtract(Duration(seconds: utcOffsetSeconds));
    }
    return dtUtc;
  }

  static double? maxNullable(double? a, double? b) {
    if (a == null) return b;
    if (b == null) return a;
    return a > b ? a : b;
  }

  static int? moreSevereWeatherCode(int? a, int? b) {
    if (a == null) return b;
    if (b == null) return a;
    if (a == b) return a;
    final condA = WeatherCondition.tryFromCode(a);
    final condB = WeatherCondition.tryFromCode(b);
    int rank(WeatherCondition? c) => switch (c) {
          WeatherCondition.severeThunderstorm => 6,
          WeatherCondition.thunderstorm => 5,
          WeatherCondition.heavyRain => 4,
          WeatherCondition.showers || WeatherCondition.rainy => 3,
          WeatherCondition.foggy => 2,
          _ => 1,
        };
    return rank(condA) >= rank(condB) ? a : b;
  }

  static void mergeInterval(
    Map<DateTime, HourlyInterval> map,
    HourlyInterval next,
  ) {
    final existing = map[next.time];
    if (existing == null) {
      map[next.time] = next;
    } else {
      map[next.time] = HourlyInterval(
        time: next.time,
        weatherCode:
            moreSevereWeatherCode(existing.weatherCode, next.weatherCode),
        tempC: existing.tempC ?? next.tempC,
        windKph: maxNullable(existing.windKph, next.windKph),
        gustKph: maxNullable(existing.gustKph, next.gustKph),
        precipMm: maxNullable(existing.precipMm, next.precipMm),
        waveM: maxNullable(existing.waveM, next.waveM),
      );
    }
  }

  static Object? _at(Object? list, int index) {
    if (list is List && index < list.length) {
      return list[index];
    }
    return null;
  }

  static double? _nonnegativeDouble(Object? value) {
    if (value is num) {
      final double d = value.toDouble();
      return (d.isFinite && d >= 0) ? d : null;
    }
    return null;
  }

  static double? _double(Object? value) {
    if (value is num) {
      final double d = value.toDouble();
      return d.isFinite ? d : null;
    }
    return null;
  }

  static int? _int(Object? value) => value is num ? value.toInt() : null;
}
