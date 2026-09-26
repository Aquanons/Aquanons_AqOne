import 'package:aqone/models/hotspot_cell.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('HotspotCell.parse', () {
    test('parses a surface with its provenance', () {
      final HotspotSurface? surface = HotspotCell.parse(<String, Object?>{
        'generated_at': '2026-08-16T02:00:00Z',
        'model_version': 'hotspot-v0.1',
        'min_reporters': 5,
        'window_days': 30,
        'cells': <Object?>[
          <String, Object?>{
            'center_lat': 11.72,
            'center_lon': 122.36,
            'cell_size_degrees': 0.05,
            'score': 0.82,
            'observations': 34,
          },
        ],
      });

      expect(surface, isNotNull);
      expect(surface!.cells.length, 1);
      expect(surface.modelVersion, 'hotspot-v0.1');
      expect(surface.minReporters, 5);
      expect(surface.windowDays, 30);
      expect(surface.cells.first.observations, 34);
      // 0.05 degrees is about 5.5 km across, so a ~2.8 km drawing radius.
      expect(surface.cells.first.approxRadiusMeters, closeTo(2775, 1));
    });

    test('distinguishes an absent endpoint from an empty real surface', () {
      expect(HotspotCell.parse(null), isNull);
      expect(HotspotCell.parse(<String, Object?>{}), isNull);
      final surface =
          HotspotCell.parse(<String, Object?>{'cells': <Object?>[]});
      expect(surface, isNotNull);
      expect(surface!.cells, isEmpty);
    });

    test('drops malformed cells rather than failing the whole surface', () {
      final HotspotSurface? surface = HotspotCell.parse(<String, Object?>{
        'cells': <Object?>[
          <String, Object?>{'center_lat': 11.7, 'center_lon': 122.3, 'score': 0.4},
          <String, Object?>{'center_lat': 'north', 'score': 0.9},
          'not a cell',
        ],
      });

      expect(surface!.cells.length, 1);
      // Missing bin size falls back to the default rather than zero, which
      // would draw an invisible cell.
      expect(surface.cells.first.cellSizeDegrees, 0.05);
    });

    test('clamps scores into range', () {
      final HotspotSurface? surface = HotspotCell.parse(<String, Object?>{
        'cells': <Object?>[
          <String, Object?>{'center_lat': 11.7, 'center_lon': 122.3, 'score': 4.2},
        ],
      });

      // Opacity is derived from score; an out-of-range value would throw when
      // it reached withValues(alpha:).
      expect(surface!.cells.first.score, 1.0);
    });
  });
}
