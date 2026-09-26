import '../core/config.dart';
import '../models/daily_outlook.dart';
import '../models/weather_snapshot.dart';

/// Device-side fallback scoring.
///
/// FALLBACK ONLY. The intended source of a risk verdict is the backend, which
/// fuses buoy sensor telemetry with a weather provider and can see things this
/// cannot - actual measured sea state at a known point, drift, other boats'
/// reports. This exists so the forecast strip is useful before that endpoint
/// exists, and so it degrades to something honest when the backend is
/// unreachable at sea.
///
/// Everything here is a threshold comparison on public forecast data. It has
/// no knowledge of tide, local bathymetry, the particular boat, or who is on
/// it. Anything it produces is labelled as guidance in the UI, never as a
/// decision.
class SafetyScore {
  const SafetyScore._();

  /// Scores a day that arrived without a backend verdict.
  ///
  /// Returns the day unchanged when the backend already supplied one - a
  /// server that has seen real buoy data always outranks this.
  static DailyOutlook applyTo(DailyOutlook day) {
    if (day.risk.source == RiskSource.backend &&
        day.risk.level != RiskLevel.unknown) {
      return day;
    }
    return day.copyWith(risk: assess(day));
  }

  static RiskAssessment assess(DailyOutlook day) {
    final List<String> inputs = <String>['open-meteo'];
    final List<RiskFactor> reasons = <RiskFactor>[];
    RiskLevel level = RiskLevel.safe;

    void raise(RiskLevel to) {
      if (to.index > level.index && to != RiskLevel.unknown) {
        level = to;
      }
    }

    // Gusts, not mean wind. A 24 km/h average with 50 km/h gusts is what
    // actually swamps a small boat, and the mean hides it.
    final bool hasExplicitGust = day.gustKph != null;
    final double? gust = day.gustKph ?? day.windKph;
    if (gust != null) {
      final RiskFactor windDesc = RiskFactor(
        hasExplicitGust ? RiskFactorKind.gusts : RiskFactorKind.wind,
        gust.round(),
      );
      if (gust >= AqOneConfig.dangerGustKph) {
        raise(RiskLevel.danger);
        reasons.add(windDesc);
      } else if (gust >= AqOneConfig.cautionGustKph) {
        raise(RiskLevel.caution);
        reasons.add(windDesc);
      }
    }

    final double? wave = day.waveM;
    if (wave != null) {
      inputs.add('wave');
      if (wave >= AqOneConfig.dangerWaveM) {
        raise(RiskLevel.danger);
        reasons.add(RiskFactor(RiskFactorKind.swell, wave));
      } else if (wave >= AqOneConfig.cautionWaveM) {
        raise(RiskLevel.caution);
        reasons.add(RiskFactor(RiskFactorKind.swell, wave));
      }
    }

    final double? precip = day.precipMm;
    if (precip != null) {
      if (precip >= AqOneConfig.dangerPrecipMm) {
        raise(RiskLevel.danger);
        reasons.add(RiskFactor(RiskFactorKind.rainMm, precip.round()));
      } else if (precip >= AqOneConfig.cautionPrecipMm) {
        raise(RiskLevel.caution);
        reasons.add(RiskFactor(RiskFactorKind.rainMm, precip.round()));
      }
    }

    switch (day.condition) {
      case WeatherCondition.severeThunderstorm:
        raise(RiskLevel.danger);
        reasons.add(const RiskFactor(RiskFactorKind.severeThunderstorm));
      case WeatherCondition.thunderstorm:
        raise(RiskLevel.danger);
        reasons.add(const RiskFactor(RiskFactorKind.thunderstorm));
      case WeatherCondition.heavyRain:
        raise(RiskLevel.caution);
        reasons.add(const RiskFactor(RiskFactorKind.heavyRain));
      case WeatherCondition.showers:
      case WeatherCondition.rainy:
        raise(RiskLevel.caution);
        reasons.add(const RiskFactor(RiskFactorKind.rain));
      case WeatherCondition.foggy:
        // Carried over from the source project as safe, which was wrong: you
        // cannot see another boat, a net marker, or the shore in fog.
        raise(RiskLevel.caution);
        reasons.add(const RiskFactor(RiskFactorKind.poorVisibility));
      case WeatherCondition.drizzle:
      case WeatherCondition.overcast:
      case WeatherCondition.partlyCloudy:
      case WeatherCondition.sunny:
      case WeatherCondition.calm:
        break;
    }

    // If numeric inputs are absent, check if a recognized adverse weather condition
    // raised the level. Never erase thunderstorm/hazard evidence into unknown.
    if (gust == null && wave == null && precip == null) {
      if (level != RiskLevel.safe) {
        return RiskAssessment(
          level: level,
          source: RiskSource.device,
          score: _score(gust: gust, wave: wave, precip: precip),
          factors: reasons,
          inputs: inputs,
        );
      }
      return RiskAssessment.unknown;
    }

    return RiskAssessment(
      level: level,
      source: RiskSource.device,
      score: _score(gust: gust, wave: wave, precip: precip),
      factors: reasons,
      inputs: inputs,
    );
  }

  /// Continuous 0-1 severity, kept alongside the bucketed level so the fused
  /// backend score can slot into the same field later without a UI change.
  static double _score({double? gust, double? wave, double? precip}) {
    double worst = 0;
    if (gust != null) {
      worst = _max(worst, gust / (AqOneConfig.dangerGustKph * 1.4));
    }
    if (wave != null) {
      worst = _max(worst, wave / (AqOneConfig.dangerWaveM * 1.4));
    }
    if (precip != null) {
      worst = _max(worst, precip / (AqOneConfig.dangerPrecipMm * 1.4));
    }
    return worst.clamp(0.0, 1.0);
  }

  static double _max(double a, double b) => a > b ? a : b;
}
