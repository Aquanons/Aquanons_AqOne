import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/config.dart';
import '../../models/daily_outlook.dart';
import '../../models/forecast_outlook.dart';
import '../../models/sea_condition.dart';
import '../../models/squall_watch.dart';
import '../../models/weather_snapshot.dart';
import '../../services/fishing_window.dart';

/// Current conditions, fishing weather window, and seven-day outlook from Open-Meteo.
///
/// Weather is a third-party reading, not an AqOne judgement, and this sits
/// below the sea-condition banner so the official MDRRMO call always reads
/// first. Nothing in this card is permission to go out - the colours are
/// forecast guidance, deliberately styled quieter than the banner above.
class WeatherCard extends StatelessWidget {
  const WeatherCard({
    super.key,
    required this.snapshot,
    required this.isLoading,
    required this.onRetry,
    this.forecast = const <DailyOutlook>[],
    this.forecastOutlook,
    this.seaCondition,
    this.squall,
    this.now,
    this.forecastAge,
    this.locationLabel = 'Aklan',
  });

  final WeatherSnapshot? snapshot;
  final bool isLoading;
  final VoidCallback onRetry;

  /// Up to [AqOneConfig.forecastDays] days, today first. Empty while loading
  /// or when every source failed.
  final List<DailyOutlook> forecast;

  /// Complete forecast result including hourly intervals and provenance.
  final ForecastOutlook? forecastOutlook;

  /// Current official MDRRMO sea condition call.
  final SeaCondition? seaCondition;

  /// Current squall watch / return-now alert.
  final SquallWatch? squall;

  /// Injected clock for deterministic rendering and testing.
  final DateTime? now;

  /// When the shown forecast was fetched. Non-null only when it came from the
  /// offline cache, so a stale strip can say so instead of passing itself off
  /// as live.
  final DateTime? forecastAge;

  /// Home reads a fixed municipal position rather than device GPS, so the
  /// card says where the reading is actually from.
  final String locationLabel;

