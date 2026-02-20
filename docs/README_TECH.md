# 📖 ALGARROBO_BASE — Documentación Técnica
**Versión**: 1.0 | **Fecha**: 2026-02-19 | **Stack**: Vanilla JS + FastAPI + PostgreSQL

---

## 1️⃣ OVERVIEW

### Propósito
**Geoportal Municipal de Algarrobo** — Plataforma web de gestión integral de proyectos de inversión pública para la Ilustre Municipalidad de Algarrobo, Chile. Permite administrar el ciclo completo de proyectos: creación, seguimiento, geolocalización, documentación, reportería y análisis.

### Arquitectura General
```
┌─────────────────────────────────────────────────┐
│                  FRONTEND (MPA)                 │
│  HTML + Vanilla JS + TailwindCSS CDN            │
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Login   │ │  Views   │ │  Admin   │        │
│  │ index.html│ │ division/│ │ admin/   │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       └─────────────┼───────────┘               │
│                     │                            │
│  ┌──────────────────┴────────────────┐          │
│  │     Shared Scripts (globals)      │          │
│  │  api.js · router.js · layout.js   │          │
│  │  utils.js · help.js               │          │
│  └──────────────┬────────────────────┘          │
└─────────────────┼───────────────────────────────┘
                  │ HTTPS (fetch)
┌─────────────────┼───────────────────────────────┐
│  BACKEND        │                               │
│  FastAPI (app21.py) — Monolito Python           │
│  JWT Auth · REST API · CORS                     │
└─────────────────┼───────────────────────────────┘
                  │
┌─────────────────┼───────────────────────────────┐
│  DATABASE                                       │
│  PostgreSQL (Neon Cloud)                        │
│  Schemas: database/, proyectos, triggers        │
└─────────────────────────────────────────────────┘
```

### Niveles de Acceso
| Nivel | Rol | Directorio | Permisos |
|-------|-----|-----------|----------|
| 10 | Admin General | `admin_general/` | CRUD completo + Administración |
| 11 | Admin Proyectos | `admin_proyectos/` | CRUD proyectos (sin admin) |
| 12 | Director Obras | `director_obras/` | Solo lectura + filtros |

---

## 2️⃣ API REFERENCE — Frontend Scripts

### `api.js` — HTTP Client

**Objeto Global**: `api`

| Método | Firma | Descripción | Retorno |
|--------|-------|-------------|---------|
| `request` | `(endpoint, options?, responseType?)` | Método base. Inyecta Bearer token. Maneja 401 con auto-logout. | `Promise<any>` |
| `get` | `(endpoint, options?)` | GET request | `Promise<JSON>` |
| `getBlob` | `(endpoint, options?)` | GET que retorna Blob (archivos) | `Promise<Blob>` |
| `post` | `(endpoint, data, options?)` | POST. Detecta FormData vs JSON automáticamente | `Promise<JSON>` |
| `put` | `(endpoint, data, options?)` | PUT con misma lógica que post | `Promise<JSON>` |
| `delete` | `(endpoint, options?)` | DELETE request | `Promise<JSON>` |

**Configuración**:
```javascript
const API_CONFIG = {
    BASE_URL: "https://186.67.61.251:8000",
    get token() { return localStorage.getItem('authToken'); }
};
```

**Tipos de respuesta** (`responseType`):
- `'json'` (default) — `response.json()`
- `'blob'` — `response.blob()`
- `'text'` — `response.text()`
- `'raw'` — Response object sin procesar

---

### `router.js` — Auth Guard & Routing

**Constantes Globales**:
- `BASE = "/ALGARROBO_BASE"` — Base path para todas las rutas
- `token` — JWT extraído al cargar el script
- `userData` — Objeto usuario parseado de localStorage

| Función | Firma | Descripción |
|---------|-------|-------------|
| `checkLoginStatus()` | `() → [token, userData]` | Valida sesión activa. Redirige a login si inválida. Ejecuta automáticamente al cargar. |
| `verificarRutaPermitida(user)` | `(user) → boolean` | Compara path actual contra `diccionarioRutas[nivel]` |
| `logout()` | `() → void` | Limpia localStorage y redirige a login |
| `toggleUserMenu()` | `() → void` | Toggle del dropdown de usuario |
| `toggleNotifications()` | `() → void` | Placeholder (no implementado) |
| `getKey(seed)` | `(string) → string` | Decodifica API key ofuscada via XOR |

**Diccionario de Rutas**:
```javascript
diccionarioRutas = {
    10: [/* 6 rutas admin_general */],
    11: [/* 5 rutas admin_proyectos */],
    12: [/* 5 rutas director_obras */]
};
```

---

### `layout.js` — UI Components

