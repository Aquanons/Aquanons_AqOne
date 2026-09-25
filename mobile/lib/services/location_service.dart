import 'package:geolocator/geolocator.dart';

import '../core/config.dart';

class Fix {
  const Fix({required this.lat, required this.lon, this.accuracy, this.at});

  final double lat;
  final double lon;

  /// Horizontal accuracy in metres, when the platform reports it.
  final double? accuracy;

  /// When the fix was taken. Lets the UI say how stale a position is, which
  /// matters when an SOS falls back to a last-known location.
  final DateTime? at;
}

/// Why a location request did not produce a fix.
enum LocationFailure {
  /// Device location services are switched off entirely.
  servicesDisabled,

  /// The user declined this time.
  denied,

  /// The user declined permanently; only app settings can undo it.
  deniedForever,

  /// Permission was fine but no fix arrived in time.
  timeout,
}

/// A location attempt: either a fix, or a reason there wasn't one.
class LocationResult {
  const LocationResult.success(this.fix) : failure = null;
  const LocationResult.failed(this.failure) : fix = null;

  final Fix? fix;
  final LocationFailure? failure;

  bool get isSuccess => fix != null;

  /// Message suitable for a snackbar.
  String get message {
    switch (failure) {
      case LocationFailure.servicesDisabled:
        return 'Turn on location services to place your boat on the map.';
      case LocationFailure.denied:
        return 'AqOne needs location permission to send your position.';
      case LocationFailure.deniedForever:
        return 'Location is blocked. Enable it in your phone settings.';
      case LocationFailure.timeout:
      case null:
        return 'Could not get a GPS fix. Move to open sky and try again.';
    }
  }
}

class LocationService {
  /// Pre-warms the GPS subsystem asynchronously without blocking the caller.
  /// Called when the venture page opens and when a trip starts.
  void warmUp() {
    locate().ignore();
  }

  /// Best-effort fix. Returns null for any failure.
  ///
  /// Kept for callers that only care whether a position exists.
  Future<Fix?> currentFix() async => (await locate()).fix;

  /// A position only if permission has already been granted.
  ///
  /// Never prompts. Used by screens that would like to know where you are
  /// but must not interrupt with a permission dialog the user has no context
  /// for yet - on a first launch, a fisherman who has not opened Venture has
  /// not been told why the app wants their location.
  ///
  /// Prefers the platform's last known position, which is cached and costs
  /// no GPS fix, then falls back to a live read.
  Future<Fix?> cachedFixIfPermitted() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        return null;
      }
      final permission = await Geolocator.checkPermission();
      final granted = permission == LocationPermission.always ||
          permission == LocationPermission.whileInUse;
      if (!granted) {
        return null;
      }

      final cached = await Geolocator.getLastKnownPosition();
      if (cached != null) {
        return Fix(
          lat: cached.latitude,
          lon: cached.longitude,
          accuracy: cached.accuracy,
          at: cached.timestamp,
        );
      }
      return (await locate()).fix;
    } catch (_) {
      return null;
    }
  }

  /// Full location attempt, reporting why it failed.
  ///
  /// Venture needs the reason so it can tell the user what to do about it,
  /// rather than silently showing a map with no boat on it.
  Future<LocationResult> locate() async {
    try {
      return await _locateInternal().timeout(
        AqOneConfig.locationTimeout + const Duration(seconds: 2),
        onTimeout: () =>
            const LocationResult.failed(LocationFailure.timeout),
      );
    } catch (_) {
      return const LocationResult.failed(LocationFailure.timeout);
    }
  }

  Future<LocationResult> _locateInternal() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        return const LocationResult.failed(LocationFailure.servicesDisabled);
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.deniedForever) {
        return const LocationResult.failed(LocationFailure.deniedForever);
      }
      if (permission == LocationPermission.denied) {
        return const LocationResult.failed(LocationFailure.denied);
      }

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: AqOneConfig.locationTimeout,
        ),
      ).timeout(AqOneConfig.locationTimeout);

      return LocationResult.success(
        Fix(
          lat: position.latitude,
          lon: position.longitude,
          accuracy: position.accuracy,
          at: DateTime.now(),
        ),
      );
    } catch (_) {
      return const LocationResult.failed(LocationFailure.timeout);
    }
  }
}
