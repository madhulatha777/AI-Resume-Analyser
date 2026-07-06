"""Resume Analysis chain.

Purpose
-------
Defines the :class:`ResumeAnalysis` Pydantic schema and the
:func:`analyze_resume` function that runs the resume-analysis prompt through
the LLM and returns a validated, structured result.

Connections
-----------
* Uses ``RESUME_ANALYSIS_PROMPT`` from ``prompts.py``.
* Uses ``run_structured_chain`` from ``utils.py`` for the prompt → LLM → JSON →
  Pydantic pipeline.
* Consumed by ``app.py`` (Resume Analysis tab) and ``report_generator.py``.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from .prompts import RESUME_ANALYSIS_PROMPT
from .utils import run_structured_chain, truncate


class ResumeAnalysis(BaseModel):
    """Structured output of the resume analysis chain."""

    summary: str = Field(default="")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    grammar_issues: List[str] = Field(default_factory=list)
    formatting_suggestions: List[str] = Field(default_factory=list)
    career_recommendations: List[str] = Field(default_factory=list)


def analyze_resume(resume_text: str, llm=None) -> ResumeAnalysis:
    """Analyze a resume and return a :class:`ResumeAnalysis`.

    Parameters
    ----------
    resume_text:
        The cleaned resume text (see ``parser.extract_text_from_pdf``).
    llm:
        Optional LLM client (mainly for testing). Defaults to the cached Groq
        client from :func:`src.utils.get_llm`.
    """

    return run_structured_chain(
        RESUME_ANALYSIS_PROMPT,
        ResumeAnalysis,
        {"resume_text": truncate(resume_text)},
        llm=llm,
    )