| Función | Firma | Descripción |
|---------|-------|-------------|
| `renderHeader(containerId?)` | `(string) → void` | Genera header con logo, notificaciones y menú de usuario. Default: `"headerRender"` |
| `renderSidebar(containerId?)` | `(string) → void` | Genera sidebar con navegación. Módulos extra para nivel 10. Default: `"asideRender"` |
| `showToast(message, type?)` | `(string, string) → void` | Toast notification con auto-dismiss (4s). Types: `'success'`, `'error'`, `'warning'`, `'info'` |

**Auto-ejecución**: `renderHeader()` y `renderSidebar()` se invocan al final del archivo (top-level).

---

### `utils.js` — Utility Functions

**Objeto Global**: `utils`

| Método | Firma | Descripción | Retorno |
|--------|-------|-------------|---------|
| `formatCurrency(value)` | `(number) → string` | Formato CLP: `$1.234.567` | `string` |
| `formatDate(dateString)` | `(string) → string` | Formato `DD/MM/YYYY` locale `es-CL` | `string` |
| `getStatusClass(status)` | `(string) → string` | Mapea estado a clase CSS badge | `string` |
| `serializeForm(formElement)` | `(HTMLFormElement) → object` | FormData a plain object | `object` |
| `formatCompactNumber(number)` | `(number) → string` | `$1.2M`, `$500K`, `$1.234` | `string` |
| `fillSelect(id, items, valueField, textField, placeholder?)` | `(...) → void` | Llena un `<select>` preservando valor actual | `void` |

---

### `help.js` — Contextual Help System

| Función | Firma | Descripción |
|---------|-------|-------------|
| `showHelpModal(viewName)` | `(string) → void` | Muestra modal de ayuda con contenido de `helpContent[viewName]` |
| `closeHelpModal(event?)` | `(Event?) → void` | Cierra modal. Soporta click outside y tecla ESC |
| `createHelpButton(viewName)` | `(string) → void` | Crea FAB flotante (bottom-right) que abre la ayuda |

**Vistas soportadas**: `dashboard`, `proyecto`, `informe`, `calendario`, `mapa`, `hitos`, `observacion`, `documento`, `geomapas`, `user`, `analisis`, `chat`, `vecinos`

---

## 3️⃣ GUÍA DE IMPLEMENTACIÓN

### Crear una nueva vista protegida

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <!-- 1. SIEMPRE cargar router primero (ejecuta auth guard) -->
    <script src="../../../script/router.js"></script>
    <script src="../../../script/api.js"></script>
    <script src="../../../script/utils.js"></script>
    
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Vista - Geoportal Municipal</title>
    
    <!-- 2. CDNs (orden importa) -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <!-- 3. Contenedores para layout -->
    <div id="headerRender"></div>
    <div class="flex">
        <div id="asideRender"></div>
        <main class="flex-1 p-6">
            <!-- Contenido de la vista -->
        </main>
    </div>
    
    <!-- 4. Layout + Help al final del body -->
    <script src="../../../script/layout.js"></script>
    <script src="../../../script/help.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => createHelpButton('miVista'));
    </script>
    
    <!-- 5. Lógica de negocio -->
    <script>
        document.addEventListener('DOMContentLoaded', async () => {
            try {
                const data = await api.get('/mi-endpoint');
                // Renderizar...
            } catch (error) {
                showToast(error.message, 'error');
            }
        });
    </script>
</body>
</html>
```

### Realizar una petición autenticada

```javascript
// GET
const projects = await api.get('/proyectos');

// POST con JSON
const newProject = await api.post('/proyectos', {
    nombre: 'Nuevo Proyecto',
    monto: 50000000,
    area_id: 1
});

// POST con archivo (FormData)
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('proyecto_id', '123');
const uploaded = await api.post('/documentos/upload', formData);

// Descargar archivo
const blob = await api.getBlob('/documentos/123/download');
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'archivo.pdf';
a.click();
URL.revokeObjectURL(url);
```

### Consideraciones de Performance
1. **Chart.js**: Destruir instancias antes de recrear: `if (charts[id]) charts[id].destroy();`
2. **DOM queries**: Cachear resultados de `getElementById` si se usan múltiples veces.
3. **Fetch**: No hay AbortController — peticiones no se cancelan al navegar.
4. **TailwindCSS CDN**: Genera CSS en runtime (~200ms de blocking time en primera carga).

### Endpoints Principales del Backend

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/login` | Autenticación → JWT |
| GET | `/proyectos` | Lista todos los proyectos |
| POST | `/proyectos` | Crear proyecto |
| PUT | `/proyectos/{id}` | Actualizar proyecto |
| DELETE | `/proyectos/{id}` | Eliminar proyecto |
| GET | `/hitos/proyecto/{id}` | Hitos de un proyecto |
| POST | `/documentos/upload` | Subir documento |
| GET | `/documentos/{id}/download` | Descargar documento |
| GET | `/observaciones/proyecto/{id}` | Observaciones |
| GET | `/areas` | Catálogo de áreas |
| GET | `/estados` | Catálogo de estados |
| GET | `/usuarios` | Lista de usuarios |
