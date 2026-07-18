from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from .models import ParsedExam


class ParseError(Exception):
    pass


def ollama_generate_url(base_url: str) -> str:
    """Accept either Ollama's server URL or its /api URL."""
    url = base_url.rstrip("/")
    return url if url.endswith("/api/generate") else url.removesuffix("/api") + "/api/generate"


def parsing_prompt(filename: str, raw_text: str) -> str:
    return f"""You extract an exam from plain text. Return ONLY one JSON object: no markdown, prose, or code fence.
The object MUST have this exact shape:
{{"exam_title":"string","source_filename":"{filename}","sections":[{{"section_number":1,"title":"string","instructions":"string","questions":[{{"question_number":1,"question_text":"string","options":[{{"option_number":1,"text":"string"}}],"correct_option_number":1}}]}}],"parsing_issues":["string"]}}
Preserve source question numbers, Japanese/Unicode, quoted passages, and headings. Parse answer-key entries and attach each answer to its matching section and question. Options may have any count but every question needs at least two. Never invent data. If any question, options, or answer is uncertain or malformed, omit nothing silently: put a concise explanation in parsing_issues. A correct_option_number must be one of the option_number values.
Filename: {filename}
Raw exam text follows exactly:
---
{raw_text}
---"""


def parse_with_ollama(
    raw_text: str, filename: str, model: str, base_url: str, timeout_seconds: int = 12000
) -> ParsedExam:
    payload = json.dumps({"model": model, "prompt": parsing_prompt(filename, raw_text), "stream": False, "format": "json"}).encode()
    endpoint = ollama_generate_url(base_url)
    request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ParseError(
            f"Ollama returned HTTP {exc.code} at {endpoint}. "
            "Use http://localhost:11434 as the URL."
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ParseError(f"Could not reach Ollama or read its response: {exc}") from exc
    try:
        return validate_exam_json(body["response"], filename)
    except KeyError as exc:
        raise ParseError("Ollama response did not include generated text.") from exc


def validate_exam_json(text: str, filename: str) -> ParsedExam:
    try:
        data = json.loads(text)
        data["source_filename"] = filename
        return ParsedExam.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ParseError(f"Invalid exam JSON: {exc}") from exc
