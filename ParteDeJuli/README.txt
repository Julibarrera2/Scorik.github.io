# INSTRUCCIONES PARA ABRIR EL PROYECTO EN OTRA PC

1. ABRIR LA TERMINAL EN LA CARPETA "ParteDeJuli"

cd ParteDeJuli

2. Creaar el entorno VIRTUAL

python -m venv .librerias

3. ACTIVAR EL ENTORNO VIRTUAL:
   .\.librerias\Scripts\Activate.ps1

   (Si da error, ejecutar una sola vez esto:)
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

4. INSTALAR LAS LIBRERÍAS:
   pip install -r requirements.txt

5. EJECUTAR EL SCRIPT PRINCIPAL:
   python LeerArchivoYnota.py

# CUALQUIER CAMBIO EN LIBRERÍAS
Si se instala algo nuevo, se actualiza el archivo con:
   pip freeze > requirements.txt