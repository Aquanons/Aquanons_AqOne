import 'package:aqone/core/l10n_fallback.dart';
import 'package:aqone/data/app_database.dart';
import 'package:aqone/data/identity_store.dart';
import 'package:aqone/data/map_snapshot_store.dart';
import 'package:aqone/data/outbox_store.dart';
import 'package:aqone/l10n/app_localizations.dart';
import 'package:aqone/models/advisory.dart';
import 'package:aqone/models/buoy_contact.dart';
import 'package:aqone/models/daily_outlook.dart';
import 'package:aqone/models/forecast_outlook.dart';
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
import 'package:aqone/ui/widgets/weather_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';

class _TestSosService extends SosService {
  _TestSosService()
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
  @override
  Future<BuoyStatus?> pollBuoy() async => null;
}

class _TestLocationService extends LocationService {
  @override
  Future<Fix?> cachedFixIfPermitted() async => null;
}

class _LifecycleFeeds extends VentureFeeds {
  _LifecycleFeeds()
      : super(
          backend: BackendClient(),
          snapshots: MapSnapshotStore(AppDatabase()),
        );

  int forecastCallCount = 0;

  @override
  Future<ForecastOutlook?> forecastOutlook({
    required double lat,
    required double lon,
    String? municipality,
  }) async {
    forecastCallCount++;
    return ForecastOutlook(
      latitude: lat,
      longitude: lon,
      fetchedAt: DateTime.now(),
      source: 'backend',
      days: const <DailyOutlook>[],
      hours: const <HourlyInterval>[],
    );
  }

  @override
  Future<SeaCondition?> seaCondition() async => null;
  @override
  Future<List<Advisory>?> advisories() async => const <Advisory>[];
  @override
  Future<WeatherSnapshot?> weather({required double lat, required double lon}) async => null;
}

const VesselIdentity _testIdentity = VesselIdentity(
  vesselId: 'test-vessel-1',
  boat: 'Test Boat',
  skipperName: 'Test Skipper',
  phone: '09123456789',
);

