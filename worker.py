import os, sys, json, time, subprocess
import shutil
import os
import json
from audio_separator import Separator

# --- DEBUG PARA VER SI MUSESCORE EXISTE EN EL CONTENEDOR ---
print("CHECK mscore3:", shutil.which("mscore3"))
print("CHECK mscore3-cli:", shutil.which("mscore3-cli"))
print("CHECK MuseScore3:", shutil.which("MuseScore3"))

BASE = "/tmp/scorik"
PROGRESS = os.path.join(BASE, "progress")

def update_meta(job_id, **kwargs):
    """Actualiza SOLO los campos enviados, sin borrar los demás."""
    path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(path, "r") as f:
        data = json.load(f)

    for k, v in kwargs.items():
        data[k] = v

    with open(path, "w") as f:
        json.dump(data, f)


def main():
    job_id = sys.argv[1]

    # Cargar metadata generada por /upload
    meta_path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(meta_path, "r") as f:
        meta = json.load(f)

    usuario     = meta["usuario"]
    instrumento = meta["instrumento"]
    filepath    = meta["filepath"]
    work_dir    = meta["work_dir"]

    # ================================================================
    # 4) SEPARACIÓN DE INSTRUMENTOS – audio-separator 0.7.3
    # ================================================================
    update_meta(job_id, msg="Separando instrumentos (MDX 0.7.3)...")

    MODEL_MAP = {
        "guitarra": "UVR-MDX-NET-Inst_1",
        "piano":    "UVR-MDX-NET-Inst_HQ_2",
        "violin":   "UVR_MDXNET_3_9662",
    }

    model_name = MODEL_MAP.get(instrumento)
    if not model_name:
        update_meta(job_id, msg="Instrumento inválido", status="error")
        return

    os.makedirs(work_dir, exist_ok=True)

    # ======= PRE-PROCESAMIENTO FFmpeg PARA EVITAR CUELGUES =======
    pre_wav = os.path.join(work_dir, "pre.wav")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", filepath,
        "-ac", "1",        # 1 canal (mono)
        "-ar", "44100",    # sample rate estándar
        pre_wav
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    filepath = pre_wav
    # ===============================================================

    # EXACTO como en app.py
    sep = Separator(
        filepath,          # audio_file
        model_name=model_name
    )

    try:
        outputs = sep.separate()
    except Exception as e:
        update_meta(job_id, msg=f"Error separando audio: {str(e)}", status="error")
        return

    # Normalización de outputs
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

    candidates = [p for p in outputs if p.lower().endswith(".wav")]
    if not candidates:
        update_meta(job_id, msg="Error: no se generó WAV separado", status="error")
        return

    stem_wav = candidates[0]

    # ================================================================
    # 5) DETECCIÓN DE NOTAS
    # ================================================================
    if instrumento == "piano":
        script = "./ParteDeJuli/LeerArchivoYnota_piano.py"
    elif instrumento == "guitarra":
        script = "./ParteDeJuli/LeerArchivoYnota_guitarra.py"
    elif instrumento == "violin":
        script = "./ParteDeJuli/LeerArchivoYnota_violin.py"

    update_meta(job_id, msg="Detectando notas...")

    try:
        subprocess.run([sys.executable, script, stem_wav, work_dir], check=True)
    except Exception as e:
        update_meta(job_id, msg=f"Error en detección: {str(e)}", status="error")
        return

    update_meta(job_id, msg="Generando imagen...")

    # ================================================================
    # 7) Buscar PNG y XML
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

    img_path, xml_path = find_outputs(work_dir)

    if not img_path:
        update_meta(job_id, msg="Error: no se generó imagen", status="error")
        return

    # Guardar resultados finales en metadata
    update_meta(
        job_id,
        result_img=img_path,
        result_xml=xml_path,
        status="done",
        msg="Completado"
    )


if __name__ == "__main__":
    main()
