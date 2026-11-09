import io
import wave

from google import genai
from google.genai import types

from ..llm.base import PODCAST_HOSTS
from .base import SAMPLE_RATE, TTSResult, pcm_duration_seconds, pcm_to_mp3

_VOICES = dict(zip(PODCAST_HOSTS, ("Kore", "Puck")))


def _script_parts(script):
    """One Part per speaker turn. The 3.8 TTS models require
    speech_metadata.speaker on every text part instead of parsing
    'Name:' labels out of a transcript string."""
    turns = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for host in PODCAST_HOSTS:
            label = f"{host}:"
            if stripped.startswith(label):
                turns.append((host, [stripped[len(label):].strip()]))
                break
        else:
            if turns:
                turns[-1][1].append(stripped)
            else:
                turns.append((PODCAST_HOSTS[0], [stripped]))
    return [
        types.Part(
            text=" ".join(lines),
            speech_metadata=types.SpeechMetadata(speaker=host),
        )
        for host, lines in turns
    ]


def _audio_to_pcm(data):
    """Gemini 3.8 TTS returns WAV (RIFF header); the retired previews returned
    raw 24kHz PCM. Accept both and report the true sample rate."""
    if data[:4] != b"RIFF":
        return data, SAMPLE_RATE
    with wave.open(io.BytesIO(data)) as f:
        if f.getnchannels() != 1 or f.getsampwidth() != 2:
            raise ValueError("unexpected WAV shape from TTS provider")
        return f.readframes(f.getnframes()), f.getframerate()


class GeminiTTSClient:
    def __init__(self, api_key, model="gemini-3.8-flash-tts"):
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
            contents=_script_parts(script),
            config=config,
        )
        pcm, sample_rate = _audio_to_pcm(
            response.candidates[0].content.parts[0].inline_data.data
        )
        usage = response.usage_metadata
        return TTSResult(
            audio_mp3=pcm_to_mp3(pcm, sample_rate=sample_rate),
            duration_seconds=pcm_duration_seconds(pcm, sample_rate=sample_rate),
            audio_tokens=usage.candidates_token_count or 0,
        )
