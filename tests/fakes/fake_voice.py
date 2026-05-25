from collections.abc import AsyncIterator

from reef.voice.ports import VoiceEvent


class FakeVoiceSession:
    def __init__(self, events: list[VoiceEvent]):
        self._events = events
        self.sent: list[bytes] = []
        self.closed = False

    async def send_audio(self, pcm: bytes) -> None:
        self.sent.append(pcm)

    async def receive(self) -> AsyncIterator[VoiceEvent]:
        for event in self._events:
            yield event

    async def close(self) -> None:
        self.closed = True
