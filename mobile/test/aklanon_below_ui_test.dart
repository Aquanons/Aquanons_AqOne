import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/welcome_advisory.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/advisory.dart';
import 'package:aqone/models/daily_outlook.dart';
import 'package:aqone/models/delivery_failure.dart';
import 'package:aqone/models/hazard_alert.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/safety_score.dart';
import 'package:aqone/ui/widgets/advisory_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

/// Plan 70 AKL-04: models and services hand the UI data, never English
/// sentences, so every line below reaches the fisher in Aklanon.
void main() {
  late AppLocalizations en;
  late AppLocalizations akl;

  setUpAll(() async {
    en = await AppLocalizations.delegate.load(const Locale('en'));
    akl = await AppLocalizations.delegate.load(const Locale('akl'));
  });

  DailyOutlook day({int code = 1, double? gust, double? wave}) => DailyOutlook(
        date: DateTime(2026, 9, 26),
        weatherCode: code,
        gustKph: gust,
        waveM: wave,
        risk: RiskAssessment.unknown,
      );

  test('hazard pop-ups speak Aklanon and count buoys', () {
    for (final HazardKind kind in HazardKind.values) {
      expect(kind.title(akl), isNot(kind.title(en)));
      expect(kind.message(akl, 3), contains('3'));
      expect(kind.message(akl, 3), isNot(kind.message(en, 3)));
    }
  });

  test('advisory priorities are labelled per language, stored by name', () {
    for (final AdvisoryPriority p in AdvisoryPriority.values) {
      expect(p.label(akl), isNot(p.label(en)));
      expect(AdvisoryPriority.fromWire(p.name), p);
    }
  });

  test('a device forecast verdict carries reasons as data', () {
    final RiskAssessment risk = SafetyScore.assess(day(gust: 12, wave: 3.0));
    expect(risk.reason, isNull);
    expect(risk.factors.map((f) => f.kind), contains(RiskFactorKind.swell));
    expect(risk.reasonText(en), '3.0 m swell');
    expect(risk.reasonText(akl), '3.0 m nga alon');
  });

  test('a calm device verdict says so in Aklanon, and admits missing waves',
      () {
    expect(
      SafetyScore.assess(day(gust: 5, wave: 0.4)).reasonText(akl),
      akl.riskNoAdverse,
    );
    expect(
      SafetyScore.assess(day(gust: 5)).reasonText(akl),
      akl.riskNoAdverseNoWave,
    );
  });

  test('reasons survive the offline cache', () {
    final DailyOutlook scored = SafetyScore.applyTo(day(code: 95, gust: 50));
    final DailyOutlook? restored =
        DailyOutlook.fromCacheJson(scored.toCacheJson());
    expect(restored!.risk.reasonText(akl), scored.risk.reasonText(akl));
    expect(restored.risk.reasonText(akl), contains('kilat'));
  });

  test('a backend verdict keeps its own text', () {
    const RiskAssessment backend = RiskAssessment(
      level: RiskLevel.caution,
      source: RiskSource.backend,
      reason: 'Buoy B reports 3 m swell',
    );
    expect(backend.reasonText(akl), 'Buoy B reports 3 m swell');
  });

  test('GPS failures are explained in Aklanon', () {
    for (final LocationFailure? f in <LocationFailure?>[
      ...LocationFailure.values,
      null,
    ]) {
      expect(f.message(akl), isNot(f.message(en)));
    }
  });

  test('the last-attempt line is stored as codes and read in Aklanon', () {
    final String stored = DeliveryFailure.encode(<DeliveryFailure>[
      DeliveryFailure.buoyNotConnected,
      DeliveryFailure.noInternet,
    ]);
    expect(stored, 'buoy_not_connected,no_internet');
    expect(
      deliveryFailureText(akl, stored),
      '${akl.deliveryFailureBuoyNotConnected} · '
      '${akl.deliveryFailureNoInternet}',
    );
    // Rows written before the codes existed hold English text.
    expect(
      deliveryFailureText(akl, 'no buoy in range · no internet connection'),
      'no buoy in range · no internet connection',
    );
  });

  testWidgets('the welcome note and "All" areas read in Aklanon',
      (WidgetTester tester) async {
    Widget card(Advisory advisory) => MaterialApp(
          locale: const Locale('akl'),
          supportedLocales: kSupportedLocales,
          localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
            ...kFallbackDelegates,
          ],
          home: Scaffold(
            body: SingleChildScrollView(child: AdvisoryCard(advisory: advisory)),
          ),
        );

    await tester.pumpWidget(card(WelcomeAdvisory.instance));
    expect(find.text(akl.welcomeAdvisoryTitle), findsOneWidget);
    expect(find.text(akl.welcomeAdvisoryByline), findsOneWidget);
    expect(find.text(en.welcomeAdvisoryTitle), findsNothing);

    await tester.pumpWidget(card(const Advisory(
      title: 'Gale warning',
      description: '',
      priority: AdvisoryPriority.warning,
      municipality: 'All',
    )));
    expect(find.text(akl.advisoryAllAreas), findsOneWidget);
    expect(find.text(akl.advisoryPriorityWarning.toUpperCase()), findsOneWidget);
  });
}
