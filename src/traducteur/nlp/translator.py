from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .fallback_dictionary import fallback_translate
from .languages import nllb_code, validate_lang
from .normalization import normalize_text


@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    backend: str
    warning: str | None = None


class Translator(Protocol):
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult: ...


class FallbackTranslator:
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        source_lang = validate_lang(source_lang)
        target_lang = validate_lang(target_lang)
        cleaned = normalize_text(text)
        return TranslationResult(
            source_text=cleaned,
            translated_text=fallback_translate(cleaned, source_lang, target_lang),
            source_lang=source_lang,
            target_lang=target_lang,
            backend="fallback",
            warning="Mode démonstration: aucun modèle neuronal n'est chargé.",
        )


class NLLBTranslator:

    def __init__(self, model_name: str, device: str = "cpu", adapter_path: str | None = None) -> None:
        self.model_name = model_name
        self.device = device
        self.adapter_path = adapter_path
        self._tokenizer = None
        self._model = None
        self._fallback = FallbackTranslator()
        self._load_error: str | None = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch

        # On charge le tokenizer depuis le dossier de l'adaptateur s'il existe (il
        # contient le tokenizer sauvegardé), sinon depuis le modèle de base.
        tokenizer_source = self.adapter_path or self.model_name
        self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        if self.adapter_path:
            from peft import PeftModel

            self._model = PeftModel.from_pretrained(self._model, self.adapter_path)
        if self.device == "cuda" and torch.cuda.is_available():
            self._model = self._model.to("cuda")
        self._model.eval()

    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        source_lang = validate_lang(source_lang)
        target_lang = validate_lang(target_lang)
        cleaned = normalize_text(text)

        try:
            self._load()
        except Exception as exc:  # chargement impossible -> repli dictionnaire
            self._load_error = str(exc)
            result = self._fallback.translate(cleaned, source_lang, target_lang)
            result.warning = (
                "Modèle NLLB indisponible (repli dictionnaire). "
                f"Cause: {type(exc).__name__}."
            )
            return result

        assert self._tokenizer is not None and self._model is not None
        try:
            self._tokenizer.src_lang = nllb_code(source_lang)
            encoded = self._tokenizer(cleaned, return_tensors="pt", truncation=True, max_length=256)
            if self.device == "cuda":
                encoded = {k: v.to("cuda") for k, v in encoded.items()}

            forced_bos_token_id = self._tokenizer.convert_tokens_to_ids(nllb_code(target_lang))
            output = self._model.generate(
                **encoded,
                forced_bos_token_id=forced_bos_token_id,
                max_new_tokens=256,
                num_beams=4,
            )
            translated = self._tokenizer.batch_decode(output, skip_special_tokens=True)[0]
        except Exception as exc:  # génération impossible -> repli dictionnaire
            result = self._fallback.translate(cleaned, source_lang, target_lang)
            result.warning = f"Erreur de génération NLLB (repli dictionnaire): {exc}"
            return result

        return TranslationResult(cleaned, translated, source_lang, target_lang, "nllb")


def build_translator(
    backend: str,
    model_name: str,
    device: str,
    adapter_path: str | None = None,
) -> Translator:
    if backend.lower() == "nllb":
        return NLLBTranslator(model_name=model_name, device=device, adapter_path=adapter_path)
    return FallbackTranslator()
