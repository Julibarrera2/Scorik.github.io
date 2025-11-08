FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common curl ca-certificates gnupg \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.9 python3.9-venv python3-pip \
    musescore3 \
    ffmpeg libsndfile1 \
    xvfb fontconfig fonts-dejavu-core fonts-freefont-ttf \
    libfreetype6 libxrender1 libxext6 libsm6 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.9 /usr/bin/python && ln -sf /usr/bin/pip3 /usr/bin/pip

# Wrapper headless para MuseScore
RUN printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -e' \
    'bin=$(command -v mscore3 || command -v mscore)' \
    'exec xvfb-run -a "$bin" "$@"' \
    > /usr/local/bin/mscore3-cli \
    && chmod +x /usr/local/bin/mscore3-cli

WORKDIR /app

# ---------- Deps APP ----------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ---------- venv aislado para Spleeter ----------
COPY requirements-spleeter.txt .
RUN python3.9 -m venv /opt/spleenv \
    && /opt/spleenv/bin/pip install --no-cache-dir -r requirements-spleeter.txt
ENV SPLEETER_BIN=/opt/spleenv/bin/spleeter

# ---------- Código ----------
COPY . .

ENV FFMPEG_BINARY=ffmpeg \
    MUSESCORE_PATH=/usr/local/bin/mscore3-cli \
    PORT=8080

EXPOSE 8080
CMD ["sh", "-c", "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app --timeout 0"]
