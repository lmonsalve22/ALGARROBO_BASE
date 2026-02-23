/**
 * RID SIMULATOR - Data Layer
 * Handles data loading and state management
 */

// Global State
window.STATE_DATA = {
    codcom: 5602,
    allData: [],
    allDataHistory: [],
    allDataHistory_total: [],
    stats: {},
    currentSection: 'seccion1',
    comunaName: 'Sin Comuna',
    regionName: 'Sin Región',
    semanaId: "Sin Semana",
    semanaDetalle: "",
    warning: "",
    isLoaded: false
};

// Column Keys - Mapeado DIRECTO a salida de proceso.py
// Lista actualizada por usuario
window.COLS = {
    // Identificadores Base
    DELITO: 'delito',
    FRECUENCIA: 'frecuencia',
    CODCOM: 'codcom',
    ID_SEMANA: 'id_semana',
    SEMANA_DETALLE: 'semana_detalle',
    FECHA: 'fecha',
    ANIO: 'año',
    MES: 'mes',
    SEMANA: 'semana_numero',
    // SEMANA_SAFE no existe en origen

    // Métricas Base
    CASOS_ACTUAL: 'casos_semana_actual',
    CASOS_ANT: 'casos_semana_anterior',
    DELTA: 'delta',
    ACUM_ANUAL: 'acumulado_anual',
    ACUM_TOTAL: 'acumulado_total',
    ACUM_ANUAL_ANT: 'acumulado_anual_anterior',

    // Medias y Stats
    MEDIA_MOVIL_4S: 'media_movil_4s',
    MEDIA_MOVIL_8S: 'media_movil_8s',
    PROMEDIO_HIST: 'promedio_hist',
    STD_HIST: 'std_hist',
    MAX_HIST: 'max_hist',
    PROMEDIO_HIST_ANUAL: 'promedio_hist_anual',
    STD_HIST_ANUAL: 'std_hist_anual',
    MAX_HIST_ANUAL: 'max_hist_anual',

    // Tendencias
    TENDENCIA: 'tendencia_corto_plazo',
    RACHA_ALZA: 'racha_alza',
    RACHA_BAJA: 'racha_baja',
    RACHA: 'racha',
    VAR_PCT_SEM: 'var_pct_vs_semana_anterior',

    // Z-Score
    Z_SCORE: 'z_score',
    Z_SCORE_YEAR_ANT: 'z_score_vs_año_anterior',
    Z_CONCL: 'conclusion_z',

    // Geografía
    PROVINCIA: 'Provincia',
    COMUNA: 'Comuna',
    REGION: 'Región',
    CODREG: 'Codreg',

    // Población
    POBLACION_CLASE: 'poblacion_clase',
    CLASE_POBLACION: 'clase_poblacion',
    POBLACION: 'poblacion',
    FACTOR_POBLACION: 'factor_poblacion',

    // Alertas y Comparativas Año Anterior
    SEMANA_MAX_HIST: 'id_semana_max_hist',
    SEMANA_DETALLE_MAX_HIST: 'semana_detalle_max_hist',
    ALERTA: 'alerta_aumento_critico',
    ALERTA_YEAR_ANT: 'alerta_vs_año_anterior',
    CASOS_YEAR_ANT: 'casos_misma_semana_año_anterior',
    CASOS_MES_YEAR_ANT: 'casos_mismo_mes_año_anterior',

    // Rankings Regionales
    RANKING: 'ranking_comunal_regional',
    RANKING_ANT: 'ranking_comunal_regional_semana_anterior',

    // Rankings Nacionales (Volumen)
    RANK_NAC_SEM: 'ranking_nacional_semanal',
    RANK_NAC_SEM_ANT: 'ranking_nacional_semanal_anterior',
    RANK_NAC_PROY: 'ranking_nacional_proy_anual',
    RANK_NAC_PROY_ANT: 'ranking_nacional_proy_anual_anterior',
    RANK_NAC_ACUM: 'ranking_nacional_acum',

    // Rankings Tasa (Nuevos)
    RANK_REG_TASA_SEM: 'ranking_regional_tasa_sem',
    RANK_REG_TASA_ANUAL: 'ranking_regional_tasa_anual',
    RANK_NAC_TASA_SEM: 'ranking_nacional_tasa_sem',
    RANK_NAC_TASA_ANUAL: 'ranking_nacional_tasa_anual',
    RANK_CLUSTER_TASA_SEM: 'ranking_cluster_tasa_sem',
    RANK_CLUSTER_TASA_ANUAL: 'ranking_cluster_tasa_anual',

    // Rankings Proyección y Cluster
    RANK_REG_PROY: 'ranking_regional_proy_anual',
    RANK_REG_PROY_ANT: 'ranking_regional_proy_anual_anterior',
    RANK_CLUSTER_PROY: 'ranking_cluster_proy_anual',
    RANK_CLUSTER_PROY_ANT: 'ranking_cluster_proy_anual_anterior',
    RANK_CLUSTER_SEM: 'ranking_cluster_semanal',
    RANK_CLUSTER_SEM_ANT: 'ranking_cluster_semanal_anterior',
    RANK_CLUSTER_ACUM: 'ranking_cluster_acum',

    // Diagnósticos T19/T20
    T19_DELITO: 't19_delito_sem',
    T19_RANK: 't19_rank_sem',
    T20_DELITO: 't20_delito_sem',
    T20_RANK: 't20_rank_sem',

    // Diagnósticos Anteriores
    T19_DELITO_ANT: 't19_delito_ant',
    T19_RANK_ANT: 't19_rank_ant',
    T20_DELITO_ANT: 't20_delito_ant',
    T20_RANK_ANT: 't20_rank_ant',

    // Aportes T25 e Indicadores Regionales
    CASOS_SEM_REG: 'casos_semana_regional',
    CASOS_REGIONALES__SEM: 'casos_semanales_regionales',
    APORTE_PCT: 'aporte_pct_region',
    APORTE_PCT_ANT: 'aporte_pct_region_ant',
    CASOS_SEM_REG_ANT: 'casos_semana_regional_ant',
    POB_REGION: 'poblacion_region',
    FACTOR_POB_REGION: 'factor_poblacion_region',
    TASA_REGIONAL_SEM: 'tasa_regional_semanal',
    POB_NACIONAL: 'poblacion_nacional',
    FACTOR_POB_NACIONAL: 'factor_poblacion_nacional',
    TASA_NACIONAL_SEM: 'tasa_nacional_semanal',

    // Proyecciones
    FECHA_FIN: 'fecha_fin',
    DIAS_ANO: 'dias_año',
    DIA_ANO_ACTUAL: 'dia_año_actual',
    FACTOR_EXP_ANUAL: 'factor_expansion_anual',
    PROYECCION_ANUAL: 'proyeccion_anual',
    TASA_SEMANAL: 'tasa_semanal',
    TASA_PROY_ANUAL: 'tasa_proyectada_anual',

    // IDI
    IDI_PESO: 'idi_peso',
    IDI_PROY_MES: 'idi_proy_mes',
    IDI_PROY_ANUAL: 'idi_proy_anual',

    // Rachas
    ES_RACHA_POS: 'es_racha_pos',
    ES_RACHA_NEG: 'es_racha_neg',

    // IDI Agregados
    IDI_PROY_REG: 'idi_proy_regional',
    IDI_PROY_NAC: 'idi_proy_nacional',
    IDI_PROY_CLUS: 'idi_proy_cluster',
    TASA_PROY_REG: 'tasa_proyectada_regional',
    TASA_PROY_NAC: 'tasa_proyectada_nacional',
    TASA_PROY_CLUS: 'tasa_proyectada_cluster',

    // T21 Pareto
    T21_DELITO_1: 't21_delito_1',
    T21_DELITO_2: 't21_delito_2',
    T21_DELITO_3: 't21_delito_3',
    T21_VAL_1: 't21_val_1',
    T21_VAL_2: 't21_val_2',
    T21_VAL_3: 't21_val_3',

    // Correlacion T23
    T23_D1: 't23_d1',
    T23_D2: 't23_d2',
    T23_VAL: 't23_val',

    // CAGR
    T31_CAGR_4S: 't31_cagr_4s',
    T32_CAGR_ANUAL: 't32_cagr_anual'
};

// Runtime Validation
if (typeof console !== 'undefined') {
    Object.keys(window.COLS).forEach(key => {
        if (!window.COLS[key]) {
            console.error(`❌ COLS Config Error: Key ${key} is empty!`);
        }
    });
    console.log("✅ Main Column Config (STOP) Reloaded & Validated");
}