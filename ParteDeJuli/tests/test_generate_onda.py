import pytest
import numpy as np
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Importamos la función a testear
from LeerArchivoYnota import generate_note_wave

#Test 1: Verifica que devuelve un array numpy de tamaño correcto
def test_generate_note_wave_output_format():
    freq = 440.0  # A4
    dur = 1.0     # 1 segundo
    sr = 16000    # frecuencia de muestreo
    wave = generate_note_wave(freq, dur, sr)

    # Verifica que la salida sea un numpy array
    assert isinstance(wave, np.ndarray), "La salida no es un ndarray"
    
    # Verifica que la forma (shape) sea la esperada
    expected_length = int(sr * dur)
    assert wave.shape == (expected_length,), f"Longitud incorrecta: {wave.shape} vs {expected_length}"

#Test 2: Verifica que no haya NaNs ni infs
def test_generate_note_wave_no_nans_or_infs():
    wave = generate_note_wave(440.0, 1.0)

    assert not np.any(np.isnan(wave)), "Hay valores NaN en la onda"
    assert not np.any(np.isinf(wave)), "Hay valores infinitos en la onda"

#Test 3: Verifica que los valores estén dentro del rango esperado
def test_generate_note_wave_amplitude_range():
    wave = generate_note_wave(440.0, 1.0)
    max_val = np.max(np.abs(wave))
    
    assert max_val <= 1.0, f"La amplitud excede 1.0: {max_val}"