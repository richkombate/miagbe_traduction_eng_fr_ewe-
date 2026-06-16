"""Compare le NLLB de base vs l'adaptateur LoRA, par direction (BLEU / chrF).

Le modèle de base est chargé UNE SEULE FOIS : on l'enrobe avec l'adaptateur LoRA,
puis on évalue la version « LoRA » normalement et la version « base » à l'intérieur
d'un contexte ``model.disable_adapter()`` (peft). Pas de double chargement mémoire.

Jeux d'évaluation :
  --source flores  (recommandé) : FLORES-200, parfaitement aligné -> scores comparables
                                  à l'état de l'art, et HONNÊTES pour en<->ewe.
Exemples :
    .venv/Scripts/python.exe scripts/compare_base_vs_lora.py --source flores --device cuda
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from pathlib import Path

import pandas as pd
import torch

BASE_DEFAULT = "facebook/nllb-200-distilled-600M"
ADAPTER_DEFAULT = "models/nllb-ewe-lora"
# Codes courts du projet -> codes FLORES / NLLB.
LANGS = {"eng": "eng_Latn", "fra": "fra_Latn", "ewe": "ewe_Latn"}


# --------------------------------------------------------------------------- args
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE_DEFAULT)
    ap.add_argument("--adapter", default=ADAPTER_DEFAULT)
    ap.add_argument("--source", choices=["flores", "local"], default="flores")
    ap.add_argument("--flores-split", default="devtest", help="dev | devtest")
    ap.add_argument("--local-test", default="data/processed/nllb/nllb_test.csv")
    ap.add_argument("--min-cos", type=float, default=0.0,
                    help="(local) seuil sur quality_score (cosinus) pour écarter les paires mésalignées")
    ap.add_argument("--max-per-direction", type=int, default=300)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--num-beams", type=int, default=4)
    ap.add_argument("--max-new-tokens", type=int, default=128)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--output", default="models/compare_base_vs_lora.csv")
    ap.add_argument("--examples", type=int, default=4, help="exemples enregistrés par direction")
    return ap.parse_args()


# ------------------------------------------------------------------- jeux de test
def build_flores(split: str) -> pd.DataFrame:
    """Charge FLORES (aligné par phrase) et construit les 6 directions."""
    from datasets import load_dataset

    texts: dict[str, list[str]] = {}
    try:  # FLORES+ : un config par langue, jointure par 'id'.
        per_id: dict[str, dict[str, str]] = {}
        for short, code in LANGS.items():
            ds = load_dataset("openlanguagedata/flores_plus", code, split=split)
            per_id[short] = {str(r["id"]): r["text"] for r in ds}
        common = sorted(set.intersection(*[set(d) for d in per_id.values()]))
        texts = {short: [per_id[short][i] for i in common] for short in LANGS}
    except Exception as exc:  # repli : config "all" de facebook/flores.
        print(f"[FLORES+] indisponible ({type(exc).__name__}), repli sur facebook/flores 'all'…")
        ds = load_dataset("facebook/flores", "all", split=split, trust_remote_code=True)
        texts = {short: [r[f"sentence_{code}"] for r in ds] for short, code in LANGS.items()}

    n = len(next(iter(texts.values())))
    print(f"FLORES {split}: {n} phrases alignées par langue.")
    rows = []
    for s in LANGS:
        for t in LANGS:
            if s == t:
                continue
            for i in range(n):
                rows.append({"src_lang": s, "tgt_lang": t,
                             "src_text": texts[s][i], "tgt_text": texts[t][i]})
    return pd.DataFrame(rows)


def build_local(path: str, min_cos: float) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["src_text"].notna() & df["tgt_text"].notna()].copy()
    if min_cos > 0 and "quality_score" in df.columns:
        before = len(df)
        df = df[pd.to_numeric(df["quality_score"], errors="coerce").fillna(0) >= min_cos]
        print(f"Filtre cosinus >= {min_cos}: {before} -> {len(df)} paires gardées.")
    return df[["src_lang", "tgt_lang", "src_text", "tgt_text"]]


def add_nllb_codes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["src_nllb"] = df["src_lang"].map(LANGS)
    df["tgt_nllb"] = df["tgt_lang"].map(LANGS)
    return df.dropna(subset=["src_nllb", "tgt_nllb"]).reset_index(drop=True)


# ------------------------------------------------------------------- génération
def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def make_generator(model, tok, args, use_bf16):
    @torch.no_grad()
    def generate(group: pd.DataFrame, use_adapter: bool) -> list[str]:
        tok.src_lang = group.iloc[0]["src_nllb"]
        bos = tok.convert_tokens_to_ids(group.iloc[0]["tgt_nllb"])
        adapter_ctx = nullcontext() if use_adapter else model.disable_adapter()
        autocast_ctx = (torch.autocast("cuda", dtype=torch.bfloat16)
                        if use_bf16 else nullcontext())
        preds: list[str] = []
        with adapter_ctx:
            for batch in chunks([str(x) for x in group["src_text"].tolist()], args.batch_size):
                enc = tok(batch, return_tensors="pt", padding=True,
                          truncation=True, max_length=128).to(args.device)
                with autocast_ctx:
                    out = model.generate(**enc, forced_bos_token_id=bos,
                                         max_new_tokens=args.max_new_tokens, num_beams=args.num_beams)
                preds.extend(tok.batch_decode(out, skip_special_tokens=True))
        return preds

    return generate


# ------------------------------------------------------------------------- main
def main() -> None:
    args = parse_args()
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    from peft import PeftModel
    from sacrebleu import corpus_bleu, corpus_chrf

    # 1) Jeu d'évaluation
    if args.source == "flores":
        df = build_flores(args.flores_split)
    else:
        df = build_local(args.local_test, args.min_cos)
    df = add_nllb_codes(df)

    # 2) Modèle : base chargé une fois, enrobé par l'adaptateur LoRA
    print(f"Chargement du tokenizer ({args.adapter}) et du modèle de base ({args.base})…")
    tok = AutoTokenizer.from_pretrained(args.adapter)
    base = AutoModelForSeq2SeqLM.from_pretrained(args.base)
    model = PeftModel.from_pretrained(base, args.adapter).to(args.device).eval()
    # On pilote la longueur via max_new_tokens uniquement (supprime le warning).
    try:
        model.generation_config.max_length = None
    except Exception:
        pass
    use_bf16 = args.device == "cuda" and torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    generate = make_generator(model, tok, args, use_bf16)

    # 3) Évaluation par direction
    reports, examples = [], []
    for (src_lang, tgt_lang), group in df.groupby(["src_lang", "tgt_lang"], sort=True):
        if args.max_per_direction:
            group = group.sample(n=min(args.max_per_direction, len(group)), random_state=42)
        group = group.reset_index(drop=True)
        refs = group["tgt_text"].astype(str).tolist()

        base_preds = generate(group, use_adapter=False)
        lora_preds = generate(group, use_adapter=True)

        b_bleu = corpus_bleu(base_preds, [refs]).score
        l_bleu = corpus_bleu(lora_preds, [refs]).score
        b_chrf = corpus_chrf(base_preds, [refs]).score
        l_chrf = corpus_chrf(lora_preds, [refs]).score
        reports.append({
            "direction": f"{src_lang}->{tgt_lang}", "rows": len(group),
            "base_bleu": round(b_bleu, 2), "lora_bleu": round(l_bleu, 2),
            "d_bleu": round(l_bleu - b_bleu, 2),
            "base_chrf": round(b_chrf, 2), "lora_chrf": round(l_chrf, 2),
            "d_chrf": round(l_chrf - b_chrf, 2),
        })
        print(f"  {src_lang}->{tgt_lang}: BLEU {b_bleu:5.2f} -> {l_bleu:5.2f} "
              f"({l_bleu-b_bleu:+5.2f}) | chrF {b_chrf:5.2f} -> {l_chrf:5.2f} ({l_chrf-b_chrf:+5.2f})")
        for i in range(min(args.examples, len(group))):
            examples.append({
                "direction": f"{src_lang}->{tgt_lang}", "src_text": group.loc[i, "src_text"],
                "reference": refs[i], "base": base_preds[i], "lora": lora_preds[i],
            })

    # 4) Sorties
    rep = pd.DataFrame(reports)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    rep.to_csv(out, index=False, encoding="utf-8")
    pd.DataFrame(examples).to_csv(out.with_suffix(".examples.csv"), index=False, encoding="utf-8")

    avg = {
        "direction": "MOYENNE", "rows": int(rep["rows"].sum()),
        "base_bleu": round(rep["base_bleu"].mean(), 2), "lora_bleu": round(rep["lora_bleu"].mean(), 2),
        "d_bleu": round(rep["d_bleu"].mean(), 2),
        "base_chrf": round(rep["base_chrf"].mean(), 2), "lora_chrf": round(rep["lora_chrf"].mean(), 2),
        "d_chrf": round(rep["d_chrf"].mean(), 2),
    }
    rep_show = pd.concat([rep, pd.DataFrame([avg])], ignore_index=True)
    print("\n=== NLLB base vs LoRA (" + (f"FLORES {args.flores_split}" if args.source == "flores"
          else f"local, cos>={args.min_cos}") + ") ===")
    print(rep_show.to_string(index=False))
    print(f"\nRapport: {out}\nExemples: {out.with_suffix('.examples.csv')}")


if __name__ == "__main__":
    main()