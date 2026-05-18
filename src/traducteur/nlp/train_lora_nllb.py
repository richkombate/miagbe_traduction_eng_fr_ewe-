"""Fine-tune NLLB-200 distilled 600M with LoRA.

Example:
python scripts/train_lora_nllb.py ^
  --train data/processed/nllb/nllb_train.csv ^
  --valid data/processed/nllb/nllb_valid.csv ^
  --output models/nllb-ewe-lora
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import torch
from datasets import Dataset

from traducteur.nlp.languages import nllb_code


REQUIRED_COLUMNS = {"src_lang", "tgt_lang", "src_text", "tgt_text"}


def read_training_csv(path: str | Path, max_samples: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")

    df = df.copy()
    df["src_text"] = df["src_text"].fillna("").astype(str).str.strip()
    df["tgt_text"] = df["tgt_text"].fillna("").astype(str).str.strip()
    df = df[(df["src_text"].str.len() > 0) & (df["tgt_text"].str.len() > 0)]

    if "src_lang_nllb" not in df.columns:
        df["src_lang_nllb"] = df["src_lang"].map(nllb_code)
    if "tgt_lang_nllb" not in df.columns:
        df["tgt_lang_nllb"] = df["tgt_lang"].map(nllb_code)

    if max_samples:
        df = df.sample(n=min(max_samples, len(df)), random_state=42)
    return df.reset_index(drop=True)


def make_preprocess_fn(tokenizer, max_source_length: int, max_target_length: int):
    def preprocess(example: dict) -> dict:
        tokenizer.src_lang = example["src_lang_nllb"]
        tokenizer.tgt_lang = example["tgt_lang_nllb"]
        model_inputs = tokenizer(
            example["src_text"],
            max_length=max_source_length,
            truncation=True,
        )
        labels = tokenizer(
            text_target=example["tgt_text"],
            max_length=max_target_length,
            truncation=True,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    return preprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune facebook/nllb-200-distilled-600M with LoRA.")
    parser.add_argument("--train", required=True, help="Training CSV prepared for NLLB.")
    parser.add_argument("--valid", required=True, help="Validation CSV prepared for NLLB.")
    parser.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    parser.add_argument("--output", default="models/nllb-ewe-lora")
    parser.add_argument("--max-source-length", type=int, default=128)
    parser.add_argument("--max-target-length", type=int, default=128)
    parser.add_argument("--train-batch-size", type=int, default=2)
    parser.add_argument("--eval-batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--eval-steps", type=int, default=500)
    parser.add_argument("--save-steps", type=int, default=500)
    parser.add_argument("--logging-steps", type=int, default=50)
    parser.add_argument("--max-train-samples", type=int, default=None)
    parser.add_argument("--max-valid-samples", type=int, default=None)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--resume-from-checkpoint", default=None)
    parser.add_argument("--no-fp16", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
    )

    train_df = read_training_csv(args.train, max_samples=args.max_train_samples)
    valid_df = read_training_csv(args.valid, max_samples=args.max_valid_samples)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)

    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    peft_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "v_proj"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    preprocess = make_preprocess_fn(
        tokenizer=tokenizer,
        max_source_length=args.max_source_length,
        max_target_length=args.max_target_length,
    )
    train_ds = Dataset.from_pandas(train_df, preserve_index=False).map(
        preprocess,
        remove_columns=train_df.columns.tolist(),
        desc="Tokenizing train",
    )
    valid_ds = Dataset.from_pandas(valid_df, preserve_index=False).map(
        preprocess,
        remove_columns=valid_df.columns.tolist(),
        desc="Tokenizing valid",
    )

    use_fp16 = torch.cuda.is_available() and not args.no_fp16
    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.train_batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.epochs,
        warmup_ratio=args.warmup_ratio,
        fp16=use_fp16,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_steps=args.save_steps,
        logging_steps=args.logging_steps,
        save_total_limit=3,
        predict_with_generate=False,
        report_to="none",
        load_best_model_at_end=False,
    )
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        processing_class=tokenizer,
        data_collator=collator,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    trainer.save_model(output_path)
    tokenizer.save_pretrained(output_path)
    print(f"Saved LoRA adapter and tokenizer to {output_path}")


if __name__ == "__main__":
    main()
