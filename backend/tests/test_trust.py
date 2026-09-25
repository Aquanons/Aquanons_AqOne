from datetime import UTC, datetime

from app.incidents.trust import vessel_verified


def test_vessel_is_verified_with_active_device():
    assert vessel_verified(True, None)


def test_vessel_is_verified_after_responder_confirmation():
    assert vessel_verified(False, datetime.now(UTC))


def test_unconfirmed_vessel_without_device_is_not_verified():
    assert not vessel_verified(False, None)
