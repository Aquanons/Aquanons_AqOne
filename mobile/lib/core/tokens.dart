import 'package:flutter/material.dart';

class AqColors {
  const AqColors._();

  static const Color brandDeep = Color(0xFF0958A6);
  static const Color brandPrimary = Color(0xFF0F69C9);
  static const Color skyAccent = Color(0xFF38BDF8);

  static const Color appNavy = Color(0xFF0F172A);
  static const Color slateSurface = Color(0xFF1E293B);
  static const Color raisedSlate = Color(0xFF334155);
  static const Color slateText = Color(0xFF64748B);
  static const Color mutedSlate = Color(0xFF94A3B8);
  static const Color lightSecondaryText = Color(0xFF475569);
  static const Color lightDimText = Color(0xFF5B6574);
  static const Color paleSlate = Color(0xFFCBD5E1);
  static const Color lightBorder = Color(0xFFCFE8F9);
  static const Color lightBlueSurface = Color(0xFFE8F8FF);
  static const Color lightCanvas = Color(0xFFF4F8FA);
  static const Color darkPrimaryText = Color(0xFFF0F4F8);

  static const Color success = Color(0xFF16A34A);
  static const Color warning = Color(0xFFD97706);
  static const Color danger = Color(0xFFE74C3C);
  static const Color info = Color(0xFF2E86AB);
  static const Color connectivity = Color(0xFF0891B2);
  static const Color disabled = Color(0xFF94A3B8);
}

class AqRadius {
  const AqRadius._();

  static const double compact = 6;
  static const double small = 8;
  static const double button = 10;
  static const double standard = 12;
  static const double card = 16;
  static const double large = 20;
  static const double pill = 999;
}

class AqSpace {
  const AqSpace._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double base = 16;
  static const double lg = 20;
  static const double screen = 24;
  static const double xl = 32;
}

class AqPalette {
  const AqPalette({
    required this.canvas,
    required this.surface,
    required this.surfaceAlt,
    required this.primaryText,
    required this.secondaryText,
    required this.dimText,
    required this.border,
    required this.active,
  });

  final Color canvas;
  final Color surface;
  final Color surfaceAlt;
  final Color primaryText;
  final Color secondaryText;
  final Color dimText;
  final Color border;
  final Color active;

  static AqPalette of(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return isDark ? dark : light;
  }

  static const AqPalette light = AqPalette(
    canvas: AqColors.lightCanvas,
    surface: Colors.white,
    surfaceAlt: AqColors.lightBlueSurface,
    primaryText: AqColors.slateSurface,
    secondaryText: AqColors.lightSecondaryText,
    dimText: AqColors.lightDimText,
    border: AqColors.lightBorder,
    active: AqColors.brandPrimary,
  );

  static const AqPalette dark = AqPalette(
    canvas: AqColors.appNavy,
    surface: AqColors.slateSurface,
    surfaceAlt: AqColors.raisedSlate,
    primaryText: AqColors.darkPrimaryText,
    secondaryText: AqColors.mutedSlate,
    dimText: AqColors.mutedSlate,
    border: Color(0x1AFFFFFF),
    active: AqColors.skyAccent,
  );
}

ThemeData buildAqTheme(Brightness brightness) {
  final palette =
      brightness == Brightness.dark ? AqPalette.dark : AqPalette.light;
  return ThemeData(
    brightness: brightness,
    scaffoldBackgroundColor: palette.canvas,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AqColors.brandPrimary,
      brightness: brightness,
    ),
    useMaterial3: true,
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AqColors.brandPrimary,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AqRadius.button),
        ),
      ),
    ),
  );
}
