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
# Visualización (opcional, útil para debugging)
import matplotlib.pyplot as plt
import os
from pydub import AudioSegment
from pydub.utils import which

#Los directorios de ffmpeg del .exe para que funciones
AudioSegment.converter = which("ffmpeg") or r"c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = which("ffprobe") or r"c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

#Ruta del archivo
ruta = r"c:\Users\fb050\OneDrive\Desktop\Scorik.github.io\ParteDeJuli\piano-lento.mp3"

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

#DETECTAR PITCH
def detectar_pitch(y, sr, step_size_ms=10, threshold=0.8):
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
        if c >= threshold:
            pitches_filtradas.append((t, f))  # tiempo y frecuencia
    
    #printeamois la informacion
    print(f"Se detectaron {len(pitches_filtradas)} pitches con confianza > {threshold}.")
    return pitches_filtradas

#Ejecutar la funcion completita
y, sr, ruta_wav = cargar_audio(ruta)
pitches = detectar_pitch(y, sr)
print("Primeros 10 pitches:", pitches[:10])  # Mostrar algunos resultados

