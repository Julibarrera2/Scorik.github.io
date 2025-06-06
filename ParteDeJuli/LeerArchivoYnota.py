#Importo librerias
# Procesamiento de audio
import librosa
import soundfile as sf
# Detección de pitch
import crepe
# Utilidades numéricas y científicas
import numpy as np
# Visualización 
import os
from pydub import AudioSegment
from pydub.utils import which
import json
np.float = float

#Links de PC
# ruta video piano: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3
# ruta ffmpeg: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe
# ruta video violin 1: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-1.mp3
# ruta video violin 2: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-2.mp3
# ruta video violin 3: C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\violin-3.mp3

#Links ruta Notebook personal
# ruta video: c:\Users\fb050\OneDrive\Desktop\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3
# ruta ffmpeg: c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe
# ruta ffprobe: c:\Users\fb050\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe
# ruta video violin 1: 
# ruta video violin 2:
# ruta video violin 3:

#Links ruta Notebook ORT
# ruta video: NOSE
# ruta ffmpeg: NOSE
# ruta ffprobe: NOSE
# ruta video violin 1: 
# ruta video violin 2:
# ruta video violin 3: 

# Utilidades extra para filtrar silencios y notas con poca energía
def filtrar_pitch_por_energia(pitch_list, y_signal, sr_signal, threshold_db=-40):
    """Descarta estimaciones de pitch en zonas con poca energía."""
    hop = int(sr_signal * 0.01)  # 10 ms, coincide con step_size_ms
    rms = librosa.feature.rms(y=y_signal, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr_signal, hop_length=hop)
    filtrados = []
    for t, f in pitch_list:
        idx = np.argmin(np.abs(times - t))
        if librosa.amplitude_to_db([rms[idx]], ref=np.max)[0] > threshold_db:
            filtrados.append((t, f))
    return filtrados

def recortar_final_por_energia(y_signal, sr_signal, threshold_db=-40):
    """Recorta el final del audio cuando la energía cae por debajo del umbral."""
    rms = librosa.feature.rms(y=y_signal)[0]
    db = librosa.amplitude_to_db(rms, ref=np.max)
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr_signal)
    valid = np.where(db > threshold_db)[0]
    if valid.size == 0:
        return y_signal
    end_sample = int(times[valid[-1]] * sr_signal)
    return y_signal[:end_sample]

#Los directorios de ffmpeg del .exe para que funciones
AudioSegment.converter = which("ffmpeg") or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = which("ffprobe") or r"C:\Users\Julia Barrera\Downloads\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

#Ruta del archivo
ruta = r"C:\Users\Julia Barrera\Downloads\Scorik.github.io\ParteDeJuli\Samples\piano-lento.mp3"

#verificás si el archivo .mp3 realmente está en esa ruta.
if not os.path.exists(ruta):
    raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

def cargar_audio(filepath, sr=22050):
    #Carga un archivo de audio. Si es .mp3 lo convierte a .wav automáticamente.
    # Parámetros:- filepath: Ruta al archivo de audio - sr: Frecuencia de muestreo deseada (por defecto 22050 Hz)
    # Devuelve:- y: señal de audio como array numpy - sr: frecuencia de muestreo
    # Verificar extensión del archivo
    filename, ext = os.path.splitext(filepath)

    # Si es .mp3, convertir a .wav
    if ext.lower() == ".mp3":
        print("Convirtiendo .mp3 a .wav...")
        audio_mp3 = AudioSegment.from_mp3(filepath)
        filepath_wav = filename + ".wav"
        audio_mp3.export(filepath_wav, format="wav")
        filepath = filepath_wav  # Actualiza la ruta para usar el nuevo .wav

    # Cargar el archivo .wav
    print(f"Cargando archivo: {filepath}")
    y, sr = librosa.load(filepath, sr=sr)
    print("Audio cargado correctamente.")
    return y, sr, filepath

#Carga el audio a la ruta
y, sr, filepath= cargar_audio(ruta)

#Confirmacion con el usuario si el archivo esta bien
# Luego de cargar_audio(...)
# def abrir_wav(path):
    # print(f"Reproduciendo {path}...")
    # pygame.init()
    # pygame.mixer.init()
    # pygame.mixer.music.load(path)
    # pygame.mixer.music.play()
    # while pygame.mixer.music.get_busy():
    #     continue   
