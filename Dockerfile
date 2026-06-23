FROM python:3.12-slim

WORKDIR /app

# Dépendances système pour soundfile / librosa
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Torch CPU d'abord pour éviter de télécharger la version CUDA (~2 Go)
RUN pip install --no-cache-dir \
    "torch>=2.2" "torchaudio>=2.2" \
    --index-url https://download.pytorch.org/whl/cpu

# Reste des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source du package
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir -e . --no-deps

# Configuration par défaut (surchargeable via les Secrets du Space HF)
ENV TRANSLATION_BACKEND=nllb
ENV MODEL_NAME=facebook/nllb-200-distilled-600M
ENV ADAPTER_PATH=miagbe-traduction/nllb-ewe-lora-bt
ENV DEVICE=cpu
ENV ENABLE_STT=false
ENV ENABLE_TTS=false
ENV HISTORY_DB_PATH=/tmp/history.db
ENV MAX_INPUT_CHARS=2000

EXPOSE 7860

CMD ["uvicorn", "traducteur.api.main:app", "--host", "0.0.0.0", "--port", "7860"]