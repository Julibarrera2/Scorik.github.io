from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import json
import sys


app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
JSON_FOLDER = os.path.join(os.getcwd(), "ParteDeJuli", "JsonFiles")
STATIC_FOLDER = os.path.join(os.getcwd(), "static")
USERS_FILE = os.path.join(os.getcwd(), "usuarios.json")
PYTHON_EXEC = sys.executable

def cargar_usuarios():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def guardar_usuarios(usuarios):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=2)

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({'success': False, 'message': 'Faltan datos'}), 400

    usuarios = cargar_usuarios()
    if any(u['email'] == email for u in usuarios):
        return jsonify({'success': False, 'message': 'Usuario ya existe'}), 400

    usuarios.append({'email': email, 'password': password})
    guardar_usuarios(usuarios)
    return jsonify({'success': True, 'message': 'Usuario registrado correctamente'})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    usuarios = cargar_usuarios()
    user = next((u for u in usuarios if u['email'] == email and u['password'] == password), None)
    if user:
        return jsonify({'success': True, 'message': 'Login exitoso'})
    else:
        return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos'}), 401

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Página principal (index.html en la raíz)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

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

    # Ejecutar el script de notas con path correcto
    subprocess.run([PYTHON_EXEC, "./ParteDeJuli/LeerArchivoYnota.py", filepath], check=True)
    # Ejecutar script de partitura
    subprocess.run(["python", "./ParteDeTota/NotasAPartitura.py"], check=True)

    # Buscar último PNG de partitura en /static
    static_files = [f for f in os.listdir(STATIC_FOLDER) if f.startswith("partitura_") and f.endswith(".png")]
    static_files.sort(key=lambda f: os.path.getmtime(os.path.join(STATIC_FOLDER, f)), reverse=True)
    image_name = static_files[0] if static_files else None

    if not image_name:
        return jsonify({"error": "No se generó imagen"}), 500

    return jsonify({
        "json": f"/json/notas_detectadas.json",
        "imagen": f"/static/{image_name}"
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

# --- ESTA RUTA VA ÚLTIMA ---
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

if __name__ == '__main__':
    app.run(debug=True)
