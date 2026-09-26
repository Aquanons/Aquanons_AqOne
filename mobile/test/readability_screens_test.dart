import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/core/tokens.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/map_snapshot_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/advisory.dart';
import 'package:aqone/models/buoy_contact.dart';
import 'package:aqone/models/buoy_marker.dart';
import 'package:aqone/models/delivery_state.dart';
import 'package:aqone/models/fisher_sos_situation.dart';
import 'package:aqone/models/forecast_outlook.dart';
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
import 'package:aqone/ui/app_shell.dart';
import 'package:aqone/ui/home_page.dart';
import 'package:aqone/ui/sos_flow.dart';
import 'package:aqone/ui/venture_page.dart';
import 'package:aqone/ui/widgets/buoy_status_card.dart';
import 'package:aqone/ui/widgets/delivery_state_tile.dart';
import 'package:aqone/ui/widgets/sos_status_card.dart';
import 'package:aqone/ui/widgets/squall_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

// docs/64_FISHER_FRICTION_REDUCTION_SPEC.md FFR-04, FFR-08, FFR-11; plan 65 Phase 3.

const SquallWatch _watch =
    SquallWatch(level: SquallLevel.watch, returnNow: false);

const VesselIdentity _identity = VesselIdentity(
  vesselId: 'test-vessel-123',
  boat: 'Test Boat',
  skipperName: 'Test Skipper',
  phone: '09123456789',
);

SosRecord _openSos({DeliveryState state = DeliveryState.relayed}) {
  final nowSec = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
  return SosRecord(
    localId: 'local-1',
    vesselId: _identity.vesselId,
    boat: _identity.boat,
    clientTs: nowSec - 120,
    state: state,
    relayedAt: state == DeliveryState.saved ? null : nowSec - 60,
    buoyId: 'BUOY01',
    seq: 7,
  );
}

Widget _host(
  Widget home, {
  double textScale = 1,
  Brightness brightness = Brightness.light,
}) {
  return MaterialApp(
    theme: buildAqTheme(brightness),
    locale: const Locale('en'),
    supportedLocales: kSupportedLocales,
    localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
      ...kFallbackDelegates,
    ],
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(context)
          .copyWith(textScaler: TextScaler.linear(textScale)),
      child: child!,
    ),
    home: home,
  );
}

