"""Unit tests for Pydantic models and chain helpers (no LLM calls)."""

from src.analyzer import ResumeAnalysisResult, ResumeImprovementResult
from src.ats import ATSResult, ats_scores_to_dataframe
from src.interview import InterviewQuestionsResult
from src.matcher import JobMatchResult, match_scores_to_dataframe


class TestResumeAnalysisResult:
    def test_model_creation(self):
        result = ResumeAnalysisResult(
            summary="Experienced developer",
            strengths=["Python expertise"],
            weaknesses=["Weak bullet points"],
            missing_skills=["Kubernetes"],
            improvements=["Add metrics to bullets"],
            ats_compatibility_score=72,
        )
        assert result.summary == "Experienced developer"
        assert result.ats_compatibility_score == 72


class TestJobMatchResult:
    def test_dataframe_conversion(self):
        result = JobMatchResult(
            match_score=82,
            skills_match_score=85,
            experience_match_score=78,
            education_match_score=90,
            matched_skills=["Python", "FastAPI"],
            missing_skills=["Kubernetes"],
            recommendations=["Add cloud experience"],
        )
        df = match_scores_to_dataframe(result)
        assert len(df) == 4
        assert df["score"].tolist() == [82, 85, 78, 90]


class TestATSResult:
    def test_dataframe_conversion(self):
        result = ATSResult(
            ats_score=85,
            keyword_optimization_score=80,
            formatting_score=90,
            section_completeness_score=85,
            issues=["Missing keywords"],
            recommendations=["Add skills section"],
            explanation="Good overall ATS compatibility.",
        )
        df = ats_scores_to_dataframe(result)
        assert len(df) == 4
        assert df.iloc[0]["score"] == 85


class TestInterviewResult:
    def test_all_questions_property(self):
        result = InterviewQuestionsResult(
            technical_questions=["Q1", "Q2", "Q3", "Q4", "Q5"],
            hr_questions=["H1", "H2", "H3", "H4", "H5"],
            project_questions=["P1", "P2", "P3", "P4", "P5"],
        )
        assert result.total_count == 15
        assert len(result.all_questions) == 15


class TestImprovementResult:
    def test_examples_optional(self):
        result = ResumeImprovementResult(
            project_improvements=["Improved project bullet"],
            skills_section_improvements=["Group skills by category"],
            summary_improvements=["Stronger opening line"],
            action_verbs=["Developed", "Architected"],
        )
        assert result.examples == []
