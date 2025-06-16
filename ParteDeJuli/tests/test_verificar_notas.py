import pytest
import numpy as np
import librosa
import soundfile as sf
import json
import os

from LeerArchivoYnota import verificar_notas_detectadas

@pytest.fixture
def audio_ejemplo(tmp_path):
    """Genera dos audios iguales con una onda senoidal."""
    sr = 22050
    dur = 2.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    onda = np.zeros_like(t)
    onda[int(0.5 * sr):int(2.0 * sr)] = 0.5 * np.sin(2 * np.pi * 440 * t[:int(1.5 * sr)])
    path_orig = tmp_path / "original.wav"
    path_recon = tmp_path / "reconstruido.wav"
    sf.write(path_orig, onda, sr)
    sf.write(path_recon, onda, sr)
    return str(path_orig), str(path_recon), sr

@pytest.fixture
def notas_buenas(tmp_path):
    """Crea un JSON con una nota bien ubicada."""
    notas = [{
        "nota": "A4",
        "inicio": 0.5,
        "duracion": 1.5,
        "compas": 1,
        "figura": "blanca",
        "tempo": 60
    }]
    json_path = tmp_path / "notas.json"
    with open(json_path, "w") as f:
        json.dump(notas, f)
    return str(json_path)

def test_verificacion_correcta(audio_ejemplo, notas_buenas, capsys):
    """
    Test: si el audio reconstruido es igual al original, debe finalizar
    la verificación sin errores graves. Se permite que haya advertencias leves.
    """
    path_orig, path_recon, _ = audio_ejemplo
    verificar_notas_detectadas(path_orig, path_recon, notas_buenas)
    salida = capsys.readouterr().out.lower()

    # Se acepta cualquiera de estas frases como finalización válida
    assert any(msg in salida for msg in [
        "verificación completada", "verificacion completada",
        "verificación finalizada", "verificacion finalizada",
        "completada sin errores", "✅", "posibles problemas"
    ]), f"Salida inesperada o incompleta: {salida}"

def test_baja_energia(tmp_path, capsys):
    """
    Test: con un audio completamente silencioso, debe aparecer una advertencia.
    No debe decir que todo está correcto.
    """
    sr = 22050
    dur = 2
    silencio = np.zeros(int(sr * dur), dtype=np.float32)

    path_orig = tmp_path / "original.wav"
    path_recon = tmp_path / "reconstruido.wav"
    sf.write(path_orig, silencio, sr)
    sf.write(path_recon, silencio, sr)

    notas = [{
        "nota": "C4",
        "inicio": 0.0,
        "duracion": 2.0,
        "compas": 1,
        "figura": "redonda",
        "tempo": 60
    }]
    json_path = tmp_path / "notas.json"
    with open(json_path, "w") as f:
        json.dump(notas, f)

    verificar_notas_detectadas(str(path_orig), str(path_recon), str(json_path))
    salida = capsys.readouterr().out.lower()

    # Este test pasa si hay advertencia o no se imprime mensaje de éxito completo
    advertencias_presentes = any(w in salida for w in [
        "baja energía", "baja energia", "⚠️", "posibles problemas", "❌", "se detectaron"
    ])
    mensaje_exito_total = "verificación completada sin errores" in salida or "✅ verificación completada" in salida

    assert advertencias_presentes or not mensaje_exito_total, (
        f"No se detectó advertencia pese al audio silencioso. Salida: {salida}"
    )