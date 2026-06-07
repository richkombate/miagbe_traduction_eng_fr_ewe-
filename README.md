# MiaGbe - Traducteur français, anglais et éwé

> **Projet de groupe — GR02** · Master 1 IA-BD EPL S2 (Informatique et Gestion de données)
>
> | Membre |
> |--------|
> | AZIGLOSSOU Judith Gracia |
> | NAPO NISSAO Rafia |
> | WOGLO Koffi Boris Gilbride |
> | PIO Sikirou Afeez Prince Cyrille |
> | KOMBATE Gountande |
>
> Sujet : *Traducteur Multilingue (Français, Anglais, Éwé) avec Reconnaissance Vocale*
> — proposé par Mme GBEDEVI.

MiaGbe est une plateforme de traduction multilingue français, anglais et éwé,
développée dans le cadre d'un projet universitaire togolais. Le projet combine :

- une API FastAPI pour la traduction ;
- une interface React/Vite inspirée d'un outil de traduction moderne ;
- un pipeline de données parallèles français/anglais/éwé ;
- un notebook unique pour le fine-tuning LoRA de `facebook/nllb-200-distilled-600M` ;
- une architecture prête pour l'authentification Google et l'historique utilisateur.

Le projet peut tourner en mode démo léger avec un fallback local, ou en mode
modèle NLLB/LoRA avec GPU NVIDIA.

## 1. Prérequis machine

### Obligatoires

- Python 3.10 ou plus récent, Python 3.11 recommandé.
- Git.
- Node.js LTS avec `npm` pour le frontend React.
- Un terminal PowerShell sous Windows, ou un shell équivalent sous Linux/macOS.

### Recommandés pour l'entraînement

- GPU NVIDIA avec pilotes à jour.
- PyTorch installé avec CUDA.
- Au moins 8 Go de VRAM pour des essais LoRA modestes ; plus si le corpus est volumineux.

Sur la machine de développement utilisée ici, la configuration GPU validée est :

```text
torch: 2.11.0+cu128
CUDA PyTorch: 12.8
GPU: NVIDIA GeForce RTX 5080 Laptop GPU
```

Le NPU Intel AI Boost et le GPU Intel intégré peuvent apparaître dans le
Gestionnaire des tâches Windows, mais l'entraînement PyTorch/Transformers de ce
projet utilise le GPU NVIDIA via CUDA. Le NPU n'est pas exploité par ce pipeline.

## 2. Installation Python

Depuis la racine du projet :

```powershell
cd D:\python\traducteur-fr-en-ewe
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si vous utilisez `uv`, vous pouvez remplacer la dernière commande par :

```powershell
uv pip install -r requirements.txt
```

### Installer PyTorch GPU

Si l'entraînement détecte le CPU au lieu du GPU, réinstallez PyTorch avec le
wheel CUDA adapté à votre carte. Pour une machine CUDA 12.8 / RTX récente :

```powershell
python -m pip uninstall -y torch torchvision torchaudio
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

Pour une autre version CUDA, choisissez la commande officielle sur
<https://pytorch.org/get-started/locally/>.

Vérification :

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Le résultat attendu pour entraîner sur GPU est :

```text
True
NVIDIA ...
```

Si `torch.cuda.is_available()` vaut `False`, vérifiez le pilote NVIDIA, la
version de PyTorch installée et le fait que l'environnement `.venv` actif est le
bon.

## 3. Configuration du backend

Copiez `.env.example` en `.env` à la racine du projet (ou adaptez le `.env`
existant) :

```env
TRANSLATION_BACKEND=nllb
MODEL_NAME=facebook/nllb-200-distilled-600M
DEVICE=cuda
ENABLE_STT=false
ENABLE_TTS=false
ADAPTER_PATH=models/nllb-ewe-lora
```

Modes utiles :

- `TRANSLATION_BACKEND=nllb` : **mode recommandé**, charge le modèle NLLB-200 et
  l'adapter LoRA éwé pour de vraies traductions neuronales.
- `TRANSLATION_BACKEND=fallback` : mode démo léger (mini-dictionnaire), sans
  charger NLLB. Utile pour tester l'interface sans GPU ni téléchargement.
- `DEVICE=cuda` : utilise le GPU NVIDIA si PyTorch CUDA est disponible.
- `DEVICE=cpu` : compatible partout, mais lent pour NLLB.
- `ADAPTER_PATH=models/nllb-ewe-lora` : charge l'adapter LoRA final sauvegardé.

**Robustesse** : en mode `nllb`, si le modèle ne peut pas être chargé (pas de
GPU, mémoire insuffisante, modèle absent…), l'API ne plante pas : elle retombe
automatiquement sur le dictionnaire de démonstration et signale un avertissement
dans la réponse (`warning`). L'API reste donc toujours opérationnelle.

Au premier lancement en mode `nllb`, Transformers peut télécharger le modèle
depuis Hugging Face si le cache local ne le contient pas encore. Prévoyez une
connexion Internet et de l'espace disque, ou remplacez `MODEL_NAME` par un
chemin local contenant le modèle.

