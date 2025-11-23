FROM python:3.10-bookworm

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
    ca-certificates \
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

# COPIAR REQUIREMENTS
COPY requirements.txt .

# Instalar dependencias (incluye PyTorch CPU)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ====== COPIAR CÓDIGO ======
COPY . .
COPY models /app/models


ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app --timeout 0"]
