from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

# Code ISO-3 du projet -> modèle MMS-TTS (VITS) correspondant sur Hugging Face.
_MMS_MODELS = {
    "fra": "facebook/mms-tts-fra",
    "eng": "facebook/mms-tts-eng",
    "ewe": "facebook/mms-tts-ewe",
}


@lru_cache
def _get_model(lang: str):
    """Charge paresseusement le modèle VITS d'une langue (une seule fois)."""
    from transformers import AutoTokenizer, VitsModel

    model_id = _MMS_MODELS[lang]
    model = VitsModel.from_pretrained(model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model.eval()
    return model, tokenizer


def synthesize_to_wav(text: str, lang: str = "fra") -> tuple[bytes, int]:
    """Synthétise ``text`` dans ``lang`` et renvoie ``(wav_bytes, sample_rate)``."""
    import soundfile as sf
    import torch

    if lang not in _MMS_MODELS:
        raise ValueError(f"Langue TTS non supportée: {lang!r}. Valeurs: {list(_MMS_MODELS)}")
    text = (text or "").strip()
    if not text:
        return b"", 16000

    model, tokenizer = _get_model(lang)
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform  # forme (1, n_échantillons), float32 dans [-1, 1]
    audio = waveform.squeeze(0).cpu().numpy().astype("float32")
    sample_rate = int(model.config.sampling_rate)

    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue(), sample_rate


def synthesize_to_file(text: str, lang: str = "fra", out_dir: str = "logs") -> Path:
    """Variante fichier : écrit un .wav et renvoie son chemin (utile pour tests/CLI)."""
    wav, _ = synthesize_to_wav(text, lang)
    out = Path(out_dir) / f"tts_{lang}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(wav)
    return out