# abrir_wav(filepath)
# confirm = input("¿Querés continuar con este archivo .wav? (s/n): ").strip().lower()
# if confirm != 's':
#     print("Proceso detenido. Revisá el archivo original.")
#     exit()

# ---------------------------------------------------------
# 1) RECORTAR SILENCIOS DEL FINAL (librosa.effects.trim):
# ---------------------------------------------------------
# Esto elimina automáticamente las porciones del principio y final donde el nivel
# de audio esté por debajo de un umbral de decibeles (top_db).
# Devolvemos y_trimmed (señal sin silencios) y unos índices (start, end) que indican
# dónde quedó “lo útil” en la grabación original.
#Recorte inicial de silencio
y_trim, index_trim = librosa.effects.trim(y, top_db=20)
# Recorte extra por energía para evitar ruidos finales
y_trim = recortar_final_por_energia(y_trim, sr)
y = y_trim
# (sr permanece igual; sr sigue siendo la misma frecuencia de muestreo que ya tenías)


#DETECTAR PITCH
def detectar_pitch(y_local, sr_local, step_size_ms=10, threshold=0.9):
    #Usa CREPE para detectar el pitch en una señal de audio.
    #Parámetros:
    # y: señal de audio   
    # sr: sample rate (frecuencia de muestreo)
    #step_size_ms: resolución temporal en milisegundos
    #threshold: umbral de confianza mínima (0 a 1)
    # Devuelve:
    #pitches_filtradas: lista de notas detectadas con tiempo y frecuencia
    print("Detectando pitch con CREPE...")

    # CREPE necesita un sample rate de 16000
    #Resampleo a 16000 Hz: CREPE solo funciona con 16000 Hz, por lo tanto si cargamos a 22050 Hz lo transformamos.
    if sr_local != 16000:
        y_local = librosa.resample(y_local, orig_sr=sr_local, target_sr=16000)
        sr_local = 16000
    
    # CREPE requiere una señal estéreo
    #Reformateo del audio: CREPE espera entrada estéreo (matriz Nx1).
    if len(y_local.shape) == 1:
        y_local = np.expand_dims(y_local, axis=1)
    
    # Ejecutamos CREPE
    #crepe.predict(...): Devuelve arrays de tiempo, frecuencia, confianza y activación
    time, frequency, confidence, _ = crepe.predict(y_local, sr_local, step_size=step_size_ms,viterbi=True)

    # Filtrar por confianza
    #Filtro de confianza: descartamos predicciones dudosas (ej: menos de 0.8 de confianza).
    pitches_filtradas = [] 
    for t, f, c in zip(time, frequency, confidence):
        if c >= threshold and 30 < f < 1200:
            pitches_filtradas.append((t, f))  # tiempo y frecuencia
    
    #printeamois la informacion
    print(f"Se detectaron {len(pitches_filtradas)} pitches con confianza > {threshold}.")
    return pitches_filtradas
# Ahora usamos y_trim para la detección
pitches = detectar_pitch(y_trim, sr)
# Filtrado adicional de ruido por energía
pitches = filtrar_pitch_por_energia(pitches, y_trim, sr)
# Eliminar últimos dos segundos para evitar falsas detecciones
dur_trim = librosa.get_duration(y=y_trim, sr=sr)
pitches = [p for p in pitches if p[0] < dur_trim - 2.0]
print("Primeros 10 pitches:", pitches[:10])

