from types import SimpleNamespace

from notes.tts.base import TTSResult
from notes.tts.fake import FakeTTSClient

SCRIPT = "Alex: Welcome.\nJordan: Today, Fourier series."


def _is_mp3(data):
    # LAME emits raw MPEG frames: 11-bit sync (0xFF + top 3 bits of next byte)
    return len(data) > 4 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


def test_pcm_to_mp3_produces_valid_smaller_mp3():
    from notes.tts.base import pcm_to_mp3, pcm_to_wav

    pcm = b"\x00\x01" * 24000  # 1.0s of 24kHz 16-bit mono
    mp3 = pcm_to_mp3(pcm)
    assert _is_mp3(mp3)
    assert len(mp3) < len(pcm_to_wav(pcm)) / 4


def test_fake_tts_returns_mp3_with_duration():
    client = FakeTTSClient()
    result = client.synthesize(SCRIPT)
    assert isinstance(result, TTSResult)
    assert _is_mp3(result.audio_mp3)
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
    assert _is_mp3(result.audio_mp3)
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
