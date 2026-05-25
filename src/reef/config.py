import os
from dataclasses import dataclass
from pathlib import Path
from reef.audio.formats import INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE, CHANNELS


def default_db_path() -> str:
    """Absolute path to Reef's local DB (~/.reef/reef.db) so it doesn't depend on CWD."""
    return str(Path.home() / ".reef" / "reef.db")

DEFAULT_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str = DEFAULT_MODEL
    input_sample_rate: int = INPUT_SAMPLE_RATE
    output_sample_rate: int = OUTPUT_SAMPLE_RATE
    channels: int = CHANNELS

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("No API key: set GOOGLE_API_KEY (or GEMINI_API_KEY)")
        return cls(api_key=key, model=os.environ.get("REEF_MODEL", DEFAULT_MODEL))
