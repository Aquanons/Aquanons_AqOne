import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

/// The official go/no-go call, set by the MDRRMO.
///
/// This is the authoritative signal in the app. The weather heuristic in
/// Venture is a rough client-side check; this is a human decision by the
/// people responsible for the response, and it outranks anything the handset
/// works out for itself.
///
/// Display text lives in [SeaStatusL10n] rather than on the enum - const enum
/// fields cannot see a BuildContext. See §4.1 of
/// `docs/22_LOCALIZATION_PLAN.md`.
enum SeaStatus {
  safe('safe', Color(0xFF16A34A), Icons.check_circle_rounded),
  caution('caution', Color(0xFFD97706), Icons.warning_amber_rounded),
  notAdvised('not_advised', Color(0xFFDC2626), Icons.dangerous_rounded),
  unknown('unknown', Color(0xFF6B7280), Icons.help_outline_rounded);

  const SeaStatus(this.wire, this.color, this.icon);

  final String wire;
  final Color color;

  /// Paired with [color] so the state is never conveyed by colour alone -
  /// important both for accessibility and for reading a phone in glare on
  /// the water.
  final IconData icon;

  static SeaStatus fromWire(String? value) {
    final normalized = value?.trim().toLowerCase();
    final aliases = <String, SeaStatus>{
      'safe to go out': SeaStatus.safe,
      'caution — check advisories': SeaStatus.caution,
      'caution - check advisories': SeaStatus.caution,
      'not advised': SeaStatus.notAdvised,
    };
    final alias = normalized == null ? null : aliases[normalized];
    if (alias != null) return alias;
    for (final status in SeaStatus.values) {
      if (status.wire == normalized) {
        return status;
      }
    }
    return SeaStatus.unknown;
  }
}

extension SeaStatusL10n on SeaStatus {
  /// The go/no-go headline. Safety critical in every language - see the
  /// review rules in `lib/l10n/README.md`.
  String headline(AppLocalizations t) => switch (this) {
        SeaStatus.safe => t.seaStatusSafeHeadline,
        SeaStatus.caution => t.seaStatusCautionHeadline,
        SeaStatus.notAdvised => t.seaStatusNotAdvisedHeadline,
        SeaStatus.unknown => t.seaStatusUnknownHeadline,
      };

  /// Used only when the MDRRMO supplied no reason of their own.
  String defaultSubtitle(AppLocalizations t) => switch (this) {
        SeaStatus.safe => t.seaStatusSafeSubtitle,
        SeaStatus.caution => t.seaStatusCautionSubtitle,
        SeaStatus.notAdvised => t.seaStatusNotAdvisedSubtitle,
        SeaStatus.unknown => t.seaStatusUnknownSubtitle,
      };
}

class SeaCondition {
  const SeaCondition({
    required this.status,
    this.reason,
    this.setByName,
    this.createdAt,
    this.fetchedAt,
    this.source,
    this.buoyCount = 0,
    this.currentSpeedMps,
    this.currentDirectionDeg,
    this.observedAt,
  });

  final SeaStatus status;

  /// Free text from the MDRRMO. Replaces the default subtitle when present.
  final String? reason;

  /// Who set it. Only returned on the authenticated endpoint.
  final String? setByName;

  final DateTime? createdAt;

  /// When this handset last successfully read the value.
  final DateTime? fetchedAt;

  /// Measurement context supplied by the backend. This is deliberately
  /// separate from [status]: a buoy observation informs the decision but does
  /// not replace the MDRRMO's official go/no-go call.
  final String? source;
  final int buoyCount;
  final double? currentSpeedMps;
  final double? currentDirectionDeg;
  final DateTime? observedAt;

  /// Free text from the MDRRMO when they gave one, otherwise the translated
  /// default for the status.
  ///
  /// [reason] is passed through verbatim and is deliberately NOT translated:
  /// a human at the MDRRMO wrote it about today's specific conditions, and
  /// machine-mangling an official safety notice would be worse than leaving
  /// it in whatever language they typed it in.
  String subtitle(AppLocalizations t) {
    final trimmed = reason?.trim();
    return trimmed == null || trimmed.isEmpty
        ? status.defaultSubtitle(t)
        : trimmed;
  }

  static SeaCondition? tryParse(Object? decoded, {DateTime? fetchedAt}) {
    if (decoded is! Map) {
      return null;
    }
    final current = decoded['current'];
    final source = current is Map ? current : decoded;
    final status = source['status'];
    final reason = source['reason'];
    final setBy = source['set_by_label'] ?? source['set_by_name'];
    final createdAt = source['created_at'];
    final telemetry = source['buoy_telemetry'];
    final telemetryMap = telemetry is Map ? telemetry : const <Object?, Object?>{};
    return SeaCondition(
      status: SeaStatus.fromWire(status is String ? status : null),
      reason: reason is String && reason.trim().isNotEmpty
          ? reason.trim()
          : null,
      setByName:
          setBy is String && setBy.trim().isNotEmpty ? setBy.trim() : null,
      createdAt:
          createdAt is String ? DateTime.tryParse(createdAt)?.toUtc() : null,
      fetchedAt: fetchedAt ?? DateTime.now(),
      source: telemetryMap['source']?.toString(),
      buoyCount: telemetryMap['buoy_count'] is num
          ? (telemetryMap['buoy_count'] as num).toInt()
          : 0,
      currentSpeedMps: telemetryMap['current_speed_mps'] is num
          ? (telemetryMap['current_speed_mps'] as num).toDouble()
          : null,
      currentDirectionDeg: telemetryMap['current_direction_deg'] is num
          ? (telemetryMap['current_direction_deg'] as num).toDouble()
          : null,
      observedAt: telemetryMap['observed_at'] is String
          ? DateTime.tryParse(telemetryMap['observed_at'] as String)?.toUtc()
          : null,
    );
  }

  SeaCondition copyWith({DateTime? fetchedAt}) => SeaCondition(
        status: status,
        reason: reason,
        setByName: setByName,
        createdAt: createdAt,
        fetchedAt: fetchedAt ?? this.fetchedAt,
        source: source,
        buoyCount: buoyCount,
        currentSpeedMps: currentSpeedMps,
        currentDirectionDeg: currentDirectionDeg,
        observedAt: observedAt,
      );

  /// Whether this reading has gone stale.
  ///
  /// The source project only showed a stale marker when `set_by_name` was
  /// present, and the public endpoint omits that field - so guests could sit
  /// looking at hours-old data with nothing to indicate it. Staleness here
  /// depends only on the clock, so it always shows.
  bool isStale({Duration threshold = const Duration(minutes: 2)}) {
    final at = fetchedAt;
    if (at == null) {
      return true;
    }
    return DateTime.now().difference(at) > threshold;
  }
}
