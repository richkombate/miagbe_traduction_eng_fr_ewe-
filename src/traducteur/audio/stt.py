from __future__ import annotations

import io
from functools import lru_cache

# Codes ISO-3 du projet -> codes langue Whisper (fr/en). L'éwé n'est PAS géré par
# Whisper : il passe par MMS-ASR (Meta, basé sur Wav2Vec2) plus bas.
_WHISPER_LANG = {"fra": "french", "eng": "english"}

# Modèle Whisper par défaut (léger). Pour de meilleurs résultats: openai/whisper-small.
_WHISPER_MODEL = "openai/whisper-base"

# MMS-ASR couvre 1100+ langues dont l'éwé. Code MMS de l'éwé = "ewe".
_MMS_ASR_MODEL = "facebook/mms-1b-all"
_MMS_LANG = {"ewe": "ewe", "fra": "fra", "eng": "eng"}


@lru_cache
def _get_pipeline():
    """Charge paresseusement le pipeline Whisper (Speech-to-Text) pour fr/en."""
    from transformers import pipeline

    return pipeline("automatic-speech-recognition", model=_WHISPER_MODEL)


@lru_cache
def _get_mms_asr():
    """Charge paresseusement MMS-ASR (Wav2Vec2 multilingue) — pour l'éwé."""
    from transformers import AutoProcessor, Wav2Vec2ForCTC

    processor = AutoProcessor.from_pretrained(_MMS_ASR_MODEL)
    model = Wav2Vec2ForCTC.from_pretrained(_MMS_ASR_MODEL)
    model.eval()
    return processor, model


def _transcribe_mms(waveform, lang: str) -> str:
    """Transcrit un signal 16 kHz avec MMS-ASR en activant l'adaptateur de langue."""
    import torch

    mms_lang = _MMS_LANG[lang]
    processor, model = _get_mms_asr()
    # Bascule le modèle sur l'adaptateur de la langue cible (ex. "ewe").
    processor.tokenizer.set_target_lang(mms_lang)
    model.load_adapter(mms_lang)

    inputs = processor(waveform, sampling_rate=16000, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    predicted_ids = torch.argmax(logits, dim=-1)
    return processor.batch_decode(predicted_ids)[0].strip()


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

    # Décodage robuste sans ffmpeg : le navigateur envoie du WAV, lu par soundfile.
    waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

    # Éwé -> MMS-ASR (Whisper ne couvre pas l'éwé).
    if lang == "ewe":
        return _transcribe_mms(waveform, "ewe")

    # Français / anglais -> Whisper.
    asr = _get_pipeline()
    generate_kwargs = {}
    whisper_lang = _WHISPER_LANG.get(lang)
    if whisper_lang:
        generate_kwargs["language"] = whisper_lang
        generate_kwargs["task"] = "transcribe"

    result = asr(waveform, generate_kwargs=generate_kwargs)
    return (result.get("text") or "").strip()
