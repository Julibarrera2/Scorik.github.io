from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import json
import sys
import shutil


app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
JSON_FOLDER = os.path.join(os.getcwd(), "ParteDeJuli", "JsonFiles")
STATIC_FOLDER = os.path.join(os.getcwd(), "static")
STATIC_TEMP_FOLDER = os.path.join(STATIC_FOLDER, "temp")  # << NUEVO: carpeta temporal
PARTITURAS_USER_FOLDER = os.path.join(os.getcwd(), "partituras_usuario")  # << NUEVO: carpeta de partituras guardadas
USERS_FILE = os.path.join(os.getcwd(), "usuarios.json")
PYTHON_EXEC = sys.executable

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(STATIC_TEMP_FOLDER, exist_ok=True)
os.makedirs(PARTITURAS_USER_FOLDER, exist_ok=True)


def cargar_usuarios():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

#Guardar el usuario en el archivo JSON
# Si el archivo no existe, se crea uno nuevo
def guardar_usuarios(usuarios):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=2)

#Lo de registrer y login
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
    
    # Limpiar archivos temporales anteriores
    for f in os.listdir(STATIC_TEMP_FOLDER):
        try:
            os.remove(os.path.join(STATIC_TEMP_FOLDER, f))
        except Exception:
            pass

    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Ejecutar el script de notas con path correcto
    subprocess.run([PYTHON_EXEC, "./ParteDeJuli/LeerArchivoYnota.py", filepath, STATIC_TEMP_FOLDER], check=True)

    # Buscar último PNG y XML TEMPORAL
    temp_pngs = [f for f in os.listdir(STATIC_TEMP_FOLDER) if f.endswith(".png")]
    temp_xmls = [f for f in os.listdir(STATIC_TEMP_FOLDER) if f.endswith(".xml") or f.endswith(".musicxml")]

    if not temp_pngs or not temp_xmls:
        return jsonify({"error": "No se generó imagen"}), 500

    return jsonify({
        "imagen": f"/static/temp/{temp_pngs[0]}",
        "xml": f"/static/temp/{temp_xmls[0]}" if temp_xmls else None
    })

@app.route('/save_partitura', methods=['POST'])
def save_partitura():
    # ======== NUEVA RUTA PARA GUARDAR DEFINITIVO ========
    data = request.json
    usuario = data.get('usuario')
    nombre = data.get('nombre', 'partitura')
    imagen = data.get('imagen')  # Ruta relativa tipo "/static/temp/partitura_xxxxx.png"
    xml = data.get('xml')  # Puede ser None

    if not (usuario and imagen):
        return jsonify({'error': 'Faltan datos'}), 400

    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)
    os.makedirs(user_dir, exist_ok=True)

    # Copiar archivos temp a carpeta del usuario (como definitivo)
    def mover_archivo(rel_path, nombre_destino):
        if not rel_path:
            return None
        src = os.path.join('.', rel_path.lstrip('/'))
        if os.path.exists(src):
            ext = os.path.splitext(src)[1]
            dst = os.path.join(user_dir, nombre_destino + ext)
            shutil.move(src, dst)
            return dst
        return None

    imagen_final = mover_archivo(imagen, nombre)
    xml_final = mover_archivo(xml, nombre) if xml else None

    # Limpiar TEMP folder (borrar todo)
    for f in os.listdir(STATIC_TEMP_FOLDER):
        try:
            os.remove(os.path.join(STATIC_TEMP_FOLDER, f))
        except Exception:
            pass

    return jsonify({'success': True, 'message': 'Partitura guardada', 'ruta': imagen_final})

@app.route('/static/temp/<path:filename>')
def get_temp_image(filename):
    return send_from_directory(STATIC_TEMP_FOLDER, filename)

@app.route('/partituras_usuario/<usuario>/<filename>')
def get_user_partitura(usuario, filename):
    # Para servir partituras guardadas
    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)
    return send_from_directory(user_dir, filename)

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

@app.route('/api/partituras_usuario/<usuario>')
def api_partituras_usuario(usuario):
    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)
    if not os.path.exists(user_dir):
        return jsonify([])
    partituras = []
    for fname in os.listdir(user_dir):
        if fname.endswith('.png'):
            base = os.path.splitext(fname)[0]
            # Buscamos el .xml asociado (si existe)
            xml = None
            for ext in ('.xml', '.musicxml'):
                xml_path = os.path.join(user_dir, base + ext)
                if os.path.exists(xml_path):
                    xml = f"/partituras_usuario/{usuario}/{base + ext}"
                    break
            partituras.append({
                "nombre": base,
                "imagen": f"/partituras_usuario/{usuario}/{fname}",
                "xml": xml
            })
    return jsonify(partituras)

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