void _phone(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

/// Every piece of text on screen, icons excluded, is at least 12 sp before
/// the system text scale is applied.
void _expectNoTinyText(WidgetTester tester, String where) {
  final tiny = <String>[];
  for (final element in find.byType(RichText).evaluate()) {
    final RichText widget = element.widget as RichText;
    widget.text.visitChildren((span) {
      final style = span.style;
      final size = style?.fontSize;
      final isIcon = style?.fontFamily == 'MaterialIcons';
      if (!isIcon && size != null && size < 12) {
        final text = span is TextSpan ? span.text ?? '' : '';
        tiny.add(
            '${size}sp "${text.length > 40 ? text.substring(0, 40) : text}"');
      }
      return true;
    });
  }
  expect(tiny, isEmpty, reason: '$where has text below 12 sp: $tiny');
}

RichText _richTextWith(WidgetTester tester, String text, {Finder? within}) {
  final finder = find.descendant(
    of: within ?? find.byType(MaterialApp),
    matching: find.byWidgetPredicate(
      (w) => w is RichText && w.text.toPlainText() == text,
    ),
  );
  expect(finder, findsOneWidget, reason: 'expected exactly one "$text"');
  return tester.widget<RichText>(finder);
}

void main() {
  group('font floor (FFR-11)', () {
    testWidgets('Home, with an SOS in history', (tester) async {
      _phone(tester, const Size(390, 844));
      await tester.pumpWidget(_host(HomePage(
        service: _FakeSosService(<SosRecord>[_openSos()]),
        identity: _identity,
        feeds: _FakeVentureFeeds(),
        location: _FakeLocationService(),
        squall: _watch,
      )));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      _expectNoTinyText(tester, 'Home');
      await tester.pumpWidget(const SizedBox());
    });

    testWidgets('At sea, with an SOS, a squall watch and an old map',
        (tester) async {
      _phone(tester, const Size(390, 844));
      await tester.pumpWidget(_host(VenturePage(
        identity: _identity,
        sos: _FakeSosService(<SosRecord>[_openSos()]),
        feeds: _FakeVentureFeeds(),
        location: _FakeLocationService(),
        squall: _watch,
      )));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      _expectNoTinyText(tester, 'At sea');
      await tester.pumpWidget(const SizedBox());
    });

    testWidgets('SOS countdown and post-SOS sheet', (tester) async {
      _phone(tester, const Size(390, 844));
      await tester.pumpWidget(
          _host(const SosCountdownScreen(duration: Duration(seconds: 5))));
      await tester.pump();
      _expectNoTinyText(tester, 'SOS countdown');

      final record =
          ValueNotifier<SosRecord>(_openSos(state: DeliveryState.saved));
      addTearDown(record.dispose);
      await tester.pumpWidget(_host(Scaffold(
        body: SingleChildScrollView(
          child: EmergencyDetailsSheet(
            record: record,
            onSubmitNote: (_) async {},
            onStandDown: () async {},
          ),
        ),
      )));
      await tester.pump();
      _expectNoTinyText(tester, 'post-SOS sheet');
      await tester.pumpWidget(const SizedBox());
    });

    testWidgets('status cards and banners', (tester) async {
      _phone(tester, const Size(390, 844));
      await tester.pumpWidget(_host(Scaffold(
        body: SingleChildScrollView(
          child: Column(
            children: <Widget>[
              DeliveryStateTile(record: _openSos()),
              BuoyStatusCard(
                status: BuoyStatus(
                  buoyId: 'BUOY01',
                  uplink: false,
                  queueDepth: 2,
                  clients: 1,
                  observedAt: DateTime.now().toUtc(),
                ),
              ),
              const SquallBanner(watch: _watch),
            ],
          ),
        ),
      )));
      await tester.pump();
      _expectNoTinyText(tester, 'status cards and banners');
      await tester.pumpWidget(const SizedBox());
    });
  });

  group('large text on a small phone (FFR-04)', () {
    for (final brightness in Brightness.values) {
      testWidgets('Home shows the SOS status card in full ($brightness)',
          (tester) async {
        _phone(tester, const Size(360, 640));
        final t = await AppLocalizations.delegate.load(const Locale('en'));
        await tester.pumpWidget(_host(
          HomePage(
            service: _FakeSosService(<SosRecord>[_openSos()]),
            identity: _identity,
            feeds: _FakeVentureFeeds(),
            location: _FakeLocationService(),
          ),
          textScale: 2,
          brightness: brightness,
        ));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));

        expect(tester.takeException(), isNull);
        final card = find.byType(SosStatusCard);
        expect(card, findsOneWidget);

        const situation = FisherSosSituation.podHasIt;
        final title = _richTextWith(tester, situation.title(t), within: card);
        expect(title.text.style?.fontSize, greaterThanOrEqualTo(20));

        final description =
            _richTextWith(tester, situation.description(t), within: card);
        expect(description.maxLines, isNull,
            reason: 'the what-to-do line wraps instead of being cut');
        expect(description.overflow, isNot(TextOverflow.ellipsis));

        await tester.pumpWidget(const SizedBox());
      });
    }

    testWidgets('countdown and post-SOS sheet fit at 200%', (tester) async {
      _phone(tester, const Size(360, 640));
      await tester.pumpWidget(_host(
        const SosCountdownScreen(duration: Duration(seconds: 5)),
        textScale: 2,
      ));
      await tester.pump();
      expect(tester.takeException(), isNull);

      final record =
          ValueNotifier<SosRecord>(_openSos(state: DeliveryState.saved));
      addTearDown(record.dispose);
      await tester.pumpWidget(_host(
        Scaffold(
          body: SingleChildScrollView(
            child: EmergencyDetailsSheet(
              record: record,
              onSubmitNote: (_) async {},
              onStandDown: () async {},
            ),
          ),
        ),
        textScale: 2,
      ));
      await tester.pump();
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    });
  });

  group('labelled dock (FFR-08)', () {
    testWidgets('four visible labels, 12 sp or more, 4.5:1 on the dock',
        (tester) async {
      _phone(tester, const Size(390, 844));
      final t = await AppLocalizations.delegate.load(const Locale('en'));
      await tester.pumpWidget(_host(AppShell(
        identity: _identity,
        sos: _FakeSosService(const <SosRecord>[]),
        feeds: _FakeVentureFeeds(),
        location: _FakeLocationService(),
        identityStore: IdentityStore(AppDatabase()),
        themeMode: ThemeMode.light,
        onThemeModeChanged: (_) {},
        onLogout: () {},
        onIdentityUpdated: (_) {},
      )));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      for (final label in <String>[
        t.navHome,
        t.navVenture,
        t.navAdvisories,
        t.navProfile,
      ]) {
        final text = _richTextWith(tester, label);
        final style = text.text.style;
        expect(style?.fontSize, greaterThanOrEqualTo(12), reason: label);
        final color = style?.color;
        expect(color, isNotNull, reason: label);
        final lc = color!.computeLuminance();
        final ls = AqPalette.light.surface.computeLuminance();
        final ratio = (ls > lc ? ls + 0.05 : lc + 0.05) /
            (ls > lc ? lc + 0.05 : ls + 0.05);
        expect(ratio, greaterThanOrEqualTo(4.5), reason: label);
      }

      await tester.pumpWidget(const SizedBox());
    });
  });
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

  @override
  Future<BuoyStatus?> pollBuoy() async => null;
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
  Future<SquallWatch> squall() async => _watch;
}
