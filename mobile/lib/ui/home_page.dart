import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:network_info_plus/network_info_plus.dart';

import '../core/config.dart';
import '../core/tokens.dart';
import '../data/forecast_cache.dart';
import '../l10n/app_localizations.dart';
import '../data/identity_store.dart';
import '../models/advisory.dart';
import '../models/daily_outlook.dart';
import '../models/forecast_outlook.dart';
import '../models/buoy_contact.dart';
import '../models/sea_condition.dart';
import '../models/sos_record.dart';
import '../models/squall_watch.dart';
import '../models/weather_snapshot.dart';
import '../services/location_service.dart';
import '../services/sos_alarm.dart';
import '../services/sos_service.dart';
import '../services/venture_feeds.dart';

import 'sos_flow.dart';
import 'widgets/action_pill.dart';
import 'widgets/advisory_card.dart';
import 'widgets/buoy_status_card.dart';
import 'widgets/delivery_state_tile.dart';
import 'widgets/sea_condition_banner.dart';
import 'widgets/squall_banner.dart';
import 'widgets/weather_card.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.service,
    required this.identity,
    required this.feeds,
    required this.location,
    this.bottomInset = 0,
    this.onOpenAdvisories,
    this.onOpenProfile,
    this.squall = SquallWatch.unavailable,
    this.squallAcknowledged = false,
    this.onAcknowledgeSquall,
    this.sosAlarm,
  });

  final SosService service;
  final VesselIdentity identity;
  final VentureFeeds feeds;
  final LocationService location;
  final SosAlarm? sosAlarm;

  /// Space reserved for the shell's floating dock, so the last card is not
  /// hidden underneath it.
  final double bottomInset;

  /// Opens the full advisories list. Null hides the "View all" action rather
  /// than leaving a control that navigates nowhere.
  final VoidCallback? onOpenAdvisories;
  final VoidCallback? onOpenProfile;

  /// Polled by AppShell, not here. A squall must reach the fisher wherever he
  /// is looking, and two pollers would mean two alarms for one squall.
  final SquallWatch squall;
  final bool squallAcknowledged;
  final VoidCallback? onAcknowledgeSquall;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  List<SosRecord> _records = const <SosRecord>[];
  BuoyStatus? _buoy;
  Timer? _buoyTimer;
  Timer? _seaTimer;
  Timer? _minuteTimer;
  StreamSubscription<void>? _changes;

  SeaCondition? _sea;
  bool _seaLoading = true;
  List<Advisory> _advisories = const <Advisory>[];
  WeatherSnapshot? _weather;
  bool _weatherLoading = true;

  /// Whether the current reading is for the device position or the fallback.
  bool _weatherAtDevice = false;

  // Seven-day outlook. Refreshed far less often than the buoy or sea polls:
  // daily data does not change minute to minute and the battery has to last
  // a trip.
  List<DailyOutlook> _forecast = const <DailyOutlook>[];
  ForecastOutlook? _forecastOutlook;
  Timer? _forecastTimer;
  static const ForecastCache _forecastCache = ForecastCache();
  final RequestGuard _forecastGuard = RequestGuard();

  /// Retrieval timestamp for the forecast on screen.
  DateTime? _forecastFetchedAt;

  bool _isSendingSos = false;
  late final SosAlarm _sosAlarm;
  static const Duration _sosCountdown = Duration(seconds: 5);

  @visibleForTesting
  ForecastOutlook? get forecastOutlook => _forecastOutlook;

  @override
  void initState() {
    super.initState();
    _sosAlarm = widget.sosAlarm ?? SosAlarm();
    WidgetsBinding.instance.addObserver(this);
    _changes = widget.service.changes.listen((_) => _loadRecords());
    widget.service.start();
    _loadRecords();
    _pollBuoy();
    _loadSea();
    _loadAdvisories();
    _loadWeather();
    // Cache first so there is something on screen immediately, including with
    // no signal at all; the live fetch overwrites it when it lands.
    _restoreCachedForecast();
    _loadForecast();
    _buoyTimer = Timer.periodic(
      AqOneConfig.buoyPollInterval,
      (_) => _pollBuoy(),
    );
    _seaTimer = Timer.periodic(
      AqOneConfig.seaConditionInterval,
      (_) => _loadSea(),
    );
    _forecastTimer = Timer.periodic(
      AqOneConfig.forecastRefreshInterval,
      (_) => _loadForecast(),
    );
    _minuteTimer = Timer.periodic(
      const Duration(minutes: 1),
      (_) {
        if (mounted) {
          setState(() {});
        }
      },
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && mounted) {
      setState(() {});
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _minuteTimer?.cancel();
    _buoyTimer?.cancel();
    _seaTimer?.cancel();
    _forecastTimer?.cancel();
    _changes?.cancel();
    unawaited(_sosAlarm.dispose());
    super.dispose();
  }

  Future<void> _loadSea() async {
    final sea = await widget.feeds.seaCondition();
    if (!mounted) {
      return;
    }
    setState(() {
      _seaLoading = false;
      if (sea != null) {
        _sea = sea;
      }
    });
  }

  Future<void> _loadAdvisories() async {
    final advisories = await widget.feeds.advisories();
    if (!mounted || advisories == null) {
      return;
    }
    setState(() => _advisories = advisories);
  }

  Future<void> _loadWeather() async {
    if (mounted) {
      setState(() => _weatherLoading = true);
    }

    final fix = await widget.location.cachedFixIfPermitted();
    final weather = await widget.feeds.weather(
      lat: fix?.lat ?? AqOneConfig.aklanLat,
      lon: fix?.lon ?? AqOneConfig.aklanLon,
    );
    if (!mounted) {
      return;
    }
    setState(() {
      _weatherLoading = false;
      _weatherAtDevice = fix != null;
      if (weather != null) {
        _weather = weather;
      }
    });
  }

  /// Paints the last stored strip before any network call returns.
  ///
  /// Skipped entirely if a live fetch has already landed, so a fast network
  /// never gets overwritten by older cached days.
  Future<void> _restoreCachedForecast() async {
    final CachedForecast? cached = await _forecastCache.load();
    if (!mounted || cached == null || _forecast.isNotEmpty) {
      return;
    }
    setState(() {
      _forecast = cached.days;
      _forecastOutlook = cached.outlook;
      _forecastFetchedAt = cached.fetchedAt;
    });
  }

  /// The card's Retry button. Current conditions and the outlook come from
  /// different endpoints, and if one is down the other usually is too, so the
  /// one button retries both.
  void _retryWeather() {
    unawaited(_loadWeather());
    unawaited(_loadForecast());
  }

  Future<void> _loadForecast() async {
    final int version = _forecastGuard.begin();
    final fix = await widget.location.cachedFixIfPermitted();
    final ForecastOutlook? outlook = await widget.feeds.forecastOutlook(
      lat: fix?.lat ?? AqOneConfig.aklanLat,
      lon: fix?.lon ?? AqOneConfig.aklanLon,
    );
    if (!mounted ||
        !_forecastGuard.isCurrent(version) ||
        outlook == null ||
        outlook.days.isEmpty) {
      // Failure leaves whatever is on screen alone. A dropped poll at sea is
      // routine and must not blank the outlook.
      return;
    }
    setState(() {
      _forecast = outlook.days;
      _forecastOutlook = outlook;
      _forecastFetchedAt = outlook.fetchedAt;
    });
    unawaited(_forecastCache.saveOutlook(outlook));
  }

  Future<void> _loadRecords() async {
    final records = await widget.service.history();
    if (!mounted) {
      return;
    }
    setState(() => _records = records);
  }

  Future<void> _pollBuoy() async {
    final status = await widget.service.pollBuoy();
    if (!mounted) {
      return;
    }
    setState(() => _buoy = status);
  }

  void _openWiFiSelection() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => _WiFiSelectionScreen(service: widget.service),
      ),
    );
    _pollBuoy();
  }

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: palette.canvas,
      floatingActionButton: Padding(
        padding: EdgeInsets.only(bottom: widget.bottomInset),
        child: ActionPill(
          icon: Icons.warning_rounded,
          label: 'SOS',
          color: const Color(0xFFDC2626),
          isDark: Theme.of(context).brightness == Brightness.dark,
          onTap: _isSendingSos
              ? null
              : () => handleSosTap(
                    context: context,
                    service: widget.service,
                    alarm: _sosAlarm,
                    countdown: _sosCountdown,
                    isSending: _isSendingSos,
                    setSending: (value) {
                      if (mounted) setState(() => _isSendingSos = value);
                    },
                    onRaised: (_) => _loadRecords(),
                  ),
        ),
      ),
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          onRefresh: () async {
            await _pollBuoy();
            await _loadSea();
            await _loadAdvisories();
            await _loadWeather();
            await _loadForecast();
            await widget.service.retryPending();
            await widget.service.reconcile();
            await _loadRecords();
          },
          child: ListView(
            padding: EdgeInsets.fromLTRB(
              AqSpace.screen,
              AqSpace.lg,
              AqSpace.screen,
              AqSpace.xl + widget.bottomInset,
            ),
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: <Widget>[
                  Expanded(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: <Widget>[
                        Image.asset(
                          'assets/images/aqoneLogo1.png',
                          height: 38,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => Icon(
                            Icons.waves_rounded,
                            size: 38,
                            color: palette.primaryText,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Image.asset(
                          'assets/images/aqoneLogo2.png',
                          height: 24,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) {
                            const appBrand = 'AqOne';
                            return Text(
                              appBrand,
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w900,
                                color: palette.primaryText,
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: AqSpace.base),
                  Semantics(
                    button: true,
                    label: 'Open fisherman profile',
                    child: InkWell(
                      onTap: widget.onOpenProfile,
                      customBorder: const CircleBorder(),
                      // The photo is inset inside the ring rather than
                      // clipped flush to it. Filling the whole circle painted
                      // the image straight over the 1px border, so the avatar
                      // read as a photo with a hard edge and no frame at all.
                      child: Container(
                        width: 48,
                        height: 48,
                        padding: const EdgeInsets.all(2.5),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: palette.surface,
                          border: Border.all(color: palette.border, width: 1.5),
                          boxShadow: <BoxShadow>[
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.06),
                              blurRadius: 10,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: ClipOval(child: _buildAvatar(palette)),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AqSpace.lg),
              // Squall nowcast sits ABOVE the sea condition. The MDRRMO's
              // declaration is a standing judgement about the day; a squall is
              // happening now and has minutes of lead time, so it must be the
              // first thing seen. Renders nothing when there is no squall.
              if (!AqOneConfig.pitchMode &&
                  widget.squall.shouldDisplay) ...<Widget>[
                SquallBanner(
                  watch: widget.squall,
                  acknowledged: widget.squallAcknowledged,
                  onAcknowledge: widget.onAcknowledgeSquall,
                ),
                const SizedBox(height: AqSpace.base),
              ],
              if (!AqOneConfig.pitchMode &&
                  widget.squall.level == SquallLevel.returnNow &&
                  !widget.squallAcknowledged) ...<Widget>[
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: widget.onAcknowledgeSquall,
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFFDC2626),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    icon: const Icon(Icons.check_circle_outline),
                    label: Text(
                      t.squallAckButton,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: AqSpace.base),
              ],
              SeaConditionBanner(condition: _sea, isLoading: _seaLoading),
              const SizedBox(height: AqSpace.base),
              WeatherCard(
                snapshot: _weather,
                isLoading: _weatherLoading,
                onRetry: _retryWeather,
                forecast: _forecast,
                forecastOutlook: _forecastOutlook,
                seaCondition: _sea,
                squall: widget.squall,
                forecastAge: _forecastFetchedAt,
                locationLabel: _weatherAtDevice
                    ? t.weatherLocationYourPosition
                    : t.weatherLocationDefault,
              ),
              if (_advisories.isNotEmpty) ...<Widget>[
                const SizedBox(height: AqSpace.base),
                AdvisoryCard(
                  advisory: _advisories.first,
                  remaining: _advisories.length - 1,
                  // Preview only: the full card, photo and all, is on the
                  // Advisories page.
                  showImage: false,
                  onViewAll: widget.onOpenAdvisories,
                ),
              ],
              const SizedBox(height: AqSpace.base),
              GestureDetector(
                onTap: _openWiFiSelection,
                behavior: HitTestBehavior.opaque,
                child: BuoyStatusCard(status: _buoy),
              ),
              const SizedBox(height: AqSpace.screen),
              Text(
                t.homeYourMessages,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: palette.primaryText,
                ),
              ),
              const SizedBox(height: AqSpace.md),
              if (_records.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: AqSpace.xl),
                  child: Text(
                    t.sosNoneSentYet,
                    style: TextStyle(fontSize: 14, color: palette.dimText),
                  ),
                )
              else
                ..._records.map(
                  (record) => DeliveryStateTile(record: record),
                ),
            ],
          ),
        ),
      ),
    );
  }

  /// The header avatar. Mirrors the profile page: the user's uploaded photo
  /// when there is one, the shared empty-profile asset otherwise, and a plain
  /// icon if either fails to decode (e.g. the file was deleted underneath us).
  Widget _buildAvatar(AqPalette palette) {
    final path = widget.identity.avatarPath;
    final hasCustomAvatar =
        !kIsWeb && path != null && path.isNotEmpty && File(path).existsSync();

    // 43, not 48: the ring is 48 across with 2.5 of padding on each side.
    // Sizing the image to the outer circle would push it back under the
    // border, which is the bug this replaces.
    const double inner = 43;

    if (hasCustomAvatar) {
      return Image.file(
        File(path),
        width: inner,
        height: inner,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => _avatarFallback(palette),
      );
    }
    return Image.asset(
      'icons/emptyProfile.png',
      width: inner,
      height: inner,
      fit: BoxFit.cover,
      errorBuilder: (_, __, ___) => _avatarFallback(palette),
    );
  }

  Widget _avatarFallback(AqPalette palette) {
    return Icon(
      Icons.person_rounded,
      color: palette.secondaryText,
      size: 28,
    );
  }
}

