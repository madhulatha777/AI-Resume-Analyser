"""ATS (Applicant Tracking System) scoring chain.

Purpose
-------
Estimates how well a resume will perform when parsed by an automated ATS,
either in general or against a specific job description. Returns an overall
score plus keyword / formatting / section sub-scores and concrete fixes.

Connections
-----------
* Uses ``ATS_PROMPT_RESUME_ONLY`` / ``ATS_PROMPT_WITH_JD`` from ``prompts.py``.
* Uses ``run_structured_chain`` / ``clamp_score`` from ``utils.py``.
* Consumed by ``app.py`` (ATS Score tab) and ``report_generator.py``.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .prompts import ATS_PROMPT_RESUME_ONLY, ATS_PROMPT_WITH_JD
from .utils import clamp_score, run_structured_chain, truncate


class ATSResult(BaseModel):
    """Structured output of the ATS chain."""

    ats_score: int = Field(default=0)
    keyword_score: int = Field(default=0)
    formatting_score: int = Field(default=0)
    section_completeness_score: int = Field(default=0)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    @field_validator(
        "ats_score",
        "keyword_score",
        "formatting_score",
        "section_completeness_score",
        mode="before",
    )
    @classmethod
    def _clamp(cls, value: object) -> int:
        return clamp_score(value)


def compute_ats_score(
    resume_text: str,
    job_description: Optional[str] = None,
    llm=None,
) -> ATSResult:
    """Compute an ATS compatibility report.

    When ``job_description`` is provided, keyword overlap with the JD is
    weighted heavily; otherwise the resume is scored for general ATS
    friendliness.
    """

    if job_description and job_description.strip():
        return run_structured_chain(
            ATS_PROMPT_WITH_JD,
            ATSResult,
            {
                "resume_text": truncate(resume_text),
                "job_description": truncate(job_description),
            },
            llm=llm,
        )

    return run_structured_chain(
        ATS_PROMPT_RESUME_ONLY,
        ATSResult,
        {"resume_text": truncate(resume_text)},
        llm=llm,
    )
