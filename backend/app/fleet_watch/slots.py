from collections.abc import Mapping
from dataclasses import dataclass

SLOT_COUNT = 80
SLOT_LENGTH_S = 1.5


@dataclass(frozen=True)
class FleetFull:
    code: str = 'fleet_full'


def assign_slot(pod_id: str, taken: Mapping[str, int]) -> int | FleetFull:
    if pod_id in taken:
        return taken[pod_id]
    occupied = set(taken.values())
    return next((slot for slot in range(SLOT_COUNT) if slot not in occupied), FleetFull())


def slot_offset_s(slot: int) -> float:
    return slot * SLOT_LENGTH_S
