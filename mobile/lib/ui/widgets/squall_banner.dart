import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import '../../models/squall_watch.dart';
import 'age_text.dart';

/// Squall nowcast card, shown directly above the sea-condition banner.
///
/// Renders nothing at all when there is no squall. An always-present "no squall
/// detected" card trains people to ignore this part of the screen, which is the
/// last thing you want from the one element that has to be noticed in a hurry.
///
/// The RETURN NOW state is deliberately loud, and it keeps showing after the
/// fisher acknowledges the alarm - acknowledging silences the sound, it does not
/// mean the weather has passed.
class SquallBanner extends StatelessWidget {
  const SquallBanner({
    super.key,
    required this.watch,
    this.acknowledged = false,
    this.onAcknowledge,
  });

  final SquallWatch watch;
  final bool acknowledged;
  final VoidCallback? onAcknowledge;

  @override
  Widget build(BuildContext context) {
    if (!watch.shouldDisplay) {
      return const SizedBox.shrink();
    }
    final t = AppLocalizations.of(context);

    // Missing/stale/insufficient telemetry that never reached watch/returnNow
    // gets a quiet, neutral notice - not the amber/red alarm styling below,
    // and never hidden outright. A fisher should be able to tell "the model
    // has nothing current to say" from "everything is fine", and from an
    // alarm.
    final bool isAlarming = watch.level == SquallLevel.watch ||
        watch.level == SquallLevel.returnNow;
    if (!isAlarming && watch.statusReason != null) {
      return _buildStaleNotice(context);
    }

    final bool isReturnNow = watch.level == SquallLevel.returnNow;
    final Color accent =
        isReturnNow ? const Color(0xFFDC2626) : const Color(0xFFF59E0B);
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: isDark ? 0.18 : 0.10),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accent, width: isReturnNow ? 2 : 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(
                isReturnNow
                    ? Icons.warning_amber_rounded
                    : Icons.thunderstorm_rounded,
                color: accent,
                size: isReturnNow ? 26 : 22,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  isReturnNow ? t.squallReturnNow : t.squallWatchTitle,
                  style: TextStyle(
                    color: accent,
                    fontWeight: FontWeight.w900,
                    fontSize: isReturnNow ? 20 : 16,
                    letterSpacing: isReturnNow ? 0.5 : 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            _body(t, isReturnNow),
            style: TextStyle(
              fontSize: 16,
              height: 1.35,
              color: isDark ? Colors.white : const Color(0xFF1F2937),
              fontWeight: isReturnNow ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
          if (watch.triggeredBuoys.isNotEmpty) ...<Widget>[
            const SizedBox(height: 4),
            Text(
              t.squallDetectedAt(watch.triggeredBuoys.join(', ')),
              style: TextStyle(
                fontSize: 12,
                color: isDark ? Colors.white70 : const Color(0xFF475569),
              ),
            ),
          ],
          const SizedBox(height: 6),
          // The calibration state is shown, not hidden. While the model is
          // trained on simulated data the app says so, even here.
          Text(
            watch.calibration == 'synthetic'
                ? t.squallNowcastSynthetic
                : t.squallNowcast,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? Colors.white60 : const Color(0xFF64748B),
            ),
          ),
          if (isReturnNow && acknowledged) ...<Widget>[
            const SizedBox(height: 8),
            Row(
              children: <Widget>[
                Icon(Icons.check_circle, size: 15, color: accent),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    t.squallAcknowledged,
                    style: TextStyle(fontSize: 16, color: accent),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStaleNotice(BuildContext context) {
    final AppLocalizations t = AppLocalizations.of(context);
    final bool isDark = Theme.of(context).brightness == Brightness.dark;
    const Color neutral = Color(0xFF6B7280);
    final DateTime? observedAt = watch.observedAt;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: neutral.withValues(alpha: isDark ? 0.16 : 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: neutral, width: 1),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(Icons.history_toggle_off_rounded,
              color: neutral, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  t.squallStaleTitle,
                  style: TextStyle(
                    color: isDark ? Colors.white : const Color(0xFF334155),
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  observedAt != null
                      ? t.squallStaleBodyWithAge(
                          shortAge(t, DateTime.now().difference(observedAt)),
                        )
                      : t.squallStaleBodyNoAge,
                  style: TextStyle(
                    fontSize: 16,
                    height: 1.3,
                    color: isDark ? Colors.white70 : const Color(0xFF64748B),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _body(AppLocalizations t, bool isReturnNow) {
    final int? lead = watch.leadMinutes;
    final bool hasLead = lead != null && lead > 0;
    if (isReturnNow) {
      return hasLead
          ? t.squallBannerReturnLead(lead)
          : t.squallBannerReturnSoon;
    }
    return hasLead ? t.squallBannerWatchLead(lead) : t.squallBannerWatchNearby;
  }
}
