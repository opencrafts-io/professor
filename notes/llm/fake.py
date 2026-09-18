from .base import GenerationResult, OutputType

_DEFAULT_SUMMARY = {
    "title": "Sample summary",
    "sections": [{"heading": "Key ideas", "points": ["point one", "point two"]}],
}


class FakeClient:
    def __init__(self, responses=None, script=None, input_tokens=10, output_tokens=5):
        self._responses = responses or {OutputType.SUMMARY: _DEFAULT_SUMMARY}
        self._script = list(script) if script else None
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self.calls = []
        self.document_text_seen = []

    def generate(self, document_markdown, output_types, context):
        self.calls.append((list(output_types), context))
        self.document_text_seen.append(document_markdown)
        responses = self._script.pop(0) if self._script else self._responses
        outputs = {t: responses[t] for t in output_types if t in responses}
        return GenerationResult(
            outputs=outputs, input_tokens=self._input_tokens, output_tokens=self._output_tokens
        )
