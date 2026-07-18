from __future__ import annotations

import json
import os

import streamlit as st

from exam_app.parser import ParseError, parse_with_ollama
from exam_app.repository import ExamRepository


def repository() -> ExamRepository:
    return ExamRepository(os.getenv("EXAM_DB_PATH", "exams.db"))


def save_ollama_settings(repo: ExamRepository) -> None:
    repo.set_setting("ollama_model", st.session_state.ollama_model)
    repo.set_setting("ollama_url", st.session_state.ollama_url)
    repo.set_setting("ollama_timeout", str(st.session_state.ollama_timeout))


def ingest_page(repo: ExamRepository, model: str, url: str, timeout_seconds: int) -> None:
    st.header("Ingest Exam")
    upload = st.file_uploader("Exam text file", type=["txt"])
    if not upload:
        return
    raw_text = upload.getvalue().decode("utf-8-sig", errors="replace")
    st.caption(upload.name)
    st.text_area("Raw text preview", raw_text, height=220, disabled=True)
    replace = st.checkbox("Replace an existing exam with this filename")
    if st.button("Parse and save with AI", type="primary"):
        with st.spinner("Extracting, validating, and repairing the exam with Ollama…"):
            try:
                parsed = parse_with_ollama(raw_text, upload.name, model, url, timeout_seconds)
                repo.save_exam(parsed, raw_text, replace)
                st.success(f"AI validated and saved {parsed.exam_title}.")
            except (ParseError, ValueError) as exc:
                st.error(str(exc))


def take_exam_page(repo: ExamRepository) -> None:
    st.header("Take Exam")
    exams = repo.list_exams()
    if not exams:
        st.info("Import an exam first.")
        return
    filename = st.selectbox("Exam filename", [row["filename"] for row in exams])
    exam_id, exam = repo.load_exam(filename)
    st.title(exam.exam_title)
    st.caption(exam.source_filename)
    answers: dict[str, int] = {}
    with st.form("exam_form"):
        for section in exam.sections:
            st.subheader(f"Section {section.section_number}: {section.title}")
            if section.instructions:
                st.write(section.instructions)
            for question in section.questions:
                key = f"{section.section_number}:{question.question_number}"
                st.write(f"{question.question_number}. {question.question_text}")
                labels = {f"{o.option_number}. {o.text}": o.option_number for o in question.options}
                selected = st.radio("Answer", list(labels), key=key, index=None, label_visibility="collapsed")
                if selected:
                    answers[key] = labels[selected]
        submitted = st.form_submit_button("Submit exam", type="primary")
    if submitted:
        correct, total, percentage = repo.save_attempt(exam_id, exam, answers)
        st.success(f"Result: {correct}/{total} correct ({percentage}%)")
        with st.expander("Per-question feedback"):
            for section in exam.sections:
                for question in section.questions:
                    key = f"{section.section_number}:{question.question_number}"
                    chosen = answers.get(key, "No answer")
                    icon = "✅" if chosen == question.correct_option_number else "❌"
                    st.write(f"{icon} {section.section_number}.{question.question_number}: selected {chosen}; correct {question.correct_option_number}")


def attempts_page(repo: ExamRepository) -> None:
    st.header("Attempts")
    exams = repo.list_exams()
    filename = st.selectbox("Filter filename", ["All"] + [row["filename"] for row in exams])
    after = st.date_input("Attempts on or after (optional)", value=None)
    rows = repo.list_attempts(None if filename == "All" else filename, after)
    st.dataframe([dict(row) | {"submitted_answers_json": json.dumps(json.loads(row["submitted_answers_json"]), ensure_ascii=False)} for row in rows], use_container_width=True, hide_index=True)


def run() -> None:
    st.set_page_config(page_title="Exam Quiz", page_icon="📝", layout="wide")
    st.markdown("""
        <style>
            div[data-testid="stMarkdownContainer"] p {
                white-space: pre-wrap;
            }
            div[data-testid="stRadio"] label p {
                white-space: pre-wrap;
            }
        </style>
    """, unsafe_allow_html=True)
    repo = repository()
    st.sidebar.header("Ollama settings")
    if "ollama_model" not in st.session_state:
        st.session_state.ollama_model = repo.get_setting("ollama_model", os.getenv("OLLAMA_MODEL", "llama3.2"))
        st.session_state.ollama_url = repo.get_setting("ollama_url", os.getenv("OLLAMA_URL", "http://localhost:11434"))
        st.session_state.ollama_timeout = int(repo.get_setting("ollama_timeout", os.getenv("OLLAMA_TIMEOUT_SECONDS", "12000")))
    model = st.sidebar.text_input("Model", key="ollama_model", on_change=save_ollama_settings, args=(repo,))
    url = st.sidebar.text_input("URL", key="ollama_url", on_change=save_ollama_settings, args=(repo,))
    timeout_seconds = st.sidebar.number_input(
        "Request timeout (seconds)", min_value=30, max_value=12000, step=60,
        key="ollama_timeout", on_change=save_ollama_settings, args=(repo,),
    )
    page = st.sidebar.radio("Page", ["Ingest Exam", "Take Exam", "Attempts"])
    if page == "Ingest Exam":
        ingest_page(repo, model, url, int(timeout_seconds))
    elif page == "Take Exam":
        take_exam_page(repo)
    else:
        attempts_page(repo)
