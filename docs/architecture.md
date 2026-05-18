# Architecture technique

Le système est organisé en trois couches : interface, API, services IA.

## Couche interface

React/Vite offre une interface plus professionnelle que Streamlit pour une soutenance. Streamlit peut rester un plan B si le temps devient critique.

## Couche API

FastAPI expose les routes :

- `GET /health`
- `POST /translate`
- `POST /transcribe`
- `POST /synthesize`

## Couche IA

Le choix scientifique principal est NLLB-200 distilled 600M avec fine-tuning LoRA. Le fallback local permet de faire tourner la démo même sans GPU.
