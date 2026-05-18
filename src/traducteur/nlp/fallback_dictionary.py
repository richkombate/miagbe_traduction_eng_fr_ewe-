from __future__ import annotations

from .normalization import normalize_text

# Mini-lexique démonstratif. Il ne remplace pas un vrai modèle NMT.
PHRASES: dict[tuple[str, str], dict[str, str]] = {
    ("fra", "eng"): {
        "bonjour": "hello",
        "bonjour mon ami": "hello my friend",
        "comment allez-vous": "how are you",
        "merci": "thank you",
        "je t'aime": "i love you",
    },
    ("eng", "fra"): {
        "hello": "bonjour",
        "hello my friend": "bonjour mon ami",
        "how are you": "comment allez-vous",
        "thank you": "merci",
        "i love you": "je t'aime",
    },
    ("fra", "ewe"): {
        "bonjour": "ndi",
        "bonjour mon ami": "ndi, xɔ̃nye",
        "merci": "akpe",
        "comment allez-vous": "aleke nèfɔ̃?",
    },
    ("ewe", "fra"): {
        "ndi": "bonjour",
        "akpe": "merci",
        "aleke nèfɔ̃": "comment allez-vous",
    },
    ("eng", "ewe"): {
        "hello": "ndi",
        "thank you": "akpe",
        "how are you": "aleke nèfɔ̃?",
    },
    ("ewe", "eng"): {
        "ndi": "hello",
        "akpe": "thank you",
        "aleke nèfɔ̃": "how are you",
    },
}


def fallback_translate(text: str, source_lang: str, target_lang: str) -> str:
    cleaned = normalize_text(text)
    key = cleaned.lower().rstrip("?.!…")
    table = PHRASES.get((source_lang, target_lang), {})
    if key in table:
        return table[key]
    if source_lang == target_lang:
        return cleaned
    return (
        f"[DÉMO - traduction approximative {source_lang}->{target_lang}] "
        f"{cleaned}"
    )