// ==========================================
// BUOY WIFI SELECTION PAGE
// ==========================================

String stripSsidQuotes(String? raw) {
  final s = (raw ?? '').trim();
  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
    return s.substring(1, s.length - 1);
  }
  if (s.isEmpty || s == '<unknown ssid>') {
    return '';
  }
  return s;
}

class _WiFiSelectionScreen extends StatefulWidget {
  const _WiFiSelectionScreen({required this.service});

  final SosService service;

  @override
  State<_WiFiSelectionScreen> createState() => _WiFiSelectionScreenState();
}

class _WiFiSelectionScreenState extends State<_WiFiSelectionScreen> {
  bool _checking = true;
  String _ssid = '';
  BuoyStatus? _buoy;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() => _checking = true);
    var ssid = '';
    try {
      ssid = stripSsidQuotes(await NetworkInfo().getWifiName());
    } catch (_) {}
    final buoy = await widget.service.pollBuoy();
    if (!mounted) return;
    setState(() {
      _checking = false;
      _ssid = ssid;
      _buoy = buoy;
    });
  }

  @override
  Widget build(BuildContext context) {
    final palette = AqPalette.of(context);
    final t = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: palette.canvas,
      appBar: AppBar(
        backgroundColor: palette.canvas,
        elevation: 0,
        scrolledUnderElevation: 0,
        title: Text(
          t.wifiTitle,
          style: TextStyle(
            color: palette.primaryText,
            fontWeight: FontWeight.bold,
          ),
        ),
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded,
              color: palette.primaryText),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          IconButton(
            icon: _checking
                ? SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: palette.primaryText,
                    ),
                  )
                : Icon(Icons.refresh_rounded, color: palette.primaryText),
            onPressed: _checking ? null : _refresh,
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AqSpace.screen,
            vertical: AqSpace.md,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                decoration: BoxDecoration(
                  color: palette.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: palette.border),
                ),
                child: ListTile(
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: AqSpace.lg,
                    vertical: AqSpace.xs,
                  ),
                  leading: Icon(
                    _ssid.isEmpty ? Icons.wifi_off_rounded : Icons.wifi_rounded,
                    color: _ssid.isEmpty
                        ? palette.secondaryText
                        : palette.primaryText,
                    size: 28,
                  ),
                  title: Text(
                    _ssid.isEmpty ? t.wifiNotConnected : _ssid,
                    style: TextStyle(
                      color: palette.primaryText,
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                    ),
                  ),
                  subtitle: _ssid.isEmpty
                      ? Text(
                          t.wifiJoinHint,
                          style: TextStyle(
                            color: palette.secondaryText,
                            fontSize: 13,
                          ),
                        )
                      : null,
                ),
              ),
              const SizedBox(height: AqSpace.sm),
              BuoyStatusCard(status: _buoy),
            ],
          ),
        ),
      ),
    );
  }
}
