import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json
import os
# Asegurarse de que la ruta al archivo JSON es correcta
# Aquí asumimos que el archivo JSON se encuentra en la carpeta "JsonFiles" dentro de "ParteDeJuli"
ruta_json = os.path.join(os.path.dirname(__file__), "..", "ParteDeJuli", "JsonFiles", "notas_detectadas.json")
ruta_json = os.path.abspath(ruta_json)

# Cargar notas desde el archivo generado
with open(ruta_json, "r") as f:
    datos = json.load(f)
notas_detectadas = [n["nota"] for n in datos]

# Lista de notas válidas para el violín (G3 a A7)
note_order = [
    "G3", "A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4", "B4",
    "C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6", "D6", "E6",
    "F6", "G6", "A6", "B6", "C7", "D7", "E7", "F7", "G7", "A7"
]
note_positions = {note: i - note_order.index("E4") for i, note in enumerate(note_order)}

def dibujar_notas_violin(notas):
    y_notas = []
    for nota in notas:
        if nota not in note_positions:
            raise ValueError(f"Nota fuera del rango del violín o no soportada: {nota}")
        y_notas.append(note_positions[nota] * 0.5)

    # Ajustar rango del gráfico
    extra_space = 2
    y_min = min(-1, int(min(y_notas)) - extra_space)
    y_max = max(5, int(max(y_notas)) + extra_space)

    fig, ax = plt.subplots(figsize=(max(5, len(notas) * 1), 3))
    ax.set_xlim(0, len(notas) + 1)
    ax.set_ylim(y_min, y_max)

    # Dibujar pentagrama
    for i in range(5):
        y = i
        ax.plot([0, len(notas) + 1], [y, y], color='black')

    # Dibujar solo la cabeza de la nota (sin plica)
    for i, y_nota in enumerate(y_notas):
        x = i + 1
        ax.add_patch(patches.Ellipse((x, y_nota), 0.4, 0.28, color='black'))  # óvalo achatado

        # Dibujar líneas adicionales si es necesario
        if y_nota < 0:
            y = 0
            while y >= y_nota:
                ax.plot([x - 0.3, x + 0.3], [y, y], color='black')
                y -= 0.5
        elif y_nota > 4:
            y = 4
            while y <= y_nota:
                ax.plot([x - 0.3, x + 0.3], [y, y], color='black')
                y += 0.5

    ax.axis('off')
    plt.title("Notas para violín (sin plica): " + ", ".join(notas))
    plt.show()

notas_detectadas = [n for n in notas_detectadas if n in note_positions]
# Ejemplo de uso
dibujar_notas_violin(notas_detectadas)

