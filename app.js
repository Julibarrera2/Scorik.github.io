document.addEventListener('DOMContentLoaded', function () {
    const mp3Input = document.getElementById('mp3-upload');
    const instrumentSelect = document.getElementById('instrumentSelect');
    const convertBtn = document.getElementById('convert-btn'); // Mejor por id

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

            // Cambiar el tab a 'sheet' ANTES de tocar el <img>
            if (data.imagen) {
                if (window.Alpine) {
                    Alpine.store('activeTab', 'sheet');
                } else if (document.querySelector('[x-data]')?.__x?.$data) {
                    document.querySelector('[x-data]').__x.$data.activeTab = 'sheet';
                }
                // Esperar que Alpine actualice el DOM
                setTimeout(() => {
                    document.querySelector('.sheet-image').src = data.imagen;
                }, 100);
            }
        });
    }
});
