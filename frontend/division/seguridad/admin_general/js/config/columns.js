/**
 * Centralized Column Definitions (CEAD)
 * Single Source of Truth for frontend column names.
 * Ensures data_manager.js and data_cead.js work with consistent keys.
 */
window.COLS_CEAD = {
    // Core Columns
    ID_PERIODO: 'id_periodo',
    DELITO: 'delito',

    // CASOS_ACTUAL: Mapped to 'frecuencia' as per Python output
    // DO NOT CHANGE UNLESS PYTHON OUTPUT CHANGES
    CASOS_ACTUAL: 'frecuencia',

    CASOS_ANT: 'casos_mes_anterior',
    DELTA: 'delta',
    VAR_PCT: 'variacion_porcentual',

    // Time Dimensions
    ANIO: 'anio',
    MES: 'mes',
    MES_NUM: 'mes_num',

    // Geography
    COMUNA: 'comuna',
    REGION: 'region',

    // Metadata
    PERIODO_DETALLE: 'periodo_detalle',
    ALERTA: 'alerta_aumento_critico'
};

// Runtime Validation
if (typeof console !== 'undefined') {
    Object.keys(window.COLS_CEAD).forEach(key => {
        if (!window.COLS_CEAD[key]) {
            console.error(`❌ COLS_CEAD Config Error: Key ${key} is empty!`);
        }
    });
    console.log("✅ Column Config Loaded & Validated");
}
