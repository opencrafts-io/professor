from google import genai
from google.genai import types

from ..llm.base import PODCAST_HOSTS
from .base import TTSResult, pcm_duration_seconds, pcm_to_mp3

_VOICES = dict(zip(PODCAST_HOSTS, ("Kore", "Puck")))


class GeminiTTSClient:
    def __init__(self, api_key, model="gemini-3.1-flash-tts-preview"):
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self.provider = model

    def synthesize(self, script):
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker=host,
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                            ),
                        )
                        for host, voice in _VOICES.items()
                    ]
                )
            ),
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=f"Read this conversation aloud naturally:\n{script}",
            config=config,
        )
        pcm = response.candidates[0].content.parts[0].inline_data.data
        usage = response.usage_metadata
        return TTSResult(
            audio_mp3=pcm_to_mp3(pcm),
            duration_seconds=pcm_duration_seconds(pcm),
            audio_tokens=usage.candidates_token_count or 0,
        )
