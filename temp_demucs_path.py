import demucs, site, os
folder = os.path.join(site.getsitepackages()[0], "demucs", "htdemucs")
files = os.listdir(folder)
print("CARPETA DEL MODELO:", folder)
print("ARCHIVOS:", files)
