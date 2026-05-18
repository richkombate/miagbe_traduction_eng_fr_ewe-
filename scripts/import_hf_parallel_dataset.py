from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


def stable_id(*parts: object) -> str:
    joined = "\u241f".join(str(part) for part in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a Hugging Face parallel dataset to CSV.")
    parser.add_argument("--dataset", required=True, help="Hugging Face dataset id.")
    parser.add_argument("--split", default="train")
    parser.add_argument("--src-column", required=True)
    parser.add_argument("--tgt-column", required=True)
    parser.add_argument("--src-lang", required=True, choices=["eng", "fra", "ewe"])
    parser.add_argument("--tgt-lang", required=True, choices=["eng", "fra", "ewe"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-name", default=None)
    parser.add_argument("--quality-column", default="similarity")
    parser.add_argument("--min-quality", type=float, default=None)
    parser.add_argument("--max-rows", type=int, default=500000)
    parser.add_argument("--license", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from datasets import load_dataset

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_name = args.source_name or f"hf:{args.dataset}:{args.split}"

    dataset = load_dataset(args.dataset, split=args.split, streaming=True)
    count = 0
    skipped = 0

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=[
                "id",
                "src_lang",
                "tgt_lang",
                "src_text",
                "tgt_text",
                "source",
                "domain",
                "quality_score",
                "is_religious",
                "license",
            ],
        )
        writer.writeheader()

        for row in dataset:
            quality = row.get(args.quality_column, "")
            if args.min_quality is not None:
                try:
                    if float(quality) < args.min_quality:
                        skipped += 1
                        continue
                except (TypeError, ValueError):
                    skipped += 1
                    continue

            src_text = clean_text(row.get(args.src_column))
            tgt_text = clean_text(row.get(args.tgt_column))
            if not src_text or not tgt_text:
                skipped += 1
                continue

            writer.writerow(
                {
                    "id": stable_id(source_name, args.src_lang, args.tgt_lang, src_text, tgt_text),
                    "src_lang": args.src_lang,
                    "tgt_lang": args.tgt_lang,
                    "src_text": src_text,
                    "tgt_text": tgt_text,
                    "source": source_name,
                    "domain": "web-mined",
                    "quality_score": quality,
                    "is_religious": False,
                    "license": args.license,
                }
            )
            count += 1
            if args.max_rows and count >= args.max_rows:
                break

    print(f"Wrote {count} rows to {output_path}; skipped {skipped}")


if __name__ == "__main__":
    main()
