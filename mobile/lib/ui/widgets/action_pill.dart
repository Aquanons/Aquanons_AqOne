import 'dart:async';
import 'package:flutter/material.dart';

const double kActionPillWidth = 176;
const double kActionPillHeight = 50;

class ActionPill extends StatefulWidget {
  const ActionPill({
    super.key,
    required this.icon,
    required this.label,
    required this.color,
    required this.isDark,
    required this.onTap,
    this.onHold,
  });

  final IconData icon;
  final String label;
  final Color color;
  final bool isDark;
  final VoidCallback? onTap;
  final VoidCallback? onHold;

  @override
  State<ActionPill> createState() => _ActionPillState();
}

class _ActionPillState extends State<ActionPill> {
  Timer? _holdTimer;
  bool _held = false;

  void _onTapDown(TapDownDetails details) {
    if (widget.onTap == null) return;
    _held = false;
    _holdTimer?.cancel();
    if (widget.onHold != null) {
      _holdTimer = Timer(const Duration(seconds: 3), () {
        _held = true;
        widget.onHold?.call();
      });
    }
  }

  void _onTapUp(TapUpDetails details) {
    _holdTimer?.cancel();
    if (widget.onTap == null) return;
    if (!_held) {
      widget.onTap?.call();
    }
    _held = false;
  }

  void _onTapCancel() {
    _holdTimer?.cancel();
    _held = false;
  }

  @override
  void dispose() {
    _holdTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onTap != null;
    final display = enabled
        ? widget.color
        : (widget.isDark ? const Color(0xFF334155) : const Color(0xFF94A3B8));
    return SizedBox(
      width: kActionPillWidth,
      height: kActionPillHeight,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(kActionPillHeight / 2),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: display.withValues(alpha: 0.4),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: GestureDetector(
          onTapDown: enabled ? _onTapDown : null,
          onTapUp: enabled ? _onTapUp : null,
          onTapCancel: enabled ? _onTapCancel : null,
          behavior: HitTestBehavior.opaque,
          child: Container(
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: display,
              borderRadius: BorderRadius.circular(kActionPillHeight / 2),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Icon(widget.icon, size: 20, color: Colors.white),
                const SizedBox(width: 8),
                Text(
                  widget.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    color: Colors.white,
                    letterSpacing: 0.3,
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
