from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Identité du projet (travail de groupe universitaire) ---------------------
GROUP_NAME = "GR02"
GROUP_MEMBERS = [
    "AZIGLOSSOU Judith Gracia",
    "NAPO NISSAO Rafia",
    "WOGLO Koffi Boris Gilbride",
    "PIO Sikirou Afeez Prince Cyrille",
    "KOMBATE Gountande",
]
PROJECT_TITLE = "Traducteur Multilingue Français-Anglais-Éwé avec Reconnaissance Vocale"
COURSE = "Master 1 IA-BD EPL S2 - Informatique et Gestion de données"


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