#Pasar de pitch a nota
# Diccionario de notas
notas_dict = {
    'C0': 16.35, 'C#0': 17.32, 'D0': 18.35, 'D#0': 19.45, 'E0': 20.60, 'F0': 21.83, 'F#0': 23.12, 'G0': 24.50,
    'G#0': 25.96, 'A0': 27.50, 'A#0': 29.14, 'B0': 30.87, 'C1': 32.70, 'C#1': 34.65, 'D1': 36.71, 'D#1': 38.89,
    'E1': 41.20, 'F1': 43.65, 'F#1': 46.25, 'G1': 49.00, 'G#1': 51.91, 'A1': 55.00, 'A#1': 58.27, 'B1': 61.74,
    'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78, 'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'G2': 98.00,
    'G#2': 103.83, 'A2': 110.00, 'A#2': 116.54, 'B2': 123.47, 'C3': 130.81, 'C#3': 138.59, 'D3': 146.83,
    'D#3': 155.56, 'E3': 164.81, 'F3': 174.61, 'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00,
    'A#3': 233.08, 'B3': 246.94, 'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63,
    'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25, 'E5': 659.25, 'F5': 698.46, 'F#5': 739.99,
    'G5': 783.99, 'G#5': 830.61, 'A5': 880.00, 'A#5': 932.33, 'B5': 987.77, 'C6': 1046.50, 'C#6': 1108.73
}

def frecuencia_a_nota(freq):
    return min(notas_dict.items(), key=lambda item: abs(item[1] - freq))[0]

# Ruta al .wav convertido
#Carga el WAV A 16000 Hz y recórtalo también con librosa.trim
ruta_wav = filepath 
y_full2, sr_full2 = librosa.load(ruta_wav, sr=16000)

# Otra vez recortamos silencio (para beat-track y CREPE “manual”)
y_trim2, idx_trim2 = librosa.effects.trim(y_full2, top_db=20)
y_trim2 = recortar_final_por_energia(y_trim2, sr_full2)
dur_trim2 = librosa.get_duration(y=y_trim2, sr=sr_full2)
print(f"(Beat-track) Audio recortado a {dur_trim2:.2f}s (antes: {len(y_full2)/sr_full2:.2f}s).")

# Usamos y_trim para todo lo siguiente:
y = y_trim2
sr = sr_full2  # en este bloque sr siempre será 16000

tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
if len(y.shape) == 1:
    y = np.expand_dims(y, axis=1)

time, frequency, confidence, _ = crepe.predict(y, sr, step_size=10, viterbi=True)
pitch_data = [
    (t, f) for t, f, c in zip(time, frequency, confidence)
    if c > 0.9 and 30 < f < 1200
]
pitch_data = filtrar_pitch_por_energia(pitch_data, y[:,0] if y.ndim > 1 else y, sr)
duracion_audio_trim = librosa.get_duration(y=y, sr=sr)
#pitch_data = [p for p in pitch_data if p[0] < duracion_audio_trim - 2.0]
print("Primeros 20 valores de pitch_data (t, f):", pitch_data[:20])

print("→ Cantidad de frames en pitch_data:", len(pitch_data))
print("→ Primeros 10 frames:", pitch_data[:10])

def calcular_figura_y_compas(duracion, tempo, inicio):
    negra_duracion = 60 / tempo
    if duracion < negra_duracion * 0.6:
        figura = "corchea"
    elif duracion < negra_duracion * 1.2:
        figura = "negra"
    elif duracion < negra_duracion * 2.2:
        figura = "blanca"
    else:
        figura = "redonda"
    compas = int(inicio / (negra_duracion * 4)) + 1
    return figura, compas

MIN_DURACION_NOTA = 0.01
NOTA_UMBRAL_VARIACION = 0.25

def semitonos(f1, f2):
    return abs(12 * np.log2(f1 / f2))

