#Importo librerias
# Procesamiento de audio
import librosa
import librosa.display
import soundfile as sf
# Detección de pitch
import crepe
# Utilidades numéricas y científicas
import numpy as np
import scipy
# Visualización 
import matplotlib.pyplot as plt
import os
from pydub import AudioSegment
from pydub.utils import which
import pygame
import json
np.float = float

#Links de PC
# ruta video: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3
# ruta ffmpeg: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe

#Links ruta Notebook personal
# ruta video: c:\Users\fb050\OneDrive\Desktop\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3
# ruta ffmpeg: c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe

#Links ruta Notebook ORT
# ruta video: NOSE
# ruta ffmpeg: NOSE
# ruta ffprobe: NOSE

#Los directorios de ffmpeg del .exe para que funciones
AudioSegment.converter = which("ffmpeg") or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = which("ffprobe") or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

#Ruta del archivo
ruta = r"C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3"

#verificás si el archivo .mp3 realmente está en esa ruta.
if not os.path.exists(ruta):
    raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

def cargar_audio(filepath, sr=22050):
    #Carga un archivo de audio. Si es .mp3 lo convierte a .wav automáticamente.
    # Parámetros:- filepath: Ruta al archivo de audio - sr: Frecuencia de muestreo deseada (por defecto 22050 Hz)
    # Devuelve:- y: señal de audio como array numpy - sr: frecuencia de muestreo
    # Verificar extensión del archivo
    filename, ext = os.path.splitext(filepath)

    # Si es .mp3, convertir a .wav
    if ext.lower() == ".mp3":
        print("Convirtiendo .mp3 a .wav...")
        audio_mp3 = AudioSegment.from_mp3(filepath)
        filepath_wav = filename + ".wav"
        audio_mp3.export(filepath_wav, format="wav")
        filepath = filepath_wav  # Actualiza la ruta para usar el nuevo .wav

    # Cargar el archivo .wav
    print(f"Cargando archivo: {filepath}")
    y, sr = librosa.load(filepath, sr=sr)
    print("Audio cargado correctamente.")
    return y, sr, filepath

#Carga el audio a la ruta
y, sr, filepath= cargar_audio(ruta)

#Confirmacion con el usuario si el archivo esta bien
# Luego de cargar_audio(...)
# def abrir_wav(path):
    # print(f"Reproduciendo {path}...")
    # pygame.init()
    # pygame.mixer.init()
    # pygame.mixer.music.load(path)
    # pygame.mixer.music.play()
    # while pygame.mixer.music.get_busy():
    #     continue   
# abrir_wav(filepath)
# confirm = input("¿Querés continuar con este archivo .wav? (s/n): ").strip().lower()
# if confirm != 's':
#     print("Proceso detenido. Revisá el archivo original.")
#     exit()



#DETECTAR PITCH
def detectar_pitch(y, sr, step_size_ms=10, threshold=0.9):
    #Usa CREPE para detectar el pitch en una señal de audio.
    #Parámetros:
    # - y: señal de audio    
    # - sr: sample rate (frecuencia de muestreo)
    #- step_size_ms: resolución temporal en milisegundos
    #- threshold: umbral de confianza mínima (0 a 1)
    #  Devuelve:
    #- pitches_filtradas: lista de notas detectadas con tiempo y frecuencia
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
    time, frequency, confidence, _ = crepe.predict(y, sr, step_size=step_size_ms, viterbi=True)

    # Filtrar por confianza
    #Filtro de confianza: descartamos predicciones dudosas (ej: menos de 0.8 de confianza).
    pitches_filtradas = [] 
    for t, f, c in zip(time, frequency, confidence):
        if c >= threshold and 30 < f < 1200:
            pitches_filtradas.append((t, f))  # tiempo y frecuencia
    
    #printeamois la informacion
    print(f"Se detectaron {len(pitches_filtradas)} pitches con confianza > {threshold}.")
    return pitches_filtradas

#Ejecutar la funcion completita
y, sr, ruta_wav = cargar_audio(ruta)
pitches = detectar_pitch(y, sr)
print("Primeros 10 pitches:", pitches[:10])  # Mostrar algunos resultados

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

def frecuencia_a_nota(freq):
    return min(notas_dict.items(), key=lambda item: abs(item[1] - freq))[0]

# Ruta al .wav convertido
ruta_wav = filepath 
y, sr = librosa.load(ruta_wav, sr=16000)

tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
if len(y.shape) == 1:
    y = np.expand_dims(y, axis=1)

time, frequency, confidence, _ = crepe.predict(y, sr, step_size=10, viterbi=True)
pitch_data = [
    (t, f) for t, f, c in zip(time, frequency, confidence)
    if c > 0.9 and 30 < f < 1200
]


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

MIN_DURACION_NOTA = 0.03
NOTA_UMBRAL_VARIACION = 0.25

