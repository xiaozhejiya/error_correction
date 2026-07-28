import 'package:flutter/material.dart';

class AppTheme {
  static const Color background = Color(0xFF080910);
  static const Color backgroundAlt = Color(0xFF242426);
  static const Color lightBackground = Color(0xFFF7F5FF);
  static const Color lightBackgroundAlt = Color(0xFFFFFFFF);
  static const Color primary = Color(0xFF8A73F5);
  static const Color primaryLight = Color(0xFFA796FF);
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFF9A98A8);
  static const Color lightTextPrimary = Color(0xFF101323);
  static const Color lightTextSecondary = Color(0xFF5F6373);
  static const Color border = Color(0x33FFFFFF);
  static const Color lightBorder = Color(0x1FA39CBC);

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: primaryLight,
        surface: backgroundAlt,
      ),
      fontFamily: 'Roboto',
    );
  }

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: lightBackground,
      colorScheme: const ColorScheme.light(
        primary: primary,
        secondary: primaryLight,
        surface: lightBackgroundAlt,
        onSurface: lightTextPrimary,
      ),
      fontFamily: 'Roboto',
    );
  }
}

class AppThemePalette {
  const AppThemePalette({required this.isLight});

  factory AppThemePalette.of(BuildContext context) {
    return AppThemePalette(
      isLight: Theme.of(context).brightness == Brightness.light,
    );
  }

  final bool isLight;

  Color get pageBg => isLight ? AppTheme.lightBackground : AppTheme.background;
  Color get cardBg => isLight
      ? AppTheme.lightBackgroundAlt.withOpacity(0.78)
      : AppTheme.background.withOpacity(0.5);
  Color get panelBg => cardBg;
  Color get panel => panelBg;
  Color get panelBorder => isLight
      ? AppTheme.lightBorder.withOpacity(0.15)
      : AppTheme.border.withOpacity(0.08);
  Color get border => panelBorder;
  Color get panelBorderStrong =>
      isLight ? Colors.black.withOpacity(0.18) : const Color(0xFF2B2C34);
  Color get primary => AppTheme.primary;
  Color get primaryLight => AppTheme.primaryLight;
  Color get primaryDeep => AppTheme.primary.withOpacity(0.84);
  Color get textMain =>
      isLight ? AppTheme.lightTextPrimary : AppTheme.textPrimary;
  Color get textSub =>
      isLight ? AppTheme.lightTextSecondary : AppTheme.textSecondary;
  Color get chip =>
      isLight ? const Color(0xFFECE9FF) : Colors.white.withOpacity(0.08);
  Color get subtleOverlay =>
      isLight ? Colors.black.withOpacity(0.08) : Colors.white.withOpacity(0.08);
  Color get controlInactiveBg =>
      isLight ? Colors.black.withOpacity(0.16) : Colors.white.withOpacity(0.16);
  Color get progressTrack =>
      isLight ? Colors.black.withOpacity(0.08) : const Color(0x20FFFFFF);
  Color get menuBg => isLight ? Colors.white : const Color(0xFF202022);
  Color get selectedBg =>
      isLight ? primary.withOpacity(0.08) : Colors.white.withOpacity(0.08);
  Color get badgeBg =>
      isLight ? Colors.black.withOpacity(0.05) : Colors.white.withOpacity(0.08);
  Color get divider =>
      isLight ? Colors.black.withOpacity(0.06) : Colors.white.withOpacity(0.08);
  Color get imageBg =>
      isLight ? const Color(0xFFF5F6FA) : const Color(0xFF202126);
  Color get emptyPaper =>
      isLight ? Colors.white : Colors.white.withOpacity(0.92);
  Color get emptyPaperLine =>
      isLight ? Colors.black.withOpacity(0.08) : Colors.black.withOpacity(0.10);
  Color get compareLine => isLight ? AppTheme.primary : const Color(0xFF8C78FF);
  Color get errorText => const Color(0xFFFF6B6B);
}