# Un for que analiza cada tramo de 10 segundos
notas_json = []
if pitch_data:
    segmento_duracion = 10.0  # duración de cada tramo en segundos
    total_tiempo = pitch_data[-1][0]
    num_segmentos = int(np.ceil(total_tiempo / segmento_duracion))
    print("Total tiempo del audio recortado:", duracion_audio_trim, "segundos")
    print("Segmento duración:", segmento_duracion)
    print("Número de segmentos:", num_segmentos)
    for s in range(num_segmentos):
        inicio_seg = s * segmento_duracion
        fin_seg = (s + 1) * segmento_duracion
        print(f"\n🔍 Analizando tramo {s+1}/{num_segmentos} ({inicio_seg:.2f}s - {fin_seg:.2f}s)")
        # Filtramos solo los pitches de este tramo
        segmento = [p for p in pitch_data if inicio_seg <= p[0] < fin_seg]
        if not segmento:
            print("  ⚠️ Sin datos en este tramo.")
            continue
        # Si es el último tramo, suavizamos frecuencias con media móvil (ventana 3)
        if s == num_segmentos - 1 and len(segmento) >= 3:
            tiempos_seg = [p[0] for p in segmento]
            freqs_seg = [p[1] for p in segmento]
            freqs_suavizadas = np.convolve(freqs_seg, np.ones(3)/3, mode='same')
            segmento = list(zip(tiempos_seg, freqs_suavizadas))
        # Inicializamos variables de agrupamiento
        inicio = segmento[0][0]
        freq_actual = segmento[0][1]
        nota_actual = frecuencia_a_nota(freq_actual)
        for i in range(1, len(segmento)):
            t, f = segmento[i]
            #Antes de la condición, mostramos la diferencia en semitonos
            diferencia_en_semitonos = semitonos(f, freq_actual)
            print(f"comparando freq_actual={freq_actual:.1f}Hz y f={f:.1f}Hz ⇒ Δ={diferencia_en_semitonos:.3f} semitonos")
            # Si la nota nueva es diferente (por semitonos), se cierra la nota anterior
            # Si la nota nueva es suficientemente distinta, cerramos la nota anterior
            if diferencia_en_semitonos > NOTA_UMBRAL_VARIACION:
                duracion = t - inicio
                #print(f"    → Duración calculada: {duracion:.3f}s")
                if duracion >= MIN_DURACION_NOTA:
                    figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                    notas_json.append({
                        "nota": nota_actual,
                        "inicio": round(inicio, 3),
                        "duracion": round(duracion, 3),
                        "compas": compas,
                        "figura": figura,
                        "tempo": int(tempo)
                    })
                # Se actualiza a la nueva nota
                inicio = t
                freq_actual = f
                nota_actual = frecuencia_a_nota(f)
            # Advertencia si hay separación anormal (solo en último tramo)
            if s == num_segmentos - 1 and abs(t - inicio) > 2.0:
                print(f"  ⚠️ Agrupamiento raro detectado entre {inicio:.2f}s y {t:.2f}s")
        # Cierre de la última nota del tramo
        duracion = segmento[-1][0] - inicio
        if MIN_DURACION_NOTA <= duracion < 6.0:
            figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
            notas_json.append({
                "nota": nota_actual,
                "inicio": round(inicio, 3),
                "duracion": round(duracion, 3),
                "compas": compas,
                "figura": figura,
                "tempo": int(tempo)
            })
        # Verificación extra de duración excesiva (último tramo)
        if s == num_segmentos - 1 and duracion > 6.0:
            print(f"⚠️ Nota descartada por duración excesiva: {duracion:.2f}s")

            # Si hay silencio significativo, se agrega pausa
            if t - inicio > 1.5:  # más de 1.5 segundos sin notas válidas
                print(f"Silencio detectado entre {inicio:.2f}s y {t:.2f}s")

            if abs(pitch_data[i][0] - inicio) > 0.03:   
                if abs(t - inicio) > 2.0:
                    print(f"⚠️ Agrupamiento raro detectado entre {inicio:.2f}s y {t:.2f}s")
                duracion = max(t - inicio, 0)
                if duracion == 0:
                    continue
                if duracion > 6.0:
                    print(f"⚠️ Nota descartada por duración demasiado larga: {duracion:.2f}s")
                    continue
                if duracion > 0.02:  # descartar eventos muy breves
                    figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                    notas_json.append({
                        "nota": nota_actual,
                        "inicio": round(inicio, 3),
                        "duracion": round(max(duracion, 0.03), 3),
                        "compas": compas,
                        "figura": figura,
                        "tempo": int(tempo)
                    })
                inicio = t

        # Agregar la última nota que se estaba tocando al final del audio
        duracion = pitch_data[-1][0] - inicio
        if 0.02 < duracion < 5:  # límite máximo de duración razonable
            figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
            notas_json.append({
                "nota": nota_actual,
                "inicio": round(inicio, 3),
                "duracion": round(max(duracion, 0.03), 3),
                "compas": compas,
                "figura": figura,
                "tempo": int(tempo)
                })
        if notas_json and notas_json[-1]["duracion"] < 0.05:
            print(f"⚠️ Nota final descartada por ser demasiado corta: {notas_json[-1]['duracion']}s")
            notas_json = notas_json[:-1]

