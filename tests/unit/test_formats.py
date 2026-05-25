from reef.audio.formats import (
    INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH_BYTES,
    chunk_bytes_for_ms,
)

def test_format_constants():
    assert INPUT_SAMPLE_RATE == 16000
    assert OUTPUT_SAMPLE_RATE == 24000
    assert CHANNELS == 1
    assert SAMPLE_WIDTH_BYTES == 2

def test_chunk_bytes_input_20ms():
    # 16000 Hz * 0.02s = 320 frames * 2 bytes * 1 ch = 640
    assert chunk_bytes_for_ms(20) == 640

def test_chunk_bytes_output_20ms():
    # 24000 Hz * 0.02s = 480 frames * 2 bytes = 960
    assert chunk_bytes_for_ms(20, OUTPUT_SAMPLE_RATE) == 960
