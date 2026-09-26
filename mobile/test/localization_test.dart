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
              Text(MaterialLocalizations.of(context).cancelButtonLabel),
            ],
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    // Our own strings are Aklanon...
    expect(find.text('Mga Abiso'), findsOneWidget);
    // ...while Flutter's built-in chrome falls back to Tagalog, the closest
    // language Flutter ships (docs/22 §4.2, plan 70 D3).
    final filChrome =
        await GlobalMaterialLocalizations.delegate.load(const Locale('fil'));
    final enChrome =
        await GlobalMaterialLocalizations.delegate.load(const Locale('en'));
    expect(filChrome.cancelButtonLabel, isNot(enChrome.cancelButtonLabel));
    expect(find.text(filChrome.cancelButtonLabel), findsOneWidget);
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

    test('no hard-coded user-facing text anywhere in lib/ui', () {
      // Plan 70 AKL-03. Brand names and the Tagalog slogan are the only
      // literals a fisher may see in every language.
      const allowed = <String>{
        'AqOne',
        'SOS',
        r'Gabay sa Bawat Alon,\nKonektado sa Bawat Layon',
      };
      final literal = RegExp(
        r"""(?:\bText\(|\b(?:title|label|labelText|hintText|helperText|tooltip|message|semanticLabel|semanticsLabel|headline|detail|body)\s*:)\s*(?:const\s+Text\(\s*)?'([^'$]*[A-Za-z][^']*)'""",
      );
      final offenders = <String>[];
      for (final file in Directory('lib/ui').listSync(recursive: true)) {
        if (file is! File || !file.path.endsWith('.dart')) continue;
        final source = file.readAsStringSync();
        for (final match in literal.allMatches(source)) {
          if (!allowed.contains(match.group(1))) {
            offenders.add('${file.path}: ${match.group(1)}');
          }
        }
      }
      expect(offenders, isEmpty);
    });

    test('every English key has an Aklanon value that is not English', () {
      // Plan 70 AKL-05. Identical values are allowed only where the word is
      // the same in both languages (brand names, units, the compass, D5).
      const sameInBoth = <String>{
        'compassNorth',
        'compassEast',
        'compassSouth',
        'compassWest',
        'chatCharacterLimitLabel',
        'buoyTitle',
        'deliveryMetaBuoy',
      };
      final en = jsonDecode(File('lib/l10n/app_en.arb').readAsStringSync())
          as Map<String, dynamic>;
      final akl = jsonDecode(File('lib/l10n/app_akl.arb').readAsStringSync())
          as Map<String, dynamic>;
      final keys = en.keys.where((k) => !k.startsWith('@'));
      expect(
        keys.where((k) => !akl.containsKey(k)).toList(),
        isEmpty,
        reason: 'keys missing from app_akl.arb',
      );
      expect(
        keys
            .where((k) => !sameInBoth.contains(k) && akl[k] == en[k])
            .toList(),
        isEmpty,
        reason: 'Aklanon values still in English',
      );
    });
  });
}