Pour l'API d'inférence, utilisez de préférence le dossier final
`models/nllb-ewe-lora`. Les sous-dossiers `checkpoint-*` servent surtout à
reprendre l'entraînement ou tester un checkpoint précis.

## 4. Lancer l'API FastAPI

Lancez cette commande depuis la racine du projet :

```powershell
.\.venv\Scripts\Activate.ps1
 uvicorn traducteur.api.main:app --app-dir src
```

URLs utiles :

- API : <http://127.0.0.1:8000>
- Documentation Swagger : <http://127.0.0.1:8000/docs>
- Santé du service : <http://127.0.0.1:8000/health>

Test rapide :

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/translate `
  -ContentType "application/json" `
  -Body '{"text":"Je vais bien.","source_lang":"fra","target_lang":"ewe"}'
```

Si vous êtes déjà dans le dossier `src`, lancez plutôt :

```powershell
uvicorn traducteur.api.main:app --reload
```

## 5. Lancer le frontend React

Dans un second terminal :

```powershell
cd D:\python\traducteur-fr-en-ewe\frontend
npm install
npm run dev
```

Frontend : <http://127.0.0.1:5173>

Le frontend appelle par défaut l'API sur `http://127.0.0.1:8000`. Si l'API est
sur une autre adresse, créez `frontend/.env.local` :

```env
VITE_API_URL=http://127.0.0.1:8000
```

Pour vérifier la compilation frontend :

```powershell
npm run build
```

Si `npm` n'est pas reconnu sous Windows, installez Node.js LTS, fermez puis
rouvrez PowerShell, puis vérifiez :

```powershell
node -v
npm -v
```

## 5b. Reconnaissance vocale (STT) et synthèse vocale (TTS)

L'interface intègre la reconnaissance vocale demandée dans le cahier des charges :

- **Dicter** (bouton micro du panneau source) : utilise l'API Web Speech du
  navigateur (Chrome/Edge) pour le français et l'anglais. Le texte reconnu
  remplit la zone de saisie et la traduction se lance automatiquement.
- **Écouter** (bouton haut-parleur du panneau cible) : lit la traduction à voix
  haute via la synthèse vocale du navigateur (français, anglais).
- L'éwé n'étant pas couvert par les moteurs vocaux des navigateurs, les boutons
  vocaux n'apparaissent que pour les langues supportées.

Pour une transcription **côté serveur** (modèle Whisper d'OpenAI, utile pour des
fichiers audio ou un meilleur contrôle), activez dans `.env` :

```env
ENABLE_STT=true
```

L'endpoint `POST /transcribe` (multipart, champ `file`, paramètre `lang`)
chargera alors `openai/whisper-base` à la première requête. Cela nécessite
`librosa`/`soundfile` (déjà dans `requirements.txt`) et, pour les formats
compressés comme webm/opus, `ffmpeg` installé sur la machine.

## 6. Connexion Google

L'interface prévoit une connexion Google pour associer l'historique et les
favoris à l'utilisateur. Tant que Google n'est pas configuré, le bouton visible
sert de point d'entrée mais ne connecte pas encore un vrai compte.

Pour l'activer :

1. Créez un projet dans Google Cloud Console.
2. Configurez un client OAuth 2.0 de type application Web.
3. Ajoutez les origines JavaScript autorisées :
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
4. Créez `frontend/.env.local` :

```env
VITE_GOOGLE_CLIENT_ID=votre-client-id.apps.googleusercontent.com
VITE_API_URL=http://127.0.0.1:8000
```

5. Redémarrez `npm run dev`.

Pour que le serveur **vérifie** les jetons d'identité Google, renseignez le même
identifiant côté backend dans `.env` :

```env
GOOGLE_CLIENT_ID=votre-client-id.apps.googleusercontent.com
```

## 6b. Historique synchronisé entre navigateurs

L'historique et les favoris sont **persistés côté serveur** (base SQLite
`data/history.db`), rattachés au compte de l'utilisateur connecté. Un même
utilisateur retrouve donc ses traductions depuis n'importe quel navigateur ou
machine — le stockage local du navigateur ne sert plus que de cache hors-ligne.

- Endpoints : `GET /history` et `PUT /history` (corps `{ "entries": [...] }`).
- Identité : jeton Google vérifié via l'en-tête `Authorization: Bearer` si
  `GOOGLE_CLIENT_ID` est configuré ; sinon repli sur l'en-tête `X-User-Id`
  (mode démo non vérifié, pratique pour tester sans configurer Google).
- Si le serveur est injoignable, l'interface bascule en cache local et affiche
  un indicateur « Hors ligne ».

## 7. Données et corpus

Les données de travail sont organisées comme suit :

```text
data/
  raw/                 # archives ou données brutes
  processed/opus/      # CSV extraits depuis OPUS
  processed/hf/        # imports Hugging Face
  processed/nllb/      # train/valid/test finaux pour NLLB
  SOURCES.md           # sources documentées et remarques qualité
```

Format canonique attendu pour les corpus parallèles :

```text
id,src_lang,tgt_lang,src_text,tgt_text,source
```

Format final pour le fine-tuning NLLB :

