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
from werkzeug.utils import secure_filename
from music21 import environment
import soundfile as sf
import numpy as np
import onnxruntime as ort


us = environment.UserSettings()
us['musicxmlPath'] = '/usr/local/bin/mscore3-cli'
us['musescoreDirectPNGPath'] = '/usr/local/bin/mscore3-cli'

def convert_to_wav_if_needed(filepath):
    """
    Convierte un MP3 a WAV usando FFmpeg dentro de Cloud Run.
    Retorna la ruta del WAV resultante.
    """
    base, ext = os.path.splitext(filepath)
    ext = ext.lower()

    # Si ya es WAV → no hacemos nada
    if ext == ".wav":
        return filepath

    wav_path = base + ".wav"

    # Ejecutar FFmpeg en Cloud Run
    cmd = [
        "ffmpeg",
        "-y",           # overwrite
        "-i", filepath,
        "-ac", "1",     # mono
        "-ar", "44100", # sample rate estándar
        wav_path
    ]

    print("Convirtiendo a WAV:", filepath, "->", wav_path)
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    return wav_path

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


# Crear solo las carpetas de ESCRITURA
for p in [TMP_BASE, UPLOAD_FOLDER, STATIC_TEMP_FOLDER, PARTITURAS_USER_FOLDER, PROGRESS_FOLDER]:
    os.makedirs(p, exist_ok=True)

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
        # ================================================================
        # 1) Datos del formulario
        # ================================================================
        usuario = request.form.get('usuario', 'anon') or 'anon'
        instrumento = request.form.get('instrumento', 'piano')

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        set_progress(usuario, "Convirtiendo el audio...")

        # ================================================================
        # 2) Validación del archivo
        # ================================================================
        if 'file' not in request.files:
            return jsonify({"error": "No se envió archivo"}), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({"error": "Archivo vacío"}), 400

        # ================================================================
        # 3) Carpeta temporal de trabajo
        # ================================================================
        req_id = f"{usuario}_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        work_dir = os.path.join(STATIC_TEMP_FOLDER, req_id)
        os.makedirs(work_dir, exist_ok=True)

        # Guardar MP3/WAV original
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        # 🔥 Convertir MP3 → WAV antes de pasar a MDX
        filepath = convert_to_wav_if_needed(filepath)


        # ================================================================
        # 4) SEPARACIÓN DE INSTRUMENTOS CON AUDIO-SEPARATOR (UVR-MDX)
        # ================================================================
        from audio_separator.separator import Separator

        set_progress(usuario, "Separando instrumentos (MDX)...")

        MODELS_DIR = os.path.join(os.getcwd(), "models")

        MODEL_MAP = {
            "guitarra": "UVR-MDX-NET-Inst_1.onnx",
            "piano":    "UVR-MDX-NET-Inst_HQ_2.onnx",
            "violin":   "UVR_MDXNET_3_9662.onnx",
        }

        model_filename = MODEL_MAP.get(instrumento)
        if not model_filename:
            return jsonify({"error": "Instrumento inválido"}), 400

        # En audio-separator 0.9.0, audio_file_path es argumento obligatorio del constructor
        # Los parámetros use_cuda y use_coreml NO existen en esta versión
        sep = Separator(
            audio_file_path=filepath,
            model_file_dir=MODELS_DIR,
            output_format="wav"
        )

        sep.load_model(model_filename)

        # Compat shim: probar varias firmas de separate(...) según versión
        outputs = None
        try:
            # firma 0.9.0: separate() sin argumentos (ya pasó filepath al constructor)
            outputs = sep.separate()
        except TypeError:
            try:
                # firma moderna: separate(input)
                outputs = sep.separate(filepath)
            except TypeError:
                try:
                    # firma: separate(input, out_dir)
                    outputs = sep.separate(filepath, work_dir)
                except TypeError:
                    try:
                        # otra variante con nombre de argumento
                        outputs = sep.separate(out_dir=work_dir)
                    except Exception as e:
                        app.logger.exception("No se pudo llamar a Separator.separate con ninguna firma conocida")
                        return jsonify({"error": "Incompatibilidad con la librería audio-separator"}), 500

        # Normalizar outputs a lista de rutas
        if isinstance(outputs, dict):
            files = []
            for v in outputs.values():
                if isinstance(v, (list, tuple)):
                    files.extend(v)
                else:
                    files.append(v)
            outputs = files
        elif isinstance(outputs, str):
            outputs = [outputs]
        elif outputs is None:
            outputs = []

        # Buscar archivo WAV generado automáticamente
        candidates = [p for p in outputs if p.lower().endswith(".wav")]
        if not candidates:
            return jsonify({"error": "No se generó WAV separado"}), 500

        stem_wav = os.path.join(work_dir, candidates[0])

        # ================================================================
        # 5) Seleccionar script según instrumento
        # ================================================================
        if instrumento == "piano":
            script = "./ParteDeJuli/LeerArchivoYnota_piano.py"

        elif instrumento == "guitarra":
            script = "./ParteDeJuli/LeerArchivoYnota_guitarra.py"

        elif instrumento == "violin":
            script = "./ParteDeJuli/LeerArchivoYnota_violin.py"

        else:
            return jsonify({"error": "Instrumento inválido"}), 400


        # ================================================================
        # 6) DETECCIÓN DE NOTAS
        # ================================================================
        set_progress(usuario, "Detectando notas...")

        subprocess.run(
            [PYTHON_EXEC, script, stem_wav, work_dir],
            check=True
        )

        set_progress(usuario, "Generando imagen...")

        # ================================================================
        # 7) Buscar PNG y XML generados
        # ================================================================
        IMG_EXTS = ('.png', '.jpg', '.jpeg', '.svg')
        XML_EXTS = ('.xml', '.musicxml')

        def find_outputs(base_dir):
            img, xml = None, None
            for root, _, files in os.walk(base_dir):
                for f in files:
                    fl = f.lower()
                    if not img and fl.endswith(IMG_EXTS):
                        img = os.path.join(root, f)
                    if not xml and fl.endswith(XML_EXTS):
                        xml = os.path.join(root, f)

                if img and xml:
                    return img, xml
            return img, xml

        img_path, xml_path = None, None

        for _ in range(20):
            img_path, xml_path = find_outputs(work_dir)
            if img_path:
                break
            time.sleep(0.4)

        if not img_path:
            return jsonify({"error": "No se generó imagen de partitura"}), 500

        # ================================================================
        # 8) Construir URLs públicas
        # ================================================================
        def to_url(p):
            rel = os.path.relpath(p, STATIC_TEMP_FOLDER).replace("\\", "/")
            return "/static/temp/" + rel

        set_progress(usuario, "Completado")

        return jsonify({
            "imagen": to_url(img_path),
            "xml": to_url(xml_path) if xml_path else None
        })

    # ================================================================
    # MANEJO DE ERRORES
    # ================================================================
    except subprocess.CalledProcessError as e:
        print("SCRIPT ERROR:", e, file=sys.stderr)
        return jsonify({"error": "Fallo el script de detección de notas", "output": str(e)}), 500

    except Exception as e:
        app.logger.exception("Error en /upload")
        return jsonify({"error": "Falló el servidor"}), 500
    
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
                if os.path.isdir(subdir) and not os.listdir(subdir):
                    os.rmdir(subdir)
            except:
                pass
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
@app.route('/api/editor/save', methods=['POST'])
def api_editor_save():
    data = request.get_json(silent=True) or {}
    usuario = data.get("usuario")
    nombre = data.get("nombre", "partitura")
    xml = data.get("xml")  # STRING del MusicXML completo
    png_base64 = data.get("png")  # PNG en base64

    if not usuario or not xml or not png_base64:
        return jsonify({"error": "Faltan datos"}), 400

    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)
    os.makedirs(user_dir, exist_ok=True)

    xml_path = os.path.join(user_dir, nombre + ".musicxml")
    png_path = os.path.join(user_dir, nombre + ".png")

    # Guardar XML
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml)

    # Guardar PNG desde base64
    import base64
    img_bytes = base64.b64decode(png_base64.split(",")[-1])
    with open(png_path, "wb") as f:
        f.write(img_bytes)

    return jsonify({"success": True, "message": "Partitura guardada"})

