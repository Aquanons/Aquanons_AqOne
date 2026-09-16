import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../models/squall_watch.dart';

/// Full-screen RETURN NOW alert.
///
/// The inline banner is not enough for this one state. A banner assumes the
/// fisherman is looking at the top of Home; at sea he is looking at the map,
/// or at nothing. A squall with twenty minutes of lead time is the single
/// most time-critical thing this app can tell anyone, so it takes the whole
/// screen from wherever he is.
///
/// Only [SquallLevel.returnNow] gets this treatment. A watch stays a banner -
/// escalating every detection to a full-screen takeover is how people learn
/// to dismiss the screen without reading it.
///
/// Dismissal is one deliberate button. No back gesture, no tap-outside, no
/// swipe: a warning dismissed by a wet thumb on a rolling deck is a warning
/// that never happened.
class SquallAlertPage extends StatelessWidget {
  const SquallAlertPage({
    super.key,
    required this.watch,
    required this.onAcknowledge,
  });

  final SquallWatch watch;

  /// Stops the alarm and closes this screen. The banner stays behind it until
  /// the backend reports the squall has passed - acknowledging means "I have
  /// seen this", never "this is over".
  final VoidCallback onAcknowledge;

  static const Color _danger = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final int? lead = watch.leadMinutes;

    return PopScope(
      // The whole point. This screen cannot be backed out of.
      canPop: false,
      child: Scaffold(
        backgroundColor: _danger,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                const Spacer(),
                const Icon(
                  Icons.warning_amber_rounded,
                  color: Colors.white,
                  size: 96,
                ),
                const SizedBox(height: 20),
                const Text(
                  'RETURN NOW',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 44,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 1.5,
                    height: 1.05,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  lead == null
                      ? 'A dangerous squall is forecast for your area.'
                      : 'A dangerous squall is forecast to arrive in about '
                          '$lead minutes.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    height: 1.4,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Head for shore.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (watch.triggeredBuoys.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 18),
                  Text(
                    'Reported by ${watch.triggeredBuoys.join(', ')}',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontSize: 13,
                    ),
                  ),
                ],
                if (watch.calibration == 'synthetic') ...<Widget>[
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    // Carried through from the model rather than hidden. The
                    // detector is calibrated on simulated data, and a warning
                    // that overstates its own certainty is how a safety tool
                    // loses the trust it needs.
                    child: Text(
                      AppLocalizations.of(context).squallModelDisclaimer,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  ),
                ],
                const Spacer(),
                FilledButton(
                  onPressed: onAcknowledge,
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: _danger,
                    padding: const EdgeInsets.symmetric(vertical: 20),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: Text(
                    AppLocalizations.of(context).squallAckButton,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  AppLocalizations.of(context).squallWarningStays,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.85),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
