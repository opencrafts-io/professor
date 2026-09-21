import io
import wave
from dataclasses import dataclass
from typing import Protocol

SAMPLE_RATE = 24000  # Hz, 16-bit mono PCM — what Gemini TTS emits


@dataclass
class TTSResult:
    audio_wav: bytes
    duration_seconds: float
    audio_tokens: int = 0


class TTSClient(Protocol):
    provider: str

    def synthesize(self, script: str) -> TTSResult: ...


def pcm_to_wav(pcm_bytes):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(pcm_bytes)
    return buffer.getvalue()


def pcm_duration_seconds(pcm_bytes):
    return len(pcm_bytes) / (SAMPLE_RATE * 2)