@app.route('/api/editor/load/<usuario>/<nombre>')
def api_editor_load(usuario, nombre):
    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)
    xml_path = os.path.join(user_dir, nombre + ".musicxml")

    if not os.path.exists(xml_path):
        return jsonify({"error": "No existe ese archivo"}), 404

    with open(xml_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    return jsonify({"xml": contenido})

@app.route('/api/editor/png/<usuario>/<nombre>')
def api_editor_png(usuario, nombre):
    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)
    png_path = os.path.join(user_dir, nombre + ".png")

    if not os.path.exists(png_path):
        return jsonify({"error": "PNG no encontrado"}), 404

    return send_from_directory(user_dir, nombre + ".png")

@app.route('/api/editor/delete', methods=['POST'])
def delete_partitura():
    data = request.get_json()
    usuario = data.get("usuario")
    nombre = data.get("nombre")

    if not usuario or not nombre:
        return jsonify({"success": False, "error": "Faltan datos"}), 400

    user_dir = os.path.join(PARTITURAS_USER_FOLDER, usuario)

    eliminados = 0
    for ext in (".png", ".xml", ".musicxml"):
        path = os.path.join(user_dir, nombre + ext)
        if os.path.exists(path):
            os.remove(path)
            eliminados += 1

    if eliminados == 0:
        return jsonify({"success": False, "error": "No se encontró la partitura"}), 404

    return jsonify({"success": True})

@app.route('/healthz')
def healthz():
    return "ok", 200

@app.route('/<pagina>.html')
def paginas_html(pagina):
    filename = pagina + ".html"
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return "Página no encontrada", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False)
