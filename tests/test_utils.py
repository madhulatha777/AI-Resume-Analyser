"""Unit tests for src/utils.py."""

from __future__ import annotations

import pytest

from src.utils import (
    LLMResponseError,
    Settings,
    clamp_score,
    extract_json,
    truncate,
)


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fence():
    text = "Here is the result:\n```json\n{\"score\": 90}\n```"
    assert extract_json(text) == {"score": 90}


def test_extract_json_with_leading_prose_and_trailing_comma():
    text = 'Sure! {"items": ["a", "b",], "n": 2,}'
    assert extract_json(text) == {"items": ["a", "b"], "n": 2}


def test_extract_json_empty_raises():
    with pytest.raises(LLMResponseError):
        extract_json("")


def test_extract_json_no_object_raises():
    with pytest.raises(LLMResponseError):
        extract_json("no json here at all")


@pytest.mark.parametrize(
    "value,expected",
    [(50, 50), (-10, 0), (150, 100), ("80", 80), ("abc", 0), (87.6, 88)],
)
def test_clamp_score(value, expected):
    assert clamp_score(value) == expected


def test_truncate():
    assert truncate("abcdef", max_chars=3).startswith("abc")
    assert truncate("short", max_chars=100) == "short"


def test_settings_has_api_key():
    assert not Settings("your_groq_api_key_here", "m", 0.1, 1, 30).has_api_key
    assert not Settings("", "m", 0.1, 1, 30).has_api_key
    assert Settings("gsk_realkey", "m", 0.1, 1, 30).has_api_key
