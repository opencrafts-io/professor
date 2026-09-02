import json

from google import genai
from google.genai import types

from .base import GenerationResult, build_prompt


class GeminiClient:
    def __init__(self, api_key, model="gemini-3.5-flash-lite"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, pdf_bytes, output_types, context):
        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                build_prompt(output_types, context),
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        payload = json.loads(response.text or "{}")
        usage = response.usage_metadata
        return GenerationResult(
            outputs={t: payload.get(t, {}) for t in output_types},
            input_tokens=usage.prompt_token_count or 0,
            output_tokens=usage.candidates_token_count or 0,
        )
