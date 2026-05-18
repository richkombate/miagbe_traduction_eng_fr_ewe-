from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    translation_backend: str = "fallback"  # fallback | nllb
    model_name: str = "facebook/nllb-200-distilled-600M"
    adapter_path: str | None = None
    device: str = "cpu"
    enable_stt: bool = False
    enable_tts: bool = False
    max_input_chars: int = 2000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
