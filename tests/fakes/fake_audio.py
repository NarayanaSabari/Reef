from collections.abc import AsyncIterator


class FakeAudioSource:
    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    async def stream(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

class FakeAudioSink:
    def __init__(self) -> None:
        self.played: list[bytes] = []
        self.flush_count = 0

    async def play(self, pcm: bytes) -> None:
        self.played.append(pcm)

    async def flush(self) -> None:
        self.flush_count += 1
