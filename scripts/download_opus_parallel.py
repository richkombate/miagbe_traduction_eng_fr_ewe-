from __future__ import annotations

import argparse
import csv
import io
import json
import re
import urllib.request
import uuid
import zipfile
from pathlib import Path


OPUS_SOURCES = {
    "bible_ee_en": {
        "url": "https://object.pouta.csc.fi/OPUS-bible-uedin/v1/moses/ee-en.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "eng",
        "source": "opus:bible-uedin:v1:ee-en",
        "expected_pairs": 16001,
    },
    "bible_ee_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-bible-uedin/v1/moses/ee-fr.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "fra",
        "source": "opus:bible-uedin:v1:ee-fr",
        "expected_pairs": 8004,
    },
    "nllb_ee_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-NLLB/v1/moses/ee-fr.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "fra",
        "source": "opus:nllb:v1:ee-fr",
        "expected_pairs": 1039385,
    },
    "ted2020_en_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-TED2020/v1/moses/en-fr.txt.zip",
        "src_lang": "eng",
        "tgt_lang": "fra",
        "source": "opus:ted2020:v1:en-fr",
        "expected_pairs": 410443,
    },
    "news_commentary_en_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-News-Commentary/v16/moses/en-fr.txt.zip",
        "src_lang": "eng",
        "tgt_lang": "fra",
        "source": "opus:news-commentary:v16:en-fr",
        "expected_pairs": 156122,
    },
    "tatoeba_en_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-Tatoeba/v2023-04-12/moses/en-fr.txt.zip",
        "src_lang": "eng",
        "tgt_lang": "fra",
        "source": "opus:tatoeba:v2023-04-12:en-fr",
        "expected_pairs": 275413,
    },
    "wikimedia_en_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-wikimedia/v20230407/moses/en-fr.txt.zip",
        "src_lang": "eng",
        "tgt_lang": "fra",
        "source": "opus:wikimedia:v20230407:en-fr",
        "expected_pairs": 1446495,
    },
    "europarl_en_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-Europarl/v8/moses/en-fr.txt.zip",
        "src_lang": "eng",
        "tgt_lang": "fra",
        "source": "opus:europarl:v8:en-fr",
        "expected_pairs": 2051014,
    },
    "qed_ee_en": {
        "url": "https://object.pouta.csc.fi/OPUS-QED/v2.0a/moses/ee-en.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "eng",
        "source": "opus:qed:v2.0a:ee-en",
        "expected_pairs": 284,
    },
    "qed_ee_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-QED/v2.0a/moses/ee-fr.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "fra",
        "source": "opus:qed:v2.0a:ee-fr",
        "expected_pairs": 166,
    },
    "tatoeba_ee_en": {
        "url": "https://object.pouta.csc.fi/OPUS-Tatoeba/v2023-04-12/moses/ee-en.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "eng",
        "source": "opus:tatoeba:v2023-04-12:ee-en",
        "expected_pairs": 6,
    },
    "wikimedia_ee_en": {
        "url": "https://object.pouta.csc.fi/OPUS-wikimedia/v20230407/moses/ee-en.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "eng",
        "source": "opus:wikimedia:v20230407:ee-en",
        "expected_pairs": 171,
    },
    "wikimedia_ee_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-wikimedia/v20230407/moses/ee-fr.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "fra",
        "source": "opus:wikimedia:v20230407:ee-fr",
        "expected_pairs": 45,
    },
    "translatewiki_ee_fr": {
        "url": "https://object.pouta.csc.fi/OPUS-translatewiki/v2025-01-01/moses/ee-fr.txt.zip",
        "src_lang": "ewe",
        "tgt_lang": "fra",
        "source": "opus:translatewiki:v2025-01-01:ee-fr",
        "expected_pairs": None,
    },
}

RECOMMENDED_SOURCE_KEYS = (
    "nllb_ee_fr",
    "translatewiki_ee_fr",
    "ted2020_en_fr",
    "news_commentary_en_fr",
    "tatoeba_en_fr",
)


def download(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        return
    with urllib.request.urlopen(url) as response:
        output_path.write_bytes(response.read())


def find_language_file(names: list[str], lang_code: str) -> str:
    escaped = re.escape(lang_code)
    candidates = [
        name
        for name in names
        if re.search(rf"\.{escaped}$", name) or re.search(rf"\.{escaped}\.txt$", name)
    ]
    if not candidates:
        raise ValueError(f"No file found for language code {lang_code}. Files: {names}")
    return sorted(candidates, key=len)[0]


def read_zip_lines(zip_path: Path, lang_code: str) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        file_name = find_language_file(names, lang_code)
        with archive.open(file_name) as file:
            wrapper = io.TextIOWrapper(file, encoding="utf-8", errors="replace")
            return [line.strip() for line in wrapper]


def write_parallel_csv(source_key: str, zip_path: Path, output_path: Path) -> int:
    config = OPUS_SOURCES[source_key]
    pair_match = re.search(r":([a-z]+)-([a-z]+)$", config["source"])
    if not pair_match:
        raise ValueError(f"Cannot infer OPUS pair from source: {config['source']}")

    opus_src_code, opus_tgt_code = pair_match.groups()
    src_lines = read_zip_lines(zip_path, opus_src_code)
    tgt_lines = read_zip_lines(zip_path, opus_tgt_code)

    if len(src_lines) != len(tgt_lines):
        raise ValueError(f"Line mismatch for {source_key}: {len(src_lines)} vs {len(tgt_lines)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["id", "src_lang", "tgt_lang", "src_text", "tgt_text", "source"],
        )
        writer.writeheader()
        count = 0
        for src_text, tgt_text in zip(src_lines, tgt_lines):
            if not src_text or not tgt_text:
                continue
            writer.writerow(
                {
                    "id": str(uuid.uuid4()),
                    "src_lang": config["src_lang"],
                    "tgt_lang": config["tgt_lang"],
                    "src_text": src_text,
                    "tgt_text": tgt_text,
                    "source": config["source"],
                }
            )
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Download OPUS Ewe parallel corpora.")
    parser.add_argument(
        "--source",
        choices=["recommended", "all", *OPUS_SOURCES.keys()],
        default="recommended",
        help="Corpus key to download and convert.",
    )
    parser.add_argument("--raw-dir", default="data/raw/opus", help="Raw ZIP output directory.")
    parser.add_argument(
        "--processed-dir",
        default="data/processed/opus",
        help="Canonical CSV output directory.",
    )
    parser.add_argument("--list", action="store_true", help="Print available sources as JSON.")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(OPUS_SOURCES, indent=2, ensure_ascii=False))
        return

    if args.source == "all":
        selected = OPUS_SOURCES.keys()
    elif args.source == "recommended":
        selected = RECOMMENDED_SOURCE_KEYS
    else:
        selected = [args.source]
    for source_key in selected:
        config = OPUS_SOURCES[source_key]
        zip_path = Path(args.raw_dir) / f"{source_key}.zip"
        csv_path = Path(args.processed_dir) / f"{source_key}.csv"

        print(f"Downloading {source_key}: {config['url']}")
        download(config["url"], zip_path)
        count = write_parallel_csv(source_key, zip_path, csv_path)
        expected = config["expected_pairs"]
        suffix = f" expected about {expected}" if expected else ""
        print(f"Wrote {count} rows to {csv_path}{suffix}")


if __name__ == "__main__":
    main()
