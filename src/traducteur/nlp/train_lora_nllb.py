"""Squelette de fine-tuning NLLB + LoRA.

Exécution indicative :
python -m traducteur.nlp.train_lora_nllb --train data/processed/train.csv --valid data/processed/valid.csv
"""
from __future__ import annotations

import argparse
import pandas as pd
from datasets import Dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--valid", required=True)
    parser.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    parser.add_argument("--output", default="models/nllb-ewe-lora")
    parser.add_argument("--max-length", type=int, default=128)
    args = parser.parse_args()

    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Seq2SeqTrainer, Seq2SeqTrainingArguments, DataCollatorForSeq2Seq
    from peft import LoraConfig, get_peft_model, TaskType
    from traducteur.nlp.languages import nllb_code

    train_df = pd.read_csv(args.train)
    valid_df = pd.read_csv(args.valid)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)

    peft_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
    )
    model = get_peft_model(model, peft_config)

    def preprocess(batch):
        tokenizer.src_lang = nllb_code(batch["src_lang"])
        model_inputs = tokenizer(batch["src_text"], max_length=args.max_length, truncation=True)
        labels = tokenizer(text_target=batch["tgt_text"], max_length=args.max_length, truncation=True)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    train_ds = Dataset.from_pandas(train_df).map(preprocess, remove_columns=train_df.columns.tolist())
    valid_ds = Dataset.from_pandas(valid_df).map(preprocess, remove_columns=valid_df.columns.tolist())

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output,
        learning_rate=2e-4,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=8,
        num_train_epochs=3,
        fp16=True,
        evaluation_strategy="steps",
        eval_steps=500,
        save_steps=500,
        logging_steps=50,
        predict_with_generate=True,
        report_to="none",
    )
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        tokenizer=tokenizer,
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)


if __name__ == "__main__":
    main()
