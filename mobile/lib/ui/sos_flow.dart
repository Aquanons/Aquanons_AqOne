import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config.dart';
import '../l10n/app_localizations.dart';
import '../models/fisher_sos_situation.dart';
import '../models/sos_record.dart';
import '../services/sos_alarm.dart';
import '../services/sos_service.dart';

const Color _brandPrimary = Color(0xFF0F69C9);
const Color _canvasDark = Color(0xFF0F172A);
const Color _danger = Color(0xFFDC2626);
Future<void> handleSosTap({
  required BuildContext context,
  required SosService service,
  required SosAlarm alarm,
  required Duration countdown,
  required bool isSending,
  required ValueChanged<bool> setSending,
  required Future<void> Function(SosRecord record) onRaised,
}) async {
  if (isSending) return;

  setSending(true);
  final preferences = await SharedPreferences.getInstance();
  if (!context.mounted) return;
  final silent = preferences.getBool('silent_sos') ?? false;
  if (!silent) unawaited(alarm.start());

  final result = await showGeneralDialog<bool>(
    context: context,
    barrierDismissible: false,
    barrierColor: Colors.black87,
    transitionDuration: const Duration(milliseconds: 150),
    pageBuilder: (context, _, __) => SosCountdownScreen(duration: countdown),
  );
  if (!context.mounted) return;

  try {
    if (result != true) {
      unawaited(alarm.stop());
      setSending(false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content:
                Text(AppLocalizations.of(context).sosCancelledNothingSent)),
      );
      return;
    }

    final record = await service.raiseSos();
    if (!context.mounted) return;
    await onRaised(record);
    if (!context.mounted) return;
    final current = ValueNotifier<SosRecord>(record);
    var active = true;
    final changes = service.changes.listen((_) async {
      final updated = await service.outbox.byLocalId(record.localId);
      if (active && updated != null) current.value = updated;
    });
    try {
      await showModalBottomSheet<void>(
        context: context,
        isDismissible: false,
        enableDrag: false,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => EmergencyDetailsSheet(
          record: current,
          onSubmitNote: (note) async {
            try {
              await service.amendNote(record.localId, note);
            } catch (_) {}
            final updated = await service.outbox.byLocalId(record.localId);
            if (updated != null) current.value = updated;
          },
          onStandDown: () async {
            await service.standDown(record.localId);
            if (!context.mounted) return;
            final t = AppLocalizations.of(context);
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                duration: const Duration(minutes: 2),
                content: Text(t.sosStoodDown),
                action: SnackBarAction(
                  label: t.sosStandDownUndo,
                  onPressed: () => service.replyToSos(record.localId, 1),
                ),
              ),
            );
          },
        ),
      );
    } finally {
      active = false;
      await changes.cancel();
      current.dispose();
    }
  } on StateError {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(AppLocalizations.of(context).sosSetupBoatRequired)),
      );
    }
  } finally {
    unawaited(alarm.stop());
    if (context.mounted) setSending(false);
  }
}

/// Preset emergency types offered on the post-dispatch follow-up. Picking
/// one amends the note already on file with the MDRRMO; it never delays the
/// SOS itself, which has already gone out by the time this is shown.
enum _EmergencyType {
  engine('Engine failure', Icons.settings_suggest_rounded),
  capsizing('Capsizing / taking on water', Icons.waves_rounded),
  medical('Medical emergency', Icons.medical_services_rounded),
  other('Other', Icons.edit_note_rounded);

  const _EmergencyType(this.label, this.icon);

  final String label;
  final IconData icon;
}

/// Full-screen "sending SOS in N…" countdown with a slide-to-cancel bar.
///
/// Deliberately not a plain [AlertDialog]: this has to be impossible to
/// dismiss by accident (no tap-outside, no back-gesture - see [PopScope]
/// below) while still being trivially easy to cancel on purpose via the
/// slide, which is a large, deliberate, hard-to-trigger-by-accident gesture.
class SosCountdownScreen extends StatefulWidget {
  const SosCountdownScreen({super.key, required this.duration});

  final Duration duration;

  @override
  State<SosCountdownScreen> createState() => _SosCountdownScreenState();
}

class _SosCountdownScreenState extends State<SosCountdownScreen> {
  static const Duration _tick = Duration(milliseconds: 100);

