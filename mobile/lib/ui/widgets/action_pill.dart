import 'package:flutter/material.dart';

const double kActionPillWidth = 176;
const double kActionPillHeight = 50;

class ActionPill extends StatelessWidget {
  const ActionPill({
    super.key,
    required this.icon,
    required this.label,
    required this.color,
    required this.isDark,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color color;
  final bool isDark;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    final display = enabled
        ? color
        : (isDark ? const Color(0xFF334155) : const Color(0xFF94A3B8));
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
        child: Material(
          color: display,
          borderRadius: BorderRadius.circular(kActionPillHeight / 2),
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(kActionPillHeight / 2),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  Icon(icon, size: 20, color: Colors.white),
                  const SizedBox(width: 8),
                  Text(
                    label,
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
      ),
    );
  }
}
