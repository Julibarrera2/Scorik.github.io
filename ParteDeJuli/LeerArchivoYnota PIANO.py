#Importo librerias
# Procesamiento de audio
import librosa
import soundfile as sf
# Detección de pitch
import crepe
# Utilidades numéricas y científicas
import numpy as np
# Visualización 
import os
from pydub import AudioSegment
from pydub.utils import which
from typing import List, Tuple, Dict
import json
import warnings
import subprocess
import sys
np.float = float

#Links de PC
# ruta video piano: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3
# ruta ffmpeg: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe
# ruta video violin 1: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-1.mp3
# ruta video violin 2: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-2.mp3
# ruta video violin 3: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-3.mp3

#Links ruta Notebook personal
# ruta video: c:\Users\fb050\Downloads\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3
# ruta ffmpeg: c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe
# ruta video violin 1: c:\Users\fb050\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-1.mp3
# ruta video violin 2: c:\Users\fb050\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-2.mp3
# ruta video violin 3: c:\Users\fb050\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-3.mp3

#Links ruta Notebook ORT
# ruta video: 
# ruta ffmpeg: C:\Users\48592310\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: C:\Users\48592310\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe
# ruta video violin 1: 
# ruta video violin 2:
# ruta video violin 3: 

warnings.filterwarnings("ignore", category=RuntimeWarning)
# Utilidades extra para filtrar silencios y notas con poca energía
def filtrar_pitch_por_energia(pitch_list, y_signal, sr_signal, threshold_db=-60):
    """Descarta estimaciones de pitch en zonas con poca energía."""
    hop = int(sr_signal * 0.01)  # 10 ms, coincide con step_size_ms
    rms = librosa.feature.rms(y=y_signal, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr_signal, hop_length=hop)
    filtrados = []
    for t, f in pitch_list:
        idx = np.argmin(np.abs(times - t))
        if librosa.amplitude_to_db([rms[idx]], ref=np.max)[0] > threshold_db:
            filtrados.append((t, f))
    return filtrados

def recortar_final_por_energia(y_signal, sr_signal, threshold_db=-60):
    """Recorta el final del audio cuando la energía cae por debajo del umbral."""
    rms = librosa.feature.rms(y=y_signal)[0]
    db = librosa.amplitude_to_db(rms, ref=np.max)
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr_signal)
    valid = np.where(db > threshold_db)[0]
    if valid.size == 0:
        return y_signal
    end_sample = int(times[valid[-1]] * sr_signal)
    return y_signal[:end_sample]

#Los directorios de ffmpeg del .exe para que funciones
AudioSegment.converter = which("ffmpeg") or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = which("ffprobe") or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

#Ruta del archivo


def load_and_preprocess_audio(filepath: str, sr: int = 22050) -> Tuple[np.ndarray, int, str]:
    #Carga un archivo de audio. Si es .mp3 lo convierte a .wav automáticamente.
    # Parámetros:- filepath: Ruta al archivo de audio - sr: Frecuencia de muestreo deseada (por defecto 22050 Hz)
    # Devuelve:- y: señal de audio como array numpy - sr: frecuencia de muestreo
    # Verificar extensión del archivo
    
    #verificás si el archivo .mp3 realmente está en esa ruta.
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
    
    filename, ext = os.path.splitext(filepath)
    # Si es .mp3, convertir a .wav
    if ext.lower() == ".mp3":
        print("Convirtiendo .mp3 a .wav...")
        audio_mp3 = AudioSegment.from_mp3(filepath)
        filepath_wav = filename + ".wav"
        audio_mp3.export(filepath_wav, format="wav")
        filepath = filepath_wav
    # Cargar el archivo .wav
    sr = int(sr)
    y, sr = librosa.load(filepath, sr=sr)
    print("Audio cargado correctamente.")
    return y, sr, filepath

