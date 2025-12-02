import os, sys, json, time, subprocess, shutil
from audio_separator import Separator

BASE = "/tmp/scorik"
PROGRESS = os.path.join(BASE, "progress")

def update_meta(job_id, **kwargs):
    path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(path, "r") as f:
        data = json.load(f)
    for k, v in kwargs.items():
        data[k] = v
    with open(path, "w") as f:
        json.dump(data, f)

def main():
    job_id = sys.argv[1]

    # cargar metadata
    meta_path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(meta_path, "r") as f:
        meta = json.load(f)

    usuario     = meta["usuario"]
    instrumento = meta["instrumento"]
    filepath    = meta["filepath"]
    work_dir    = meta["work_dir"]

    # -----------------------------
    # 1) SEPARACIÓN DE INSTRUMENTOS
    # -----------------------------
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

    # preprocesamiento WAV
    pre_wav = os.path.join(work_dir, "pre.wav")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", filepath,
        "-ac", "1",
        "-ar", "44100",
        pre_wav
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    filepath = pre_wav

    # separar
    sep = Separator(filepath, model_name=model_name)
    try:
        outputs = sep.separate()
    except Exception as e:
        update_meta(job_id, msg=f"Error separando audio: {str(e)}", status="error")
        return

    # normalizar outputs
    if isinstance(outputs, dict):
        files = []
        for v in outputs.values():
            if isinstance(v, list):
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

    # -----------------------------
    # 2) DETECCIÓN DE NOTAS
    # -----------------------------
    update_meta(job_id, msg="Detectando notas...")

    if instrumento == "piano":
        script_det = "./ParteDeJuli/LeerArchivoYnota_piano.py"
    elif instrumento == "guitarra":
        script_det = "./ParteDeJuli/LeerArchivoYnota_guitarra.py"
    else:
        script_det = "./ParteDeJuli/LeerArchivoYnota_violin.py"

    try:
        # genera work_dir/notas_detectadas.json
        subprocess.run([sys.executable, script_det, stem_wav, work_dir], check=True)
    except Exception as e:
        update_meta(job_id, msg=f"Error en detección: {str(e)}", status="error")
        return

    # -----------------------------
    # 3) JSON → XML + PNG (NotasAPartitura + MuseScore)
    # -----------------------------
    update_meta(job_id, msg="Generando partitura...")

    if instrumento == "piano":
        script_part = "./ParteDeTota/NotasAPartitura_piano.py"
    elif instrumento == "guitarra":
        script_part = "./ParteDeTota/NotasAPartitura_guitarra.py"
    else:
        script_part = "./ParteDeTota/NotasAPartitura_violin.py"

    try:
        # este script:
        #   - lee work_dir/notas_detectadas.json
        #   - crea XML
        #   - llama a MuseScore y genera PNG
        subprocess.run([sys.executable, script_part, work_dir], check=True)
    except Exception as e:
        update_meta(job_id, msg=f"Error generando partitura: {str(e)}", status="error")
        return

    # -----------------------------
    # 4) BUSCAR XML Y PNG GENERADOS
    # -----------------------------
    xml_path = None
    png_path = None
    for root, _, files in os.walk(work_dir):
        for f in files:
            low = f.lower()
            full = os.path.join(root, f)
            if low.endswith((".xml", ".musicxml")) and xml_path is None:
                xml_path = full
            if low.endswith(".png") and png_path is None:
                png_path = full

    if not png_path:
        update_meta(job_id, msg="ERROR: no se generó PNG", status="error")
        return
    if not xml_path:
        update_meta(job_id, msg="ERROR: no se generó XML", status="error")
        return

    # -----------------------------
    # 5) FIN — guardar rutas
    # -----------------------------
    update_meta(
        job_id,
        result_img=png_path,
        result_xml=xml_path,
        status="done",
        msg="Completado"
    )

if __name__ == "__main__":
    main()
