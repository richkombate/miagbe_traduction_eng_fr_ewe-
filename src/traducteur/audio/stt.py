from __future__ import annotations


def transcribe(audio_bytes: bytes, lang: str = "fra") -> str:
    """Point d'extension STT.

    Version volontairement légère. Pour la soutenance, intégrer ici Whisper pour fr/en
    et MMS/Whisper adapté pour ewe.
    """
    if not audio_bytes:
        return ""
    return "[Transcription STT à activer avec Whisper/MMS]"