def main(filepath: str):
    #Carga el audio a la ruta
    y, sr, filepath = load_and_preprocess_audio(filepath)

    # dejamos y_trim apuntando a toda la señal original:
    y_trim = y
    
    #Debajo de detectar pitch va esto
    # Ahora usamos y_trim para la detección
    pitches = detect_pitch(y_trim, sr)
    # Filtrado adicional de ruido por energía
    pitches = filtrar_pitch_por_energia(pitches, y_trim, sr)
    # Eliminar últimos dos segundos para evitar falsas detecciones
    dur_trim = librosa.get_duration(y=y_trim, sr=sr)
    pitches = [p for p in pitches if p[0] < dur_trim - 0.2 or p[1] > 100]
    print("Primeros 10 pitches:", pitches[:10])

    #esto va despues de group_pitches_to_notes
    tempo, _ = librosa.beat.beat_track(y=y_trim, sr=sr)
    notas_json = group_pitches_to_notes(pitches, tempo, notas_dict)
    write_notes_to_json(notas_json)

    #Esto va a abajo de lo de arriba de generate_note_wave
    # 3) Ahora imprimimos antes y después de filtrar los últimos 2s
    print(f"\n=== Antes de filtrar últimos 2 s, notas_json tiene {len(notas_json)} elementos ===")
    for n in notas_json:
        pass

    duracion_audio_trim = librosa.get_duration(y=y, sr=sr)

    print(f"\n=== Después de filtrar últimos 2 s, notas_json tiene {len(notas_json)} elementos ===")
    for n in notas_json:
        pass

    #Testeo con una devolucion de un archivo .wav
    # Cargar notas desde el JSON
    ruta_json = os.path.join("JsonFiles", "notas_detectadas.json")
    with open(ruta_json, "r") as f:
        notas = json.load(f)
    if not notas:
        print("⚠️ No se detectaron notas válidas. Abortando reconstrucción.")
        exit()

    # 1) Cargo notas y compruebo que existan
    with open(ruta_json, "r") as f:
        notas = json.load(f)

    # 2) Cargo WAV original para sample rate y duración
    audio_original, sr_original = sf.read (filepath)
    expected_duration = len(audio_original) / sr_original
    sr_out=sr_original

    # 3) FILTRAR NOTAS QUE SALEN DEL RANGO DEL AUDIO
    expected_duration = len(audio_original) / sr_original
    notas = [
        n for n in notas
        if n["inicio"] + n["duracion"] <= expected_duration
    ]

    # 3 bis) Preparo buffer de salida alineado al input (mantiene canales)
    total_samples = int(np.ceil(expected_duration * sr_original))
    audio_total = np.zeros((total_samples, ) + (() if audio_original.ndim == 1 else (audio_original.shape[1],)), dtype=np.float32)
    if audio_original.ndim > 1:
        n_channels = audio_original.shape[1]
        audio_total = np.zeros((audio_original.shape[0], n_channels), dtype=np.float32)
    else:
        # Mono
        audio_total = np.zeros(audio_total.shape, dtype=np.float32)
    
    #Esto va despues de la funcion generate_note_wave hasta exportar_json_si_confirmado
    # 5) Inserto cada nota en su posición exacta
    for n in notas:
        freq = notas_dict[n["nota"]]
        start = int(n["inicio"] * sr_out)
        end   = start + int(n["duracion"] * sr_out)

        # extraigo el audio ORIGINAL (mono o estéreo)
        wave = generate_note_wave(freq, n["duracion"], sr=sr_out, volume=1.0)

        # opcional: un pequeño cross-fade para evitar clicks de borde
        fade_ms = int(0.005 * sr_out)
        if wave.shape[0] > fade_ms*2:
            ramp = np.linspace(0,1,fade_ms)
            if wave.ndim == 1:
                wave[:fade_ms]  *= ramp
                wave[-fade_ms:] *= ramp[::-1]
            else:
                wave[:fade_ms]  *= ramp[:,None]
                wave[-fade_ms:] *= ramp[::-1][:,None]

        # Cortar al buffer real
        slice_end = min(end, audio_total.shape[0])
        # Me aseguro de que wave y audio_total tienen la misma dimensión
        existing = audio_total[start:slice_end]
        wave = wave[:len(existing)]
        # si original es estéreo y wave mono, replico la pista
        if existing.ndim == 2 and wave.ndim == 1:
            wave = np.tile(wave[:, None], (1, existing.shape[1]))
        # Mezcla directa
        mix = existing + wave
        # Clip si excede [-1,1]
        audio_total[start:slice_end] = np.clip(mix, -1.0, 1.0)

        # Normalización local por RMS (igualar volumen local al original)
        # nuevo: RMS real por frame (ambos canales juntos)
        seg = audio_original[start: slice_end]
        # si es estéreo, promediamos potencias de ambos canales
        power = seg**2
        if seg.ndim>1:
            power = power.mean(axis=1)
        orig_rms = np.sqrt(np.mean(power)) + 1e-8
        wave_rms = np.sqrt(np.mean(wave**2))    + 1e-8
        wave *= (orig_rms / wave_rms)

        # Cortar al buffer real
    slice_end = min(end, audio_total.shape[0])

    # Extraer los segmentos a mezclar
    existing  = audio_total[start: slice_end]       # (M,) o (M,2)
    wave_part = wave[: len(existing)]               # (M,) o (M,2)

    # Mezcla directa, independientemente de mono/estéreo
    mix = existing + wave_part                      # suma elemento a elemento

    # Clip para evitar valores fuera de [-1,1]
    audio_total[start: slice_end] = np.clip(mix, -1.0, 1.0)

    # 6) Aplico un fade-out suave en los últimos 10 segundos
    fade_dur = min(10.0, expected_duration)
    fs = min(int(fade_dur * sr_original), len(audio_total))
    fade_env = np.linspace(1.0, 0.0, fs)
    if audio_total.ndim == 1:
        audio_total[-fs:] *= fade_env
    else:
        audio_total[-fs:, :] *= fade_env[:, None]

    # Genero el env de fade (1D)
    fade_env = np.linspace(1.0, 0.0, fs)

    # 7) Normalizo para éviter clipping
    peak = np.max(np.abs(audio_total))
    if peak > 0:
        audio_total /= peak

    # 8) Guardo el WAV reconstruido
    sf.write("reconstruccion.wav", audio_total, sr_out)
    print("✅ 'reconstruccion.wav' generado correctamente con fade-out al final.")
    exportar_json_si_confirmado(notas_json, duracion_audio_trim)
    verificar_notas_detectadas(filepath, "reconstruccion.wav")



