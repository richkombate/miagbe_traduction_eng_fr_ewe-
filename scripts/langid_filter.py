"""Filtrage par identification de langue (fastText NLLB-LID).

Le filtre cosinus (`align_filter.py`) ne detecte PAS la contamination de langue :
l'encodeur NLLB etant multilingue, une paire "Menu pour le reinitialiser" ->
"menu to be reset" obtient un cosinus eleve (bonne traduction... mais la cible
est en ANGLAIS, pas en ewe). Ce script verifie que chaque texte est reellement
ecrit dans la langue declaree, a l'aide du modele officiel NLLB
`facebook/fasttext-language-identification` (218 langues, dont ewe_Latn).

Pour chaque CSV canonique en entree (colonnes src_lang/tgt_lang/src_text/tgt_text),
on predit la langue de chaque cote et on ne garde que les lignes ou la langue
predite correspond a la langue declaree (avec une confiance >= --min-prob).
Sortie : <stem>_lid.csv.

Usage :
    .venv/Scripts/python.exe scripts/langid_filter.py \
        --inputs data/processed/opus/nllb_ee_fr_aligned.csv ... \
        --min-prob 0.5 --check both
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

# Codes courts (CSV canoniques) -> etiquettes fastText NLLB-LID.
LANG_TO_LID = {
    "fra": "fra_Latn", "fr": "fra_Latn", "french": "fra_Latn", "fra_latn": "fra_Latn",
    "eng": "eng_Latn", "en": "eng_Latn", "english": "eng_Latn", "eng_latn": "eng_Latn",
    "ewe": "ewe_Latn", "ee": "ewe_Latn", "ewe_latn": "ewe_Latn",
}

LID_REPO = "facebook/fasttext-language-identification"
LID_FILE = "model.bin"


def lid_code(value: object) -> str:
    key = str(value or "").strip().lower()
    if key not in LANG_TO_LID:
        raise ValueError(f"Langue non supportee: {value!r}")
    return LANG_TO_LID[key]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Filtre les paires dont le texte n'est pas dans la langue declaree.")
    p.add_argument("--inputs", nargs="+", required=True, help="CSV canoniques a filtrer.")
    p.add_argument("--min-prob", type=float, default=0.5,
                   help="Confiance minimale de la langue predite (top-1) pour garder la ligne.")
    p.add_argument("--check", choices=["both", "tgt", "src"], default="both",
                   help="Quel(s) cote(s) doivent correspondre a la langue declaree.")
    p.add_argument("--suffix", default="_lid", help="Suffixe ajoute au nom de fichier de sortie.")
    return p.parse_args()


def load_model():
    import fasttext
    from huggingface_hub import hf_hub_download

    print(f"Telechargement/cache du modele {LID_REPO}/{LID_FILE} ...")
    model_path = hf_hub_download(repo_id=LID_REPO, filename=LID_FILE)
    print(f"Chargement fastText : {model_path}")
    # fasttext affiche un warning de chargement inoffensif ; on le tolere.
    return fasttext.load_model(model_path)


def predict_langs(model, texts: list[str]) -> tuple[list[str], list[float]]:
    """Predit la langue top-1 de chaque texte. Renvoie (labels, probas).

    fastText refuse les retours a la ligne -> on les remplace par des espaces.
    """
    cleaned = [t.replace("\n", " ").replace("\r", " ").strip() for t in texts]
    labels, probs = model.predict(cleaned, k=1)
    out_labels = [lab[0].replace("__label__", "") if lab else "" for lab in labels]
    out_probs = [float(pr[0]) if len(pr) else 0.0 for pr in probs]
    # Un texte vide ne peut pas etre une langue valide.
    out_labels = [lab if cleaned[i] else "" for i, lab in enumerate(out_labels)]
    return out_labels, out_probs


def filter_one(model, path: Path, min_prob: float, check: str, suffix: str) -> tuple[int, int]:
    df = pd.read_csv(path).reset_index(drop=True)
    for col in ("src_lang", "tgt_lang", "src_text", "tgt_text"):
        if col not in df.columns:
            raise ValueError(f"{path} : colonne manquante {col!r}")

    df["src_text"] = df["src_text"].fillna("").astype(str)
    df["tgt_text"] = df["tgt_text"].fillna("").astype(str)
    exp_src = df["src_lang"].map(lid_code)
    exp_tgt = df["tgt_lang"].map(lid_code)

    pred_src, prob_src = predict_langs(model, df["src_text"].tolist())
    pred_tgt, prob_tgt = predict_langs(model, df["tgt_text"].tolist())
    pred_src = pd.Series(pred_src, index=df.index)
    pred_tgt = pd.Series(pred_tgt, index=df.index)
    prob_src = pd.Series(prob_src, index=df.index)
    prob_tgt = pd.Series(prob_tgt, index=df.index)

    ok_src = (pred_src == exp_src) & (prob_src >= min_prob)
    ok_tgt = (pred_tgt == exp_tgt) & (prob_tgt >= min_prob)
    if check == "both":
        keep = ok_src & ok_tgt
    elif check == "tgt":
        keep = ok_tgt
    else:
        keep = ok_src

    kept = df[keep].copy()
    out = path.with_name(path.stem + suffix + ".csv")
    kept.to_csv(out, index=False, encoding="utf-8")

    # Diagnostic : sur le cote ewe (src OU tgt selon le corpus), quelles langues
    # "intruses" ont fait rejeter des lignes ? (typiquement de l'anglais)
    ewe_pred_dropped: list[str] = []
    if (exp_src == "ewe_Latn").any():
        ewe_pred_dropped += pred_src[~ok_src & (exp_src == "ewe_Latn")].tolist()
    if (exp_tgt == "ewe_Latn").any():
        ewe_pred_dropped += pred_tgt[~ok_tgt & (exp_tgt == "ewe_Latn")].tolist()
    top = Counter(ewe_pred_dropped).most_common(5)
    top_str = ", ".join(f"{lang or '(vide/inconnu)'}={n}" for lang, n in top) if len(top) else "-"
    pct = 100 * len(kept) / max(len(df), 1)
    print(f"{path.name:38} {len(df):>7} -> {len(kept):>7} gardes ({pct:4.1f}%)"
          f" | cote ewe rejete surtout: {top_str} -> {out.name}")
    return len(df), len(kept)


def main() -> None:
    args = parse_args()
    model = load_model()
    grand_total = grand_kept = 0
    for path_str in args.inputs:
        total, kept = filter_one(model, Path(path_str), args.min_prob, args.check, args.suffix)
        grand_total += total
        grand_kept += kept
    pct = 100 * grand_kept / max(grand_total, 1)
    print(f"\nTOTAL: {grand_total} -> {grand_kept} ({pct:.1f}%) gardes")


if __name__ == "__main__":
    main()
