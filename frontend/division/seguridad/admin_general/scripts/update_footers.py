import os
import re

VIEW_MAP = {
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
}

BASE_DIR = r"d:\GitHub\ALGARROBO_BASE\frontend\division\seguridad\admin_general\vistas2"

for filename, title in VIEW_MAP.items():
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Skipping {filename} (not found)")
        continue
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "Nota Metodológica" in content:
        print(f"Skipping {filename} (already has footer)")
        continue

    # Create Footer HTML
    footer = f"""
<!-- Nota Metodológica -->
<div class="row" style="margin-top: 2rem;">
    <div style="background-color: #f8fafc; border-left: 4px solid #cbd5e1; padding: 1rem; border-radius: 4px; color: #64748b; font-size: 0.85rem; line-height: 1.5;">
        <strong>Nota Metodológica:</strong> Esta vista presenta un análisis detallado de <strong>{title}</strong>, permitiendo evaluar patrones y tendencias clave para la toma de decisiones estratégicas basadas en evidencia.
    </div>
</div>
"""
    
    # Insert before <script> tag
    # Use explicit <script> usually near the end
    script_idx = content.rfind("<script")
    if script_idx != -1:
        new_content = content[:script_idx] + footer + "\n" + content[script_idx:]
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {filename}")
    else:
        # Append to end if no script found
        new_content = content + "\n" + footer
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {filename} (appended to end)")
