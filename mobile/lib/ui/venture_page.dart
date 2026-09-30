import 'dart:async';
import 'dart:math' as math;

import 'package:aqone/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../core/config.dart';
import '../data/identity_store.dart';
import '../models/buoy_marker.dart';
import '../models/hazard_alert.dart';
import '../models/fisher_sos_situation.dart';
import '../models/nearby_sos.dart';
import '../models/sos_record.dart';
import '../models/weather_snapshot.dart';
import '../services/compass_service.dart';
import '../services/location_service.dart';
import '../services/mbtiles_provider.dart';
import '../services/nearby_alarm.dart';
import '../services/nearby_sos_watcher.dart';
import '../services/sos_alarm.dart';
import '../services/sos_service.dart';
import '../services/tile_cache.dart';
import '../services/venture_feeds.dart';
import 'chathubb.dart';
import 'sos_flow.dart';
import 'widgets/action_pill.dart';
import 'widgets/compass_dial.dart';
import 'widgets/offline_map_banner.dart';

const Color _brandPrimary = Color(0xFF0F69C9);
const Color _brandDeep = Color(0xFF0B4C8C);
const Color _accentDark = Color(0xFF38BDF8);
const Color _surfaceDark = Color(0xFF1E293B);
const Color _canvasDark = Color(0xFF0F172A);
const Color _danger = Color(0xFFDC2626);
const Color _success = Color(0xFF16A34A);

/// How long a fisher has to slide-to-cancel before the SOS actually sends.
/// Short enough to still read as "immediate" - the button does not gate the
/// alert behind typing a note - but long enough that a pocket tap can be
/// caught before anything reaches the MDRRMO.
const Duration _sosCountdown = Duration(seconds: 4);

/// The at-sea operational screen: map, conditions and SOS.
///
/// Ported from the source project's Venture mode, with two deliberate
/// departures:
///   * writes go through the offline outbox instead of straight to HTTP, so
///     an SOS raised out of range is queued rather than lost; and
///   * SOS captures a fresh GPS fix at submission time rather than reusing
///     the map's cached position.
class VenturePage extends StatefulWidget {
  const VenturePage({
    super.key,
    required this.identity,
    required this.sos,
    required this.feeds,
    required this.location,
    this.bottomInset = 0,
    this.sosAlarm,
    this.nearbyAlarm,
    this.nearby,
    this.targetLocation,
  });

  final VesselIdentity identity;
  final SosService sos;
  final VentureFeeds feeds;
  final LocationService location;
  final SosAlarm? sosAlarm;
  final NearbyAlarm? nearbyAlarm;
  final NearbySosWatcher? nearby;
  final LatLng? targetLocation;

  /// Space reserved for the shell's floating dock. The map stays full-bleed
  /// behind it; only the controls are lifted clear so they never get covered.
  final double bottomInset;

  @override
  State<VenturePage> createState() => _VenturePageState();
}

class _VenturePageState extends State<VenturePage> {
  final MapController _mapController = MapController();

  final RequestGuard _weatherGuard = RequestGuard();
  final RequestGuard _buoyGuard = RequestGuard();
  final RequestGuard _waveGuard = RequestGuard();
  final RequestGuard _capsizeGuard = RequestGuard();
  StreamSubscription<void>? _sosSub;
  Timer? _pollTimer;

  double _rotation = 0;

  /// Basemap tiles the fisherman has already looked at, kept on disk.
  ///
  /// Required by the OSM tile policy rather than optional - see TileCache.
  /// Only tiles that were actually drawn are stored; nothing is pre-fetched.
  final TileCache _tiles = TileCache();

  /// Bundled pack first, disk cache second, network last. Null until the
  /// chain is built, and the map simply renders from the network until then -
  /// one frame, and never a blocking spinner over a safety screen.
  TileProvider? _tileProvider;

  final CompassService _compass = CompassService();
  StreamSubscription<CompassReading>? _compassSub;

  /// Null until the magnetometer produces a sample. Stays null forever on
  /// hardware without one (emulators, web), which is what makes the dial
  /// render in its greyed north-up state instead of pretending.
  double? _heading;
  bool _compassNeedsCalibration = false;

  LatLng? _userLocation;
  bool _isLocating = false;

