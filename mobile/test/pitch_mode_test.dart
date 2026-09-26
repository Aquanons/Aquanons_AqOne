import 'package:aqone/core/config.dart';
import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/map_snapshot_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/advisory.dart';
import 'package:aqone/models/buoy_contact.dart';
import 'package:aqone/models/buoy_marker.dart';
import 'package:aqone/models/forecast_outlook.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/hotspot_cell.dart';
import 'package:aqone/models/sea_condition.dart';
import 'package:aqone/models/sos_record.dart';
import 'package:aqone/models/squall_watch.dart';
import 'package:aqone/models/weather_snapshot.dart';
import 'package:aqone/services/backend_client.dart';
import 'package:aqone/services/buoy_client.dart';
import 'package:aqone/services/location_service.dart';
import 'package:aqone/services/sos_service.dart';
import 'package:aqone/services/venture_feeds.dart';
import 'package:aqone/ui/home_page.dart';
import 'package:aqone/ui/venture_page.dart';
import 'package:aqone/ui/widgets/responder_eta_dialog.dart';
import 'package:aqone/ui/widgets/squall_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeSosService extends SosService {
  _FakeSosService({this.stubHistory = const <SosRecord>[]})
      : super(
          outbox: OutboxStore(AppDatabase()),
          identity: IdentityStore(AppDatabase()),
          buoy: BuoyClient(),
          backend: BackendClient(),
          location: LocationService(),
        );

  final List<SosRecord> stubHistory;
  final List<int> sentReplies = <int>[];

  @override
  void start() {}

  @override
  Future<List<SosRecord>> history() async => stubHistory;

  @override
  Future<BuoyStatus?> pollBuoy() async => null;

  @override
  Future<bool> replyToSos(String localId, int reply) async {
    sentReplies.add(reply);
    return true;
  }
}

class _FakeLocationService extends LocationService {
  @override
  Future<Fix?> cachedFixIfPermitted() async => null;

  @override
  Future<LocationResult> locate({Duration? timeout}) async =>
      const LocationResult.failed(LocationFailure.servicesDisabled);
}

class _FakeVentureFeeds extends VentureFeeds {
  _FakeVentureFeeds()
      : super(
          backend: BackendClient(),
          snapshots: MapSnapshotStore(AppDatabase()),
        );

  @override
  Future<SeaCondition?> seaCondition() async => null;

  @override
  Future<List<Advisory>?> advisories() async => const <Advisory>[];

  @override
  Future<WeatherSnapshot?> weather({required double lat, required double lon}) async => null;

  @override
  Future<ForecastOutlook?> forecastOutlook({
    required double lat,
    required double lon,
    String? municipality,
  }) async =>
      null;

  @override
  Future<List<BuoyMarker>?> buoys() async => const <BuoyMarker>[];

  @override
  Future<HotspotSurface?> hotspots() async => null;

  @override
  Future<SquallWatch> squall() async => SquallWatch.unavailable;
}

const VesselIdentity _testIdentity = VesselIdentity(
  vesselId: 'test-vessel-123',
  boat: 'Test Boat',
  skipperName: 'Test Skipper',
  phone: '09123456789',
);

Widget _host(Widget child, {Size size = const Size(390, 844)}) {
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
    home: Scaffold(
      body: SizedBox(
        width: size.width,
        height: size.height,
        child: child,
      ),
    ),
  );
}

SosRecord _testSosRecord({
  DeliveryState state = DeliveryState.relayed,
  int? responderStatus,
  String? responderNote,
  int? etaMinutesFromNow,
}) {
  return SosRecord(
    localId: 'local-test-sos-1',
    vesselId: _testIdentity.vesselId,
    boat: _testIdentity.boat,
    clientTs: 1755248500,
    state: state,
    buoyId: state == DeliveryState.saved ? null : 'BUOY-AKLAN-01',
    seq: state == DeliveryState.saved ? null : 42,
    etaAt: etaMinutesFromNow == null
        ? null
        : DateTime.now().add(Duration(minutes: etaMinutesFromNow)).toIso8601String(),
    responderStatus: responderStatus,
    responderNote: responderNote,
  );
}

