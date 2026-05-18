from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


LANG_TO_NLLB = {
    "fra": "fra_Latn",
    "fr": "fra_Latn",
    "eng": "eng_Latn",
    "en": "eng_Latn",
    "ewe": "ewe_Latn",
    "ee": "ewe_Latn",
}

LANG_ALIASES = {
    "fr": "fra",
    "fra": "fra",
    "french": "fra",
    "en": "eng",
    "eng": "eng",
    "english": "eng",
    "ee": "ewe",
    "ewe": "ewe",
}

RELIGIOUS_MARKERS = ("bible", "biblenlp", "tanzil", "jw300", "quran")
DEFAULT_DOMAINS = {
    "nllb": "web-mined",
    "ted2020": "talks",
    "news-commentary": "news",
    "tatoeba": "daily",
    "wikimedia": "web",
    "translatewiki": "software",
    "europarl": "parliament",
    "bible-uedin": "religion",
}


def stable_id(*parts: object) -> str:
    joined = "\u241f".join(str(part) for part in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def canonical_lang(value: object) -> str:
    key = str(value or "").strip().lower()
    if key not in LANG_ALIASES:
        raise ValueError(f"Unsupported language code: {value}")
    return LANG_ALIASES[key]


def nllb_code(value: object) -> str:
    key = str(value or "").strip().lower()
    if key not in LANG_TO_NLLB:
        key = canonical_lang(key)
    return LANG_TO_NLLB[key]


def clean_text_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def infer_domain(source: str) -> str:
    source_lower = source.lower()
    for marker, domain in DEFAULT_DOMAINS.items():
        if marker in source_lower:
            return domain
    return "mixed"


def is_religious_source(source: str) -> bool:
    source_lower = source.lower()
    return any(marker in source_lower for marker in RELIGIOUS_MARKERS)


def load_canonical_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"src_lang", "tgt_lang", "src_text", "tgt_text", "source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")

    df = df.copy()
    df["src_lang"] = df["src_lang"].map(canonical_lang)
    df["tgt_lang"] = df["tgt_lang"].map(canonical_lang)
    df["src_text"] = clean_text_series(df["src_text"])
    df["tgt_text"] = clean_text_series(df["tgt_text"])
    df["source"] = df["source"].fillna(path.stem).astype(str)
    if "domain" not in df.columns:
        df["domain"] = df["source"].map(infer_domain)
    if "quality_score" not in df.columns:
        df["quality_score"] = 1.0
    if "is_religious" not in df.columns:
        df["is_religious"] = df["source"].map(is_religious_source)
    if "license" not in df.columns:
        df["license"] = ""
    return df


def filter_rows(df: pd.DataFrame, min_chars: int, max_chars: int, max_ratio: float) -> pd.DataFrame:
    df = df.copy()
    src_len = df["src_text"].str.len()
    tgt_len = df["tgt_text"].str.len()
    shorter = pd.concat([src_len, tgt_len], axis=1).min(axis=1).clip(lower=1)
    longer = pd.concat([src_len, tgt_len], axis=1).max(axis=1)
    ratio = longer / shorter

    df = df[
        (src_len >= min_chars)
        & (tgt_len >= min_chars)
        & (src_len <= max_chars)
        & (tgt_len <= max_chars)
        & (ratio <= max_ratio)
    ]
    return df.drop_duplicates(subset=["src_lang", "tgt_lang", "src_text", "tgt_text"])


def make_directional(df: pd.DataFrame, bidirectional: bool) -> pd.DataFrame:
    forward = df.copy()
    if not bidirectional:
        return forward

    reverse = df.copy()
    reverse = reverse.rename(
        columns={
            "src_lang": "tgt_lang",
            "tgt_lang": "src_lang",
            "src_text": "tgt_text",
            "tgt_text": "src_text",
        }
    )
    return pd.concat([forward, reverse], ignore_index=True)


def cap_per_direction(df: pd.DataFrame, max_per_direction: int, seed: int) -> pd.DataFrame:
    if max_per_direction <= 0:
        return df
    capped = []
    for _, group in df.groupby(["src_lang", "tgt_lang"], sort=False):
        if len(group) > max_per_direction:
            group = group.sample(n=max_per_direction, random_state=seed)
        capped.append(group)
    return pd.concat(capped, ignore_index=True)


def assign_splits(df: pd.DataFrame, valid_ratio: float, test_ratio: float) -> pd.DataFrame:
    if valid_ratio <= 0 or test_ratio <= 0 or valid_ratio + test_ratio >= 1:
        raise ValueError("Split ratios must be > 0 and sum to less than 1.")

    def split_for_row(row: pd.Series) -> str:
        key = stable_id(row["src_lang"], row["tgt_lang"], row["src_text"], row["tgt_text"])
        bucket = int(key[:8], 16) / 0xFFFFFFFF
        if bucket < test_ratio:
            return "test"
        if bucket < test_ratio + valid_ratio:
            return "valid"
        return "train"

    df = df.copy()
    df["split"] = df.apply(split_for_row, axis=1)
    return df


