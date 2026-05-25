# Test fixtures
Drop a short mono 16 kHz PCM WAV named `hello_16k.wav` here (say "hello, what time is it").
Used by tests/integration/test_gemini_smoke.py. Record with QuickTime or:
`ffmpeg -i any_input.m4a -ac 1 -ar 16000 -sample_fmt s16 hello_16k.wav`