```text
id,split,src_lang,tgt_lang,src_lang_nllb,tgt_lang_nllb,src_text,tgt_text,source,domain,quality_score,is_religious,license
```

Le projet évite de biaiser le modèle vers le domaine religieux. Les corpus Bible
doivent rester séparés ou limités fortement. Voir `data/SOURCES.md` pour les
sources, volumes, limites et recommandations.

### Repréparer le dataset NLLB

Exemple avec les fichiers déjà convertis dans `data/processed/opus` et
`data/processed/hf` :

```powershell
python scripts/prepare_nllb_training_data.py `
  --inputs data/processed/opus/*.csv data/processed/hf/*.csv `
  --output-dir data/processed/nllb `
  --max-per-direction 120000
```

Sorties attendues :

```text
data/processed/nllb/nllb_train.csv
data/processed/nllb/nllb_valid.csv
data/processed/nllb/nllb_test.csv
data/processed/nllb/nllb_summary.csv
```

## 8. Notebook unique de fine-tuning

Le pipeline notebook est regroupé dans :

```text
notebooks/01_pipeline_nllb_lora.ipynb
```

Il couvre :

- exploration du corpus ;
- vérification GPU ;
- préparation train/valid/test ;
- fine-tuning LoRA de NLLB ;
- suivi des pertes ;
- évaluation BLEU/chrF ;
- démonstration de traduction.

Installez les dépendances notebook si besoin :

```powershell
python -m pip install notebook ipykernel matplotlib
python -m ipykernel install --user --name traducteur-fr-en-ewe --display-name "Python (traducteur-fr-en-ewe)"
```

Ouvrez ensuite :

```powershell
jupyter notebook notebooks/01_pipeline_nllb_lora.ipynb
```

Dans le notebook :

- `MODE = "smoke"` pour un test rapide ;
- `MODE = "full"` pour un vrai entraînement ;
- `REQUIRE_CUDA = True` pour éviter de lancer par erreur sur CPU ;
- `OUTPUT_DIR = models/nllb-ewe-lora`.

Un entraînement complet peut prendre longtemps car NLLB-200 distilled 600M reste
un modèle lourd, même avec LoRA. Le temps dépend surtout du volume du corpus, de
la longueur maximale des séquences, du batch size et du nombre d'epochs.

## 9. Évaluation

Évaluation d'un adapter LoRA :

```powershell
python scripts/evaluate_nllb_model.py `
  --test data/processed/nllb/nllb_test.csv `
  --model facebook/nllb-200-distilled-600M `
  --adapter models/nllb-ewe-lora `
  --output models/nllb-ewe-lora/evaluation_report.csv `
  --device cuda
```

## 10. Tests et contrôles rapides

Backend :

```powershell
pytest -q
```

Frontend :

```powershell
cd frontend
npm run build
```

Vérification GPU :

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## 11. Docker

Le Dockerfile fourni lance l'API en mode serveur. Le `docker-compose.yml`
configure par défaut le backend en mode `fallback` et `DEVICE=cpu`.

```powershell
docker compose up --build
```

Pour utiliser CUDA dans Docker, il faut installer NVIDIA Container Toolkit et
adapter le compose. Le flux recommandé pour l'entraînement reste le notebook
local dans `.venv`.

## 12. Structure du projet

```text
src/traducteur/
  api/          # FastAPI, schemas, routes
  nlp/          # traduction, normalisation, langues
  audio/        # STT/TTS optionnels
  data/         # ingestion/nettoyage/splitting
  evaluation/   # métriques
frontend/       # interface React/Vite MiaGbe
scripts/        # préparation corpus et évaluation (l'entraînement est dans le notebook)
notebooks/      # notebook unique NLLB LoRA (pipeline complet de fine-tuning)
models/         # adapters, checkpoints, rapports
data/           # données brutes et traitées
tests/          # tests backend
```

## 13. Dépannage

### L'API ne démarre pas

- Vérifiez que le `.venv` est activé.
- Lancez `uvicorn` depuis la racine avec `--app-dir src`.
- Vérifiez que `requirements.txt` est installé.

### Le frontend affiche une erreur de traduction

- Démarrez d'abord l'API sur `http://127.0.0.1:8000`.
- Vérifiez `VITE_API_URL` dans `frontend/.env.local`.
- Redémarrez `npm run dev` après modification du `.env.local`.

### L'entraînement part sur CPU

- Vérifiez `torch.cuda.is_available()`.
- Réinstallez PyTorch avec le wheel CUDA adapté.
- Mettez `REQUIRE_CUDA = True` dans le notebook pour bloquer l'entraînement CPU.
- Dans `.env`, utilisez `DEVICE=cuda` pour l'inférence backend.

### Le Gestionnaire des tâches montre plusieurs GPU

Sur un laptop hybride, Windows peut afficher :

- `GPU 0` : Intel Graphics ;
- `GPU 1` : NVIDIA GeForce RTX.

Pour ce projet, la source fiable est PyTorch :

```powershell
python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Si cette commande affiche NVIDIA, l'entraînement utilise bien le GPU CUDA.