#DETECTAR PITCH
def detect_pitch(y: np.ndarray, sr: int, threshold=0.9) -> List[Tuple[float, float]]:
    #Usa CREPE para detectar el pitch en una señal de audio.
    #Parámetros:
    # y: señal de audio   
    # sr: sample rate (frecuencia de muestreo)
    #step_size_ms: resolución temporal en milisegundos
    #threshold: umbral de confianza mínima (0 a 1)
    # Devuelve:
    #pitches_filtradas: lista de notas detectadas con tiempo y frecuencia
    step_size_ms=10
    threshold=0.9
    print("Detectando pitch con CREPE...")

    # CREPE necesita un sample rate de 16000
    #Resampleo a 16000 Hz: CREPE solo funciona con 16000 Hz, por lo tanto si cargamos a 22050 Hz lo transformamos.
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        sr = 16000
    
    # CREPE requiere una señal estéreo
    #Reformateo del audio: CREPE espera entrada estéreo (matriz Nx1).
    if len(y.shape) == 1:
        y = np.expand_dims(y, axis=1)
    
    # Ejecutamos CREPE
    #crepe.predict(...): Devuelve arrays de tiempo, frecuencia, confianza y activación
    time, frequency, confidence, _ = crepe.predict(y, sr, step_size=step_size_ms,viterbi=True)

    # Filtrar por confianza
    #Filtro de confianza: descartamos predicciones dudosas (ej: menos de 0.8 de confianza).
    pitches_filtradas = [] 
    for t, f, c in zip(time, frequency, confidence):
        if c >= threshold and 30 < f < 1200:
            pitches_filtradas.append((t, f))  # tiempo y frecuencia
    
        #printeamois la informacion
    print(f"Se detectaron {len(pitches_filtradas)} pitches con confianza > {threshold}.")
    return pitches_filtradas

#Pasar de pitch a nota
# Diccionario de notas
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

    MIN_DURACION_NOTA = 0.1
    NOTA_UMBRAL_VARIACION = 0.25

    def semitonos(f1, f2):
        return abs(12 * np.log2(f1 / f2))

    # — AGRUPAR NOTAS EN TODO EL AUDIO SIN SEGMENTACIÓN —
    notas_json = []
    if pitch_data:
        # Inicializo con la primera detección
        inicio = pitch_data[0][0]
        freq_actual = pitch_data[0][1]
        nota_actual = frecuencia_a_nota(freq_actual)

        for t, f in pitch_data[1:]:
            # Si cambia de nota (umbral en semitonos)
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
                #Actualizo para la siguiente nota
                inicio = t
                freq_actual = f
                nota_actual = frecuencia_a_nota(f)
            else:
                # Suavizo pequeñas variaciones dentro de la misma nota
                freq_actual = (freq_actual + f) / 2

        # Cierro la última nota al final del audio
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

