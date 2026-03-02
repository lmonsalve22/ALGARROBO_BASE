let rawData = [];
const url = 'https://raw.githubusercontent.com/Sud-Austral/TRANSPARENCIA_FACIL/refs/heads/main/archivo3.json'

async function cargarJSON() {
    try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP error: ${response.status}`);        
    rawData = await response.json();
    console.log("Datos cargados:", rawData);
    } catch (error) {
    console.error('Error al leer el JSON:', error);
    }
}

cargarJSON();  // llamada inicial

let data = [];
let filteredData = [];
let allMonths = [];

function initializeApp() {
    try {
    data = rawData
    filteredData = [...data];
    
    // Obtener todos los meses únicos
    const allKeys = new Set();
    data.forEach(row => {
        Object.keys(row).forEach(key => {
        if (key !== 'organismo_nombre') allKeys.add(key);
        //if (key !== 'organismo_nombre' || key !== 'padre_org') allKeys.add(key);
        });
    });
    allMonths = Array.from(allKeys); //.sort();
    
    updateStats();
    renderTable();
    setupEventListeners();
    
    // Ocultar loading y mostrar tabla
    document.getElementById('loading').style.display = 'none';
    document.getElementById('data-table').style.display = 'table';
    
    } catch (error) {
    console.error('Error al procesar los datos:', error);
    document.getElementById('loading').innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error al cargar los datos';
    }
}

function updateStats() {
    document.getElementById('total-organismos').textContent = data.length;
    document.getElementById('periodo-analisis').textContent = allMonths.length;
    document.getElementById('ultimo-mes').textContent = allMonths[allMonths.length - 1].replace("_"," ") || '-';
    
    // Calcular promedio general
    let totalSum = 0;
    let totalCount = 0;
    
    data.forEach(row => {
    allMonths.forEach(month => {
        const val = row[month];
        if (val && val > 0) {
        totalSum += val;
        totalCount++;
        }
    });
    });
    
    const promedioGeneral = totalCount > 0 ? (totalSum / totalCount).toFixed(1) : '-';
    document.getElementById('promedio-general').textContent = promedioGeneral;
}

function renderTable() {
    const table = document.getElementById('data-table');
    table.innerHTML = '';

    // Crear header
    const header = document.createElement('thead');
    const headerRow = document.createElement('tr');

    const thOrg = document.createElement('th');
    thOrg.innerHTML = '<i class="fas fa-building"></i> Organismo';
    headerRow.appendChild(thOrg);

    allMonths.forEach(month => {
    const th = document.createElement('th');
    th.textContent = month.replace('_', ' ');
    headerRow.appendChild(th);
    });

    const thAvg = document.createElement('th');
    thAvg.innerHTML = '<i class="fas fa-calculator"></i> Promedio';
    headerRow.appendChild(thAvg);

    header.appendChild(headerRow);
    table.appendChild(header);

    // Crear body
    const body = document.createElement('tbody');

    filteredData.forEach(row => {
    const tr = document.createElement('tr');

    // Celda del nombre del organismo
    const tdName = document.createElement('td');
    tdName.textContent = row.organismo_nombre;
    tdName.title = row.organismo_nombre;
    tr.appendChild(tdName);

    let sum = 0;
    let count = 0;
    const values = [];

    // Celdas de valores mensuales
    allMonths.forEach(month => {
        const val = row[month];
        const td = document.createElement('td');
        
        if (val === 0) {
        td.classList.add('sin-registro');
        td.innerHTML = '<i class="fas fa-times"></i> Sin datos';
        } else if (val) {
        td.textContent = val.toLocaleString();
        sum += val;
        count++;
        values.push(val);
        } else {
        td.textContent = '-';
        }
        
        tr.appendChild(td);
    });

    // Calcular promedio y desviación estándar
    const avg = count > 0 ? sum / count : 0;
    const variance = values.length > 1 ? values.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / values.length : 0;
    const stdDev = Math.sqrt(variance);
    

    // Celda del promedio
    const tdAvg = document.createElement('td');
    tdAvg.classList.add('promedio-cell');
    tdAvg.textContent = count > 0 ? avg.toFixed(1) : '-';
    tr.appendChild(tdAvg);

    // Segunda pasada para agregar tooltips y colores
    const cells = tr.children;
    for (let i = 1; i < cells.length - 1; i++) {
        const td = cells[i];
        const val = row[allMonths[i - 1]];
        
        if (val && val > 0 && avg > 0) {
        const percent = ((val - avg) / avg * 100);
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        //tooltip.textContent = `${percent > 0 ? '+' : ''}${percent.toFixed(1)}% del promedio`;
        tooltip.textContent = `${percent > 0 ? '+' : ''}${percent.toFixed(1)}% del promedio`;

        td.appendChild(tooltip);
        
        // Colorear según desviación del promedio
        if (Math.abs(val - avg) > stdDev * 0.9) {
            td.classList.add('valor-bajo');
        }
        else{
            td.classList.add('valor-alto');
        }
        }
    }
    body.appendChild(tr);
    });

    table.appendChild(body);
}

function setupEventListeners() {
    const searchInput = document.getElementById('search-input');

    // Función para normalizar texto (eliminar acentos y convertir a minúsculas)
    const normalizeText = str => 
        str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

    searchInput.addEventListener('input', (e) => {
        const searchTerm = normalizeText(e.target.value);

        filteredData = data.filter(row => 
            normalizeText(row.organismo_nombre).includes(searchTerm)
        );

        renderTable();
    });
}


// Inicializar la aplicación cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initializeApp, 500); // Simular carga
});