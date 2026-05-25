from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class AudioSource(Protocol):
    def stream(self) -> AsyncIterator[bytes]:
        """Yield raw 16 kHz mono int16 PCM chunks until exhausted."""
        ...

@runtime_checkable
class AudioSink(Protocol):
    async def play(self, pcm: bytes) -> None:
        """Enqueue a 24 kHz mono int16 PCM chunk for playback."""
        ...
    async def flush(self) -> None:
        """Discard any queued/playing audio immediately (barge-in)."""
        ...
