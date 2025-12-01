from music21 import stream, note, instrument, tempo as m21tempo, meter, duration
import os, sys, json, subprocess, traceback
from time import time as timestamp

MUSESCORE_PATH = os.environ.get(
    "MUSESCORE_PATH",
    r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe" if os.name == "nt" else "mscore3-cli"
)

def safe_print(*a, **kw):
    print(*a, file=sys.stderr, **kw)

# NO reemplazar mscore3-cli (Cloud Run lo necesita así)
safe_print("MUSESCORE_PATH_RESOLVED:", MUSESCORE_PATH)

def sanitize(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)

# --- Cuantizar duraciones ---
def quantize_duration(d: float, step: float = 0.25) -> float:
    if d is None or d <= 0:
        return 0.0
    q = round(d / step) * step
    if abs(q) < 1e-6:
        return 0.0
    return q

# Duraciones permitidas por MusicXML
ALLOWED_DURS = {4.0, 2.0, 1.0, 0.5, 0.25, 0.125, 0.0625}

def limpiar_duraciones(score):
    """
    Si music21 genera duraciones "complejas", las reemplazamos por simples.
    """
    for el in score.recurse().notesAndRests:
        d = el.duration
        ql = d.quarterLength

        if getattr(d, "isComplex", False) or ql not in ALLOWED_DURS:
            new_d = quantize_duration(ql)
            if new_d <= 0:
                new_d = 0.25
            el.duration = duration.Duration(new_d)

figura_a_duracion = {
    'redonda': 4.0,
    'blanca': 2.0,
    'negra': 1.0,
    'corchea': 0.5,
    'semicorchea': 0.25,
    'fusa': 0.125,
    'semifusa': 0.0625,
}

def main():
    try:
        out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("static", "temp")
        os.makedirs(out_dir, exist_ok=True)

        safe_print("OUT_DIR:", out_dir)
        safe_print("MUSESCORE_PATH:", MUSESCORE_PATH)

        JSON_PATH = os.path.join(out_dir, "notas_detectadas.json")

        if not os.path.exists(JSON_PATH):
            safe_print("ERROR: No se encontró JSON:", JSON_PATH)
            return sys.exit(1)

        with open(JSON_PATH, "r", encoding="utf-8") as f:
            notas = json.load(f)

        if not notas:
            safe_print("ERROR: JSON sin notas.")
            return sys.exit(1)

        score = stream.Score()
        part = stream.Part()
        part.insert(0, instrument.Piano())

        # Tempo
        primer_tempo = next((n.get('tempo') for n in notas if 'tempo' in n), 120)
        part.insert(0, m21tempo.MetronomeMark(number=primer_tempo))

        # Agrupar por compás
        notas = [
            n for n in notas
            if 'compas' in n and 'nota' in n
        ]
        notas = sorted(notas, key=lambda n: (n['compas'], n.get('inicio', 0)))

        compases = {}
        for n in notas:
            compases.setdefault(n['compas'], []).append(n)

        if not compases:
            safe_print("ERROR: no hay compases válidos")
            return sys.exit(1)

        # Determinar métrica
        primer_compas = compases[sorted(compases.keys())[0]]
        suma = sum(
            figura_a_duracion.get(n.get('figura', 'negra').lower(), 1.0)
            for n in primer_compas
        )

        if abs(suma - 4.0) < 0.01: tsig, dur_compas = '4/4', 4.0
        elif abs(suma - 3.0) < 0.01: tsig, dur_compas = '3/4', 3.0
        elif abs(suma - 2.0) < 0.01: tsig, dur_compas = '2/4', 2.0
        elif abs(suma - 6.0) < 0.01: tsig, dur_compas = '6/4', 6.0
        else:                        tsig, dur_compas = '4/4', 4.0

        part.append(meter.TimeSignature(tsig))

        # Construir compases
        for num_compas in sorted(compases.keys()):
            m = stream.Measure(number=num_compas)
            tC = 0.0

            for n in compases[num_compas]:
                nombre = n['nota']
                figura = n.get('figura', 'negra').lower()
                dur_raw = figura_a_duracion.get(figura, 1.0)
                dur = quantize_duration(dur_raw)

                if dur <= 0:
                    continue

                nn = note.Note(nombre)
                nn.quarterLength = dur
                m.append(nn)
                tC += dur

            resto_raw = max(0.0, dur_compas - tC)
            resto = quantize_duration(resto_raw)

            if resto > 0:
                r = note.Rest()
                r.quarterLength = resto
                m.append(r)

            part.append(m)

        score.insert(0, part)

        # 🔧 normalizamos duraciones raras ANTES del export
        limpiar_duraciones(score)

        # Paths
        base = sanitize(f"partitura_piano_{int(timestamp())}")
        xml_path = os.path.join(out_dir, base + ".musicxml")
        xml_path2 = os.path.join(out_dir, base + ".xml")
        png_path = os.path.join(out_dir, base + ".png")

        # Guardar XML — makeNotation=True evita errores
        try:
            safe_print("WRITE_XML:", xml_path)
            score.write('musicxml', fp=xml_path, makeNotation=True)
        except Exception as e:
            safe_print("XML_WRITE_ERROR:", repr(e))
            traceback.print_exc()
            return sys.exit(1)

        # MuseScore PNG
        if not os.path.exists(xml_path) and os.path.exists(xml_path2):
            xml_path = xml_path2

        cmd = [MUSESCORE_PATH, xml_path, "-o", png_path]
        safe_print("RUN_MUSESCORE:", cmd)

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            safe_print("PNG_ERROR:", e.stderr)
            return sys.exit(1)

        if not any(p.endswith(".png") for p in os.listdir(out_dir)):
            safe_print("ERROR: No PNG generado")
            return sys.exit(1)

        safe_print("OK_XML:", xml_path)
        safe_print("OK_PNG:", png_path)
        return 0

    except Exception as e:
        safe_print("FATAL:", repr(e))
        traceback.print_exc()
        return sys.exit(1)


if __name__ == "__main__":
    main()