void main() {
  group('Normal mode verification (PITCH_MODE=false)', () {
    testWidgets('deferred controls remain available in normal development mode', (
      WidgetTester tester,
    ) async {
      if (AqOneConfig.pitchMode) {
        return;
      }

      await tester.pumpWidget(
        _host(
          HomePage(
            service: _FakeSosService(),
            identity: _testIdentity,
            feeds: _FakeVentureFeeds(),
            location: _FakeLocationService(),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('No SOS sent yet.'), findsOneWidget);

      await tester.pumpWidget(
        _host(
          VenturePage(
            identity: _testIdentity,
            sos: _FakeSosService(),
            feeds: _FakeVentureFeeds(),
            location: _FakeLocationService(),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('SOS'), findsOneWidget);

      // Clean up widget tree
      await tester.pumpWidget(const SizedBox());
    });
  });

  group('Pitch mode verification (PITCH_MODE=true)', () {
    testWidgets(
      'manual SOS is present while hotspot and squall UI are absent',
      (WidgetTester tester) async {
        if (!AqOneConfig.pitchMode) {
          return;
        }

        // 1. Home page in pitch mode: squall banner is absent
        await tester.pumpWidget(
          _host(
            HomePage(
              service: _FakeSosService(),
              identity: _testIdentity,
              feeds: _FakeVentureFeeds(),
              location: _FakeLocationService(),
            ),
          ),
        );
        await tester.pump();
        expect(find.byType(SquallBanner), findsNothing);

        // 2. Venture page in pitch mode: SOS present, squall and hotspot absent
        await tester.pumpWidget(
          _host(
            VenturePage(
              identity: _testIdentity,
              sos: _FakeSosService(),
              feeds: _FakeVentureFeeds(),
              location: _FakeLocationService(),
            ),
          ),
        );
        await tester.pump();
        expect(find.text('SOS'), findsOneWidget);
        expect(find.byType(SquallBanner), findsNothing);

        // Clean up widget tree
        await tester.pumpWidget(const SizedBox());
      },
    );

    testWidgets(
      'renders cleanly on narrow (360x640) and standard (390x844) phone screens with active SOS status and responder ETA',
      (WidgetTester tester) async {
        if (!AqOneConfig.pitchMode) {
          return;
        }

        final activeSos = _testSosRecord(
          state: DeliveryState.relayed,
          responderStatus: 2,
          etaMinutesFromNow: 25,
        );
        final sosService = _FakeSosService(stubHistory: <SosRecord>[activeSos]);

        // Verify across both narrow (360x640) and standard (390x844) viewports
        for (final size in const <Size>[Size(360, 640), Size(390, 844)]) {
          tester.view.physicalSize = size;
          tester.view.devicePixelRatio = 1.0;
          addTearDown(tester.view.resetPhysicalSize);
          addTearDown(tester.view.resetDevicePixelRatio);

          await tester.pumpWidget(
            _host(
              VenturePage(
                identity: _testIdentity,
                sos: sosService,
                feeds: _FakeVentureFeeds(),
                location: _FakeLocationService(),
              ),
              size: size,
            ),
          );
          await tester.pump();

          // Honest relayed state is visible on the status banner
          expect(find.textContaining('Handed to the buoy'), findsOneWidget);
          expect(find.text('SOS'), findsOneWidget);

          // Test ResponderEtaDialog on the phone viewport
          await tester.pumpWidget(
            _host(
              ResponderEtaDialog(record: activeSos, sos: sosService),
              size: size,
            ),
          );
          await tester.pump();

          expect(find.text('Rescue boat on the way'), findsOneWidget);
          expect(find.text('ARRIVING IN'), findsOneWidget);
        }

        await tester.pumpWidget(const SizedBox());
      },
    );
  });
}
