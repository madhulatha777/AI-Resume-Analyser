"""Unit tests for src/parser.py."""

from __future__ import annotations

import pytest

from src.parser import clean_text, extract_text_from_pdf
from src.utils import PDFParsingError


def test_clean_text_normalizes_whitespace_and_bullets():
    raw = "Jane\xa0Doe\r\n\n\n\n- item1\n\u2022 item2   \t end"
    cleaned = clean_text(raw)
    assert "Jane Doe" in cleaned
    assert "\xa0" not in cleaned
    assert "\u2022" not in cleaned
    # No more than one blank line in a row.
    assert "\n\n\n" not in cleaned


def test_clean_text_empty():
    assert clean_text("") == ""


def test_extract_text_from_pdf_bytes(sample_resume_pdf_bytes):
    text = extract_text_from_pdf(sample_resume_pdf_bytes)
    assert "Jane Doe" in text
    assert "Python" in text


def test_extract_text_from_invalid_pdf_raises():
    with pytest.raises(PDFParsingError):
        extract_text_from_pdf(b"this is not a pdf")
