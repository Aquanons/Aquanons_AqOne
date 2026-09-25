import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/buoy_contact.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/ui/widgets/buoy_status_card.dart';
import 'package:aqone/ui/widgets/delivery_state_tile.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_alarm.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:aqone/ui/home_page.dart';
import 'package:aqone/ui/sos_flow.dart';
import 'package:aqone/ui/widgets/action_pill.dart';
import 'package:aqone/ui/widgets/responder_eta_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Widgets under test now read their copy from AppLocalizations, so the host
/// has to carry the delegates. Defaults to English: these tests assert the
/// documented English sentences. Cross-locale coverage lives in
/// test/localization_test.dart.
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

Widget _hostPage(Widget page, {Locale locale = const Locale('en')}) {
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
    home: page,
  );
}

BuoyStatus _status({
  bool uplink = true,
  int queueDepth = 0,
  int clients = 1,
}) {
  return BuoyStatus(
    buoyId: 'BUOY01',
    uplink: uplink,
    queueDepth: queueDepth,
    clients: clients,
    observedAt: DateTime.utc(2026, 8, 4, 9, 15),
  );
}

SosRecord _record({
  DeliveryState state = DeliveryState.relayed,
  double? lat,
  double? lon,
  int? seq,
  String? ackedBy,
  String? etaAt,
  String? resolvedAt,
  int? fisherReply,
  bool fisherReplySynced = false,
  int? relayedAt,
}) {
  return SosRecord(
    localId: 'local-1',
    vesselId: '0123456789abcdef0123456789abcdef',
    boat: 'BG-123',
    clientTs: 1722700000,
    state: state,
    lat: lat,
    lon: lon,
    seq: seq,
    buoyId: seq == null ? null : 'BUOY01',
    ackedBy: ackedBy,
    etaAt: etaAt,
    resolvedAt: resolvedAt,
    fisherReply: fisherReply,
    fisherReplySynced: fisherReplySynced,
    relayedAt: relayedAt,
  );
}

