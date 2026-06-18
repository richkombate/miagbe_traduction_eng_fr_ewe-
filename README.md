# MiaGbe — Traducteur français, anglais et éwé

> **Projet de groupe — GR02** · Master 1 IA-BD EPL S2 (Informatique et Gestion de données)
>
> | Membre                           |
> |----------------------------------|
> | AZIGLOSSOU Judith Gracia         |
> | NAPO NISSAO Rafia                |
> | WOGLO Koffi Boris Gilbride       |
> | PIO Sikirou Afeez Prince Cyrille |
> | KOMBATE Gountande                |
>
> Sujet : *Traducteur Multilingue (Français, Anglais, Éwé) avec Reconnaissance Vocale* — proposé par Mme GBEDEVI.

MiaGbe traduit dans les **six directions** entre le français, l'anglais et l'éwé, avec
reconnaissance et synthèse vocales. Le projet réunit :

- une **API FastAPI** pour la traduction, la transcription et la synthèse ;
- une interface **React + Vite** ;
- un pipeline de données parallèles (notebook `00_donnees.ipynb`) ;
- le fine-tuning **LoRA** de `facebook/nllb-200-distilled-600M` (notebooks `01` et `02`) ;
- l'historique synchronisé et l'authentification Google optionnelle.

## 1. Prérequis

- Python 3.11 (recommandé) et Git.
- Node.js LTS (`npm`) pour le frontend.
- Pour l'entraînement : un GPU NVIDIA avec PyTorch CUDA (≥ 8 Go VRAM).

## 2. Installation Python

```powershell
cd D:\python\traducteur-fr-en-ewe
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

PyTorch CUDA (adapter le canal à votre version CUDA, voir <https://pytorch.org/get-started/locally/>) :

```powershell
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## 3. Configuration du backend

Copiez `.env.example` en `.env` :

```env
TRANSLATION_BACKEND=nllb
MODEL_NAME=facebook/nllb-200-distilled-600M
DEVICE=cuda
ENABLE_STT=false
ENABLE_TTS=false
ADAPTER_PATH=models/nllb-ewe-lora
```

- `TRANSLATION_BACKEND=nllb` : charge NLLB-200 + l'adaptateur LoRA éwé (mode recommandé).
- `TRANSLATION_BACKEND=fallback` : mini-dictionnaire de démo, pour tester l'interface sans charger le modèle.
- `ADAPTER_PATH=models/nllb-ewe-lora` : adaptateur final pour l'inférence (pas les `checkpoint-*`).

Si le modèle ne peut pas être chargé en mode `nllb`, l'API retombe automatiquement sur
le dictionnaire de démo et signale un `warning` dans la réponse. Au premier lancement,
le modèle est téléchargé depuis Hugging Face s'il n'est pas en cache.

## 4. Lancer l'API

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn traducteur.api.main:app --app-dir src
```

- API : <http://127.0.0.1:8000> · Swagger : <http://127.0.0.1:8000/docs> · Santé : `/health`

Test rapide :

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/translate `
  -ContentType "application/json" `
  -Body '{"text":"Je vais bien.","source_lang":"fra","target_lang":"ewe"}'
```

Endpoints : `/translate`, `/transcribe`, `/synthesize`, `/history`.

## 5. Lancer le frontend (React + Vite)

```powershell
cd frontend
npm install
npm run dev
```

Frontend : <http://127.0.0.1:5173>. Pour pointer vers une autre API, créez `frontend/.env.local` :

```env
VITE_API_URL=http://127.0.0.1:8000
```

## 6. Reconnaissance et synthèse vocales

La chaîne vocale couvre les trois langues **côté serveur** ; le navigateur enregistre en
WAV (décodé par `librosa`, sans `ffmpeg`).

- **STT** (`POST /transcribe`, `ENABLE_STT=true`) : Whisper (OpenAI) pour le français et
  l'anglais, **MMS-ASR** (Meta, Wav2Vec2) pour l'éwé.
