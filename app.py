from flask import Flask, request, jsonify, send_from_directory, session, Response
import os
import subprocess
import json
import sys
import shutil
import time 
import uuid
from google.cloud import storage
from urllib.parse import quote, unquote
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cambia_esta_clave')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@app.before_request
def _force_cookie_flags():
    app.config['SESSION_COOKIE_SECURE'] = True


# Configuración de rutas y carpetas

TMP_BASE = '/tmp/scorik'
ROOT_DIR = os.getcwd()

JSON_FOLDER = os.path.join(ROOT_DIR, "ParteDeJuli", "JsonFiles")
UPLOAD_FOLDER = os.path.join(TMP_BASE, "uploads")
STATIC_TEMP_FOLDER = os.path.join(TMP_BASE, "static_temp")        # imágenes/temp
PARTITURAS_USER_FOLDER = os.path.join(TMP_BASE, "partituras_usuario") # biblioteca usuario
PROGRESS_FOLDER = os.path.join(TMP_BASE, "progress")
USERS_FILE = os.path.join(TMP_BASE, "usuarios.json") 

PYTHON_EXEC = sys.executable

PARTITURAS_BUCKET = os.environ.get("PARTITURAS_BUCKET")
USERS_BUCKET = os.environ.get('USERS_BUCKET')
USERS_BLOB   = os.environ.get('USERS_BLOB', 'usuarios.json')


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_TEMP_FOLDER, exist_ok=True)
os.makedirs(PARTITURAS_USER_FOLDER, exist_ok=True)
os.makedirs(PROGRESS_FOLDER, exist_ok=True) # carpeta de progreso

# Crear solo las carpetas de ESCRITURA
for p in (TMP_BASE, UPLOAD_FOLDER, STATIC_TEMP_FOLDER, PARTITURAS_USER_FOLDER, PROGRESS_FOLDER):
    os.makedirs(p, exist_ok=True)

PYTHON_EXEC = sys.executable

def _gcs_client():
    return storage.Client()

def gcs_upload(bucket_name, dst_path, local_path, content_type=None):
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dst_path)
    blob.upload_from_filename(local_path, content_type=content_type)
    return True

def gcs_list(bucket_name, prefix):
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    return list(bucket.list_blobs(prefix=prefix))

def gcs_download_bytes(bucket_name, path):
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    return blob.download_as_bytes()

def cargar_usuarios():
    if USERS_BUCKET:
        try:
            client = _gcs_client()
            bucket = client.bucket(USERS_BUCKET)
            blob = bucket.blob(USERS_BLOB)
            if not blob.exists(client):    # si aún no existe, lista vacía
                return []
            data = blob.download_as_text(encoding='utf-8')
            return json.loads(data or '[]')
        except Exception as e:
            print("WARN cargar_usuarios GCS:", e, file=sys.stderr)
            return []
    # Si no hay bucket, cargar localmente
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
    if USERS_BUCKET:
        try:
            client = _gcs_client()
            bucket = client.bucket(USERS_BUCKET)
            blob = bucket.blob(USERS_BLOB)
            blob.upload_from_string(json.dumps(usuarios, indent=2), content_type='application/json')
            return
        except Exception as e:
            print("ERROR guardar_usuarios GCS:", e, file=sys.stderr)
    # Si hay error, guardar localmente de todas formas
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=2)

