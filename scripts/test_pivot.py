"""Test rapide : traduction directe vs pivot, pour la direction faible fra->ewe.

Charge l'adaptateur LoRA entraine et compare, sur quelques phrases du quotidien :
  - direct   : fra -> ewe
  - pivot EN : fra -> eng -> ewe
Objectif : voir si passer par l'anglais corrige l'off-target (sortie en anglais).
Tourne sur CPU par defaut pour ne pas entrer en conflit avec le kernel Jupyter.
"""
from __future__ import annotations

import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

BASE = "facebook/nllb-200-distilled-600M"
ADAPTER = "models/nllb-ewe-lora"
NLLB = {"fra": "fra_Latn", "eng": "eng_Latn", "ewe": "ewe_Latn"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(ADAPTER)
    model = AutoModelForSeq2SeqLM.from_pretrained(BASE)
    model = PeftModel.from_pretrained(model, ADAPTER).to(args.device).eval()

    @torch.no_grad()
    def tr(text: str, src: str, tgt: str) -> str:
        tok.src_lang = NLLB[src]
        enc = tok(text, return_tensors="pt", truncation=True, max_length=128).to(args.device)
        out = model.generate(
            **enc,
            forced_bos_token_id=tok.convert_tokens_to_ids(NLLB[tgt]),
            max_new_tokens=128,
            num_beams=4,
        )
        return tok.batch_decode(out, skip_special_tokens=True)[0]

    phrases = [
        "Bonjour, comment vas-tu ?",
        "Je vais bien, merci.",
        "Quel est ton nom ?",
        "Demain je vais au marché.",
    ]
    for p in phrases:
        direct = tr(p, "fra", "ewe")
        en = tr(p, "fra", "eng")
        pivot = tr(en, "eng", "ewe")
        print("FR    :", p)
        print("  direct  fra->ewe :", direct)
        print("  pivot   fra->en  :", en)
        print("  pivot   en->ewe  :", pivot)
        print()


if __name__ == "__main__":
    main()
