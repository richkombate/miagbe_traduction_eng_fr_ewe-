"""Augmentation par back-translation (cf. cahier des charges 2.b).

Principe : on garde l'EWE humain en CIBLE et on genere une SOURCE synthetique.
On part des paires propres (ewe_humain, fr_humain) du SPLIT TRAIN uniquement
(pas de fuite test/valid), et on utilise le modele entraine pour :

  A. fr -> en   => nouvelles paires  en_synth -> ewe_humain   (enrichit en->ewe, divers/non-biblique)
  B. ewe -> fr  => nouvelles paires  fr_synth -> ewe_humain   (renforce fr->ewe, casse l'off-target)

Sortie : data/processed/nllb/nllb_train_aug.csv = train original + paires synthetiques.
Le test et le valid ne sont PAS modifies.

Usage :
    .venv/Scripts/python.exe scripts/make_backtranslation.py --sample-a 150000 --sample-b 100000
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
import torch
from peft import PeftModel
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

BASE = "facebook/nllb-200-distilled-600M"
ADAPTER = "models/nllb-ewe-lora"
NLLB = {"fra": "fra_Latn", "eng": "eng_Latn", "ewe": "ewe_Latn"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-csv", default="data/processed/nllb/nllb_train.csv")
    ap.add_argument("--out", default="data/processed/nllb/nllb_train_aug.csv")
    ap.add_argument("--sample-a", type=int, default=60000, help="paires pour fr->en (en->ewe)")
    ap.add_argument("--sample-b", type=int, default=60000, help="paires pour ewe->fr (fr->ewe)")
    ap.add_argument("--min-quality", type=float, default=0.65, help="cos minimal du pool (cibles ewe pristines)")
    ap.add_argument("--batch-size", type=int, default=48)
    ap.add_argument("--num-beams", type=int, default=4)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return ap.parse_args()


def sid(*parts: object) -> str:
    return hashlib.sha1("␟".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def main() -> None:
    args = parse_args()
    tok = AutoTokenizer.from_pretrained(ADAPTER)
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE)
    model = PeftModel.from_pretrained(model, ADAPTER).to(args.device).eval()
    try:
        model.generation_config.max_length = None
    except Exception:
        pass
    use_bf16 = args.device == "cuda" and torch.cuda.is_bf16_supported()

    @torch.no_grad()
    def translate_batch(texts: list[str], src: str, tgt: str) -> list[str]:
        tok.src_lang = NLLB[src]
        bos = tok.convert_tokens_to_ids(NLLB[tgt])
        out: list[str] = []
        ctx = torch.autocast("cuda", dtype=torch.bfloat16) if use_bf16 else torch.autocast("cpu", enabled=False)
        for i in range(0, len(texts), args.batch_size):
            batch = [str(x) for x in texts[i : i + args.batch_size]]
            enc = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=128).to(args.device)
            with ctx:
                gen = model.generate(**enc, forced_bos_token_id=bos, max_new_tokens=128, num_beams=args.num_beams)
            out.extend(tok.batch_decode(gen, skip_special_tokens=True))
            if (i // args.batch_size) % 50 == 0:
                print(f"  {src}->{tgt}: {min(i + args.batch_size, len(texts))}/{len(texts)}", flush=True)
        return out

    train = pd.read_csv(args.train_csv)
    # Pool de paires (ewe_humain, fr_humain) issues du TRAIN uniquement.
    pool = train[(train.src_lang == "ewe") & (train.tgt_lang == "fra")][["src_text", "tgt_text", "quality_score"]].copy()
    pool.columns = ["ewe", "fr", "cos"]
    pool = pool.dropna().drop_duplicates(subset=["ewe", "fr"]).reset_index(drop=True)
    # Cibles ewe PRISTINES uniquement : cos eleve + presence de caracteres ewe specifiques
    # (evite d'injecter du bruit type "Bad guy be me" comme cible de back-translation).
    ewe_chars = set("ɖƒŋɔɛɣʋ̃")
    has_ewe = pool["ewe"].map(lambda s: any(c in ewe_chars for c in str(s)))
    pool = pool[(pool["cos"].astype(float) >= args.min_quality) & has_ewe].reset_index(drop=True)
    print(f"Pool ewe-fr propre (train, cos>={args.min_quality} + car. ewe): {len(pool)} paires")

    new_rows = []

    def emit(src_lang, tgt_lang, src_texts, ewe_targets, source_tag):
        for s, e in zip(src_texts, ewe_targets):
            s, e = str(s).strip(), str(e).strip()
            if not s or not e:
                continue
            new_rows.append({
                "id": sid("train", src_lang, tgt_lang, s, e),
                "split": "train",
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "src_lang_nllb": NLLB[src_lang],
                "tgt_lang_nllb": NLLB[tgt_lang],
                "src_text": s,
                "tgt_text": e,
                "source": source_tag,
                "domain": "synthetic",
                "quality_score": 1.0,
                "is_religious": False,
                "license": "",
            })

    # A. fr -> en  =>  en_synth -> ewe_humain
    if args.sample_a > 0:
        a = pool.sample(n=min(args.sample_a, len(pool)), random_state=1)
        print(f"[A] fr->en sur {len(a)} paires (cree en->ewe)")
        en_synth = translate_batch(a["fr"].tolist(), "fra", "eng")
        emit("eng", "ewe", en_synth, a["ewe"].tolist(), "synthetic:bt:fr2en")

    # B. ewe -> fr  =>  fr_synth -> ewe_humain
    if args.sample_b > 0:
        b = pool.sample(n=min(args.sample_b, len(pool)), random_state=2)
        print(f"[B] ewe->fr sur {len(b)} paires (cree fr->ewe)")
        fr_synth = translate_batch(b["ewe"].tolist(), "ewe", "fra")
        emit("fra", "ewe", fr_synth, b["ewe"].tolist(), "synthetic:bt:ewe2fr")

    aug = pd.DataFrame(new_rows)
    print(f"Paires synthetiques generees: {len(aug)}")
    out_df = pd.concat([train, aug], ignore_index=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"Train augmente: {len(train)} + {len(aug)} = {len(out_df)} -> {args.out}")
    print(out_df.groupby(["src_lang", "tgt_lang"]).size().to_string())


if __name__ == "__main__":
    main()
