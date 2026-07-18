from __future__ import annotations

import json

from pydantic import ValidationError
from langchain_ollama import ChatOllama

from .models import ParsedExam


class ParseError(Exception):
    pass


def ollama_generate_url(base_url: str) -> str:
    """Accept either Ollama's server URL or its /api URL."""
    url = base_url.rstrip("/")
    return url if url.endswith("/api/generate") else url.removesuffix("/api") + "/api/generate"


def ollama_base_url(base_url: str) -> str:
    return ollama_generate_url(base_url).removesuffix("/api/generate")


def parsing_prompt(filename: str, raw_text: str) -> str:
    return f"""You extract an exam from plain text. Return ONLY one JSON object: no markdown, prose, or code fence.
The object MUST have this exact shape:
{{"exam_title":"string","source_filename":"{filename}","sections":[{{"section_number":1,"title":"string","instructions":"string","questions":[{{"question_number":1,"question_text":"string","options":[{{"option_number":1,"text":"string"}}],"correct_option_number":1}}]}}],"parsing_issues":["string"]}}
Preserve source question numbers, Japanese/Unicode, quoted passages, and headings. Parse answer-key entries and attach each answer to its matching section and question. Options may have any count but every question needs at least two. Never invent data. If any question, options, or answer is uncertain or malformed, omit nothing silently: put a concise explanation in parsing_issues. A correct_option_number must be one of the option_number values.
Do not report an issue merely because the answer key is not a separate output field: when its answer is assigned to correct_option_number, it has been handled successfully.
Filename: {filename}
Raw exam text follows exactly:
---
{raw_text}
---"""


def repair_prompt(filename: str, raw_text: str, draft: ParsedExam) -> str:
    return f"""Repair this AI-extracted exam using only the original text below. Return the complete replacement exam through the supplied schema.
Every question must have a correct_option_number that matches one of its options. Match answer-key question numbers exactly; never guess. Resolve all parsing_issues before returning. Preserve Japanese text and question numbering.
Filename: {filename}
Original text:
---
{raw_text}
---
Draft to repair:
---
{draft.model_dump_json()}
---"""


def _structured_exam(prompt: str, model: str, base_url: str, timeout_seconds: int) -> ParsedExam:
    llm = ChatOllama(
        model=model, base_url=ollama_base_url(base_url), temperature=0,
        client_kwargs={"timeout": timeout_seconds},
    )
    result = llm.with_structured_output(ParsedExam, method="json_schema", include_raw=True).invoke(prompt)
    if result["parsed"] is None:
        raise ParseError(f"Ollama did not produce a schema-valid draft: {result['parsing_error']}")
    return result["parsed"]


def parse_with_ollama(
    raw_text: str, filename: str, model: str, base_url: str, timeout_seconds: int = 12000
) -> ParsedExam:
    try:
        exam = _structured_exam(parsing_prompt(filename, raw_text), model, base_url, timeout_seconds)
        if exam.completeness_issues():
            exam = _structured_exam(repair_prompt(filename, raw_text, exam), model, base_url, timeout_seconds)
    except Exception as exc:
        raise ParseError(f"Could not reach Ollama or request structured output: {exc}") from exc
    exam = exam.model_copy(update={"source_filename": filename})
    if issues := exam.completeness_issues():
        raise ParseError("AI could not create a complete exam after an automatic repair pass: " + "; ".join(issues))
    return exam


def validate_exam_json(text: str, filename: str, require_complete: bool = True) -> ParsedExam:
    try:
        data = json.loads(text)
        data["source_filename"] = filename
        exam = ParsedExam.model_validate(data)
        if require_complete and (issues := exam.completeness_issues()):
            raise ParseError("Resolve parser issues before saving: " + "; ".join(issues))
        return exam
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ParseError(f"Invalid exam JSON: {exc}") from exc