- **TTS** (`POST /synthesize`, `ENABLE_TTS=true`) : **MMS-TTS** (VITS) pour les trois
  langues — seule voix éwé disponible.

Les modèles sont préchargés au démarrage et mis en cache.

## 7. Connexion Google et historique

L'historique et les favoris sont persistés côté serveur (SQLite `data/history.db`) et
rattachés au compte connecté : un même utilisateur les retrouve depuis n'importe quel
navigateur. Sans connexion, repli sur un cache local.

Pour activer la connexion Google, créez un client OAuth 2.0 (application Web) avec les
origines `http://localhost:5173` et `http://127.0.0.1:5173`, puis :

```env
# frontend/.env.local
VITE_GOOGLE_CLIENT_ID=votre-client-id.apps.googleusercontent.com
VITE_API_URL=http://127.0.0.1:8000
```

```env
# .env (backend, pour vérifier les jetons)
GOOGLE_CLIENT_ID=votre-client-id.apps.googleusercontent.com
```

## 8. Données et corpus

Toute la construction du corpus est dans le notebook **`notebooks/00_donnees.ipynb`**
(unique source de vérité). `data/processed/` n'est pas versionné : après un clone,
exécuter le notebook de haut en bas régénère les données.

Étapes : collecte (OPUS, google/SMOL, FLORES dev, MAFAND) → alignement cosinus (encodeur
NLLB) → filtrage par identification de langue (fastText) → filtre caractères éwé →
durcissement du seuil → filtres anti-bruit, déduplication, plafond du domaine religieux,
bidirectionnalisation et découpage déterministe (pas de fuite train/test).

Sorties dans `data/processed/nllb/` : `nllb_train.csv`, `nllb_valid.csv`, `nllb_test.csv`,
`nllb_summary.csv`.

## 9. Fine-tuning et back-translation

- **`notebooks/01_pipeline_nllb_lora.ipynb`** : fine-tuning LoRA de NLLB-200 sur les six
  directions, suivi des pertes, évaluation BLEU/chrF (section 9) et comparaison
  base vs adaptateur sur FLORES-200 (section 10). `MODE = "smoke"` pour un test rapide,
  `"full"` pour l'entraînement complet ; sortie dans `models/nllb-ewe-lora`.
- **`notebooks/02_backtranslation_nllb_lora.ipynb`** : génère des paires synthétiques
  `en→ewe` (à partir des paires `ewe-fr` propres, éwé humain gardé en cible), ré-entraîne
  un adaptateur dans un dossier séparé `models/nllb-ewe-lora-bt`, puis compare au modèle
  de base. On adopte la back-translation si elle gagne sur `en↔ewe` sans régresser
  ailleurs.

> Ordre de bout en bout : `00_donnees` → entraînement sur `nllb_train.csv` →
> back-translation (génère `nllb_train_aug.csv`) → ré-entraînement sur le train augmenté.

## 10. Tests

```powershell
pytest -q              # backend
cd frontend; npm run build   # frontend
```

## 11. Structure du projet

```text
src/traducteur/
  api/          # FastAPI, schémas, routes
  nlp/          # traduction, normalisation, langues
  audio/        # STT (Whisper + MMS) et TTS (MMS-TTS)
  data/         # ingestion / nettoyage / découpage
  evaluation/   # métriques
frontend/       # interface React + Vite
notebooks/      # 00 données · 01 pipeline NLLB+LoRA · 02 back-translation
report/         # rapport LaTeX et figures
models/         # adaptateurs, checkpoints, rapports
data/           # données brutes et traitées
tests/          # tests backend
```

## 12. Dépannage

- **L'API ne démarre pas** : `.venv` activé ? Lancée depuis la racine avec `--app-dir src` ?
  `requirements.txt` installé ?
- **Erreur de traduction côté frontend** : démarrer l'API d'abord, vérifier `VITE_API_URL`,
  relancer `npm run dev` après modification de `.env.local`.