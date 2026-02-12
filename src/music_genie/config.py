from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Tuple, Type

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


def _xdg_music_dir() -> Path:
    """Return the XDG music directory, falling back to ~/Music."""
    # 1. Explicit environment variable
    env = os.environ.get("XDG_MUSIC_DIR")
    if env:
        return Path(env)
    # 2. Parse ~/.config/user-dirs.dirs (Linux/freedesktop standard)
    user_dirs = Path.home() / ".config" / "user-dirs.dirs"
    if user_dirs.exists():
        for line in user_dirs.read_text().splitlines():
            if line.startswith("XDG_MUSIC_DIR="):
                val = line.split("=", 1)[1].strip().strip('"')
                return Path(val.replace("$HOME", str(Path.home())))
    # 3. Fallback
    return Path.home() / "Music"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MUSIC_GENIE_",
        extra="ignore",
    )

    output_dir: Path = Field(default_factory=_xdg_music_dir)
    audio_format: str = "mp3"
    audio_quality: int = 192
    record_duration: int = 8

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        from pydantic_settings import TomlConfigSettingsSource

        toml_path = config_dir() / "config.toml"
        if toml_path.exists():
            return (
                init_settings,
                env_settings,
                TomlConfigSettingsSource(settings_cls, toml_file=toml_path),
            )
        return (init_settings, env_settings)

    def model_post_init(self, __context: Any) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        config_dir().mkdir(parents=True, exist_ok=True)
        data_dir().mkdir(parents=True, exist_ok=True)
        snippets_dir().mkdir(parents=True, exist_ok=True)


def config_dir() -> Path:
    return Path.home() / ".config" / "music-genie"


def data_dir() -> Path:
    return Path.home() / ".local" / "share" / "music-genie"


def snippets_dir() -> Path:
    return data_dir() / "snippets"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
