import asyncio
from collections.abc import AsyncIterator

import sounddevice as sd

from reef.config import Settings


class MicAudioSource:
    """Streams 20 ms 16 kHz mono int16 PCM chunks from the default microphone.

    Optional `gate`: when provided, mic chunks are only forwarded while the event is set.
    Used by main.py to implement push-to-talk via a global hotkey (the hotkey toggles
    the event). If `gate` is None, the mic streams unconditionally (default).
    """
    def __init__(
        self,
        settings: Settings,
        blocksize_ms: int = 20,
        gate: asyncio.Event | None = None,
    ):
        self._settings = settings
        self._blocksize = settings.input_sample_rate * blocksize_ms // 1000
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._gate = gate

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
                chunk = await self._queue.get()
                # Push-to-talk: drop chunks unless the gate is open.
                if self._gate is not None and not self._gate.is_set():
                    continue
                yield chunk
        finally:
            stream.stop()
            stream.close()
