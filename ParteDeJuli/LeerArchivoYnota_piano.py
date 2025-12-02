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
import subprocess
import sys
import scipy.signal
from scipy.signal import windows

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


# --------------------------
# FILTRO ENERGÍA
# --------------------------
def filtrar_pitch_por_energia(pitch_list, y_signal, sr_signal, threshold_db=-60):
    hop = int(sr_signal * 0.01)
    rms = librosa.feature.rms(y=y_signal, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr_signal, hop_length=hop)

    filtrados = []
    for t, f in pitch_list:
        idx = np.argmin(np.abs(times - t))
        if librosa.amplitude_to_db([rms[idx]], ref=np.max)[0] > threshold_db:
            filtrados.append((t, f))
    return filtrados

# --------------------------
# CARGA AUDIO
# --------------------------
def load_and_preprocess_audio(filepath: str, sr: int = 22050) -> Tuple[np.ndarray, int, str]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
    sr = int(sr)
    y, sr = librosa.load(filepath, sr=sr)
    print("Audio cargado correctamente.")
    return y, sr, filepath

# --------------------------
# DETECT PITCH
# --------------------------
def detect_pitch(y: np.ndarray, sr: int, threshold=0.90):
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        sr = 16000

    if y.ndim == 1:
        y = np.expand_dims(y, axis=1)

    time, frequency, confidence, _ = crepe.predict(
        y, sr, step_size=10, viterbi=True
    )

    return [(t, f) for t, f, c in zip(time, frequency, confidence)
            if c >= threshold and 30 < f < 4200]

# --------------------------
# DICCIONARIO NOTAS
# --------------------------
notas_dict = {
    'C0': 16.35, 'C#0': 17.32, 'D0': 18.35, 'D#0': 19.45, 'E0': 20.60, 'F0': 21.83, 'F#0': 23.12, 
    'G0': 24.50, 'G#0': 25.96, 'A0': 27.50, 'A#0': 29.14, 'B0': 30.87, 'C1': 32.70, 'C#1': 34.65, 
    'D1': 36.71, 'D#1': 38.89, 'E1': 41.20, 'F1': 43.65, 'F#1': 46.25, 'G1': 49.00, 'G#1': 51.91, 
    'A1': 55.00, 'A#1': 58.27, 'B1': 61.74, 'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78, 
    'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'G2': 98.00, 'G#2': 103.83, 'A2': 110.00, 'A#2': 116.54, 
    'B2': 123.47, 'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'E3': 164.81, 'F3': 174.61, 
    'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00, 'A#3': 233.08, 'B3': 246.94, 'C4': 261.63, 
    'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 
    'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88, 'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 
    'D#5': 622.25, 'E5': 659.25, 'F5': 698.46, 'F#5': 739.99, 'G5': 783.99, 'G#5': 830.61, 'A5': 880.00, 
    'A#5': 932.33, 'B5': 987.77, 'C6': 1046.50, 'C#6': 1108.73
}

# --------------------------
# AGRUPACIÓN NOTAS
# --------------------------
def group_pitches_to_notes(pitch_data, tempo, notas_dict):
    def frecuencia_a_nota(freq):
        return min(notas_dict.items(), key=lambda i: abs(i[1] - freq))[0]

    def figura(dur, tempo):
        negra = 60 / tempo
        if dur < negra * 0.6: return "corchea"
        if dur < negra * 1.2: return "negra"
        if dur < negra * 2.2: return "blanca"
        return "redonda"

    if not pitch_data:
        return []

    notas = []
    inicio = pitch_data[0][0]
    f_actual = pitch_data[0][1]
    n_actual = frecuencia_a_nota(f_actual)

    for t, f in pitch_data[1:]:
        if abs(12 * np.log2(f / f_actual)) > 0.3:
            dur = t - inicio
            if dur >= 0.08:
                notas.append({
                    "instrumento": "piano",
                    "nota": n_actual,
                    "inicio": round(inicio, 3),
                    "duracion": round(dur, 3),
                    "compas": int(inicio / (60/tempo*4)) + 1,
                    "figura": figura(dur, tempo),
                    "tempo": int(tempo)
                })
            inicio = t
            f_actual = f
            n_actual = frecuencia_a_nota(f)
        else:
            f_actual = (f_actual + f) / 2

    dur = pitch_data[-1][0] - inicio
    if dur >= 0.08:
        notas.append({
            "instrumento": "piano",
            "nota": n_actual,
            "inicio": round(inicio, 3),
            "duracion": round(dur, 3),
            "compas": int(inicio / (60/tempo*4)) + 1,
            "figura": figura(dur, tempo),
            "tempo": int(tempo)
        })

    return notas

# --------------------------
# JSON
# --------------------------
def write_notes_to_json(notas_json, carpeta_destino):
    os.makedirs(carpeta_destino, exist_ok=True)
    with open(os.path.join(carpeta_destino, "notas_detectadas.json"), "w") as f:
        json.dump(notas_json, f, indent=2)

# --------------------------
# SÍNTESIS PIANO
# --------------------------
def generate_note_wave_piano(freq, dur, sr=16000, volume=1.0):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = np.zeros_like(t)
    for k in range(1, 5):
        wave += (1/k) * np.sin(2*np.pi*freq*k*t)
    env = np.exp(-t / (dur * 0.4))
    env[: int(0.01*sr)] *= np.linspace(0, 1, int(0.01*sr))
    wave = wave * env
    wave /= np.max(np.abs(wave) + 1e-8)
    return (wave * volume).astype(np.float32)

# --------------------------
# MAIN
# --------------------------
def main(filepath, carpeta_destino="static/temp"):

    y, sr, filepath = load_and_preprocess_audio(filepath)

    pitches = detect_pitch(y, sr)
    pitches = filtrar_pitch_por_energia(pitches, y, sr)

    dur = librosa.get_duration(y=y, sr=sr)
    pitches = [p for p in pitches if p[0] < dur - 0.2]

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if tempo == 0:
        tempo = 120

    notas_json = group_pitches_to_notes(pitches, tempo, notas_dict)
    write_notes_to_json(notas_json, carpeta_destino)

    print("🎼 Piano: JSON generado, listo para MuseScore (worker).")
    return



if __name__ == "__main__":
    filepath = sys.argv[1]
    carpeta = sys.argv[2] if len(sys.argv) > 2 else "static/temp"
    main(filepath, carpeta)
