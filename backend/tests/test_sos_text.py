from app.incidents.text import truncate_utf8


def test_ascii_is_unchanged():
    assert truncate_utf8('safe at dock', 64) == 'safe at dock'


def test_multibyte_character_at_limit_is_dropped_whole():
    assert truncate_utf8('a' * 63 + '\u00f1', 64) == 'a' * 63


def test_four_byte_character_at_limit_is_dropped_whole():
    assert truncate_utf8('a' * 61 + '\U0001f6a4', 64) == 'a' * 61


def test_result_never_exceeds_byte_limit():
    for limit in range(65):
        assert len(truncate_utf8('\u00f1' * 40, limit).encode('utf-8')) <= limit


def test_empty_text_stays_empty():
    assert truncate_utf8('', 64) == ''