void main() {
  List<DailyOutlook> sevenDays() {
    final DateTime start = DateTime.now();
    return List<DailyOutlook>.generate(7, (int i) {
      return DailyOutlook(
        date: DateTime(start.year, start.month, start.day).add(
          Duration(days: i),
        ),
        // Day 3 is the stormy one, so the icon assertion is meaningful.
        weatherCode: i == 3 ? 95 : 0,
        tempMax: 30.0 + i,
        tempMin: 24,
        gustKph: i == 3 ? 55 : 10,
        waveM: i == 3 ? 2.9 : 0.5,
        risk: RiskAssessment(
          level: i == 3 ? RiskLevel.danger : RiskLevel.safe,
          source: RiskSource.device,
          reason: i == 3 ? 'Gusts 55 km/h and 2.9 m swell' : 'Calm',
          inputs: const <String>['open-meteo', 'wave'],
        ),
      );
    });
  }

  ForecastOutlook createOutlook({
    required DateTime now,
    DateTime? fetchedAt,
    List<HourlyInterval>? hours,
    List<DailyOutlook>? days,
    String source = 'backend',
  }) {
    final effectiveFetchedAt = fetchedAt ?? now;
    final defaultDays = days ??
        List<DailyOutlook>.generate(7, (int i) {
          final d = DateTime(now.year, now.month, now.day).add(Duration(days: i));
          return DailyOutlook(
            date: d,
            weatherCode: 0,
            risk: const RiskAssessment(
              level: RiskLevel.safe,
              source: RiskSource.device,
            ),
          );
        });
    final defaultHours = hours ??
        List<HourlyInterval>.generate(72, (int i) {
          final t = now.add(Duration(hours: i + 1));
          final isDeteriorated = i + 1 == 31;
          return HourlyInterval(
            time: t,
            weatherCode: isDeteriorated ? 95 : 0,
            windKph: isDeteriorated ? 35.0 : 10.0,
            gustKph: isDeteriorated ? 55.0 : 15.0,
            waveM: isDeteriorated ? 2.6 : 0.5,
          );
        });

    return ForecastOutlook(
      latitude: 11.5,
      longitude: 122.5,
      fetchedAt: effectiveFetchedAt,
      source: source,
      days: defaultDays,
      hours: defaultHours,
    );
  }

  Widget wrap(
    Widget child, {
    Locale locale = const Locale('en'),
    ThemeData? theme,
    Size? size,
    TextScaler? textScaler,
    bool isFullPage = false,
  }) {
    Widget content = child;
    if (textScaler != null) {
      content = MediaQuery(
        data: MediaQueryData(
          size: size ?? const Size(390, 844),
          textScaler: textScaler,
        ),
        child: content,
      );
    }
    if (size != null && !isFullPage) {
      content = SizedBox(
        width: size.width,
        child: content,
      );
    }
    return MaterialApp(
      locale: locale,
      theme: theme ?? ThemeData.light(),
      supportedLocales: kSupportedLocales,
      localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        ...kFallbackDelegates,
      ],
      home: isFullPage ? content : Scaffold(body: SingleChildScrollView(child: content)),
    );
  }

  testWidgets('renders one chip per forecast day', (WidgetTester tester) async {
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(
            temperature: 30,
            windSpeed: 8,
            weatherCode: 0,
          ),
          isLoading: false,
          onRetry: () {},
          forecast: sevenDays(),
        ),
      ),
    );

    expect(find.text('7-day outlook'), findsOneWidget);
    expect(find.text('Today'), findsOneWidget);
    // Today plus six named weekdays.
    expect(find.byIcon(Icons.check_circle_rounded), findsNWidgets(6));
    expect(find.byIcon(Icons.dangerous_rounded), findsOneWidget);
    expect(find.byIcon(Icons.thunderstorm_rounded), findsOneWidget);
  });

  testWidgets('says so when sea state was not available', (
    WidgetTester tester,
  ) async {
    final List<DailyOutlook> noWaves = sevenDays()
        .map(
          (DailyOutlook d) => DailyOutlook(
            date: d.date,
            weatherCode: d.weatherCode,
            tempMax: d.tempMax,
            risk: RiskAssessment(
              level: d.risk.level,
              source: RiskSource.device,
              inputs: const <String>['open-meteo'],
            ),
          ),
        )
        .toList(growable: false);

    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(
            temperature: 30,
            windSpeed: 8,
            weatherCode: 0,
          ),
          isLoading: false,
          onRetry: () {},
          forecast: noWaves,
        ),
      ),
    );

    expect(
      find.textContaining('sea state not available'),
      findsOneWidget,
    );
  });

  testWidgets('stamps a cached strip with when it was fetched', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: null,
          isLoading: false,
          onRetry: () {},
          forecast: sevenDays(),
          forecastAge: DateTime(2026, 8, 16, 6, 12),
        ),
      ),
    );

    expect(find.text('as of 6:12 AM'), findsOneWidget);
    // No live current-conditions reading, so the retry affordance still shows.
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('builds in Aklanon without throwing', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(
            temperature: 30,
            windSpeed: 8,
            weatherCode: 0,
          ),
          isLoading: false,
          onRetry: () {},
          forecast: sevenDays(),
        ),
        locale: const Locale('akl'),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.byIcon(Icons.dangerous_rounded), findsOneWidget);

    // Plan 70 AKL-06: intl has no Aklanon data, and the Spanish-derived day
    // names are the same words in Tagalog, so Aklanon chips use `fil`.
    final DateTime tomorrow = sevenDays()[1].date;
    expect(find.text(DateFormat('E', 'fil').format(tomorrow)), findsOneWidget);
    expect(find.text(DateFormat('E', 'en').format(tomorrow)), findsNothing);
  });

  testWidgets('omits the strip entirely when there is no forecast', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(
            temperature: 30,
            windSpeed: 8,
            weatherCode: 0,
          ),
          isLoading: false,
          onRetry: () {},
        ),
      ),
    );

    expect(find.text('7-day outlook'), findsNothing);
  });

  testWidgets('renders fishing weather window with positive countdown and disclaimer', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final outlook = createOutlook(now: now);
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(
            temperature: 30,
            windSpeed: 8,
            weatherCode: 0,
          ),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlook,
          now: now,
        ),
      ),
    );

    expect(find.text('Fishing weather window'), findsOneWidget);
    expect(find.text('Conditions may worsen in about 1 day 6 hours'), findsOneWidget);
    expect(find.text('Lower forecast risk'), findsOneWidget);
    expect(find.textContaining('stronger winds'), findsOneWidget);
    expect(find.text('Does not include return travel or preparation time.'), findsOneWidget);
    expect(find.textContaining('Forecast location: Aklan'), findsOneWidget);
  });

  testWidgets('renders under one hour countdown when deterioration is within 60 minutes', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final outlook = createOutlook(
      now: now,
      hours: <HourlyInterval>[
        HourlyInterval(
          time: DateTime(2026, 9, 13, 10, 0),
          weatherCode: 0,
          windKph: 10,
          gustKph: 15,
          waveM: 0.5,
        ),
        HourlyInterval(
          time: DateTime(2026, 9, 13, 11, 0),
          weatherCode: 0,
          windKph: 10,
          gustKph: 15,
          waveM: 0.5,
        ),
        HourlyInterval(
          time: DateTime(2026, 9, 13, 11, 45),
          weatherCode: 95,
          windKph: 35,
          gustKph: 55,
          waveM: 2.5,
        ),
      ],
    );

    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlook,
          now: now,
        ),
      ),
    );

    expect(find.text('Conditions may worsen in about within an hour'), findsOneWidget);
  });

  testWidgets('renders days only and hours only plural durations correctly', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    // 48 hours = 2 days
    final hours48 = List<HourlyInterval>.generate(50, (i) {
      final isAdverse = i + 1 == 49;
      return HourlyInterval(
        time: now.add(Duration(hours: i + 1)),
        weatherCode: isAdverse ? 95 : 0,
        windKph: isAdverse ? 40 : 10,
        gustKph: isAdverse ? 55 : 15,
        waveM: isAdverse ? 2.6 : 0.5,
      );
    });
    final outlookDays = createOutlook(now: now, hours: hours48);

    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlookDays,
          now: now,
        ),
      ),
    );
    expect(find.text('Conditions may worsen in about 2 days'), findsOneWidget);

    // 5 hours only:
    final hours5 = List<HourlyInterval>.generate(10, (i) {
      final isAdverse = i + 1 == 6;
      return HourlyInterval(
        time: now.add(Duration(hours: i + 1)),
        weatherCode: isAdverse ? 95 : 0,
        windKph: isAdverse ? 40 : 10,
        gustKph: isAdverse ? 55 : 15,
        waveM: isAdverse ? 2.6 : 0.5,
      );
    });
    final outlookHours = createOutlook(now: now, hours: hours5);

    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlookHours,
          now: now,
        ),
      ),
    );
    expect(find.text('Conditions may worsen in about 5 hours'), findsOneWidget);
  });

  testWidgets('renders caution and danger states with warning text and no positive countdown', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final cautionHours = <HourlyInterval>[
      HourlyInterval(
        time: DateTime(2026, 9, 13, 11, 0),
        weatherCode: 0,
        windKph: 25,
        gustKph: 35,
        waveM: 0.8,
      ),
    ];
    final cautionOutlook = createOutlook(now: now, hours: cautionHours);

    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: cautionOutlook,
          now: now,
        ),
      ),
    );
    expect(find.text('Conditions need caution now'), findsOneWidget);
    expect(find.textContaining('stronger winds. Prepare and check advisories.'), findsOneWidget);
    expect(find.textContaining('Conditions may worsen in about'), findsNothing);

    final dangerHours = <HourlyInterval>[
      HourlyInterval(
        time: DateTime(2026, 9, 13, 11, 0),
        weatherCode: 95,
        windKph: 15,
        gustKph: 20,
        waveM: 1.0,
      ),
    ];
    final dangerOutlook = createOutlook(now: now, hours: dangerHours);

    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: dangerOutlook,
          now: now,
        ),
      ),
    );
    expect(find.text('High-risk conditions now'), findsOneWidget);
    expect(find.textContaining('thunderstorms. Follow MDRRMO guidance.'), findsOneWidget);
    expect(find.textContaining('Conditions may worsen in about'), findsNothing);
  });

  testWidgets('official warnings and squall alerts override forecast', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final greenOutlook = createOutlook(now: now);

    // Official not advised:
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: greenOutlook,
          seaCondition: const SeaCondition(status: SeaStatus.notAdvised),
          now: now,
        ),
      ),
    );
    expect(find.text('High-risk conditions now'), findsOneWidget);
    expect(find.textContaining('official warning: not advised. Follow MDRRMO guidance.'), findsOneWidget);

    // Official caution:
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: greenOutlook,
          seaCondition: const SeaCondition(status: SeaStatus.caution),
          now: now,
        ),
      ),
    );
    expect(find.text('Conditions need caution now'), findsOneWidget);
    expect(find.textContaining('official caution. Prepare and check advisories.'), findsOneWidget);

    // Squall return now:
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: greenOutlook,
          squall: const SquallWatch(level: SquallLevel.returnNow, returnNow: true),
          now: now,
        ),
      ),
    );
    expect(find.text('High-risk conditions now'), findsOneWidget);
    expect(find.textContaining('squall danger: return now. Follow MDRRMO guidance.'), findsOneWidget);
  });

  testWidgets('renders no worsening forecast when entire horizon is clear', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final calmHours = List<HourlyInterval>.generate(72, (i) {
      return HourlyInterval(
        time: now.add(Duration(hours: i + 1)),
        weatherCode: 0,
        windKph: 10,
        gustKph: 15,
        waveM: 0.5,
      );
    });
    final outlook = createOutlook(now: now, hours: calmHours);

    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlook,
          now: now,
        ),
      ),
    );
    expect(find.textContaining('No worsening forecast through'), findsOneWidget);
    expect(find.text('Near-term forecast remains low risk.'), findsOneWidget);
  });

  testWidgets('renders unavailable states and provides retry action', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    bool retried = false;

    // Stale refresh (> 30 min old):
    final staleOutlook = createOutlook(
      now: now,
      fetchedAt: now.subtract(const Duration(minutes: 35)),
    );
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () => retried = true,
          forecastOutlook: staleOutlook,
          now: now,
        ),
      ),
    );
    expect(find.text('Forecast refresh needed'), findsOneWidget);
    expect(find.text('Forecast is over 30 minutes old. Tap to refresh.'), findsOneWidget);

    await tester.tap(find.text('Retry').first);
    expect(retried, isTrue);

    // Expired cache (> 12 hours old):
    final expiredOutlook = createOutlook(
      now: now,
      fetchedAt: now.subtract(const Duration(hours: 13)),
    );
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: expiredOutlook,
          now: now,
        ),
      ),
    );
    expect(find.text('Forecast expired'), findsOneWidget);

    // Clock skew:
    final skewOutlook = createOutlook(
      now: now,
      fetchedAt: now.add(const Duration(minutes: 5)),
    );
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: skewOutlook,
          now: now,
        ),
      ),
    );
    expect(find.text('Forecast timestamp unavailable'), findsOneWidget);
  });

  testWidgets('renders in narrow 360x640 layout with large text and dark theme without overflow', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final outlook = createOutlook(now: now);
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlook,
          now: now,
        ),
        size: const Size(360, 640),
        textScaler: const TextScaler.linear(1.5),
        theme: ThemeData.dark(),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.text('Fishing weather window'), findsOneWidget);
  });

  testWidgets('renders window in Aklanon and Tagalog without error', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final outlook = createOutlook(now: now);

    for (final locale in const [Locale('akl'), Locale('fil')]) {
      await tester.pumpWidget(
        wrap(
          WeatherCard(
            snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
            isLoading: false,
            onRetry: () {},
            forecastOutlook: outlook,
            now: now,
          ),
          locale: locale,
        ),
      );

      expect(tester.takeException(), isNull);
      expect(
        find.text(lookupAppLocalizations(locale).weatherWindowTitle),
        findsOneWidget,
      );
    }
  });

  testWidgets('HomePage minute timer and app resume re-renders without fetching weather every minute', (WidgetTester tester) async {
    final feeds = _LifecycleFeeds();
    final sosService = _TestSosService();
    final locationService = _TestLocationService();

    await tester.pumpWidget(
      wrap(
        HomePage(
          service: sosService,
          identity: _testIdentity,
          feeds: feeds,
          location: locationService,
        ),
        isFullPage: true,
      ),
    );
    await tester.pump();
    final int initialCalls = feeds.forecastCallCount;

    // Advance 1 minute: minute timer ticks and calls setState, but does not fetch weather
    await tester.pump(const Duration(minutes: 1));
    expect(feeds.forecastCallCount, equals(initialCalls));

    // App resumed: calls setState, but does not fetch weather
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(feeds.forecastCallCount, equals(initialCalls));

    // Pump empty widget to dispose HomePage and cancel minute timer
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Finding 1 (UI): displays window summary when forecast is null but official notAdvised is present', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: null,
          seaCondition: const SeaCondition(status: SeaStatus.notAdvised),
          now: now,
        ),
      ),
    );

    expect(find.text('Fishing weather window'), findsOneWidget);
    expect(find.text('High-risk conditions now'), findsOneWidget);
    expect(find.textContaining('official warning: not advised'), findsOneWidget);
  });

  testWidgets('Finding 6 (UI): displays forecast coordinates in footer', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final outlook = createOutlook(now: now);
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlook,
          now: now,
          locationLabel: 'Panay Offshore',
        ),
      ),
    );

    expect(find.textContaining('11.50°N, 122.50°E'), findsOneWidget);
  });

  testWidgets('Finding 8 (UI): renders upcoming risk tier in subtitle alongside onset', (WidgetTester tester) async {
    final now = DateTime(2026, 9, 13, 10, 0);
    final hours = List<HourlyInterval>.generate(12, (int i) {
      final t = now.add(Duration(hours: i + 1));
      final isDeteriorated = i + 1 == 5;
      return HourlyInterval(
        time: t,
        weatherCode: isDeteriorated ? 95 : 0,
        gustKph: isDeteriorated ? 55.0 : 15.0,
        waveM: isDeteriorated ? 2.6 : 0.5,
      );
    });
    final outlook = createOutlook(now: now, hours: hours);
    await tester.pumpWidget(
      wrap(
        WeatherCard(
          snapshot: const WeatherSnapshot(temperature: 30, windSpeed: 8, weatherCode: 0),
          isLoading: false,
          onRetry: () {},
          forecastOutlook: outlook,
          now: now,
        ),
      ),
    );

    expect(find.text('Fishing weather window'), findsOneWidget);
    expect(find.textContaining('(Dangerous)'), findsOneWidget);
  });
}
