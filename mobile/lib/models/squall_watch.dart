/// Squall nowcast from the backend's AI (`GET /api/public/squall`).
///
/// The alarm condition is decided server-side, by the model's own threshold.
/// This client never re-derives it from raw probabilities: a cutoff invented on
/// the handset could disagree with the dashboard about whether a squall is
/// happening, and the two must never tell different stories about the same
/// weather.
///
/// Wire shape (docs/05_PUBLIC_API.md "Squall nowcast"):
/// ```json
/// {
///   "source": "live",
///   "calibration": "synthetic",
///   "observed_at": "2026-08-16T02:00:00Z",
///   "generated_at": "2026-08-16T02:03:00Z",
///   "data_age_seconds": 180,
///   "status_reason": null,
///   "level": "clear",
///   "return_now": false,
///   "detections": [],
///   "threshold": 0.55,
///   "triggered_buoys": [],
///   "lead_minutes": null
/// }
/// ```
library;

enum SquallLevel {
  /// No detections. Nothing to show.
  clear,

  /// Detections below the model's threshold. Visible, but must not alarm.
  watch,

  /// At or above the threshold. This is the RETURN NOW condition.
  returnNow,

  /// Telemetry is missing, stale, invalid, or an insufficiently distributed
  /// array - or the model could not be evaluated, or the fetch failed.
  /// Deliberately distinct from `clear`: an alarm that cannot be evaluated
  /// must never be rendered as "all clear".
  unknown,
}

class SquallWatch {
  const SquallWatch({
    required this.level,
    required this.returnNow,
    this.leadMinutes,
    this.triggeredBuoys = const <String>[],
    this.observedAt,
    this.onsetAt,
    this.generatedAt,
    this.dataAgeSeconds,
    this.calibration,
    this.source,
    this.statusReason,
  });

  final SquallLevel level;
  final bool returnNow;

  /// Soonest forecast arrival across affected buoys, in minutes.
  final int? leadMinutes;

  final List<String> triggeredBuoys;

  /// The newest real pressure reading the backend has ever seen, whether or
  /// not the array currently qualifies for a live nowcast.
  final DateTime? observedAt;

  /// Time when propagation began across the array (ISO string).
  final String? onsetAt;

  /// Server clock time this response was computed.
  final DateTime? generatedAt;

  final double? dataAgeSeconds;

  /// "synthetic" while the models are calibrated on simulated data. Surfaced
  /// in the UI rather than hidden, so the app never implies more certainty
  /// than the model has earned.
  final String? calibration;

  /// "live" or "synthetic" - which table this response was computed from.
  final String? source;

  /// Why [level] is [SquallLevel.unknown] - missing/stale/insufficient
  /// telemetry, or the model being unavailable. `null` whenever level is
  /// clear/watch/returnNow, since a successful evaluation needs no
  /// explanation. Not localized and not shown verbatim to the fisher (it is
  /// backend-internal wording, e.g. "only 2 of 3 required buoys...") - only
  /// used to decide [shouldDisplay] and to derive a neutral, localized notice.
  final String? statusReason;

  /// The state to show when the backend cannot be reached at all.
  static const SquallWatch unavailable = SquallWatch(
    level: SquallLevel.unknown,
    returnNow: false,
  );

  bool get shouldDisplay =>
      level == SquallLevel.watch ||
      level == SquallLevel.returnNow ||
      statusReason != null;

  static SquallLevel _levelFrom(String? raw) {
    switch (raw) {
      case 'return_now':
        return SquallLevel.returnNow;
      case 'watch':
        return SquallLevel.watch;
      case 'clear':
        return SquallLevel.clear;
      default:
        return SquallLevel.unknown;
    }
  }

  static SquallWatch? tryParse(Object? decoded) {
    if (decoded is! Map<String, dynamic>) {
      return null;
    }

    final level = _levelFrom(decoded['level'] as String?);

    // Trust the server's boolean, but never render returnNow without the
    // level agreeing. If the two disagree the payload is malformed, and the
    // safe reading of a malformed alarm is "unknown", not "fire it".
    final serverReturnNow = decoded['return_now'] == true;
    final returnNow = serverReturnNow && level == SquallLevel.returnNow;

    final lead = decoded['lead_minutes'];
    final buoys = decoded['triggered_buoys'];
    final observedAtRaw = decoded['observed_at'];
    final onsetAtRaw = decoded['onset_at'];
    final generatedAtRaw = decoded['generated_at'];
    final dataAge = decoded['data_age_seconds'];

    return SquallWatch(
      level: level,
      returnNow: returnNow,
      leadMinutes: lead is num ? lead.round() : null,
      triggeredBuoys: buoys is List
          ? buoys.whereType<String>().toList(growable: false)
          : const <String>[],
      observedAt:
          observedAtRaw is String ? DateTime.tryParse(observedAtRaw) : null,
      onsetAt: onsetAtRaw is String ? onsetAtRaw : null,
      generatedAt:
          generatedAtRaw is String ? DateTime.tryParse(generatedAtRaw) : null,
      dataAgeSeconds: dataAge is num ? dataAge.toDouble() : null,
      calibration: decoded['calibration'] as String?,
      source: decoded['source'] as String?,
      statusReason: decoded['status_reason'] as String?,
    );
  }

  /// Identity for deciding whether this is the *same* squall the fisher has
  /// already acknowledged, or a new one that should alarm again.
  ///
  /// Keyed on the affected buoys plus onset_at. Without onset_at, falls back
  /// to observed_at floored to a 3-hour UTC bucket so a later squall alarms
  /// again after a missed clear.
  String get identity {
    final buoysPart = triggeredBuoys.isEmpty
        ? 'squall'
        : (List<String>.from(triggeredBuoys)..sort()).join(',');
    if (onsetAt != null && onsetAt!.isNotEmpty) {
      return '$buoysPart:$onsetAt';
    }
    if (observedAt != null) {
      final utc = observedAt!.toUtc();
      final flooredHour = utc.hour - (utc.hour % 3);
      final bucket = DateTime.utc(utc.year, utc.month, utc.day, flooredHour);
      return '$buoysPart:${bucket.toIso8601String()}';
    }
    return buoysPart;
  }
}
