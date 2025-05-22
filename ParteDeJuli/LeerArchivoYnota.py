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

def cargar_audio(filepath, sr=22050):
    """
    Carga un archivo de audio. Si es .mp3 lo convierte a .wav automáticamente.

    Parámetros:
    - filepath: Ruta al archivo de audio
    - sr: Frecuencia de muestreo deseada (por defecto 22050 Hz)

    Devuelve:
    - y: señal de audio como array numpy
    - sr: frecuencia de muestreo
    """
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
    return y, sr

ruta = r"C:\Users\48592310\Downloads\Scorik.github.io\ParteDeJuli\piano-lento.mp3"
y, sr = cargar_audio(ruta)

if not os.path.exists(ruta):
    raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
