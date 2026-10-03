from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

# 0 means never. HeadsetControl accepts 0–90 minutes for this headset, and
# these are the steps SteelSeries GG offers.
AUTO_OFF_PRESETS = (0, 5, 10, 15, 30, 60, 90)
DEFAULT_AUTO_OFF_MINUTES = 30


@dataclass(frozen=True)
class Settings:
    auto_off_minutes: int = DEFAULT_AUTO_OFF_MINUTES
    low_battery_alert: bool = True


def default_path() -> Path:
    config_root = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config_root) / "headset-tray" / "settings.json"


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_path()

    def load(self) -> Settings:
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return Settings()
        if not isinstance(stored, dict):
            return Settings()

        defaults = Settings()
        minutes = stored.get("auto_off_minutes")
        if isinstance(minutes, bool) or minutes not in AUTO_OFF_PRESETS:
            minutes = defaults.auto_off_minutes
        alert = stored.get("low_battery_alert")
        if not isinstance(alert, bool):
            alert = defaults.low_battery_alert
        return Settings(auto_off_minutes=minutes, low_battery_alert=alert)

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Written beside the real file and renamed over it, so that a crash
        # mid-write never leaves a truncated settings file behind.
        staging = self.path.with_suffix(".tmp")
        staging.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
        staging.replace(self.path)
