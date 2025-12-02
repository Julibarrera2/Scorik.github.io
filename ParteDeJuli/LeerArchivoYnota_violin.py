# Procesamiento de audio
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

def load_and_preprocess_audio(filepath: str, sr: int = 22050) -> Tuple[np.ndarray, int, str]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
    sr = int(sr)
    y, sr = librosa.load(filepath, sr=sr)
    print("Audio cargado correctamente.")
    return y, sr, filepath

def detect_pitch(y: np.ndarray, sr: int, threshold=0.85) -> List[Tuple[float, float]]:
    #ACA SE VE LA CANTIDAD DE FRAMES QUE SE VAN A ANALIZAR (10ms) para menor timepo y menor presicion cambiar
    step_size_ms=10
    print("Detectando notas...")
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        sr = 16000
    if len(y.shape) == 1:
        y = np.expand_dims(y, axis=1)
    time, frequency, confidence, _ = crepe.predict(y, sr, step_size=step_size_ms, viterbi=True)
    pitches_filtradas = []
    for t, f, c in zip(time, frequency, confidence):
        if c >= threshold and 30 < f < 1200:
            pitches_filtradas.append((t, f))
    print(f"Se detectaron {len(pitches_filtradas)} pitches con confianza > {threshold}.")
    return pitches_filtradas

notas_dict = {
    'C0': 16.35, 'C#0': 17.32, 'D0': 18.35, 'D#0': 19.45, 'E0': 20.60, 'F0': 21.83, 'F#0': 23.12, 'G0': 24.50,
    'G#0': 25.96, 'A0': 27.50, 'A#0': 29.14, 'B0': 30.87, 'C1': 32.70, 'C#1': 34.65, 'D1': 36.71, 'D#1': 38.89,
    'E1': 41.20, 'F1': 43.65, 'F#1': 46.25, 'G1': 49.00, 'G#1': 51.91, 'A1': 55.00, 'A#1': 58.27, 'B1': 61.74,
    'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78, 'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'G2': 98.00,
    'G#2': 103.83, 'A2': 110.00, 'A#2': 116.54, 'B2': 123.47, 'C3': 130.81, 'C#3': 138.59, 'D3': 146.83,
    'D#3': 155.56, 'E3': 164.81, 'F3': 174.61, 'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00,
    'A#3': 233.08, 'B3': 246.94, 'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63,
    'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25, 'E5': 659.25, 'F5': 698.46, 'F#5': 739.99,
    'G5': 783.99, 'G#5': 830.61, 'A5': 880.00, 'A#5': 932.33, 'B5': 987.77, 'C6': 1046.50, 'C#6': 1108.73
}

def group_pitches_to_notes(pitch_data: List[Tuple[float, float]], tempo: float, notas_dict: Dict[str, float]) -> List[Dict]:
    def frecuencia_a_nota(freq):
        return min(notas_dict.items(), key=lambda item: abs(item[1] - freq))[0]
    print("Primeros 20 valores de pitch_data (t, f):", pitch_data[:20])
    print("→ Cantidad de frames en pitch_data:", len(pitch_data))
    print("→ Primeros 10 frames:", pitch_data[:10])
    def calcular_figura_y_compas(duracion, tempo, inicio):
        negra_duracion = 60 / tempo
        if duracion < negra_duracion * 0.6:
            figura = "corchea"
        elif duracion < negra_duracion * 1.2:
            figura = "negra"
        elif duracion < negra_duracion * 2.2:
            figura = "blanca"
        else:
            figura = "redonda"
        compas = int(inicio / (negra_duracion * 4)) + 1
        return figura, compas

    MIN_DURACION_NOTA = 0.08
    NOTA_UMBRAL_VARIACION = 0.4

    def semitonos(f1, f2):
        return abs(12 * np.log2(f1 / f2))

    notas_json = []
    if pitch_data:
        inicio = pitch_data[0][0]
        freq_actual = pitch_data[0][1]
        nota_actual = frecuencia_a_nota(freq_actual)

        for t, f in pitch_data[1:]:
            if semitonos(f, freq_actual) > NOTA_UMBRAL_VARIACION:
                duracion = t - inicio
                if duracion >= MIN_DURACION_NOTA:
                    figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                    notas_json.append({
                        "nota": nota_actual,
                        "inicio": round(inicio, 3),
                        "duracion": round(duracion, 3),
                        "compas": compas,
                        "figura": figura,
                        "tempo": int(tempo)
                    })
                inicio = t
                freq_actual = f
                nota_actual = frecuencia_a_nota(f)
            else:
                freq_actual = (freq_actual + f) / 2

        duracion = pitch_data[-1][0] - inicio
        if duracion >= MIN_DURACION_NOTA:
            figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
            notas_json.append({
                "nota": nota_actual,
                "inicio": round(inicio, 3),
                "duracion": round(duracion, 3),
                "compas": compas,
                "figura": figura,
                "tempo": int(tempo)
            })
    return notas_json

def write_notes_to_json(notas_json: List[Dict], carpeta_destino="JsonFiles") -> None:
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_completa = os.path.join(carpeta_destino, "notas_detectadas.json")
    with open(ruta_completa, "w") as f:
        json.dump(notas_json, f, indent=2)

