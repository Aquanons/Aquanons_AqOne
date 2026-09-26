import 'dart:convert';
import 'dart:io';

import 'package:aqone/core/locale_controller.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/main.dart';
import 'package:aqone/ui/onboarding_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Plan 70, AKL-01 and AKL-02: the handset is Aklanon out of the box, and the
/// phone's own language is never consulted.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfiNoIsolate;

  final Map<String, dynamic> akl =
      jsonDecode(File('lib/l10n/app_akl.arb').readAsStringSync())
          as Map<String, dynamic>;

  test('no stored choice means Aklanon', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final controller = await LocaleController.load();
    expect(controller.locale, const Locale('akl'));
  });

  test('an explicit pick wins and survives a restart', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await (await LocaleController.load()).setLocale(const Locale('en'));
    final reloaded = await LocaleController.load();
    expect(reloaded.locale, const Locale('en'));
  });

  test('the SOS notification text is Aklanon by default', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final controller = await LocaleController.load();
    expect(
      lookupAppLocalizations(controller.locale).sosPendingNotificationTitle,
      akl['sosPendingNotificationTitle'],
    );
  });

  Future<Locale> launchLocale(WidgetTester tester) async {
    tester.platformDispatcher.localesTestValue = const <Locale>[
      Locale('en', 'US'),
    ];
    addTearDown(tester.platformDispatcher.clearLocalesTestValue);
    await tester.pumpWidget(const AqOneApp());
    await tester.pump(const Duration(seconds: 5));
    final Locale locale =
        Localizations.localeOf(tester.element(find.byType(OnboardingPage)));
    await tester.pumpWidget(const SizedBox());
    return locale;
  }

  testWidgets('a fresh install on an English phone opens in Aklanon',
      (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    expect(await launchLocale(tester), const Locale('akl'));
  });

  testWidgets('a fisher who picked English gets English on the next launch',
      (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'aqone.locale': 'en',
    });
    expect(await launchLocale(tester), const Locale('en'));
  });
}
