# 📝 DOCUMENTACIÓN TÉCNICA: ALGARROBO_BASE (Módulo Seguridad)

## 1. OVERVIEW
El módulo de Seguridad de ALGARROBO_BASE es una Single Page Application (SPA) liviana construida sobre estándares web modernos (Vanilla JS, ES2020). Su propósito es centralizar la visualización de datos del sistema STOP y CEAD, proporcionando análisis automáticos mediante modelos de lenguaje (IA) y capacidades de generación de reportes en PDF.

### Arquitectura General
El sistema sigue un patrón modular donde los datos son gestionados por un `DataManager` central, y las vistas son inyectadas dinámicamente según la navegación.

---

## 2. API REFERENCE

### `DataManager` (Global Singleton)
Gestiona la carga, descompresión (Gzip) y normalización de datos.
- **`init(codcom)`**: Inicializa la carga para una comuna específica.
- **`state`**: Objeto que contiene las colecciones `stop` y `cead` ya procesadas.
- **Eventos**: Dispara `dataManagerLoaded` cuando el estado está listo.

### `App` (Layout Manager)
Controla la navegación y el renderizado de vistas.
- **`loadView(viewName)`**: Carga un archivo HTML de la carpeta `vistas2/` en el contenedor principal.
- **`exportPdf()`**: Orquesta la captura de todas las vistas activas para generar un documento PDF.

### `RID.View` (View Controller)
Utility para desacoplar la lógica de las vistas del ciclo de vida del `DataManager`.
- **`init(callback, options)`**: Ejecuta el callback solo cuando los datos necesarios están disponibles en el scope global.

### `IAModuleV2` (IA Analysis)
Interface con BigModel API para interpretaciones estratégicas.
- **`fetchAllAnalyses()`**: Dispara una petición única para obtener el análisis de las 5 vistas estratégicas.
- **`updateAllViews()`**: Inyecta los textos analíticos en los elementos del DOM correspondientes.

---

## 3. GUÍA DE IMPLEMENTACIÓN

### Añadir una nueva Vista Estratégica
1. Crear el archivo `frontend/division/seguridad/admin_general/vistas2/vistaN.html`.
2. Registrar la vista en `dashboard.html` dentro del objeto `VIEW_TITLES` y el array `vistasSeguridad`.
3. (Opcional) Añadir el prompt correspondiente en `ia2.js` si requiere soporte de IA.

### Ejemplo de Inicialización de Vista
```javascript
RID.View.init(async (S, C) => {
    // S contiene STATE_DATA consolidado
    // C contiene los mapeos de columnas (COLS)
    const ctx = document.getElementById('myChart');
    new Chart(ctx, { ... });
});
```

### Consideraciones de Performance
- **Memoria**: Se recomienda llamar a `ChartHelper.destroyAllCharts()` antes de renderizar nuevos gráficos para evitar fugas de memoria.
- **Caché**: Los análisis de IA se almacenan en `localStorage` con un TTL de 2 horas para minimizar costes de API.

---
*Generado por Technical Documentation Agent v1.0.*
