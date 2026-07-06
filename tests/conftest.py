"""Pytest fixtures and helpers shared across the test suite.

Provides a ``fake_llm`` factory that turns a fixed JSON string into a LangChain
``Runnable`` mimicking a chat model. This lets us test the full
prompt -> LLM -> JSON -> Pydantic pipeline deterministically and offline (no
Groq API key required).
"""

from __future__ import annotations

import io
import os
import sys

import pytest
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

# Make the project root importable when tests are run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def make_fake_llm(json_response: str) -> RunnableLambda:
    """Return a Runnable that ignores its input and emits ``json_response``."""

    return RunnableLambda(lambda _inputs: AIMessage(content=json_response))


@pytest.fixture
def fake_llm():
    """Expose :func:`make_fake_llm` as a fixture."""

    return make_fake_llm


@pytest.fixture
def sample_resume_pdf_bytes() -> bytes:
    """A small, valid, text-based PDF for parser tests."""

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in [
        "Jane Doe",
        "Software Engineer",
        "Skills: Python, Flask, Docker",
        "Experience: Built REST APIs at Acme Corp.",
    ]:
        pdf.multi_cell(0, 8, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    buffer = io.BytesIO()
    buffer.write(bytes(pdf.output()))
    buffer.seek(0)
    return buffer.getvalue()
