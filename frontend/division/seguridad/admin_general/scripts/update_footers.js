const fs = require('fs');
const path = require('path');

const VIEW_MAP = {
    "vista1.html": "Resumen Ejecutivo",
    "vista2.html": "Tendencia Reciente",
    "vista3.html": "Comparativo Temporal",
    "vista4.html": "Estacionalidad Mensual",
    "vista5.html": "Delitos Críticos",
    "vista6.html": "Evolución por Delito",
    "vista7.html": "Evolución Histórica",
    "vista8.html": "Correlaciones",
    "vista9.html": "Puntos Débiles",
    "vista10.html": "Comparativa Regional",
    "vista11.html": "Ranking Histórico",
    "vista12.html": "Comparativa Nacional",
    "vista13.html": "Comparativa con Comunas Similares",
    "vista14.html": "Aporte Regional",
    "vista15.html": "Efectividad Policial",
    "vista16.html": "Gravedad (IDI)",
    "vista17.html": "Proyección Gravedad",
    "vista18.html": "Gravedad por Delito",
    "vista19.html": "IDI Comparativo",
    "vista20.html": "Tendencia 20 Años",
    "vista21.html": "Proyecciones y Rachas",
    "vista22.html": "Priorización Estratégica",
    "vista23.html": "Decisiones Tácticas",
    "vista24.html": "Reporte Ejecutivo",
    "vista25.html": "Auditoría Técnica"
};

const BASE_DIR = path.join(__dirname, '../vistas2');

Object.entries(VIEW_MAP).forEach(([filename, title]) => {
    const filepath = path.join(BASE_DIR, filename);

    if (!fs.existsSync(filepath)) {
        console.log(`Skipping ${filename} (not found)`);
        return;
    }

    let content = fs.readFileSync(filepath, 'utf8');

    if (content.includes('Nota Metodológica')) {
        console.log(`Skipping ${filename} (already has footer)`);
        return;
    }

    const footer = `
<!-- Nota Metodológica -->
<div class="row" style="margin-top: 2rem;">
    <div style="background-color: #f8fafc; border-left: 4px solid #cbd5e1; padding: 1rem; border-radius: 4px; color: #64748b; font-size: 0.85rem; line-height: 1.5;">
        <strong>Nota Metodológica:</strong> Esta vista presenta un análisis detallado de <strong>${title}</strong>, permitiendo evaluar patrones y tendencias clave para la toma de decisiones estratégicas basadas en evidencia.
    </div>
</div>
`;

    const scriptIdx = content.lastIndexOf('<script');
    if (scriptIdx !== -1) {
        const newContent = content.slice(0, scriptIdx) + footer + "\n" + content.slice(scriptIdx);
        fs.writeFileSync(filepath, newContent, 'utf8');
        console.log(`Updated ${filename}`);
    } else {
        const newContent = content + "\n" + footer;
        fs.writeFileSync(filepath, newContent, 'utf8');
        console.log(`Updated ${filename} (appended)`);
    }
});
