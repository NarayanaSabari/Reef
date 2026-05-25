import json
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass(frozen=True)
class AppConfig:
    hotkey: str = "cmd+shift+r"
    brief_hour: int = 8
    brief_minute: int = 30

def save_config(path: str, config: AppConfig) -> None:
    Path(path).write_text(json.dumps(asdict(config)))

def load_config(path: str) -> AppConfig:
    p = Path(path)
    if not p.exists():
        return AppConfig()
    return AppConfig(**json.loads(p.read_text()))