def write_notes_to_json(notas_json: List[Dict], filename="notas_detectadas.json") -> None:
    carpeta_destino = "JsonFiles"
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_completa = os.path.join(carpeta_destino, filename)
    
    with open(ruta_completa, "w") as f:
        json.dump(notas_json, f, indent=2)

print("✅ Archivo 'notas_detectadas.json' generado correctamente.")

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
        # Paso extra: eliminar notas muy cortas dentro del último medio segundo del audio original
        umbral_tiempo_final = duracion_audio_trim - 0.5  # últimos 0.5 segundos

        notas_json_filtradas = []
        for n in notas_json:
            if n["inicio"] > umbral_tiempo_final and n["duracion"] < 0.05:
                print(f"⚠️ Nota descartada cerca del final: {n['nota']} en t={n['inicio']}s dur={n['duracion']}s")
                continue
            notas_json_filtradas.append(n)

        # Guardamos el nuevo JSON limpio
        ruta_json = os.path.join("JsonFiles", "notas_detectadas.json")
        with open(ruta_json, "w") as f:
            json.dump(notas_json_filtradas, f, indent=2)
        print("✅ Archivo JSONx guardado.")
    else:
        print("❌ No se guardó el archivo JSON.")

# función automatiza el chequeo final verificando que lo anterior es correcto y si hay errores
def verificar_notas_detectadas(audio_path: str, reconstruido_path: str, ruta_json= "JsonFiles""notas_detectadas.json"):
    print("\n Iniciando verificación automática de las notas detectadas...")

    # Cargar audio original y reconstruido
    y_orig, sr = librosa.load(audio_path, sr=None)
    y_recon, _ = librosa.load(reconstruido_path, sr=sr)

    # Cargar notas
    ruta_json = os.path.join("JsonFiles", "notas_detectadas.json")
    with open(ruta_json, "r") as f:
        notas = json.load(f)

    errores = []

    # A. Chequeo de energía espectral por nota
    S = librosa.feature.melspectrogram(y=y_orig, sr=sr, n_fft=2048, hop_length=512)
    S_db = librosa.power_to_db(S, ref=np.max)
    times = librosa.frames_to_time(np.arange(S_db.shape[1]), sr=sr, hop_length=512)

    for n in notas:
        start = n["inicio"]
        end = n["inicio"] + n["duracion"]
        mask = (times >= start) & (times <= end)
        energia = np.mean(S_db[:, mask])
        if np.isnan(energia) or energia < -35:  # umbral más alto y chequeo de NaN
            errores.append(f"⚠️ Baja energía detectada en {n['nota']} entre {start:.2f}-{end:.2f}s")

    # B. Comparación con reconstrucción
    if len(y_recon) > len(y_orig):
        y_recon = y_recon[:len(y_orig)]
    elif len(y_orig) > len(y_recon):
        y_orig = y_orig[:len(y_recon)]

    correlacion = np.corrcoef(y_orig, y_recon)[0,1]
    print(f"🔗 Correlación entre original y reconstruido: {correlacion:.3f}")
    if correlacion < 0.85:
        errores.append(f"⚠️ Baja correlación entre señales: {correlacion:.3f}")

    # Métricas adicionales
    duraciones = [n["duracion"] for n in notas]
    promedio_dur = np.mean(duraciones)

    # Resultado final
    if not errores:
        print("✅ Verificación completada sin errores. Las notas detectadas parecen correctas.")
    else:
        print("❌ Se detectaron posibles problemas:")
        for err in errores:
            print("   →", err)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python LeerArchivoYnota.py <ruta_mp3>")
        exit(1)
    mp3_path = sys.argv[1]
    main(mp3_path)

    print("\n🎯 Generando imagen a partir del JSON con el script de Tota...")
    subprocess.run(["python", "../ParteDeTota/NotasAPartitura.py"])