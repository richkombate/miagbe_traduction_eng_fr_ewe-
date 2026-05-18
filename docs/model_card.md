# Model Card

## Modele cible

`facebook/nllb-200-distilled-600M` + adaptation LoRA.

## Usage prevu

Traduction academique et demonstrative entre francais, anglais et ewe.

## Limites

- Qualite dependante du volume et de la validation des donnees ewe.
- Risque de biais de domaine.
- Les corpus religieux doivent rester exclus ou plafonnes pour eviter un style biblique.
- Mauvaise gestion possible des tons et diacritiques si les donnees sont mal normalisees.
