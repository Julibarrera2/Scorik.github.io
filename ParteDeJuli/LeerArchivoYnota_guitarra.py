# Procesamiento de audio (GUITARRA)
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

# FIX: SciPy >=1.11 eliminó signal.hann, pero librosa todavía lo usa
if not hasattr(scipy.signal, "hann"):
    scipy.signal.hann = windows.hann

# Compatibilidad con paquetes antiguos
np.float = float
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ====== Config FFmpeg (igual que violín) ======
FFMPEG_BIN  = os.getenv("FFMPEG_BINARY") or which("ffmpeg") or which("ffmpeg.exe")
FFPROBE_BIN = os.getenv("FFPROBE_BINARY") or which("ffprobe") or which("ffprobe.exe")

if (not FFMPEG_BIN or not FFPROBE_BIN) and os.name == "nt":
    FFMPEG_BIN  = FFMPEG_BIN  or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
    FFPROBE_BIN = FFPROBE_BIN or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

AudioSegment.converter = FFMPEG_BIN
AudioSegment.ffprobe   = FFPROBE_BIN
if not AudioSegment.converter or not AudioSegment.ffprobe:
    raise RuntimeError(
        "FFmpeg/ffprobe no encontrados. En Docker vienen instalados; "
        "en Windows setear FFMPEG_BINARY/FFPROBE_BINARY o agregar al PATH."
    )

# ====== Parámetros específicos de GUITARRA ======
GTR_MIN_FREQ = 82.0      # ~E2
GTR_MAX_FREQ = 1400.0    # ~E6 (suficiente)
CREPE_SR     = 16000
STEP_MS      = 5         # más fino para ataques
CONF_THRESH  = 0.90
ENERGY_DB    = -55       # menos estricto que violín

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

def load_and_preprocess_audio(filepath: str, sr: int = 22050) -> Tuple[np.ndarray, int, str]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
    sr = int(sr)
    y, sr = librosa.load(filepath, sr=sr, mono=True)
    print("Audio cargado correctamente.")
    return y, sr, filepath

def detect_pitch(y: np.ndarray, sr: int, threshold=CONF_THRESH) -> List[Tuple[float, float]]:
    print("Detectando notas (guitarra)...")
    # CREPE requiere 16k y forma (N,1)
    if sr != CREPE_SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=CREPE_SR)
        sr = CREPE_SR
    if y.ndim == 1:
        y = np.expand_dims(y, axis=1)

    time, frequency, confidence, _ = crepe.predict(
        y, sr, step_size=STEP_MS, viterbi=True
    )

    # Filtrado por confianza + rango de guitarra
    pitches = []
    for t, f, c in zip(time, frequency, confidence):
        if c >= threshold and GTR_MIN_FREQ <= f <= GTR_MAX_FREQ:
            pitches.append((t, f))

    # Suavizado muy corto (mediana ventana 3) para vibrato leve
    if len(pitches) >= 3:
        ts = np.array([t for t, _ in pitches])
        fs = np.array([f for _, f in pitches])
        fs_med = fs.copy()
        for i in range(1, len(fs) - 1):
            fs_med[i] = np.median(fs[i-1:i+2])
        pitches = list(zip(ts.tolist(), fs_med.tolist()))

    print(f"Se detectaron {len(pitches)} frames con confianza > {threshold}.")
    return pitches

