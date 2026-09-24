import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../core/endpoint_guard.dart';
import '../models/forecast_outlook.dart';
import 'backend_client.dart';
import 'safety_score.dart';

/// Where the daily outlook comes from.
///
/// Exists so the provider can be swapped without the UI knowing. Three are
/// planned:
///
///  * [OpenMeteoForecastProvider] - now. Free, keyless, global.
///  * A PAGASA provider - once a data-sharing agreement exists. Note their
///    TenDay API is keyed by municipality rather than coordinates and carries
///    no sea state, which is why [municipality] is on this interface from the
///    start and why waves keep coming from the marine model either way.
///  * [AqOneForecastProvider] - the real target. Backend fuses buoy sensor
///    telemetry with a weather provider and scores the risk server-side.
abstract class ForecastProvider {
  /// Complete outlook with both daily strips and hourly intervals,
  /// plus source provenance.
  Future<ForecastOutlook?> outlook({
    required double lat,
    required double lon,
    String? municipality,
    int days,
  });
}

/// Open-Meteo: atmospheric forecast plus a second call to the marine model
/// for wave height.
///
/// The two are separate hosts and the marine one frequently has no data for
/// nearshore cells, so a failed or empty wave response degrades to a forecast
/// with `waveM == null` rather than failing the whole fetch. That null is
/// load-bearing: it is what makes the UI admit sea state was not considered.
class OpenMeteoForecastProvider implements ForecastProvider {
  OpenMeteoForecastProvider({http.Client? client})
      : _client = client ?? http.Client();

  final http.Client _client;

  @override
  Future<ForecastOutlook?> outlook({
    required double lat,
    required double lon,
    String? municipality,
    int days = AqOneConfig.forecastDays,
  }) async {
    final coarseLat = double.parse(lat.toStringAsFixed(1));
    final coarseLon = double.parse(lon.toStringAsFixed(1));

    final Object? atmoRaw = await _atmosphericRaw(coarseLat, coarseLon, days);
    if (atmoRaw == null) {
      return null;
    }

    final Object? marineRaw = await _marineRaw(coarseLat, coarseLon, days);

    final parsed = ForecastOutlook.parseOpenMeteo(
      atmo: atmoRaw,
      marine: marineRaw,
      fetchedAt: DateTime.now(),
      lat: coarseLat,
      lon: coarseLon,
      marineLat: coarseLat,
      marineLon: coarseLon,
    );
    if (parsed == null) {
      return null;
    }

    final scoredDays =
        parsed.days.map(SafetyScore.applyTo).toList(growable: false);
    return parsed.copyWith(days: scoredDays);
  }

  Future<Object?> _atmosphericRaw(
    double lat,
    double lon,
    int days,
  ) async {
    try {
      final Uri uri = EndpointGuard.requireHttpsAbsolute(
        AqOneConfig.openMeteoBase,
        label: 'AqOneConfig.openMeteoBase',
      ).replace(
        queryParameters: <String, String>{
          'latitude': '$lat',
          'longitude': '$lon',
          'daily':
              'weather_code,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max,precipitation_sum',
          'hourly':
              'weather_code,temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation',
          'forecast_days': '$days',
          'timezone': 'auto',
        },
      );
      final http.Response response =
          await _client.get(uri).timeout(AqOneConfig.backendTimeout);
      if (response.statusCode != 200) {
        return null;
      }
      return jsonDecode(response.body);
    } catch (_) {
      return null;
    }
  }

  /// Wave heights are sampled at a fixed offshore point rather than at the
  /// municipal centre: the marine grid only covers water, and asking it about
  /// a point on Panay returns nothing at all.
  Future<Object?> _marineRaw(double lat, double lon, int days) async {
    try {
      final Uri uri = EndpointGuard.requireHttpsAbsolute(
        AqOneConfig.openMeteoMarineBase,
        label: 'AqOneConfig.openMeteoMarineBase',
      ).replace(
        queryParameters: <String, String>{
          'latitude': '$lat',
          'longitude': '$lon',
          'hourly': 'wave_height',
          'forecast_days': '$days',
          'timezone': 'auto',
        },
      );
      final http.Response response =
          await _client.get(uri).timeout(AqOneConfig.backendTimeout);
      if (response.statusCode != 200) {
        return null;
      }
      return jsonDecode(response.body);
    } catch (_) {
      return null;
    }
  }

  void close() => _client.close();
}

/// Tries the AqOne fused endpoint first, falls back to [fallback].
///
/// This is the seam that lets the buoy-fusion scorer be switched on
/// server-side with no handset release: the moment /api/public/forecast starts
/// answering, every phone in the water picks it up on its next refresh.
///
/// Days that come back without a `risk` block are scored on-device, so a
/// backend that can serve weather but not yet a verdict is still an upgrade
/// rather than a regression.
class AqOneForecastProvider implements ForecastProvider {
  AqOneForecastProvider({
    required BackendClient backend,
    required ForecastProvider fallback,
  })  : _backend = backend,
        _fallback = fallback;

  final BackendClient _backend;
  final ForecastProvider _fallback;

  @override
  Future<ForecastOutlook?> outlook({
    required double lat,
    required double lon,
    String? municipality,
    int days = AqOneConfig.forecastDays,
  }) async {
    final coarseLat = double.parse(lat.toStringAsFixed(1));
    final coarseLon = double.parse(lon.toStringAsFixed(1));

    final Object? decoded = await _backend.getJson(
      '${AqOneConfig.publicForecastPath}?lat=$coarseLat&lon=$coarseLon&days=$days',
    );
    final ForecastOutlook? parsed = decoded != null
        ? ForecastOutlook.parseBackend(decoded, fetchedAt: DateTime.now())
        : null;

    if (parsed != null && parsed.days.isNotEmpty) {
      final scoredDays =
          parsed.days.map(SafetyScore.applyTo).toList(growable: false);
      var result = parsed.copyWith(days: scoredDays);

      if (!result.hasHourly) {
        // Backend answered without hourly intervals (older server version).
        // Fuse hourly intervals from fallback provider if available.
        final fallbackOutlook = await _fallback.outlook(
          lat: coarseLat,
          lon: coarseLon,
          municipality: municipality,
          days: days,
        );
        if (fallbackOutlook != null && fallbackOutlook.hours.isNotEmpty) {
          result = result.copyWith(
            hours: fallbackOutlook.hours,
            source: 'backend+open-meteo-fallback',
          );
        }
      }
      return result;
    }

    return _fallback.outlook(
      lat: coarseLat,
      lon: coarseLon,
      municipality: municipality,
      days: days,
    );
  }
}
