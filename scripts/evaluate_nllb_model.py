from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd
import torch


def chunks(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an NLLB base model or LoRA adapter.")
    parser.add_argument("--test", default="data/processed/nllb/nllb_test.csv")
    parser.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--output", default="models/evaluation_report.csv")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-per-direction", type=int, default=200)
    parser.add_argument("--max-source-length", type=int, default=128)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def load_model(model_name: str, adapter_path: str | None, device: str):
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    if adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_path)
    model.to(device)
    model.eval()
    return tokenizer, model


def generate_predictions(
    tokenizer,
    model,
    rows: pd.DataFrame,
    batch_size: int,
    max_source_length: int,
    max_new_tokens: int,
    device: str,
) -> list[str]:
    predictions: list[str] = []
    tokenizer.src_lang = rows.iloc[0]["src_lang_nllb"]
    forced_bos_token_id = tokenizer.convert_tokens_to_ids(rows.iloc[0]["tgt_lang_nllb"])

    texts = rows["src_text"].tolist()
    with torch.no_grad():
        for batch in chunks(texts, batch_size):
            encoded = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_source_length,
            ).to(device)
            generated = model.generate(
                **encoded,
                forced_bos_token_id=forced_bos_token_id,
                max_new_tokens=max_new_tokens,
                num_beams=4,
            )
            predictions.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
    return predictions


def main() -> None:
    args = parse_args()
    from sacrebleu import corpus_bleu, corpus_chrf

    df = pd.read_csv(args.test)
    tokenizer, model = load_model(args.model, args.adapter, args.device)

    reports = []
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    examples_path = output_path.with_suffix(".examples.csv")

    with examples_path.open("w", newline="", encoding="utf-8") as examples_file:
        examples_writer = csv.DictWriter(
            examples_file,
            fieldnames=["src_lang", "tgt_lang", "src_text", "reference", "prediction"],
        )
        examples_writer.writeheader()

        for (src_lang, tgt_lang), group in df.groupby(["src_lang", "tgt_lang"], sort=True):
            if args.max_per_direction:
                group = group.sample(n=min(args.max_per_direction, len(group)), random_state=42)
            group = group.reset_index(drop=True)
            predictions = generate_predictions(
                tokenizer=tokenizer,
                model=model,
                rows=group,
                batch_size=args.batch_size,
                max_source_length=args.max_source_length,
                max_new_tokens=args.max_new_tokens,
                device=args.device,
            )
            references = group["tgt_text"].tolist()
            bleu = corpus_bleu(predictions, [references]).score
            chrf = corpus_chrf(predictions, [references]).score
            reports.append(
                {
                    "src_lang": src_lang,
                    "tgt_lang": tgt_lang,
                    "rows": len(group),
                    "bleu": round(float(bleu), 4),
                    "chrf": round(float(chrf), 4),
                }
            )
            for _, row in group.head(25).iterrows():
                examples_writer.writerow(
                    {
                        "src_lang": src_lang,
                        "tgt_lang": tgt_lang,
                        "src_text": row["src_text"],
                        "reference": row["tgt_text"],
                        "prediction": predictions[row.name],
                    }
                )

    pd.DataFrame(reports).to_csv(output_path, index=False)
    print(pd.DataFrame(reports).to_string(index=False))
    print(f"Wrote {output_path} and {examples_path}")


if __name__ == "__main__":
    main()
