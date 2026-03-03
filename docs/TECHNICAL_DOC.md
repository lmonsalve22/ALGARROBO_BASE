# 📝 Documentación Técnica — ALGARROBO_BASE: Módulo Seguridad v2
**Actualizado**: 2026-03-03 | **Post-Refactoring Ciclo 1**

---

## 1. OVERVIEW

**Módulo Seguridad** es un dashboard de inteligencia delictual municipal para la Ilustre Municipalidad de Algarrobo (ALGARROBO_BASE). Procesa datos oficiales de Carabineros (STOP) y el Ministerio del Interior (CEAD), genera análisis de IA mediante GLM-4-Flash (BigModel) y permite exportar reportes PDF profesionales.

### Arquitectura General

```
dashboard.html
    ↓ (scripts síncronos)
[Config] data.js + data_cead.js + config/columns.js
    ↓
[Core]   logger.js → DataManager.init()
    ↓ (fetch paralelo con Promise.allSettled)
[Data]   STOP (.gz) + CEAD (.gz) + Union Taxonomy + Cluster Config
    ↓ (evento: dataManagerLoaded)
[Legacy] window.STATE_DATA + window.STATE_DATA_CEAD
    ↓ (evento: viewLoaded por cada vista)
[IA]     IAModuleV2.fetchAllAnalyses()  ←→  IAModule.generateAllInterpretations()
    ↓
[View]   App.loadView(viewName) → fetch vistaX.html → executeScripts()
    ↓
[PDF]    PDFModule.exportReport() | App.exportPdf()
```

---

## 2. API REFERENCE

### `DataManager`

**Módulo**: `js/data_manager.js`  
**Patrón**: Singleton con estado centralizado

#### `DataManager.init(codcom?)`
Inicializa el módulo de datos. Cancela peticiones previas en curso si se llama nuevamente.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `codcom` | `number?` | Código de comuna. Si omitido, lee de `?codcom=` en URL |

**Retorno**: `Promise<void>`  
**Dispara**: `CustomEvent('dataManagerLoaded', { detail: { meta, stop, cead } })`

```javascript
// Uso
await DataManager.init(5602);
// o vía URL: dashboard.html?codcom=5602
```

#### `DataManager._abortAllPending()`
Cancela todas las peticiones HTTP en curso. Se llama automáticamente en re-inits.

#### `DataManager.state`
Estado global del módulo:

```javascript
{
    isLoaded: boolean,
    isLoading: boolean,
    _controllers: AbortController[],  // peticiones activas
    union: { data, byStopName, byCeadCode },
    stop: { data, history, totalHistory, currentWeek, weekDetail },
    cead: { data, history, totalHistory, currentPeriod, periodDetail },
    meta: { comuna, region, provincia, clusterConfig }
}
```

---

### `App`

**Módulo**: `js/app.js`  
**Patrón**: Singleton-Object

#### `App.init()`
Punto de entrada. Carga sidebar, vincula eventos globales, carga vista por defecto.

#### `App.loadView(viewName)`
Carga una vista HTML en `#viewContainer`.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `viewName` | `string` | Nombre de vista (ej. `'vista1'`) |

**Dispara**: `CustomEvent('viewLoaded', { detail: { viewName } })`

#### `App.exportPdf()`
Export simplificado (5 vistas, sin portada/TOC). Deshabilita animaciones de Chart.js durante captura.

---

### `IAModuleV2`

**Módulo**: `js/ia2.js`  
**Patrón**: Module Object (5 vistas estratégicas de Seguridad)

#### Eventos escuchados:
| Evento | Acción |
|---|---|
| `dataManagerLoaded` | Revisa caché; si vacío, dispara `fetchAllAnalyses()` |
| `viewLoaded` | Llama `updateAllViews(hasError)` para actualizar DOM |

#### `IAModuleV2.fetchAllAnalyses()`
Realiza 1 petición HTTP a BigModel API con contexto de 5 vistas. Timeout: 45s.  
**Retorno**: `Promise<void>`. Estado actualizado en `IAModuleV2.cache`.

#### `IAModuleV2.saveCache(data)`
Guarda análisis en `localStorage`. Valida tamaño antes de escribir. Limpia caches antiguos si `QuotaExceededError`.

---

### `IAModule`

**Módulo**: `js/ia.js`  
**Patrón**: Module Object (25+ vistas clásicas)

#### `IAModule.generateAllInterpretations()`
Genera interpretaciones para todas las vistas. Con caché TTL 7 días.  
**Retorno**: `Promise<object>` — mapa `{ vista1: string, vista2: string, ... }`

#### `IAModule.getInterpretation(viewId)`
Retorna la interpretación para una vista específica. Si la carga está en curso, espera con timeout de 30s.

---

### `RID.View`

**Módulo**: `js/utils/view-controller.js`  
**Patrón**: Namespace / Utility

#### `RID.View.init(callback, options?)`
Inicializa una vista cuando los datos estén listos.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `callback` | `async (S, C) => void` | Función de inicialización. `S` = STATE_DATA, `C` = COLS |
| `options.source` | `'stop' \| 'cead'` | Fuente de datos a esperar (default: `'stop'`) |

```javascript
// Uso en cualquier vistaX.html:
RID.View.init(async (S, C) => {
    const casos = S.allDataHistory.filter(r => r[C.ID_SEMANA] === S.semanaId);
    // ...renderizar
});
```

