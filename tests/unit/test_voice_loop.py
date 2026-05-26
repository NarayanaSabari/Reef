import asyncio

from reef.voice.loop import VoiceLoop
from reef.voice.ports import AudioOut, Interrupted, TurnComplete
from tests.fakes.fake_audio import FakeAudioSink, FakeAudioSource
from tests.fakes.fake_voice import FakeVoiceSession


async def test_forwards_mic_chunks_to_session():
    src = FakeAudioSource([b"a", b"b"])
    sink = FakeAudioSink()
    sess = FakeVoiceSession(events=[])
    await VoiceLoop(src, sink, sess).run()
    assert sess.sent == [b"a", b"b"]

async def test_plays_audio_out_events_to_sink():
    src = FakeAudioSource([])
    sink = FakeAudioSink()
    sess = FakeVoiceSession(events=[AudioOut(b"x"), AudioOut(b"y")])
    await VoiceLoop(src, sink, sess).run()
    assert sink.played == [b"x", b"y"]

async def test_flushes_sink_on_interruption():
    src = FakeAudioSource([])
    sink = FakeAudioSink()
    sess = FakeVoiceSession(events=[AudioOut(b"x"), Interrupted(), AudioOut(b"y")])
    await VoiceLoop(src, sink, sess).run()
    assert sink.flush_count == 1
    assert sink.played == [b"x", b"y"]

async def test_run_completes_when_streams_exhausted():
    src = FakeAudioSource([b"a"])
    sink = FakeAudioSink()
    sess = FakeVoiceSession(events=[TurnComplete()])
    await asyncio.wait_for(VoiceLoop(src, sink, sess).run(), timeout=1.0)
    assert sess.sent == [b"a"]


async def test_run_returns_when_events_end_even_with_infinite_source():
    """Production case: a real mic never exhausts. When the Gemini session ends,
    run() must return cleanly instead of hanging on the mic pump."""
    class _InfiniteSource:
        def __init__(self) -> None:
            self.sent = 0
        async def stream(self):
            while True:
                self.sent += 1
                yield b"x"
                await asyncio.sleep(0)  # yield to other tasks so events can run

    src = _InfiniteSource()
    sink = FakeAudioSink()
    sess = FakeVoiceSession(events=[AudioOut(b"reply"), TurnComplete()])
    await asyncio.wait_for(VoiceLoop(src, sink, sess).run(), timeout=1.0)
    # mic pump observed the stop signal and exited; events were processed.
    assert sink.played == [b"reply"]
    assert src.sent > 0  # mic did pump at least one chunk before exit