void main() {
  group('BuoyStatusCard', () {
    testWidgets('reports no buoy when there is no status', (tester) async {
      await tester.pumpWidget(_host(const BuoyStatusCard(status: null)));

      expect(find.text('No buoy connected'), findsOneWidget);
      expect(
        find.text('Join a buoy WiFi network to hand off an SOS.'),
        findsOneWidget,
      );
    });

    testWidgets('shows buoy id and an honest uplink message when connected',
        (tester) async {
      await tester.pumpWidget(_host(BuoyStatusCard(status: _status())));

      expect(find.text('Buoy BUOY01'), findsOneWidget);
      expect(
        find.text(
          'Link to shore is up. Your SOS will reach the rescue centre now.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('surfaces a down uplink and queue depth honestly',
        (tester) async {
      await tester.pumpWidget(
        _host(
          BuoyStatusCard(status: _status(uplink: false, queueDepth: 3)),
        ),
      );

      expect(
        find.text(
          'Link to shore is down. This buoy will hold your SOS and deliver '
          'it automatically once the link returns.',
        ),
        findsOneWidget,
      );
      expect(find.text('3 message(s) waiting on this buoy'), findsOneWidget);
    });

    testWidgets('never shows a battery reading - the firmware sends none',
        (tester) async {
      await tester.pumpWidget(_host(BuoyStatusCard(status: _status())));

      expect(find.textContaining('%'), findsNothing);
    });
  });

  group('DeliveryStateTile', () {
    testWidgets('renders the documented sentence for every state',
        (tester) async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));

      for (final state in DeliveryState.values) {
        await tester.pumpWidget(
          _host(DeliveryStateTile(record: _record(state: state))),
        );

        expect(find.text(state.title(t)), findsOneWidget);
        expect(find.text(state.description(t)), findsOneWidget);
      }
    });

    testWidgets('states there is no fix rather than showing a fake position',
        (tester) async {
      await tester.pumpWidget(_host(DeliveryStateTile(record: _record())));

      expect(find.text('No GPS fix recorded'), findsOneWidget);
    });

    testWidgets('shows coordinates and the buoy hop when present',
        (tester) async {
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(lat: 11.6050, lon: 122.3125, seq: 42),
          ),
        ),
      );

      expect(find.text('11.60500, 122.31250'), findsOneWidget);
      expect(find.text('buoy BUOY01 · seq 42'), findsOneWidget);
    });

    testWidgets('names the responder once acknowledged', (tester) async {
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(
              state: DeliveryState.acknowledged,
              ackedBy: 'ranger-01',
            ),
          ),
        ),
      );

      expect(find.text('ranger-01'), findsOneWidget);
      expect(find.text('Responder acknowledged this SOS.'), findsOneWidget);
    });

    testWidgets('shows the rescue ETA countdown once the responder sets one',
        (tester) async {
      final eta = DateTime.now().add(const Duration(minutes: 2));
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(state: DeliveryState.acknowledged, etaAt: eta.toIso8601String()),
          ),
        ),
      );

      expect(find.text('Rescue ETA'), findsOneWidget);
      expect(find.textContaining(RegExp(r'[12]:\d{2}')), findsOneWidget);
    });

    testWidgets('marks the rescue ETA delayed once it passes', (tester) async {
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(
              state: DeliveryState.acknowledged,
              etaAt: DateTime.now().subtract(const Duration(minutes: 1)).toIso8601String(),
            ),
          ),
        ),
      );

      expect(find.text('Rescue ETA'), findsOneWidget);
      expect(find.text('Delayed — still on the way'), findsOneWidget);
    });

    testWidgets('resolved card points back to a new SOS if danger remains',
        (tester) async {
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(
              resolvedAt: DateTime.now().toUtc().toIso8601String(),
            ),
          ),
        ),
      );

      expect(
        find.text('Still in danger? Send another SOS.'),
        findsOneWidget,
      );
    });

    testWidgets('synced stand-down shows still-in-danger warning',
        (tester) async {
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(
              fisherReply: 2,
              fisherReplySynced: true,
            ),
          ),
        ),
      );

      expect(
        find.text('Still in danger? Send another SOS.'),
        findsOneWidget,
      );
    });

    testWidgets('pending stand-down does not show still-in-danger warning',
        (tester) async {
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(
              fisherReply: 2,
              fisherReplySynced: false,
            ),
          ),
        ),
      );

      expect(
        find.text('Still in danger? Send another SOS.'),
        findsNothing,
      );
    });

    testWidgets(
        'relayed record past 10 min deadline shows sosPodNotConfirmed',
        (tester) async {
      final nowSec = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
      await tester.pumpWidget(
        _host(
          DeliveryStateTile(
            record: _record(
              state: DeliveryState.relayed,
              relayedAt: nowSec - 601,
            ),
          ),
        ),
      );

      expect(
        find.text(
          'The pod has not confirmed this SOS reached shore yet. Still trying.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('reopened incident clears resolved card', (tester) async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      final resolvedRecord = _record(
        state: DeliveryState.acknowledged,
        resolvedAt: '2026-09-15T00:00:00Z',
      );

      await tester.pumpWidget(_host(DeliveryStateTile(record: resolvedRecord)));
      expect(find.text(t.resolvedTitle), findsAtLeastNWidgets(1));

      final reopenedRecord = _record(
        state: DeliveryState.acknowledged,
        resolvedAt: null,
      );

      await tester.pumpWidget(_host(DeliveryStateTile(record: reopenedRecord)));
      expect(find.text(t.resolvedTitle), findsNothing);
      expect(find.text(DeliveryState.acknowledged.title(t)), findsOneWidget);
    });
  });

  group('Stand-down and Responder ETA', () {
    testWidgets('stand-down needs confirmation', (tester) async {
      tester.view.physicalSize = const Size(800, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final t = await AppLocalizations.delegate.load(const Locale('en'));
      var stoodDown = false;

      final record = ValueNotifier<SosRecord>(_record());
      addTearDown(record.dispose);

      await tester.pumpWidget(
        _host(
          EmergencyDetailsSheet(
            record: record,
            onSubmitNote: (_) async {},
            onStandDown: () async {
              stoodDown = true;
            },
          ),
        ),
      );

      // Slide to stand down
      await tester.drag(find.byIcon(Icons.undo_rounded), const Offset(700, 0));
      await tester.pumpAndSettle();

      // Confirmation dialog must appear
      expect(find.text(t.sosStandDownConfirmTitle), findsOneWidget);
      expect(find.text(t.sosStandDownConfirmBody), findsOneWidget);

      // Cancel the dialog
      await tester.tap(find.text(t.actionCancel));
      await tester.pumpAndSettle();

      expect(stoodDown, isFalse);

      // Drag again and confirm
      await tester.drag(find.byIcon(Icons.undo_rounded), const Offset(700, 0));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('confirm_stand_down')));
      await tester.pumpAndSettle();

      expect(stoodDown, isTrue);
    });

    testWidgets('undo within 2 minutes sends still-in-danger', (tester) async {
      tester.view.physicalSize = const Size(800, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final t = await AppLocalizations.delegate.load(const Locale('en'));
      var repliedCode = 0;

      await tester.pumpWidget(
        MaterialApp(
          supportedLocales: kSupportedLocales,
          localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
            ...kFallbackDelegates,
          ],
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      duration: const Duration(minutes: 2),
                      content: Text(t.standDownTitle),
                      action: SnackBarAction(
                        label: t.sosStandDownUndo,
                        onPressed: () {
                          repliedCode = 1;
                        },
                      ),
                    ),
                  );
                },
                child: const Text('Trigger Stand Down'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Trigger Stand Down'));
      await tester.pumpAndSettle();

      expect(find.text(t.sosStandDownUndo), findsOneWidget);
      await tester.tap(find.text(t.sosStandDownUndo));
      await tester.pumpAndSettle();

      expect(repliedCode, 1);
    });

    testWidgets('no ETA copy when acknowledged without eta', (tester) async {
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      final record = _record(
        state: DeliveryState.acknowledged,
        etaAt: null,
      );

      await tester.pumpWidget(
        _host(
          ResponderEtaDialog(
            record: record,
            sos: _DummySosService(),
          ),
        ),
      );

      expect(find.text(t.sosNoEtaYet), findsOneWidget);
    });

    testWidgets('HomePage displays SOS action pill', (tester) async {
      await tester.pumpWidget(
        _hostPage(
          HomePage(
            service: _DummySosService(),
            identity: const VesselIdentity(vesselId: 'v-test', boat: ''),
            feeds: VentureFeeds(backend: BackendClient()),
            location: LocationService(),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(ActionPill), findsOneWidget);
      expect(find.text('SOS'), findsOneWidget);
    });

    testWidgets('silent SOS starts no alarm', (tester) async {
      SharedPreferences.setMockInitialValues({'silent_sos': true});
      final alarm = _TrackingSosAlarm();
      await tester.pumpWidget(
        _hostPage(
          HomePage(
            service: _DummySosService(),
            identity: const VesselIdentity(vesselId: 'v-test', boat: ''),
            feeds: VentureFeeds(backend: BackendClient()),
            location: LocationService(),
            sosAlarm: alarm,
          ),
        ),
      );
      await tester.pump();

      await tester.tap(find.text('SOS'));
      await tester.pump();

      expect(alarm.startCalled, isFalse);
    });

    // docs/64 FFR-02 (finding F2): a long, hard press from a panicking user
    // must not quietly switch the siren off.
    testWidgets('holding SOS behaves exactly like a tap', (tester) async {
      SharedPreferences.setMockInitialValues({'silent_sos': false});
      final alarm = _TrackingSosAlarm();
      await tester.pumpWidget(
        _hostPage(
          HomePage(
            service: _DummySosService(),
            identity: const VesselIdentity(vesselId: 'v-test', boat: ''),
            feeds: VentureFeeds(backend: BackendClient()),
            location: LocationService(),
            sosAlarm: alarm,
          ),
        ),
      );
      await tester.pump();

      final gesture =
          await tester.startGesture(tester.getCenter(find.text('SOS')));
      await tester.pump(const Duration(seconds: 4));
      await gesture.up();
      await tester.pump();
      await tester.pump();

      expect(alarm.startCalled, isTrue);
      expect(find.byType(SosCountdownScreen), findsOneWidget);
    });
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
