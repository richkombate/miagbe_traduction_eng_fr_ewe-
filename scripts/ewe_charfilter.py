"""Filtrage de la contamination par caracteres specifiques a l'ewe.

fastText NLLB-LID (`langid_filter.py`) ne separe PAS l'anglais de l'ewe sur les
textes courts : il etiquette `ewe_Latn` avec forte confiance presque tout le cote
declare ewe, y compris de l'anglais evident ("By Mawuena Agede," -> ewe 0.971).
Aucun seuil de probabilite ne separe le vrai ewe ASCII (~0.96) de l'anglais
bruite (~0.97).

Le seul signal fiable est orthographique : le vrai ewe contient presque toujours
des caracteres que l'anglais n'a JAMAIS (ɖ ƒ ŋ ɔ ɛ ɣ ʋ + majuscules + voyelles
nasalisees / diacritiques de ton). Ce script ne garde que les lignes ou CHAQUE
cote declare ewe contient au moins un de ces caracteres.

Compromis assume : on supprime aussi le vrai ewe ecrit en pur ASCII (impossible a
distinguer automatiquement de l'anglais), au profit d'une precision maximale. Les
cotes non-ewe (fr, en) ne sont pas touches.

Usage :
    .venv/Scripts/python.exe scripts/ewe_charfilter.py \
        --inputs data/processed/opus/*_lid.csv data/processed/hf/*_lid.csv
Sortie : <stem>_ewe.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# Caracteres uniques a l'ewe (jamais en anglais) : consonnes/voyelles speciales
# (minuscules + majuscules) + voyelles nasalisees precomposees + diacritiques
# combinants de ton/nasalisation.
EWE_CHARS = set(
    "ɖƒŋɔɛɣʋ"          # minuscules : d-cedille, f-hook, eng, open-o, open-e, gamma, v-hook
    "ƉƑŊƆƐƔƲ"          # majuscules correspondantes
    "ãẽĩõũ"            # voyelles nasalisees precomposees (NFC)
    "̣̃̀́̄̌"  # tilde, grave, aigu, macron, caron, point souscrit (combinants)
)

EWE_ALIASES = {"ewe", "ee", "ewe_latn"}


def is_ewe_decl(value: object) -> bool:
    return str(value or "").strip().lower() in EWE_ALIASES


def has_ewe_char(text: object) -> bool:
    return any(c in EWE_CHARS for c in str(text or ""))


def expand_inputs(patterns: list[str]) -> list[Path]:
    """Developpe les globs (PowerShell ne le fait pas pour les .exe externes)."""
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(Path().glob(pattern.replace("\\", "/")))
        if matches:
            paths.extend(matches)
        elif Path(pattern).exists():
            paths.append(Path(pattern))
    unique = sorted({p.resolve() for p in paths})
    if not unique:
        raise FileNotFoundError(f"Aucun fichier ne correspond a: {patterns}")
    return unique


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Garde les paires dont chaque cote declare ewe contient un caractere ewe specifique."
    )
    p.add_argument("--inputs", nargs="+", required=True, help="CSV canoniques a filtrer.")
    p.add_argument("--suffix", default="_ewe", help="Suffixe ajoute au nom de fichier de sortie.")
    return p.parse_args()


def filter_one(path: Path, suffix: str) -> tuple[int, int]:
    df = pd.read_csv(path).reset_index(drop=True)
    for col in ("src_lang", "tgt_lang", "src_text", "tgt_text"):
        if col not in df.columns:
            raise ValueError(f"{path} : colonne manquante {col!r}")

    df["src_text"] = df["src_text"].fillna("").astype(str)
    df["tgt_text"] = df["tgt_text"].fillna("").astype(str)

    src_is_ewe = df["src_lang"].map(is_ewe_decl)
    tgt_is_ewe = df["tgt_lang"].map(is_ewe_decl)
    # Une ligne est rejetee seulement si un cote declare ewe n'a aucun caractere ewe.
    src_bad = src_is_ewe & ~df["src_text"].map(has_ewe_char)
    tgt_bad = tgt_is_ewe & ~df["tgt_text"].map(has_ewe_char)
    keep = ~(src_bad | tgt_bad)

    kept = df[keep].copy()
    out = path.with_name(path.stem + suffix + ".csv")
    kept.to_csv(out, index=False, encoding="utf-8")

    n_ewe_rows = int((src_is_ewe | tgt_is_ewe).sum())
    n_dropped = int((~keep).sum())
    pct = 100 * len(kept) / max(len(df), 1)
    print(
        f"{path.name:42} {len(df):>7} -> {len(kept):>7} gardes ({pct:4.1f}%)"
        f" | lignes avec cote ewe: {n_ewe_rows} | rejetees (ewe sans car. ewe): {n_dropped}"
        f" -> {out.name}"
    )
    return len(df), len(kept)


def main() -> None:
    args = parse_args()
    grand_total = grand_kept = 0
    for path in expand_inputs(args.inputs):
        total, kept = filter_one(path, args.suffix)
        grand_total += total
        grand_kept += kept
    pct = 100 * grand_kept / max(grand_total, 1)
    print(f"\nTOTAL: {grand_total} -> {grand_kept} ({pct:.1f}%) gardes")


if __name__ == "__main__":
    main()
