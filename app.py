from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
JSON_FOLDER = os.path.join(os.getcwd(), "ParteDeJuli", "JsonFiles")
STATIC_FOLDER = os.path.join(os.getcwd(), "static")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Página principal (index.html en la raíz)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Para servir cualquier archivo .html de la raíz (register.html, login.html, etc)
@app.route('/<path:filename>')
def root_files(filename):
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    # Si no existe en raíz, probar en subcarpetas:
    for folder in ['Img', 'static', 'uploads']:
        folder_path = os.path.join(folder, filename)
        if os.path.exists(folder_path):
            return send_from_directory(folder, filename)
    return "Archivo no encontrado", 404

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400
    file = request.files.get('file')
    if file is None or file.filename is None or file.filename == '':
        return jsonify({"error": "Archivo vacío"}), 400

    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Ejecutar tu script con ese mp3
    subprocess.run(["python", "./ParteDeJuli/LeerArchivoYnota.py", filepath], check=True)

    # Generar la imagen con el script de tu amiga
    subprocess.run(["python", "./ParteDeTota/NotasAPartitura.py"], check=True)

    image_name = "resultado.jpg"  # Cambia esto por el nombre REAL generado por el script
    image_path = f"/uploads/{image_name}"
    
    return jsonify({
        "json": f"/json/notas_detectadas.json",
        "imagen": f"/static/partitura.jpeg"
    })

@app.route('/json/<path:filename>')
def download_json(filename):
    return send_from_directory(JSON_FOLDER, filename)

@app.route('/static/<path:filename>')
def get_image(filename):
    return send_from_directory(STATIC_FOLDER, filename)

# Extra: para servir imágenes de /Img/
@app.route('/Img/<path:filename>')
def serve_img(filename):
    return send_from_directory('Img', filename)

# Extra: para servir JS y CSS (Front.css, app.js) si están en raíz
@app.route('/<filename>.js')
def serve_js(filename):
    return send_from_directory('.', filename + '.js')

@app.route('/<filename>.css')
def serve_css(filename):
    return send_from_directory('.', filename + '.css')

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
