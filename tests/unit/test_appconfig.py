from reef.onboarding.config import AppConfig, load_config, save_config


def test_save_then_load_roundtrip(tmp_path):
    p = str(tmp_path / "config.json")
    save_config(p, AppConfig(hotkey="cmd+shift+r", brief_hour=7, brief_minute=15))
    cfg = load_config(p)
    assert cfg.hotkey == "cmd+shift+r" and cfg.brief_hour == 7 and cfg.brief_minute == 15

def test_load_missing_returns_defaults(tmp_path):
    cfg = load_config(str(tmp_path / "nope.json"))
    assert cfg == AppConfig()