  late Duration _remaining = widget.duration;
  Timer? _timer;
  bool _resolved = false;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(_tick, (_) {
      final next = _remaining - _tick;
      if (next <= Duration.zero) {
        _finish(true);
        return;
      }
      setState(() => _remaining = next);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _finish(bool dispatch) {
    if (_resolved) {
      return;
    }
    _resolved = true;
    _timer?.cancel();
    final route = ModalRoute.of(context)!;
    final navigator = Navigator.of(context);
    if (route.isCurrent) {
      navigator.pop(dispatch);
    } else {
      navigator.removeRoute(route, dispatch);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final fraction = 1 -
        (_remaining.inMilliseconds / widget.duration.inMilliseconds)
            .clamp(0.0, 1.0);
    final secondsLeft = (_remaining.inMilliseconds / 1000).ceil().clamp(1, 99);
    final secondsDisplay = '$secondsLeft';

    return PopScope(
      // No back-gesture, no back-button dismissal - the only way out of this
      // screen is the slide-to-cancel control below, or letting it run out.
      canPop: false,
      child: Scaffold(
        backgroundColor: const Color(0xFF7A0E0E),
        body: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) => SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 28,
                    vertical: 16,
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: <Widget>[
                      const Icon(
                        Icons.warning_rounded,
                        color: Colors.white,
                        size: 48,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        t.sosSendingTitle,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        t.sosSendingSubtitle,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        width: 110,
                        height: 110,
                        child: Stack(
                          alignment: Alignment.center,
                          children: <Widget>[
                            SizedBox(
                              width: 110,
                              height: 110,
                              child: CircularProgressIndicator(
                                value: fraction,
                                strokeWidth: 7,
                                backgroundColor: Colors.white24,
                                valueColor: const AlwaysStoppedAnimation<Color>(
                                  Colors.white,
                                ),
                              ),
                            ),
                            Text(
                              secondsDisplay,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 42,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                      ),
                      _SlideToAction(
                        label: t.sosSlideToCancel,
                        icon: Icons.close_rounded,
                        accentColor: Colors.white,
                        thumbIconColor: const Color(0xFF7A0E0E),
                        onConfirmed: () => _finish(false),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        t.sosAutoSendNotice,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white54,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Shown right after dispatch. Lets the fisher attach what's actually wrong
/// (updating the note already on file at the MDRRMO) or stand the alert
/// down if it went out by mistake - both remain available at once, they are
/// not mutually exclusive steps.
@visibleForTesting
class EmergencyDetailsSheet extends StatefulWidget {
  const EmergencyDetailsSheet({
    super.key,
    required this.record,
    required this.onSubmitNote,
    required this.onStandDown,
  });

  final ValueListenable<SosRecord> record;
  final Future<void> Function(String note) onSubmitNote;
  final Future<void> Function() onStandDown;

  @override
  State<EmergencyDetailsSheet> createState() => _EmergencyDetailsSheetState();
}

class _EmergencyDetailsSheetState extends State<EmergencyDetailsSheet> {
  _EmergencyType? _selected;
  final TextEditingController _custom = TextEditingController();
  bool _submitting = false;
  bool _standingDown = false;

  @override
  void dispose() {
    _custom.dispose();
    super.dispose();
  }

  String? get _noteToSend {
    final type = _selected;
    if (type == null) {
      return null;
    }
    if (type == _EmergencyType.other) {
      final text = _custom.text.trim();
      return text.isEmpty ? null : text;
    }
    return type.label;
  }

  Future<void> _submit() async {
    final note = _noteToSend;
    setState(() => _submitting = true);
    if (note != null) {
      await widget.onSubmitNote(note);
    }
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  Future<void> _standDown() async {
    final t = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(t.sosStandDownConfirmTitle),
        content: Text(t.sosStandDownConfirmBody),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(t.actionCancel),
          ),
          FilledButton(
            key: const Key('confirm_stand_down'),
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(backgroundColor: _danger),
            child: Text(t.standDownTitle),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) {
      return;
    }
    setState(() => _standingDown = true);
    await widget.onStandDown();
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final AppLocalizations t = AppLocalizations.of(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? _canvasDark : Colors.white;
    final fg = isDark ? Colors.white : const Color(0xFF0F172A);
    final dim = isDark ? Colors.white60 : const Color(0xFF64748B);

    return PopScope(
      // Closing this sheet is only ever a deliberate choice - "send update",
      // "stand down", or explicitly dismissing without either - never an
      // accidental back-swipe, since the alarm is still ringing underneath
      // it and a stray dismissal must not leave the fisher unsure whether
      // anything was recorded.
      canPop: false,
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: SingleChildScrollView(
          child: Container(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(24),
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 14),
                    decoration: BoxDecoration(
                      color: dim.withValues(alpha: 0.4),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                ValueListenableBuilder<SosRecord>(
                  valueListenable: widget.record,
                  builder: (context, record, _) {
                    final situation = FisherSosSituation.of(record);
                    return Row(
                      children: <Widget>[
                        Icon(situation.icon, color: situation.color, size: 22),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                situation.title(t),
                                style: TextStyle(
                                  color: fg,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 16,
                                ),
                              ),
                              Text(record.boat,
                                  style: TextStyle(color: dim, fontSize: 13)),
                            ],
                          ),
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 4),
                Text(
                  t.sosSituationNotePrompt,
                  style: TextStyle(color: dim, fontSize: 16, height: 1.35),
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: <Widget>[
                    for (final type in _EmergencyType.values)
                      ChoiceChip(
                        label: Text(type.label),
                        avatar: Icon(type.icon, size: 16),
                        selected: _selected == type,
                        onSelected: _submitting || _standingDown
                            ? null
                            : (value) =>
                                setState(() => _selected = value ? type : null),
                      ),
                  ],
                ),
                if (_selected == _EmergencyType.other) ...<Widget>[
                  const SizedBox(height: 10),
                  TextField(
                    controller: _custom,
                    maxLength: AqOneConfig.maxNoteBytes,
                    textCapitalization: TextCapitalization.sentences,
                    enabled: !_submitting && !_standingDown,
                    decoration: InputDecoration(
                      hintText: t.sosDescribeWrong,
                      counterText: '',
                      isDense: true,
                    ),
                  ),
                ],
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: (_submitting || _standingDown) ? null : _submit,
                    style: FilledButton.styleFrom(
                      backgroundColor: _brandPrimary,
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: Text(
                      _selected == null ? t.actionClose : t.sosSendUpdate,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Divider(color: dim.withValues(alpha: 0.25)),
                const SizedBox(height: 8),
                Text(
                  t.sosSentByMistake,
                  style: TextStyle(
                    color: fg,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 8),
                _SlideToAction(
                  label:
                      _standingDown ? t.standDownTitle : t.sosSlideToStandDown,
                  icon: Icons.undo_rounded,
                  accentColor: _danger,
                  onConfirmed: _submitting || _standingDown ? null : _standDown,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// A large, deliberate "slide to confirm" control - used both to cancel the
/// countdown and to stand down an already-sent SOS. A tap can happen by
/// accident; dragging a thumb the width of a track cannot, which is exactly
/// the asymmetry wanted for actions this consequential.
class _SlideToAction extends StatefulWidget {
  const _SlideToAction({
    required this.label,
    required this.icon,
    required this.accentColor,
    required this.onConfirmed,
    this.thumbIconColor = Colors.white,
  });

  final String label;
  final IconData icon;
  final Color accentColor;
  final Color thumbIconColor;

  /// Null disables the control (shown mid-action, e.g. while a stand-down
  /// request is already in flight).
  final VoidCallback? onConfirmed;

  @override
  State<_SlideToAction> createState() => _SlideToActionState();
}

class _SlideToActionState extends State<_SlideToAction> {
  static const double _thumbSize = 48;

  double _fraction = 0;
  bool _dragging = false;
  bool _confirmed = false;

  void _onDragUpdate(DragUpdateDetails details, double maxDrag) {
    if (_confirmed || widget.onConfirmed == null || maxDrag <= 0) {
      return;
    }
    setState(() {
      _dragging = true;
      _fraction =
          (_fraction * maxDrag + details.delta.dx).clamp(0, maxDrag) / maxDrag;
    });
  }

  void _onDragEnd(DragEndDetails details) {
    if (_confirmed || widget.onConfirmed == null) {
      return;
    }
    if (_fraction > 0.8) {
      setState(() {
        _confirmed = true;
        _fraction = 1;
        _dragging = false;
      });
      widget.onConfirmed!();
      if (mounted) {
        setState(() {
          _confirmed = false;
          _fraction = 0;
        });
      }
    } else {
      setState(() {
        _dragging = false;
        _fraction = 0;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onConfirmed != null;
    final accent = enabled ? widget.accentColor : Colors.grey;
    return LayoutBuilder(
      builder: (context, constraints) {
        final trackWidth = constraints.maxWidth;
        final maxDrag = (trackWidth - _thumbSize).clamp(0, trackWidth);
        final thumbLeft = _fraction * maxDrag;
        return Container(
          height: _thumbSize + 8,
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: accent.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular((_thumbSize + 8) / 2),
            border: Border.all(color: accent.withValues(alpha: 0.45)),
          ),
          child: Stack(
            alignment: Alignment.center,
            children: <Widget>[
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: _thumbSize),
                  child: Text(
                    widget.label,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: accent,
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
              AnimatedPositioned(
                duration: _dragging
                    ? Duration.zero
                    : const Duration(milliseconds: 220),
                curve: Curves.easeOut,
                left: thumbLeft,
                child: GestureDetector(
                  onHorizontalDragUpdate: (d) =>
                      _onDragUpdate(d, maxDrag.toDouble()),
                  onHorizontalDragEnd: _onDragEnd,
                  child: Container(
                    width: _thumbSize,
                    height: _thumbSize,
                    decoration: BoxDecoration(
                      color: accent,
                      shape: BoxShape.circle,
                      boxShadow: const <BoxShadow>[
                        BoxShadow(color: Colors.black26, blurRadius: 6),
                      ],
                    ),
                    child: Icon(
                      widget.icon,
                      color: widget.thumbIconColor,
                      size: 22,
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
