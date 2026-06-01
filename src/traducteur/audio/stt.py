from __future__ import annotations

import io
from functools import lru_cache

# Codes ISO-3 du projet -> codes langue Whisper
_WHISPER_LANG = {"fra": "french", "eng": "english", "ewe": None}

# Modèle Whisper par défaut (léger). Pour de meilleurs résultats: openai/whisper-small.
_WHISPER_MODEL = "openai/whisper-base"


@lru_cache
def _get_pipeline():
    """Charge paresseusement le pipeline Whisper (Speech-to-Text).

    Isolé dans une fonction cachée pour ne charger le modèle qu'une seule fois,
    et seulement lorsque la transcription serveur est réellement demandée.
    """
    from transformers import pipeline

    return pipeline("automatic-speech-recognition", model=_WHISPER_MODEL)


def transcribe(audio_bytes: bytes, lang: str = "fra") -> str:
    """Transcrit un enregistrement audio en texte avec Whisper (OpenAI).

    L'éwé n'est pas couvert nativement par Whisper : on laisse alors le modèle
    détecter automatiquement la langue. Pour le français et l'anglais, on force
    la langue cible afin d'améliorer la précision.

    L'audio est décodé avec ``librosa`` (rééchantillonné à 16 kHz, mono), ce qui
    accepte la plupart des formats (wav, flac, ogg, et webm/opus si ffmpeg est
    présent sur la machine).
    """
    if not audio_bytes:
        return ""

    import librosa

    waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

    asr = _get_pipeline()
    generate_kwargs = {}
    whisper_lang = _WHISPER_LANG.get(lang)
    if whisper_lang:
        generate_kwargs["language"] = whisper_lang
        generate_kwargs["task"] = "transcribe"

    result = asr(waveform, generate_kwargs=generate_kwargs)
    return (result.get("text") or "").strip()
