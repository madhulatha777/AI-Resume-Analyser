"""PDF parsing and text preprocessing.

Purpose
-------
Turns an uploaded PDF (resume or job description) into clean, analyzable text.
Uses ``pdfplumber`` as the primary extractor (best layout fidelity) and falls
back to ``PyPDF2`` if pdfplumber yields nothing. Includes a lightweight text
cleaner that normalizes whitespace and strips common PDF artifacts.

Connections
-----------
``app.py`` calls :func:`extract_text_from_pdf` / :func:`extract_text_from_upload`
on uploaded files, then passes the cleaned text to the analysis chains in
``analyzer.py``, ``ats.py``, ``matcher.py`` and ``interview.py``.
"""

from __future__ import annotations

import io
import re
from typing import BinaryIO, Union

from .utils import PDFParsingError, logger

# Accept a path, raw bytes, or any binary file-like object (e.g. a Streamlit
# UploadedFile).
PDFSource = Union[str, bytes, BinaryIO]


def _to_stream(source: PDFSource) -> io.BytesIO:
    """Normalize any supported PDF source into a fresh ``BytesIO`` stream."""

    if isinstance(source, str):
        with open(source, "rb") as fh:
            return io.BytesIO(fh.read())
    if isinstance(source, (bytes, bytearray)):
        return io.BytesIO(bytes(source))
    # File-like object (Streamlit UploadedFile, open file handle, etc.).
    if hasattr(source, "read"):
        try:
            source.seek(0)
        except (OSError, ValueError):
            pass
        return io.BytesIO(source.read())
    raise PDFParsingError(f"Unsupported PDF source type: {type(source)!r}")


def _extract_with_pdfplumber(stream: io.BytesIO) -> str:
    import pdfplumber

    stream.seek(0)
    pages: list[str] = []
    with pdfplumber.open(stream) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _extract_with_pypdf2(stream: io.BytesIO) -> str:
    from PyPDF2 import PdfReader

    stream.seek(0)
    reader = PdfReader(stream)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def clean_text(text: str) -> str:
    """Normalize extracted PDF text.

    * Converts non-breaking spaces and common bullet glyphs to plain text.
    * Collapses runs of spaces/tabs.
    * Trims trailing whitespace per line and limits consecutive blank lines.
    """

    if not text:
        return ""

    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize a variety of bullet characters to a simple hyphen.
    text = re.sub(r"[•▪◦●○‣·]", "-", text)

    # Collapse horizontal whitespace.
    text = re.sub(r"[ \t]+", " ", text)

    # Trim each line and drop excessive blank lines.
    lines = [line.strip() for line in text.split("\n")]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def extract_text_from_pdf(source: PDFSource) -> str:
    """Extract and clean text from a PDF.

    Tries pdfplumber first, then PyPDF2. Raises :class:`PDFParsingError` if the
    file cannot be read or contains no extractable text (e.g. a scanned image).
    """

    stream = _to_stream(source)

    raw = ""
    try:
        raw = _extract_with_pdfplumber(stream)
    except Exception as exc:  # noqa: BLE001 - we have a fallback.
        logger.warning("pdfplumber extraction failed, trying PyPDF2: %s", exc)

    if not raw.strip():
        try:
            raw = _extract_with_pypdf2(stream)
        except Exception as exc:  # noqa: BLE001
            raise PDFParsingError(
                "Failed to read the PDF with both pdfplumber and PyPDF2. "
                "The file may be corrupt or password protected."
            ) from exc

    cleaned = clean_text(raw)
    if not cleaned:
        raise PDFParsingError(
            "No text could be extracted. If this is a scanned/image-only PDF, "
            "please upload a text-based PDF instead."
        )

    logger.info("Extracted %d characters of text from PDF.", len(cleaned))
    return cleaned


def extract_text_from_upload(uploaded_file) -> str:
    """Convenience wrapper for a Streamlit ``UploadedFile``.

    Raises :class:`PDFParsingError` if nothing was uploaded.
    """

    if uploaded_file is None:
        raise PDFParsingError("No file was uploaded.")
    return extract_text_from_pdf(uploaded_file)
