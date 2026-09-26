import 'dart:convert';

import 'package:aqone/data/welcome_advisory.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/advisory.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:aqone/ui/widgets/advisory_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  group('WelcomeAdvisory', () {
    test('is never marked official', () {
      // The single most important assertion in this file. The Advisories
      // screen is where a fisherman reads instructions that may keep him
      // ashore; a developer note that could pass as an MDRRMO advisory
      // borrows authority the app has no right to.
      expect(WelcomeAdvisory.instance.isOfficial, isFalse);
      expect(WelcomeAdvisory.instance.byline, isNotNull);
    });

    test('sorts below every real advisory', () {
      // Lowest severity, so Home's single-advisory preview shows an MDRRMO
      // notice rather than us whenever one exists.
      for (final AdvisoryPriority p in AdvisoryPriority.values) {
        if (p == AdvisoryPriority.unknown) {
          continue;
        }
        expect(
          WelcomeAdvisory.instance.priority.severity <= p.severity,
          isTrue,
          reason: '${p.name} must not sort below the welcome note',
        );
      }
    });

    test('never expires', () {
      expect(WelcomeAdvisory.instance.expirationDate, isNull);
      expect(WelcomeAdvisory.instance.isActive, isTrue);
    });
  });

  group('Advisory image parsing', () {
    test('reads image_url off the wire', () {
      final Advisory? advisory = Advisory.tryParse(<String, Object?>{
        'title': 'Damaged pier at Jawili',
        'description': 'Do not moor at the eastern posts.',
        'priority': 'warning',
        'image_url': 'https://example.org/pier.jpg',
      });

      expect(advisory!.imageUrl, 'https://example.org/pier.jpg');
      // A backend cannot reference an image inside the APK.
      expect(advisory.imageAsset, isNull);
      expect(advisory.isOfficial, isTrue);
    });

    test('blank or missing image_url stays null, not empty', () {
      final Advisory? blank = Advisory.tryParse(<String, Object?>{
        'title': 'Notice',
        'image_url': '   ',
      });
      final Advisory? absent = Advisory.tryParse(<String, Object?>{
        'title': 'Notice',
      });

      expect(blank!.imageUrl, isNull);
      expect(absent!.imageUrl, isNull);
    });

    test('anything parsed from the wire is official by default', () {
      final Advisory? advisory =
          Advisory.tryParse(<String, Object?>{'title': 'From the MDRRMO'});
      expect(advisory!.isOfficial, isTrue);
    });
  });

  group('AdvisoryCard', () {
    Widget wrap(Advisory advisory) => MaterialApp(
          locale: const Locale('en'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(
            body: SingleChildScrollView(child: AdvisoryCard(advisory: advisory)),
          ),
        );

    testWidgets('an unofficial notice says so on its face', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(wrap(WelcomeAdvisory.instance));

      expect(find.text('APP NOTICE'), findsOneWidget);
      expect(find.textContaining('not an official'), findsOneWidget);
      expect(find.text('From the AqOne team'), findsOneWidget);
      // The byline replaces the municipality, so the card cannot read as
      // though a municipality issued it.
      expect(find.text('New Washington, Aklan'), findsNothing);
    });

    testWidgets('a real advisory carries none of that', (
      WidgetTester tester,
    ) async {
      const Advisory official = Advisory(
        title: 'Not advised to go out',
        description: 'Habagat surge.',
        priority: AdvisoryPriority.warning,
        municipality: 'New Washington',
      );

      await tester.pumpWidget(wrap(official));

      expect(find.text('WARNING'), findsOneWidget);
      expect(find.text('APP NOTICE'), findsNothing);
      expect(find.textContaining('not an official'), findsNothing);
      expect(find.text('New Washington'), findsOneWidget);
    });
  });

  group('VentureFeeds.advisories', () {
    test('a failed fetch with nothing cached is null, never the welcome note standing in for real data', () async {
      final feeds = VentureFeeds(
        backend: BackendClient(
          client: MockClient((request) async => http.Response('', 500)),
        ),
      );

      final result = await feeds.advisories();

      // AdvisoriesPage relies on exactly this null to show "could not load"
      // instead of an empty/placeholder list - see advisories_page.dart.
      expect(result, isNull);
    });

    test('a successful fetch appends the welcome note after real advisories', () async {
      final feeds = VentureFeeds(
        backend: BackendClient(
          client: MockClient((request) async => http.Response(
                jsonEncode(<String, Object?>{
                  'advisories': <Object?>[
                    <String, Object?>{
                      'title': 'Habagat surge',
                      'description': 'Small craft warning in effect.',
                      'priority': 'warning',
                    },
                  ],
                }),
                200,
              )),
        ),
      );

      final result = await feeds.advisories();

      expect(result, isNotNull);
      expect(result!.last, same(WelcomeAdvisory.instance));
      expect(result.any((Advisory a) => a.title == 'Habagat surge'), isTrue);
    });
  });
}
