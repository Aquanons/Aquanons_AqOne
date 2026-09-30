// docs/64 Rev 5 D10: SOS is reachable in one tap from Home again (P1,
// FFR-07); `546a38c` removed it. These are the Home tests that commit moved
// to At sea, restored unchanged in intent. Acceptance tests written by the
// spec author; do not edit them to make them pass.

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
import 'package:aqone/ui/widgets/action_pill.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Widget _hostPage(Widget page) {
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
    home: page,
  );
}

HomePage _home({SosAlarm? alarm}) => HomePage(
      service: _DummySosService(),
      identity: const VesselIdentity(vesselId: 'v-test', boat: ''),
      feeds: VentureFeeds(backend: BackendClient()),
      location: LocationService(),
      sosAlarm: alarm,
    );

void main() {
  testWidgets('Home shows the SOS control', (tester) async {
    await tester.pumpWidget(_hostPage(_home()));
    await tester.pump();

    expect(find.byType(ActionPill), findsOneWidget);
    expect(find.text('SOS'), findsOneWidget);
  });

  testWidgets('tapping SOS on Home starts the countdown and the alarm', (tester) async {
    SharedPreferences.setMockInitialValues({'silent_sos': false});
    final alarm = _TrackingSosAlarm();
    await tester.pumpWidget(_hostPage(_home(alarm: alarm)));
    await tester.pump();

    await tester.tap(find.text('SOS'));
    await tester.pump();
    await tester.pump();

    expect(alarm.startCalled, isTrue);
    expect(find.byType(SosCountdownScreen), findsOneWidget);
  });

  testWidgets('silent SOS from Home starts no alarm', (tester) async {
    SharedPreferences.setMockInitialValues({'silent_sos': true});
    final alarm = _TrackingSosAlarm();
    await tester.pumpWidget(_hostPage(_home(alarm: alarm)));
    await tester.pump();

    await tester.tap(find.text('SOS'));
    await tester.pump();

    expect(alarm.startCalled, isFalse);
  });

  // docs/64 FFR-02: a long, hard press must not quietly switch the siren off.
  testWidgets('holding SOS on Home behaves exactly like a tap', (tester) async {
    SharedPreferences.setMockInitialValues({'silent_sos': false});
    final alarm = _TrackingSosAlarm();
    await tester.pumpWidget(_hostPage(_home(alarm: alarm)));
    await tester.pump();

    final gesture = await tester.startGesture(tester.getCenter(find.text('SOS')));
    await tester.pump(const Duration(seconds: 4));
    await gesture.up();
    await tester.pump();
    await tester.pump();

    expect(alarm.startCalled, isTrue);
    expect(find.byType(SosCountdownScreen), findsOneWidget);
  });
}

class _TrackingSosAlarm extends SosAlarm {
  bool startCalled = false;

  @override
  Future<void> start() async {
    startCalled = true;
  }

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
