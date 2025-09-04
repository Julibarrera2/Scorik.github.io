# ---------- Base Ubuntu ----------
FROM ubuntu:22.04

# Evita prompts de apt
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Paquetes base + PPA para Python 3.9
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common curl ca-certificates gnupg \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.9 python3.9-venv python3-pip \
    # MuseScore 3 desde APT (más simple y estable que AppImage)
    musescore3 \
    # Audio/GUI headless
    ffmpeg libsndfile1 \
    xvfb fontconfig fonts-dejavu-core fonts-freefont-ttf \
    # libs X/Qt que MuseScore suele necesitar
    libfreetype6 libxrender1 libxext6 libsm6 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Aliases por comodidad
RUN ln -sf /usr/bin/python3.9 /usr/bin/python && ln -sf /usr/bin/pip3 /usr/bin/pip

# Wrapper headless para MuseScore bajo Xvfb
RUN printf '%s\n' \
            '#!/usr/bin/env bash' \
            'set -e' \
            'bin=$(command -v mscore3 || command -v mscore)' \
            'exec xvfb-run -a "$bin" "$@"' \
    > /usr/local/bin/mscore3-cli \
    && chmod +x /usr/local/bin/mscore3-cli

WORKDIR /app

# ---------- Python deps ----------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Código ----------
COPY . .

# Carpetas que usa tu app
RUN mkdir -p uploads static/temp partituras_usuario progress

# Env que usa tu código
ENV FFMPEG_BINARY=ffmpeg \
    MUSESCORE_PATH=/usr/local/bin/mscore3-cli \
    PORT=8080

EXPOSE 8080

# Servidor de producción
CMD ["sh", "-c", "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app --timeout 0"]