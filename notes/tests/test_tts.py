from types import SimpleNamespace

from notes.tts.base import TTSResult
from notes.tts.fake import FakeTTSClient

SCRIPT = "Alex: Welcome.\nJordan: Today, Fourier series."


def test_fake_tts_returns_wav_with_duration():
    client = FakeTTSClient()
    result = client.synthesize(SCRIPT)
    assert isinstance(result, TTSResult)
    assert result.audio_wav.startswith(b"RIFF")
    assert result.duration_seconds > 0
    assert client.scripts == [SCRIPT]
    assert client.provider == "fake"


def test_gemini_tts_builds_multispeaker_request_and_wraps_wav(monkeypatch):
    from notes.tts import gemini as tts_gemini

    calls = {}
    pcm = b"\x00\x01" * 24000  # exactly 1.0s of 24kHz 16-bit mono

    class StubModels:
        def generate_content(self, **kwargs):
            calls.update(kwargs)
            part = SimpleNamespace(inline_data=SimpleNamespace(data=pcm))
            return SimpleNamespace(
                candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))],
                usage_metadata=SimpleNamespace(prompt_token_count=50, candidates_token_count=800),
            )

    monkeypatch.setattr(
        tts_gemini.genai, "Client", lambda api_key: SimpleNamespace(models=StubModels())
    )

    client = tts_gemini.GeminiTTSClient(api_key="key")
    result = client.synthesize(SCRIPT)

    assert SCRIPT in calls["contents"]
    speech_config = calls["config"].speech_config
    speakers = {
        c.speaker for c in speech_config.multi_speaker_voice_config.speaker_voice_configs
    }
    assert speakers == {"Alex", "Jordan"}
    assert result.audio_wav.startswith(b"RIFF")
    assert result.duration_seconds == 1.0
    assert result.audio_tokens == 800
    assert "tts" in client.provider


def test_get_tts_client_honours_settings_backend(settings):
    from notes.services.generation import get_tts_client
    from notes.tts.gemini import GeminiTTSClient

    assert isinstance(get_tts_client(), FakeTTSClient)  # conftest forces "fake"
    settings.AI_TTS_BACKEND = "gemini"
    settings.GEMINI_API_KEY = "key"
    assert isinstance(get_tts_client(), GeminiTTSClient)