# 3) Ahora imprimimos antes y después de filtrar los últimos 2s
print(f"\n=== Antes de filtrar últimos 2 s, notas_json tiene {len(notas_json)} elementos ===")
for n in notas_json:
    print(f"   → inicio={n['inicio']:.2f}s, dur={n['duracion']:.3f}s")

duracion_audio_trim = librosa.get_duration(y=y, sr=sr)

#Filtrar notas muy tardías (últimos 2s) que pueden ser errores de pitch
# Usamos duracion_audio_trim en lugar de pitch_data[-1][0]:
#notas_json = [
#    n for n in notas_json
#    if n["inicio"] < duracion_audio_trim - 2.0 or n["duracion"] >= 0.1
#]

print(f"\n=== Después de filtrar últimos 2 s, notas_json tiene {len(notas_json)} elementos ===")
for n in notas_json:
    print(f"   → inicio={n['inicio']:.2f}s, dur={n['duracion']:.3f}s")

with open("notas_detectadas.json", "w") as f:
    json.dump(notas_json, f, indent=2)

#Testeo con una devolucion de un archivo .wav
# Cargar notas desde el JSON
with open("notas_detectadas.json", "r") as f:
    notas = json.load(f)
if not notas:
    print("⚠️ No se detectaron notas válidas. Abortando reconstrucción.")
    exit()

# Frecuencia de muestreo para el audio de salida
sr = 16000

# Función para generar una onda senoidal por nota
def generar_onda(freq, duracion, sr=16000, volumen=1.0):
    # t: vector temporal
    t = np.linspace(0, duracion, int(sr * duracion), False)

    # --- Construimos una envolvente ADSR muy simple ---
    env = np.ones_like(t)
    ataque_sec = 0.01   # 10 ms de ataque
    decay_sec  = 0.1    # 100 ms de decay
    sustain_lv = 0.8    # nivel de sustain

    # convertir a muestras
    n_ataque = int(sr * ataque_sec)
    n_decay  = int(sr * decay_sec)

    # ataque (ramp up)
    if n_ataque < len(env):
        env[:n_ataque] = np.linspace(0, 1, n_ataque)

    # decay (ramp down a sustain_lv)
    inicio_decay = n_ataque
    fin_decay    = n_ataque + n_decay
    if fin_decay < len(env):
        env[inicio_decay:fin_decay] = np.linspace(1, sustain_lv, n_decay)
        env[fin_decay:] = sustain_lv
    else:
        env[inicio_decay:] = np.linspace(1, sustain_lv, len(env) - inicio_decay)

    # --- finalmente la senoide por nota con la envolvente aplicada ---
    onda = volumen * env * np.sin(2 * np.pi * freq * t)
    return onda.astype(np.float32)

# Crear la pista de audio completa
# Ajustar duración del output al input si es necesario
# Ajustar duración del output al input si es necesario
# Calcular RMS del audio original por ventanas
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)

# 1) Volvemos a leer el JSON (para asegurarnos de la ruta actual)
with open("notas_detectadas.json", "r") as f:
    notas = json.load(f)
if not notas:
    print("⚠️ No se detectaron notas válidas. Abortando reconstrucción.")
    exit()

# 2) Leemos el WAV original para medir su duración real
audio_original, sr_original = sf.read(filepath)  # filepath viene de tu cargar_audio(...)
dur_audio = len(audio_original) / sr_original

# 3) Calculamos la última nota del JSON
dur_json = max(n["inicio"] + n["duracion"] for n in notas)

# 4) Escogemos la duración máxima
dur_max = max(dur_audio, dur_json)

# 5) Precreamos un buffer lleno de ceros de la longitud necesaria
total_samples = int(np.ceil(dur_max * sr_original))
audio_total = np.zeros(total_samples, dtype=np.float32)
tiempo_actual = 0.0