  WeatherSnapshot? _weather;
  bool _weatherFailed = false;
  bool _safetyDialogShown = false;

  List<BuoyMarker> _buoys = const <BuoyMarker>[];

  /// When each cached feed was last fetched. Drives the offline banner, and
  /// is refreshed after every poll rather than on a timer of its own so it
  /// can never disagree with what is on the map.
  Map<String, DateTime> _snapshotAges = const <String, DateTime>{};
  final Map<HazardKind, List<HazardAlert>> _hazards =
      <HazardKind, List<HazardAlert>>{};
  final Set<String> _announcedHazardIds = <String>{};

  SosRecord? _latestSos;
  bool _isSendingSos = false;
  late final SosAlarm _sosAlarm;

  List<NearbySos> _nearby = const <NearbySos>[];

  bool _offlineCollapsed = false;
  bool _sosCollapsed = false;
  bool _nearbyCollapsed = false;
  String? _seenSosId;
  Set<int> _seenBroadcastIds = <int>{};
  Set<String> _seenFeedKeys = <String>{};

  /// True while a hazard dialog is on screen, so a second alert arriving from
  /// the same poll cannot stack a dialog on top of the first.
  bool _hazardDialogOpen = false;
  final List<HazardKind> _hazardQueue = <HazardKind>[];

  @override
  void initState() {
    super.initState();
    _sosAlarm = widget.sosAlarm ?? SosAlarm();
    if (widget.nearby != null) {
      _onNearbyWatcherChanged();
      widget.nearby!.items.addListener(_onNearbyWatcherChanged);
    }
    widget.location.warmUp();
    _sosSub = widget.sos.changes.listen((_) => _refreshSosStatus());
    _initTileProvider();
    _compassSub = _compass.readings.listen((CompassReading reading) {
      if (!mounted) {
        return;
      }
      setState(() {
        _heading = reading.headingDegrees;
        _compassNeedsCalibration = reading.needsCalibration;
      });
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _locate(initial: true);
      _loadBuoys();
      _loadHazards();
      _refreshSosStatus();
      _refreshSnapshotAges();
      _pollTimer = Timer.periodic(AqOneConfig.hazardPollInterval, (_) {
        _loadBuoys();
        _loadHazards();
        _refreshSnapshotAges();
      });
    });
  }

  void _onNearbyWatcherChanged() {
    if (!mounted) return;
    final items = widget.nearby?.items.value ?? const <NearbySos>[];
    final fresh = items.take(4).toList();
    final ids = fresh.map((n) => n.broadcastId).toSet();
    setState(() {
      _nearby = fresh;
      if (ids.length != _seenBroadcastIds.length ||
          !ids.containsAll(_seenBroadcastIds)) {
        _seenBroadcastIds = ids;
        _nearbyCollapsed = false;
      }
    });
  }

