"""PDF report generation.

Purpose
-------
Assembles the outputs of every chain (resume analysis, ATS score, job match,
interview questions) into a single, nicely formatted PDF report that the user
can download.

Implementation
--------------
Uses ``fpdf2`` (imported as ``fpdf``) with the built-in Helvetica font. Because
the core fonts are Latin-1, all text is sanitized to the Latin-1 range so the
report never crashes on emoji or smart quotes coming from the LLM.

Connections
-----------
* Consumes :class:`~src.analyzer.ResumeAnalysis`,
  :class:`~src.ats.ATSResult`, :class:`~src.matcher.JobMatch`, and
  :class:`~src.interview.InterviewQuestions`.
* Called by ``app.py`` (Report tab) which streams the returned bytes through
  ``st.download_button``.
"""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .analyzer import ResumeAnalysis
from .ats import ATSResult
from .interview import InterviewQuestions
from .matcher import JobMatch


def _latin1(text: str) -> str:
    """Make text safe for the built-in Latin-1 PDF fonts."""

    if text is None:
        return ""
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u2022": "-",
        "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


class _ReportPDF(FPDF):
    """FPDF subclass with a consistent header and footer."""

    def header(self) -> None:  # noqa: D401 - fpdf hook.
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "AI Resume Analyzer - Report", align="R")
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:  # noqa: D401 - fpdf hook.
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


class ReportBuilder:
    """Incrementally builds a PDF report and renders it to bytes."""

    def __init__(self, candidate_name: str = "Candidate") -> None:
        self.candidate_name = candidate_name
        self.pdf = _ReportPDF()
        self.pdf.set_auto_page_break(auto=True, margin=18)
        self.pdf.add_page()
        self._title_page()

    # -- low-level helpers ------------------------------------------------- #
    def _title_page(self) -> None:
        self.pdf.set_font("Helvetica", "B", 22)
        self.pdf.ln(6)
        self._line(_latin1("AI Resume Analyzer & Job Match Report"), 10)
        self.pdf.set_font("Helvetica", "", 12)
        self.pdf.set_text_color(90, 90, 90)
        timestamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        self._line(_latin1(f"Candidate: {self.candidate_name}"), 8)
        self._line(_latin1(f"Generated: {timestamp}"), 8)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(4)

    def _section_title(self, title: str) -> None:
        self.pdf.ln(3)
        self.pdf.set_font("Helvetica", "B", 15)
        self.pdf.set_fill_color(33, 102, 172)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.cell(0, 9, _latin1(f"  {title}"), fill=True)
        self.pdf.ln(11)
        self.pdf.set_text_color(0, 0, 0)

    def _line(self, text: str, height: float) -> None:
        """Write one wrapped line and return the cursor to the left margin."""
        self.pdf.multi_cell(
            0, height, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

    def _subtitle(self, text: str) -> None:
        self.pdf.set_font("Helvetica", "B", 11)
        self._line(_latin1(text), 6)

    def _paragraph(self, text: str) -> None:
        self.pdf.set_font("Helvetica", "", 11)
        self._line(_latin1(text), 6)
        self.pdf.ln(1)

    def _bullets(self, items: List[str]) -> None:
        self.pdf.set_font("Helvetica", "", 11)
        if not items:
            self._line(_latin1("- (none)"), 6)
            return
        for item in items:
            self._line(_latin1(f"- {item}"), 6)
        self.pdf.ln(1)

    def _score_line(self, label: str, score: int) -> None:
        self.pdf.set_font("Helvetica", "B", 11)
        self.pdf.cell(70, 7, _latin1(f"{label}:"))
        self.pdf.set_font("Helvetica", "", 11)
        self.pdf.cell(0, 7, _latin1(f"{score}/100"))
        self.pdf.ln(7)

    # -- public sections --------------------------------------------------- #
    def add_resume_analysis(self, analysis: ResumeAnalysis) -> "ReportBuilder":
        self._section_title("1. Resume Analysis")
        self._subtitle("Summary")
        self._paragraph(analysis.summary or "N/A")
        self._subtitle("Strengths")
        self._bullets(analysis.strengths)
        self._subtitle("Weaknesses")
        self._bullets(analysis.weaknesses)
        self._subtitle("Missing Skills")
        self._bullets(analysis.missing_skills)
        self._subtitle("Grammar Issues")
        self._bullets(analysis.grammar_issues)
        self._subtitle("Formatting Suggestions")
        self._bullets(analysis.formatting_suggestions)
        self._subtitle("Career Recommendations")
        self._bullets(analysis.career_recommendations)
        return self

    def add_ats(self, ats: ATSResult) -> "ReportBuilder":
        self._section_title("2. ATS Score")
        self._score_line("Overall ATS Score", ats.ats_score)
        self._score_line("Keyword Optimization", ats.keyword_score)
        self._score_line("Formatting", ats.formatting_score)
        self._score_line("Section Completeness", ats.section_completeness_score)
        self.pdf.ln(2)
        self._subtitle("Issues")
        self._bullets(ats.issues)
        self._subtitle("Recommendations")
        self._bullets(ats.recommendations)
        return self

    def add_job_match(self, match: JobMatch) -> "ReportBuilder":
        self._section_title("3. Job Match Score")
        self._score_line("Overall Match", match.match_score)
        self._score_line("Skills Match", match.skills_match_score)
        self._score_line("Experience Match", match.experience_match_score)
        self._score_line("Education Match", match.education_match_score)
        self.pdf.ln(1)
        if match.verdict:
            self._subtitle("Verdict")
            self._paragraph(match.verdict)
        self._subtitle("Matched Skills")
        self._bullets(match.matched_skills)
        self._subtitle("Missing Skills")
        self._bullets(match.missing_skills)
        self._subtitle("Recommendations")
        self._bullets(match.recommendations)
        return self

    def add_interview(self, interview: InterviewQuestions) -> "ReportBuilder":
        self._section_title("4. Interview Questions")
        self._subtitle("Technical Questions")
        self._bullets(interview.technical_questions)
        self._subtitle("Project Questions")
        self._bullets(interview.project_questions)
        self._subtitle("HR Questions")
        self._bullets(interview.hr_questions)
        return self

    def render(self) -> bytes:
        """Return the finished PDF as bytes."""

        output = self.pdf.output()
        # fpdf2 returns a bytearray; normalize to immutable bytes.
        return bytes(output)


def build_pdf_report(
    candidate_name: str = "Candidate",
    analysis: Optional[ResumeAnalysis] = None,
    ats: Optional[ATSResult] = None,
    match: Optional[JobMatch] = None,
    interview: Optional[InterviewQuestions] = None,
) -> bytes:
    """Build a full PDF report from whichever results are available.

    Every section is optional; only the provided results are rendered. Returns
    the PDF as ``bytes`` ready for ``st.download_button`` or writing to disk.
    """

    builder = ReportBuilder(candidate_name=candidate_name)
    if analysis is not None:
        builder.add_resume_analysis(analysis)
    if ats is not None:
        builder.add_ats(ats)
    if match is not None:
        builder.add_job_match(match)
    if interview is not None:
        builder.add_interview(interview)
    return builder.render()