for nota in notas:
    nombre = nota["nota"]
    inicio = nota["inicio"]
    duracion = nota["duracion"]
    freq = notas_dict.get(nombre, None)

    if freq is None:
        continue

    # Evitar notas excesivamente largas por error
    if duracion > 5.0:
        continue

    # Calcular energía (RMS) local para ajustar volumen
    rms_local = next((r for t_, r in zip(rms_times, rms) if abs(t_ - inicio) < 0.05), 0.03)
    volumen = np.clip(rms_local * 3, 0.05, 1.0)

    if rms_local < 0.01:
        continue  # evitar sonidos en zonas silenciosas

    # Insertar silencio si la nota no arranca justo después de la anterior
    if inicio > tiempo_actual:
        silencio = np.zeros(int(sr * (inicio - tiempo_actual)))
        audio_total = np.concatenate((audio_total, silencio))
        tiempo_actual = inicio

    # Generar onda y sumarla al audio
    onda = generar_onda(freq, duracion, sr, volumen)
    audio_total = np.concatenate((audio_total, onda))
    tiempo_actual += duracion

# Asegurarse que la duración final coincida con el input original
# Calcular duración real del archivo WAV original (antes del resampleo estéreo)
expected_duration = librosa.get_duration(path=filepath)
actual_duration = librosa.get_duration(y=audio_total, sr=sr)

if actual_duration > expected_duration:
    print(f"⚠️ Duración excedida por {actual_duration - expected_duration:.2f}s, recortando.")
    audio_total = audio_total[:int(expected_duration * sr)]
elif actual_duration < expected_duration:
    padding = np.zeros(int((expected_duration - actual_duration) * sr))
    audio_total = np.concatenate((audio_total, padding))

# Normalizar para evitar clipping y controlar el volumen
rms = np.sqrt(np.mean(audio_total**2))
if rms > 0.5:
    print(f"⚠️ RMS alto ({rms:.2f}), bajando volumen.")
    audio_total *= 0.7  # reducir volumen general si está muy fuerte
# Normalizar (re-asegurar que el valor máximo sea 1.0 o menos)
if np.max(np.abs(audio_total)) > 0:
    if len(audio_total) < 10 or np.all(audio_total == 0):
        print("⚠️ Error: El audio generado está vacío o contiene solo silencio.")
        exit()
    audio_total = audio_total / np.max(np.abs(audio_total))


# Guardar en un archivo WAV
sf.write("reconstruccion.wav", audio_total, sr)
print("Archivo 'reconstruccion.wav' generado correctamente.")

# Solución: revisar si el final está vacío y forzar un fade out si es necesario
if np.max(np.abs(audio_total[-sr * 2:])) < 0.01:  # Últimos 2 segundos muy silenciosos
    print("⚠️ El final del audio reconstruido está silencioso. Se aplicará fade-out o corrección.")
    duracion_restante = expected_duration - librosa.get_duration(y=audio_total, sr=sr)
    if duracion_restante > 0:
        padding = np.zeros(int(sr * duracion_restante))
        audio_total = np.concatenate((audio_total, padding))
#Chequeo con el usuario
# abrir_wav("reconstruccion.wav")
# confirm = input("¿La reconstrucción suena similar al archivo original? (s/n): ").strip().lower()
# if confirm == 's':
#     with open("notas_detectadas.json", "w") as f:
#         json.dump(notas_json, f, indent=2)
#     print("✅ Archivo JSON exportado correctamente.")
# else:
#     print("❌ Proceso detenido. La reconstrucción no fue satisfactoria.")
#     exit()

def exportar_json_si_confirmado(notas_json):
    confirmar = input("¿Querés exportar las notas a un .json? (s/n): ").strip().lower()
    if confirmar == 's':
        # Paso extra: eliminar notas muy cortas dentro del último medio segundo del audio original
        umbral_tiempo_final = expected_duration - 0.5  # últimos 0.5 segundos

        notas_json_filtradas = []
        for n in notas_json:
            if n["inicio"] > umbral_tiempo_final and n["duracion"] < 0.05:
                print(f"⚠️ Nota descartada cerca del final: {n['nota']} en t={n['inicio']}s dur={n['duracion']}s")
                continue
            notas_json_filtradas.append(n)

        # Guardamos el nuevo JSON limpio
        with open("notas_detectadas.json", "w") as f:
            json.dump(notas_json_filtradas, f, indent=2)
        print("✅ Archivo JSON guardado.")
    else:
        print("❌ No se guardó el archivo JSON.")