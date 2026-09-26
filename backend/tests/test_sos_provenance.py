from app.incidents.trust import SosProvenance, sos_provenance

# SEC-06 (docs/security-audit): the transport and trust a caller claims are
# only believed when its credentials back them up.


def _provenance(**overrides):
    values = dict(
        vessel_id='V1',
        requested_tier='phone_verified',
        source='direct',
        buoy_id=None,
        src_id=None,
        seq=None,
        device_vessel_id=None,
        gateway_authenticated=False,
    )
    values.update(overrides)
    return sos_provenance(**values)


def test_an_anonymous_direct_call_is_self_declared():
    assert _provenance() == SosProvenance('self_declared', None, None, None, True, False)


def test_a_device_bound_to_the_same_vessel_may_claim_phone_verified():
    assert _provenance(device_vessel_id='V1').trust_tier == 'phone_verified'


def test_a_device_bound_to_another_vessel_stays_self_declared():
    assert _provenance(device_vessel_id='V2').trust_tier == 'self_declared'


def test_a_bound_device_that_does_not_ask_for_phone_verified_stays_self_declared():
    assert _provenance(device_vessel_id='V1', requested_tier='self_declared').trust_tier == 'self_declared'


def test_the_gateway_keeps_the_buoy_route_fields():
    provenance = _provenance(source='buoy', buoy_id='BUOY01', src_id=7, seq=3, gateway_authenticated=True)
    assert provenance == SosProvenance('self_declared', 'BUOY01', 7, 3, False, True)


def test_a_buoy_claim_without_the_gateway_key_is_stored_as_direct():
    provenance = _provenance(source='buoy', buoy_id='BUOY01', src_id=7, seq=3)
    assert provenance == SosProvenance('self_declared', None, None, None, True, False)


def test_the_gateway_key_on_a_direct_call_does_not_make_it_a_buoy_delivery():
    assert _provenance(gateway_authenticated=True, buoy_id='BUOY01').delivered_direct is True
