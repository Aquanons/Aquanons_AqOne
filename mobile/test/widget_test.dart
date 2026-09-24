import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/buoy_contact.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/ui/widgets/buoy_status_card.dart';
import 'package:aqone/ui/widgets/delivery_state_tile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

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
  });
}
