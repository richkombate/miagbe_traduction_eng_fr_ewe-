import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalise le texte sans détruire les caractères ewe.

    On conserve les lettres comme ɖ, ɛ, ƒ, ɣ, ŋ, ɔ, ʋ et les tons.
    """
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_reasonable_text(text: str, max_chars: int = 2000) -> bool:
    text = normalize_text(text)
    return 0 < len(text) <= max_chars
