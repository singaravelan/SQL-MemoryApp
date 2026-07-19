import pytest

from exam_app.parser import (
    ParseError,
    apply_answer_key_mapping,
    clean_exam_text,
    ollama_base_url,
    ollama_generate_url,
    validate_exam_json,
)
from exam_app.models import ParsedExam, Section, Question, Option
from exam_app.repository import ExamRepository


def exam_json():
    return '''{"exam_title":"日本語","source_filename":"sample.txt","sections":[{"section_number":1,"title":"語彙","instructions":"","questions":[{"question_number":1,"question_text":"あの（ ）","options":[{"option_number":1,"text":"ひと"},{"option_number":2,"text":"かた"}],"correct_option_number":2}]}],"parsing_issues":[]}'''


def test_valid_exam_can_be_saved_and_scored(tmp_path):
    exam = validate_exam_json(exam_json(), "sample.txt")
    repo = ExamRepository(str(tmp_path / "test.db"))
    repo.save_exam(exam, "raw")
    exam_id, saved = repo.load_exam("sample.txt")
    assert repo.save_attempt(exam_id, saved, {"1:1": 2}) == (1, 1, 100.0)


def test_incomplete_answer_is_rejected():
    bad = exam_json().replace('"correct_option_number":2', '"correct_option_number":null')
    with pytest.raises(ParseError):
        validate_exam_json(bad, "sample.txt")


def test_parser_issues_are_rejected_before_save():
    draft = exam_json().replace('"parsing_issues":[]', '"parsing_issues":["Answer key is missing"]')
    assert validate_exam_json(draft, "sample.txt", require_complete=False).parsing_issues
    with pytest.raises(ParseError, match="Resolve parser issues"):
        validate_exam_json(draft, "sample.txt")


def test_clean_exam_text_extracts_the_real_exam_from_streamlit_noise():
    raw_text = """### Section 1:[](http://localhost:8501/#section-1)

1. あの（ ）は どなたですか。

Result: 4/10 correct (40.0%)

Per-question feedback

❌ 1.1: selected 1; correct 3

actual file Section 1: Vocabulary
かっこに なにを いれますか。 1・2・3・4から いちばん いい ものを ひとつ えらんで ください。
これは （　　） です。
ほん　2. めいし　3. ざっし　4. じしょ

Correct Options (Answer Key)
Section 1, Question 1: (2)"""

    cleaned = clean_exam_text(raw_text)

    assert "Result:" not in cleaned
    assert "Per-question feedback" not in cleaned
    assert "Correct Options" not in cleaned
    assert "actual file" not in cleaned.lower()
    assert "かっこに なにを いれますか。" in cleaned
    assert "これは （　　） です。" in cleaned


def test_answer_key_entries_are_applied_and_renumbered():
    exam = ParsedExam(
        exam_title="日本語",
        source_filename="sample.txt",
        sections=[
            Section(
                section_number=1,
                title="Section 1",
                questions=[
                    Question(question_number=1, question_text="Q1", options=[Option(option_number=1, text="A"), Option(option_number=2, text="B")]),
                    Question(question_number=2, question_text="Q2", options=[Option(option_number=1, text="A"), Option(option_number=2, text="B")]),
                ],
            ),
            Section(
                section_number=2,
                title="Section 2",
                questions=[
                    Question(question_number=1, question_text="Q3", options=[Option(option_number=1, text="A"), Option(option_number=2, text="B")]),
                    Question(question_number=2, question_text="Q4", options=[Option(option_number=1, text="A"), Option(option_number=2, text="B")]),
                ],
            ),
        ],
        parsing_issues=[],
    )
    raw_text = """Correct Options (Answer Key)
Section 1, Question 1: (2)
Section 1, Question 2: (1)
Section 2, Question 6: (2)
Section 2, Question 7: (1)
"""

    apply_answer_key_mapping(exam, raw_text)

    assert exam.sections[0].questions[0].question_number == 1
    assert exam.sections[0].questions[0].correct_option_number == 2
    assert exam.sections[0].questions[1].correct_option_number == 1
    assert exam.sections[1].questions[0].question_number == 6
    assert exam.sections[1].questions[0].correct_option_number == 2
    assert exam.sections[1].questions[1].question_number == 7
    assert exam.sections[1].questions[1].correct_option_number == 1


def test_ollama_url_accepts_server_or_api_path():
    assert ollama_generate_url("http://localhost:11434") == "http://localhost:11434/api/generate"
    assert ollama_generate_url("http://localhost:11434/api") == "http://localhost:11434/api/generate"
    assert ollama_base_url("http://localhost:11434/api/generate") == "http://localhost:11434"


def test_settings_are_persisted(tmp_path):
    repo = ExamRepository(str(tmp_path / "test.db"))
    repo.set_setting("ollama_model", "qwen2.5:7b")
    assert repo.get_setting("ollama_model", "llama3.2") == "qwen2.5:7b"
    assert repo.get_setting("missing", "default") == "default"