  @override
  Widget build(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;
    final List<DailyOutlook> effectiveDays = forecast.isNotEmpty
        ? forecast
        : (forecastOutlook?.days ?? const <DailyOutlook>[]);

    final bool shouldCalculateWindow = forecastOutlook != null ||
        seaCondition?.status == SeaStatus.notAdvised ||
        seaCondition?.status == SeaStatus.caution ||
        squall?.level == SquallLevel.returnNow ||
        squall?.level == SquallLevel.watch ||
        squall?.returnNow == true;

    final FishingWindowResult? windowResult = shouldCalculateWindow
        ? FishingWindowCalculator.calculate(
            forecast: forecastOutlook,
            seaCondition: seaCondition,
            squall: squall,
            now: now ?? DateTime.now(),
          )
        : null;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (windowResult != null) ...<Widget>[
            _FishingWindowSummary(
              result: windowResult,
              forecast: forecastOutlook,
              isDark: isDark,
              locationLabel: locationLabel,
              onRetry: onRetry,
            ),
            const SizedBox(height: 14),
            Divider(
              height: 1,
              color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
            ),
            const SizedBox(height: 14),
          ],
          if (effectiveDays.isNotEmpty) ...<Widget>[
            _ForecastStrip(
              days: effectiveDays,
              isDark: isDark,
              age: forecastAge ?? forecastOutlook?.fetchedAt,
            ),
            const SizedBox(height: 14),
            Divider(
              height: 1,
              color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
            ),
            const SizedBox(height: 14),
          ],
          _buildContent(context, isDark),
        ],
      ),
    );
  }

  Widget _buildContent(BuildContext context, bool isDark) {
    final AppLocalizations t = AppLocalizations.of(context);
    if (isLoading && snapshot == null) {
      return Row(
        children: <Widget>[
          const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              t.weatherLoading,
              style: const TextStyle(fontSize: 16),
            ),
          ),
        ],
      );
    }

    final WeatherSnapshot? value = snapshot;
    if (value == null) {
      return Row(
        children: <Widget>[
          Icon(
            Icons.cloud_off_rounded,
            size: 22,
            color: isDark ? Colors.white54 : const Color(0xFF94A3B8),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              t.weatherUnavailable,
              style: TextStyle(
                fontSize: 16,
                color: isDark ? Colors.white70 : const Color(0xFF475569),
              ),
            ),
          ),
          TextButton(onPressed: onRetry, child: Text(t.weatherRetry)),
        ],
      );
    }

    final WeatherCondition condition = value.condition;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(
              condition.icon,
              size: 34,
              color: isDark ? Colors.amber.shade300 : Colors.amber.shade700,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    condition.label(t),
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.white : const Color(0xFF0F172A),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    t.weatherWindLine(
                      value.windSpeed.toStringAsFixed(0),
                      locationLabel,
                    ),
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? Colors.white54 : const Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
            Text(
              '${value.temperature.toStringAsFixed(0)}°C',
              style: TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.w900,
                color: isDark ? Colors.white : const Color(0xFF0B4C8C),
              ),
            ),
          ],
        ),
        if (value.looksUnsafe) ...<Widget>[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFFD97706).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: <Widget>[
                const Icon(
                  Icons.info_outline_rounded,
                  size: 15,
                  color: Color(0xFF8A5A12),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    <String>[
                      value.hasHighWind
                          ? t.weatherHighWindNote(
                              value.windSpeed.toStringAsFixed(0),
                              AqOneConfig.unsafeWindKph.toStringAsFixed(0),
                            )
                          : t.weatherAdverseNote(value.condition.label(t)),
                      t.weatherSourceNote,
                    ].join(' '),
                    style: const TextStyle(
                      fontSize: 16,
                      height: 1.35,
                      color: Color(0xFF8A5A12),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// Compact fishing weather window summary card.
class _FishingWindowSummary extends StatelessWidget {
  const _FishingWindowSummary({
    required this.result,
    this.forecast,
    required this.isDark,
    required this.locationLabel,
    required this.onRetry,
  });

  final FishingWindowResult result;
  final ForecastOutlook? forecast;
  final bool isDark;
  final String locationLabel;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final AppLocalizations t = AppLocalizations.of(context);
    final _SummaryStyle style = _resolveStyle(result, isDark, t);
    final String headline = _resolveHeadline(result, context, t);
    final String? subtitle = _resolveSubtitle(result, context, t);

    return Semantics(
      label: '${t.weatherWindowTitle}. $headline. ${subtitle ?? ''}',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: style.backgroundColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: style.borderColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Icon(
                  style.icon,
                  size: 18,
                  color: style.iconColor,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    t.weatherWindowTitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
                      color: isDark ? Colors.white70 : const Color(0xFF334155),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                    decoration: BoxDecoration(
                      color: style.badgeBackgroundColor,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      style.badgeText,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: style.badgeTextColor,
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              headline,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: style.headlineColor,
              ),
            ),
            if (subtitle != null && subtitle.isNotEmpty) ...<Widget>[
              const SizedBox(height: 3),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  if (result.hasPositiveWindow &&
                      result.upcomingRisk != null) ...<Widget>[
                    Padding(
                      padding: const EdgeInsets.only(top: 2, right: 5),
                      child: Icon(
                        result.upcomingRisk!.icon,
                        size: 13,
                        color: result.upcomingRisk!.color,
                      ),
                    ),
                  ],
                  Expanded(
                    child: Text(
                      subtitle,
                      style: TextStyle(
                        fontSize: 16,
                        height: 1.35,
                        fontWeight: FontWeight.w500,
                        color: style.subtitleColor,
                      ),
                    ),
                  ),
                ],
              ),
            ],
            if (result.hasPositiveWindow) ...<Widget>[
              const SizedBox(height: 4),
              Text(
                t.weatherWindowReturnTravelDisclaimer,
                style: TextStyle(
                  fontSize: 16,
                  color: isDark ? Colors.white54 : const Color(0xFF64748B),
                ),
              ),
            ],
            const SizedBox(height: 8),
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    _footerProvenance(t),
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? Colors.white38 : const Color(0xFF94A3B8),
                    ),
                  ),
                ),
                if (_needsRetryAction(result.availability))
                  InkWell(
                    onTap: onRetry,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 4, vertical: 2),
                      child: Text(
                        t.weatherRetry,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: isDark
                              ? Colors.blue.shade300
                              : const Color(0xFF0B4C8C),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _footerProvenance(AppLocalizations t) {
    final StringBuffer sb = StringBuffer();
    final String targetLoc;
    if (forecast?.latitude != null && forecast?.longitude != null) {
      final lat = forecast!.latitude!;
      final lon = forecast!.longitude!;
      final latStr = '${lat.abs().toStringAsFixed(2)}°${lat >= 0 ? 'N' : 'S'}';
      final lonStr = '${lon.abs().toStringAsFixed(2)}°${lon >= 0 ? 'E' : 'W'}';
      targetLoc = '$locationLabel ($latStr, $lonStr)';
    } else {
      targetLoc = locationLabel;
    }
    sb.write(t.weatherWindowLocationLabel(targetLoc));
    final fetchedAt = forecast?.fetchedAt;
    if (fetchedAt != null) {
      sb.write(' · ');
      sb.write(t.forecastAsOf(_clock(fetchedAt)));
    }
    return sb.toString();
  }

  static bool _needsRetryAction(FishingWindowAvailability availability) {
    return availability == FishingWindowAvailability.staleRefreshNeeded ||
        availability == FishingWindowAvailability.incompleteData ||
        availability == FishingWindowAvailability.expired ||
        availability == FishingWindowAvailability.noForecast;
  }

  static String _resolveHeadline(
    FishingWindowResult result,
    BuildContext context,
    AppLocalizations t,
  ) {
    if (result.hasPositiveWindow) {
      final String durationStr;
      if (result.isUnderOneHour) {
        durationStr = t.weatherWindowWithinHour;
      } else {
        final int days = result.windowDays ?? 0;
        final int hours = result.windowHours ?? 0;
        if (days > 0 && hours > 0) {
          durationStr = t.weatherWindowDurationDaysHours(days, hours);
        } else if (days > 0) {
          durationStr = t.weatherWindowDurationDaysOnly(days);
        } else {
          durationStr = t.weatherWindowDurationHoursOnly(hours);
        }
      }
      return t.weatherWindowWorsenPrefix(durationStr);
    }

    if (result.currentRisk == RiskLevel.danger ||
        result.availability == FishingWindowAvailability.currentDanger) {
      return t.weatherWindowDangerNow;
    }

    if (result.currentRisk == RiskLevel.caution ||
        result.availability == FishingWindowAvailability.currentCaution) {
      return t.weatherWindowCautionNow;
    }

    return switch (result.availability) {
      FishingWindowAvailability.noWorseningForecast =>
        t.weatherWindowNoWorsening(
            _formatDateTime(context, result.coverageEnd ?? DateTime.now())),
      FishingWindowAvailability.earlierDataMissing => result
                      .deteriorationTime !=
                  null &&
              result.upcomingReason != null
          ? '${t.weatherWindowUpcoming(
              _formatDateTime(context, result.deteriorationTime!),
              result.upcomingReason!.label(t),
            )}${result.upcomingRisk != null ? ' (${result.upcomingRisk!.label(t)})' : ''}'
          : t.weatherWindowEarlierMissing,
      FishingWindowAvailability.missingHourly => result.firstAdverseDay != null
          ? t.weatherWindowDailyAdverse(
              _formatDay(context, result.firstAdverseDay!))
          : t.weatherWindowDailyOnly,
      FishingWindowAvailability.incompleteData => t.weatherWindowIncomplete,
      FishingWindowAvailability.staleRefreshNeeded =>
        t.weatherWindowRefreshNeeded,
      FishingWindowAvailability.expired => t.weatherWindowExpired,
      FishingWindowAvailability.clockSkew => t.weatherWindowClockSkew,
      FishingWindowAvailability.noForecast => t.weatherWindowNoForecast,
      _ => t.weatherWindowNoForecast,
    };
  }

  static String? _resolveSubtitle(
    FishingWindowResult result,
    BuildContext context,
    AppLocalizations t,
  ) {
    if (result.hasPositiveWindow) {
      if (result.deteriorationTime != null && result.upcomingReason != null) {
        final String base = t.weatherWindowUpcoming(
          _formatDateTime(context, result.deteriorationTime!),
          result.upcomingReason!.label(t),
        );
        if (result.upcomingRisk != null) {
          return '$base (${result.upcomingRisk!.label(t)})';
        }
        return base;
      }
      return null;
    }

    if (result.currentRisk == RiskLevel.danger ||
        result.availability == FishingWindowAvailability.currentDanger) {
      return result.currentReason != null
          ? '${result.currentReason!.label(t)}. ${t.weatherWindowDangerSubtitle}'
          : t.weatherWindowDangerSubtitle;
    }

    if (result.currentRisk == RiskLevel.caution ||
        result.availability == FishingWindowAvailability.currentCaution) {
      return result.currentReason != null
          ? '${result.currentReason!.label(t)}. ${t.weatherWindowCautionSubtitle}'
          : t.weatherWindowCautionSubtitle;
    }

    return switch (result.availability) {
      FishingWindowAvailability.noWorseningForecast =>
        t.weatherWindowNoWorseningSubtitle,
      FishingWindowAvailability.earlierDataMissing =>
        t.weatherWindowEarlierMissingSubtitle,
      FishingWindowAvailability.missingHourly =>
        t.weatherWindowEarlierMissingSubtitle,
      FishingWindowAvailability.incompleteData =>
        t.weatherWindowIncompleteSubtitle,
      FishingWindowAvailability.staleRefreshNeeded =>
        t.weatherWindowRefreshNeededSubtitle,
      FishingWindowAvailability.expired => t.weatherWindowExpiredSubtitle,
      FishingWindowAvailability.clockSkew => t.weatherWindowClockSkewSubtitle,
      FishingWindowAvailability.noForecast => t.weatherWindowNoForecastSubtitle,
      _ => null,
    };
  }

  static _SummaryStyle _resolveStyle(
    FishingWindowResult result,
    bool isDark,
    AppLocalizations t,
  ) {
    if (result.currentRisk == RiskLevel.danger ||
        result.availability == FishingWindowAvailability.currentDanger) {
      return _SummaryStyle(
        backgroundColor: isDark
            ? const Color(0xFF7F1D1D).withValues(alpha: 0.35)
            : const Color(0xFFFEF2F2),
        borderColor: isDark
            ? const Color(0xFFDC2626).withValues(alpha: 0.5)
            : const Color(0xFFFECACA),
        iconColor: isDark ? const Color(0xFFF87171) : const Color(0xFFDC2626),
        headlineColor: isDark ? Colors.white : const Color(0xFF991B1B),
        subtitleColor:
            isDark ? const Color(0xFFFCA5A5) : const Color(0xFFB91C1C),
        icon: Icons.error_outline_rounded,
        badgeText: t.riskLevelDanger,
        badgeBackgroundColor:
            isDark ? const Color(0xFF991B1B) : const Color(0xFFFEE2E2),
        badgeTextColor: isDark ? Colors.white : const Color(0xFF991B1B),
      );
    }

    if (result.currentRisk == RiskLevel.caution ||
        result.availability == FishingWindowAvailability.currentCaution) {
      return _SummaryStyle(
        backgroundColor: isDark
            ? const Color(0xFF78350F).withValues(alpha: 0.35)
            : const Color(0xFFFEF3C7),
        borderColor: isDark
            ? const Color(0xFFD97706).withValues(alpha: 0.5)
            : const Color(0xFFFDE68A),
        iconColor: isDark ? const Color(0xFFFBBF24) : const Color(0xFFD97706),
        headlineColor:
            isDark ? const Color(0xFFFDE68A) : const Color(0xFF78350F),
        subtitleColor:
            isDark ? const Color(0xFFFCD34D) : const Color(0xFF92400E),
        icon: Icons.warning_amber_rounded,
        badgeText: t.riskLevelCaution,
        badgeBackgroundColor:
            isDark ? const Color(0xFF92400E) : const Color(0xFFFDE68A),
        badgeTextColor: isDark ? Colors.white : const Color(0xFF78350F),
      );
    }

    if (result.hasPositiveWindow) {
      return _SummaryStyle(
        backgroundColor: isDark
            ? const Color(0xFF064E3B).withValues(alpha: 0.35)
            : const Color(0xFFECFDF5),
        borderColor: isDark
            ? const Color(0xFF059669).withValues(alpha: 0.5)
            : const Color(0xFFA7F3D0),
        iconColor: isDark ? const Color(0xFF34D399) : const Color(0xFF059669),
        headlineColor: isDark ? Colors.white : const Color(0xFF065F46),
        subtitleColor:
            isDark ? const Color(0xFFA7F3D0) : const Color(0xFF047857),
        icon: Icons.schedule_rounded,
        badgeText: t.weatherWindowLowerRisk,
        badgeBackgroundColor:
            isDark ? const Color(0xFF047857) : const Color(0xFFD1FAE5),
        badgeTextColor: isDark ? Colors.white : const Color(0xFF065F46),
      );
    }

    if (result.availability == FishingWindowAvailability.noWorseningForecast) {
      return _SummaryStyle(
        backgroundColor: isDark
            ? const Color(0xFF0C4A6E).withValues(alpha: 0.35)
            : const Color(0xFFF0FDF4),
        borderColor: isDark
            ? const Color(0xFF0284C7).withValues(alpha: 0.4)
            : const Color(0xFFBBF7D0),
        iconColor: isDark ? const Color(0xFF38BDF8) : const Color(0xFF0284C7),
        headlineColor: isDark ? Colors.white : const Color(0xFF0C4A6E),
        subtitleColor:
            isDark ? const Color(0xFFBAE6FD) : const Color(0xFF0369A1),
        icon: Icons.check_circle_outline_rounded,
        badgeText: t.weatherWindowLowerRisk,
        badgeBackgroundColor:
            isDark ? const Color(0xFF0369A1) : const Color(0xFFE0F2FE),
        badgeTextColor: isDark ? Colors.white : const Color(0xFF0C4A6E),
      );
    }

    return _SummaryStyle(
      backgroundColor: isDark
          ? const Color(0xFF334155).withValues(alpha: 0.35)
          : const Color(0xFFF8FAFC),
      borderColor: isDark ? const Color(0xFF475569) : const Color(0xFFE2E8F0),
      iconColor: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
      headlineColor: isDark ? Colors.white : const Color(0xFF1E293B),
      subtitleColor: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
      icon: Icons.info_outline_rounded,
      badgeText: t.riskLevelUnknown,
      badgeBackgroundColor:
          isDark ? const Color(0xFF475569) : const Color(0xFFE2E8F0),
      badgeTextColor: isDark ? Colors.white : const Color(0xFF475569),
    );
  }

  static String _formatDateTime(BuildContext context, DateTime at) {
    try {
      final String locale = Localizations.localeOf(context).languageCode;
      return DateFormat('E, h a', locale).format(at.toLocal());
    } catch (_) {
      return DateFormat('E, h a').format(at.toLocal());
    }
  }

  static String _formatDay(BuildContext context, DateTime at) {
    try {
      final String locale = Localizations.localeOf(context).languageCode;
      return DateFormat('EEEE', locale).format(at.toLocal());
    } catch (_) {
      return DateFormat('EEEE').format(at.toLocal());
    }
  }

  static String _clock(DateTime at) {
    final int hour = at.hour % 12 == 0 ? 12 : at.hour % 12;
    final String minute = at.minute.toString().padLeft(2, '0');
    return '$hour:$minute ${at.hour < 12 ? 'AM' : 'PM'}';
  }
}

