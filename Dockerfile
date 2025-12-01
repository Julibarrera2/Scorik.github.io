FROM python:3.10-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ====== SISTEMA ======
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    xvfb \
    xauth \
    libxrender1 \
    libxext6 \
    libsm6 \
    libfreetype6 \
    libfontconfig1 \
    libxkbcommon0 \
    libgl1-mesa-glx \
    libxcb-xinerama0 \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# ================================
# INSTALAR MUSESCORE 3.6.2 AppImage
# ================================
WORKDIR /opt
RUN wget https://github.com/musescore/MuseScore/releases/download/v3.6.2/MuseScore-3.6.2-x86_64.AppImage -O mscore.AppImage \
    && chmod +x mscore.AppImage

# Extraer AppImage (modo portable)
RUN ./mscore.AppImage --appimage-extract
RUN mv squashfs-root /opt/mscore3

# Wrapper para llamarlo como "mscore3"
RUN printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -e' \
    'export QT_QPA_PLATFORM=offscreen' \
    'exec xvfb-run -a /opt/mscore3/AppRun "$@"' \
    > /usr/local/bin/mscore3 \
    && chmod +x /usr/local/bin/mscore3
ENV APPIMAGE_EXTRACT_AND_RUN=1


WORKDIR /app

# COPIAR REQUIREMENTS
COPY requirements.txt .

# Instalar dependencias (incluye PyTorch CPU)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ====== COPIAR CÓDIGO ====
COPY models /app/models
COPY . /app

ENV PORT=8080
EXPOSE 8080
RUN echo "TEST MUSESCORE:" && /usr/local/bin/mscore3 -v || true

CMD ["sh", "-c", "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app --timeout 0"]
