import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import '../core/config.dart';

/// A current-conditions reading from Open-Meteo.
///
/// Weather does not come from the AqOne backend. It is a public third-party
/// reading and is treated as advisory only - the authoritative go/no-go signal
/// is the MDRRMO-set sea condition.
class WeatherSnapshot {
  const WeatherSnapshot({
    required this.temperature,
    required this.windSpeed,
    required this.weatherCode,
  });

  /// Degrees Celsius.
  final double temperature;

  /// Kilometres per hour.
  final double windSpeed;

  /// WMO weather interpretation code.
  final int weatherCode;

  static WeatherSnapshot? tryParse(Object? payload) {
    if (payload is! Map) {
      return null;
    }
    final current = payload['current_weather'];
    if (current is! Map) {
      return null;
    }
    final temperature = current['temperature'];
    final windSpeed = current['windspeed'];
    final weatherCode = current['weathercode'];
    if (temperature is! num || windSpeed is! num || weatherCode is! num) {
      return null;
    }
    final parsedTemperature = temperature.toDouble();
    final parsedWindSpeed = windSpeed.toDouble();
    if (!parsedTemperature.isFinite || !parsedWindSpeed.isFinite) {
      return null;
    }
    return WeatherSnapshot(
      temperature: parsedTemperature,
      windSpeed: parsedWindSpeed,
      weatherCode: weatherCode.toInt(),
    );
  }

  WeatherCondition get condition => WeatherCondition.fromCode(weatherCode);

  /// Client-side go/no-go heuristic.
  ///
  /// IMPORTANT: this is a crude threshold, not an authoritative decision. It
  /// ignores the official sea condition, buoy hazards, wave height and tide.
  /// Anything shown from this must be labelled as informational.
  ///
  /// The condition buckets were widened when the forecast strip landed, so
  /// this now has to name the wet ones explicitly. Fog and showers are still
  /// treated as safe here, which is too permissive - but this only drives the
  /// current-conditions note, and the forecast strip's SafetyScore is the
  /// place where that judgement is made properly.
  bool get hasHighWind => windSpeed > AqOneConfig.unsafeWindKph;

  bool get hasAdverseCondition =>
      condition == WeatherCondition.thunderstorm ||
      condition == WeatherCondition.severeThunderstorm ||
      condition == WeatherCondition.heavyRain ||
      condition == WeatherCondition.rainy;

  bool get looksUnsafe => hasHighWind || hasAdverseCondition;
}

/// WMO code buckets, one per distinguishable icon.
///
/// Widened from the source project's seven buckets: every wet code from
/// drizzle to a downpour used to collapse into a single umbrella, so a
/// thunderstorm on Thursday looked exactly like light drizzle on Tuesday.
/// A forecast strip is useless if the days do not look different.
enum WeatherCondition {
  sunny(Icons.wb_sunny_rounded),
  partlyCloudy(Icons.wb_cloudy_rounded),
  overcast(Icons.cloud_rounded),
  foggy(Icons.foggy),
  // Icons are deliberately drawn from the long-standing Material set rather
  // than the newer weather symbols (Icons.rainy and friends), which do not
  // exist on every Flutter version this has to build against.
  drizzle(Icons.blur_on_rounded),
  rainy(Icons.umbrella_rounded),
  heavyRain(Icons.water_drop_rounded),
  showers(Icons.grain_rounded),
  thunderstorm(Icons.thunderstorm_rounded),
  severeThunderstorm(Icons.flash_on_rounded),
  calm(Icons.wb_sunny_rounded);

  const WeatherCondition(this.icon);

  final IconData icon;

  /// WMO 4677 interpretation codes as served by Open-Meteo. Returns null
  /// if the code is negative, unrecognized, or missing.
  static WeatherCondition? tryFromCode(int? code) {
    if (code == null || code < 0) {
      return null;
    }
    if (code == 0) {
      return WeatherCondition.sunny;
    }
    if (code >= 1 && code <= 2) {
      return WeatherCondition.partlyCloudy;
    }
    if (code == 3) {
      return WeatherCondition.overcast;
    }
    if (code == 45 || code == 48) {
      return WeatherCondition.foggy;
    }
    // 51-57 drizzle and freezing drizzle.
    if (code >= 51 && code <= 57) {
      return WeatherCondition.drizzle;
    }
    // 61 slight, 63 moderate, 65 heavy rain; 66/67 freezing rain.
    if (code == 65 || code == 67) {
      return WeatherCondition.heavyRain;
    }
    if (code >= 61 && code <= 67) {
      return WeatherCondition.rainy;
    }
    // 71-77 snow: not a Philippine concern, but the codes exist and must not
    // fall through to "calm".
    if (code >= 71 && code <= 77) {
      return WeatherCondition.heavyRain;
    }
    // 80 slight showers, 81 moderate, 82 violent.
    if (code == 82) {
      return WeatherCondition.heavyRain;
    }
    if (code >= 80 && code <= 81) {
      return WeatherCondition.showers;
    }
    if (code == 85 || code == 86) {
      return WeatherCondition.showers;
    }
    // 95 thunderstorm; 96/99 thunderstorm with hail.
    if (code == 96 || code == 99) {
      return WeatherCondition.severeThunderstorm;
    }
    if (code >= 95 && code <= 99) {
      return WeatherCondition.thunderstorm;
    }
    return null;
  }

  /// WMO 4677 interpretation codes as served by Open-Meteo. Falls back to calm
  /// for legacy backwards-compatibility when a non-null enum is required.
  static WeatherCondition fromCode(int code) =>
      tryFromCode(code) ?? WeatherCondition.calm;
}

extension WeatherConditionL10n on WeatherCondition {
  String label(AppLocalizations t) => switch (this) {
        WeatherCondition.sunny => t.weatherConditionSunny,
        WeatherCondition.partlyCloudy => t.weatherConditionPartlyCloudy,
        WeatherCondition.overcast => t.weatherConditionOvercast,
        WeatherCondition.foggy => t.weatherConditionFoggy,
        WeatherCondition.drizzle => t.weatherConditionDrizzle,
        WeatherCondition.rainy => t.weatherConditionRainy,
        WeatherCondition.heavyRain => t.weatherConditionHeavyRain,
        WeatherCondition.showers => t.weatherConditionShowers,
        WeatherCondition.thunderstorm => t.weatherConditionThunderstorm,
        WeatherCondition.severeThunderstorm => t.weatherConditionSevereStorm,
        WeatherCondition.calm => t.weatherConditionCalm,
      };
}
