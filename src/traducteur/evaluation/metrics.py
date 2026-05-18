from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class EvaluationReport:
    bleu: float | None
    chrf: float | None
    wer: float | None = None
    cer: float | None = None


def compute_bleu(predictions: Sequence[str], references: Sequence[str]) -> float:
    import sacrebleu
    return float(sacrebleu.corpus_bleu(list(predictions), [list(references)]).score)


def compute_chrf(predictions: Sequence[str], references: Sequence[str]) -> float:
    import sacrebleu
    return float(sacrebleu.corpus_chrf(list(predictions), [list(references)]).score)


def compute_wer(reference: str, hypothesis: str) -> float:
    from jiwer import wer
    return float(wer(reference, hypothesis))


def compute_cer(reference: str, hypothesis: str) -> float:
    from jiwer import cer
    return float(cer(reference, hypothesis))
