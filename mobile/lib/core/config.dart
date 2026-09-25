import 'endpoint_guard.dart';

class AqOneConfig {
  const AqOneConfig._();

  /// Verified against the checked-in firmware
  /// (`firmware/buoy/AqOneBuoy/AqOneBuoy.ino`: `WiFi.softAP(...)` with no
  /// custom AP config, which defaults to `192.168.4.1`) — see
  /// `docs/21_WEEK1_CONTRACT_FIXTURES.md`. Previously `10.0.0.1`, which does
  /// not match the buoy's actual AP address and made every `/v1/status` and
  /// `/v1/sos` call fail outright while a phone was joined to the buoy's
  /// WiFi.
  static const String buoyBaseUrl = String.fromEnvironment(
    'BUOY_BASE_URL',
    defaultValue: 'http://192.168.4.1',
  );

  /// The buoy's chat WebSocket, a separate server from the HTTP API above
  /// (`WebSocketsServer ws(WS_PORT)` with `WS_PORT = 81` in the firmware; no
  /// path routing, so there is no `/ws` suffix). Single source of truth for
  /// `ChatService` so the buoy's HTTP host and its WS host cannot drift apart
  /// again.
  static String buoyWsUrl(String host) => 'ws://$host:81';

  /// The deployed Render service. Override at build time with
  /// `--dart-define=BACKEND_BASE_URL=https://...` when pointing a build at a
  /// different environment.
  ///
  /// Railway (`aqone-backend.up.railway.app`, then
  /// `incredible-liberation-production-aad7.up.railway.app`, then
  /// `aihackathon2026aquanonsaqone-production.up.railway.app`) answered
  /// `/healthz` with Railway's own 404 "Application not found" - those
  /// services no longer exist. The live deployment, confirmed against
  /// `/health/ready` and matching `docs/05_PUBLIC_API.md`, is
  /// `aqone-backend.onrender.com`.
  static const String backendBaseUrl = String.fromEnvironment(
    'BACKEND_BASE_URL',
    defaultValue: 'https://aqone-backend.onrender.com',
  );

  static const bool pitchMode = bool.fromEnvironment(
    'PITCH_MODE',
    defaultValue: false,
  );

  static const int protocolVersion = 1;

  static const Duration buoyTimeout = Duration(seconds: 6);
  static const Duration backendTimeout = Duration(seconds: 12);
  static const Duration buoyPollInterval = Duration(seconds: 10);
  static const Duration outboxRetryInterval = Duration(seconds: 20);
  /// How often the app asks the backend what happened to an outstanding SOS.
  ///
  /// Two minutes was fine when this only reconciled delivery bookkeeping. Now
  /// it also carries the responder's ETA, and two minutes is far too long to
  /// leave someone wondering whether anybody heard them.
  ///
  /// The cost of the faster rate is near zero: reconcile() opens with a local
  /// query and returns immediately when nothing is outstanding, so an idle
  /// handset does one cheap SQLite read per tick and never touches the network.
  static const Duration reconcileInterval = Duration(seconds: 15);
  static const Duration locationTimeout = Duration(seconds: 8);

  /// How often Venture refreshes buoys and hazard feeds while it is visible.
  static const Duration hazardPollInterval = Duration(seconds: 30);

  /// How often Home refreshes the MDRRMO-set sea condition.
  static const Duration seaConditionInterval = Duration(seconds: 18);

  // --- Venture map ---------------------------------------------------------

  /// Map-only starting point near Aklan.
  ///
  /// This is where the camera sits before a GPS fix exists. It must never be
  /// submitted as the user's position - an SOS carrying a default coordinate
  /// would send responders to the wrong place.
  static const double defaultMapLat = 11.7000;
  static const double defaultMapLon = 122.4400;
  static const double defaultMapZoom = 11.5;
  static const double locatedMapZoom = 14.5;

  /// Fixed coordinates used for the ashore weather reading.
  static const double aklanLat = 11.6892;
  static const double aklanLon = 122.3667;

  static const String osmTileUrl =
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

  /// Required by the OSM tile usage policy, and currently missing from the
  /// source project. Rendered as a visible attribution on the map.
  static const String osmAttribution = '© OpenStreetMap contributors';

  /// Sent on every basemap tile request.
  ///
  /// The OSM tile policy §3.4 requires a distinct, stable User-Agent naming
  /// the app with a contact, and says traffic using a library's generic
  /// default "will be blocked" without notice. Keep the product name stable
  /// across releases and bump only the version.
  static const String tileUserAgent =
      'AqOne/0.1 (+https://github.com/Aquanons; municipal fisher safety, '
      'New Washington, Aklan)';

  /// Bundled offline basemap for the municipal waters.
  ///
  /// Absent until someone generates it - see docs/24_OFFLINE_MAP.md, which
  /// documents the self-hosted render that produces this file legally. The
  /// app checks for it at startup and carries on without it, so a missing
  /// pack is a degraded map rather than a broken one.
  static const String offlineMapAsset = 'assets/map/new_washington.mbtiles';