def prepare_dataset(
    input_paths: list[Path],
    output_dir: Path,
    bidirectional: bool,
    include_religious: bool,
    max_religious_fraction: float,
    max_per_direction: int,
    min_chars: int,
    max_chars: int,
    max_ratio: float,
    valid_ratio: float,
    test_ratio: float,
    seed: int,
) -> pd.DataFrame:
    frames = [load_canonical_csv(path) for path in input_paths]
    if not frames:
        raise ValueError("No input files provided.")

    df = pd.concat(frames, ignore_index=True)
    df = filter_rows(df, min_chars=min_chars, max_chars=max_chars, max_ratio=max_ratio)

    if not include_religious:
        df = df[~df["is_religious"].astype(bool)]

    df = make_directional(df, bidirectional=bidirectional)
    if include_religious and max_religious_fraction >= 0:
        non_religious = df[~df["is_religious"].astype(bool)]
        religious = df[df["is_religious"].astype(bool)]
        max_religious = int(len(non_religious) * max_religious_fraction)
        if len(religious) > max_religious:
            religious = religious.sample(n=max_religious, random_state=seed)
        df = pd.concat([non_religious, religious], ignore_index=True)

    df = cap_per_direction(df, max_per_direction=max_per_direction, seed=seed)
    df = assign_splits(df, valid_ratio=valid_ratio, test_ratio=test_ratio)
    df["src_lang_nllb"] = df["src_lang"].map(nllb_code)
    df["tgt_lang_nllb"] = df["tgt_lang"].map(nllb_code)
    df["id"] = df.apply(
        lambda row: stable_id(row["split"], row["src_lang"], row["tgt_lang"], row["src_text"], row["tgt_text"]),
        axis=1,
    )

    columns = [
        "id",
        "split",
        "src_lang",
        "tgt_lang",
        "src_lang_nllb",
        "tgt_lang_nllb",
        "src_text",
        "tgt_text",
        "source",
        "domain",
        "quality_score",
        "is_religious",
        "license",
    ]
    df = df[columns].sort_values(["split", "src_lang", "tgt_lang", "source"]).reset_index(drop=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "nllb_all.csv", index=False)
    for split, split_df in df.groupby("split"):
        split_df.to_csv(output_dir / f"nllb_{split}.csv", index=False)

    summary = (
        df.groupby(["split", "src_lang", "tgt_lang", "domain", "is_religious"])
        .size()
        .reset_index(name="rows")
        .sort_values(["split", "src_lang", "tgt_lang", "domain"])
    )
    summary.to_csv(output_dir / "nllb_summary.csv", index=False)
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a balanced NLLB fine-tuning dataset.")
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=["data/processed/opus/*.csv"],
        help="CSV files or glob patterns in canonical parallel format.",
    )
    parser.add_argument("--output-dir", default="data/processed/nllb")
    parser.add_argument("--no-bidirectional", action="store_true")
    parser.add_argument("--include-religious", action="store_true")
    parser.add_argument("--max-religious-fraction", type=float, default=0.05)
    parser.add_argument("--max-per-direction", type=int, default=120000)
    parser.add_argument("--min-chars", type=int, default=2)
    parser.add_argument("--max-chars", type=int, default=512)
    parser.add_argument("--max-ratio", type=float, default=3.0)
    parser.add_argument("--valid-ratio", type=float, default=0.02)
    parser.add_argument("--test-ratio", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def expand_inputs(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(Path().glob(pattern))
        if matches:
            paths.extend(matches)
            continue
        path = Path(pattern)
        if path.exists():
            paths.append(path)
    unique_paths = sorted({path.resolve() for path in paths})
    if not unique_paths:
        raise FileNotFoundError(f"No input CSV files matched: {patterns}")
    return unique_paths


def main() -> None:
    args = parse_args()
    input_paths = expand_inputs(args.inputs)
    df = prepare_dataset(
        input_paths=input_paths,
        output_dir=Path(args.output_dir),
        bidirectional=not args.no_bidirectional,
        include_religious=args.include_religious,
        max_religious_fraction=args.max_religious_fraction,
        max_per_direction=args.max_per_direction,
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        max_ratio=args.max_ratio,
        valid_ratio=args.valid_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    print(f"Wrote {len(df)} rows to {args.output_dir}")
    print(df.groupby(["split", "src_lang", "tgt_lang"]).size().to_string())


if __name__ == "__main__":
    main()