# Función para establecer el progreso del usuario
def set_progress(usuario, msg):
    if not usuario:
        usuario = "anon"
    path = os.path.join(PROGRESS_FOLDER, f"{usuario}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"msg": msg}, f)

# Ruta para obtener el progreso del usuario
@app.route('/api/progress/<usuario>')
def api_progress(usuario):
    if not usuario:
        usuario = "anon"
    path = os.path.join(PROGRESS_FOLDER, f"{usuario}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"msg": "Convirtiendo el audio..."})

# Progreso SIN usuario → usa "anon"
@app.route('/api/progress/', defaults={'usuario': 'anon'})
def api_progress_default(usuario):
    return api_progress(usuario)

#Lo de registrer y login
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({'success': False, 'message': 'Faltan datos'}), 400
    usuarios = cargar_usuarios()
    if any(u['email'] == email for u in usuarios):
        return jsonify({'success': False, 'message': 'Usuario ya existe'}), 400
    usuarios.append({'email': email, 'password': password})
    guardar_usuarios(usuarios)
    # deja cookie de sesión ya logueado
    session['user_email'] = email
    return jsonify({'success': True, 'message': 'Usuario registrado correctamente'})

app.permanent_session_lifetime = timedelta(days=30)
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    usuarios = cargar_usuarios()
    user = next((u for u in usuarios if u['email'] == email and u['password'] == password), None)
    if user:
        session.permanent = True
        session['user_email'] = email
        return jsonify({'success': True, 'message': 'Login exitoso'})
    else:
        return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos'}), 401

@app.route('/api/session')
def api_session():
    email = session.get('user_email')
    if email:
        return jsonify({'logged_in': True, 'email': email})
    else:
        return jsonify({'logged_in': False}), 401
    
@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_email', None)
    return jsonify({'success': True})

# Página principal (index.html en la raíz)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # --- 1. Tomar usuario del FormData (si no, poné "anon") ---
        usuario = request.form.get('usuario', 'anon') or 'anon'
        set_progress(usuario, "Convirtiendo el audio...")

        if 'file' not in request.files:
            set_progress(usuario, "Error: No se envió archivo")
            return jsonify({"error": "No se envió archivo"}), 400

        file = request.files.get('file')
        if not file or not file.filename:
            set_progress(usuario, "Error: Archivo vacío")
            return jsonify({"error": "Archivo vacío"}), 400

        # === subcarpeta de trabajo por request ===
        req_id   = f"{usuario}_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        work_dir = os.path.join(STATIC_TEMP_FOLDER, req_id)
        os.makedirs(work_dir, exist_ok=True)

        # Guardar el MP3 en uploads (opcional) o en work_dir
        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        set_progress(usuario, "Audio cargado correctamente.")
        set_progress(usuario, "Detectando notas...")

        # Acá deberías modificar LeerArchivoYnota.py (o llamar por partes) para poder actualizar la barra entre pasos,
        # pero si no lo podés dividir, simplemente llamá el script externo y actualizá después:
        # Ejecutar script y capturar salida
        # Ejecutar tu script apuntando la salida a work_dir
        def separate_with_spleeter(input_path: str, out_dir: str) -> str:
            os.makedirs(out_dir, exist_ok=True)
            spleeter_bin = os.environ.get("SPLEETER_BIN", "spleeter")  # <— usa la ENV
            cmd = [spleeter_bin, "separate", "-p", "spleeter:2stems", "-o", out_dir, input_path]
            subprocess.run(cmd, check=True)
            base = os.path.splitext(os.path.basename(input_path))[0]
            instrumental = os.path.join(out_dir, base, "accompaniment.wav")
            return instrumental if os.path.exists(instrumental) else input_path
    
        set_progress(usuario, "Separando instrumentos...")
        try:
            stem_path = separate_with_spleeter(filepath, work_dir)
            print("Usando stem:", stem_path, file=sys.stderr)
        except Exception as e:
            print("Fallo separacion, uso original:", e, file=sys.stderr)
            stem_path = filepath

        set_progress(usuario, "Detectando notas...")
        proc = subprocess.run(
            [PYTHON_EXEC, "./ParteDeJuli/LeerArchivoYnota.py", stem_path, work_dir],
            check=True, capture_output=True, text=True
        )
        set_progress(usuario, "Generando imagen ...")

        # Buscar PNG y XML en toda la carpeta (subcarpetas incl.)
        # --- helper para encontrar la salida (con subcarpetas) ---
        IMG_EXTS = ('.png', '.jpg', '.jpeg', '.svg')
        XML_EXTS = ('.xml', '.musicxml')

        def find_outputs(base_dir):
            img, xml = None, None
            for root, _, files in os.walk(base_dir):
                for f in files:
                    fl = f.lower()
                    if (not img) and fl.endswith(IMG_EXTS):
                        img = os.path.join(root, f)
                    if (not xml) and fl.endswith(XML_EXTS):
                        xml = os.path.join(root, f)
                if img and xml:
                    return img, xml
            return img, xml

        # Reintentar hasta 8s por si el script escribe al final
        img_path, xml_path = None, None
        for _ in range(16):
            img_path, xml_path = find_outputs(work_dir)
            if img_path:
                break
            time.sleep(0.5)

        if not img_path:
            tree = []
            for root, _, files in os.walk(work_dir):
                tree.append({"dir": root, "files": files})
            print("Contenido de work_dir:", tree)
            set_progress(usuario, "Error: No se generó imagen")
            return jsonify({"error": "No se generó imagen", "tree": tree}), 500

        # NO mover los archivos fuera: servilos desde la subcarpeta
        # /static/temp/<req_id>/<archivo>
        def to_url(p):
            rel = os.path.relpath(p, STATIC_TEMP_FOLDER).replace("\\", "/")
            return "/static/temp/" + rel

        img_url = to_url(img_path)
        xml_url = to_url(xml_path) if xml_path else None

        set_progress(usuario, "Imagen generada")
        return jsonify({"imagen": img_url, "xml": xml_url})

    except subprocess.CalledProcessError as e:
        print("ERROR ejecutando script:\n", e.stdout, "\nSTDERR:\n", e.stderr, file=sys.stderr)
        set_progress(usuario, "Error: procesamiento")
        return jsonify({"error": "Fallo el script de conversión", "stdout": e.stdout, "stderr": e.stderr}), 500
    except Exception:
        app.logger.exception("Fallo en /upload")
        set_progress(request.form.get('usuario','anon'), "Error: procesamiento")
        return jsonify({"error": "fallo servidor"}), 500
    
@app.route('/save_partitura', methods=['POST'])
def save_partitura():
    # ======== NUEVA RUTA PARA GUARDAR DEFINITIVO ========
    data = request.get_json(silent=True) or {}
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

        if rel_path.startswith('/static/temp/'):
            rel_sub = rel_path[len('/static/temp/'):]           # puede incluir subcarpeta
            src = os.path.join(STATIC_TEMP_FOLDER, rel_sub)
        else:
            src = os.path.join('.', rel_path.lstrip('/'))

        if os.path.exists(src):
            ext = os.path.splitext(src)[1]
            dst = os.path.join(user_dir, nombre_destino + ext)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)

            # si quedó la subcarpeta vacía, la limpiamos
            try:
                subdir = os.path.dirname(src)
                if subdir.startswith(STATIC_TEMP_FOLDER):
                    if not os.listdir(subdir):
                        os.rmdir(subdir)
            except: pass

            return dst
        return None

    imagen_final = mover_archivo(imagen, nombre)
    xml_final    = mover_archivo(xml, nombre) if xml else None

    # si hay bucket -> subir
    img_url = None
    if PARTITURAS_BUCKET and imagen_final:
        gcs_key = f"{usuario}/{os.path.basename(imagen_final)}"
        gcs_upload(PARTITURAS_BUCKET, gcs_key, imagen_final, content_type="image/png")
        # opcional: subimos xml también
        if xml_final and os.path.exists(xml_final):
            gcs_upload(PARTITURAS_BUCKET, f"{usuario}/{os.path.basename(xml_final)}", xml_final, content_type="application/xml")
        # borramos local para no llenar /tmp
        try:
            os.remove(imagen_final)
        except: pass
        if xml_final:
            try: os.remove(xml_final)
            except: pass
        # URL interna que sirve desde GCS (ver ruta más abajo)
        img_url = f"/gcs_partituras/{usuario}/{os.path.basename(imagen_final)}"
    else:
        # modo local (/tmp) – mantiene compatibilidad
        if imagen_final:
            img_url = f"/partituras_usuario/{usuario}/{os.path.basename(imagen_final)}"

    # limpiar static_temp
    for f in os.listdir(STATIC_TEMP_FOLDER):
        try: os.remove(os.path.join(STATIC_TEMP_FOLDER, f))
        except Exception: pass

    return jsonify({'success': True, 'message': 'Partitura guardada', 'ruta': img_url})

@app.route('/gcs_partituras/<usuario>/<filename>')
def gcs_partitura(usuario, filename):
    if not PARTITURAS_BUCKET:
        return "Bucket no configurado", 404
    try:
        usuario = unquote(usuario)
        path = f"{usuario}/{filename}"
        data = gcs_download_bytes(PARTITURAS_BUCKET, path)
        # mimetype simple
        low = filename.lower()
        if   low.endswith(".png"):   mime = "image/png"
        elif low.endswith((".jpg",".jpeg")): mime = "image/jpeg"
        elif low.endswith((".xml",".musicxml")): mime = "application/xml"
        elif low.endswith(".svg"): mime = "image/svg+xml"
        else: mime = "application/octet-stream"
        return Response(data, mimetype=mime)
    except Exception as e:
        print("ERROR sirviendo GCS:", e, file=sys.stderr)
        return "No encontrado", 404

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
    return send_from_directory(STATIC_TEMP_FOLDER, filename)

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
    # Modo GCS (recomendado)
    if PARTITURAS_BUCKET:
        try:
            blobs = gcs_list(PARTITURAS_BUCKET, prefix=f"{usuario}/")
        except Exception as e:
            print("ERROR listando GCS:", e, file=sys.stderr)
            return jsonify([])

        por_base = {}
        for b in blobs:
            fname = os.path.basename(b.name)
            base, ext = os.path.splitext(fname)
            if not base:
                continue
            por_base.setdefault(base, {"nombre": base, "imagen": None, "xml": None})

            user_q = quote(usuario, safe='')
            if ext.lower() == ".png":
                por_base[base]["imagen"] = f"/gcs_partituras/{user_q}/{fname}"
            if ext.lower() in (".xml", ".musicxml"):
                por_base[base]["xml"] = f"/gcs_partituras/{user_q}/{fname}"

        return jsonify([v for v in por_base.values() if v["imagen"]])

    # Modo local (/tmp) – compatibilidad
    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)
    if not os.path.exists(user_dir):
        return jsonify([])
    partituras = []
    for fname in os.listdir(user_dir):
        if fname.endswith('.png'):
            base = os.path.splitext(fname)[0]
            xml = None
            for ext in ('.xml', '.musicxml'):
                if os.path.exists(os.path.join(user_dir, base + ext)):
                    xml = f"/partituras_usuario/{usuario}/{base + ext}"
                    break
            partituras.append({
                "nombre": base,
                "imagen": f"/partituras_usuario/{usuario}/{fname}",
                "xml": xml
            })
    return jsonify(partituras)

@app.route('/healthz')
def healthz():
    return "ok", 200

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
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False)
