/**
 * RID SIMULATOR - AI Interpretation Module
 * Generates AI interpretations for all 13 views in a single request
 */

const IAModule = {
    // Decryption utilities
    strToBytes(str) {
        return new TextEncoder().encode(str);
    },

    bytesToStr(bytes) {
        return new TextDecoder().decode(bytes);
    },

    getKey(seed) {
        const OFUSCADO = "VgAMFkZXBBFdUEpXQwFFXRZXA19NXV1XXQdQBVpDFlBIIwMkGxUkEgJcIRAXAUBcBQ==";
        const data = Uint8Array.from(atob(OFUSCADO), c => c.charCodeAt(0));
        const s = this.strToBytes(seed);
        const out = new Uint8Array(data.length);
        for (let i = 0; i < data.length; i++) {
            out[i] = data[i] ^ s[i % s.length];
        }
        return this.bytesToStr(out);
    },

    // API Configuration (initialized in init())
    API_KEY: null,
    API_URL: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    MODEL_NAME: "glm-4-flash",

    // Cache Configuration
    CACHE_PREFIX: 'ia_v3_',
    CACHE_TTL_MS: 7 * 24 * 60 * 60 * 1000, // 7 días

    // State to store interpretations
    interpretations: {},
    isLoaded: false,
    isLoading: false,

    /**
     * Initialize the AI module
     */
    init() {
        this.API_KEY = this.getKey("gfhrsdfsdfseweretfghtddfdf");
    },

    /**
     * Build cache key based on codcom + semanaId
     */
    getCacheKey() {
        const codcom = (window.STATE_DATA?.codcom || window.STATE_DATA_CEAD?.codcom) || 'default';
        const semana = (window.STATE_DATA?.semanaId || window.STATE_DATA_CEAD?.periodoId) || 'unknown';
        return this.CACHE_PREFIX + codcom + '_' + semana;
    },

    /**
     * Load interpretations from localStorage cache
     * @returns {object|null} cached interpretations or null if expired/missing
     */
    loadFromCache() {
        try {
            const key = this.getCacheKey();
            const raw = localStorage.getItem(key);
            if (!raw) return null;

            const cached = JSON.parse(raw);
            const age = Date.now() - (cached.timestamp || 0);

            if (age > this.CACHE_TTL_MS) {
                localStorage.removeItem(key);
                LOG.info('[IA] Cache expirado, se renovará');
                return null;
            }

            LOG.info(`[IA] Cache válido (${(age / 3600000).toFixed(1)}h de ${(this.CACHE_TTL_MS / 3600000)}h)`);
            return cached.data;
        } catch (e) {
            LOG.warn('[IA] Error leyendo cache:', e);
            return null;
        }
    },

    /**
     * Save interpretations to localStorage cache
     */
    saveToCache(data) {
        try {
            const key = this.getCacheKey();
            const payload = JSON.stringify({ timestamp: Date.now(), data });
            localStorage.setItem(key, payload);

            // Limpiar caches antiguos de otras semanas/comunas
            this.cleanOldCaches(key);
        } catch (e) {
            // ERR-009: Handle QuotaExceededError — clean and retry once
            if (e.name === 'QuotaExceededError' || e.code === 22) {
                LOG.warn('[IA] localStorage lleno, limpiando caches antiguos...');
                this.cleanOldCaches(this.getCacheKey());
                try {
                    localStorage.setItem(this.getCacheKey(), JSON.stringify({ timestamp: Date.now(), data }));
                } catch (e2) {
                    LOG.warn('[IA] Cache no guardado tras limpieza:', e2);
                }
            } else {
                LOG.warn('[IA] Error guardando cache:', e);
            }
        }
    },

    /**
     * Remove old cache entries to avoid localStorage bloat
     */
    cleanOldCaches(currentKey) {
        try {
            for (let i = localStorage.length - 1; i >= 0; i--) {
                const k = localStorage.key(i);
                if (k && k.startsWith(this.CACHE_PREFIX) && k !== currentKey) {
                    localStorage.removeItem(k);
                }
            }
        } catch (e) { /* silent */ }
    },

    /**
     * Build the context from current data (STOP or CEAD) for AI interpretation
     */
    buildDataContext() {
        // Source 1: STOP Data (Weekly)
        const hasStop = window.STATE_DATA && window.STATE_DATA.allDataHistory && window.STATE_DATA.allDataHistory.length > 0;
        // Source 2: CEAD Data (Monthly)
        const hasCead = window.STATE_DATA_CEAD && window.STATE_DATA_CEAD.isLoaded && window.STATE_DATA_CEAD.allDataHistory && window.STATE_DATA_CEAD.allDataHistory.length > 0;

        if (!hasStop && !hasCead) {
            return null;
        }

        const context = {
            comunaName: (window.STATE_DATA?.comunaName !== 'Cargando...' ? window.STATE_DATA?.comunaName : window.STATE_DATA_CEAD?.comunaName) || 'La comuna',
            semanaId: 'N/A',
            totalCasos: 0,
            totalCasosAnt: 0,
            totalCasosYearAnt: 0,
            varSemanal: 0,
            varAnual: 0,
            avgZScore: '0.00',
            topDelitos: [],
            alertas: 0,
            alertasCriticas: 0,
            highRiskDelitos: [],
            numDelitos: 0,
            v15_risk: 'BAJO',
            promHist: '0',
            varVsProm: 0,
            mm4s: '0',
            mm8s: '0',
            aceleracion: '0',
            zScoreTotal: '0.00',
            anomalias: 0,
            ceadSummary: "Datos CEAD no disponibles",
            ceadTrend: "Desconocida"
        };

        // --- Process STOP Data (Primary for weekly views) ---
        if (hasStop) {
            const data = window.STATE_DATA.allDataHistory;
            const COLS = window.COLS;
            context.comunaName = window.STATE_DATA.comunaName || context.comunaName;

            const semanaIds = data.map(row => row[COLS.ID_SEMANA]).filter(id => id != null);
            if (semanaIds.length === 0) return context;

            const maxSemana = semanaIds.reduce((a, b) => Math.max(a, b), -Infinity);
            context.semanaId = maxSemana;
            const currentWeekData = data.filter(row => row[COLS.ID_SEMANA] === maxSemana);

            context.totalCasos = currentWeekData.reduce((sum, row) => sum + (row[COLS.CASOS_ACTUAL] || 0), 0);
            context.totalCasosAnt = currentWeekData.reduce((sum, row) => sum + (row[COLS.CASOS_ANT] || 0), 0);
            context.totalCasosYearAnt = currentWeekData.reduce((sum, row) => sum + (row[COLS.CASOS_YEAR_ANT] || 0), 0);
            context.varSemanal = context.totalCasosAnt > 0 ? ((context.totalCasos - context.totalCasosAnt) / context.totalCasosAnt * 100).toFixed(1) : 0;
            context.varAnual = context.totalCasosYearAnt > 0 ? ((context.totalCasos - context.totalCasosYearAnt) / context.totalCasosYearAnt * 100).toFixed(1) : 0;

            let weightedZSum = 0;
            let totalCasesForZ = 0;
            const delitoGroups = {};

            currentWeekData.forEach(row => {
                const z = row[COLS.Z_SCORE] || 0;
                const c = row[COLS.CASOS_ACTUAL] || 0;
                weightedZSum += z * c;
                totalCasesForZ += c;

                const delito = row[COLS.DELITO];
                delitoGroups[delito] = (delitoGroups[delito] || 0) + c;
            });

            context.avgZScore = totalCasesForZ > 0 ? (weightedZSum / totalCasesForZ).toFixed(2) : "0.00";
            context.topDelitos = Object.entries(delitoGroups)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([name, count]) => `${name}: ${count} casos`);

            context.alertas = currentWeekData.filter(row => row[COLS.Z_SCORE] > 1).length;
            context.alertasCriticas = currentWeekData.filter(row => row[COLS.Z_SCORE] > 2).length;
            context.highRiskDelitos = currentWeekData
                .filter(row => row[COLS.Z_SCORE] > 0.5)
                .sort((a, b) => (b[COLS.Z_SCORE] || 0) - (a[COLS.Z_SCORE] || 0))
                .slice(0, 3)
                .map(row => `${row[COLS.DELITO]} (Z=${(row[COLS.Z_SCORE] || 0).toFixed(2)})`);

            context.numDelitos = currentWeekData.length;
            context.v15_risk = context.avgZScore > 1 ? 'ALTO' : (context.avgZScore > 0.5 ? 'MEDIO' : 'BAJO');

            context.promHist = (currentWeekData.reduce((s, r) => s + (r[COLS.PROMEDIO_HIST] || 0), 0)).toFixed(0);
            context.varVsProm = context.promHist > 0 ? ((context.totalCasos - context.promHist) / context.promHist * 100).toFixed(1) : 0;

            const totalRow = (window.STATE_DATA.allDataHistory_total || []).find(r => r[COLS.ID_SEMANA] === maxSemana);
            context.zScoreTotal = totalRow ? parseFloat(totalRow[COLS.Z_SCORE] || 0).toFixed(2) : "0.00";
            context.anomalias = currentWeekData.filter(r => Math.abs(r[COLS.Z_SCORE] || 0) > 1.5).length;

            const mm4s = totalRow ? (totalRow[COLS.MEDIA_MOVIL_4S] || 0) : 0;
            const mm8s = totalRow ? (totalRow[COLS.MEDIA_MOVIL_8S] || 0) : 0;
            context.mm4s = mm4s.toFixed(1);
            context.mm8s = mm8s.toFixed(1);
            context.aceleracion = mm8s > 0 ? ((mm4s - mm8s) / mm8s * 100).toFixed(1) : 0;
        }

        // --- Process CEAD Data (Integration or Fallback) ---
        if (hasCead) {
            const cead = window.STATE_DATA_CEAD;
            const idxCead = window.COLS_CEAD;
            const ceadData = cead.allDataHistory_total;

            // If No STOP data, use CEAD for basic context strings
            if (!hasStop) {
                context.comunaName = cead.comunaName || context.comunaName;
            }

            const latestCead = ceadData.filter(r => !r[idxCead.IS_FORECAST]).sort((a, b) => b[idxCead.ID_PERIODO] - a[idxCead.ID_PERIODO])[0];

            if (latestCead) {
                context.ceadSummary = `Total Delitos (${latestCead[idxCead.PERIODO_DETALLE] || 'Último Mes'}): ${latestCead[idxCead.CASOS_ACTUAL]}. Alerta: ${latestCead[idxCead.ALERTA] || 'Normal'}.`;
                context.ceadTrend = latestCead[idxCead.TENDENCIA] || "Estable";

                // Fallback for KPIs if STOP is missing
                if (!hasStop) {
                    context.totalCasos = latestCead[idxCead.CASOS_ACTUAL] || 0;
                    context.varSemanal = latestCead[idxCead.VAR_PCT_MES] || 0;
                    context.zScoreTotal = parseFloat(latestCead[idxCead.Z_SCORE] || 0).toFixed(2);
                }
            }
        }

        return context;
    },

    /**
     * Generate all interpretations — uses localStorage cache (7 días / por semana+comuna)
     */
    async generateAllInterpretations() {
        if (this.isLoading) return;
        if (this.isLoaded && Object.keys(this.interpretations).length > 0) {
            return this.interpretations;
        }

        this.isLoading = true;

        try {
            // 1. Intentar cargar desde cache
            const cached = this.loadFromCache();
            if (cached && Object.keys(cached).length > 0) {
                this.interpretations = cached;
                this.isLoaded = true;
                this.isLoading = false;
                LOG.info('[IA] ✅ Interpretaciones cargadas desde cache');
                return this.interpretations;
            }

            // 2. Sin cache válido → llamar API
            const context = this.buildDataContext();
            if (!context) {
                LOG.warn('[IA] No data available for AI interpretation');
                this.isLoading = false;
                return this.getDefaultInterpretations();
            }

            LOG.info('[IA] Cache vacío/expirado, consultando API...');
            const prompt = this.buildPrompt(context);

            const requestBody = {
                model: this.MODEL_NAME,
                messages: [
                    {
                        role: "system",
                        content: "Eres un analista experto en seguridad pública y criminología con un enfoque en comunicación estratégica. Debes generar interpretaciones breves y profesionales para un dashboard de inteligencia delictual municipal. Responde SOLO con el JSON solicitado, sin explicaciones adicionales."
                    },
                    {
                        role: "user",
                        content: prompt
                    }
                ],
                temperature: 0.7,
                max_tokens: 4000
            };

            // ERR-004: AbortController con timeout de 30s para la API
            const controller = new AbortController();
            const fetchTimeoutId = setTimeout(() => controller.abort(), 30000);
            let response;
            try {
                response = await fetch(this.API_URL, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.API_KEY}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestBody),
                    signal: controller.signal
                });
            } finally {
                clearTimeout(fetchTimeoutId);
            }

            if (!response.ok) {
                const errBody = await response.text();
                LOG.error('[IA] API Error:', errBody);
                throw new Error(`API Error: ${response.status} - ${errBody}`);
            }

            const result = await response.json();
            const content = result.choices?.[0]?.message?.content || '';

            // Parse JSON response
            this.interpretations = this.parseAIResponse(content);
            this.isLoaded = true;

            // 3. Guardar en cache para reutilizar durante la semana
            this.saveToCache(this.interpretations);
            LOG.info('[IA] ✅ Interpretaciones generadas y guardadas en cache');

        } catch (error) {
            LOG.error('[IA] Error generating AI interpretations:', error);
            this.interpretations = this.getDefaultInterpretations();
        }

        this.isLoading = false;
        return this.interpretations;
    },

    /**
     * Build the prompt for generating all interpretations
     */

    buildPrompt(context) {
        return `
Analiza los siguientes datos delictuales de ${context.comunaName} y genera interpretaciones estratégicas para las vistas del dashboard.

DATOS DE REFERENCIA:
- Comuna: ${context.comunaName}
- Total casos semana (STOP): ${context.totalCasos}
- Variación semanal: ${context.varSemanal}% | Variación anual: ${context.varAnual}%
- Z-Score Promedio: ${context.avgZScore}
- Alertas STOP: ${context.alertas} (${context.alertasCriticas} críticas)
- Top Delitos: ${context.topDelitos.join(', ')}
- Resumen CEAD: ${context.ceadSummary}

Genera un JSON con la siguiente estructura exacta. Cada interpretación debe ser profesional, de 1-2 oraciones y orientada a la toma de decisiones:

{
  "vista1": "Interpretación general...", 
  "vista2": "Análisis de alertas...",
  "vista3": "Análisis comparativo (${context.totalCasos} casos, Δ${context.varSemanal}% semanal)...",
  "vista4": "Perfil de gravedad y riesgo...",
  "vista5": "Distribución de violencia vs delitos menores...",
  "vista6": "Análisis de correlaciones entre delitos...",
  "vista7": "Tendencia histórica ( STOP )...",
  "vista8": "Patrones estacionales detectados...",
  "vista9": "Correlaciones delictuales...",
  "vista10": "Pronóstico de tendencia ( STOP )...",
  "vista11": "Impacto y simulación...",
  "vista12": "Predicción de peaks...",
  "vista13": "Notas metodológicas...",
  "vista14": "Proyección y regresión lineal...",
  "vista15": "Diagnóstico inmediato de riesgo: ${context.v15_risk}...",
  "vista16": "Análisis demográfico y tasas...",
  "vista17": "Contexto regional y ranking...",
  "vista18": "Aceleración delictual (${context.aceleracion}%)...",
  "vista19": "Normalidad estadística (Z=${context.zScoreTotal})...",
  "vista20": "Resumen ejecutivo integral...",
  "vista21": "Evolución mensual (CEAD)...",
  "vista22": "Comparativa anual (CEAD)...",
  "vista23": "Tendencia sostenida vs hechos aislados...",
  "vista24": "Matriz de variaciones...",
  "vista25": "Distribución territorial..."
}

Responde ÚNICAMENTE con el objeto JSON.`;
    },

    /**
     * Parse the AI response and extract interpretations
     */
    parseAIResponse(content) {
        try {
            // Clean the response - remove markdown code blocks if present
            let cleanContent = content.trim();
            if (cleanContent.startsWith('```json')) {
                cleanContent = cleanContent.slice(7);
            }
            if (cleanContent.startsWith('```')) {
                cleanContent = cleanContent.slice(3);
            }
            if (cleanContent.endsWith('```')) {
                cleanContent = cleanContent.slice(0, -3);
            }
            cleanContent = cleanContent.trim();

            // Try to parse as-is first
            try {
                return JSON.parse(cleanContent);
            } catch (e) {
                // If JSON is truncated, try to fix it
                LOG.warn('JSON truncated, attempting to fix...');

                // Find the last complete key-value pair
                const lastQuoteIndex = cleanContent.lastIndexOf('"');
                if (lastQuoteIndex > 0) {
                    // Try to close the JSON properly
                    let fixedContent = cleanContent.substring(0, lastQuoteIndex + 1);

                    // Check if we need to close the value
                    const afterLastKey = fixedContent.substring(fixedContent.lastIndexOf('": "') + 4);
                    if (!afterLastKey.endsWith('"')) {
                        fixedContent += '"';
                    }

                    // Close the object
                    if (!fixedContent.endsWith('}')) {
                        fixedContent += '\n}';
                    }

                    try {
                        const parsed = JSON.parse(fixedContent);
                        LOG.info('Successfully recovered partial AI response');

                        // ERR-006: Mark truncated values (< 20 chars likely incomplete)
                        Object.keys(parsed).forEach(key => {
                            if (typeof parsed[key] === 'string' && parsed[key].length < 20) {
                                parsed[key] = '[⚠️ parcial] ' + parsed[key];
                            }
                        });

                        // Merge with defaults for missing keys
                        const defaults = this.getDefaultInterpretations();
                        return { ...defaults, ...parsed };
                    } catch (e2) {
                        LOG.warn('Could not fix truncated JSON');
                    }
                }

                throw e;
            }
        } catch (error) {
            LOG.error('Error parsing AI response:', error);
            LOG.info('Raw content:', content.substring(0, 500) + '...');
            return this.getDefaultInterpretations();
        }
    },

    /**
     * Get default interpretations when AI is unavailable
     */
    getDefaultInterpretations() {
        return {
            vista1: "Analizando situación general de la comuna...",
            vista2: "Evaluando alertas y anomalías detectadas...",
            vista3: "Determinando si existe una tendencia sostenida...",
            vista4: "Evaluando el perfil de gravedad delictual...",
            vista5: "Analizando distribución entre violencia y delitos menores...",
            vista6: "Analizando correlaciones entre tipos de delitos...",
            vista7: "Analizando tendencias históricas a largo plazo...",
            vista8: "Evaluando patrones estacionales...",
            vista9: "Analizando correlaciones entre tipos de delitos...",
            vista10: "Generando pronóstico hacia fin de año...",
            vista11: "Simulador de impacto disponible...",
            vista12: "Prediciendo el próximo peak delictual...",
            vista13: "Revisando fuentes y notas metodológicas...",
            vista14: "Calculando proyección y regresión lineal delictual...",
            vista15: "Generando diagnóstico crítico inmediato de seguridad...",
            vista16: "Analizando tasas ajustadas por población y demografía...",
            vista17: "Calculando posición en el ranking regional...",
            vista18: "Identificando rachas tácticas y patrones operativos...",
            vista19: "Detectando anomalías estadísticas mediante Z-Score...",
            vista20: "Consolidando tablero de mando ejecutivo...",
            vista21: "Analizando evolución histórica CEAD...",
            vista22: "Comparando métricas anuales CEAD...",
            vista23: "Evaluando tendencias sostenidas en el tiempo...",
            vista24: "Calculando variaciones porcentuales...",
            vista25: "Analizando distribución territorial...",
            vista26: "Comparando con promedios regionales...",
            vista27: "Proyectando tendencias a largo plazo...",
            vista28: "Identificando patrones estacionales...",
            vista29: "Analizando correlaciones delictuales...",
            vista30: "Calculando proyección de fin de año...",
            vista31: "Simulando escenarios hipotéticos...",
            vista32: "Prediciendo próximos peaks de actividad..."
        };
    },

    /**
     * Get interpretation for a specific view
     * @param {string} viewId - e.g., 'vista1', 'vista2', etc.
     */
    async getInterpretation(viewId) {
        if (!this.isLoaded && !this.isLoading) {
            await this.generateAllInterpretations();
        }

        // ERR-003: Wait with 30s safety timeout (prevents infinite busy-wait)
        let waited = 0;
        while (this.isLoading && waited < 30000) {
            await new Promise(resolve => setTimeout(resolve, 200));
            waited += 200;
        }
        if (waited >= 30000) {
            LOG.warn('[IA] Timeout esperando interpretaciones (30s)');
        }

        return this.interpretations[viewId] || this.getDefaultInterpretations()[viewId];
    },

    /**
     * Update a specific DOM element with the interpretation
     * @param {string} viewId - e.g., 'vista1'
     * @param {string} elementId - DOM element ID to update
     */
    async updateElement(viewId, elementId) {
        const interpretation = await this.getInterpretation(viewId);
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = interpretation;
        }
    }
};

// Initialize the module
IAModule.init();

// Expose globally
window.IAModule = IAModule;
