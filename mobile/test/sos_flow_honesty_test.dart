import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/fisher_sos_situation.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/ui/sos_flow.dart';
import 'package:aqone/ui/widgets/delivery_state_tile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

// docs/64_FISHER_FRICTION_REDUCTION_SPEC.md FFR-01 and FFR-03 (finding F1).

Widget _host(Widget child, {Locale locale = const Locale('en')}) {
  return MaterialApp(
    locale: locale,
    supportedLocales: kSupportedLocales,
    localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
      ...kFallbackDelegates,
    ],
    home: Scaffold(body: SingleChildScrollView(child: child)),
  );
}

SosRecord _record({
  DeliveryState state = DeliveryState.saved,
  int? relayedAt,
  int? fisherReply,
  bool fisherReplySynced = false,
}) {
  return SosRecord(
    localId: 'local-1',
    vesselId: '0123456789abcdef0123456789abcdef',
    boat: 'BG-123',
    clientTs: DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000,
    state: state,
    relayedAt: relayedAt,
    fisherReply: fisherReply,
    fisherReplySynced: fisherReplySynced,
  );
}

void _tallView(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 1400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  group('post-SOS sheet tells the truth', () {
    testWidgets('an SOS that has not reached a pod is not shown as sent',
        (tester) async {
      _tallView(tester);
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      final record = ValueNotifier<SosRecord>(_record());
      addTearDown(record.dispose);

      await tester.pumpWidget(
        _host(
          EmergencyDetailsSheet(
            record: record,
            onSubmitNote: (_) async {},
            onStandDown: () async {},
          ),
        ),
      );

      expect(
        find.text(FisherSosSituation.notSentYet.title(t)),
        findsOneWidget,
      );
      expect(find.textContaining('BG-123'), findsWidgets);
      expect(find.byIcon(Icons.check_circle_rounded), findsNothing);
      expect(find.textContaining('SOS sent'), findsNothing);
      expect(find.textContaining('gone out'), findsNothing);
    });

    testWidgets('the sheet follows the record while it is open',
        (tester) async {
      _tallView(tester);
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      final record = ValueNotifier<SosRecord>(_record());
      addTearDown(record.dispose);

      await tester.pumpWidget(
        _host(
          EmergencyDetailsSheet(
            record: record,
            onSubmitNote: (_) async {},
            onStandDown: () async {},
          ),
        ),
      );
      expect(
        find.text(FisherSosSituation.notSentYet.title(t)),
        findsOneWidget,
      );

      record.value = _record(
        state: DeliveryState.relayed,
        relayedAt: DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000,
      );
      await tester.pump();

      expect(find.text(FisherSosSituation.notSentYet.title(t)), findsNothing);
      expect(find.text(FisherSosSituation.podHasIt.title(t)), findsOneWidget);
    });

    testWidgets('the sheet is honest in Tagalog and Aklanon too',
        (tester) async {
      _tallView(tester);
      for (final code in <String>['fil', 'akl']) {
        final t = await AppLocalizations.delegate.load(Locale(code));
        final record = ValueNotifier<SosRecord>(_record());

        await tester.pumpWidget(
          _host(
            EmergencyDetailsSheet(
              record: record,
              onSubmitNote: (_) async {},
              onStandDown: () async {},
            ),
            locale: Locale(code),
          ),
        );

        expect(
          find.text(FisherSosSituation.notSentYet.title(t)),
          findsOneWidget,
          reason: code,
        );
        expect(find.byIcon(Icons.check_circle_rounded), findsNothing,
            reason: code);
        record.dispose();
      }
    });
  });

  group('SOS history reads the same situation model', () {
    testWidgets('a stand-down the backend confirmed reads as cancelled',
        (tester) async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(
              state: DeliveryState.delivered,
              fisherReply: 2,
              fisherReplySynced: true,
            ),
          ),
        ),
      );

      expect(find.text(FisherSosSituation.cancelled.title(t)), findsOneWidget);
    });

    testWidgets('a stand-down still on its way reads as cancelling',
        (tester) async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(state: DeliveryState.delivered, fisherReply: 2),
          ),
        ),
      );

      expect(
        find.text(FisherSosSituation.cancelling.title(t)),
        findsOneWidget,
      );
    });
  });

  // Plan 70 AKL-04: the fisher reads the emergency types in Aklanon, but the
  // note on the MDRRMO dashboard stays English - responders work in English.
  testWidgets('an Aklanon emergency type still sends an English note',
      (tester) async {
    _tallView(tester);
    final akl = await AppLocalizations.delegate.load(const Locale('akl'));
    final record = ValueNotifier<SosRecord>(_record());
    addTearDown(record.dispose);
    final sent = <String>[];

    await tester.pumpWidget(
      _host(
        EmergencyDetailsSheet(
          record: record,
          onSubmitNote: (note) async => sent.add(note),
          onStandDown: () async {},
        ),
        locale: const Locale('akl'),
      ),
    );

    await tester.tap(find.text(akl.emergencyEngine));
    await tester.pump();
    await tester.tap(find.text(akl.sosSendUpdate));
    await tester.pump();

    expect(sent, <String>['Engine failure']);
  });
}
