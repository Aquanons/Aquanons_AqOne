class NearbySos {
  const NearbySos({
    required this.broadcastId,
    required this.sosEventId,
    required this.centerLat,
    required this.centerLon,
    this.distanceKm,
    this.radiusKm,
    this.etaAt,
    this.responderStatus,
    this.createdAt,
  });

  final int broadcastId;
  final int sosEventId;
  final double centerLat;
  final double centerLon;
  final double? distanceKm;
  final int? radiusKm;
  final DateTime? etaAt;
  final int? responderStatus;
  final DateTime? createdAt;

  static int _toInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value.toString()) ?? 0;
  }

  static double? _toDouble(Object? value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }

  static DateTime? _toTime(Object? value) {
    if (value is! String || value.isEmpty) return null;
    return DateTime.tryParse(value);
  }

  static NearbySos? tryParse(Object? raw) {
    if (raw is! Map) return null;
    final lat = _toDouble(raw['center_lat']);
    final lon = _toDouble(raw['center_lon']);
    if (lat == null || lon == null) return null;
    return NearbySos(
      broadcastId: _toInt(raw['broadcast_id']),
      sosEventId: _toInt(raw['sos_event_id']),
      centerLat: lat,
      centerLon: lon,
      distanceKm: _toDouble(raw['distance_km']),
      radiusKm: raw['radius_km'] is num ? (raw['radius_km'] as num).toInt() : null,
      etaAt: _toTime(raw['eta_at'] as Object?),
      responderStatus: raw['responder_status'] is num ? (raw['responder_status'] as num).toInt() : null,
      createdAt: _toTime(raw['created_at'] as Object?),
    );
  }

  static List<NearbySos> parseList(Object? decoded) {
    final List<Object?> rows;
    if (decoded is Map && decoded['broadcasts'] is List) {
      rows = List<Object?>.from(decoded['broadcasts'] as List);
    } else if (decoded is List) {
      rows = List<Object?>.from(decoded);
    } else {
      return const <NearbySos>[];
    }
    final out = <NearbySos>[];
    for (final row in rows) {
      final parsed = tryParse(row);
      if (parsed != null) out.add(parsed);
    }
    out.sort((a, b) => (a.distanceKm ?? 1e9).compareTo(b.distanceKm ?? 1e9));
    return out;
  }

  static String distanceText(double? km) {
    if (km == null) return 'distance unknown';
    if (km < 1) return '${(km * 1000).round()} m away';
    return '${km.toStringAsFixed(1)} km away';
  }
}
