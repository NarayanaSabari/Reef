import asyncio

from reef.audio.ports import AudioSink, AudioSource
from reef.voice.ports import AudioOut, Interrupted, TurnComplete, VoiceSession


class VoiceLoop:
    """Wires a microphone source to a voice session and plays back its audio.

    On an Interrupted event it flushes the sink immediately (barge-in).
    Pure orchestration — all I/O is behind the injected ports.
    The caller owns the session lifecycle (start/close); VoiceLoop only orchestrates an already-started session.
    """
    def __init__(self, source: AudioSource, sink: AudioSink, session: VoiceSession):
        self._source = source
        self._sink = sink
        self._session = session

    async def run(self) -> None:
        await asyncio.gather(self._pump_mic(), self._pump_events())

    async def _pump_mic(self) -> None:
        async for chunk in self._source.stream():
            await self._session.send_audio(chunk)

    async def _pump_events(self) -> None:
        async for event in self._session.receive():
            if isinstance(event, AudioOut):
                await self._sink.play(event.data)
            elif isinstance(event, Interrupted):
                await self._sink.flush()
            elif isinstance(event, TurnComplete):
                pass  # turn finished; nothing to play
