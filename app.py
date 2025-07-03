from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import os
import subprocess

app = Flask(__name__)

# Configuración de rutas
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
JSON_FOLDER = os.path.join(os.getcwd(), "ParteDeJuli", "JsonFiles")
IMAGE_FOLDER = os.path.join(os.getcwd(), "static")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return send_file("index.html")  # tu página principal

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Archivo vacío"}), 400

    UPLOAD_FOLDER = "uploads"
    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Ejecutar tu script con ese mp3
    subprocess.run(["python", "./ParteDeJuli/LeerArchivoYnota.py", filepath], check=True)

    # Generar la imagen con el script de tu amiga
    subprocess.run(["python", "./ParteDeTota/NotasAPartitura.py"], check=True)

    # Retornar rutas para que el front las muestre
    return jsonify({
        "json": f"/json/notas_detectadas.json",
        "imagen": f"/static/partitura.jpeg"
    })

@app.route('/json/<path:filename>')
def download_json(filename):
    return send_from_directory(JSON_FOLDER, filename)

@app.route('/static/<path:filename>')
def get_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)

#¿Qué hace esto?
# Va a servir tu página HTML (index.html que está en templates)
# Permite subir un .mp3 vía POST a /upload.
# Guarda el archivo, corre tu pipeline:
# LeerArchivoYnota.py genera el JSON en ParteDeJuli/JsonFiles.
# NotasAPartitura.py genera el .jpeg en static
# Devuelve un JSON con las rutas:
# json
#"json": "/json/notas_detectadas.json",
#"imagen": "/static/partitura.jpeg"
# Permite descargar el JSON y ver la imagen desde las rutas especificadas.
#<img src="/static/partitura.jpeg">
# <a href="/json/notas_detectadas.json" download>Descargar JSON</a>