def semitonos(f1, f2):
    return abs(12 * np.log2(f1 / f2))

# Un for que analiza cada tramo de 10 segundos
notas_json = []
if pitch_data:
    segmento_duracion = 10.0  # duración de cada tramo en segundos
    total_tiempo = pitch_data[-1][0]
    num_segmentos = int(np.ceil(total_tiempo / segmento_duracion))
for s in range(num_segmentos):
    inicio_seg = s * segmento_duracion
    fin_seg = (s + 1) * segmento_duracion
    print(f"\n🔍 Analizando tramo {s+1}/{num_segmentos} ({inicio_seg:.2f}s - {fin_seg:.2f}s)")
    # Filtramos solo los pitches de este tramo
    segmento = [p for p in pitch_data if inicio_seg <= p[0] < fin_seg]
    if not segmento:
        print("  ⚠️ Sin datos en este tramo.")
        continue
    # Si es el último tramo, suavizamos frecuencias con media móvil (ventana 3)
    if s == num_segmentos - 1 and len(segmento) >= 3:
        tiempos_seg = [p[0] for p in segmento]
        freqs_seg = [p[1] for p in segmento]
        freqs_suavizadas = np.convolve(freqs_seg, np.ones(3)/3, mode='same')
        segmento = list(zip(tiempos_seg, freqs_suavizadas))
    # Inicializamos variables de agrupamiento
    inicio = segmento[0][0]
    freq_actual = segmento[0][1]
    nota_actual = frecuencia_a_nota(freq_actual)
    for i in range(1, len(segmento)):
        t, f = segmento[i]
        # Si la nota nueva es diferente (por semitonos), se cierra la nota anterior
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
            # Se actualiza a la nueva nota
            inicio = t
            freq_actual = f
            nota_actual = frecuencia_a_nota(f)
        # Advertencia si hay separación anormal (solo en último tramo)
        if s == num_segmentos - 1 and abs(t - inicio) > 2.0:
            print(f"  ⚠️ Agrupamiento raro detectado entre {inicio:.2f}s y {t:.2f}s")
    # Cierre de la última nota del tramo
    duracion = segmento[-1][0] - inicio
    if MIN_DURACION_NOTA <= duracion < 6.0:
        figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
        notas_json.append({
            "nota": nota_actual,
            "inicio": round(inicio, 3),
            "duracion": round(duracion, 3),
            "compas": compas,
            "figura": figura,
            "tempo": int(tempo)
        })
    # Verificación extra de duración excesiva (último tramo)
    if s == num_segmentos - 1 and duracion > 6.0:
        print(f"⚠️ Nota descartada por duración excesiva: {duracion:.2f}s")


        # Si hay silencio significativo, se agrega pausa
        if t - inicio > 1.5:  # más de 1.5 segundos sin notas válidas
            print(f"Silencio detectado entre {inicio:.2f}s y {t:.2f}s")

        if abs(pitch_data[i][0] - inicio) > 0.03:   
            if abs(t - inicio) > 2.0:
                print(f"⚠️ Agrupamiento raro detectado entre {inicio:.2f}s y {t:.2f}s")
            duracion = max(t - inicio, 0)
            if duracion == 0:
                continue
            if duracion > 6.0:
                print(f"⚠️ Nota descartada por duración demasiado larga: {duracion:.2f}s")
                continue
            if duracion > 0.02:  # descartar eventos muy breves
                figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                notas_json.append({
                    "nota": nota_actual,
                    "inicio": round(inicio, 3),
                    "duracion": round(max(duracion, 0.03), 3),
                    "compas": compas,
                    "figura": figura,
                    "tempo": int(tempo)
                })
            inicio = t

    # Agregar la última nota que se estaba tocando al final del audio
    duracion = pitch_data[-1][0] - inicio
    if 0.02 < duracion < 5:  # límite máximo de duración razonable
        figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
        notas_json.append({
            "nota": nota_actual,
            "inicio": round(inicio, 3),
            "duracion": round(max(duracion, 0.03), 3),
            "compas": compas,
            "figura": figura,
            "tempo": int(tempo)
            })
    if notas_json and notas_json[-1]["duracion"] < 0.05:
        print(f"⚠️ Nota final descartada por ser demasiado corta: {notas_json[-1]['duracion']}s")
        notas_json = notas_json[:-1]

with open("notas_detectadas.json", "w") as f:
    json.dump(notas_json, f, indent=2)

#Testeo con una devolucion de un archivo .wav
# Cargar notas desde el JSON
with open("notas_detectadas.json", "r") as f:
    notas = json.load(f)
if not notas:
    print("⚠️ No se detectaron notas válidas. Abortando reconstrucción.")
    exit()

# Frecuencia de muestreo para el audio de salida
sr = 16000

# Función para generar una onda senoidal por nota
def generar_onda(freq, duracion, sr=16000, volumen=1.0):
    t = np.linspace(0, duracion, int(sr * duracion), False)
    onda = volumen * np.sin(2 * np.pi * freq * t)
    return onda.astype(np.float32)

