from pathlib import Path


def synthesize_to_file(text: str, lang: str = "fra") -> Path:
    """Point d'extension TTS. Retourne un chemin cible prévisible."""
    out = Path("logs/tts_placeholder.txt")
    out.parent.mkdir(exist_ok=True)
    out.write_text(f"TTS placeholder ({lang}): {text}", encoding="utf-8")
    return out
