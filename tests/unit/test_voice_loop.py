import asyncio
from reef.voice.ports import AudioOut, Interrupted, TurnComplete
from reef.voice.loop import VoiceLoop
from tests.fakes.fake_audio import FakeAudioSource, FakeAudioSink
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