# Crear la pista de audio completa
# Ajustar duración del output al input si es necesario
# Ajustar duración del output al input si es necesario
# Calcular RMS del audio original por ventanas
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)

audio_total = np.array([], dtype=np.float32)
tiempo_actual = 0.0

for nota in notas:
    nombre = nota["nota"]
    inicio = nota["inicio"]
    duracion = nota["duracion"]
    freq = notas_dict.get(nombre, None)

    if freq is None:
        continue

    # Evitar notas excesivamente largas por error
    if duracion > 5.0:
        continue

    # Calcular energía (RMS) local para ajustar volumen
    rms_local = next((r for t_, r in zip(rms_times, rms) if abs(t_ - inicio) < 0.05), 0.03)
    volumen = np.clip(rms_local * 3, 0.05, 1.0)

    if rms_local < 0.01:
        continue  # evitar sonidos en zonas silenciosas

    # Insertar silencio si la nota no arranca justo después de la anterior
    if inicio > tiempo_actual:
        silencio = np.zeros(int(sr * (inicio - tiempo_actual)))
        audio_total = np.concatenate((audio_total, silencio))
        tiempo_actual = inicio

    # Generar onda y sumarla al audio
    onda = generar_onda(freq, duracion, sr, volumen)
    audio_total = np.concatenate((audio_total, onda))
    tiempo_actual += duracion

# Asegurarse que la duración final coincida con el input original
# Calcular duración real del archivo WAV original (antes del resampleo estéreo)
expected_duration = librosa.get_duration(path=filepath)
actual_duration = librosa.get_duration(y=audio_total, sr=sr)

if actual_duration > expected_duration:
    print(f"⚠️ Duración excedida por {actual_duration - expected_duration:.2f}s, recortando.")
    audio_total = audio_total[:int(expected_duration * sr)]
elif actual_duration < expected_duration:
    padding = np.zeros(int((expected_duration - actual_duration) * sr))
    audio_total = np.concatenate((audio_total, padding))

# Normalizar para evitar clipping y controlar el volumen
rms = np.sqrt(np.mean(audio_total**2))
if rms > 0.5:
    print(f"⚠️ RMS alto ({rms:.2f}), bajando volumen.")
    audio_total *= 0.7  # reducir volumen general si está muy fuerte
# Normalizar (re-asegurar que el valor máximo sea 1.0 o menos)
if np.max(np.abs(audio_total)) > 0:
    if len(audio_total) < 10 or np.all(audio_total == 0):
        print("⚠️ Error: El audio generado está vacío o contiene solo silencio.")
        exit()
    audio_total = audio_total / np.max(np.abs(audio_total))


# Guardar en un archivo WAV
sf.write("reconstruccion.wav", audio_total, sr)
print("Archivo 'reconstruccion.wav' generado correctamente.")

# Solución: revisar si el final está vacío y forzar un fade out si es necesario
if np.max(np.abs(audio_total[-sr * 2:])) < 0.01:  # Últimos 2 segundos muy silenciosos
    print("⚠️ El final del audio reconstruido está silencioso. Se aplicará fade-out o corrección.")
    duracion_restante = expected_duration - librosa.get_duration(y=audio_total, sr=sr)
    if duracion_restante > 0:
        padding = np.zeros(int(sr * duracion_restante))
        audio_total = np.concatenate((audio_total, padding))
#Chequeo con el usuario
# abrir_wav("reconstruccion.wav")
# confirm = input("¿La reconstrucción suena similar al archivo original? (s/n): ").strip().lower()
# if confirm == 's':
#     with open("notas_detectadas.json", "w") as f:
#         json.dump(notas_json, f, indent=2)
#     print("✅ Archivo JSON exportado correctamente.")
# else:
#     print("❌ Proceso detenido. La reconstrucción no fue satisfactoria.")
#     exit()

def exportar_json_si_confirmado(notas_json):
    confirmar = input("¿Querés exportar las notas a un .json? (s/n): ").strip().lower()
    if confirmar == 's':
        # Paso extra: eliminar notas muy cortas dentro del último medio segundo del audio original
        umbral_tiempo_final = expected_duration - 0.5  # últimos 0.5 segundos

        notas_json_filtradas = []
        for n in notas_json:
            if n["inicio"] > umbral_tiempo_final and n["duracion"] < 0.05:
                print(f"⚠️ Nota descartada cerca del final: {n['nota']} en t={n['inicio']}s dur={n['duracion']}s")
                continue
            notas_json_filtradas.append(n)

        # Guardamos el nuevo JSON limpio
        with open("notas_detectadas.json", "w") as f:
            json.dump(notas_json_filtradas, f, indent=2)
        print("✅ Archivo JSON guardado.")
    else:
        print("❌ No se guardó el archivo JSON.")
