import os, sys, json, subprocess, resource
from audio_separator import Separator

print(">>> WORKER IMPORTED OK", flush=True)
print(">>> TEST MUSESCORE:", flush=True)
subprocess.run(["mscore3", "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(">>> MUSESCORE OK", flush=True)

BASE = "/tmp/scorik"
PROGRESS = os.path.join(BASE, "progress")
LOG_DIR = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def log(job_id, *msg):
    """Guarda en /tmp/scorik/logs/{job_id}.log"""
    text = " ".join(str(m) for m in msg)
    print(text, flush=True)
    with open(os.path.join(LOG_DIR, f"{job_id}.log"), "a") as f:
        f.write(text + "\n")

def update_meta(job_id, **kwargs):
    path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(path) as f:
        data = json.load(f)
    for k,v in kwargs.items():
        data[k] = v
    with open(path, "w") as f:
        json.dump(data, f)

def main():
    job_id = sys.argv[1]
    log(job_id, "WORKER START")

    # --- cargar metadata ---
    meta_path = os.path.join(PROGRESS, f"{job_id}.json")
    with open(meta_path) as f:
        meta = json.load(f)

    instrumento = meta["instrumento"]
    filepath    = meta["filepath"]
    work_dir    = meta["work_dir"]

    os.makedirs(work_dir, exist_ok=True)

    # -----------------------------
    # 1) SEPARACIÓN
    # -----------------------------
    update_meta(job_id, msg="Separando instrumentos...")
    log(job_id, "Separando instrumentos:", instrumento)

    models = {
        "guitarra":"UVR-MDX-NET-Inst_1",
        "piano":"UVR-MDX-NET-Inst_HQ_2",
        "violin":"UVR_MDXNET_3_9662",
    }
    model = models.get(instrumento)

    # convertir a wav
    pre_wav = os.path.join(work_dir, "pre.wav")
    subprocess.run(["ffmpeg","-y","-i",filepath,"-ac","1","-ar","44100",pre_wav],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    filepath = pre_wav

    # separar
    sep = Separator(filepath, model_name=model)
    try:
        outputs = sep.separate()
        log(job_id, "Separación OK")
    except Exception as e:
        update_meta(job_id, msg="Error separando", status="error")
        log(job_id, "ERROR separando:", e)
        return

    # normalizar outputs
    wavs = []
    if isinstance(outputs, dict):
        for v in outputs.values():
            if isinstance(v, list):
                wavs += v
            else:
                wavs.append(v)
    elif isinstance(outputs, str):
        wavs = [outputs]

    stem = next((w for w in wavs if w.endswith(".wav")), None)
    if not stem:
        update_meta(job_id, msg="No WAV", status="error")
        log(job_id, "NO WAV SEPARADO")
        return

    # -----------------------------
    # 2) DETECTAR NOTAS
    # -----------------------------
    update_meta(job_id, msg="Detectando notas...")
    log(job_id, "Detectando notas (CREPE)")

    script_det = {
        "guitarra":"./ParteDeJuli/LeerArchivoYnota_guitarra.py",
        "piano":"./ParteDeJuli/LeerArchivoYnota_piano.py",
        "violin":"./ParteDeJuli/LeerArchivoYnota_violin.py",
    }[instrumento]

    result = subprocess.run(
        [sys.executable, script_det, stem, work_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        update_meta(job_id, msg="Error detectando", status="error")
        log(job_id, "ERROR detectando:", result.stderr)
        return

    log(job_id, "Notas detectadas OK")

    # -----------------------------
    # 3) XML + PNG
    # -----------------------------
    update_meta(job_id, msg="Generando partitura...")
    log(job_id, "Generando PNG...")

    script_part = {
        "guitarra":"./ParteDeTota/NotasAPartitura_guitarra.py",
        "piano":"./ParteDeTota/NotasAPartitura_piano.py",
        "violin":"./ParteDeTota/NotasAPartitura_violin.py",
    }[instrumento]

    result = subprocess.run(
        [sys.executable, script_part, work_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        update_meta(job_id, msg="Error generando partitura", status="error")
        log(job_id, "ERROR partitura:", result.stderr)
        return

    # -----------------------------
    # 4) BUSCAR PNG Y XML
    # -----------------------------
    xml = None
    png = None

    for root,_,files in os.walk(work_dir):
        for f in files:
            p = os.path.join(root,f)
            if f.endswith(".png"): png = p
            if f.endswith(".xml") or f.endswith(".musicxml"): xml = p

    if not png or not xml:
        update_meta(job_id,msg="No PNG/XML",status="error")
        log(job_id,"ERROR: faltan archivos", xml, png)
        return

    update_meta(job_id,
        result_img=png,
        result_xml=xml,
        status="done",
        msg="Completado"
    )
    log(job_id, "FIN OK")

if __name__ == "__main__":
    main()
