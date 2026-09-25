import pytest

from app.mesh.chat_policy import chat_origin, sender_is_reserved


@pytest.mark.parametrize(
    'name',
    ['MDRRMO', 'mdrrm0', 'M.D.R.R.M.O', 'Coast Guard', 'PCG', 'PAGASA', 'Admin', 'Official'],
)
def test_sender_is_reserved_for_official_names(name):
    assert sender_is_reserved(name)


@pytest.mark.parametrize('name', ['Juan', 'Mang Dodong', 'Bangka 7'])
def test_sender_is_not_reserved_for_vessel_names(name):
    assert not sender_is_reserved(name)


@pytest.mark.parametrize(
    ('credential_kind', 'expected'),
    [('operator', 'mdrrmo'), ('vessel', 'app'), ('gateway', 'mesh'), (None, 'app')],
)
def test_chat_origin_is_derived_from_credential(credential_kind, expected):
    assert chat_origin(credential_kind) == expected
