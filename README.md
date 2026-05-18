# Traducteur multilingue Français – Anglais – Ewe avec reconnaissance vocale

Projet universitaire de Master : traduction automatique multilingue avec module vocal, centré sur une langue africaine peu dotée en ressources numériques : l'ewe.

## Objectif

Construire une démonstration complète capable de :

- traduire du texte entre français, anglais et ewe ;
- exposer une API FastAPI propre ;
- proposer une interface React/Vite ;
- intégrer une architecture prête pour NLLB-200 + LoRA ;
- préparer le pipeline STT/TTS ;
- évaluer les traductions avec BLEU, chrF et WER/CER ;
- fournir une base de rapport académique et de soutenance.

## Architecture retenue

```text
Frontend React/Vite
      |
      v
API FastAPI (/translate, /transcribe, /synthesize, /health)
      |
      +--> NLP: normalisation Unicode + moteur NLLB optionnel + fallback local
      +--> Audio: STT/TTS optionnels
      +--> Évaluation: BLEU, chrF, WER, CER
```

Le projet fonctionne en mode démonstration sans télécharger de gros modèles. Si un modèle Hugging Face est disponible localement, le backend peut basculer vers NLLB.

## Installation rapide

```bash
cd traducteur-fr-en-ewe
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
uvicorn traducteur.api.main:app --reload --app-dir src
```

API : <http://127.0.0.1:8000/docs>

## Lancer le frontend

```bash
cd frontend
npm install
npm run dev
```

## Démonstration API

```bash
curl -X POST http://127.0.0.1:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour mon ami", "source_lang":"fra", "target_lang":"eng"}'
```

## Variables d'environnement utiles

Créez un fichier `.env` à la racine si nécessaire :

```env
TRANSLATION_BACKEND=fallback
MODEL_NAME=facebook/nllb-200-distilled-600M
DEVICE=cpu
ENABLE_STT=false
ENABLE_TTS=false
```

Valeurs possibles :

- `TRANSLATION_BACKEND=fallback` : démonstration légère sans modèle ;
- `TRANSLATION_BACKEND=nllb` : utilise Transformers si le modèle est installé/téléchargé ;
- `DEVICE=cpu` ou `cuda`.

## Structure

```text
src/traducteur/
├── api/          # FastAPI
├── nlp/          # traduction, normalisation, configuration des langues
├── audio/        # STT/TTS optionnels
├── data/         # ingestion/nettoyage/splitting
└── evaluation/   # métriques
frontend/         # interface React/Vite
scripts/          # commandes de préparation et d'entraînement
report/           # squelette LaTeX du rapport
notebooks/        # notebooks de démonstration
```

## Limites assumées

- Le fallback local n'est pas un vrai modèle de traduction ; il sert à rendre la démonstration exécutable même sans GPU.
- Pour une vraie performance scientifique, il faut fine-tuner `facebook/nllb-200-distilled-600M` avec LoRA sur un corpus parallèle nettoyé.
- Le module vocal ewe dépend fortement des données audio disponibles et doit être présenté comme preuve de concept si le corpus reste limité.

## Prochaines étapes scientifiques

1. Constituer le corpus parallèle : FLORES-200, JW300/OPUS, Bible parallèle, sources locales validées.
2. Nettoyer les textes avec normalisation Unicode NFC.
3. Fine-tuner NLLB-200 distilled 600M avec PEFT/LoRA.
4. Évaluer sur FLORES devtest : BLEU, chrF++, analyse qualitative.
5. Ajouter STT avec Whisper pour fr/en et MMS/Whisper adapté pour ewe.
