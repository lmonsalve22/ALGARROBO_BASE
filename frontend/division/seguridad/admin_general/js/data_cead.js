/**
 * CEAD Data Layer
 * Handles data loading for CEAD monthly crime statistics
 */

// Global State for CEAD
window.STATE_DATA_CEAD = {
    codcom: 5602,
    allData: [],
    allDataHistory: [],
    allDataHistory_total: [],
    stats: {},
    comunaName: 'Sin Comuna',
    regionName: 'Sin Región',
    periodoId: null,
    periodoDetalle: '',
    warning: '',
    isLoaded: false,
    lastMonth: null,
    lastYear: null
};

// CEAD Column Keys - Mapped to proceso_cead.py output (orient='records')
/**
 * CEAD Data Loader
 * Loads data from json files produced by Python script
 * Relies on window.COLS_CEAD defined in config/columns.js
 */

// If COLS_CEAD is missing, recreate it (fallback), but prefer config/columns.js
if (!window.COLS_CEAD) {
    console.warn("⚠️ COLS_CEAD missing! Using fallback configuration.");
    window.COLS_CEAD = {
        ID_PERIODO: 'id_periodo',
        DELITO: 'delito',
        CASOS_ACTUAL: 'frecuencia',
        CASOS_ANT: 'casos_mes_anterior',
        DELTA: 'delta',
        VAR_PCT: 'variacion_porcentual',
        ANIO: 'anio',
        MES: 'mes',
        MES_NUM: 'mes_num',
        COMUNA: 'comuna',
        REGION: 'region',
        PERIODO_DETALLE: 'periodo_detalle',
        ALERTA: 'alerta_aumento_critico'
    };
} else {
    console.log("✅ Using Centralized COLS_CEAD configuration.");
}
window.COLS_CEAD = {
    // Identificadores Base
    CODCOM: 'codcom',
    ANIO: 'año',
    TIPO_VAL_COD: 'tipoValCod',
    TIPO_VAL: 'tipoVal',
    CODIGO: 'CODIGO',
    DELITO: 'delito',
    NIVEL: 'Nivel',
    MES_NOMBRE: 'mes_nombre',
    MES: 'mes',
    ID_PERIODO: 'id_periodo',
    FECHA: 'fecha',
    TOTAL_ANIO_REAL: 'total_año_real',
    TASA_CEAD_ANUAL: 'tasa_cead',
    TASA_ANUAL_REAL: 'tasa_anual_real',
    PERIODO_DETALLE: 'periodo_detalle',
    IS_FORECAST: 'is_forecast',

    // Métricas Base
    FRECUENCIA: 'frecuencia',
    CASOS_ACTUAL: 'frecuencia', // Mapped to 'frecuencia' as 'casos_mes_actual' does not exist in CEAD output
    CASOS_ANT: 'casos_mes_anterior',
    DELTA: 'delta',

    // Acumulados
    ACUM_ANUAL: 'acumulado_anual',
    ACUM_TOTAL: 'acumulado_total',
    ACUM_ANUAL_ANT: 'acumulado_anual_anterior',

    // Medias Móviles
    MEDIA_MOVIL_3M: 'media_movil_3m',
    MEDIA_MOVIL_6M: 'media_movil_6m',

    // Históricos
    PROMEDIO_HIST: 'promedio_hist',
    STD_HIST: 'std_hist',
    MAX_HIST: 'max_hist',
    PROMEDIO_HIST_ANUAL: 'promedio_hist_anual',
    STD_HIST_ANUAL: 'std_hist_anual',
    MAX_HIST_ANUAL: 'max_hist_anual',

    // Tendencias y Rachas
    TENDENCIA: 'tendencia_corto_plazo',
    RACHA_ALZA: 'racha_alza',
    RACHA_BAJA: 'racha_baja',
    RACHA: 'racha',

    // Z-Score y Variaciones
    VAR_PCT_MES: 'var_pct_vs_mes_anterior',
    Z_SCORE: 'z_score',
    Z_SCORE_YEAR_ANT: 'z_score_vs_año_anterior',
    Z_CONCL: 'conclusion_z',

    // Geografía y Población
    PROVINCIA: 'Provincia',
    COMUNA: 'Comuna',
    REGION: 'Región',
    CODREG: 'Codreg',
    POBLACION_CLASE: 'poblacion_clase',
    CLASE_POBLACION: 'clase_poblacion',
    POBLACION: 'poblacion',
    FACTOR_POBLACION: 'factor_poblacion',

    // Rankings
    RANKING: 'ranking_comunal_regional',
    RANKING_REG_ANUAL: 'ranking_regional_anual_metric', // Nuevo calculo anual consolidado
    RANKING_REG_ANUAL_TASA: 'ranking_regional_anual_tasa',
    RANKING_ANT: 'ranking_comunal_regional_mes_anterior',
    RANK_NAC_MES: 'ranking_nacional_mensual',
    RANK_NAC_MES_ANT: 'ranking_nacional_mensual_anterior',
    RANK_REG_PROY: 'ranking_regional_proy_anual',
    RANK_REG_PROY_ANT: 'ranking_regional_proy_anual_anterior',
    RANK_NAC_PROY: 'ranking_nacional_proy_anual',
    RANK_NAC_PROY_ANT: 'ranking_nacional_proy_anual_anterior',
    RANK_CLUSTER_PROY: 'ranking_cluster_proy_anual',
    RANK_CLUSTER_PROY_ANT: 'ranking_cluster_proy_anual_anterior',
    RANK_CLUSTER_MES: 'ranking_cluster_mensual',
    RANK_CLUSTER_MES_ANT: 'ranking_cluster_mensual_anterior',

    // Alertas y Récords
    ID_PERIODO_MAX_HIST: 'id_periodo_max_hist',
    PERIODO_DETALLE_MAX_HIST: 'periodo_detalle_max_hist',
    ALERTA: 'alerta_aumento_critico',
    ALERTA_YEAR_ANT: 'alerta_vs_año_anterior',
    CASOS_MISMO_MES_YEAR_ANT: 'casos_mismo_mes_año_anterior',

    // Proyecciones
    FACTOR_EXPANSION_ANUAL: 'factor_expansion_anual',
    PROYECCION_ANUAL: 'proyeccion_anual',
    TASA_MENSUAL: 'tasa_mensual',
    TASA_PROY_ANUAL: 'tasa_proyectada_anual',

    // Diagnósticos (T19-T20)
    T19_DELITO: 't19_delito',
    T19_RANK: 't19_rank',
    T20_DELITO: 't20_delito',
    T20_RANK: 't20_rank',

    // Aportes
    CASOS_REGIONAL: 'casos_regional',
    APORTE_PCT: 'aporte_pct_region',
    APORTE_PCT_ANT: 'aporte_pct_region_ant',

    // Correlaciones (T23)
    T23_D1: 't23_d1',
    T23_D2: 't23_d2',
    T23_VAL: 't23_val',

    // Pareto (T21)
    T21_DELITO_1: 't21_delito_1',
    T21_DELITO_2: 't21_delito_2',
    T21_DELITO_3: 't21_delito_3',
    T21_VAL_1: 't21_val_1',
    T21_VAL_2: 't21_val_2',
    T21_VAL_3: 't21_val_3',

    // Crecimiento
    MM3M_LAG3: 'mm3m_lag3',
    CAGR_3M: 'cagr_3m',
    CAGR_ANUAL: 'cagr_anual',

    // ─── Backward-Compatible Aliases (for existing vista scripts) ───
    // Old COLS_CEAD keys → new column names
    MES_NUM: 'mes',                          // was separate from MES
    DESCRIPCION: 'delito',                   // old name for DELITO
    CASOS_MES_ACTUAL: 'casos_mes_actual',    // alias for CASOS_ACTUAL
    CASOS_MES_ANTERIOR: 'casos_mes_anterior',// alias for CASOS_ANT
    CASOS_MISMO_MES_ANIO_ANTERIOR: 'casos_mismo_mes_año_anterior',
    ACUMULADO_MENSUAL: 'acumulado_anual',    // monthly accumulation → annual
    ACUMULADO_ANUAL: 'acumulado_anual',
    ACUMULADO_ANUAL_ANIO_ANTERIOR: 'acumulado_anual_anterior',
    MEDIA_MOVIL_4M: 'media_movil_3m',       // closest equivalent
    VAR_PCT_VS_MES_ANTERIOR: 'var_pct_vs_mes_anterior',
    VAR_PCT_VS_ANIO_ANTERIOR: 'z_score_vs_año_anterior',
    RANKING_COMUNAL_REGIONAL: 'ranking_comunal_regional',
    RANKING_COMUNAL_REGIONAL_MES_ANTERIOR: 'ranking_comunal_regional_mes_anterior',
    ALERTA_AUMENTO_CRITICO: 'alerta_aumento_critico',

    // STOP-compatible aliases (for views that use STOP key names with CEAD data)
    ID_SEMANA: 'id_periodo',                 // period identifier
    SEMANA_DETALLE: 'periodo_detalle',
    SEMANA: 'mes',
    CASOS_YEAR_ANT: 'casos_mismo_mes_año_anterior',
    MEDIA_MOVIL_4S: 'media_movil_3m',
    MEDIA_MOVIL_8S: 'media_movil_6m',
    VAR_PCT_SEM: 'var_pct_vs_mes_anterior',
    SEMANA_MAX_HIST: 'id_periodo_max_hist',
    SEMANA_DETALLE_MAX_HIST: 'periodo_detalle_max_hist',
    ALERTA: 'alerta_aumento_critico',
    ALERTA_YEAR_ANT: 'alerta_vs_año_anterior',
    RANK_NAC_SEM: 'ranking_nacional_mensual',
    RANK_NAC_SEM_ANT: 'ranking_nacional_mensual_anterior',
    RANK_CLUSTER_SEM: 'ranking_cluster_mensual',
    RANK_CLUSTER_SEM_ANT: 'ranking_cluster_mensual_anterior',
    CASOS_SEM_REG: 'casos_regional',
    TASA_SEMANAL: 'tasa_mensual',

    // Additional STOP aliases for vista0 compatibility
    SEMANA_SAFE: 'mes',
    CASOS_MES_YEAR_ANT: 'casos_mismo_mes_año_anterior',
    PROY_MES: 'proyeccion_anual',            // CEAD no tiene proy mensual, usa anual
    TASA_PROY_REGIONAL: '_na_tasa_proy_reg',  // No existe en CEAD
    TASA_PROY_NACIONAL: '_na_tasa_proy_nac',
    TASA_PROY_CLUSTER: '_na_tasa_proy_clus',
    CASOS_SEM_REG_ANT: '_na_casos_reg_ant',
    PRIORIDAD_VAL: '_na_prioridad',
    ES_RACHA_NEG: '_na_racha_neg',
    ES_RACHA_POS: '_na_racha_pos',

    // IDI (Calculated via Union Mapping)
    IDI_PESO: 'idi_peso',
    IDI_PROY_MES: 'idi_mensual',
    IDI_MES_ANT_YEAR: '_na_idi_ant_year',
    IDI_MES_ANTERIOR: '_na_idi_mes_ant',
    IDI_PROY_ANUAL: 'idi_acumulado_anual',
    IDI_ANUAL_ANT: '_na_idi_anual_ant',
    IDI_REGIONAL: '_na_idi_reg',
    IDI_NACIONAL: '_na_idi_nac',
    IDI_CLUSTER: '_na_idi_clus',

    // Rachas Top 3 (no calculado en CEAD)
    RACHA_NEG_DELITO_1: '_na_t29_d1',
    RACHA_NEG_DELITO_2: '_na_t29_d2',
    RACHA_NEG_DELITO_3: '_na_t29_d3',
    RACHA_NEG_SEM_1: '_na_t29_s1',
    RACHA_NEG_SEM_2: '_na_t29_s2',
    RACHA_NEG_SEM_3: '_na_t29_s3',
    RACHA_POS_DELITO_1: '_na_t30_d1',
    RACHA_POS_DELITO_2: '_na_t30_d2',
    RACHA_POS_DELITO_3: '_na_t30_d3',
    RACHA_POS_SEM_1: '_na_t30_s1',
    RACHA_POS_SEM_2: '_na_t30_s2',
    RACHA_POS_SEM_3: '_na_t30_s3',

    // Crecimiento aliases
    T31_CAGR: 'cagr_3m',
    T32_CAGR: 'cagr_anual',
    MM4S_LAG4: 'mm3m_lag3',
    CASOS_SEM1: '_na_casos_sem1',

    // T22 Estacionalidad Histórica
    T22_MES_NOMBRE: 't22_mes_nombre',
    T22_MES_PCT: 't22_mes_pct',
    T22_TRIMESTRE_NOMBRE: 't22_trimestre_nombre',
    T22_TRIMESTRE_PCT: 't22_trimestre_pct',

    // T24 Correlación Largo Plazo (Top 4 pares)
    T24_D1_1: 't24_d1_1',
    T24_D1_2: 't24_d1_2',
    T24_V1: 't24_v1',
    T24_D2_1: 't24_d2_1',
    T24_D2_2: 't24_d2_2',
    T24_V2: 't24_v2',
    T24_D3_1: 't24_d3_1',
    T24_D3_2: 't24_d3_2',
    T24_V3: 't24_v3',
    T24_D4_1: 't24_d4_1',
    T24_D4_2: 't24_d4_2',
    T24_V4: 't24_v4'
};

