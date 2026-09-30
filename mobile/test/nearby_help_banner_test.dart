// docs/73 Rev 2 G3: a compact nearby-help banner on Home and Advisories.
// Acceptance tests written by the spec author; do not edit them to make them
// pass.

import 'dart:io';

import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/data/seen_broadcast_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/nearby_sos.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/nearby_alarm.dart';
import 'package:aqone/services/nearby_sos_watcher.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:aqone/ui/advisories_page.dart';
import 'package:aqone/ui/home_page.dart';
import 'package:aqone/ui/widgets/nearby_help_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Widget _host(Widget child) {
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
    home: child,
  );
}

NearbySos _item(int id, double km) => NearbySos(
      broadcastId: id,
      sosEventId: id * 10,
      centerLat: 11.70,
      centerLon: 122.44,
      distanceKm: km,
      radiusKm: 10,
    );

class _QuietAlarm implements NearbyAlarm {
  @override
  dynamic noSuchMethod(Invocation invocation) => Future<void>.value();
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfiNoIsolate;

  testWidgets('shows the nearest call with its distance and how many more', (tester) async {
    await tester.pumpWidget(_host(Scaffold(
      body: NearbyHelpBanner(items: <NearbySos>[_item(1, 2.34), _item(2, 6.0)], hasFix: true, onTap: () {}),
    )));

    expect(find.textContaining('Fisher needs help'), findsOneWidget);
    expect(find.textContaining('2.3 km away'), findsOneWidget);
    expect(find.textContaining('away away'), findsNothing);
    expect(find.textContaining('+1 more'), findsOneWidget);
  });

  testWidgets('says distance unknown without a fix instead of hiding the call', (tester) async {
    await tester.pumpWidget(_host(Scaffold(
      body: NearbyHelpBanner(items: <NearbySos>[_item(1, 2.34)], hasFix: false, onTap: () {}),
    )));

    expect(find.textContaining('Fisher needs help'), findsOneWidget);
    expect(find.textContaining('distance unknown'), findsOneWidget);
  });

  testWidgets('renders nothing when no call is active', (tester) async {
    await tester.pumpWidget(_host(Scaffold(
      body: NearbyHelpBanner(items: const <NearbySos>[], hasFix: true, onTap: () {}),
    )));

    expect(find.textContaining('Fisher needs help'), findsNothing);
  });

  testWidgets('tapping the banner opens At sea', (tester) async {
    var taps = 0;
    await tester.pumpWidget(_host(Scaffold(
      body: NearbyHelpBanner(items: <NearbySos>[_item(1, 0.45)], hasFix: true, onTap: () => taps += 1),
    )));

    await tester.tap(find.textContaining('Fisher needs help'));
    expect(taps, 1);
  });

  group('on Home and Advisories', () {
    late Directory dir;
    late AppDatabase db;
    late NearbySosWatcher watcher;

    setUp(() async {
      dir = await Directory.systemTemp.createTemp('aqone_banner_');
      db = AppDatabase(overridePath: '${dir.path}/aqone.db');
      watcher = NearbySosWatcher(
        fetch: (lat, lon) async => <NearbySos>[_item(1, 2.34)],
        position: () async => const Fix(lat: 11.71, lon: 122.45),
        seen: SeenBroadcastStore(db),
        alarm: _QuietAlarm(),
        notify: (_) async {},
      );
    });
    tearDown(() async {
      watcher.dispose();
      await db.close();
      await dir.delete(recursive: true);
    });

    testWidgets('Home shows the banner and opens At sea from it', (tester) async {
      var opened = 0;
      await tester.runAsync(() => watcher.poll());
      await tester.pumpWidget(_host(HomePage(
        service: _DummySosService(),
        identity: const VesselIdentity(vesselId: 'v-test', boat: ''),
        feeds: VentureFeeds(backend: BackendClient()),
        location: LocationService(),
        nearby: watcher,
        onOpenNearby: () => opened += 1,
      )));
      await tester.pump();

      expect(find.byType(NearbyHelpBanner), findsOneWidget);
      expect(find.textContaining('2.3 km away'), findsOneWidget);
      await tester.tap(find.textContaining('Fisher needs help'));
      expect(opened, 1);
    });

    testWidgets('Advisories shows the banner', (tester) async {
      await tester.runAsync(() => watcher.poll());
      await tester.pumpWidget(_host(AdvisoriesPage(
        feeds: VentureFeeds(backend: BackendClient()),
        nearby: watcher,
        onOpenNearby: () {},
      )));
      await tester.pump();

      expect(find.byType(NearbyHelpBanner), findsOneWidget);
    });
  });
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
