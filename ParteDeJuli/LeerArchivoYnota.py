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
# ruta video: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\piano-lento.mp3
# ruta ffmpeg: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe

#Links ruta Notebook personal
# ruta video: c:\Users\fb050\OneDrive\Desktop\Scorik.github.io\ParteDeJuli\piano-lento.mp3
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
ruta = r"C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\piano-lento.mp3"

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
ruta_wav = "piano-lento.wav"
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

notas_json = []
if pitch_data:
    prev_nota = frecuencia_a_nota(pitch_data[0][1])
    inicio = pitch_data[0][0]

    for i in range(1, len(pitch_data)):
        t, f = pitch_data[i]
        if not (30 < f < 1200):  # descartar frecuencias fuera del rango
            continue
        nota_actual = frecuencia_a_nota(f)

        # Si hay silencio significativo, se agrega pausa
        if t - inicio > 1.5:  # más de 1.5 segundos sin notas válidas
            print(f"Silencio detectado entre {inicio:.2f}s y {t:.2f}s")

        if nota_actual != prev_nota and abs(pitch_data[i][0] - inicio) > 0.03:
            if abs(t - inicio) > 2.0:
                print(f"⚠️ Agrupamiento raro detectado entre {inicio:.2f}s y {t:.2f}s")
            duracion = max(t - inicio, 0)
            if duracion == 0:
                continue
            if duracion > 0.02:  # descartar eventos muy breves
                figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                notas_json.append({
                    "nota": prev_nota,
                    "inicio": round(inicio, 3),
                    "duracion": round(duracion, 3),
                    "compas": compas,
                    "figura": figura,
                    "tempo": int(tempo)
                })
            inicio = t
            prev_nota = nota_actual

    # Agregar la última nota que se estaba tocando al final del audio
    duracion = pitch_data[-1][0] - inicio
    if duracion > 0.02:
        figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
        notas_json.append({
            "nota": prev_nota,
            "inicio": round(inicio, 3),
            "duracion": round(duracion, 3),
            "compas": compas,
            "figura": figura,
            "tempo": int(tempo)
        })

with open("notas_detectadas.json", "w") as f:
    json.dump(notas_json, f, indent=2)



#Testeo con una devolucion de un archivo .wav
# Cargar notas desde el JSON
with open("notas_detectadas.json", "r") as f:
    notas = json.load(f)

# Frecuencia de muestreo para el audio de salida
sr = 16000

# Función para generar una onda senoidal por nota
def generar_onda(freq, duracion, sr=16000):
    t = np.linspace(0, duracion, int(sr * duracion), False)
    onda = 0.5 * np.sin(2 * np.pi * freq * t)
    return onda

# Crear la pista de audio completa
# Ajustar duración del output al input si es necesario
# Ajustar duración del output al input si es necesario
audio_total = np.array([], dtype=np.float32)
tiempo_actual = 0.0

for nota in notas:
    nombre = nota["nota"]
    inicio = nota["inicio"]
    duracion = nota["duracion"]
    freq = notas_dict.get(nombre, None)

    # Insertar silencio si hace falta
    if inicio > tiempo_actual:
        silencio = np.zeros(int(sr * (inicio - tiempo_actual)))
        audio_total = np.concatenate((audio_total, silencio))
        tiempo_actual = inicio

    if freq:
        onda = generar_onda(freq, duracion, sr)
        audio_total = np.concatenate((audio_total, onda))
        if duracion > 0.02:
            tiempo_actual += duracion

# Asegurarse que la duración final coincida con el input original
expected_duration = librosa.get_duration(y=y, sr=sr)  # y es el audio original cargado
actual_duration = librosa.get_duration(y=audio_total, sr=sr)

if actual_duration < expected_duration:
    padding = np.zeros(int((expected_duration - actual_duration) * sr))
    audio_total = np.concatenate((audio_total, padding))

# Normalizar para evitar clipping
audio_total = audio_total / np.max(np.abs(audio_total))

# Guardar en un archivo WAV
sf.write("reconstruccion.wav", audio_total, sr)
print("Archivo 'reconstruccion.wav' generado correctamente.")

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
        with open("notas_detectadas.json", "w") as f:
            json.dump(notas_json, f, indent=2)
        print("Archivo JSON guardado.")
    else:
        print("No se guardó el archivo JSON.")  

