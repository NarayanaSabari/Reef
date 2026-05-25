import os
from pathlib import Path

import pytest

from reef.config import Settings, default_db_path


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "abc123")
    s = Settings.from_env()
    assert s.api_key == "abc123"
    assert s.input_sample_rate == 16000
    assert s.output_sample_rate == 24000
    assert s.model.startswith("gemini-")

def test_settings_model_override(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "abc123")
    monkeypatch.setenv("REEF_MODEL", "gemini-test-model")
    assert Settings.from_env().model == "gemini-test-model"

def test_settings_missing_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        Settings.from_env()


def test_default_db_path_absolute_under_home():
    p = default_db_path()
    assert os.path.isabs(p) and p.endswith("reef.db") and str(Path.home()) in p
