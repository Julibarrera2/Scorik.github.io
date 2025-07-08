document.addEventListener('DOMContentLoaded', function () {
    const mp3Input = document.getElementById('mp3-upload');
    const instrumentSelect = document.getElementById('instrumentSelect');
    const convertBtn = document.getElementById('convert-btn');

    if (convertBtn) {
        convertBtn.addEventListener('click', async function () {
            const file = mp3Input.files[0];
            const instrument = instrumentSelect.value;
            if (!file || !instrument) {
                alert("Seleccioná instrumento y archivo mp3");
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            // Subir el archivo al backend
            const resp = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await resp.json();

            // Mostrar la imagen generada
            if (data.imagen) {
                document.querySelector('.sheet-image').src = data.imagen;

                // Cambiar tab a "sheet"
                if (window.Alpine) Alpine.store('activeTab', 'sheet');
                else document.querySelector('[x-data]').__x.$data.activeTab = 'sheet';
            }
        });
    }
});
