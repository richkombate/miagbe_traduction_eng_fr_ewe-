# Fine-tuning NLLB avec LoRA

Modele cible: `facebook/nllb-200-distilled-600M`.

## 1. Sources non religieuses

La commande recommandee OPUS exclut les corpus bibliques:

```powershell
.\.venv\Scripts\python.exe scripts\download_opus_parallel.py --source recommended
```

Pour completer la paire anglais-ewe, importez le corpus Ghana NLP:

```powershell
.\.venv\Scripts\python.exe scripts\import_hf_parallel_dataset.py `
  --dataset ghananlpcommunity/english-ewe-sentence-pairs-4m `
  --src-column English `
  --tgt-column Ewe `
  --src-lang eng `
  --tgt-lang ewe `
  --min-quality 0.80 `
  --max-rows 500000 `
  --output data/processed/hf/ghana_en_ewe.csv
```

## 2. Dataset final NLLB

Chaque ligne est directionnelle. Une paire `fra -> ewe` et sa version inverse
`ewe -> fra` sont deux lignes distinctes.

Colonnes produites:

```text
id,split,src_lang,tgt_lang,src_lang_nllb,tgt_lang_nllb,src_text,tgt_text,source,domain,quality_score,is_religious,license
```

Preparation sans corpus religieux:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_nllb_training_data.py `
  --inputs data/processed/opus/*.csv data/processed/hf/*.csv `
  --output-dir data/processed/nllb `
  --max-per-direction 120000
```

Le script ecrit:

```text
data/processed/nllb/nllb_train.csv
data/processed/nllb/nllb_valid.csv
data/processed/nllb/nllb_test.csv
data/processed/nllb/nllb_summary.csv
```

## 3. Lancement LoRA (notebook)

L'entraînement se fait désormais **exclusivement dans le notebook unique**
`notebooks/01_pipeline_nllb_lora.ipynb`, qui couvre tout le pipeline (corpus,
GPU, tokenisation, fine-tuning LoRA, courbes de perte, évaluation BLEU/chrF,
démo). Les anciens scripts d'entraînement ont été retirés au profit du notebook.

Ouvrez-le avec le kernel `.venv` :

```powershell
jupyter notebook notebooks/01_pipeline_nllb_lora.ipynb
```

Réglages principaux dans la cellule de configuration :

- `MODE = "smoke"` pour une vérification rapide, `MODE = "full"` pour un vrai
  entraînement ;
- `REQUIRE_CUDA = True` pour éviter de lancer par erreur sur CPU ;
- `OUTPUT_DIR = models/nllb-ewe-lora` pour la sortie de l'adapter.

## 4. Utiliser l'adapter dans l'API

Evaluation rapide apres entrainement:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_nllb_model.py `
  --test data/processed/nllb/nllb_test.csv `
  --adapter models/nllb-ewe-lora `
  --max-per-direction 200 `
  --output models/evaluation_report.csv
```

Le script produit un tableau BLEU/chrF par direction et un fichier
`models/evaluation_report.examples.csv` avec quelques predictions.

## 5. Utiliser l'adapter dans l'API

Apres entrainement, configurez `.env`:

```env
TRANSLATION_BACKEND=nllb
MODEL_NAME=facebook/nllb-200-distilled-600M
ADAPTER_PATH=models/nllb-ewe-lora
DEVICE=cuda
```

Puis relancez l'API.

## 6. Controle du biais religieux

La preparation exclut les lignes `is_religious=true` par defaut. Si vous voulez
faire une experience separee avec BibleNLP ou bible-uedin, gardez le plafond a
0-5 % maximum et comparez les sorties avec le modele non religieux.