class _SummaryStyle {
  const _SummaryStyle({
    required this.backgroundColor,
    required this.borderColor,
    required this.iconColor,
    required this.headlineColor,
    required this.subtitleColor,
    required this.icon,
    required this.badgeText,
    required this.badgeBackgroundColor,
    required this.badgeTextColor,
  });

  final Color backgroundColor;
  final Color borderColor;
  final Color iconColor;
  final Color headlineColor;
  final Color subtitleColor;
  final IconData icon;
  final String badgeText;
  final Color badgeBackgroundColor;
  final Color badgeTextColor;
}

/// The seven-day strip.
class _ForecastStrip extends StatelessWidget {
  const _ForecastStrip({
    required this.days,
    required this.isDark,
    this.age,
  });

  final List<DailyOutlook> days;
  final bool isDark;
  final DateTime? age;

  @override
  Widget build(BuildContext context) {
    final AppLocalizations t = AppLocalizations.of(context);
    final List<DailyOutlook> shown =
        days.take(AqOneConfig.forecastDays).toList(growable: false);

    // If no day in the strip had sea state to work with, say it once at the
    // bottom rather than on every chip.
    final bool anyMissingSeaState =
        shown.any((DailyOutlook d) => d.risk.missingSeaState);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                t.forecastStripTitle,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (age != null) ...<Widget>[
              const SizedBox(width: 8),
              Text(
                t.forecastAsOf(_clock(age!)),
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? Colors.white38 : const Color(0xFF94A3B8),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: <Widget>[
            for (int i = 0; i < shown.length; i++) ...<Widget>[
              if (i > 0) const SizedBox(width: 4),
              Expanded(
                child: _DayChip(
                  day: shown[i],
                  isDark: isDark,
                  isFirst: i == 0,
                  // Beyond day 3 the WMO codes get weak. Fading them stops a
                  // red Friday that turns out sunny from teaching people to
                  // ignore the colours entirely.
                  isOutlook: i >= AqOneConfig.forecastConfidentDays,
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 10),
        Text(
          anyMissingSeaState
              ? t.forecastDisclaimerNoSeaState
              : t.forecastDisclaimer,
          style: TextStyle(
            fontSize: 16,
            height: 1.35,
            color: isDark ? Colors.white38 : const Color(0xFF94A3B8),
          ),
        ),
      ],
    );
  }

  static String _clock(DateTime at) {
    final int hour = at.hour % 12 == 0 ? 12 : at.hour % 12;
    final String minute = at.minute.toString().padLeft(2, '0');
    return '$hour:$minute ${at.hour < 12 ? 'AM' : 'PM'}';
  }
}

class _DayChip extends StatelessWidget {
  const _DayChip({
    required this.day,
    required this.isDark,
    required this.isFirst,
    required this.isOutlook,
  });

  final DailyOutlook day;
  final bool isDark;
  final bool isFirst;
  final bool isOutlook;

  @override
  Widget build(BuildContext context) {
    final AppLocalizations t = AppLocalizations.of(context);
    final RiskLevel level = day.risk.level;
    final Color risk = level.color;
    final double alpha = isOutlook ? 0.55 : 1.0;

    final String label = isFirst ? t.forecastToday : day.shortWeekday;
    final String high = day.tempMax == null ? '–' : '${day.tempMax!.round()}°';
    final String low = day.tempMin == null ? '' : '${day.tempMin!.round()}°';

    final String? reason = day.risk.reasonText(t);

    return Semantics(
      label: '$label, ${day.condition.label(t)}, ${level.label(t)}.'
          '${reason == null ? '' : ' $reason.'}'
          '${isOutlook ? ' ${t.forecastLongRangeSemantics}' : ''}',
      child: Tooltip(
        message: reason ?? level.label(t),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 2),
          decoration: BoxDecoration(
            color: risk.withValues(alpha: isDark ? 0.16 : 0.09),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: risk.withValues(alpha: isFirst ? 0.75 : 0.28),
              width: isFirst ? 1.4 : 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.clip,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: isFirst ? FontWeight.w900 : FontWeight.w700,
                  color: (isDark ? Colors.white : const Color(0xFF0F172A))
                      .withValues(alpha: alpha),
                ),
              ),
              const SizedBox(height: 5),
              Icon(
                day.condition.icon,
                size: 19,
                color: (isDark ? Colors.white : const Color(0xFF334155))
                    .withValues(alpha: alpha),
              ),
              const SizedBox(height: 5),
              Text(
                high,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: (isDark ? Colors.white : const Color(0xFF0F172A))
                      .withValues(alpha: alpha),
                ),
              ),
              if (low.isNotEmpty)
                Text(
                  low,
                  style: TextStyle(
                    fontSize: 12,
                    color: (isDark ? Colors.white54 : const Color(0xFF64748B))
                        .withValues(alpha: alpha),
                  ),
                ),
              const SizedBox(height: 5),
              // Risk is carried by an icon as well as the colour - this gets
              // read in glare, by people who may not distinguish red from
              // green.
              Icon(
                level.icon,
                size: 12,
                color: risk.withValues(alpha: alpha),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
