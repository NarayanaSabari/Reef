from tests.fakes.fake_audio import FakeAudioSource, FakeAudioSink

async def test_source_yields_chunks_in_order():
    src = FakeAudioSource([b"a", b"b", b"c"])
    got = [chunk async for chunk in src.stream()]
    assert got == [b"a", b"b", b"c"]

async def test_sink_records_played_audio():
    sink = FakeAudioSink()
    await sink.play(b"x")
    await sink.play(b"y")
    assert sink.played == [b"x", b"y"]

async def test_sink_flush_increments_counter():
    sink = FakeAudioSink()
    await sink.play(b"x")
    await sink.flush()
    assert sink.flush_count == 1
    assert sink.played == [b"x"]  # history preserved for assertions
