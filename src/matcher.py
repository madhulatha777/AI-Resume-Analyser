"""Job Matching chain.

Purpose
-------
Compares a resume against a job description and returns structured match
scores plus matched / missing skills and improvement recommendations.

Connections
-----------
* Uses ``JOB_MATCH_PROMPT`` from ``prompts.py``.
* Uses ``run_structured_chain`` / ``clamp_score`` from ``utils.py``.
* Consumed by ``app.py`` (Job Match tab) and ``report_generator.py``.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator

from .prompts import JOB_MATCH_PROMPT
from .utils import clamp_score, run_structured_chain, truncate


class JobMatch(BaseModel):
    """Structured output of the job-matching chain."""

    match_score: int = Field(default=0)
    skills_match_score: int = Field(default=0)
    experience_match_score: int = Field(default=0)
    education_match_score: int = Field(default=0)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    verdict: str = Field(default="")

    @field_validator(
        "match_score",
        "skills_match_score",
        "experience_match_score",
        "education_match_score",
        mode="before",
    )
    @classmethod
    def _clamp(cls, value: object) -> int:
        return clamp_score(value)


def match_resume_to_job(resume_text: str, job_description: str, llm=None) -> JobMatch:
    """Score how well ``resume_text`` matches ``job_description``."""

    return run_structured_chain(
        JOB_MATCH_PROMPT,
        JobMatch,
        {
            "resume_text": truncate(resume_text),
            "job_description": truncate(job_description),
        },
        llm=llm,
    )
