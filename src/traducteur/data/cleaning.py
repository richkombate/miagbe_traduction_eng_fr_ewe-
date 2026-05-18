from __future__ import annotations

import unicodedata
import re
import pandas as pd


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def clean_text(text: str) -> str:
    text = normalize_unicode(text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_parallel_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required = {"src_text", "tgt_text", "src_lang", "tgt_lang"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes: {missing}")
    df = df.copy()
    df["src_text"] = df["src_text"].map(clean_text)
    df["tgt_text"] = df["tgt_text"].map(clean_text)
    df = df[(df["src_text"].str.len() > 0) & (df["tgt_text"].str.len() > 0)]
    df = df.drop_duplicates(subset=["src_lang", "tgt_lang", "src_text", "tgt_text"])
    return df.reset_index(drop=True)
