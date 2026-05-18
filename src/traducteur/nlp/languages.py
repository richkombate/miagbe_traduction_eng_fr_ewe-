from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    iso3: str
    label: str
    nllb_code: str


LANGUAGES: dict[str, Language] = {
    "fra": Language("fra", "Français", "fra_Latn"),
    "eng": Language("eng", "Anglais", "eng_Latn"),
    "ewe": Language("ewe", "Ewe", "ewe_Latn"),
}


def validate_lang(code: str) -> str:
    code = code.lower().strip()
    if code not in LANGUAGES:
        raise ValueError(f"Langue non supportée: {code}. Valeurs: {list(LANGUAGES)}")
    return code


def nllb_code(code: str) -> str:
    return LANGUAGES[validate_lang(code)].nllb_code
