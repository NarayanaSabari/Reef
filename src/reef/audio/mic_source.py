import asyncio
from typing import AsyncIterator, Optional
import sounddevice as sd
from reef.config import Settings

class MicAudioSource:
    """Streams 20 ms 16 kHz mono int16 PCM chunks from the default microphone."""
    def __init__(self, settings: Settings, blocksize_ms: int = 20):
        self._settings = settings
        self._blocksize = settings.input_sample_rate * blocksize_ms // 1000
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _callback(self, indata, frames, time_info, status) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, bytes(indata))

    async def stream(self) -> AsyncIterator[bytes]:
        self._loop = asyncio.get_running_loop()
        stream = sd.RawInputStream(
            samplerate=self._settings.input_sample_rate,
            channels=self._settings.channels, dtype="int16",
            blocksize=self._blocksize, callback=self._callback,
        )
        stream.start()
        try:
            while True:
                yield await self._queue.get()
        finally:
            stream.stop(); stream.close()
