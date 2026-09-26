import 'package:flutter/material.dart';

import '../../data/map_snapshot_store.dart';
import '../../l10n/app_localizations.dart';
import 'age_text.dart';

/// Tells the fisherman the map he is looking at is not live.
///
/// §3.4 of the system design requires data age to be visible wherever a model
/// or feed drives a decision. That matters more here than anywhere else in
/// the app: a cached map looks exactly like a live one, and the whole point
/// of showing it offshore is that someone will act on it.
///
/// Renders nothing when the newest snapshot is fresh, so it stays out of the
/// way on a normal trip within coverage.
class OfflineMapBanner extends StatelessWidget {
  const OfflineMapBanner({
    super.key,
    required this.ages,
    required this.isDark,
  });

  /// Feed key to last successful fetch, from [MapSnapshotStore.ages].
  final Map<String, DateTime> ages;

  final bool isDark;

  /// Below this the map is effectively live and the banner would be noise.
  static const Duration _quiet = Duration(minutes: 2);

  /// Past this the map is old enough that the warning should be loud.
  static const Duration _severe = Duration(hours: 3);

  @override
  Widget build(BuildContext context) {
    if (ages.isEmpty) {
      return const SizedBox.shrink();
    }
    final t = AppLocalizations.of(context);

    // The oldest feed sets the tone. Saying "updated 2 minutes ago" because
    // one feed refreshed, while the hazard layer is three hours stale, is the
    // reassuring-but-wrong version of this widget.
    DateTime oldest = ages.values.first;
    for (final DateTime at in ages.values) {
      if (at.isBefore(oldest)) {
        oldest = at;
      }
    }
    final Duration age = DateTime.now().difference(oldest);
    if (age < _quiet) {
      return const SizedBox.shrink();
    }

    final bool severe = age >= _severe;
    final Color fg = severe ? const Color(0xFF7F1D1D) : const Color(0xFF8A5A12);
    final Color bg = severe ? const Color(0xFFFEE2E2) : const Color(0xFFFFF4E0);

    final bool hazardsMissing =
        !ages.containsKey(MapSnapshotStore.feedWaveAlerts) &&
            !ages.containsKey(MapSnapshotStore.feedCapsizeAlerts);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bg.withValues(alpha: isDark ? 0.92 : 0.96),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: fg.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: <Widget>[
          Icon(
            severe ? Icons.cloud_off_rounded : Icons.history_rounded,
            size: 16,
            color: fg,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  t.offlineMapShowing(ageAgo(t, age)),
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: fg,
                  ),
                ),
                Text(
                  hazardsMissing
                      // Not a footnote. The absence of a hazard layer looks
                      // identical to "no hazards", and those mean opposite
                      // things to someone deciding whether to go out.
                      ? t.offlineMapHazardsMissing
                      : t.offlineMapStale,
                  style: TextStyle(fontSize: 16, height: 1.3, color: fg),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
