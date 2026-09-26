import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_alarm.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:aqone/ui/home_page.dart';
import 'package:aqone/ui/sos_flow.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

// The countdown froze at "1" and sent nothing (docs/edge-remediation/
// EVIDENCE-critical.md, C3 run, 2026-09-25 22:08). The countdown's own state
// said it had finished, yet its route was still on top and idle: its
// Navigator.pop had removed a different route. These tests pin the two ways
// that happens.

Widget _app(Widget home) {
  return MaterialApp(
    locale: const Locale('en'),
    supportedLocales: kSupportedLocales,
    localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
      ...kFallbackDelegates,
    ],
    home: home,
  );
}

void main() {
  testWidgets(
      'a route opened on top of the countdown does not stop the SOS '
      'and is not closed by it', (tester) async {
    late BuildContext context;
    await tester.pumpWidget(_app(Scaffold(
      body: Builder(builder: (c) {
        context = c;
        return const SizedBox.shrink();
      }),
    )));

    bool? dispatched;
    showGeneralDialog<bool>(
      context: context,
      barrierDismissible: false,
      pageBuilder: (_, __, ___) =>
          const SosCountdownScreen(duration: Duration(seconds: 5)),
    ).then((value) => dispatched = value);
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    // What the app shell really does mid-countdown: a squall RETURN NOW page,
    // a rescue ETA dialog or the unsent-SOS prompt opens on the root navigator.
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const AlertDialog(title: Text('Opened on top')),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    await tester.pump(const Duration(seconds: 5));
    await tester.pump(const Duration(milliseconds: 500));

    expect(dispatched, isTrue,
        reason: 'the countdown ran out, so the SOS must be dispatched');
    expect(find.byType(SosCountdownScreen), findsNothing);
    expect(find.text('Opened on top'), findsOneWidget,
        reason: 'the countdown must close itself, not whatever is on top');
  });

  testWidgets('two quick taps on SOS open one countdown, not two',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'silent_sos': false,
    });
    await tester.pumpWidget(_app(HomePage(
      service: _DummySosService(),
      identity: const VesselIdentity(vesselId: 'v-test', boat: ''),
      feeds: VentureFeeds(backend: BackendClient()),
      location: LocationService(),
      sosAlarm: _SilentAlarm(),
    )));
    await tester.pump();

    // A nervous double tap: both taps land before the app gets a turn to
    // mark itself as sending.
    final Offset sos = tester.getCenter(find.text('SOS'));
    for (var pointer = 1; pointer <= 2; pointer++) {
      tester.binding.handlePointerEvent(
          PointerDownEvent(pointer: pointer, position: sos));
      tester.binding
          .handlePointerEvent(PointerUpEvent(pointer: pointer, position: sos));
    }
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byType(SosCountdownScreen), findsOneWidget);
  });
}

class _SilentAlarm extends SosAlarm {
  @override
  Future<void> start() async {}

  @override
  Future<void> stop() async {}

  @override
  Future<void> dispose() async {}
}

class _DummySosService extends SosService {
  _DummySosService()
      : super(
          outbox: OutboxStore(AppDatabase()),
          identity: IdentityStore(AppDatabase()),
          buoy: BuoyClient(),
          backend: BackendClient(),
          location: LocationService(),
        );

  @override
  void start() {}

  @override
  Future<List<SosRecord>> history() async => const <SosRecord>[];
}
