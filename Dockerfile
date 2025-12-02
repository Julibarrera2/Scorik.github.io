FROM python:3.10-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    xvfb \
    xauth \
    libfontconfig1 \
    libfreetype6 \
    libxrender1 \
    libxext6 \
    libsm6 \
    libxkbcommon0 \
    libxcb-xinerama0 \
    libnss3 \
    libnspr4 \
    libxss1 \
    libxtst6 \
    libxdamage1 \
    libxcomposite1 \
    libegl1 \
    libgbm1 \
    libgl1 \
    libgl1-mesa-glx \
    libglvnd0 \
    libasound2 \
    musescore3 \
    && rm -rf /var/lib/apt/lists/*

# MuseScore headless wrapper
RUN printf '%s\n' \
    '#!/usr/bin/env bash' \
    'xvfb-run -a musescore3 "$@"' \
    > /usr/local/bin/mscore3 && chmod +x /usr/local/bin/mscore3

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY models /app/models
COPY . /app

ENV PORT=8080
EXPOSE 8080

RUN echo "TEST MUSESCORE:" && mscore3 -v || true

CMD ["sh", "-c", "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app --timeout 0"]
