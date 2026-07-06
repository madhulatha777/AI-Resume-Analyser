"""Unit tests for the four LLM chains using a fake (offline) LLM.

These verify the full prompt -> LLM -> JSON -> Pydantic pipeline, including the
score-clamping validators, without requiring a Groq API key.
"""

from __future__ import annotations

import json

import pytest

from src.analyzer import ResumeAnalysis, analyze_resume
from src.ats import ATSResult, compute_ats_score
from src.interview import InterviewQuestions, generate_interview_questions
from src.matcher import JobMatch, match_resume_to_job
from src.utils import LLMResponseError
from tests.conftest import make_fake_llm

RESUME = "Jane Doe. Python, Flask, Docker. 4 years experience."
JD = "Senior Python engineer. AWS, Kubernetes, FastAPI required."


def test_analyze_resume_parses_fake_response():
    payload = {
        "summary": "Strong mid-level engineer.",
        "strengths": ["Python", "APIs"],
        "weaknesses": ["Vague bullets"],
        "missing_skills": ["AWS"],
        "grammar_issues": ["None"],
        "formatting_suggestions": ["Use a single column"],
        "career_recommendations": ["Learn cloud"],
    }
    llm = make_fake_llm(json.dumps(payload))
    result = analyze_resume(RESUME, llm=llm)
    assert isinstance(result, ResumeAnalysis)
    assert result.summary == "Strong mid-level engineer."
    assert "AWS" in result.missing_skills


def test_compute_ats_clamps_scores():
    payload = {
        "ats_score": 130,  # should clamp to 100
        "keyword_score": -5,  # should clamp to 0
        "formatting_score": 70,
        "section_completeness_score": 80,
        "issues": ["Uses tables"],
        "recommendations": ["Remove tables"],
    }
    llm = make_fake_llm(json.dumps(payload))
    result = compute_ats_score(RESUME, JD, llm=llm)
    assert isinstance(result, ATSResult)
    assert result.ats_score == 100
    assert result.keyword_score == 0


def test_match_resume_to_job():
    payload = {
        "match_score": 72,
        "skills_match_score": 65,
        "experience_match_score": 70,
        "education_match_score": 90,
        "matched_skills": ["Python", "Docker"],
        "missing_skills": ["AWS", "Kubernetes"],
        "recommendations": ["Get AWS certified"],
        "verdict": "Good but light on cloud.",
    }
    llm = make_fake_llm(json.dumps(payload))
    result = match_resume_to_job(RESUME, JD, llm=llm)
    assert isinstance(result, JobMatch)
    assert result.match_score == 72
    assert "Kubernetes" in result.missing_skills


def test_generate_interview_questions_total():
    payload = {
        "technical_questions": ["q1", "q2", "q3"],
        "hr_questions": ["q4", "q5"],
        "project_questions": ["q6", "q7", "q8"],
    }
    llm = make_fake_llm(json.dumps(payload))
    result = generate_interview_questions(RESUME, JD, llm=llm)
    assert isinstance(result, InterviewQuestions)
    assert result.total == 8


def test_invalid_json_raises_llmresponseerror():
    llm = make_fake_llm("totally not json")
    with pytest.raises(LLMResponseError):
        analyze_resume(RESUME, llm=llm)
