from reef.voice.ports import AudioOut, TurnComplete
from tests.fakes.fake_voice import FakeVoiceSession


async def test_send_audio_records_chunks():
    sess = FakeVoiceSession(events=[])
    await sess.send_audio(b"a")
    await sess.send_audio(b"b")
    assert sess.sent == [b"a", b"b"]

async def test_receive_yields_scripted_events():
    events = [AudioOut(b"x"), TurnComplete()]
    sess = FakeVoiceSession(events=events)
    got = [ev async for ev in sess.receive()]
    assert got == events

async def test_close_sets_flag():
    sess = FakeVoiceSession(events=[])
    await sess.close()
    assert sess.closed is True
