# ===========================================
# GUITARRA – CloudRun SAFE
# Solo detecta notas y genera notas_detectadas.json
# NO genera PNG, NO llama MuseScore, NO reconstruye audio
# ===========================================

import librosa
import soundfile as sf
import crepe
import numpy as np
import os
from pydub import AudioSegment
from pydub.utils import which
from typing import List, Tuple, Dict
import json
import warnings
import sys
import scipy.signal
from scipy.signal import windows
from pydub.utils import which
from pydub import AudioSegment
# ===========================
#   🔥 FIX PARA CLOUD RUN
#   Limitar TensorFlow / CREPE a 1 thread
# ===========================
import tensorflow as tf
tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.threading.set_inter_op_parallelism_threads(1)
os.environ["TF_NUM_INTEROP_THREADS"] = "1"
os.environ["TF_NUM_INTRAOP_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
# ===========================

# ---- FIX librosa / scipy ----
if not hasattr(scipy.signal, "hann"):
    scipy.signal.hann = windows.hann

np.float = float
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---- FFmpeg para pydub (funciona en local y en Cloud Run) ----


FFMPEG_BIN = which("ffmpeg") or "ffmpeg"
FFPROBE_BIN = which("ffprobe") or "ffprobe"

AudioSegment.converter = FFMPEG_BIN
AudioSegment.ffprobe   = FFPROBE_BIN


# ---- Config GUITARRA ----
GTR_MIN_FREQ = 82.0
GTR_MAX_FREQ = 1400.0
CREPE_SR     = 16000
STEP_MS      = 5
CONF_THRESH  = 0.90
ENERGY_DB    = -55

def filtrar_pitch_por_energia(pitch_list, y_signal, sr_signal, threshold_db=ENERGY_DB):
    hop = int(sr_signal * 0.01)
    rms = librosa.feature.rms(y=y_signal, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr_signal, hop_length=hop)
    filtrados = []
    for t, f in pitch_list:
        idx = np.argmin(np.abs(times - t))
        if librosa.amplitude_to_db([rms[idx]], ref=np.max)[0] > threshold_db:
            filtrados.append((t, f))
    return filtrados

def load_and_preprocess_audio(filepath, sr=22050):
    y, sr = librosa.load(filepath, sr=sr, mono=True)
    return y, sr, filepath

def detect_pitch(y, sr, threshold=CONF_THRESH):
    if sr != CREPE_SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=CREPE_SR)
        sr = CREPE_SR
    if y.ndim == 1:
        y = np.expand_dims(y, axis=1)
    time, freq, conf, _ = crepe.predict(y, sr, step_size=STEP_MS, viterbi=True)
    return [(t, f) for t, f, c in zip(time, freq, conf)
            if c >= threshold and GTR_MIN_FREQ <= f <= GTR_MAX_FREQ]

notas_dict = {  # igual que siempre
    'C0': 16.35, 'C#0': 17.32, 'D0': 18.35, 'D#0': 19.45, 'E0': 20.60, 'F0': 21.83,
    'F#0': 23.12, 'G0': 24.50, 'G#0': 25.96, 'A0': 27.50, 'A#0': 29.14, 'B0': 30.87,
    'C1': 32.70, 'C#1': 34.65, 'D1': 36.71, 'D#1': 38.89, 'E1': 41.20, 'F1': 43.65,
    'F#1': 46.25, 'G1': 49.00, 'G#1': 51.91, 'A1': 55.00, 'A#1': 58.27, 'B1': 61.74,
    'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78, 'E2': 82.41, 'F2': 87.31,
    'F#2': 92.50, 'G2': 98.00, 'G#2': 103.83, 'A2': 110.00, 'A#2': 116.54, 'B2': 123.47,
    'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'E3': 164.81, 'F3': 174.61,
    'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00, 'A#3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63, 'F4': 349.23,
    'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
}

def group_pitches_to_notes(pitch_data, tempo, notas_dict):
    def freq_to_note(f):
        return min(notas_dict.items(), key=lambda x: abs(x[1] - f))[0]

    notas = []
    if not pitch_data:
        return []

    inicio = pitch_data[0][0]
    freq_a = pitch_data[0][1]
    nota_a = freq_to_note(freq_a)

    for t, f in pitch_data[1:]:
        if abs(12 * np.log2(f/freq_a)) > 0.6:
            dur = t - inicio
            if dur >= 0.06:
                negra = 60 / tempo
                if dur < negra*0.6: fig = "corchea"
                elif dur < negra*1.2: fig = "negra"
                elif dur < negra*2.2: fig = "blanca"
                else: fig = "redonda"
                compas = int(inicio / (negra*4)) + 1
                notas.append({
                    "instrumento": "guitarra",
                    "nota": nota_a,
                    "inicio": round(inicio,3),
                    "duracion": round(dur,3),
                    "compas": compas,
                    "figura": fig,
                    "tempo": int(tempo)
                })
            inicio = t
            freq_a = f
            nota_a = freq_to_note(f)
        else:
            freq_a = (freq_a + f)/2

    dur = pitch_data[-1][0] - inicio
    if dur >= 0.06:
        negra = 60 / tempo
        if dur < negra*0.6: fig = "corchea"
        elif dur < negra*1.2: fig = "negra"
        elif dur < negra*2.2: fig = "blanca"
        else: fig = "redonda"
        compas = int(inicio/(negra*4)) + 1
        notas.append({
            "instrumento": "guitarra",
            "nota": nota_a,
            "inicio": round(inicio,3),
            "duracion": round(dur,3),
            "compas": compas,
            "figura": fig,
            "tempo": int(tempo)
        })

    return notas

def write_json(notas, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "notas_detectadas.json"), "w") as f:
        json.dump(notas, f, indent=2)

def main(filepath, carpeta_destino):
    y, sr, filepath = load_and_preprocess_audio(filepath)
    pitches = detect_pitch(y, sr)
    pitches = filtrar_pitch_por_energia(pitches, y, sr)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if tempo == 0 or np.isnan(tempo):
        tempo = 120

    notas = group_pitches_to_notes(pitches, tempo, notas_dict)
    write_json(notas, carpeta_destino)

if __name__ == "__main__":
    filepath = sys.argv[1]
    carpeta = sys.argv[2]
    main(filepath, carpeta)
