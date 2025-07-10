# NotasAPartitura.py - VERSIÓN TOLERANTE A .musicxml/.xml

from music21 import stream, note, instrument
import os
import json
import subprocess
from time import time as timestamp

MUSESCORE_PATH = r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe"
JSON_PATH = os.path.join("JsonFiles", "notas_detectadas.json")
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
    if not os.path.exists(JSON_PATH):
        print("No se encontró el archivo de notas:", JSON_PATH)
        return
    with open(JSON_PATH, "r") as f:
        notas = json.load(f)
    if not notas:
        print("No se encontraron notas en el JSON.")
        return

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
    xml_path_alt = os.path.join(STATIC_FOLDER, f"{base_name}.xml")
    png_output = os.path.join(STATIC_FOLDER, f"{base_name}.png")

    # Guardar MusicXML (puede terminar siendo .xml)
    score.write('musicxml', fp=xml_path)
    print(f"XML generado: {xml_path}  | Existe: {os.path.exists(xml_path)}")
    if not os.path.exists(xml_path):
        # ¿Lo generó como .xml?
        if os.path.exists(xml_path_alt):
            print(f"El archivo se guardó como: {xml_path_alt}")
            xml_path = xml_path_alt
        else:
            print("ERROR: No se generó el archivo MusicXML, aborto.")
            return

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
