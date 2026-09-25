import 'dart:async';

import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import '../../core/tokens.dart';
import '../../models/delivery_state.dart';
import '../../models/fisher_sos_situation.dart';
import '../../models/sos_record.dart';

class DeliveryStateTile extends StatelessWidget {
  const DeliveryStateTile({super.key, required this.record});

  final SosRecord record;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);
    final situation = FisherSosSituation.of(record);
    final accent = situation.color;
    final resolved = record.isResolved;

    // Coordinates are numbers, not copy - they are formatted, never
    // translated. Only the "no fix" case has words in it.
    final position = record.hasFix
        ? '${record.lat!.toStringAsFixed(5)}, ${record.lon!.toStringAsFixed(5)}'
        : t.deliveryNoGpsFix;

    return Container(
      margin: const EdgeInsets.only(bottom: AqSpace.md),
      padding: const EdgeInsets.all(AqSpace.base),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: BorderRadius.circular(AqRadius.card),
        border: Border.all(color: palette.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(situation.icon, size: 20, color: accent),
              const SizedBox(width: AqSpace.sm),
              Text(
                situation.title(t),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: palette.primaryText,
                ),
              ),
              const Spacer(),
              Text(
                _formatTime(record.createdAt),
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: palette.dimText,
                ),
              ),
            ],
          ),
          const SizedBox(height: AqSpace.sm),
          Text(
            situation.description(t),
            style: TextStyle(
              fontSize: 14,
              height: 1.5,
              color: palette.secondaryText,
            ),
          ),
          if (resolved)
            Padding(
              padding: const EdgeInsets.only(top: AqSpace.xs),
              child: Text(
                t.resolvedStillEndangered,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AqColors.warning,
                ),
              ),
            ),
          const SizedBox(height: AqSpace.md),
          _MetaLine(
            label: t.deliveryMetaPosition,
            value: position,
            monospace: true,
          ),
          if (record.seq != null)
            _MetaLine(
              label: t.deliveryMetaBuoy,
              // Identifiers, not prose. Left untranslated on purpose: this is
              // what a responder reads back over the radio.
              value: 'buoy ${record.buoyId} · seq ${record.seq}',
              monospace: true,
            ),
          if (record.note != null)
            _MetaLine(label: t.deliveryMetaNote, value: record.note!),
          if (record.ackedBy != null)
            _MetaLine(label: t.deliveryMetaResponder, value: record.ackedBy!),
          if (record.resolvedAt != null)
            _MetaLine(
              label: t.resolvedTitle,
              value: _formatTime(record.resolvedTime!),
            )
          else if (record.etaAt != null)
            _EtaCountdownLine(
              label: t.deliveryMetaEta,
              eta: record.etaTime!,
              overdueLabel: t.responderDelayedStillOnWay,
            ),
          if (record.state == DeliveryState.saved && record.lastError != null)
            _MetaLine(
              label: t.deliveryMetaLastAttempt,
              value: record.lastError!,
              tone: AqColors.warning,
            ),
        ],
      ),
    );
  }

  static String _formatTime(DateTime value) {
    final h = value.hour.toString().padLeft(2, '0');
    final m = value.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

class _MetaLine extends StatelessWidget {
  const _MetaLine({
    required this.label,
    required this.value,
    this.monospace = false,
    this.tone,
  });

  final String label;
  final String value;
  final bool monospace;
  final Color? tone;

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: AqSpace.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            // 84 in the English-only version. Tagalog and Aklanon labels run
            // longer ("Huling subok", "Huling pagtinguha") and wrapped.
            width: 96,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: palette.dimText,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                fontFamily: monospace ? 'monospace' : null,
                color: tone ?? palette.secondaryText,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// The MDRRMO's promised rescue arrival time, counting down live.
///
/// A thumbnail of the responder dialog (responder_eta_dialog.dart): the
/// promise must not vanish when the dialog closes and the fisher switches
/// back to Home - the tile carries it on until the time passes. Never renders
/// a negative number; once overdue it says the responder is delayed but still
/// coming, matching the dialog.
class _EtaCountdownLine extends StatefulWidget {
  const _EtaCountdownLine({
    required this.label,
    required this.eta,
    required this.overdueLabel,
  });

  final String label;
  final DateTime eta;
  final String overdueLabel;

  @override
  State<_EtaCountdownLine> createState() => _EtaCountdownLineState();
}

class _EtaCountdownLineState extends State<_EtaCountdownLine> {
  Timer? _tick;

  @override
  void initState() {
    super.initState();
    _tick = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  String _countdown() {
    final remaining = widget.eta.difference(DateTime.now());
    if (remaining.isNegative) {
      return widget.overdueLabel;
    }
    final minutes = remaining.inMinutes;
    final seconds = remaining.inSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final overdue = widget.eta.isBefore(DateTime.now());
    final tone = overdue ? AqColors.warning : AqColors.success;
    return Padding(
      padding: const EdgeInsets.only(bottom: AqSpace.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 96,
            child: Text(
              widget.label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: palette.dimText,
              ),
            ),
          ),
          Expanded(
            child: Text(
              _countdown(),
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                fontFamily: 'monospace',
                color: tone,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
