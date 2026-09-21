from .base import TTSResult, pcm_duration_seconds, pcm_to_wav

_SILENCE_PCM = b"\x00\x00" * 2400  # 0.1s


class FakeTTSClient:
    provider = "fake"

    def __init__(self, error=None):
        self._error = error
        self.scripts = []

    def synthesize(self, script):
        self.scripts.append(script)
        if self._error is not None:
            raise self._error
        return TTSResult(
            audio_wav=pcm_to_wav(_SILENCE_PCM),
            duration_seconds=pcm_duration_seconds(_SILENCE_PCM),
            audio_tokens=10,
        )