---

### `PDFModule`

**Módulo**: `js/pdf.js`  
**Patrón**: Singleton-Object con estado de progreso

#### `PDFModule.exportReport()`
Export completo con portada, resumen ejecutivo, TOC, 45 vistas y contraportada.

#### `PDFModule.showEnhancedOverlay(totalViews)`
Muestra overlay de progreso. Inicia `setInterval` para reloj de tiempo.  
⚠️ **Siempre** llamar `hideEnhancedOverlay()` en `finally`.

---

### `RID.UI` / `UIHelper`

**Módulo**: `js/utils/ui-helper.js`

| Método | Descripción |
|---|---|
| `renderKpi(valId, deltaId, value, deltaPct, inverse, suffix)` | Renderiza KPI con indicador de cambio |
| `setText(id, text)` | Asigna `textContent` con null-safety |
| `setHtml(id, html)` | Asigna `innerHTML` — **solo con HTML interno** |
| `renderColoredPercent(id, pct, inverse)` | Porcentaje coloreado (rojo/verde) |
| `fillHeaders(comuna, semana)` | Rellena todos los `.comuna-fill` y `.semana-fill` |
| `formatNumber(n)` | Formato numérico chileno (`Intl.NumberFormat es-CL`) |

---

### `ChartHelper`

**Módulo**: `js/utils/chart-helper.js`

| Método | Descripción |
|---|---|
| `createBarChart(id, labels, datasets, opts?)` | Gráfico de barras con gradientes |
| `createLineChart(id, labels, datasets, opts?, trendline?)` | Línea con línea de tendencia opcional |
| `createDoughnutChart(id, labels, data, centerText?, opts?)` | Donut con texto central |
| `destroyAllCharts()` | Destruye todas las instancias Chart.js activas |
| `formatNumber(value, decimals?)` | Formato es-CL |
| `getDelitoColor(name)` | Color semántico por tipo de delito |

---

## 3. EVENTOS DEL SISTEMA

| Evento | Dispatcher | Listener(s) | Payload |
|---|---|---|---|
| `dataManagerLoaded` | `DataManager` | `IAModuleV2`, `IAModule`, `dashboard.html` inline | `{ meta, stop, cead }` |
| `dataCeadLoaded` | `data_cead.js` (legacy) | `RID.View.init` (source: 'cead') | `STATE_DATA_CEAD` |
| `viewLoaded` | `App.loadView()` | `IAModuleV2` | `{ viewName }` |
| `dataManagerError` | `DataManager` | `App` (showErrorUI) | `{ message }` |

---

## 4. GUÍA DE IMPLEMENTACIÓN

### Agregar una nueva vista

```html
<!-- vistas2/vista99.html -->
<div class="card">
    <h2>Mi Vista</h2>
    <div id="miKpi">--</div>
</div>
<script>
RID.View.init(async (S, C) => {
    const ultimaSemana = S.semanaId;
    const datos = S.allDataHistory.filter(r => r[C.ID_SEMANA] === ultimaSemana);
    RID.UI.setText('miKpi', ChartHelper.formatNumber(datos.length));
});
</script>
```

### Esperar datos CEAD

```javascript
RID.View.init(async (S, C) => {
    // S = STATE_DATA_CEAD, C = COLS_CEAD
    console.log(S.periodoDetalle);
}, { source: 'cead' });
```

### Acceder a interpretaciones de IA

```javascript
// En una vista con IAModule (clásico):
const interpretation = await IAModule.getInterpretation('vista1');
document.getElementById('iaText').textContent = interpretation;

// Con IAModuleV2 (Seguridad, 5 vistas):
const text = IAModuleV2.cache?.vista1 || 'Cargando análisis...';
```

---

## 5. CONSIDERACIONES DE PERFORMANCE

| Área | Recomendación |
|---|---|
| **Charts en PDF** | `Chart.defaults.animation = false` durante export (ya implementado en app.js) |
| **DOM queries en loops** | Cachear `getElementById` fuera del loop (pendiente en `pdf.js`) |
| **DecompressionStream** | Solo disponible en Chrome 80+, Firefox 113+, Safari 16.4+ |
| **localStorage** | IAModuleV2 valida tamaño antes de escribir (> 200KB aviso) |
| **AbortController** | DataManager registra y cancela todos los fetches en re-init |

---

## 6. DEPENDENCIAS EXTERNAS

| Librería | Versión | CDN | Propósito |
|---|---|---|---|
| Tailwind CSS | latest | cdn.tailwindcss.com | Layout base |
| Font Awesome | 6.4.0 | cdnjs | Iconografía |
| Chart.js | latest | jsdelivr | Visualizaciones |
| chartjs-plugin-datalabels | 2.x | jsdelivr | Etiquetas en gráficos |
| chartjs-plugin-annotation | 3.x | jsdelivr | Líneas de referencia |
| html2canvas | 1.4.1 | cdnjs | Captura DOM para PDF |
| jsPDF | 2.5.1 | cdnjs | Generación de PDF |
| GLM-4-Flash (BigModel) | API | open.bigmodel.cn | Análisis de IA |

> ⚠️ **Nota de Seguridad**: Los CDNs no tienen SRI implementado. Pendiente de Ciclo 2.
