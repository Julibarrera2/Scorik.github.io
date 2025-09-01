# Python 3.9
FROM python:3.9-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Paquetes del sistema:
# - ffmpeg/libsndfile: pydub/soundfile
# - xvfb + fuentes: para correr MuseScore sin GUI
# - libs X/Qt comunes requeridas por el AppImage
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 \
    xvfb fontconfig fonts-dejavu-core fonts-freefont-ttf \
    libfreetype6 libxrender1 libxext6 libsm6 libglib2.0-0 \
    curl xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- MuseScore 3 (AppImage) ----
# Si el link cambia, usa cualquier AppImage 3.x desde GitHub de MuseScore
ENV MSCORE_URL=https://github.com/musescore/MuseScore/releases/download/v3.6.2/MuseScore-3.6.2.548021803-x86_64.AppImage
RUN curl -L $MSCORE_URL -o /tmp/mscore.AppImage && \
    chmod +x /tmp/mscore.AppImage && \
    /tmp/mscore.AppImage --appimage-extract && \
    mv squashfs-root /opt/musescore3 && \
    ln -s /opt/musescore3/AppRun /usr/local/bin/mscore3

# Wrapper headless para usar siempre xvfb-run
RUN printf '#!/bin/sh\nexec xvfb-run -a /usr/local/bin/mscore3 "$@"\n' > /usr/local/bin/mscore3-cli && \
    chmod +x /usr/local/bin/mscore3-cli

# ---- Python deps ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Directorios que usa tu app
RUN mkdir -p uploads static/temp partituras_usuario progress

# FFmpeg en PATH para pydub y MuseScore wrapper como valor por defecto
ENV FFMPEG_BINARY=ffmpeg
ENV MUSESCORE_PATH=/usr/local/bin/mscore3-cli
ENV PORT=8080

EXPOSE 8080

# Gunicorn para producción
CMD ["gunicorn", "-w", "2", "-k", "gthread", "-b", "0.0.0.0:8080", "app:app", "--timeout", "0"]
