from __future__ import annotations

import pytest

from easy_social.captcha import (
    captcha_digest,
    captcha_matches,
    generate_captcha_code,
    normalize_captcha_answer,
    render_captcha_svg,
)

pytestmark = pytest.mark.unit


def test_generate_captcha_code_uses_readable_characters():
    code = generate_captcha_code()

    assert len(code) == 5
    assert code.isalnum()
    assert not set(code) & set("0O1IL")


def test_captcha_matching_ignores_case_and_spaces():
    expected_digest = captcha_digest("ABC7", "secret")

    assert normalize_captcha_answer(" a b C 7 ") == "ABC7"
    assert captcha_matches(expected_digest, " a b c 7 ", "secret")
    assert not captcha_matches(expected_digest, "ABC8", "secret")
    assert not captcha_matches(None, "ABC7", "secret")


def test_render_captcha_svg_contains_image_markup():
    svg = render_captcha_svg("ABCD2")

    assert svg.startswith("<svg")
    assert 'role="img"' in svg
    assert "ABCD2" not in svg
    for char in "ABCD2":
        assert f">{char}</text>" in svg
