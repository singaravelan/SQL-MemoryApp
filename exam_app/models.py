from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Option(BaseModel):
    option_number: int = Field(ge=1)
    text: str = Field(min_length=1)


class Question(BaseModel):
    question_number: int = Field(ge=1)
    question_text: str = Field(min_length=1)
    options: list[Option] = Field(min_length=2)
    correct_option_number: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def correct_option_exists(self) -> "Question":
        numbers = [option.option_number for option in self.options]
        if len(numbers) != len(set(numbers)):
            raise ValueError("option numbers must be unique")
        return self

    def answer_issue(self) -> str | None:
        if self.correct_option_number is None:
            return "correct option number is missing"
        if self.correct_option_number not in [option.option_number for option in self.options]:
            return "correct option number does not match an option"
        return None


class Section(BaseModel):
    section_number: int = Field(ge=1)
    title: str = ""
    instructions: str = ""
    questions: list[Question] = Field(min_length=1)


class ParsedExam(BaseModel):
    exam_title: str = Field(min_length=1)
    source_filename: str = Field(min_length=1)
    sections: list[Section] = Field(min_length=1)
    parsing_issues: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def has_unique_questions_and_no_issues(self) -> "ParsedExam":
        seen = set()
        for section in self.sections:
            for question in section.questions:
                key = (section.section_number, question.question_number)
                if key in seen:
                    raise ValueError("question numbers must be unique within a section")
                seen.add(key)
        return self

    def completeness_issues(self) -> list[str]:
        issues = list(self.parsing_issues)
        for section in self.sections:
            for question in section.questions:
                if issue := question.answer_issue():
                    issues.append(f"Section {section.section_number}, question {question.question_number}: {issue}")
        return issues
