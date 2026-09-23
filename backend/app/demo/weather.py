from __future__ import annotations

from datetime import UTC, datetime


def _number_list(value: str | None) -> list[float]:
    if not value:
        return []
    try:
        return [float(item) for item in value.split(',')]
    except ValueError as exc:
        raise ValueError('latitude and longitude must be comma-separated numbers') from exc


MAX_COORDINATE_CELLS = 64


def coordinates(latitude: str | None, longitude: str | None) -> list[tuple[float, float]]:
    latitudes = _number_list(latitude)
    longitudes = _number_list(longitude)
    if len(latitudes) != len(longitudes) or not latitudes:
        raise ValueError('latitude and longitude must contain the same non-zero number of cells')
    if len(latitudes) > MAX_COORDINATE_CELLS:
        raise ValueError(f'coordinate cell count exceeds maximum of {MAX_COORDINATE_CELLS}')
    return list(zip(latitudes, longitudes, strict=True))


def _current_time() -> str:
    return datetime.now(UTC).replace(second=0, microsecond=0).isoformat(timespec='minutes')


def _is_northern(lat: float, lon: float) -> bool:
    return lat >= 11.68 and lon >= 122.36


def _conditions(beat: int, lat: float, lon: float) -> dict[str, float | int | str]:
    if beat >= 2 and _is_northern(lat, lon):
        return {
            'wind_speed_10m': 34.0,
            'wind_gusts_10m': 48.0,
            'precipitation': 0.0,
            'weather_code': 80,
            'wave_height': 2.2,
            'wave_period': 7.0,
        }
    return {
        'wind_speed_10m': 16.0,
        'wind_gusts_10m': 22.0,
        'precipitation': 0.0,
        'weather_code': 1,
        'wave_height': 0.8,
        'wave_period': 5.0,
    }


def forecast(beat: int, cells: list[tuple[float, float]]) -> list[dict[str, dict[str, float | int | str]]]:
    return [
        {
            'current': {
                'time': _current_time(),
                'wind_speed_10m': _conditions(beat, lat, lon)['wind_speed_10m'],
                'wind_gusts_10m': _conditions(beat, lat, lon)['wind_gusts_10m'],
                'precipitation': _conditions(beat, lat, lon)['precipitation'],
                'weather_code': _conditions(beat, lat, lon)['weather_code'],
            }
        }
        for lat, lon in cells
    ]


def marine(beat: int, cells: list[tuple[float, float]]) -> list[dict[str, dict[str, float | int | str]]]:
    return [
        {
            'current': {
                'time': _current_time(),
                'wave_height': _conditions(beat, lat, lon)['wave_height'],
                'wave_period': _conditions(beat, lat, lon)['wave_period'],
            }
        }
        for lat, lon in cells
    ]
