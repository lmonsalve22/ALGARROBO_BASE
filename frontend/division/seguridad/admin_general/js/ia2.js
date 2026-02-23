/**
 * IA Module V2 - Strategic Analysis
 * Single Request Pattern, 5-Day Cache
 */
window.IAModuleV2 = {
    // Configuration
    CACHE_KEY: 'ia_v2_fix_', // Changed key to force refresh
    CACHE_TTL: 5 * 24 * 60 * 60 * 1000, // 5 days
    API_URL: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    MODEL_NAME: "GLM-4.7-Flash",

    // Obfuscated Key (Same as ia.js)
    getKey(seed) {
        const OFUSCADO = "VgAMFkZXBBFdUEpXQwFFXRZXA19NXV1XXQdQBVpDFlBIIwMkGxUkEgJcIRAXAUBcBQ==";
        const data = Uint8Array.from(atob(OFUSCADO), c => c.charCodeAt(0));
        const s = new TextEncoder().encode(seed);
        const out = new Uint8Array(data.length);
        for (let i = 0; i < data.length; i++) out[i] = data[i] ^ s[i % s.length];
        return new TextDecoder().decode(out);
    },

    init() {
        console.log('🤖 IA [INIT]: Módulo inicializado. Esperando datos...');
        this.cache = {};

        window.addEventListener('dataManagerLoaded', () => {
            console.log('🤖 IA [EVENT]: dataManagerLoaded detectado. Esperando 30s de cortesía (Legacy Stable Delay)...');
            setTimeout(() => {
                this.cache = this.loadCache();
                if (!this.cache.vista1) {
                    console.log('🤖 IA [CACHE]: Vacío o incompleto. Solicitando análisis...');
                    this.fetchAllAnalyses();
                } else {
                    console.log('🤖 IA [CACHE]: Cargado desde local con', Object.keys(this.cache).length, 'vistas.');
                    this.updateAllViews();
                }
            }, 30000);
        });

        window.addEventListener('viewLoaded', () => {
            this.updateAllViews();
        });
    },

    loadCache() {
        try {
            const codcom = window.STATE_DATA?.codcom || 'default';
            const raw = localStorage.getItem(this.CACHE_KEY + codcom);
            if (!raw) return {};

            if (raw.includes("Sin localización") || raw.includes("anonimato")) {
                console.warn("🤖 IA [CACHE]: Datos genéricos detectantes. Limpiando.");
                localStorage.removeItem(this.CACHE_KEY + codcom);
                return {};
            }

            const { timestamp, data } = JSON.parse(raw);
            if (Date.now() - timestamp > this.CACHE_TTL) {
                console.log('🤖 IA [CACHE]: Expirado por tiempo.');
                return {};
            }
            return data;
        } catch (e) { return {}; }
    },

    saveCache(data) {
        const codcom = window.STATE_DATA?.codcom || 'default';
        const key = this.CACHE_KEY + codcom;
        try {
            localStorage.setItem(key, JSON.stringify({ timestamp: Date.now(), data }));
        } catch (e) {
            // ERR-009: Handle QuotaExceededError
            if (e.name === 'QuotaExceededError' || e.code === 22) {
                LOG.warn('[IA2] localStorage lleno, limpiando caches antiguos...');
                for (let i = localStorage.length - 1; i >= 0; i--) {
                    const k = localStorage.key(i);
                    if (k && k.startsWith(this.CACHE_KEY) && k !== key) localStorage.removeItem(k);
                }
                try { localStorage.setItem(key, JSON.stringify({ timestamp: Date.now(), data })); } catch (_) { }
            }
        }
    },

    buildContext(S) {
        const C = window.COLS;
        const C_CEAD = window.COLS_CEAD;
        const S_CEAD = window.STATE_DATA_CEAD;

        if (!S.comunaName || S.comunaName.includes('Cargando')) return null;
        if (!S.allDataHistory_total || S.allDataHistory_total.length === 0) return null;

        // --- Core Data (STOP) ---
        const totalRow = S.allDataHistory_total.find(r => r[C.ID_SEMANA] === S.currentSemana) || {};
        const cases = totalRow[C.CASOS_ACTUAL] || 0;
        const prev = totalRow[C.CASOS_ANT] || 0;
        const delta = prev > 0 ? ((cases - prev) / prev * 100) : 0;

        // --- Specific Vistas Metrics ---

        // V12-V16: Context & Ranks (Simulated/Calculated)
        const nationalRank = totalRow[C.RANK_NAC] || 120; // Example
        const clusterRank = totalRow[C.RANK_CLUSTER] || 5;
        const effectiveness = (totalRow[C.DETENIDOS] || 0) / (cases || 1) * 100;

        // V19: Emerging (STOP & CEAD)
        const stopEmerging = S.allDataHistory
            .filter(r => r[C.ID_SEMANA] === S.currentSemana && r[C.CASOS_ACTUAL] > r[C.CASOS_ANT] * 1.2)
            .map(r => r[C.DELITO]).slice(0, 2);

        const ceadEmerging = S_CEAD && S_CEAD.allDataHistory
            ? S_CEAD.allDataHistory.filter(r => r[C_CEAD.ID_PERIODO] === S_CEAD.periodoId && r[C_CEAD.Z_SCORE] > 1.5).map(r => r[C_CEAD.DELITO]).slice(0, 2)
            : [];

        // V20: Success
        const stopSuccess = S.allDataHistory
            .filter(r => r[C.ID_SEMANA] === S.currentSemana && r[C.CASOS_ACTUAL] < r[C.CASOS_ANT] * 0.8)
            .map(r => r[C.DELITO]).slice(0, 2);

        // V21: Forecast (Simplified)
        const forecastTrend = "Estable"; // Placeholder for complex SARIMA logic output

        // V22: Priority
        const priorityCrime = S.allDataHistory
            .filter(r => r[C.ID_SEMANA] === S.currentSemana)
            .sort((a, b) => (b[C.CASOS_ACTUAL] * (b[C.CASOS_ACTUAL] / b[C.CASOS_ANT] || 1)) - (a[C.CASOS_ACTUAL] * (a[C.CASOS_ACTUAL] / a[C.CASOS_ANT] || 1)))
            .map(r => r[C.DELITO])[0] || 'N/A';

        const regionalRank = totalRow['ranking_regional_proy_anual'] || totalRow['ranking_regional_tasa_sem'] || totalRow[C.RANK_REG_TASA] || 'N/A';

        return {
            comuna: S.comunaName,
            week: S.semanaDetalle,
            metrics: {
                total_cases: cases,
                weekly_delta: delta.toFixed(1) + '%',
                communal_rate: (totalRow[C.TASA_SEMANAL] || 0).toFixed(1),
                national_rank: nationalRank,
                cluster_rank: clusterRank,
                regional_rank: regionalRank,
                effectiveness_ratio: effectiveness.toFixed(1) + '%'
            },
            insights: {
                emerging_short_term: stopEmerging.join(', '),
                emerging_long_term: ceadEmerging.join(', '),
                success_stories: stopSuccess.join(', '),
                priority_focus: priorityCrime,
                forecast_trend: forecastTrend
            }
        };
    },

    async fetchAllAnalyses() {
        if (this.fetching) {
            console.log('🤖 IA [INFO]: Petición en curso, ignorando duplicado.');
            return;
        }
        this.fetching = true;
        console.log('🤖 IA [START]: Generando nuevo análisis estratégico...');

        const S = window.STATE_DATA;
        console.log('🤖 IA [DEBUG]: Construyendo contexto para', S?.comunaName);
        const context = this.buildContext(S);

        if (!context) {
            console.warn("🤖 IA [WARN]: Contexto insuficiente (faltan datos o comuna).");
            this.fetching = false;
            return;
        }

        try {
            console.log('🤖 IA [FETCH]: Iniciando llamada a API Zhipu (GLM-4)...');
            const prompt = `
Eres un analista de inteligencia estratégica y perfilador criminal experto en el sistema STOP y CEAD de Carabineros de Chile.
Tu misión es generar interpretaciones estratégicas DETALLADAS, ANALÍTICAS y EJECUTIVAS para el dashboard de seguridad de la COMUNA DE ${context.comuna.toUpperCase()}.

CONTEXTO OPERATIVO (${context.week}):
${JSON.stringify(context, null, 2)}

REGLAS CRÍTICAS DE RESPUESTA:
- El análisis debe ser profundo, extenso y profesional (entre 50 y 85 palabras por cada vista). Aborda el QUÉ, el POR QUÉ y el QUÉ HACER.
- Menciona siempre la comuna ("${context.comuna}") para contextualizar territorialmente de manera natural y formal.
- Adopta un tono de mando policial técnico, directo, sin eufemismos, orientado puramente a toma de decisiones y mitigación de crisis.
- Relaciona los hallazgos directamente con los datos entregados en el CONTEXTO OPERATIVO. Si falta algún dato empírico, realiza inferencias lógicas basadas en la posición del ranking global de la comuna o en el comportamiento habitual de Chile.

PREGUNTAS A RESPONDER DETALLADAMENTE (UNA RESPUESTA CERRADA Y COMPLETA POR VISTA):
- vista1: ¿Qué ha pasado en la última semana? (Veredicto general, magnitud de la variación y tipología principal que tracciona la estadística).
- vista2: ¿Cómo ha sido la evolución mensual durante este año y la tendencia de los últimos 6 meses respecto a la media histórica del sector?
- vista3: ¿Cómo se compara el volumen de la última semana con el historial? ¿Alcanzamos un peak o un valle preocupante?
- vista4: ¿Existe estacionalidad o patrones recurrentes en el año histórico que debamos anticipar para los próximos meses en esta jurisdicción?
- vista5: ¿Cuáles son las problemáticas que concentran el 80% de los incidentes en la comuna (Ley de Pareto) que requieren foco operativo inmediato?
- vista6: ¿Qué tipologías han mostrado las variaciones porcentuales más drásticas recientemente y cómo cambian el pulso de la percepción local?
- vista7: ¿Hay delitos que muestran rachas continuas de aumento durante varias semanas? ¿A qué táctica evasiva criminal podrían atribuirse?
- vista8: ¿Existen delitos que suelen ocurrir o aumentar en conjunto indicando un modus operandi complejo en el territorio?
- vista9: ¿Cuál es nuestra tasa delictual relativa a la población y cómo contrasta el volumen delictual frente al total regional (intercomunal)?
- vista10: ¿Cómo es nuestra carga comparada con el resto de la región? Analiza la posición del ranking regional de la comuna en el contexto amplio.
- vista11: En perspectiva de una o dos décadas atrás (sistema CEAD), ¿cuál es el diagnóstico estructural histórico de la zona?
- vista12: Considerando la posición en el Ranking Nacional de Casos de la comuna, ¿qué lectura estratégica se hace sobre nuestro desempeño frente al país?
- vista13: Según el Ranking de Clúster (grupos demográficos similares), ¿por qué presentamos estas problemáticas particulares respecto a nuestros pares sociodemográficos?
- vista14: ¿De todo el panorama regional, qué carga asume nuestra comuna y por qué la vuelve un objetivo crítico o secundario?
- vista15: Tasa de resolución/detención. ¿La efectividad operativa y preventiva está frenando la tasa de ingresos de ilícitos adecuadamente en el momento?
- vista16: Mapa de Posicionamiento: ¿Qué tan efectivos somos en comparación a otras comunas vecinas en términos de mitigación de daños?
- vista17: En base a la inercia delictual actual, ¿cuál es la proyección de casos más agresiva esperada para el Cierre Anual?
- vista18: Analizando el historial crítico de rachas y fluctuaciones o quiebres estructurales en los últimos meses, ¿hay control sobre la serie?
- vista19: ¿Qué nuevos delitos "Emergentes" de expansión rápida están apareciendo en la zona para romper el molde normal esperado?
- vista20: ¿Qué delitos específicos estamos logrando reducir con éxito prolongado y por qué se sostiene la disipación sobre el tiempo?
- vista21: ¿Están los delitos acelerando su ritmo (Momentum alcista) superando la capacidad de respuesta policial e intervención operativa disponible?
- vista22: Prioridad estratégica urgente. Si el mando logístico forzara intervenir sólo en un factor, ¿en qué fenómeno enfoca y por qué motivo radical?
- vista23: ¿Cuál debería ser el diseño o recomendación de la siguiente ronda de servicios focalizados para desbaratar esta coyuntura de manera asimétrica?
- vista24: REPORTE DE INTELIGENCIA (RESUMEN): Veredicto ejecutivo total del Estado Operacional de la comuna para las altas esferas de Autoridad o Jefatura.
- vista25: Calidad del informe y suficiencia del dato. ¿Los vacíos de información empírica limitan la toma de decisiones definitivas hoy para este polígono?

FORMATO DE RESPUESTA:
Crea SOLO Y EXCLUSIVAMENTE un bloque con formato JSON VÁLIDO.
Las claves deben ir de "vista1" hasta "vista25" estrictamente.
El valor de cada clave debe ser un STRING directo y simple (sin saltos de línea \n ni comillas no escapadas).
No escribas la palabra json, no agregues explicaciones afuera. Empieza siempre el mensaje con "{" y termínalo con "}".`;

            const API_KEY = this.getKey("gfhrsdfsdfseweretfghtddfdf");
            const fetchController = new AbortController();
            // Aumentamos a 90s por latencia y carga de la API GLM-4
            const fetchTimeoutId = setTimeout(() => {
                console.warn('🤖 IA [TIMEOUT]: La petición excedió los 90s y será abortada.');
                fetchController.abort();
            }, 90000);

            // jitter
            await new Promise(r => setTimeout(r, 1000 + Math.random() * 2000));

            let response;
            try {
                response = await fetch(this.API_URL, {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + API_KEY, 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model: this.MODEL_NAME,
                        messages: [{ role: "user", content: prompt }],
                        temperature: 0.5
                    }),
                    signal: fetchController.signal
                });
                console.log('🤖 IA [RES]: HTTP Status', response.status);
            } finally {
                clearTimeout(fetchTimeoutId);
            }

            if (response.status === 429) {
                throw new Error("Límite de peticiones alcanzado (429). Reintentando en próxima sesión.");
            }
            if (!response.ok) throw new Error(`HTTP Error ${response.status}`);

            const result = await response.json();
            const content = result.choices?.[0]?.message?.content || '{}';
            console.log('🤖 IA [DATA]: Respuesta recibida (longitud:', content.length, ')');

            const jsonStart = content.indexOf('{');
            const jsonEnd = content.lastIndexOf('}') + 1;
            const cleanJson = content.substring(jsonStart, jsonEnd);
            const analyses = JSON.parse(cleanJson);

            console.log('🤖 IA [OK]: Análisis parseado correctamente. Actualizando UI.');
            this.cache = analyses;
            this.saveCache(analyses);
            this.updateAllViews();

        } catch (e) {
            console.error('🤖 IA [ERROR]:', e);
            if (e.name === 'AbortError') {
                console.error('🤖 IA [CRITICAL]: La petición fue cancelada por timeout o señal externa.');
            }
            this.updateAllViews(true);
        } finally {
            this.fetching = false;
        }
    },

    updateAllViews(isError = false) {
        for (let i = 1; i <= 25; i++) {
            const vid = `vista${i}`;
            const el = document.getElementById(`v${i}_ia_analysis`);
            if (el) {
                const parent = el.closest('.alert');
                if (isError) {
                    el.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Servicio de IA no disponible. Verifique conexión.';
                    if (parent) {
                        // Cambiar estilo a Error visualmente
                        parent.style.backgroundColor = 'rgba(254, 226, 226, 0.5)'; // Rojo claro
                        parent.style.borderColor = '#fca5a5';
                        parent.style.color = '#b91c1c';
                        // Intentar quitar alert--info si entra en conflicto
                        parent.classList.remove('alert--info');
                        parent.classList.add('alert--danger');
                    }
                }
                else if (this.cache[vid]) {
                    el.textContent = this.cache[vid];
                    if (parent) {
                        // Restaurar estilo Info
                        parent.style.backgroundColor = '';
                        parent.style.borderColor = '';
                        parent.style.color = '';
                        parent.classList.add('alert--info');
                        parent.classList.remove('alert--danger');
                    }
                }
            }
        }
    }
};

window.IAModuleV2.init();
