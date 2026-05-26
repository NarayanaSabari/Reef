import asyncio

from reef.audio.ports import AudioSink, AudioSource
from reef.voice.ports import AudioOut, Interrupted, TurnComplete, VoiceSession


class VoiceLoop:
    """Wires a microphone source to a voice session and plays back its audio.

    On an Interrupted event it flushes the sink immediately (barge-in).
    Pure orchestration — all I/O is behind the injected ports.
    The caller owns the session lifecycle (start/close); VoiceLoop only orchestrates an already-started session.

    Lifetime: the session event stream is authoritative. When it ends (server timeout, model
    finished, etc.), the mic pump exits on its next iteration by checking a shared stop flag.
    Without this, an infinite real mic would keep `asyncio.gather` waiting and freeze the app
    after the session ends. Finite-stream tests stay green because the mic also returns
    naturally on its own when its source exhausts.
    """
    def __init__(self, source: AudioSource, sink: AudioSink, session: VoiceSession):
        self._source = source
        self._sink = sink
        self._session = session

    async def run(self) -> None:
        # Event must be created inside the running loop, not in __init__.
        self._stop = asyncio.Event()
        await asyncio.gather(self._pump_mic(), self._pump_events())

    async def _pump_mic(self) -> None:
        async for chunk in self._source.stream():
            if self._stop.is_set():
                return
            await self._session.send_audio(chunk)

    async def _pump_events(self) -> None:
        try:
            async for event in self._session.receive():
                if isinstance(event, AudioOut):
                    await self._sink.play(event.data)
                elif isinstance(event, Interrupted):
                    await self._sink.flush()
                elif isinstance(event, TurnComplete):
                    pass  # turn finished; nothing to play
        finally:
            # Signal the mic pump to exit on its next iteration.
            self._stop.set()
