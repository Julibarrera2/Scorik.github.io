import pytest
from typing import List, Dict, Tuple

# Suponemos que la función está definida en el archivo principal
from LeerArchivoYnota import group_pitches_to_notes

# Diccionario de prueba simple con solo 3 notas
notas_dict = {
    'A4': 440.0,
    'B4': 493.88,
    'C5': 523.25
}

#Test 1: Devuelve una lista de diccionarios con claves correctas
def test_group_notes_format():
    pitch_data = [
        (0.00, 440.0),  # A4
        (0.10, 440.0),
        (0.20, 493.88),  # B4
        (0.30, 493.88),
        (0.50, 523.25)   # C5
    ]
    tempo = 120  # BPM
    
    notas = group_pitches_to_notes(pitch_data, tempo, notas_dict)

    # Asegura que la salida sea lista de diccionarios
    assert isinstance(notas, list), "La salida no es una lista"
    assert all(isinstance(n, dict) for n in notas), "La lista no contiene diccionarios"

    # Asegura que cada diccionario tenga las claves correctas
    for nota in notas:
        assert all(k in nota for k in ["nota", "inicio", "duracion", "compas", "figura", "tempo"]), \
            f"Faltan claves en una nota: {nota}"

#Test 2: Verifica que se ignoren notas cortas menores al umbral
def test_group_notes_filters_short_notes():
    pitch_data = [
        (0.00, 440.0),
        (0.02, 493.88),  # Solo 0.02s de duración, debería ser descartada si MIN_DURACION_NOTA > 0.1
        (0.50, 523.25)
    ]
    tempo = 100
    notas = group_pitches_to_notes(pitch_data, tempo, notas_dict)

    # Solo deberían quedar 2 notas como máximo
    assert len(notas) <= 2, f"Demasiadas notas detectadas: {len(notas)}"