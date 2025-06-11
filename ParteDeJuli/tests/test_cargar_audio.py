import pytest
import os
from LeerArchivoYnota import load_and_preprocess_audio

def test_load_and_preprocess_audio():
    ruta = "Samples/piano-lento.wav"  # Ruta relativa o absoluta
    y, sr, path = load_and_preprocess_audio(ruta)
    
    assert isinstance(y, (list, tuple, type(y))), "Debe devolver un array"
    assert isinstance(sr, int), "Debe devolver el sample rate como entero"
    assert os.path.exists(path), "El archivo convertido debe existir"
    assert y is not None and len(y) > 0, "La señal de audio no debe estar vacía"

