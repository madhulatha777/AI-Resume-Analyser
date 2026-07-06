"""Interview Questions generation chain.

Purpose
-------
Generates ~15 tailored interview questions (technical, HR, and project-based)
from a resume and, optionally, a job description.

Connections
-----------
* Uses ``INTERVIEW_PROMPT`` from ``prompts.py``.
* Uses ``run_structured_chain`` from ``utils.py``.
* Consumed by ``app.py`` (Interview Prep tab) and ``report_generator.py``.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from .prompts import INTERVIEW_PROMPT
from .utils import run_structured_chain, truncate


class InterviewQuestions(BaseModel):
    """Structured output of the interview-questions chain."""

    technical_questions: List[str] = Field(default_factory=list)
    hr_questions: List[str] = Field(default_factory=list)
    project_questions: List[str] = Field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of generated questions across all categories."""
        return (
            len(self.technical_questions)
            + len(self.hr_questions)
            + len(self.project_questions)
        )


def generate_interview_questions(
    resume_text: str,
    job_description: str = "",
    llm=None,
) -> InterviewQuestions:
    """Generate interview questions tailored to the resume (and optional JD)."""

    return run_structured_chain(
        INTERVIEW_PROMPT,
        InterviewQuestions,
        {
            "resume_text": truncate(resume_text),
            "job_description": truncate(job_description or "Not provided."),
        },
        llm=llm,
    )
