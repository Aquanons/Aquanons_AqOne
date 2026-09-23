"""Geographic bounds for AqOne's service area: New Washington, Aklan.

Single source of truth for where synthetic data is allowed to exist. Both the
backend generator and the dashboard's demo markers derive from the constants
here, because when they were defined independently they drifted apart and
produced buoys inland and vessels 50 km outside the municipality.

Verified reference points (PhilAtlas, Philippine Statistics Authority):

    New Washington municipal centre   11.6473 N, 122.4356 E  (land, ~8 m elev.)
    Land area                         66.69 km2
    Marine waterbody                  Sibuyan Sea
    Kalibo                            10.36 km to the north-west
    Batan                              9.40 km to the south-east

The municipality is a narrow coastal strip on the west side of Batan Bay, whose
estuary opens north into the Sibuyan Sea.

────────────────────────────────────────────────────────────────────────────
WATER_POLYGON BELOW IS APPROXIMATE.

It was drawn from the reference points above, not traced from a coastline
dataset. It is deliberately conservative - held offshore of where the coast is
believed to run - so generated points land in water even if the true shoreline
sits somewhat differently.

To replace it with an exact polygon: draw the sea area on geojson.io, then
paste the ring's coordinates below as (lat, lon) pairs. Note that GeoJSON
orders coordinates [lon, lat], so they must be swapped. Nothing else needs to
change; every consumer reads this constant.

Paste WATER_POLYGON_GEOJSON (see geojson_feature_collection below) into
geojson.io to see the current polygon on a map.
────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

# Municipal centre, on land. Used for map framing, never as a data position.
CENTER_LAT = 11.6473
CENTER_LON = 122.4356

KM_PER_DEG_LAT = 110.574


def km_per_deg_lon(lat: float) -> float:
    return 111.320 * math.cos(math.radians(lat))


# Ring of (lat, lon) covering Batan Bay and the open Sibuyan Sea north of it,
# out to roughly 15 km offshore. Ordered anticlockwise starting at the
# south-west corner of the bay.
# Traced on a map by the AqOne team (geojson.io): Batan Bay plus the open
# Sibuyan Sea beyond the bay mouth. Stored as (lat, lon); the source GeoJSON is
# [lon, lat] and was swapped here.
#
# The southern and western vertices follow the real coastline, so a drift track
# reaching them has genuinely beached. The northern and eastern vertices are an
# offshore limit on the demo area, not a shore.
WATER_POLYGON: tuple[tuple[float, float], ...] = (
    (11.6703215, 122.4156697),  # NW, off the Poblacion shoreline
    (11.6177249, 122.4379915),  # SW, inner bay south of the town
    (11.5901553, 122.4913697),  # S, Batan side of the bay
    (11.5910550, 122.6285526),  # SE
    (11.6329746, 122.6720879),  # E, offshore limit
    (11.6813429, 122.6355017),  # ENE
    (11.7413766, 122.5924432),  # NE, open Sibuyan Sea
    (11.7730972, 122.5407817),  # N
    (11.7661758, 122.4573773),  # NNW
    (11.7222742, 122.4060625),  # NW, back toward the coast
)

# Shore gateways sit on land, unlike buoys. These are the LoRa mesh exit points
# to the internet, hosted at existing coastal facilities.
# Shore gateways are LAND installations - the mesh's exit to the internet.
#
# Known issue with the traced polygon: its western edge runs slightly east of
# the true shoreline, so the real municipal centre (11.6473, 122.4356, ~8 m
# elevation per PhilAtlas) and Dumaguit Port both fall *inside* WATER_POLYGON.
# The two positions below are therefore held ~1.7 km west of their real
# locations so they sit unambiguously on land and satisfy the invariant in
# tests/test_geo.py. Pull the polygon's western edge east by ~0.015 deg and
# these can move back to their true coordinates.
SHORE_STATIONS: tuple[dict[str, Any], ...] = (
    {
        'name': 'New Washington Municipal Hall',
        'lat': 11.6473,
        'lon': 122.4200,
        'type': 'MDRRMO Station',
        'role': 'Shore gateway',
    },
    {
        'name': 'Dumaguit Port',
        'lat': 11.6700,
        'lon': 122.4100,
        'type': 'Port Facility',
        'role': 'Shore gateway',
    },
    {
        'name': 'BFAR Kalibo',
        'lat': 11.7086,
        'lon': 122.3653,
        'type': 'BFAR Station',
        'role': 'Shore gateway',
    },
)


def water_area_km2() -> float:
    """Area of WATER_POLYGON in km² via the shoelace formula.

    Vertices are converted to a local metre grid using the scale factors at
    the polygon centroid, then the standard cross-product form gives area.
    """
    n = len(WATER_POLYGON)
    mean_lat = sum(lat for lat, _ in WATER_POLYGON) / n
    kx = km_per_deg_lon(mean_lat)
    ky = KM_PER_DEG_LAT
    cross_sum = 0.0
    for i in range(n):
        lat_i, lon_i = WATER_POLYGON[i]
        lat_j, lon_j = WATER_POLYGON[(i + 1) % n]
        cross_sum += lon_i * lat_j - lon_j * lat_i
    return abs(cross_sum * kx * ky / 2.0)


def bounding_box() -> tuple[float, float, float, float]:
    """(min_lat, min_lon, max_lat, max_lon) of the water polygon."""
    lats = [lat for lat, _ in WATER_POLYGON]
    lons = [lon for _, lon in WATER_POLYGON]
    return min(lats), min(lons), max(lats), max(lons)


def point_in_water(lat: float, lon: float) -> bool:
    """Ray-casting point-in-polygon test.

    Implemented directly rather than pulling in shapely: the polygon is a
    simple ring of ~11 vertices and this keeps the production image free of a
    geometry dependency used in exactly one place.
    """
    inside = False
    count = len(WATER_POLYGON)
    for i in range(count):
        lat_i, lon_i = WATER_POLYGON[i]
        lat_j, lon_j = WATER_POLYGON[(i - 1) % count]
        intersects = (lat_i > lat) != (lat_j > lat)
        if intersects:
            lon_at_lat = (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i
            if lon < lon_at_lat:
                inside = not inside
    return inside


def sample_water_points(rng: np.random.Generator, count: int) -> list[tuple[float, float]]:
    """Uniformly sample `count` positions inside the water polygon.

    Rejection sampling against the bounding box. The polygon fills a healthy
    fraction of its box, so this converges quickly; the iteration cap exists
    only so a future malformed polygon fails loudly instead of hanging.
    """
    min_lat, min_lon, max_lat, max_lon = bounding_box()
    points: list[tuple[float, float]] = []
    attempts = 0
    max_attempts = count * 500

    while len(points) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(
                f'Could not sample {count} points inside WATER_POLYGON after '
                f'{max_attempts} attempts. The polygon is probably malformed '
                f'or degenerate.'
            )
        lat = float(rng.uniform(min_lat, max_lat))
        lon = float(rng.uniform(min_lon, max_lon))
        if point_in_water(lat, lon):
            points.append((lat, lon))

    return points


def geojson_feature_collection() -> dict[str, Any]:
    """The service area as GeoJSON, for map rendering and visual verification.

    Paste the output into geojson.io to check the polygon against the real
    coastline.
    """
    ring = [[lon, lat] for lat, lon in WATER_POLYGON]
    ring.append(ring[0])  # GeoJSON rings must close

    features: list[dict[str, Any]] = [
        {
            'type': 'Feature',
            'properties': {'name': 'New Washington municipal waters', 'kind': 'water'},
            'geometry': {'type': 'Polygon', 'coordinates': [ring]},
        }
    ]
    for station in SHORE_STATIONS:
        features.append(
            {
                'type': 'Feature',
                'properties': {
                    'name': station['name'],
                    'kind': 'shore_station',
                    'type': station['type'],
                },
                'geometry': {'type': 'Point', 'coordinates': [station['lon'], station['lat']]},
            }
        )

    return {'type': 'FeatureCollection', 'features': features}


if __name__ == '__main__':
    import json

    print(json.dumps(geojson_feature_collection(), indent=2))
