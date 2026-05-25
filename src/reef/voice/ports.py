from dataclasses import dataclass
from typing import Protocol, AsyncIterator, Union, runtime_checkable

@dataclass(frozen=True)
class AudioOut:
    """A chunk of model audio (24 kHz mono int16 PCM)."""
    data: bytes

@dataclass(frozen=True)
class Interrupted:
    """The user spoke over the model; discard queued playback."""

@dataclass(frozen=True)
class TurnComplete:
    """The model finished its turn."""

VoiceEvent = Union[AudioOut, Interrupted, TurnComplete]

@runtime_checkable
class VoiceSession(Protocol):
    async def send_audio(self, pcm: bytes) -> None: ...
    def receive(self) -> AsyncIterator[VoiceEvent]: ...
    async def close(self) -> None: ...
