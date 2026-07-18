import pytest

from exam_app.parser import ParseError, ollama_base_url, ollama_generate_url, validate_exam_json
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


def test_ollama_url_accepts_server_or_api_path():
    assert ollama_generate_url("http://localhost:11434") == "http://localhost:11434/api/generate"
    assert ollama_generate_url("http://localhost:11434/api") == "http://localhost:11434/api/generate"
    assert ollama_base_url("http://localhost:11434/api/generate") == "http://localhost:11434"


def test_settings_are_persisted(tmp_path):
    repo = ExamRepository(str(tmp_path / "test.db"))
    repo.set_setting("ollama_model", "qwen2.5:7b")
    assert repo.get_setting("ollama_model", "llama3.2") == "qwen2.5:7b"
    assert repo.get_setting("missing", "default") == "default"
