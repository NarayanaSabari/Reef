INPUT_SAMPLE_RATE = 16000   # Gemini Live input: 16 kHz PCM
OUTPUT_SAMPLE_RATE = 24000  # Gemini Live output: 24 kHz PCM
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2      # 16-bit signed PCM

def chunk_bytes_for_ms(ms: int, sample_rate: int = INPUT_SAMPLE_RATE) -> int:
    """Bytes in `ms` of mono int16 PCM at `sample_rate`."""
    frames = sample_rate * ms // 1000
    return frames * SAMPLE_WIDTH_BYTES * CHANNELS
