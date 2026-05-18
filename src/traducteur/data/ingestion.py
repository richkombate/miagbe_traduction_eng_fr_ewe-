from __future__ import annotations

from pathlib import Path
import uuid
import pandas as pd


def read_parallel_csv(path: str | Path) -> pd.DataFrame:
    """Lit un CSV parallèle au format canonique.

    Colonnes attendues: src_lang,tgt_lang,src_text,tgt_text,source
    """
    df = pd.read_csv(path)
    if "id" not in df.columns:
        df.insert(0, "id", [str(uuid.uuid4()) for _ in range(len(df))])
    return df


def save_processed(df: pd.DataFrame, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    else:
        df.to_csv(output_path, index=False)
