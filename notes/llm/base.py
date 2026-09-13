from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

PROMPT_VERSION = "v2"
_PROMPTS_DIR = Path(__file__).parent / "prompts"


class OutputType(StrEnum):
    SUMMARY = "summary"
    QUESTIONS = "questions"
    PODCAST_SCRIPT = "podcast_script"
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


class LLMClient(Protocol):
    def generate(self, pdf_bytes, output_types, context) -> GenerationResult: ...


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
    if context.corrective_note:
        parts.append(f"IMPORTANT — your previous response was rejected: {context.corrective_note}")
    return "\n\n".join(parts)


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