  static const String openMeteoBase = 'https://api.open-meteo.com/v1/forecast';

  /// Wave model, a different host from the atmospheric one above. Free and
  /// keyless like the main endpoint.
  ///
  /// This stays in use even after PAGASA is wired in: PAGASA's TenDay API is
  /// a land forecast keyed by municipality and carries no sea state, so it
  /// replaces the atmospheric half only.
  static const String openMeteoMarineBase =
      'https://marine-api.open-meteo.com/v1/marine';

  /// Wind above this is treated as unsafe by the client-side heuristic.
  static const double unsafeWindKph = 30;

  // --- Forecast ------------------------------------------------------------

  /// Days shown in the Home forecast strip.
  ///
  /// Seven is what the strip is designed for, but WMO codes past about day 4
  /// are weak. [forecastConfidentDays] is where the chips start being drawn
  /// as a lower-confidence outlook rather than a forecast.
  static const int forecastDays = 7;
  static const int forecastConfidentDays = 3;

  /// Daily data does not change minute to minute, and the battery has to last
  /// a fishing trip. Deliberately far slower than [hazardPollInterval].
  static const Duration forecastRefreshInterval = Duration(minutes: 30);

  /// Marine grid cells are open water. Sampling the municipal centre - which
  /// is on land - returns nulls, so the wave request is nudged offshore.
  /// Roughly 8 km south-west of the Aklan reading point, into Sibuyan Sea
  /// water rather than over Panay.
  static const double marineSampleLat = 11.7450;
  static const double marineSampleLon = 122.3200;

  /// PAGASA keys its forecasts by municipality rather than coordinates, so
  /// the provider interface carries one from the start. Swapping this for a
  /// value derived from the user's fix is a later change.
  static const String defaultMunicipality = 'Kalibo, Aklan';

  // Risk thresholds for the device-side fallback score.
  //
  // PROVISIONAL. These were picked to be defensible, not because anyone who
  // fishes these waters has signed off on them. They decide whether a chip
  // reads green or red, so they should be reviewed by the MDRRMO or an
  // experienced fisherman before this is put in front of real users.
  static const double cautionGustKph = 30;
  static const double dangerGustKph = 50;
  static const double cautionWaveM = 1.5;
  static const double dangerWaveM = 2.5;
  static const double cautionPrecipMm = 20;
  static const double dangerPrecipMm = 50;

  // --- Backend paths -------------------------------------------------------

  static const String buoysPath = '/api/public/buoys';
  static const String waveAlertsPath = '/api/public/alerts/waves';
  static const String capsizingAlertsPath = '/api/public/alerts/capsizing';
  static const String seaConditionPath = '/api/sea-condition';
  static const String publicSeaConditionPath = '/api/public/sea-condition';
  static const String advisoriesPath = '/api/advisories?status=Published';
  static const String publicAdvisoriesPath = '/api/public/advisories';

  /// Fish-hotspot surface (§6.2): binned cells scored by a model over
  /// environmental data.
  ///
  /// Not implemented yet - Phase 3 in the delivery plan. The client renders
  /// the layer only when this answers, so switching the model on is a backend
  /// deploy rather than a handset release. Contract in docs/05_PUBLIC_API.md.
  static const String publicHotspotsPath = '/api/public/hotspots';

  /// How often Venture refreshes the hotspot surface. A model that runs daily
  /// does not need a 30-second poll; this only exists so a surface published
  /// mid-trip appears without a restart.
  static const Duration hotspotRefreshInterval = Duration(minutes: 15);

  /// Squall nowcast (AI #1). Public because the handset has no account - see
  /// backend/app/api/public.py.
  static const String publicSquallPath = '/api/public/squall';

  /// Fused daily outlook: buoy sensor telemetry combined with a weather
  /// provider, scored server-side. Not implemented yet - the client falls
  /// back to Open-Meteo plus its own heuristic whenever this 404s, so it can
  /// be switched on without a handset release. Contract is documented on
  /// DailyOutlook.fromAqOne.
  static const String publicForecastPath = '/api/public/forecast';

  /// How often the handset re-checks for a squall. Short enough that the
  /// warning is useful (the model forecasts tens of minutes of lead time),
  /// long enough not to drain a battery at sea.
  static const Duration squallPollInterval = Duration(seconds: 60);

  static const int maxVesselIdLength = 32;
  static const int maxBoatBytes = 32;
  static const int maxNoteBytes = 64;

  static const int maxSpotNoteLength = 240;
  static const int maxNameLength = 64;
  static const int maxPhoneLength = 20;
  static const int minLicenseLength = 5;
  static const int maxLicenseLength = 24;

  static void validateEndpoints() {
    EndpointGuard.validateStaticConfig(
      buoyBaseUrl: buoyBaseUrl,
      backendBaseUrl: backendBaseUrl,
      openMeteoBase: openMeteoBase,
      openMeteoMarineBase: openMeteoMarineBase,
      osmTileUrl: osmTileUrl,
    );
  }
}
