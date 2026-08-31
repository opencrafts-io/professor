from notes.llm.base import (
    GenerationContext,
    OutputType,
    build_prompt,
    validate_summary,
)
from notes.llm.fake import FakeClient


def test_fake_client_returns_valid_summary():
    client = FakeClient()
    result = client.generate(b"%PDF-", [OutputType.SUMMARY], GenerationContext(course_name="Math"))
    summary = result.outputs[OutputType.SUMMARY]
    assert validate_summary(summary) == []
    assert result.input_tokens > 0
    assert client.calls == [([OutputType.SUMMARY], GenerationContext(course_name="Math"))]


def test_validate_summary_flags_problems():
    problems = validate_summary({"title": 3, "sections": [{"heading": "h"}]})
    assert any("title" in p for p in problems)
    assert any("points" in p for p in problems)


def test_build_prompt_includes_course_and_output_block():
    prompt = build_prompt(
        [OutputType.SUMMARY], GenerationContext(course_name="Math", course_code="MAT 2201")
    )
    assert "MAT 2201" in prompt
    assert "summary" in prompt.lower()
