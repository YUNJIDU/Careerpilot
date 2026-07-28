import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.security import safe_path


class LocalSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(default="personal", max_length=100)
    email: str = Field(default="", max_length=320)
    tracker_path: str = "tracker.xlsx"
    markdown_path: str = "markdown"
    model_base_url: str = Field(default="", max_length=500)
    model_name: str = Field(default="", max_length=200)
    scheduling_enabled: bool = False


class SettingsStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.path = data_dir / "settings.json"

    def load(self) -> LocalSettings:
        if not self.path.exists():
            return LocalSettings()
        return LocalSettings.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, values: dict[str, Any]) -> LocalSettings:
        settings = LocalSettings.model_validate(values)
        if settings.scheduling_enabled:
            raise ValueError("scheduling is not available")
        safe_path(self.data_dir, Path(settings.tracker_path))
        safe_path(self.data_dir, Path(settings.markdown_path))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.data_dir, delete=False
        ) as temporary:
            json.dump(settings.model_dump(), temporary, ensure_ascii=False, indent=2)
            temporary_path = Path(temporary.name)
        temporary_path.replace(self.path)
        return settings
