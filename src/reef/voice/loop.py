import asyncio

from reef.audio.ports import AudioSink, AudioSource
from reef.voice.ports import AudioOut, Interrupted, TurnComplete, VoiceSession


class VoiceLoop:
    """Wires a microphone source to a voice session and plays back its audio.

    On an Interrupted event it flushes the sink immediately (barge-in).
    Pure orchestration — all I/O is behind the injected ports.
    The caller owns the session lifecycle (start/close); VoiceLoop only orchestrates
    an already-started session.

    Lifetime: the session event stream is authoritative. When it ends (server timeout,
    model finished, etc.), the mic pump exits on its next iteration by checking a shared
    stop flag, so run() returns cleanly instead of hanging on an infinite mic.

    Half-duplex mic gating: while Reef is producing audio, mic chunks are DROPPED to
    prevent the speaker output from feeding back into the mic (acoustic echo). The mic
    re-opens MUTE_GRACE_SECONDS after the last AudioOut event. Trade-off: no barge-in
    (the model can't be interrupted mid-utterance because its own audio isn't being
    streamed to the server during playback). Use headphones or push-to-talk if you
    need true barge-in.
    """

    MUTE_GRACE_SECONDS = 0.5  # how long after the last AudioOut to keep the mic muted

    def __init__(self, source: AudioSource, sink: AudioSink, session: VoiceSession):
        self._source = source
        self._sink = sink
        self._session = session

    async def run(self) -> None:
        # Created in the running loop, not in __init__.
        self._stop = asyncio.Event()
        self._last_audio_out = 0.0   # asyncio loop time; 0 == "Reef hasn't spoken yet"
        await asyncio.gather(self._pump_mic(), self._pump_events())

    async def _pump_mic(self) -> None:
        loop = asyncio.get_running_loop()
        async for chunk in self._source.stream():
            if self._stop.is_set():
                return
            # Drop chunks while Reef is speaking or within the grace window after.
            if loop.time() - self._last_audio_out < self.MUTE_GRACE_SECONDS:
                continue
            await self._session.send_audio(chunk)

    async def _pump_events(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            async for event in self._session.receive():
                if isinstance(event, AudioOut):
                    # Mark the mic as muted from now (+grace window).
                    self._last_audio_out = loop.time()
                    await self._sink.play(event.data)
                elif isinstance(event, Interrupted):
                    # Barge-in path: open the mic again immediately.
                    self._last_audio_out = 0.0
                    await self._sink.flush()
                elif isinstance(event, TurnComplete):
                    pass  # turn finished; mic stays muted for the grace window then re-opens
        finally:
            # Signal the mic pump to exit on its next iteration.
            self._stop.set()
