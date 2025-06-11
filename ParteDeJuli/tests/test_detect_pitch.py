import pytest
import numpy as np
import librosa
from typing import List, Tuple

# Importamos la función que vamos a testear
from LeerArchivoYnota import detect_pitch

# Ruta de ejemplo al archivo .wav
AUDIO_PATH = "Samples/piano-lento.wav"

#Test 1: Comprobar que detect_pitch devuelve una lista de tuplas (t, f)
def test_detect_pitch_returns_valid_format():
    # Cargamos el audio (librosa carga por defecto a 22050 Hz)
    y, sr = librosa.load(AUDIO_PATH, sr=None)
    
    # Ejecutamos la función
    result = detect_pitch(y, sr)

    # Validamos que devuelve una lista
    assert isinstance(result, list), "detect_pitch no devuelve una lista"

    # Validamos que haya al menos 1 resultado
    assert len(result) > 0, "detect_pitch no detectó ningún pitch"

    # Validamos que todos los elementos sean tuplas de 2 elementos (tiempo, frecuencia)
    for item in result:
        assert isinstance(item, tuple), f"Elemento no es una tupla: {item}"
        assert len(item) == 2, f"La tupla no tiene 2 elementos: {item}"
        t, f = item
        assert isinstance(t, (float, int)), f"El tiempo no es numérico: {t}"
        assert isinstance(f, (float, int)), f"La frecuencia no es numérica: {f}"

#Test 2: Comprobar que todas las frecuencias son positivas
def test_detect_pitch_only_positive_frequencies():
    y, sr = librosa.load(AUDIO_PATH, sr=None)
    result = detect_pitch(y, sr)

    # Verificamos que todas las frecuencias detectadas sean > 0
    for _, f in result:
        assert f > 0, f"Se detectó frecuencia no positiva: {f}"