from typing import AsyncIterator, List
from reef.voice.ports import VoiceEvent

class FakeVoiceSession:
    def __init__(self, events: List[VoiceEvent]):
        self._events = events
        self.sent: List[bytes] = []
        self.closed = False

    async def send_audio(self, pcm: bytes) -> None:
        self.sent.append(pcm)

    async def receive(self) -> AsyncIterator[VoiceEvent]:
        for event in self._events:
            yield event

    async def close(self) -> None:
        self.closed = True
