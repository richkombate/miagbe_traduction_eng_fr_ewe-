from pathlib import Path
import pandas as pd

rows = [
    {"src_lang":"fra","tgt_lang":"eng","src_text":"Bonjour mon ami","tgt_text":"Hello my friend","source":"sample"},
    {"src_lang":"eng","tgt_lang":"fra","src_text":"Thank you","tgt_text":"Merci","source":"sample"},
    {"src_lang":"fra","tgt_lang":"ewe","src_text":"Bonjour","tgt_text":"Ndi","source":"sample"},
]
out = Path("data/processed/sample_parallel.csv")
out.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)
print(f"Écrit: {out}")