// Parse URL parameters
const paramsCead = new URLSearchParams(window.location.search);
const codcom_url_cead = paramsCead.get('codcom');

/**
 * CEAD Data Loader
 */
const dataLoaderCead = {
    _loadingInProgress: false,
    _hasLoaded: false,

    async load() {
        // Guard: Avoid multiple loads
        if (this._loadingInProgress || this._hasLoaded) {
            console.warn('⚠️ CEAD DataLoader: Load already in progress or completed');
            return;
        }
        this._loadingInProgress = true;

        try {
            console.log('📊 Loading CEAD data...');

            const targetCod = codcom_url_cead ? parseInt(codcom_url_cead) : 5602;
            STATE_DATA_CEAD.codcom = targetCod;

            console.log(`📊 Loading CEAD data for comuna ${targetCod}...`);

            const fileUrl = `data/cead_split/${targetCod}`;

            const response = await fetch(fileUrl);
            if (!response.ok) {
                if (response.status === 404) {
                    console.warn(`CEAD data for ${targetCod} not found. Using empty dataset.`);
                    STATE_DATA_CEAD.allData = [];
                } else {
                    throw new Error(`Failed to load ${fileUrl}: ${response.status} ${response.statusText}`);
                }
            } else {
                // Decompress gzip
                const ds = new DecompressionStream('gzip');
                const decompressed = new Response(response.body.pipeThrough(ds));
                const rawData = await decompressed.json();

                console.log('🔍 CEAD Raw Data Sample:', rawData[0]);
                console.log('🔍 CEAD Total rows loaded:', rawData.length);

                // Habilitar datos completos (incluyendo proyecciones 202510-202512)
                const filteredData = rawData;
                console.log('📅 CEAD Data fully loaded (including projections). Total rows:', filteredData.length);

                // Separate 'Total' from individual delitos
                STATE_DATA_CEAD.allDataHistory = filteredData.filter(
                    row => row[COLS_CEAD.DELITO] !== 'Total' && row[COLS_CEAD.DELITO] !== 'TOTAL');
                STATE_DATA_CEAD.allDataHistory_total = filteredData.filter(
                    row => row[COLS_CEAD.DELITO] === 'Total' || row[COLS_CEAD.DELITO] === 'TOTAL');

                console.log('📊 CEAD Delitos individuales:', STATE_DATA_CEAD.allDataHistory.length);
                console.log('📊 CEAD Filas Total:', STATE_DATA_CEAD.allDataHistory_total.length);

                STATE_DATA_CEAD.allData = STATE_DATA_CEAD.allDataHistory;
            }

            if (STATE_DATA_CEAD.allDataHistory_total.length > 0) {
                // Get max ID_PERIODO
                const allPeriodos = STATE_DATA_CEAD.allDataHistory_total
                    .map(row => row[COLS_CEAD.ID_PERIODO])
                    .filter(p => p != null);
                const maxPeriodo = allPeriodos.length > 0 ? Math.max(...allPeriodos) : 0;

                STATE_DATA_CEAD.periodoId = maxPeriodo;

                const latestRow = STATE_DATA_CEAD.allDataHistory_total.find(
                    row => row[COLS_CEAD.ID_PERIODO] === maxPeriodo);

                if (latestRow) {
                    STATE_DATA_CEAD.comunaName = String(latestRow[COLS_CEAD.COMUNA] || 'Sin Comuna');
                    STATE_DATA_CEAD.regionName = String(latestRow[COLS_CEAD.REGION] || 'Sin Región');
                    STATE_DATA_CEAD.periodoDetalle = latestRow[COLS_CEAD.PERIODO_DETALLE] || '';
                    STATE_DATA_CEAD.lastMonth = latestRow[COLS_CEAD.MES];
                    STATE_DATA_CEAD.lastYear = latestRow[COLS_CEAD.ANIO];
                    STATE_DATA_CEAD.warning = latestRow[COLS_CEAD.ALERTA];
                }
            }

            STATE_DATA_CEAD.isLoaded = true;
            this._hasLoaded = true;
            this._loadingInProgress = false;

            window.dispatchEvent(new CustomEvent('dataCeadLoaded', { detail: STATE_DATA_CEAD }));

        } catch (error) {
            console.error("❌ Critical Error loading CEAD data:", error);
            STATE_DATA_CEAD.isLoaded = false;
            this._loadingInProgress = false;
            this._hasLoaded = false;
        }
    },

    updateHeader() {
        const subtitle = document.getElementById('headerSubtitleCead');
        if (subtitle) {
            subtitle.innerHTML = `${STATE_DATA_CEAD.periodoDetalle || 'Período Actual'}`;
        }

        const comunaBtn = document.getElementById('btnComunaTextCead');
        if (comunaBtn) {
            comunaBtn.textContent = STATE_DATA_CEAD.comunaName || 'Santiago';
        }
    }
};

// Load data immediately
/*
(async () => {
    await dataLoaderCead.load();
})();
*/
// DISABLED: Using Unified DataManager