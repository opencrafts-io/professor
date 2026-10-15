import io
import wave
from dataclasses import dataclass
from typing import Protocol

import lameenc

SAMPLE_RATE = 24000  # Hz, 16-bit mono PCM — what Gemini TTS emits
MP3_BITRATE_KBPS = 64  # plenty for mono speech; ~0.5MB/min vs 2.9MB/min raw


@dataclass
class TTSResult:
    audio_mp3: bytes
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


def pcm_to_mp3(pcm_bytes, bitrate_kbps=MP3_BITRATE_KBPS):
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate_kbps)
    encoder.set_in_sample_rate(SAMPLE_RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)  # 0 best/slowest .. 9 worst; 2 = high
    return bytes(encoder.encode(pcm_bytes)) + bytes(encoder.flush())


def pcm_duration_seconds(pcm_bytes):
    return len(pcm_bytes) / (SAMPLE_RATE * 2)
