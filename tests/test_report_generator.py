"""Unit tests for src/report_generator.py."""

from __future__ import annotations

from src.analyzer import ResumeAnalysis
from src.ats import ATSResult
from src.interview import InterviewQuestions
from src.matcher import JobMatch
from src.report_generator import build_pdf_report


def _sample_results():
    analysis = ResumeAnalysis(
        summary="Solid engineer with smart quotes \u201cdemo\u201d and em-dash \u2014.",
        strengths=["Python", "Teamwork"],
        weaknesses=["Vague bullets"],
        missing_skills=["AWS"],
        grammar_issues=["None"],
        formatting_suggestions=["Single column"],
        career_recommendations=["Learn cloud"],
    )
    ats = ATSResult(
        ats_score=82,
        keyword_score=70,
        formatting_score=90,
        section_completeness_score=85,
        issues=["Uses a table"],
        recommendations=["Remove the table"],
    )
    match = JobMatch(
        match_score=75,
        skills_match_score=70,
        experience_match_score=72,
        education_match_score=90,
        matched_skills=["Python"],
        missing_skills=["Kubernetes"],
        recommendations=["Learn k8s"],
        verdict="Good fit overall.",
    )
    interview = InterviewQuestions(
        technical_questions=["Explain GIL"],
        hr_questions=["Tell me about yourself"],
        project_questions=["Describe your finance tracker"],
    )
    return analysis, ats, match, interview


def test_build_pdf_report_returns_pdf_bytes():
    analysis, ats, match, interview = _sample_results()
    pdf = build_pdf_report(
        candidate_name="Jane Doe",
        analysis=analysis,
        ats=ats,
        match=match,
        interview=interview,
    )
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000  # non-trivial document


def test_build_pdf_report_with_partial_results():
    analysis, _, _, _ = _sample_results()
    pdf = build_pdf_report(candidate_name="Partial", analysis=analysis)
    assert pdf.startswith(b"%PDF")
