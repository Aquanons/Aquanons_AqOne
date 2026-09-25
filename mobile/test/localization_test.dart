import 'dart:convert';
import 'dart:io';

import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/core/validators.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/license_type.dart';
import 'package:aqone/models/sea_condition.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _app(Locale locale, Widget child) => MaterialApp(
      locale: locale,
      supportedLocales: kSupportedLocales,
      localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        ...kFallbackDelegates,
      ],
      home: child,
    );

void main() {
  group('locale resolution', () {
    test('matches on language code, ignoring region', () {
      expect(
        resolveLocale(const Locale('fil', 'PH'), kSupportedLocales),
        const Locale('fil'),
      );
      expect(
        resolveLocale(const Locale('en', 'US'), kSupportedLocales),
        const Locale('en'),
      );
    });

    // Some Android builds and older webviews still report the deprecated
    // `tl` for Tagalog. A phone set to Tagalog must get a Tagalog app.
    test('maps the deprecated tl code onto fil', () {
      expect(
        resolveLocale(const Locale('tl'), kSupportedLocales),
        const Locale('fil'),
      );
    });

    test('falls back to English for anything unsupported', () {
      expect(
        resolveLocale(const Locale('ja'), kSupportedLocales),
        const Locale('en'),
      );
      expect(resolveLocale(null, kSupportedLocales), const Locale('en'));
    });
  });

  // The regression this whole fallback-delegate arrangement exists to
  // prevent: `akl` has no CLDR data in flutter_localizations, so without the
  // fallbacks the first Material widget to ask for MaterialLocalizations
  // throws. Rendering a DatePicker forces that lookup.
  testWidgets('Aklanon renders Material widgets without throwing',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      _app(
        const Locale('akl'),
        Builder(
          builder: (BuildContext context) => Column(
            children: <Widget>[
              Text(AppLocalizations.of(context).navAdvisories),
              Text(MaterialLocalizations.of(context).okButtonLabel),
            ],
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    // Our own strings are Aklanon...
    expect(find.text('Mga Abiso'), findsOneWidget);
    // ...while Flutter's built-in chrome falls back to English. Documented
    // trade-off, see §4.2 of docs/22_LOCALIZATION_PLAN.md.
    expect(find.text('OK'), findsOneWidget);
  });

  testWidgets('sea status headline is translated in every locale',
      (WidgetTester tester) async {
    final seen = <String>{};

    for (final code in <String>['en', 'fil', 'akl']) {
      late String headline;
      await tester.pumpWidget(
        _app(
          Locale(code),
          Builder(
            builder: (BuildContext context) {
              headline =
                  SeaStatus.notAdvised.headline(AppLocalizations.of(context));
              return Text(headline);
            },
          ),
        ),
      );
      expect(tester.takeException(), isNull);
      seen.add(headline);
    }

    expect(
      seen.length,
      3,
      reason: 'the strongest safety warning is identical across locales, '
          'which means at least one is falling back to English',
    );
  });

  testWidgets('MDRRMO free text is passed through, never translated',
      (WidgetTester tester) async {
    const reason = 'Habagat surge, 2m waves off Jawili';
    const condition =
        SeaCondition(status: SeaStatus.notAdvised, reason: reason);

    await tester.pumpWidget(
      _app(
        const Locale('fil'),
        Builder(
          builder: (BuildContext context) =>
              Text(condition.subtitle(AppLocalizations.of(context))),
        ),
      ),
    );

    expect(find.text(reason), findsOneWidget);
  });

  testWidgets('registration flow translates in every locale',
      (WidgetTester tester) async {
    final headings = <String>{};
    final fieldLabels = <String>{};
    final registrationLabels = <String>{};
    final validationMessages = <String>{};

    for (final code in <String>['en', 'fil', 'akl']) {
      await tester.pumpWidget(
        _app(
          Locale(code),
          Builder(
            builder: (BuildContext context) {
              final t = AppLocalizations.of(context);
              headings.add(t.onboardingRegisterBoat);
              fieldLabels.add(t.fieldFullName);
              registrationLabels.add(LicenseType.none.label(t));
              validationMessages.add(Validators.skipperName('', t)!);
              return Text(t.onboardingRegisterBoat);
            },
          ),
        ),
      );
      expect(tester.takeException(), isNull);
    }

    expect(headings.length, 3);
    expect(fieldLabels.length, 3);
    expect(registrationLabels.length, 3);
    expect(validationMessages.length, 3);
  });

  testWidgets('profile and settings labels translate in every locale',
      (WidgetTester tester) async {
    final boatLabels = <String>{};
    final settingsLabels = <String>{};
    final darkModeLabels = <String>{};
    final logoutLabels = <String>{};

    for (final code in <String>['en', 'fil', 'akl']) {
      await tester.pumpWidget(
        _app(
          Locale(code),
          Builder(
            builder: (BuildContext context) {
              final t = AppLocalizations.of(context);
              boatLabels.add(t.profileBoatName);
              settingsLabels.add(t.settingsTitle);
              darkModeLabels.add(t.darkMode);
              logoutLabels.add(t.logoutAction);
              return Text(t.profileBoatName);
            },
          ),
        ),
      );
      expect(tester.takeException(), isNull);
    }

    expect(boatLabels.length, 3);
    expect(settingsLabels.length, 2);
    expect(darkModeLabels.length, 2);
    expect(logoutLabels.length, 3);
  });

  group('Phase M6 localization', () {
    test('the new keys exist in all three ARB files', () {
      final en = jsonDecode(File('lib/l10n/app_en.arb').readAsStringSync())
          as Map<String, dynamic>;
      final fil = jsonDecode(File('lib/l10n/app_fil.arb').readAsStringSync())
          as Map<String, dynamic>;
      final akl = jsonDecode(File('lib/l10n/app_akl.arb').readAsStringSync())
          as Map<String, dynamic>;

      const requiredKeys = <String>[
        'settingsSilentSos',
        'settingsSilentSosDescription',
        'sosStoodDown',
        'sosNoneSentYet',
      ];

      for (final key in requiredKeys) {
        expect(en.containsKey(key), isTrue,
            reason: 'app_en.arb missing $key');
        expect(fil.containsKey(key), isTrue,
            reason: 'app_fil.arb missing $key');
        expect(akl.containsKey(key), isTrue,
            reason: 'app_akl.arb missing $key');
      }
    });

    test('no bare Text literal remains in venture_page.dart or home_page.dart',
        () {
      final ventureContent =
          File('lib/ui/venture_page.dart').readAsStringSync();
      final homeContent = File('lib/ui/home_page.dart').readAsStringSync();

      final bareTextRegex = RegExp(r"Text\(\s*'");

      expect(bareTextRegex.hasMatch(ventureContent), isFalse,
          reason: 'venture_page.dart contains bare Text(\' literals');
      expect(bareTextRegex.hasMatch(homeContent), isFalse,
          reason: 'home_page.dart contains bare Text(\' literals');
    });
  });
}