  @override
  void didUpdateWidget(VenturePage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.nearby != oldWidget.nearby) {
      oldWidget.nearby?.items.removeListener(_onNearbyWatcherChanged);
      widget.nearby?.items.addListener(_onNearbyWatcherChanged);
      _onNearbyWatcherChanged();
    }
    if (widget.targetLocation != null &&
        widget.targetLocation != oldWidget.targetLocation) {
      _mapController.move(widget.targetLocation!, 14);
    }
  }

  @override
  void dispose() {
    // Polling must stop with the screen. Left running it drains battery and
    // keeps hitting the backend while the phone is in a pocket at sea.
    _pollTimer?.cancel();
    _sosSub?.cancel();
    widget.nearby?.items.removeListener(_onNearbyWatcherChanged);
    // The magnetometer keeps the SoC awake while subscribed, so it must go
    // down with the screen.
    _compassSub?.cancel();
    _tiles.dispose();
    unawaited(_compass.dispose());
    _mapController.dispose();
    unawaited(_sosAlarm.dispose());
    super.dispose();
  }

  Future<void> _refreshSosStatus() async {
    final history = await widget.sos.history();
    if (!mounted) {
      return;
    }
    final latest = history.isEmpty ? null : history.first;
    final latestId = latest?.localId;
    setState(() {
      _latestSos = latest;
      if (latestId != _seenSosId) {
        _seenSosId = latestId;
        _sosCollapsed = false;
      }
    });
  }

  Future<void> _loadWeather(double lat, double lon) async {
    final version = _weatherGuard.begin();
    final snapshot = await widget.feeds.weather(lat: lat, lon: lon);
    if (!mounted || !_weatherGuard.isCurrent(version)) {
      return;
    }
    setState(() {
      _weather = snapshot;
      _weatherFailed = snapshot == null;
    });
    if (!_safetyDialogShown && mounted) {
      _safetyDialogShown = true;
      _showSafetyDialog();
    }
  }

  Future<void> _loadBuoys() async {
    final version = _buoyGuard.begin();
    final buoys = await widget.feeds.buoys();
    if (!mounted || !_buoyGuard.isCurrent(version) || buoys == null) {
      return;
    }
    setState(() => _buoys = buoys);
  }

  Future<void> _initTileProvider() async {
    final TileProvider provider = await buildTileProvider(
      cache: _tiles,
      assetPath: AqOneConfig.offlineMapAsset,
    );
    if (!mounted) {
      return;
    }
    setState(() => _tileProvider = provider);
  }

  Future<void> _refreshSnapshotAges() async {
    final Map<String, DateTime> ages = await widget.feeds.snapshotAges();
    if (!mounted) {
      return;
    }
    final keys = ages.keys.toSet();
    setState(() {
      _snapshotAges = ages;
      if (keys.length != _seenFeedKeys.length ||
          !keys.containsAll(_seenFeedKeys)) {
        _seenFeedKeys = keys;
        _offlineCollapsed = false;
      }
    });
  }

  Future<void> _loadHazards() async {
    for (final kind in HazardKind.values) {
      final guard = kind == HazardKind.wave ? _waveGuard : _capsizeGuard;
      final version = guard.begin();
      final alerts = await widget.feeds.hazards(kind);
      if (!mounted || !guard.isCurrent(version) || alerts == null) {
        continue;
      }
      final fresh = alerts
          .where((alert) => !_announcedHazardIds.contains(alert.id))
          .toList();
      setState(() => _hazards[kind] = alerts);
      if (fresh.isNotEmpty) {
        _announcedHazardIds.addAll(fresh.map((alert) => alert.id));
        _queueHazardDialog(kind);
      }
    }
  }


  Future<void> _locate({bool initial = false}) async {
    setState(() => _isLocating = true);
    final result = await widget.location.locate();
    if (!mounted) {
      return;
    }
    setState(() => _isLocating = false);

    final fix = result.fix;
    if (fix == null) {
      _snack(result.failure.message(AppLocalizations.of(context)));
      // Still show conditions ashore so the screen is not empty.
      if (initial) {
        await _loadWeather(AqOneConfig.aklanLat, AqOneConfig.aklanLon);
      }
      return;
    }

    final point = LatLng(fix.lat, fix.lon);
    setState(() => _userLocation = point);
    _mapController.move(point, AqOneConfig.locatedMapZoom);
    await _loadWeather(fix.lat, fix.lon);
  }

  /// Tapping the SOS pill starts the alarm immediately and a short,
  /// cancellable countdown - it does not wait on any dialog or typed note.
  /// Only once the countdown runs out (uninterrupted) does anything actually
  /// go to the MDRRMO; the "what's wrong?" detail is gathered afterwards,
  /// while the alert is already in flight.
  void _queueHazardDialog(HazardKind kind) {
    if (!_hazardQueue.contains(kind)) {
      _hazardQueue.add(kind);
    }
    _drainHazardQueue();
  }

  Future<void> _drainHazardQueue() async {
    if (_hazardDialogOpen || _hazardQueue.isEmpty || !mounted) {
      return;
    }
    _hazardDialogOpen = true;
    final kind = _hazardQueue.removeAt(0);
    final count = _hazards[kind]?.length ?? 0;
    final t = AppLocalizations.of(context);

    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: <Widget>[
            Icon(kind.icon, color: kind.color, size: 28),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                kind.title(t),
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        content: Text(
          kind.message(t, count),
          style: const TextStyle(fontSize: 14, height: 1.4),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              t.gotItButton,
              style: TextStyle(
                color: kind.color,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );

    _hazardDialogOpen = false;
    if (mounted) {
      unawaited(_drainHazardQueue());
    }
  }

  void _showSafetyDialog() {
    final AppLocalizations t = AppLocalizations.of(context);
    final weather = _weather;
    final bool unsafe = weather?.looksUnsafe ?? true;
    final bool highWind = weather?.hasHighWind ?? false;
    final color = unsafe ? const Color(0xFFD97706) : _success;

    final String titleText;
    if (weather == null) {
      titleText = t.weatherUnavailable;
    } else if (highWind) {
      titleText = t.safetyTitleHighWind;
    } else if (unsafe) {
      titleText = t.safetyTitleConditionForecast(weather.condition.label(t));
    } else {
      titleText = t.safetyTitleCalm;
    }

    final String thresholdNote = highWind
        ? t.weatherSourceNoteThreshold(
            AqOneConfig.unsafeWindKph.toStringAsFixed(0),
          )
        : t.weatherSourceNote;

    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: <Widget>[
            Icon(
              unsafe ? Icons.error_outline_rounded : Icons.check_circle_outline,
              color: color,
              size: 28,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                titleText,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              weather == null
                  ? t.safetyWeatherLoadFailed
                  : t.safetyWeatherSummary(
                      weather.condition.label(t),
                      weather.temperature.toStringAsFixed(0),
                      weather.windSpeed.toStringAsFixed(0),
                    ),
              style: const TextStyle(fontSize: 14, height: 1.4),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF4E0),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                thresholdNote,
                style: const TextStyle(
                  fontSize: 16,
                  color: Color(0xFF8A5A12),
                  height: 1.35,
                ),
              ),
            ),
          ],
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(t.gotItButton),
          ),
        ],
      ),
    );
  }

  void _snack(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  // --- Build --------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Stack(
          children: <Widget>[
            Positioned.fill(child: _buildMap()),
            Positioned(
              top: 12,
              left: 0,
              right: 0,
              child: Column(
                children: <Widget>[
                  _buildWeatherCapsule(isDark),
                  if (_nearby.isNotEmpty) ...<Widget>[
                    const SizedBox(height: 8),
                    _collapsible(
                      collapsed: _nearbyCollapsed,
                      onToggle: () =>
                          setState(() => _nearbyCollapsed = !_nearbyCollapsed),
                      icon: Icons.warning_amber_rounded,
                      color: _danger,
                      child: _buildNearbyHelp(isDark),
                    ),
                  ],
                  const SizedBox(height: 8),
                  if (_offlineStale()) ...<Widget>[
                    _collapsible(
                      collapsed: _offlineCollapsed,
                      onToggle: () => setState(
                          () => _offlineCollapsed = !_offlineCollapsed),
                      icon: Icons.history_rounded,
                      color: const Color(0xFF8A5A12),
                      child: OfflineMapBanner(
                          ages: _snapshotAges, isDark: isDark),
                    ),
                  ],
                  if (_latestSos != null) ...<Widget>[
                    const SizedBox(height: 8),
                    _collapsible(
                      collapsed: _sosCollapsed,
                      onToggle: () =>
                          setState(() => _sosCollapsed = !_sosCollapsed),
                      icon: Icons.mark_email_read_rounded,
                      color: _brandPrimary,
                      child: _buildSosStatus(isDark, _latestSos!),
                    ),
                  ],
                ],
              ),
            ),
            Positioned(
              top: 72,
              bottom: 16 + widget.bottomInset,
              right: 16,
              child: _buildRightControls(isDark),
            ),
            // Opposite corner from the action rail. The compass is a readout,
            // not a control, and stacking it with the buttons made a crowded
            // column crowded by one more thing. Lifted clear of the OSM
            // attribution that runs along the bottom edge.
            //
            // Shares this corner with the hotspot legend, so both live in one
            // column: two independently positioned widgets anchored to the
            // same corner would sit on top of each other the day the hotspot
            // endpoint starts answering.
            Positioned(
              bottom: 26 + widget.bottomInset,
              left: 16,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  _buildCompass(isDark),
                ],
              ),
            ),
            if (_isLocating)
              Positioned(
                top: 90,
                left: 0,
                right: 0,
                child: Center(child: _buildLocatingPill(isDark)),
              ),
            // OSM requires visible attribution. The source project omitted
            // this, which is a licence-compliance gap as well as a courtesy.
            Positioned(
              left: 8,
              bottom: 4 + widget.bottomInset,
              child: _buildAttribution(isDark),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMap() {
    final markers = <Marker>[
      for (final buoy in _buoys)
        Marker(
          point: LatLng(buoy.latitude, buoy.longitude),
          width: 30,
          height: 30,
          alignment: Alignment.center,
          child: Icon(
            Icons.circle_rounded,
            size: 14,
            color: buoy.isActive ? _success : const Color(0xFF9CA3AF),
          ),
        ),
      for (final item in _nearby)
        Marker(
          point: LatLng(item.centerLat, item.centerLon),
          width: 36,
          height: 36,
          alignment: Alignment.center,
          child: Container(
            decoration: BoxDecoration(
              color: _danger,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 2),
            ),
            child: const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 20),
          ),
        ),
      if (_userLocation != null) _buildUserMarker(_userLocation!),
    ];

    final circles = <CircleMarker>[
      for (final buoy in _buoys)
        CircleMarker(
          point: LatLng(buoy.latitude, buoy.longitude),
          radius: buoy.coverageRadiusMeters,
          useRadiusInMeter: true,
          color: _brandPrimary.withValues(alpha: 0.08),
          borderColor: _brandPrimary.withValues(alpha: 0.25),
          borderStrokeWidth: 1.5,
        ),
    ];

    return FlutterMap(
      mapController: _mapController,
      options: MapOptions(
        // Camera-only default. Never submitted as the user's position.
        initialCenter: widget.targetLocation ??
            _userLocation ??
            const LatLng(AqOneConfig.defaultMapLat, AqOneConfig.defaultMapLon),
        initialZoom: 12.8,
        minZoom: 3,
        maxZoom: 18,
        onMapEvent: (_) {
          final next = _mapController.camera.rotation * (math.pi / 180.0);
          if (next != _rotation && mounted) {
            setState(() => _rotation = next);
          }
        },
      ),
      children: <Widget>[
        TileLayer(
          urlTemplate: AqOneConfig.osmTileUrl,
          userAgentPackageName: 'ph.aqone.app',
          tileProvider:
              _tileProvider ?? CachedNetworkTileProvider(cache: _tiles),
          // Keep showing the coarser tile already on screen while a finer one
          // loads or fails. Offline, that is the difference between a blurry
          // map and a grey one.
          keepBuffer: 3,
          panBuffer: 1,
        ),
        if (circles.isNotEmpty) CircleLayer(circles: circles),
        MarkerLayer(markers: markers),
      ],
    );
  }

  Marker _buildUserMarker(LatLng point) {
    return Marker(
      point: point,
      width: 50,
      height: 50,
      alignment: Alignment.center,
      child: Stack(
        alignment: Alignment.center,
        children: <Widget>[
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: Colors.blue.withValues(alpha: 0.25),
              shape: BoxShape.circle,
            ),
          ),
          Container(
            width: 18,
            height: 18,
            decoration: BoxDecoration(
              color: const Color(0xFF0284C7),
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 3),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.3),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWeatherCapsule(bool isDark) {
    final AppLocalizations t = AppLocalizations.of(context);
    final weather = _weather;
    final label = _weatherFailed
        ? t.weatherUnavailable
        : weather?.condition.label(t) ?? t.loadingShort;
    final tempDisplay = '${weather?.temperature.toStringAsFixed(0) ?? '--'}°C';
    final icon = weather?.condition.icon ?? Icons.wb_sunny_rounded;

    return GestureDetector(
      onTap: _showSafetyDialog,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 18),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: (isDark ? _surfaceDark : const Color(0xFFF4F8FA))
              .withValues(alpha: 0.9),
          borderRadius: BorderRadius.circular(30),
          border: Border.all(
            color: (isDark ? _accentDark : Colors.white).withValues(alpha: 0.6),
            width: 1.5,
          ),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.06),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: <Widget>[
            Icon(
              icon,
              size: 22,
              color: isDark ? Colors.amber.shade300 : Colors.amber.shade700,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: isDark ? Colors.white : _brandDeep,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Text(
              tempDisplay,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: isDark ? Colors.white : _brandDeep,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNearbyHelp(bool isDark) {
    final t = AppLocalizations.of(context);
    final shown = _nearby.take(3).toList();
    final extra = _nearby.length - shown.length;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 18),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF2F2).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _danger, width: 2),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          for (final item in shown)
            InkWell(
              onTap: () {
                widget.nearby?.silence();
                widget.nearbyAlarm?.stop();
                _mapController.move(LatLng(item.centerLat, item.centerLon), 14);
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: <Widget>[
                    Container(
                      width: 32,
                      height: 32,
                      decoration: const BoxDecoration(color: _danger, shape: BoxShape.circle),
                      child: const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 20),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            '${t.nearbyHelpTitle} - ${t.nearbyHelpAway(_userLocation == null ? t.nearbyHelpDistanceUnknown : NearbySos.distanceText(item.distanceKm, t))}',
                            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: _danger),
                          ),
                          if (item.etaAt != null)
                            Text(
                              t.nearbyHelpEta('${item.etaAt!.toLocal().hour.toString().padLeft(2, '0')}:${item.etaAt!.toLocal().minute.toString().padLeft(2, '0')}'),
                              style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                            ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right_rounded, color: _danger),
                  ],
                ),
              ),
            ),
          if (extra > 0)
            Text(
              t.nearbyHelpMore(extra),
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _danger),
            ),
        ],
      ),
    );
  }

  bool _offlineStale() {
    if (_snapshotAges.isEmpty) return false;
    final now = DateTime.now();
    return _snapshotAges.values.any(
        (at) => now.difference(at) >= const Duration(minutes: 2));
  }

  Widget _collapsible({
    required bool collapsed,
    required VoidCallback onToggle,
    required IconData icon,
    required Color color,
    required Widget child,
  }) {
    final t = AppLocalizations.of(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    if (collapsed) {
      return Align(
        alignment: Alignment.centerRight,
        child: Semantics(
          button: true,
          label: t.bannerExpand,
          child: GestureDetector(
            onTap: onToggle,
            child: Container(
              width: 36,
              height: 36,
              margin: const EdgeInsets.only(right: 18),
              decoration: BoxDecoration(
                color: (isDark ? _surfaceDark : Colors.white)
                    .withValues(alpha: 0.9),
                shape: BoxShape.circle,
                border: Border.all(color: color, width: 1.5),
              ),
              child: Icon(icon, size: 18, color: color),
            ),
          ),
        ),
      );
    }
    return Stack(
      clipBehavior: Clip.none,
      children: <Widget>[
        child,
        Positioned(
          top: -10,
          right: 8,
          child: Semantics(
            button: true,
            label: t.bannerCollapse,
            child: GestureDetector(
              onTap: onToggle,
              child: Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: (isDark ? _surfaceDark : Colors.white)
                      .withValues(alpha: 0.95),
                  shape: BoxShape.circle,
                  border: Border.all(color: color, width: 1.5),
                ),
                child: Icon(Icons.keyboard_arrow_up_rounded,
                    size: 18, color: color),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRightControls(bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: <Widget>[
        Expanded(
          // Bottom-anchored so the actions sit just above the dock, clear of
          // the screen edge.
          child: Align(
            alignment: Alignment.bottomRight,
            child: _buildActionRail(isDark),
          ),
        ),
      ],
    );
  }

  Widget _buildActionRail(bool isDark) {
    final AppLocalizations t = AppLocalizations.of(context);
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: <Widget>[
        _RoundButton(
          icon: Icons.my_location_rounded,
          tooltip: t.myLocationTooltip,
          isActive: false,
          isDark: isDark,
          onTap: _locate,
        ),
        const SizedBox(height: 10),
        // Chat sits immediately above SOS rather than in its own corner, so
        // every action on this screen is reachable from one thumb position.
        _RoundButton(
          icon: Icons.chat_bubble_rounded,
          tooltip: t.chatWithBoatsTooltip,
          isActive: false,
          isDark: isDark,
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute<void>(
                builder: (_) => Chathubb(identity: widget.identity)),
          ),
        ),
        const SizedBox(height: 14),
        ActionPill(
          icon: Icons.warning_rounded,
          label: 'SOS',
          color: _danger,
          isDark: isDark,
          onTap: _isSendingSos
              ? null
              : () => handleSosTap(
                    context: context,
                    service: widget.sos,
                    alarm: _sosAlarm,
                    countdown: _sosCountdown,
                    isSending: _isSendingSos,
                    setSending: (value) {
                      if (mounted) setState(() => _isSendingSos = value);
                    },
                    onRaised: (record) async =>
                        setState(() => _latestSos = record),
                  ),
        ),
      ],
    );
  }

  Widget _buildSosStatus(bool isDark, SosRecord record) {
    final t = AppLocalizations.of(context);
    final situation = FisherSosSituation.of(record);
    final title = 'SOS: ${situation.title(t)}';
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 18),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: (isDark ? _surfaceDark : const Color(0xFFF4F8FA))
            .withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(
          color: (isDark ? _accentDark : Colors.white).withValues(alpha: 0.6),
          width: 1.5,
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.06),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: <Widget>[
          Icon(situation.icon, size: 20, color: situation.color),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                    color: situation.color,
                  ),
                ),
                Text(
                  situation.description(t),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    color: isDark ? Colors.white70 : const Color(0xFF475569),
                  ),
                ),
              ],
            ),
          ),
          if (!record.hasFix) ...<Widget>[
            const SizedBox(width: 8),
            const Icon(Icons.gps_off_rounded,
                size: 15, color: Color(0xFFD97706)),
          ],
        ],
      ),
    );
  }

  /// Live magnetic compass. Falls back to showing the map's own rotation when
  /// the handset has no magnetometer, so the control still does something
  /// truthful on a laptop or emulator.
  Widget _buildCompass(bool isDark) {
    final AppLocalizations t = AppLocalizations.of(context);
    final double? sensorHeading = _heading;
    final double? shown =
        sensorHeading ?? (_rotation == 0 ? null : -_rotation * 180.0 / math.pi);

    return Semantics(
      button: true,
      // Screen-reader label reuses the tooltip strings rather than adding two
      // more keys to translate: a blind user hearing "Heading 142°" is served
      // as well as one reading it, and every extra safety string is another
      // thing to get reviewed.
      label: sensorHeading == null
          ? t.compassUnavailable
          : t.compassHeading(sensorHeading.round()),
      child: Tooltip(
        message: sensorHeading == null
            ? t.compassUnavailable
            : _compassNeedsCalibration
                ? t.compassNeedsCalibration
                : t.compassHeading(sensorHeading.round()),
        child: GestureDetector(
          // Unchanged behaviour: tapping squares the map back up to north.
          onTap: () => _mapController.rotate(0),
          child: CompassDial(
            headingDegrees: shown,
            isDark: isDark,
            needsCalibration: _compassNeedsCalibration,
          ),
        ),
      ),
    );
  }

  Widget _buildLocatingPill(bool isDark) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isDark ? _surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 8,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: isDark ? _accentDark : _brandDeep,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            t.locatingLabel,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: isDark ? Colors.white : Colors.black87,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAttribution(bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      color: (isDark ? Colors.black : Colors.white).withValues(alpha: 0.6),
      child: Text(
        AqOneConfig.osmAttribution,
        style: TextStyle(
          fontSize: 12,
          color: isDark ? Colors.white70 : const Color(0xFF475569),
        ),
      ),
    );
  }
}

class _RoundButton extends StatelessWidget {
  const _RoundButton({
    required this.icon,
    required this.tooltip,
    required this.isActive,
    required this.isDark,
    required this.onTap,
  });

  final IconData icon;
  final String tooltip;
  final bool isActive;
  final bool isDark;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final primary = isDark ? _accentDark : _brandPrimary;
    return Tooltip(
      message: tooltip,
      child: Semantics(
        button: true,
        label: tooltip,
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color:
                  (isActive ? primary : (isDark ? _canvasDark : Colors.white))
                      .withValues(alpha: 0.9),
              shape: BoxShape.circle,
              border: Border.all(color: primary, width: 1.5),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.15),
                  blurRadius: 6,
                ),
              ],
            ),
            child: Icon(
              icon,
              size: 18,
              color: isActive ? Colors.white : primary,
            ),
          ),
        ),
      ),
    );
  }
}
