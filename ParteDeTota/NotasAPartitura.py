from music21 import stream, note, instrument, tempo as m21tempo, meter
import os, sys, json, subprocess, traceback
from time import time as timestamp

# MuseScore: en Cloud Run viene por ENV como /usr/local/bin/mscore3-cli
MUSESCORE_PATH = os.environ.get(
    "MUSESCORE_PATH",
    r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe" if os.name == "nt" else "mscore3-cli"
)

def safe_print(*a, **kw):
    print(*a, file=sys.stderr, **kw)

def sanitize(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)

# --- Cuantizar duraciones a múltiplos simples ---
def quantize_duration(d: float, step: float = 0.25) -> float:
    """
    Redondea la duración 'd' (en quarterLength) al múltiplo más cercano de 'step'
    (step=0.25 -> semicorchea). Evita valores muy pequeños o negativos.
    """
    if d is None or d <= 0:
        return 0.0
    q = round(d / step) * step
    if abs(q) < 1e-6:
        return 0.0
    return q

# === Carpeta destino por argumento (default static/temp) ===
out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("static", "temp")
os.makedirs(out_dir, exist_ok=True)
safe_print("OUT_DIR:", out_dir)
safe_print("MUSESCORE_PATH:", MUSESCORE_PATH)

JSON_PATH = os.path.join(out_dir, "notas_detectadas.json")

figura_a_duracion = {
    'redonda': 4.0, 'blanca': 2.0, 'negra': 1.0, 'corchea': 0.5,
    'semicorchea': 0.25, 'fusa': 0.125, 'semifusa': 0.0625
}

def main():
    try:
        if not os.path.exists(JSON_PATH):
            safe_print("ERROR: No se encontró notas JSON:", JSON_PATH)
            return sys.exit(1)

        with open(JSON_PATH, "r", encoding="utf-8") as f:
            notas = json.load(f)

        if not notas:
            safe_print("ERROR: JSON sin notas.")
            return sys.exit(1)

        score = stream.Score()
        part  = stream.Part()
        part.insert(0, instrument.Violin())

        # Tempo (toma el primero que aparezca, default 120)
        primer_tempo = next((n.get('tempo') for n in notas if 'tempo' in n), 120)
        part.insert(0, m21tempo.MetronomeMark(number=primer_tempo))

        # Ordenar y agrupar por compás
        notas = [n for n in notas if 'compas' in n and 'nota' in n]
        notas = sorted(notas, key=lambda n: (n['compas'], n.get('inicio', 0.0)))

        compases = {}
        for n in notas:
            compases.setdefault(n['compas'], []).append(n)

        if not compases:
            safe_print("ERROR: No hay compases válidos.")
            return sys.exit(1)

        # Métrica heurística con el primer compás
        primer_compas = compases[sorted(compases.keys())[0]]
        suma = sum(figura_a_duracion.get(n.get('figura', 'negra').lower(), 1.0)
                   for n in primer_compas)

        if   abs(suma - 4.0) < 0.01: tsig, dur_compas = '4/4', 4.0
        elif abs(suma - 3.0) < 0.01: tsig, dur_compas = '3/4', 3.0
        elif abs(suma - 2.0) < 0.01: tsig, dur_compas = '2/4', 2.0
        elif abs(suma - 6.0) < 0.01: tsig, dur_compas = '6/4', 6.0
        else:                        tsig, dur_compas = '4/4', 4.0

        part.append(meter.TimeSignature(tsig))

        # === Construir cada compás SOLO con figuras, sin usar "inicio" ===
        for num_compas in sorted(compases.keys()):
            m  = stream.Measure(number=num_compas)
            tC = 0.0  # tiempo acumulado dentro del compás

            for n in compases[num_compas]:
                try:
                    nombre = n['nota']
                    figura = n.get('figura', 'negra').lower()
                    dur_raw = figura_a_duracion.get(figura, 1.0)
                    dur     = quantize_duration(dur_raw)

                    if dur <= 0:
                        continue

                    nn = note.Note(nombre)
                    nn.quarterLength = dur
                    m.append(nn)
                    tC += dur
                except Exception as e:
                    safe_print("WARN: nota inválida:", n, repr(e))

            # Rellenar hasta completar compás
            resto_raw = max(0.0, dur_compas - tC)
            resto     = quantize_duration(resto_raw)
            if resto > 0:
                r = note.Rest()
                r.quarterLength = resto
                m.append(r)

            part.append(m)

        score.insert(0, part)

        base = sanitize(f"partitura_{int(timestamp())}")
        xml_path  = os.path.join(out_dir, base + ".musicxml")
        xml_path2 = os.path.join(out_dir, base + ".xml")
        png_path  = os.path.join(out_dir, base + ".png")

        # --- Escribir MusicXML con manejo de errores
        try:
            safe_print("WRITE_XML ->", xml_path)
            score.write('musicxml', fp=xml_path)
        except Exception as e:
            safe_print("XML_WRITE_ERROR:", repr(e))
            traceback.print_exc()
            return sys.exit(1)

        # A veces music21 escribe .xml aunque pidas .musicxml
        if not os.path.exists(xml_path) and os.path.exists(xml_path2):
            xml_path = xml_path2
        if not os.path.exists(xml_path):
            safe_print("ERROR: No se generó MusicXML en", xml_path, "ni", xml_path2)
            return sys.exit(1)

        # --- Render PNG con MuseScore
        cmd = [MUSESCORE_PATH, xml_path, "-o", png_path]
        safe_print("RUN_MUSESCORE:", cmd)
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            safe_print("PNG_WRITE_ERROR: returncode=", e.returncode)
            safe_print("STDOUT:", e.stdout)
            safe_print("STDERR:", e.stderr)
            if not os.path.exists(MUSESCORE_PATH):
                safe_print("HINT: MUSESCORE_PATH no existe:", MUSESCORE_PATH)
            return sys.exit(1)

        # Verificar PNG
        pngs = [f for f in os.listdir(out_dir) if f.startswith(base) and f.endswith(".png")]
        if not pngs:
            safe_print("ERROR: MuseScore no produjo PNG en", out_dir)
            return sys.exit(1)

        safe_print("OK_XML ->", xml_path)
        safe_print("OK_PNG ->", [os.path.join(out_dir, p) for p in pngs])
        return 0

    except Exception as e:
        safe_print("FATAL:", repr(e))
        traceback.print_exc()
        return sys.exit(1)

if __name__ == "__main__":
    main()
