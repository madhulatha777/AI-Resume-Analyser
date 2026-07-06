"""AI Resume Analyzer & Job Match Scorer — Streamlit UI.

Purpose
-------
The single entry point of the application. It wires together every module in
``src`` into a polished, tab-based Streamlit interface:

* **Sidebar** — API key status, model settings, resume upload, JD input.
* **Resume Analysis** tab — strengths, weaknesses, missing skills, grammar,
  formatting, and career recommendations.
* **ATS Score** tab — overall + sub-scores with gauges, issues, fixes.
* **Job Match** tab — match scores, matched/missing skills, recommendations.
* **Interview Prep** tab — ~15 tailored technical/HR/project questions.
* **Report** tab — one-click downloadable PDF report.

Run with::

    streamlit run app.py

Connections
-----------
Calls ``parser`` (PDF extraction), ``analyzer`` / ``ats`` / ``matcher`` /
``interview`` (LLM chains), and ``report_generator`` (PDF export). Reads config
via ``utils.get_settings``.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analyzer import ResumeAnalysis, analyze_resume
from src.ats import ATSResult, compute_ats_score
from src.interview import InterviewQuestions, generate_interview_questions
from src.matcher import JobMatch, match_resume_to_job
from src.parser import extract_text_from_upload
from src.report_generator import build_pdf_report
from src.utils import (
    MissingAPIKeyError,
    PDFParsingError,
    ResumeAnalyzerError,
    get_settings,
)

st.set_page_config(
    page_title="AI Resume Analyzer & Job Match Scorer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# # --------------------------------------------------------------------------- #
# # Styling
# # --------------------------------------------------------------------------- #
# st.markdown(
#     """
#     <style>
#     .main > div { padding-top: 1.5rem; }
#     .score-card {
#         border-radius: 14px; padding: 18px 20px; color: #ffffff;
#         box-shadow: 0 4px 14px rgba(0,0,0,0.12); margin-bottom: 8px;
#     }
#     .score-card h1 { font-size: 2.4rem; margin: 0; }
#     .score-card p { margin: 0; opacity: 0.9; font-size: 0.95rem; }
#     .pill {
#         display:inline-block; padding:4px 10px; border-radius:999px;
#         background:#eef2ff; color:#3730a3; margin:3px; font-size:0.85rem;
#     }
#     .pill-missing { background:#fef2f2; color:#991b1b; }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )










# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
st.markdown(
    """
<style>

/* ===== Animated Multi-Color Background ===== */
.stApp {
    background: linear-gradient(
        -45deg,
        #0f172a,
        #1e3a8a,
        #7c3aed,
        #ec4899,
        #06b6d4,
        #10b981
    );
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
}

/* ===== Gradient Animation ===== */
@keyframes gradientBG {
    0% {
        background-position: 0% 50%;
    }
    50% {
        background-position: 100% 50%;
    }
    100% {
        background-position: 0% 50%;
    }
}

/* ===== Global Text ===== */
html, body,
h1, h2, h3, h4, h5, h6,
p, div, span, label {
    color: white !important;
}

/* ===== Sidebar ===== */
section[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.85);
    backdrop-filter: blur(15px);
}

/* ===== Cards ===== */
.score-card {
    border-radius: 16px;
    padding: 18px 20px;
    color: white;
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    margin-bottom: 10px;
    backdrop-filter: blur(10px);
}

/* ===== Pills ===== */
.pill {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.15);
    color: white;
    margin: 3px;
    font-size: 0.85rem;
}

.pill-missing {
    background: rgba(255,80,80,0.25);
    color: white;
}

/* ===== Buttons ===== */
.stButton > button {
    background: linear-gradient(
        135deg,
        #667eea,
        #764ba2
    );
    color: white !important;
    border: none;
    border-radius: 12px;
    font-weight: bold;
    padding: 0.6rem 1rem;
}

/* ===== Inputs ===== */
.stTextInput input,
.stTextArea textarea {
    background: rgba(255,255,255,0.10);
    color: white !important;
    border-radius: 12px;
}

/* ===== File Uploaders ===== */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 10px;
}

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab"] {
    color: white !important;
    font-weight: 600;
}

/* ===== Metrics ===== */
[data-testid="stMetricValue"] {
    color: white !important;
}

/* ===== Progress Bar ===== */
.stProgress > div > div > div > div {
    background: linear-gradient(
        90deg,
        #00c9ff,
        #92fe9d
    );
}

/* ===== Expander ===== */
.streamlit-expanderHeader {
    color: white !important;
}

/* ===== DataFrames ===== */
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
}

</style>
""",
    unsafe_allow_html=True,
)











# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
def _init_state() -> None:
    defaults = {
        "resume_text": "",
        "jd_text": "",
        "analysis": None,
        "ats": None,
        "match": None,
        "interview": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


_init_state()


# --------------------------------------------------------------------------- #
# Small UI helpers
# --------------------------------------------------------------------------- #
def _score_color(score: int) -> str:
    if score >= 75:
        return "linear-gradient(135deg,#16a34a,#22c55e)"
    if score >= 50:
        return "linear-gradient(135deg,#d97706,#f59e0b)"
    return "linear-gradient(135deg,#dc2626,#ef4444)"


def score_card(label: str, score: int) -> None:
    st.markdown(
        f"""
        <div class="score-card" style="background:{_score_color(score)};">
            <h1>{score}<span style="font-size:1rem;">/100</span></h1>
            <p>{label}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pills(items: list[str], missing: bool = False) -> None:
    cls = "pill pill-missing" if missing else "pill"
    if not items:
        st.caption("None reported.")
        return
    st.markdown(
        " ".join(f'<span class="{cls}">{i}</span>' for i in items),
        unsafe_allow_html=True,
    )


def require_resume() -> bool:
    if not st.session_state.resume_text:
        st.info("⬅️ Upload a resume PDF in the sidebar to begin.")
        return False
    return True


def require_api_key() -> bool:
    if not get_settings().has_api_key:
        st.error(
            "No Groq API key configured. Add `GROQ_API_KEY` to your `.env` "
            "file (see `.env.example`) and restart the app."
        )
        return False
    return True


def run_safely(fn, spinner: str):
    """Execute ``fn`` with a spinner and friendly error handling."""

    try:
        with st.spinner(spinner):
            return fn()
    except MissingAPIKeyError as exc:
        st.error(str(exc))
    except ResumeAnalyzerError as exc:
        st.error(f"Something went wrong: {exc}")
    except Exception as exc:  # noqa: BLE001 - last-resort guard for the UI.
        st.error(f"Unexpected error: {exc}")
    return None


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def render_sidebar() -> None:
    with st.sidebar:
        st.title("📄 Resume Analyzer")
        settings = get_settings()

        if settings.has_api_key:
            st.success(f"Groq connected · `{settings.model}`")
        else:
            st.warning("Groq API key missing — add it to `.env`.")

        st.divider()
        st.subheader("1 · Upload Resume")
        resume_file = st.file_uploader(
            "Resume (PDF)", type=["pdf"], key="resume_uploader"
        )
        if resume_file is not None:
            try:
                st.session_state.resume_text = extract_text_from_upload(resume_file)
                st.success(
                    f"Parsed {len(st.session_state.resume_text):,} characters."
                )
            except PDFParsingError as exc:
                st.error(str(exc))

        st.divider()
        st.subheader("2 · Job Description")
        jd_mode = st.radio(
            "Provide JD via", ["Paste text", "Upload PDF"], horizontal=True
        )
        if jd_mode == "Paste text":
            st.session_state.jd_text = st.text_area(
                "Paste the job description",
                value=st.session_state.jd_text,
                height=160,
                placeholder="Paste the full job description here...",
            )
        else:
            jd_file = st.file_uploader(
                "Job description (PDF)", type=["pdf"], key="jd_uploader"
            )
            if jd_file is not None:
                try:
                    st.session_state.jd_text = extract_text_from_upload(jd_file)
                    st.success(f"Parsed JD ({len(st.session_state.jd_text):,} chars).")
                except PDFParsingError as exc:
                    st.error(str(exc))

        st.divider()
        if st.button("🔄 Reset session", use_container_width=True):
            for key in ["analysis", "ats", "match", "interview"]:
                st.session_state[key] = None
            st.success("Cleared previous results.")


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
def tab_resume_analysis() -> None:
    st.subheader("Resume Analysis")
    if not require_resume():
        return

    with st.expander("📄 Extracted resume text", expanded=False):
        st.text(st.session_state.resume_text)

    if st.button("Analyze Resume", type="primary"):
        if not require_api_key():
            return
        result = run_safely(
            lambda: analyze_resume(st.session_state.resume_text),
            "Analyzing your resume...",
        )
        if result is not None:
            st.session_state.analysis = result

    analysis: ResumeAnalysis | None = st.session_state.analysis
    if analysis is None:
        return

    st.success("Analysis complete.")
    st.markdown("#### Summary")
    st.write(analysis.summary)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ✅ Strengths")
        for item in analysis.strengths:
            st.markdown(f"- {item}")
        st.markdown("#### 🧩 Missing Skills")
        pills(analysis.missing_skills, missing=True)
    with col2:
        st.markdown("#### ⚠️ Weaknesses")
        for item in analysis.weaknesses:
            st.markdown(f"- {item}")
        st.markdown("#### ✍️ Grammar Issues")
        for item in analysis.grammar_issues:
            st.markdown(f"- {item}")

    with st.expander("🎨 Formatting suggestions"):
        for item in analysis.formatting_suggestions:
            st.markdown(f"- {item}")
    with st.expander("🚀 Career recommendations"):
        for item in analysis.career_recommendations:
            st.markdown(f"- {item}")


def tab_ats() -> None:
    st.subheader("ATS Score")
    if not require_resume():
        return

    use_jd = bool(st.session_state.jd_text.strip())
    st.caption(
        "Scoring against the provided job description."
        if use_jd
        else "Scoring for general ATS friendliness (add a JD for keyword scoring)."
    )

    if st.button("Check ATS Score", type="primary"):
        if not require_api_key():
            return
        result = run_safely(
            lambda: compute_ats_score(
                st.session_state.resume_text,
                st.session_state.jd_text if use_jd else None,
            ),
            "Scoring ATS compatibility...",
        )
        if result is not None:
            st.session_state.ats = result

    ats: ATSResult | None = st.session_state.ats
    if ats is None:
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        score_card("Overall ATS", ats.ats_score)
    with c2:
        score_card("Keywords", ats.keyword_score)
    with c3:
        score_card("Formatting", ats.formatting_score)
    with c4:
        score_card("Sections", ats.section_completeness_score)

    st.progress(ats.ats_score / 100, text=f"Overall ATS score: {ats.ats_score}/100")

    chart_df = pd.DataFrame(
        {
            "Category": ["Keywords", "Formatting", "Sections"],
            "Score": [
                ats.keyword_score,
                ats.formatting_score,
                ats.section_completeness_score,
            ],
        }
    ).set_index("Category")
    st.bar_chart(chart_df)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ❌ Issues")
        for item in ats.issues:
            st.markdown(f"- {item}")
    with col2:
        st.markdown("#### 🛠️ Recommendations")
        for item in ats.recommendations:
            st.markdown(f"- {item}")


def tab_job_match() -> None:
    st.subheader("Job Match Score")
    if not require_resume():
        return
    if not st.session_state.jd_text.strip():
        st.info("⬅️ Add a job description in the sidebar to compute a match score.")
        return

    if st.button("Compute Match Score", type="primary"):
        if not require_api_key():
            return
        result = run_safely(
            lambda: match_resume_to_job(
                st.session_state.resume_text, st.session_state.jd_text
            ),
            "Comparing resume to job description...",
        )
        if result is not None:
            st.session_state.match = result

    match: JobMatch | None = st.session_state.match
    if match is None:
        return

    if match.verdict:
        st.info(match.verdict)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        score_card("Overall Match", match.match_score)
    with c2:
        score_card("Skills", match.skills_match_score)
    with c3:
        score_card("Experience", match.experience_match_score)
    with c4:
        score_card("Education", match.education_match_score)

    chart_df = pd.DataFrame(
        {
            "Category": ["Skills", "Experience", "Education"],
            "Score": [
                match.skills_match_score,
                match.experience_match_score,
                match.education_match_score,
            ],
        }
    ).set_index("Category")
    st.bar_chart(chart_df)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ✅ Matched Skills")
        pills(match.matched_skills)
    with col2:
        st.markdown("#### 🧩 Missing Skills")
        pills(match.missing_skills, missing=True)

    st.markdown("#### 🛠️ Recommendations")
    for item in match.recommendations:
        st.markdown(f"- {item}")


def tab_interview() -> None:
    st.subheader("Interview Preparation")
    if not require_resume():
        return

    if st.button("Generate Interview Questions", type="primary"):
        if not require_api_key():
            return
        result = run_safely(
            lambda: generate_interview_questions(
                st.session_state.resume_text, st.session_state.jd_text
            ),
            "Generating tailored interview questions...",
        )
        if result is not None:
            st.session_state.interview = result

    interview: InterviewQuestions | None = st.session_state.interview
    if interview is None:
        return

    st.success(f"Generated {interview.total} questions.")
    t1, t2, t3 = st.tabs(["💻 Technical", "🧱 Project", "👤 HR"])
    with t1:
        for i, q in enumerate(interview.technical_questions, 1):
            st.markdown(f"**{i}.** {q}")
    with t2:
        for i, q in enumerate(interview.project_questions, 1):
            st.markdown(f"**{i}.** {q}")
    with t3:
        for i, q in enumerate(interview.hr_questions, 1):
            st.markdown(f"**{i}.** {q}")


def tab_report() -> None:
    st.subheader("Download Report")
    if not require_resume():
        return

    st.write("The report includes whichever sections you have generated:")
    cols = st.columns(4)
    cols[0].metric("Analysis", "Ready" if st.session_state.analysis else "—")
    cols[1].metric("ATS", "Ready" if st.session_state.ats else "—")
    cols[2].metric("Match", "Ready" if st.session_state.match else "—")
    cols[3].metric("Interview", "Ready" if st.session_state.interview else "—")

    has_any = any(
        st.session_state[k] for k in ["analysis", "ats", "match", "interview"]
    )
    if not has_any:
        st.info("Generate at least one analysis in the other tabs first.")
        return

    candidate = st.text_input("Candidate name (for the report)", value="Candidate")
    if st.button("Build PDF Report", type="primary"):
        pdf_bytes = run_safely(
            lambda: build_pdf_report(
                candidate_name=candidate or "Candidate",
                analysis=st.session_state.analysis,
                ats=st.session_state.ats,
                match=st.session_state.match,
                interview=st.session_state.interview,
            ),
            "Building your PDF report...",
        )
        if pdf_bytes:
            st.download_button(
                "⬇️ Download report.pdf",
                data=pdf_bytes,
                file_name="resume_analysis_report.pdf",
                mime="application/pdf",
                type="primary",
            )
            st.success("Report ready — click the download button above.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    render_sidebar()

    st.title("AI Resume Analyzer & Job Match Scorer")
    st.caption(
        "Upload a resume, optionally add a job description, and get AI-powered "
        "analysis, ATS scoring, match scoring, interview prep, and a PDF report."
    )

    tabs = st.tabs(
        ["Resume Analysis", "ATS Score", "Job Match", "Interview Prep", "Report"]
    )
    with tabs[0]:
        tab_resume_analysis()
    with tabs[1]:
        tab_ats()
    with tabs[2]:
        tab_job_match()
    with tabs[3]:
        tab_interview()
    with tabs[4]:
        tab_report()


if __name__ == "__main__":
    main()
