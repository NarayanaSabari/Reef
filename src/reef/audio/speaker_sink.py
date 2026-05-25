import asyncio
import sounddevice as sd
from reef.config import Settings

class SpeakerAudioSink:
    """Plays 24 kHz mono int16 PCM; flush() discards queued audio (barge-in)."""
    def __init__(self, settings: Settings):
        self._settings = settings
        self._stream = sd.RawOutputStream(
            samplerate=settings.output_sample_rate,
            channels=settings.channels, dtype="int16",
        )
        self._stream.start()

    async def play(self, pcm: bytes) -> None:
        await asyncio.get_running_loop().run_in_executor(None, self._stream.write, pcm)

    async def flush(self) -> None:
        self._stream.stop(); self._stream.start()

    async def close(self) -> None:
        self._stream.stop()
        self._stream.close()
