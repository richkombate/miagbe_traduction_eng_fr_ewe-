"""Calibration du filtrage d'alignement par similarite cosinus (encodeur NLLB).

On encode chaque cote d'une paire avec l'encodeur de facebook/nllb-200-distilled-600M
(mean-pooling masque + normalisation L2) puis on calcule le cosinus. Objectif :
verifier que les paires bien alignees scorent HAUT et le bruit/mesaligne scorent BAS.

Sortie : distributions (percentiles) par direction + un CSV d'exemples horodate.
Usage :
    .venv/Scripts/python.exe scripts/align_calibrate.py --per-dir 150 --device cpu
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_NAME = "facebook/nllb-200-distilled-600M"
NLLB = {"fra": "fra_Latn", "eng": "eng_Latn", "ewe": "ewe_Latn"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--train-csv", default="data/processed/nllb/nllb_train.csv")
    p.add_argument("--per-dir", type=int, default=150, help="paires echantillonnees par direction")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--out", default="data/processed/nllb/align_calibration.csv")
    return p.parse_args()


@torch.no_grad()
def embed(texts: list[str], lang: str, tok, enc, device: str, batch_size: int) -> np.ndarray:
    tok.src_lang = NLLB[lang]
    vecs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        enc_in = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=128).to(device)
        out = enc(**enc_in).last_hidden_state  # (B, T, H)
        mask = enc_in["attention_mask"].unsqueeze(-1).float()
        pooled = (out * mask).sum(1) / mask.sum(1).clamp(min=1)  # mean-pool masque
        pooled = torch.nn.functional.normalize(pooled, dim=-1)
        vecs.append(pooled.float().cpu().numpy())
    return np.concatenate(vecs, axis=0)


def main() -> None:
    args = parse_args()
    print(f"Device: {args.device}")
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    enc = model.get_encoder().to(args.device).eval()

    df = pd.read_csv(args.train_csv)
    rows = []
    for (sl, tl), grp in df.groupby(["src_lang", "tgt_lang"], sort=True):
        grp = grp.sample(n=min(args.per_dir, len(grp)), random_state=0).reset_index(drop=True)
        src_vec = embed(grp["src_text"].tolist(), sl, tok, enc, args.device, args.batch_size)
        tgt_vec = embed(grp["tgt_text"].tolist(), tl, tok, enc, args.device, args.batch_size)
        cos = (src_vec * tgt_vec).sum(axis=1)
        g = grp.copy()
        g["cos"] = cos
        rows.append(g[["src_lang", "tgt_lang", "src_text", "tgt_text", "source", "cos"]])
        pcts = np.percentile(cos, [5, 25, 50, 75, 95])
        print(
            f"{sl}->{tl:4} n={len(grp):4} | cos p5={pcts[0]:.3f} "
            f"p25={pcts[1]:.3f} med={pcts[2]:.3f} p75={pcts[3]:.3f} p95={pcts[4]:.3f} "
            f"| <0.5 : {100*(cos<0.5).mean():.0f}%"
        )

    out = pd.concat(rows, ignore_index=True).sort_values(["src_lang", "tgt_lang", "cos"])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False, encoding="utf-8")
    print("Detail ecrit dans:", args.out)


if __name__ == "__main__":
    main()
