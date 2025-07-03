# INSTRUCCIONES PARA ABRIR EL PROYECTO EN OTRA PC

1. ABRIR LA TERMINAL EN LA CARPETA "ParteDeJuli"

cd ...

2. Creaar el entorno VIRTUAL

python -m venv .libreriasRaiz

3. ACTIVAR EL ENTORNO VIRTUAL:
   .\.libreriasRaiz\Scripts\Activate.ps1


4. INSTALAR LAS LIBRERÍAS:
   pip install -r requirements.txt

5. EJECUTAR EL SCRIPT PRINCIPAL:
   python LeerArchivoYnota.py

# CUALQUIER CAMBIO EN LIBRERÍAS
Si se instala algo nuevo, se actualiza el archivo con:
   pip freeze > requirements.txt

