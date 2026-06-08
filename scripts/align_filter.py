"""Filtrage d'alignement des corpus paralleles par similarite cosinus (encodeur NLLB).

Pour chaque CSV canonique en entree, on encode src_text et tgt_text avec l'encodeur
de facebook/nllb-200-distilled-600M (mean-pooling masque + L2), on calcule le cosinus,
et on ecrit un fichier <stem>_aligned.csv ne gardant que les paires cos >= seuil.
La colonne quality_score est remplacee par le cosinus (score reel d'alignement).

Calibration (validee) : paires propres ~0.66-0.90 ; bruit/mesaligne ~0.33.

Usage :
    .venv/Scripts/python.exe scripts/align_filter.py \
        --inputs data/processed/opus/nllb_ee_fr.csv ... \
        --threshold 0.5 --device cuda
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_NAME = "facebook/nllb-200-distilled-600M"
LANG = {
    "fr": "fra_Latn", "fra": "fra_Latn", "french": "fra_Latn",
    "en": "eng_Latn", "eng": "eng_Latn", "english": "eng_Latn",
    "ee": "ewe_Latn", "ewe": "ewe_Latn",
}


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
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", nargs="+", required=True)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--sample", type=int, default=0, help="sous-echantillon aleatoire avant embedding (0 = tout)")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


@torch.no_grad()
def embed_series(texts: list[str], nllb_lang: str, tok, enc, device, bs, use_bf16) -> np.ndarray:
    tok.src_lang = nllb_lang
    out = []
    ctx = torch.autocast("cuda", dtype=torch.bfloat16) if use_bf16 else torch.autocast("cpu", enabled=False)
    for i in range(0, len(texts), bs):
        batch = [str(x) for x in texts[i : i + bs]]
        enc_in = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=128).to(device)
        with ctx:
            h = enc(**enc_in).last_hidden_state
        m = enc_in["attention_mask"].unsqueeze(-1).float()
        pooled = (h.float() * m).sum(1) / m.sum(1).clamp(min=1)
        pooled = torch.nn.functional.normalize(pooled, dim=-1)
        out.append(pooled.cpu().numpy())
    return np.concatenate(out, axis=0)


def embed_by_lang(df: pd.DataFrame, text_col: str, lang_col: str, tok, enc, device, bs, use_bf16) -> np.ndarray:
    """Embed une colonne texte en respectant la langue ligne par ligne."""
    vecs = np.zeros((len(df), enc.config.d_model), dtype=np.float32)
    for lang_code, idx in df.groupby(lang_col).groups.items():
        idx = list(idx)
        nllb = LANG[str(lang_code).strip().lower()]
        sub = df.loc[idx, text_col].tolist()
        vecs[[df.index.get_loc(i) for i in idx]] = embed_series(sub, nllb, tok, enc, device, bs, use_bf16)
    return vecs


def main() -> None:
    args = parse_args()
    use_bf16 = args.device == "cuda" and torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    print(f"Device: {args.device} | bf16: {use_bf16} | seuil: {args.threshold}")
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    enc = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).get_encoder().to(args.device).eval()

    grand_total = grand_kept = 0
    for path in expand_inputs(args.inputs):
        df = pd.read_csv(path)
        if args.sample and len(df) > args.sample:
            df = df.sample(n=args.sample, random_state=42)
        df = df.reset_index(drop=True)
        sv = embed_by_lang(df, "src_text", "src_lang", tok, enc, args.device, args.batch_size, use_bf16)
        tv = embed_by_lang(df, "tgt_text", "tgt_lang", tok, enc, args.device, args.batch_size, use_bf16)
        cos = (sv * tv).sum(axis=1)
        df["quality_score"] = cos
        kept = df[cos >= args.threshold].copy()
        out = path.with_name(path.stem + "_aligned.csv")
        kept.to_csv(out, index=False, encoding="utf-8")
        grand_total += len(df)
        grand_kept += len(kept)
        print(
            f"{path.name:34} {len(df):>7} -> {len(kept):>7} gardes "
            f"({100*len(kept)/max(len(df),1):4.1f}%) | cos med={np.median(cos):.3f} -> {out.name}"
        )
    print(f"\nTOTAL: {grand_total} -> {grand_kept} ({100*grand_kept/max(grand_total,1):.1f}%)")


if __name__ == "__main__":
    main()