# Diccionario de notas (igual)
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

    print("→ Cantidad de frames:", len(pitch_data))
    if not pitch_data:
        return []

    def calcular_figura_y_compas(duracion, tempo, inicio):
        negra_duracion = 60 / max(tempo, 1e-6)
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

    MIN_DURACION_NOTA = 0.06          # ataques cortos
    NOTA_UMBRAL_VARIACION = 0.6       # más sensible que violín

    def semitonos(f1, f2):
        return abs(12 * np.log2(max(f1,1e-6) / max(f2,1e-6)))

    notas_json = []
    inicio = pitch_data[0][0]
    freq_actual = pitch_data[0][1]
    nota_actual = frecuencia_a_nota(freq_actual)

    for t, f in pitch_data[1:]:
        if semitonos(f, freq_actual) > NOTA_UMBRAL_VARIACION:
            duracion = t - inicio
            if duracion >= MIN_DURACION_NOTA:
                figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                notas_json.append({
                    "instrumento": "guitarra",
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
            # media para estabilidad
            freq_actual = (freq_actual + f) / 2

    # última nota
    duracion = pitch_data[-1][0] - inicio
    if duracion >= MIN_DURACION_NOTA:
        figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
        notas_json.append({
            "instrumento": "guitarra",
            "nota": nota_actual,
            "inicio": round(inicio, 3),
            "duracion": round(duracion, 3),
            "compas": compas,
            "figura": figura,
            "tempo": int(tempo)
        })

    return notas_json

def write_notes_to_json(notas_json: List[Dict], carpeta_destino="static/temp"):
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_completa = os.path.join(carpeta_destino, "notas_detectadas.json")
    with open(ruta_completa, "w") as f:
        json.dump(notas_json, f, indent=2)

# Reconstrucción con timbre tipo guitarra (armónicos + decay exp)
def generate_note_wave_guitar(freq, dur, sr=16000, volume=1.0) -> np.ndarray:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = np.zeros_like(t)
    n_harm = 6
    # Envolvente de plucked: ataque rápido, decay exp
    atk = max(1, int(0.005 * sr))
    env = np.ones_like(t)
    env[:atk] = np.linspace(0, 1, atk)
    tau = dur * 0.6
    if tau > 0:
        env *= np.exp(-t / tau)

    for k in range(1, n_harm + 1):
        amp = 1.0 / k
        wave += amp * np.sin(2 * np.pi * (k * freq) * t)

    wave = (volume * env * wave / np.max(np.abs(wave) + 1e-9)).astype(np.float32)
    return wave

def main(filepath: str, carpeta_destino="static/temp"):
    y, sr, filepath = load_and_preprocess_audio(filepath)
    y_trim = y

    pitches = detect_pitch(y_trim, sr)
    pitches = filtrar_pitch_por_energia(pitches, y_trim, sr)

    dur_trim = librosa.get_duration(y=y_trim, sr=sr)
    # Evitar colas raras al final
    pitches = [p for p in pitches if p[0] < dur_trim - 0.2]

    print("Primeros 10 pitches:", pitches[:10])

    tempo, _ = librosa.beat.beat_track(y=y_trim, sr=sr)
    if tempo == 0 or np.isnan(tempo):
        tempo = 120.0

    notas_json = group_pitches_to_notes(pitches, tempo, notas_dict)

    # Guardar JSON en la carpeta destino:
    write_notes_to_json(notas_json, carpeta_destino)
    print(f"\n=== Guitarra: notas_json = {len(notas_json)} elementos ===")

    # ====== RECONSTRUCCIÓN ======
    ruta_json = os.path.join(carpeta_destino, "notas_detectadas.json")
    with open(ruta_json, "r") as f:
        notas = json.load(f)
    if not notas:
        print("⚠️ No se detectaron notas válidas. Abortando reconstrucción.")
        return

    audio_original, sr_original = sf.read(filepath)
    expected_duration = len(audio_original) / sr_original
    sr_out = sr_original

    notas = [n for n in notas if n["inicio"] + n["duracion"] <= expected_duration]
    total_samples = int(np.ceil(expected_duration * sr_original))
    if audio_original.ndim > 1:
        n_channels = audio_original.shape[1]
        audio_total = np.zeros((total_samples, n_channels), dtype=np.float32)
    else:
        audio_total = np.zeros(total_samples, dtype=np.float32)

    end = 0
    start = 0
    for n in notas:
        freq = notas_dict[n["nota"]]
        start = int(n["inicio"] * sr_out)
        end = start + int(n["duracion"] * sr_out)
        wave = generate_note_wave_guitar(freq, n["duracion"], sr=sr_out, volume=1.0)

        fade_ms = int(0.003 * sr_out)
        if wave.shape[0] > fade_ms * 2:
            ramp = np.linspace(0, 1, fade_ms)
            wave[:fade_ms] *= ramp
            wave[-fade_ms:] *= ramp[::-1]

        slice_end = min(end, audio_total.shape[0])
        existing = audio_total[start:slice_end]
        wave = wave[:len(existing)]

        if existing.ndim == 2 and wave.ndim == 1:
            wave = np.tile(wave[:, None], (1, existing.shape[1]))

        mix = existing + wave
        audio_total[start:slice_end] = np.clip(mix, -1.0, 1.0)

    # Normalización suave + fade-out global cortito
    fs = min(int(5.0 * sr_original), len(audio_total))
    if fs > 0:
        tail = np.linspace(1.0, 0.0, fs)
        if audio_total.ndim == 1:
            audio_total[-fs:] *= tail
        else:
            audio_total[-fs:, :] *= tail[:, None]

    peak = np.max(np.abs(audio_total)) + 1e-9
    audio_total /= peak

    sf.write("reconstruccion.wav", audio_total, sr_out)
    print("✅ [Guitarra] 'reconstruccion.wav' generado correctamente.")

    # ====== Llamada a NotasAPartitura.py ======
    print("\n Generando imagen...")
    REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    notas_script = os.path.join(REPO_ROOT, "ParteDeTota", "NotasAPartitura_guitarra.py")
    subprocess.run([sys.executable, notas_script, carpeta_destino], check=True)

# ========== ENTRADA ==========
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python LeerArchivoYnota_guitarra.py <ruta_mp3> [carpeta_destino]")
        sys.exit(1)
    mp3_path = sys.argv[1]
    carpeta_destino = sys.argv[2] if len(sys.argv) > 2 else "static/temp"
    main(mp3_path, carpeta_destino)
