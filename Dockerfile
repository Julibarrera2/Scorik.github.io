FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ========= DEPENDENCIAS DEL SISTEMA =========
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    musescore3 \
    libsndfile1 \
    xvfb \
    fontconfig \
    git \
    && rm -rf /var/lib/apt/lists/*

# ---------- WRAPPER HEADLESS PARA MUSESCORE ----------
RUN printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -e' \
    'bin=$(command -v mscore3 || command -v mscore)' \
    'exec xvfb-run -a "$bin" "$@"' \
    > /usr/local/bin/mscore3-cli \
    && chmod +x /usr/local/bin/mscore3-cli

# ========== DEPENDENCIAS PYTHON ==========
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ========= INSTALAR SOLO DEMUCS + MODELO Htdemucs =========
RUN pip install --no-cache-dir demucs==4.0.0 && \
    mkdir -p /root/.cache/torch/hub/checkpoints && \
    curl -L -o /root/.cache/torch/hub/checkpoints/htdemucs.th \
      https://dl.fbaipublicfiles.com/demucs/v4/htdemucs/htdemucs.th

# ========= BLOQUEAR DESCARGA DE MODELOS EXTRA =========
ENV DEMUCS_CACHE=/root/.cache/torch/hub/checkpoints
ENV DEMUCS_DISABLE_AUTO_DOWNLOAD=1
ENV TORCH_HOME=/root/.cache/torch

# ========= COPIAR CÓDIGO =========
COPY . .

# Variables de entorno
ENV FFMPEG_BINARY=ffmpeg
ENV MUSESCORE_PATH=/usr/local/bin/mscore3-cli
ENV PORT=8080

EXPOSE 8080

# Gunicorn para servir Flask en Cloud Run
CMD ["sh", "-c", "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app --timeout 0"]
