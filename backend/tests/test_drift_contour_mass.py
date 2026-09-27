"""docs/71 RND-07: a labelled ring holds the mass its label claims.

With a few thousand particles most occupied cells hold one or two of them, so
their densities tie. Selecting `density >= cutoff` then pulled every tied cell
into the ring: on the histogram below all three rings held 100% of the mass,
and the "95% search area" was really the 100% area.
"""

from datetime import UTC, datetime, timedelta

import numpy as np

from app.ai.drift import _contour_polygon
from app.ai.drift_replay import replay_horizon_hours, resolved_object_class
from app.ai.search import contour_area_km2

MASSES = (0.50, 0.75, 0.95)


def _sparse_histogram():
    rng = np.random.default_rng(1)
    points = rng.normal(0, 3000, size=(500, 2))
    edges = np.arange(-12000, 12001, 250)
    hist, y_edges, x_edges = np.histogram2d(points[:, 1], points[:, 0], bins=[edges, edges])
    hist = hist / hist.sum()
    return (x_edges[:-1] + x_edges[1:]) / 2.0, (y_edges[:-1] + y_edges[1:]) / 2.0, hist


def _ring_area(contour):
    return contour_area_km2(contour)


def test_tied_cells_do_not_inflate_a_ring_to_the_whole_plume():
    x, y, hist = _sparse_histogram()
    areas = [_ring_area(_contour_polygon(x, y, hist, mass, 11.7, 122.5)) for mass in MASSES]
    assert areas[0] < areas[1] < areas[2], areas


def test_a_ring_is_the_smallest_top_density_set_reaching_its_mass():
    from app.ai.drift import _mass_cells

    _, _, hist = _sparse_histogram()
    largest = hist.max()
    previous = set()
    for mass in MASSES:
        cells = _mass_cells(hist, mass)
        held = float(sum(hist[row, col] for row, col in cells))
        assert mass <= held < mass + largest + 1e-9, (mass, held)
        chosen = {tuple(cell) for cell in cells}
        assert previous <= chosen, 'rings must nest'
        previous = chosen


def test_the_replay_horizon_is_the_span_of_the_truth_track():
    start = datetime(2026, 8, 12, 6, 21, tzinfo=UTC)
    track = [
        {'lat': 11.7, 'lon': 122.5, 'observed_at': (start + timedelta(minutes=30 * i)).isoformat()}
        for i in range(9)
    ]
    assert replay_horizon_hours(track) == 4.0
    assert replay_horizon_hours(track[:1]) is None
    assert replay_horizon_hours([]) is None
    assert replay_horizon_hours([{'lat': 1, 'lon': 1}, {'lat': 1, 'lon': 1}, {'lat': 1, 'lon': 1}]) == 1.0


def test_one_object_class_rule_for_replay_and_evaluation():
    assert resolved_object_class('intact_hull_adrift', 'capsize').value == 'intact_hull_adrift'
    assert resolved_object_class(None, 'capsize').value == 'swamped_banca'
    assert resolved_object_class(None, 'adverse_weather').value == 'swamped_banca'
    assert resolved_object_class(None, 'engine_failure').value == 'intact_hull_adrift'


def test_a_ring_encloses_every_cell_it_counts():
    from app.ai.drift import _mass_cells, _to_latlon, contour_contains

    x, y, hist = _sparse_histogram()
    for mass in (0.05, 0.50, 0.95):
        ring = _contour_polygon(x, y, hist, mass, 11.7, 122.5)
        cells = _mass_cells(hist, mass)
        lat, lon = _to_latlon(x[cells[:, 1]], y[cells[:, 0]], 11.7, 122.5)
        assert all(contour_contains(ring, float(a), float(b)) for a, b in zip(lat, lon, strict=True)), mass
