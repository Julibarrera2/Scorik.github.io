from flask import Flask, request, jsonify
from music21 import stream, note, instrument, environment
import os
import subprocess
import time
from time import time as timestamp

us = environment.UserSettings()
us['musicxmlPath'] = r'C:\Program Files\MuseScore 3\bin\MuseScore3.exe'

app = Flask(__name__)

figura_a_duracion = {
    'redonda': 4.0,
    'blanca': 2.0,
    'negra': 1.0,
    'corchea': 0.5,
    'semicorchea': 0.25,
    'fusa': 0.125,
    'semifusa': 0.0625
}

@app.route('/generar_partitura', methods=['POST'])
def generar_partitura():
    notas = request.json.get('notas', [])

    if not notas:
        return jsonify({'error': 'No se recibieron notas'}), 400

    score = stream.Score()
    part = stream.Part()
    part.insert(0, instrument.Violin())

    for n in notas:
        try:
            nombre_nota = n['nota']
            figura = n.get('figura', 'negra').lower()
            duracion = figura_a_duracion.get(figura)

            if duracion is None:
                return jsonify({'error': f'Figura desconocida: {figura}'}), 400

            nueva_nota = note.Note(nombre_nota)
            nueva_nota.quarterLength = duracion
            part.append(nueva_nota)
        except Exception as e:
            return jsonify({'error': f'Error procesando nota: {n}. Detalle: {str(e)}'}), 400

    score.insert(0, part)

    try:
        if not os.path.exists("static"):
            os.makedirs("static")

        ts = int(timestamp())
        base_name = f'partitura_{ts}'
        xml_path = f'static/{base_name}.musicxml'
        png_output = f'static/{base_name}.png'
        musescore_path = r'C:\Program Files\MuseScore 3\bin\MuseScore3.exe'

        score.write('musicxml', fp=xml_path)

        # Borrar versiones previas si existen
        for f in os.listdir("static"):
            if f.startswith(base_name) and f.endswith(".png"):
                os.remove(os.path.join("static", f))

        # Ejecutar MuseScore con nombre de salida especificado
        result = subprocess.run([
            musescore_path,
            xml_path,
            '-o',
            png_output
        ], capture_output=True, text=True)

        print("📤 STDOUT:", result.stdout)
        print("❌ STDERR:", result.stderr)
        time.sleep(0.5)

        archivos_static = os.listdir("static")
        print("📁 Archivos en static/:", archivos_static)

        # Buscar el PNG que coincida con el prefijo
        imagen_generada = None
        for f in archivos_static:
            if f.startswith(base_name) and f.endswith(".png"):
                imagen_generada = f
                break

        if result.returncode != 0:
            raise Exception(f"MuseScore falló: {result.stderr}")

        if not imagen_generada:
            raise Exception("MuseScore no generó una imagen con el nombre esperado.")

    except Exception as e:
        print("❌ ERROR al generar imagen:", str(e))
        return jsonify({'error': f'Error al generar la imagen con MuseScore: {str(e)}'}), 500

    return jsonify({
        'mensaje': 'Partitura generada correctamente',
        'img_url': f'/static/{imagen_generada}?ts={ts}'
    })

if __name__ == '__main__':
    app.run(debug=True)
