import pytest
import numpy as np

# Suponemos que la función está en tu script principal
from LeerArchivoYnota import generate_note_wave

#Test 1: Verifica que la función genera una onda de la duración correcta
def test_generate_note_wave_shape():
    freq = 440.0  # A4
    dur = 1.0     # 1 segundo
    sr = 16000

    wave = generate_note_wave(freq, dur, sr)
    
    # La longitud debe coincidir con duración * sample rate
    expected_len = int(sr * dur)
    assert isinstance(wave, np.ndarray)
    assert wave.shape[0] == expected_len, f"Tamaño incorrecto: {wave.shape[0]} != {expected_len}"
    assert wave.dtype == np.float32, "La onda no está en float32"

#Test 2: Amplitud máxima no debe superar 1.0 ni ser NaN
def test_wave_amplitude_range():
    wave = generate_note_wave(440.0, 1.0)
    max_val = np.max(np.abs(wave))

    assert not np.isnan(max_val), "El valor máximo es NaN"
    assert max_val <= 1.0, f"El valor máximo excede 1.0: {max_val}"

#Test 3: Verifica que se puedan generar notas cortas sin error
@pytest.mark.parametrize("dur", [0.05, 0.1, 0.2])
def test_generate_short_notes(dur):
    wave = generate_note_wave(440.0, dur)
    assert len(wave) > 0, f"Onda vacía para duración {dur}"