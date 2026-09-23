from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

PROMPT_VERSION = "v3"
_PROMPTS_DIR = Path(__file__).parent / "prompts"


class OutputType(StrEnum):
    SUMMARY = "summary"
    QUESTIONS = "questions"
    PODCAST = "podcast"
    STUDY_PLAN = "study_plan"


@dataclass(frozen=True)
class GenerationContext:
    course_name: str = ""
    course_code: str = ""
    question_format: str = ""
    corrective_note: str = ""


@dataclass
class GenerationResult:
    outputs: dict = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class DocumentSource:
    """Markdown when extraction worked; raw PDF bytes as the vision fallback."""

    markdown: str = ""
    pdf_bytes: bytes = b""


class LLMClient(Protocol):
    def generate(self, document: DocumentSource, output_types, context) -> GenerationResult: ...


QUESTION_FORMATS = ("flashcard", "mcq", "open_ended")

_QUESTION_SHAPES = {
    "flashcard": '{"front": "prompt side", "back": "answer side"}',
    "mcq": (
        '{"question": "...", "choices": ["four plausible options"],'
        ' "answer_index": 0, "explanation": "why that answer is right"}'
    ),
    "open_ended": '{"question": "...", "model_answer": "a complete answer"}',
}

_QUESTION_FIELDS = {
    "flashcard": ("front", "back"),
    "mcq": ("question", "explanation"),
    "open_ended": ("question", "model_answer"),
}


def _template(name):
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def build_prompt(output_types, context):
    parts = [
        _template("system.txt").format(
            course_name=context.course_name or "unknown",
            course_code=context.course_code or "unknown",
        )
    ]
    if OutputType.SUMMARY in output_types:
        parts.append(_template("summary.txt"))
    if OutputType.QUESTIONS in output_types:
        parts.append(
            _template("questions.txt").format(
                question_format=context.question_format,
                question_shape=_QUESTION_SHAPES[context.question_format],
            )
        )
    if OutputType.PODCAST in output_types:
        parts.append(_template("podcast.txt"))
    if context.corrective_note:
        parts.append(f"IMPORTANT — your previous response was rejected: {context.corrective_note}")
    return "\n\n".join(parts)


def validate_questions(data, question_format):
    if question_format not in QUESTION_FORMATS:
        return [f"unknown question format '{question_format}'"]
    if not isinstance(data, list) or not data:
        return ["questions is not a non-empty list"]
    problems = []
    for i, question in enumerate(data):
        if not isinstance(question, dict):
            problems.append(f"question {i}: not an object")
            continue
        for field_name in _QUESTION_FIELDS[question_format]:
            value = question.get(field_name)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"question {i}: missing/invalid '{field_name}'")
        if question_format == "mcq":
            choices = question.get("choices")
            answer_index = question.get("answer_index")
            if not isinstance(choices, list) or len(choices) < 2 or not all(
                isinstance(c, str) for c in choices
            ):
                problems.append(f"question {i}: missing/invalid 'choices'")
            elif (
                not isinstance(answer_index, int)
                or isinstance(answer_index, bool)
                or not 0 <= answer_index < len(choices)
            ):
                problems.append(f"question {i}: 'answer_index' out of range")
    return problems


PODCAST_HOSTS = ("Alex", "Jordan")


def validate_podcast_script(data):
    if not isinstance(data, dict):
        return ["podcast is not an object"]
    problems = []
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        problems.append("missing/invalid 'title'")
    script = data.get("script")
    if not isinstance(script, str) or not script.strip():
        problems.append("missing/invalid 'script'")
        return problems
    for host in PODCAST_HOSTS:
        if f"{host}:" not in script:
            problems.append(f"script has no lines for host '{host}'")
    return problems


def validate_summary(data):
    problems = []
    if not isinstance(data, dict):
        return ["summary is not an object"]
    if not isinstance(data.get("title"), str):
        problems.append("missing/invalid 'title'")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        problems.append("missing/empty 'sections'")
        return problems
    for i, section in enumerate(sections):
        if not isinstance(section, dict) or not isinstance(section.get("heading"), str):
            problems.append(f"section {i}: missing 'heading'")
        points = section.get("points") if isinstance(section, dict) else None
        if not isinstance(points, list) or not all(isinstance(p, str) for p in points or []):
            problems.append(f"section {i}: missing/invalid 'points'")
    return problems
