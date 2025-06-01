const processBtn = document.getElementById('processBtn');
const fileInput = document.getElementById('fileInput');
const instrumentSelect = document.getElementById('instrumentSelect');
const warning = document.getElementById('warning');
const library = document.getElementById('libraryCards');

let sheetCount = 0;

processBtn.addEventListener('click', () => {
const instrument = instrumentSelect.value;
const file = fileInput.files[0];

if (!instrument || !file) {
    warning.style.display = 'block';
    return;
}

warning.style.display = 'none';
sheetCount++;

const col = document.createElement('div');
col.className = 'col-md-4';
col.innerHTML = `
    <div class="card text-center">
    <h4>Sheet #${sheetCount}</h4>
    <button onclick="window.location.href='editor.html'">Edit</button>
    </div>
`;
library.appendChild(col);
});