def generate_note_wave(freq, dur, sr=16000, volume=1.0) -> np.ndarray:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = np.sin(2 * np.pi * freq * t)
    env = np.ones_like(t)
    n_ataque = int(sr * 0.01)
    n_decay = int(sr * 0.1)
    if n_ataque + n_decay < len(env):
        env[:n_ataque] = np.linspace(0, 1, n_ataque)
        env[n_ataque:n_ataque+n_decay] = np.linspace(1, 0.8, n_decay)
        env[n_ataque+n_decay:] = 0.8
    else:
        env[n_ataque:] = np.linspace(1, 0.8, len(env)-n_ataque)
    return (volume * wave * env).astype(np.float32)

def exportar_json_si_confirmado(notas_json, duracion_audio_trim):
    confirmar = input("¿Querés exportar las notas a un .json? (s/n): ").strip().lower()
    if confirmar == 's':
        umbral_tiempo_final = duracion_audio_trim - 0.5
        notas_json_filtradas = []
        for n in notas_json:
            if n["inicio"] > umbral_tiempo_final and n["duracion"] < 0.05:
                print(f"⚠️ Nota descartada cerca del final: {n['nota']} en t={n['inicio']}s dur={n['duracion']}s")
                continue
            notas_json_filtradas.append(n)
        ruta_json = os.path.join("JsonFiles", "notas_detectadas.json")
        with open(ruta_json, "w") as f:
            json.dump(notas_json_filtradas, f, indent=2)
        print("✅ Archivo JSONx guardado.")
    else:
        print("❌ No se guardó el archivo JSON.")

def verificar_notas_detectadas(audio_path: str, reconstruido_path: str, ruta_json= "JsonFiles/notas_detectadas.json"):
    print("\n Iniciando verificación automática de las notas detectadas...")
    y_orig, sr = librosa.load(audio_path, sr=None)
    y_recon, _ = librosa.load(reconstruido_path, sr=sr)
    ruta_json = os.path.join("JsonFiles", "notas_detectadas.json")
    with open(ruta_json, "r") as f:
        notas = json.load(f)
    errores = []
    S = librosa.feature.melspectrogram(y=y_orig, sr=sr, n_fft=2048, hop_length=512)
    S_db = librosa.power_to_db(S, ref=np.max)
    times = librosa.frames_to_time(np.arange(S_db.shape[1]), sr=sr, hop_length=512)
    for n in notas:
        start = n["inicio"]
        end = n["inicio"] + n["duracion"]
        mask = (times >= start) & (times <= end)
        energia = np.mean(S_db[:, mask])
        if np.isnan(energia) or energia < -35:
            errores.append(f"⚠️ Baja energía detectada en {n['nota']} entre {start:.2f}-{end:.2f}s")
    if len(y_recon) > len(y_orig):
        y_recon = y_recon[:len(y_orig)]
    elif len(y_orig) > len(y_recon):
        y_orig = y_orig[:len(y_recon)]
    correlacion = np.corrcoef(y_orig, y_recon)[0,1]
    print(f"🔗 Correlación entre original y reconstruido: {correlacion:.3f}")
    if correlacion < 0.85:
        errores.append(f"⚠️ Baja correlación entre señales: {correlacion:.3f}")
    if not errores:
        print("✅ Verificación completada sin errores. Las notas detectadas parecen correctas.")
    else:
        print("❌ Se detectaron posibles problemas:")
        for err in errores:
            print("   →", err)

def main(filepath: str, carpeta_destino="static/temp"):
    # --- Cargar audio ---
    y, sr, filepath = load_and_preprocess_audio(filepath)
    y_trim = y

    # --- Pitch detection ---
    pitches = detect_pitch(y_trim, sr)
    pitches = filtrar_pitch_por_energia(pitches, y_trim, sr)

    dur_trim = librosa.get_duration(y=y_trim, sr=sr)
    pitches = [p for p in pitches if p[0] < dur_trim - 0.2 or p[1] > 100]

    print("👉 Primeros 10 pitches:", pitches[:10])

    # --- Tempo ---
    tempo, _ = librosa.beat.beat_track(y=y_trim, sr=sr)

    # --- Conversión y agrupación ---
    notas_json = group_pitches_to_notes(pitches, tempo, notas_dict)

    # --- Filtrado de notas inválidas ---
    valid_notes = {"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"}
    notas_filtradas = []

    for n in notas_json:
        nombre = n["nota"].strip().upper()

        base = ''.join([c for c in nombre if not c.isdigit()])
        if base not in valid_notes:
            continue

        num = ''.join([c for c in nombre if c.isdigit()])
        if num == "" or not num.isdigit():
            continue
        if not (0 <= int(num) <= 7):
            continue

        if float(n["duracion"]) <= 0:
            continue

        if n["figura"].lower() not in ["corchea","negra","blanca","redonda","semicorchea"]:
            continue

        notas_filtradas.append(n)

    notas_json = notas_filtradas
    print(f"🎼 Violín: {len(notas_json)} notas válidas final.")

    # --- Guardar JSON ---
    write_notes_to_json(notas_json, carpeta_destino)
    print(f"📄 JSON guardado en {carpeta_destino}/notas_detectadas.json")

    print("🎯 Script violin listo. El worker generará PNG + XML con MuseScore.")
    return


# ========== ENTRADA SCRIPT ==========
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python LeerArchivoYnota_violin.py <ruta_mp3> [carpeta_destino]")
        exit(1)

    mp3_path = sys.argv[1]
    carpeta_destino = sys.argv[2] if len(sys.argv) > 2 else "static/temp"
    main(mp3_path, carpeta_destino)