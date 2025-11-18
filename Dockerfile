FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ====== SISTEMA ======
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    musescore3 \
    libsndfile1 \
    xvfb \
    fontconfig \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ====== WRAPPER PARA MUSESCORE ======
RUN printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -e' \
    'bin=$(command -v mscore3 || command -v mscore)' \
    'exec xvfb-run -a "$bin" "$@"' \
    > /usr/local/bin/mscore3-cli \
    && chmod +x /usr/local/bin/mscore3-cli

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ====== COPIAR CÓDIGO ======
COPY . .

# ====== DEMUCS v3 ======
RUN pip install --no-cache-dir demucs==3.0.6 && \
    mkdir -p /root/.cache/torch/hub/checkpoints && \
    mkdir -p /app/.cache/torch/hub/checkpoints && \
    curl -L --retry 5 --retry-delay 3 \
        -o /root/.cache/torch/hub/checkpoints/htdemucs.th \
        https://dl.fbaipublicfiles.com/demucs/v3.0.6/htdemucs.th && \
    test -s /root/.cache/torch/hub/checkpoints/htdemucs.th && \
    cp /root/.cache/torch/hub/checkpoints/htdemucs.th \
        /app/.cache/torch/hub/checkpoints/htdemucs.th

ENV TORCH_HOME=/app/.cache/torch
ENV DEMUCS_ONLY_HTDEMUCS=1
ENV FFMPEG_BINARY=ffmpeg
ENV MUSESCORE_PATH=/usr/local/bin/mscore3-cli
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app --timeout 0"]
