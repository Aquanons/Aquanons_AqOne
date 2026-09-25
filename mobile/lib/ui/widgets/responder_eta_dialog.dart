import 'dart:async';

import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import '../../models/sos_record.dart';
import '../../services/sos_service.dart';

/// The dispatcher's answer to a distress call, shown wherever the fisher is.
///
/// This is the moment the whole product exists for: the difference between
/// "someone might have seen my SOS" and "help is 20 minutes away". It is
/// deliberately a barrier-dismissible-false dialog rather than a snackbar,
/// because a fisher glancing at a phone in bad weather must not be able to
/// miss it by looking away for three seconds.
class ResponderEtaDialog extends StatefulWidget {
  const ResponderEtaDialog({super.key, required this.record, required this.sos});

  final SosRecord record;
  final SosService sos;

  @override
  State<ResponderEtaDialog> createState() => _ResponderEtaDialogState();
}

class _ResponderEtaDialogState extends State<ResponderEtaDialog> {
  Timer? _tick;

  // Reply flow state. Local-first: SosService.replyToSos() already saves the
  // fisher's tap immediately regardless of connectivity, so this only tracks
  // what to show, never whether the tap "worked" in some other sense.
  bool _confirmingSafeNow = false;
  bool _sendingReply = false;
  int? _sentReply;
  bool _replyQueued = false;

  @override
  void initState() {
    super.initState();
    // Live countdown. One second is not wasteful here - this dialog is on
    // screen for a few seconds at a time.
    _tick = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  /// Never renders a negative number. Once the promised time passes it says
  /// the responder is delayed but still coming, because a countdown expiring
  /// into silence reads as "nobody is coming".
  String _countdown(AppLocalizations t, DateTime eta) {
    final remaining = eta.difference(DateTime.now());
    if (remaining.isNegative) {
      return t.responderDelayedStillOnWay;
    }
    final minutes = remaining.inMinutes;
    final seconds = remaining.inSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  /// The fixed one-byte status vocabulary in docs/13_RESPONDER_LOOP.md,
  /// localized. Not an enum extension like DeliveryStateL10n because this
  /// code arrives as a bare int over the wire (backend/app/api/sos.py's
  /// RESPONDER_STATUS_LABELS) with no Dart type to hang the pattern on.
  String? _responderStatusText(AppLocalizations t, int? status) {
    switch (status) {
      case 1:
        return t.responderStatusReceived;
      case 2:
        return t.responderStatusDispatched;
      case 3:
        return t.responderStatusCoastGuard;
      case 4:
        return t.responderStatusNearestVessel;
      case 5:
        return t.responderStatusDelayed;
      default:
        return null;
    }
  }

  Future<void> _sendReply(int reply) async {
    if (_sendingReply) return;
    setState(() {
      _sendingReply = true;
      _confirmingSafeNow = false;
    });
    final sentDirectly = await widget.sos.replyToSos(widget.record.localId, reply);
    if (!mounted) return;
    setState(() {
      _sendingReply = false;
      _sentReply = reply;
      _replyQueued = !sentDirectly;
    });
  }

  /// The fisher's one-tap answer, or a confirmation step / queued notice in
  /// its place. Kept out of `build()` only for readability - all the state it
  /// reads and writes belongs to this same State object.
  Widget _buildReplySection(BuildContext context, AppLocalizations t, bool isDark) {
    final mutedColor = isDark ? Colors.white60 : const Color(0xFF64748B);

    if (_sentReply != null) {
      final sentText = _sentReply == 2
          ? (_replyQueued
              ? t.standDownPendingDescription
              : t.responderReplySentSafeNow)
          : t.responderReplySentStillInDanger;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(
                _sentReply == 2 ? Icons.check_circle_rounded : Icons.info_rounded,
                size: 18,
                color: _sentReply == 2 ? const Color(0xFF16A34A) : const Color(0xFFF59E0B),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  sentText,
                  style: TextStyle(fontSize: 13, color: isDark ? Colors.white : const Color(0xFF1F2937)),
                ),
              ),
            ],
          ),
          if (_replyQueued) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              t.responderReplyPending,
              style: TextStyle(fontSize: 12, height: 1.3, color: mutedColor),
            ),
          ],
        ],
      );
    }

    if (_confirmingSafeNow) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            t.responderReplyConfirmBody,
            style: TextStyle(fontSize: 12.5, height: 1.35, color: mutedColor),
          ),
          const SizedBox(height: 10),
          Row(
            children: <Widget>[
              Expanded(
                child: TextButton(
                  onPressed: _sendingReply ? null : () => setState(() => _confirmingSafeNow = false),
                  child: Text(t.actionCancel),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton(
                  onPressed: _sendingReply ? null : () => _sendReply(2),
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
                  child: Text(t.responderReplyConfirmConfirm),
                ),
              ),
            ],
          ),
        ],
      );
    }

    return Row(
      children: <Widget>[
        Expanded(
          child: OutlinedButton(
            onPressed: _sendingReply ? null : () => _sendReply(1),
            child: Text(t.responderReplyStillInDanger),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: FilledButton(
            onPressed: _sendingReply ? null : () => setState(() => _confirmingSafeNow = true),
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
            child: Text(t.responderReplySafeNow),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final eta = widget.record.etaTime;
    final overdue = eta != null && eta.isBefore(DateTime.now());
    final accent = overdue ? const Color(0xFFF59E0B) : const Color(0xFF16A34A);
    final statusText = _responderStatusText(t, widget.record.responderStatus);

    return AlertDialog(
      backgroundColor: isDark ? const Color(0xFF111827) : Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: <Widget>[
          Icon(Icons.verified_rounded, color: accent, size: 26),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Help is coming',
              style: TextStyle(
                color: accent,
                fontWeight: FontWeight.w900,
                fontSize: 20,
              ),
            ),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            statusText ?? 'MDRRMO has received your SOS.',
            style: TextStyle(
              fontSize: 15,
              color: isDark ? Colors.white : const Color(0xFF1F2937),
            ),
          ),
          if (eta != null) ...<Widget>[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: accent),
              ),
              child: Column(
                children: <Widget>[
                  Text(
                    overdue ? t.etaArrivalOverdue : t.etaArrivingIn,
                    style: TextStyle(
                      fontSize: 11,
                      letterSpacing: 1,
                      fontWeight: FontWeight.w800,
                      color: accent,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _countdown(t, eta),
                    style: TextStyle(
                      fontSize: overdue ? 16 : 34,
                      fontWeight: FontWeight.w900,
                      color: accent,
                      fontFeatures: const <FontFeature>[
                        FontFeature.tabularFigures(),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ] else ...<Widget>[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: accent),
              ),
              child: Text(
                t.sosNoEtaYet,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: accent,
                ),
              ),
            ),
          ],
          if (widget.record.responderNote != null &&
              widget.record.responderNote!.trim().isNotEmpty) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              widget.record.responderNote!,
              style: TextStyle(
                fontSize: 13,
                height: 1.35,
                color: isDark ? Colors.white70 : const Color(0xFF475569),
              ),
            ),
          ],
          const SizedBox(height: 16),
          _buildReplySection(context, t, isDark),
          const SizedBox(height: 14),
          Text(
            t.stayWithBoat,
            style: TextStyle(
              fontSize: 12,
              height: 1.35,
              color: isDark ? Colors.white60 : const Color(0xFF64748B),
            ),
          ),
        ],
      ),
      actions: <Widget>[
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          style: FilledButton.styleFrom(backgroundColor: accent),
          child: Text(t.understoodButton),
        ),
      ],
    );
  }
}
