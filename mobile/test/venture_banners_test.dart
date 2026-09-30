import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/map_snapshot_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/advisory.dart';
import 'package:aqone/models/buoy_marker.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/forecast_outlook.dart';
import 'package:aqone/models/hazard_alert.dart';
import 'package:aqone/models/hotspot_cell.dart';
import 'package:aqone/models/sea_condition.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/models/weather_snapshot.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:aqone/ui/venture_page.dart';
import 'package:aqone/ui/widgets/squall_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget page) {
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

SosRecord _openSos() {
  return SosRecord(
    localId: 'local-test-1',
    vesselId: 'v-test',
    boat: 'Test Boat',
    clientTs: DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000,
    state: DeliveryState.delivered,
  );
}

class _FakeSosService extends SosService {
  _FakeSosService(this.stubHistory)
      : super(
          outbox: OutboxStore(AppDatabase()),
          identity: IdentityStore(AppDatabase()),
          buoy: BuoyClient(),
          backend: BackendClient(),
          location: LocationService(),
        );

  final List<SosRecord> stubHistory;

  @override
  void start() {}

  @override
  Future<List<SosRecord>> history() async => stubHistory;
}

class _FakeLocationService extends LocationService {
  @override
  Future<Fix?> cachedFixIfPermitted() async => Fix(
        lat: 11.70,
        lon: 122.44,
        accuracy: 5,
        at: DateTime.now().toUtc(),
      );

  @override
  Future<LocationResult> locate() async => LocationResult.success(
        Fix(
          lat: 11.70,
          lon: 122.44,
          accuracy: 5,
          at: DateTime.now().toUtc(),
        ),
      );
}

class _FakeVentureFeeds extends VentureFeeds {
  _FakeVentureFeeds()
      : super(
          backend: BackendClient(),
          snapshots: MapSnapshotStore(AppDatabase()),
        );

  @override
  Future<Map<String, DateTime>> snapshotAges() async => <String, DateTime>{
        MapSnapshotStore.feedBuoys:
            DateTime.now().subtract(const Duration(hours: 4)),
      };

  @override
  Future<SeaCondition?> seaCondition() async => null;

  @override
  Future<List<Advisory>?> advisories() async => const <Advisory>[];

  @override
  Future<WeatherSnapshot?> weather(
          {required double lat, required double lon}) async =>
      const WeatherSnapshot(temperature: 28, windSpeed: 5, weatherCode: 0);

  @override
  Future<List<BuoyMarker>?> buoys() async => const <BuoyMarker>[];

  @override
  Future<HotspotSurface?> hotspots() async => null;

  @override
  Future<List<HazardAlert>?> hazards(HazardKind kind) async =>
      const <HazardAlert>[];

  @override
  Future<ForecastOutlook?> forecastOutlook({
    required double lat,
    required double lon,
    String? municipality,
  }) async =>
      null;
}

Future<void> _pumpVenture(
  WidgetTester tester, {
  List<SosRecord> history = const <SosRecord>[],
}) async {
  await tester.pumpWidget(_host(VenturePage(
    identity: const VesselIdentity(vesselId: 'v-test', boat: ''),
    sos: _FakeSosService(history),
    feeds: _FakeVentureFeeds(),
    location: _FakeLocationService(),
  )));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  for (var i = 0;
      i < 5 && find.byType(AlertDialog).evaluate().isNotEmpty;
      i++) {
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.byType(TextButton),
      ),
      warnIfMissed: false,
    );
    await tester.pump(const Duration(milliseconds: 500));
  }
}

void main() {
  testWidgets('Venture shows no squall nowcast card', (tester) async {
    await _pumpVenture(tester);
    expect(find.byType(SquallBanner), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('SOS status banner collapses and expands again',
      (tester) async {
    final SemanticsHandle handle = tester.ensureSemantics();
    final t = await AppLocalizations.delegate.load(const Locale('en'));
    await _pumpVenture(tester, history: <SosRecord>[_openSos()]);
    expect(find.textContaining('SOS:'), findsWidgets);

    // Offline banner is also up (stale fake ages), so the SOS toggle is
    // the second collapse affordance in tree order.
    await tester.tap(find.bySemanticsLabel(t.bannerCollapse).at(1));
    await tester.pump();
    expect(find.textContaining('SOS:'), findsNothing);
    expect(find.bySemanticsLabel(t.bannerExpand), findsWidgets);

    await tester.tap(find.bySemanticsLabel(t.bannerExpand).first);
    await tester.pump();
    expect(find.textContaining('SOS:'), findsWidgets);
    await tester.pumpWidget(const SizedBox());
    handle.dispose();
  });

  testWidgets('stale map banner collapses and expands again', (tester) async {
    final SemanticsHandle handle = tester.ensureSemantics();
    final t = await AppLocalizations.delegate.load(const Locale('en'));
    await _pumpVenture(tester);
    expect(find.textContaining('saved map data'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel(t.bannerCollapse).first);
    await tester.pump();
    expect(find.textContaining('saved map data'), findsNothing);

    await tester.tap(find.bySemanticsLabel(t.bannerExpand).first);
    await tester.pump();
    expect(find.textContaining('saved map data'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    handle.dispose();
  });
}
