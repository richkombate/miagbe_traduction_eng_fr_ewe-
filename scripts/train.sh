#!/usr/bin/env bash
set -e
python -m traducteur.nlp.train_lora_nllb \
  --train data/processed/train.csv \
  --valid data/processed/valid.csv \
  --output models/nllb-ewe-lora
