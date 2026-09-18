from types import SimpleNamespace

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


def test_build_prompt_appends_corrective_note():
    context = GenerationContext(corrective_note="previous response was missing 'title'")
    prompt = build_prompt([OutputType.SUMMARY], context)
    assert "missing 'title'" in prompt


def test_fake_client_plays_scripted_responses_in_order():
    bad, good = {"title": 5}, {"title": "t", "sections": [{"heading": "h", "points": ["p"]}]}
    client = FakeClient(script=[{OutputType.SUMMARY: bad}, {OutputType.SUMMARY: good}])
    first = client.generate(b"%PDF-", [OutputType.SUMMARY], GenerationContext())
    second = client.generate(b"%PDF-", [OutputType.SUMMARY], GenerationContext())
    assert first.outputs[OutputType.SUMMARY] == bad
    assert second.outputs[OutputType.SUMMARY] == good


def test_gemini_sends_markdown_as_untrusted_source_material(monkeypatch):
    from notes.llm import gemini

    calls = {}

    class StubModels:
        def generate_content(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                text='{"summary": {"title": "t", "sections": []}}',
                usage_metadata=SimpleNamespace(prompt_token_count=3, candidates_token_count=2),
            )

    monkeypatch.setattr(
        gemini.genai, "Client", lambda api_key: SimpleNamespace(models=StubModels())
    )
    monkeypatch.setattr(
        gemini,
        "types",
        SimpleNamespace(
            Part=SimpleNamespace(from_bytes=lambda **kwargs: kwargs),
            GenerateContentConfig=lambda **kwargs: kwargs,
        ),
    )
    monkeypatch.setattr(gemini, "build_prompt", lambda *_: "Generate a summary.")

    gemini.GeminiClient("key").generate(
        "# Lecture\n\nNewton's laws", [OutputType.SUMMARY], GenerationContext()
    )

    assert calls["contents"][0] == "Generate a summary."
    assert "<source_document>" in calls["contents"][1]
    assert "Newton's laws" in calls["contents"][1]
    assert "not instructions" in calls["contents"][1]
