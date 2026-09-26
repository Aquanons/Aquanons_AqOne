/// One binned cell of the fish-hotspot surface.
///
/// A cell, never a point. §6.2 of the system design requires hotspot output to
/// be spatially binned and "protected against exposing an individual's exact
/// productive location", and the manual pin-drop this replaces did the
/// opposite: exact coordinates, attributed to a vessel, published to every
/// handset. The wire format therefore has no way to express a point, and the
/// map has no way to draw one - the privacy property is a property of the
/// contract, not of the widget that happens to render it.
///
/// Filled by the server-side aggregation at `/api/public/hotspots`.
class HotspotCell {
  const HotspotCell({
    required this.centerLat,
    required this.centerLon,
    required this.cellSizeDegrees,
    required this.score,
    required this.observations,
  });

  final double centerLat;
  final double centerLon;

  /// Edge length of the square bin, in degrees. Carried per cell rather than
  /// assumed, so the backend can coarsen the grid where reporting is sparse
  /// without the client needing a release.
  final double cellSizeDegrees;

  /// Relative recent catch activity, 0-1. Explicitly NOT a probability of
  /// catching anything: §6.2 forbids implying guaranteed catch.
  final double score;

  /// How many independent observations back this cell. Displayed, not hidden -
  /// a cell resting on two reports and a cell resting on two hundred must not
  /// look alike.
  final int observations;

  /// Approximate radius in metres for drawing, derived from the bin size.
  /// One degree of latitude is ~111 km; longitude convergence is ignored
  /// because at Aklan's latitude it is a few percent and this is a fuzzy
  /// surface, not a boundary.
  double get approxRadiusMeters => cellSizeDegrees * 111000 / 2;

  static HotspotSurface? parse(Object? payload) {
    if (payload is! Map) {
      return null;
    }
    final Object? cells = payload['cells'];
    if (cells is! List) {
      return null;
    }

    final List<HotspotCell> parsed = <HotspotCell>[];
    for (final Object? entry in cells) {
      if (entry is! Map) {
        continue;
      }
      final Object? lat = entry['center_lat'];
      final Object? lon = entry['center_lon'];
      final Object? score = entry['score'];
      if (lat is! num || lon is! num || score is! num) {
        continue;
      }
      final Object? size = entry['cell_size_degrees'];
      final Object? obs = entry['observations'];
      parsed.add(
        HotspotCell(
          centerLat: lat.toDouble(),
          centerLon: lon.toDouble(),
          cellSizeDegrees: size is num ? size.toDouble() : 0.05,
          score: score.toDouble().clamp(0.0, 1.0),
          observations: obs is num ? obs.toInt() : 0,
        ),
      );
    }
    final Object? generated = payload['generated_at'];
    final Object? model = payload['model_version'];
    final Object? minReporters = payload['min_reporters'];
    final Object? windowDays = payload['window_days'];

    return HotspotSurface(
      cells: parsed,
      generatedAt:
          generated is String ? DateTime.tryParse(generated) : null,
      modelVersion: model is String ? model : null,
      minReporters: minReporters is num ? minReporters.toInt() : null,
      windowDays: windowDays is num ? windowDays.toInt() : null,
    );
  }
}

/// A whole surface plus the provenance the UI is required to show.
class HotspotSurface {
  const HotspotSurface({
    required this.cells,
    this.generatedAt,
    this.modelVersion,
    this.minReporters,
    this.windowDays,
    this.isDemo = false,
  });

  final List<HotspotCell> cells;

  /// When the model last ran. §3.4 requires data age to be visible; a
  /// three-week-old surface must not look like this morning's.
  final DateTime? generatedAt;

  final String? modelVersion;

  /// The reporter threshold the backend applied before publishing a cell.
  /// §6.3's minimum-reporter rule exists so one prolific fisher cannot become
  /// "the model", and showing it lets a fisher judge the surface for himself.
  final int? minReporters;
  final int? windowDays;

  /// True for the illustrative cells the app ships to show what the layer
  /// will look like. Never set from the wire - a backend cannot mark its own
  /// output as an example, and a fisherman burning fuel on invented
  /// coordinates is the exact outcome this flag exists to prevent.
  final bool isDemo;
}
