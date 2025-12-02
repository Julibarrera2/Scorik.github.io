import os, sys, json, subprocess

BASE = "/tmp/scorik"
PROGRESS = os.path.join(BASE, "progress")

def update_meta(job_id, **kwargs):
    path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k, v in kwargs.items():
        data[k] = v
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

def main():
    job_id = sys.argv[1]
    print(">>> WORKER START", job_id, flush=True)

    # ---------------------------------
    # CARGAR META
    # ---------------------------------
    meta_path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    usuario     = meta["usuario"]
    instrumento = meta["instrumento"]
    filepath    = meta["filepath"]
    work_dir    = meta["work_dir"]

    print(">>> USUARIO:", usuario, flush=True)
    print(">>> INSTRUMENTO:", instrumento, flush=True)
    print(">>> FILEPATH INICIAL:", filepath, "exists?", os.path.exists(filepath), flush=True)
    print(">>> WORK_DIR:", work_dir, flush=True)

    os.makedirs(work_dir, exist_ok=True)

    # ---------------------------------
    # 1) PREPROCESO WAV (MONO 44.1k)
    #    SIN SEPARAR INSTRUMENTOS
    # ---------------------------------
    update_meta(job_id, msg="Preparando audio...")

    pre_wav = os.path.join(work_dir, "pre.wav")
    print(">>> FFmpeg a mono 44.1k:", pre_wav, flush=True)

    cmd_ffmpeg = [
        "ffmpeg", "-y",
        "-i", filepath,
        "-ac", "1",
        "-ar", "44100",
        pre_wav
    ]
    proc_ff = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(">>> FFMPEG RETURN:", proc_ff.returncode, flush=True)
    if proc_ff.returncode != 0:
        print(">>> FFMPEG OUTPUT:\n", proc_ff.stdout, flush=True)
        update_meta(job_id, msg="Error en ffmpeg", status="error")
        return

    if not os.path.exists(pre_wav):
        print(">>> ERROR: pre.wav NO existe", flush=True)
        update_meta(job_id, msg="No se pudo generar WAV", status="error")
        return

    stem_wav = pre_wav
    print(">>> STEM_WAV:", stem_wav, "exists?", os.path.exists(stem_wav), flush=True)

    # ---------------------------------
    # 2) DETECCIÓN DE NOTAS (CREPE)
    # ---------------------------------
    update_meta(job_id, msg="Detectando notas...")
    print(">>> DETECCIÓN DE NOTAS", flush=True)

    if instrumento == "piano":
        script_det = "./ParteDeJuli/LeerArchivoYnota_piano.py"
    elif instrumento == "guitarra":
        script_det = "./ParteDeJuli/LeerArchivoYnota_guitarra.py"
    else:
        script_det = "./ParteDeJuli/LeerArchivoYnota_violin.py"

    cmd_det = [sys.executable, script_det, stem_wav, work_dir]
    print(">>> CMD DET:", cmd_det, flush=True)

    proc_det = subprocess.run(cmd_det, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(">>> DET RETURN:", proc_det.returncode, flush=True)
    print(">>> DET OUTPUT:\n", proc_det.stdout, flush=True)

    if proc_det.returncode != 0:
        update_meta(job_id, msg="Error en detección de notas", status="error")
        return

    notas_json = os.path.join(work_dir, "notas_detectadas.json")
    print(">>> notas_detectadas.json exists?", os.path.exists(notas_json), flush=True)
    if not os.path.exists(notas_json):
        update_meta(job_id, msg="No se generó notas_detectadas.json", status="error")
        return

    # ---------------------------------
    # 3) JSON → XML + PNG (MuseScore)
    # ---------------------------------
    update_meta(job_id, msg="Generando partitura...")
    print(">>> GENERANDO PARTITURA", flush=True)

    if instrumento == "piano":
        script_part = "./ParteDeTota/NotasAPartitura_piano.py"
    elif instrumento == "guitarra":
        script_part = "./ParteDeTota/NotasAPartitura_guitarra.py"
    else:
        script_part = "./ParteDeTota/NotasAPartitura_violin.py"

    cmd_part = [sys.executable, script_part, work_dir]
    print(">>> CMD PART:", cmd_part, flush=True)

    proc_part = subprocess.run(cmd_part, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(">>> PART RETURN:", proc_part.returncode, flush=True)
    print(">>> PART OUTPUT:\n", proc_part.stdout, flush=True)

    if proc_part.returncode != 0:
        update_meta(job_id, msg="Error generando partitura", status="error")
        return

    # ---------------------------------
    # 4) BUSCAR XML Y PNG
    # ---------------------------------
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

    print(">>> XML FOUND:", xml_path, flush=True)
    print(">>> PNG FOUND:", png_path, flush=True)

    if not png_path:
        update_meta(job_id, msg="ERROR: no se generó PNG", status="error")
        return
    if not xml_path:
        update_meta(job_id, msg="ERROR: no se generó XML", status="error")
        return

    # ---------------------------------
    # 5) FIN
    # ---------------------------------
    update_meta(
        job_id,
        result_img=png_path,
        result_xml=xml_path,
        status="done",
        msg="Completado"
    )
    print(">>> WORKER DONE OK", flush=True)

if __name__ == "__main__":
    main()
