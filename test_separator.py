import inspect
from audio_separator.separator import Separator

print("========== Separator SIGNATURE ==========")
print(inspect.signature(Separator.__init__))

print("\n\n========== Separator SOURCE ==========")
try:
    print(inspect.getsource(Separator.__init__))
except:
    print("No se pudo cargar el código fuente")
