# NotasAPartitura.py - VERSIÓN SIN FLASK

from music21 import stream, note, instrument, environment
import os
import json
import subprocess
from time import time as timestamp

# Poner tu ruta a MuseScore aquí:
MUSESCORE_PATH = r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe"

# Dónde está el JSON:
JSON_PATH = os.path.join("JsonFiles", "notas_detectadas.json")

# Dónde guardar los archivos:
STATIC_FOLDER = "static"
os.makedirs(STATIC_FOLDER, exist_ok=True)

figura_a_duracion = {
    'redonda': 4.0,
    'blanca': 2.0,
    'negra': 1.0,
    'corchea': 0.5,
    'semicorchea': 0.25,
    'fusa': 0.125,
    'semifusa': 0.0625
}

def main():
    # Leer JSON
    if not os.path.exists(JSON_PATH):
        print("No se encontró el archivo de notas:", JSON_PATH)
        return
    with open(JSON_PATH, "r") as f:
        notas = json.load(f)
    if not notas:
        print("No se encontraron notas en el JSON.")
        return

    # Crear partitura
    score = stream.Score()
    part = stream.Part()
    part.insert(0, instrument.Violin())
    for n in notas:
        try:
            nombre_nota = n['nota']
            figura = n.get('figura', 'negra').lower()
            duracion = figura_a_duracion.get(figura, 1.0)
            nueva_nota = note.Note(nombre_nota)
            nueva_nota.quarterLength = duracion
            part.append(nueva_nota)
        except Exception as e:
            print(f"Error procesando nota: {n} ({e})")
    score.insert(0, part)

    ts = int(timestamp())
    base_name = f'partitura_{ts}'
    xml_path = os.path.join(STATIC_FOLDER, f"{base_name}.musicxml")
    png_output = os.path.join(STATIC_FOLDER, f"{base_name}.png")

    # Guardar MusicXML
    score.write('musicxml', fp=xml_path)

    # Llamar MuseScore para generar PNG
    print("Llamando MuseScore...")
    result = subprocess.run([
        MUSESCORE_PATH,
        xml_path,
        '-o',
        png_output
    ], capture_output=True, text=True)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    if result.returncode == 0 and os.path.exists(png_output):
        print("✅ Imagen generada:", png_output)
    else:
        print("❌ Error al generar imagen PNG. Revisá los mensajes de error arriba.")
        if not os.path.exists(MUSESCORE_PATH):
            print("La ruta a MuseScore no existe. Chequeá la variable MUSESCORE_PATH.")

if __name__ == "__main__":
    main()
# Nota: Este script no usa Flask, es una versión standalone para generar la partitura a partir del JSON.