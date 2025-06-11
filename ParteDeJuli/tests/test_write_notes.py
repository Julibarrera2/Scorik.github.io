import os
import json
import pytest
from typing import List, Dict
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from LeerArchivoYnota import write_notes_to_json 

#Nota de ejemplo para testear escritura
notas_ejemplo: List[Dict] = [
    {
        "nota": "C4",
        "inicio": 0.0,
        "duracion": 1.0,
        "compas": 1,
        "figura": "negra",
        "tempo": 90
    },
    {
        "nota": "E4",
        "inicio": 1.0,
        "duracion": 1.5,
        "compas": 1,
        "figura": "blanca",
        "tempo": 90
    }
]

#Test de escritura del archivo
def test_write_notes_to_json_crea_archivo(tmp_path):
    # Crear una ruta temporal para no sobrescribir archivos reales
    output_path = tmp_path / "notas_test.json"
    
    # Ejecutar la función
    write_notes_to_json(notas_ejemplo, filename=str(output_path))
    
    # Verificar que el archivo fue creado
    assert os.path.exists(output_path), "El archivo JSON no fue creado"
    
    # Verificar que el contenido coincida
    with open(output_path, "r") as f:
        data = json.load(f)
        assert isinstance(data, list), "El contenido del JSON no es una lista"
        assert data == notas_ejemplo, "El contenido del JSON no coincide con las notas originales"