"""Plan 69 Phase 2, slot assignment (docs/fleet-watch/PHASE_2_PLAN.md T2-37 to T2-42; spec 68 REQ-031)."""

from app.fleet_watch.slots import SLOT_COUNT, SLOT_LENGTH_S, FleetFull, assign_slot, slot_offset_s


def full_registry():
    return {f'AQ-{slot:08X}': slot for slot in range(SLOT_COUNT)}


def test_slot_grid_matches_docs_02():
    assert SLOT_COUNT == 80
    assert SLOT_LENGTH_S == 1.5


def test_t2_37_first_pod_gets_slot_0():
    assert assign_slot('AQ-A1B2C3D4', {}) == 0


def test_t2_38_lowest_free_slot_is_used():
    assert assign_slot('AQ-A1B2C3D4', {'AQ-1': 0, 'AQ-2': 1, 'AQ-4': 3}) == 2


def test_t2_39_re_enrolling_keeps_the_slot():
    assert assign_slot('AQ-A1B2C3D4', {'AQ-1': 0, 'AQ-A1B2C3D4': 7}) == 7


def test_t2_40_the_81st_pod_is_refused():
    result = assign_slot('AQ-NEWPOD01', full_registry())
    assert isinstance(result, FleetFull)
    assert result.code == 'fleet_full'


def test_t2_41_an_enrolled_pod_keeps_its_slot_in_a_full_fleet():
    registry = full_registry()
    assert assign_slot('AQ-0000002A', registry) == 42


def test_t2_42_slot_offset_matches_docs_02():
    assert slot_offset_s(0) == 0.0
    assert slot_offset_s(7) == 10.5
    assert slot_offset_s(79) == 118.5
