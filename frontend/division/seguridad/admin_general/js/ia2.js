/**
 * IA Module V2 - Strategic Analysis (Seguridad Municipal)
 * Restricted to 5 strategic views: vista1, vista5, vista13, vista18, vista22
 * Single Request Pattern, 5-Day Cache
 */
window.IAModuleV2 = {
    // Configuration
    CACHE_KEY: 'ia_seg_v2_', // Unique key for Seguridad module
    CACHE_TTL: 5 * 24 * 60 * 60 * 1000, // 5 days
    API_URL: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    MODEL_NAME: "GLM-4.7-Flash",

    // Only these 5 views
    ACTIVE_VIEWS: ['vista1', 'vista5', 'vista13', 'vista18', 'vista22'],
    ACTIVE_VIEW_NUMS: [1, 5, 13, 18, 22],

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
        console.log('🤖 IA [INIT]: Módulo Seguridad inicializado (5 vistas). Esperando datos...');
        this.cache = {};

        window.addEventListener('dataManagerLoaded', () => {
            console.log('🤖 IA [EVENT]: dataManagerLoaded detectado. Esperando 3s para sincronización de UI...');
            setTimeout(() => {
                this.cache = this.loadCache();
                if (!this.cache.vista1) {
                    console.log('🤖 IA [CACHE]: Vacío o incompleto. Solicitando análisis...');
                    this.fetchAllAnalyses();
                } else {
                    console.log('🤖 IA [CACHE]: Cargado desde local con', Object.keys(this.cache).length, 'vistas.');
                    this.updateAllViews();
                }
            }, 3000);
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
        const cagr_4s = totalRow[C.T31_CAGR_4S] || 0;

        // --- Specific Vistas Metrics ---
        const nationalRank = totalRow['ranking_nacional_semanal'] || totalRow[C.RANK_NAC] || '--';
        const clusterRank = totalRow[C.RANK_CLUSTER_SEM] || totalRow[C.RANK_CLUSTER] || '--';
        const regionalRank = totalRow['ranking_regional_semanal'] || '--';
        const effectiveness = (totalRow[C.DETENIDOS] || 0) / (cases || 1) * 100;

        // Crime breakdown (Top 5 actual week)
        const currentData = S.allDataHistory.filter(r => r[C.ID_SEMANA] === S.currentSemana).sort((a, b) => (b[C.CASOS_ACTUAL] || 0) - (a[C.CASOS_ACTUAL] || 0));
        const topCrimes = currentData.slice(0, 5).map(r => `${r[C.DELITO]}: ${r[C.CASOS_ACTUAL]}`);
        const risingCrimes = currentData.filter(r => (r[C.CASOS_ACTUAL] > r[C.CASOS_ANT])).map(r => `${r[C.DELITO]} (+${r[C.CASOS_ACTUAL] - r[C.CASOS_ANT]})`);
        const fallingCrimes = currentData.filter(r => (r[C.CASOS_ACTUAL] < r[C.CASOS_ANT])).map(r => `${r[C.DELITO]} (${r[C.CASOS_ACTUAL] - r[C.CASOS_ANT]})`);

        // V22: Priority
        const priorityCrime = currentData
            .filter(r => r[C.CASOS_ACTUAL] > 5 && r[C.CASOS_ACTUAL] > r[C.CASOS_ANT])
            .map(r => r[C.DELITO])[0] || 'N/A';

        // V18: Gravity balance
        const highMomentum = currentData
            .filter(r => r[C.DELITO] !== 'Total' && r[C.T31_CAGR_4S] > 0)
            .sort((a, b) => b[C.T31_CAGR_4S] - a[C.T31_CAGR_4S])
            .map(r => `${r[C.DELITO]} (CAGR 4S: ${r[C.T31_CAGR_4S].toFixed(1)}%)`).slice(0, 3);

        return {
            comuna: S.comunaName,
            week: S.semanaDetalle,
            metrics: {
                total_cases: cases,
                total_cases_last_week: prev,
                weekly_delta_percent: delta.toFixed(1) + '%',
                overall_momentum_cagr_4s: cagr_4s.toFixed(1) + '%',
                communal_rate: (totalRow[C.TASA_SEMANAL] || 0).toFixed(1),
                national_rank: nationalRank,
                regional_rank: regionalRank,
                cluster_rank: clusterRank,
                effectiveness_ratio: effectiveness.toFixed(1) + '%'
            },
            insights: {
                top_crimes_volume: topCrimes.join(', '),
                crimes_increasing_wow: risingCrimes.join(', '),
                crimes_decreasing_wow: fallingCrimes.join(', '),
                crimes_with_high_momentum: highMomentum.join(', '),
                priority_focus: priorityCrime
            }
        };
    },

    async fetchAllAnalyses() {
        if (this.fetching) {
            console.log('🤖 IA [INFO]: Petición en curso, ignorando duplicado.');
            return;
        }
        this.fetching = true;
        console.log('🤖 IA [START]: Generando análisis estratégico (5 vistas)...');

        const S = window.STATE_DATA;
        const context = this.buildContext(S);

        if (!context) {
            console.warn("🤖 IA [WARN]: Contexto insuficiente (faltan datos o comuna).");
            this.fetching = false;
            return;
        }

        try {
            const prompt = `
Eres un analista de inteligencia estratégica y perfilador criminal experto en el sistema STOP y CEAD de Carabineros de Chile.
Tu misión es generar interpretaciones estratégicas DETALLADAS, ANALÍTICAS y EJECUTIVAS para el dashboard de seguridad de la COMUNA DE ${context.comuna.toUpperCase()}.

CONTEXTO OPERATIVO (${context.week}):
${JSON.stringify(context, null, 2)}

REGLAS CRÍTICAS DE RESPUESTA:
- ESTILO MILITAR ULTRA-CONCISO: Respuestas de impacto, máximo 20 a 30 palabras por vista. Ve directo a la conclusión operativa.
- Menciona siempre la comuna ("${context.comuna}") para contextualizar territorialmente de manera natural y formal.
- Adopta un tono de mando policial técnico, directo, sin eufemismos, orientado puramente a toma de decisiones y mitigación de crisis. Elimina verbosidad inútil.
- Relaciona los hallazgos directamente con los datos entregados en el CONTEXTO OPERATIVO. Si falta algún dato empírico, realiza inferencias lógicas y razonables según la criminología y el comportamiento habitual en Chile.

PREGUNTAS A RESPONDER (SOLO 5 VISTAS REQUERIDAS):
- vista1: ¿Qué ha pasado en la última semana? (Veredicto general, magnitud de la variación y tipologías principales que traccionan la estadística).
- vista5: ¿Cuáles son los delitos críticos que requieren foco inmediato? (Aplicación de Ley de Pareto, qué ilícitos concentran el 80% del daño).
- vista13: ¿Cómo nos comparamos con comunas similares? (Clúster sociodemográfico, ¿somos los peores o los mejores entre pares?).
- vista18: ¿Está aumentando la violencia en los delitos? (Balance cualitativo: delitos violentos vs delitos contra la propiedad).
- vista22: ¿Dónde debemos concentrar los recursos hoy? (Focalización táctica cruzada de alto volumen y alza urgente).

FORMATO DE RESPUESTA:
NUNCA uses JSON. Devuelve tu respuesta como texto simple, separando cada análisis con una etiqueta de corchetes.
Tu respuesta debe lucir exactamente así:
[vista1]
Tu análisis para la vista 1 aquí...
[vista5]
Tu análisis para la vista 5 aquí...
[vista13]
Tu análisis para la vista 13 aquí...
[vista18]
Tu análisis para la vista 18 aquí...
[vista22]
Tu análisis para la vista 22 aquí...
No agregues encabezados ni despedidas.`;

            // Auditoría de Calidad Preventiva
            if (window.PromptQuality && !window.PromptQuality.audit(prompt, context)) {
                this.updateAllViews(true);
                this.fetching = false;
                return;
            }

            const API_KEY = this.getKey("gfhrsdfsdfseweretfghtddfdf");
            const fetchController = new AbortController();
            const fetchTimeoutId = setTimeout(() => {
                console.warn('🤖 IA [TIMEOUT]: La petición excedió los 240s y será abortada.');
                fetchController.abort();
            }, 240000);

            const payload = {
                model: this.MODEL_NAME,
                messages: [{ role: "user", content: prompt }],
                temperature: 0.5
            };

            // jitter
            await new Promise(r => setTimeout(r, 1000 + Math.random() * 2000));

            let response;
            try {
                response = await fetch(this.API_URL, {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + API_KEY, 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    signal: fetchController.signal
                });
            } finally {
                clearTimeout(fetchTimeoutId);
            }

            if (response.status === 429) {
                let errorDetails = "Límite de peticiones alcanzado (429).";
                try {
                    const errorJson = await response.json();
                    if (errorJson.error && errorJson.error.message) {
                        errorDetails += " Detalle: " + errorJson.error.message;
                    }
                } catch (e) {
                    try {
                        const errorText = await response.text();
                        if (errorText) errorDetails += " Info: " + errorText.substring(0, 100);
                    } catch (e2) { }
                }
                console.error('🤖 IA [ERROR]:', errorDetails);
                throw new Error(errorDetails);
            }

            if (!response.ok) {
                let failMsg = `HTTP Error ${response.status}`;
                try {
                    const failBody = await response.text();
                    failMsg += ` - ${failBody.substring(0, 150)}`;
                } catch (e) { }
                throw new Error(failMsg);
            }

            const result = await response.json();
            const content = result.choices?.[0]?.message?.content || '';

            // Parser de Texto Libre (RegEx) para extraer [vistaX]
            const analyses = {};
            const regex = /\[(vista\d+)\]([\s\S]*?)(?=\[vista\d+\]|$)/gi;
            let match;

            while ((match = regex.exec(content)) !== null) {
                const vistaKey = match[1].toLowerCase();
                const textVal = match[2].trim();
                // Only store if it's one of our 5 active views
                if (this.ACTIVE_VIEWS.includes(vistaKey)) {
                    analyses[vistaKey] = textVal;
                }
            }

            if (Object.keys(analyses).length === 0) {
                throw new Error("El modelo generó un texto pero no se detectaron etiquetas de vistas.");
            }

            this.cache = analyses;
            this.saveCache(analyses);
            this.updateAllViews();

        } catch (e) {
            console.error('🤖 IA [ERROR]:', e);
            if (e.name === 'AbortError') {
                console.error('🤖 IA [CRITICAL]: La petición fue cancelada por timeout.');
            }
            this.updateAllViews(true);
        } finally {
            this.fetching = false;
        }
    },

    updateAllViews(isError = false) {
        // Only update the 5 active views
        for (const viewNum of this.ACTIVE_VIEW_NUMS) {
            const vid = `vista${viewNum}`;
            const el = document.getElementById(`v${viewNum}_ia_analysis`);
            if (el) {
                const parent = el.closest('.alert');
                if (isError) {
                    el.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Servicio de IA no disponible. Verifique conexión.';
                    if (parent) {
                        parent.classList.remove('alert--info');
                        parent.classList.add('alert--danger');
                        parent.style.backgroundColor = 'rgba(254, 226, 226, 0.5)';
                        parent.style.borderColor = '#fca5a5';
                        parent.style.color = '#b91c1c';
                    }
                } else if (this.cache[vid]) {
                    el.textContent = this.cache[vid];
                    if (parent) {
                        parent.classList.add('alert--info');
                        parent.classList.remove('alert--danger');
                        parent.style.backgroundColor = '';
                        parent.style.borderColor = '';
                        parent.style.color = '';
                    }
                }
            }
        }
    }
};

window.IAModuleV2.init();
