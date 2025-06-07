import json
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt

# 1. Cargo el JSON con las notas "extraídas"
with open('notas_detectadas.json', 'r') as f:
    notas = json.load(f)

# Mapa de semitonos relativo a C para convertir "C#4", "A3", etc., a semitono
note_to_semitone = {
    'C': 0,  'C#': 1, 'Db': 1, 
    'D': 2,  'D#': 3, 'Eb': 3, 
    'E': 4,  'F': 5,  'F#': 6, 'Gb': 6,
    'G': 7,  'G#': 8, 'Ab': 8, 
    'A': 9,  'A#': 10,'Bb': 10, 
    'B': 11
}

def nombre_a_freq(nombre):
    """
    Convierte un string tipo "C4", "C#5", "A3", "Eb4", etc. 
    en su frecuencia en Hz usando la fórmula MIDI->Hz.
    """
    # Determinar nota y octava
    if len(nombre) == 2:
        nota = nombre[0]
        accidental = ''
        octave = int(nombre[1])
    else:
        nota      = nombre[0]
        accidental = nombre[1]
        octave     = int(nombre[2])

    nombre_base = nota + accidental
    semitone = note_to_semitone.get(nombre_base, 0)
    midi = 12 * (octave + 1) + semitone
    return 440.0 * 2 ** ((midi - 69) / 12)

# 2. Cargo el audio original para saber su frecuencia de muestreo (sr)
audio_original, sr = sf.read('piano-lento.wav')

# 3. Calculo la duración total necesaria basándome en el último 'inicio + duración'
dur_max = max(n['inicio'] + n['duracion'] for n in notas)
total_samples = int(np.ceil(dur_max * sr))

# Preparo un buffer de ceros para la reconstrucción
recon = np.zeros(total_samples)

# Por cada evento en el JSON, genero un seno en la posición adecuada
for event in notas:
    f = nombre_a_freq(event['nota'])                   # Frecuencia de la nota
    start_sample = int(np.floor(event['inicio'] * sr)) # Muestra de inicio
    dur_samples = int(np.ceil(event['duracion'] * sr)) # Cuántas muestras dura la nota
    t = np.arange(dur_samples) / sr                     # Vector de tiempos para esa nota
    wave = 0.5 * np.sin(2 * np.pi * f * t)              # Onda senoidal (amplitud 0.5)
    recon[start_sample : start_sample + dur_samples] += wave

# 4. Normalizo todo para que no haya clipping y guardo a WAV
recon /= np.max(np.abs(recon))
sf.write('reconstruccion_debug.wav', recon, sr)

# 5. Grafico el espectrograma de los últimos 10 segundos
start_plot = max(0, int((dur_max - 10) * sr))
plt.figure(figsize=(10, 4))
plt.specgram(recon[start_plot:], Fs=sr, NFFT=2048, noverlap=1024, cmap='viridis')
plt.title('Espectrograma de los últimos 10 segundos de la reconstrucción')
plt.ylabel('Frecuencia (Hz)')
plt.xlabel('Tiempo (s)')
plt.colorbar(label='Intensidad (dB)')
plt.tight_layout()
plt.show()
