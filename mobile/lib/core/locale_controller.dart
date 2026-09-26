import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app_diagnostics.dart';
import 'l10n_fallback.dart';

/// Holds the app's active locale and remembers an explicit choice.
///
/// With no stored choice the app runs in [kDefaultLocale]; once the fisher
/// picks a language, that wins, permanently, across restarts.
///
/// Deliberately backed by `shared_preferences` rather than the sqflite
/// database used for identity and the SOS outbox. The language choice is
/// needed to build the very first frame, and blocking startup on opening the
/// database - which `main.dart` already treats as failable - would mean a
/// database problem could leave the app with no language at all.
class LocaleController extends ChangeNotifier {
  LocaleController._(this._override);

  static const String _prefsKey = 'aqone.locale';

  Locale? _override;

  /// The locale to hand to `MaterialApp.locale`.
  Locale get locale => _override ?? kDefaultLocale;

  /// Load the stored choice. Never throws: a preferences failure degrades to
  /// the default language rather than blocking launch.
  static Future<LocaleController> load() async {
    try {
      final SharedPreferences prefs = await SharedPreferences.getInstance()
          .timeout(const Duration(milliseconds: 500));
      final String? stored = prefs.getString(_prefsKey);
      if (stored == null || stored.isEmpty) {
        return LocaleController._(null);
      }
      final Locale candidate = Locale(stored);
      final bool known = kSupportedLocales.any(
        (Locale l) => l.languageCode == candidate.languageCode,
      );
      return LocaleController._(known ? candidate : null);
    } catch (e) {
      AppDiagnostics.log('locale-load', e);
      return LocaleController._(null);
    }
  }

  /// Set an explicit language and remember it.
  Future<void> setLocale(Locale locale) async {
    if (locale.languageCode == _override?.languageCode) {
      return;
    }
    _override = locale;
    notifyListeners();
    try {
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefsKey, locale.languageCode);
    } catch (e) {
      // The in-memory switch already happened, so the user sees the language
      // change; it just will not survive a restart.
      AppDiagnostics.log('locale-save', e);
    }
  }
}
