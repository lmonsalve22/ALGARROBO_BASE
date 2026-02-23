
"""
comunas.py
==========
Genera data/comunas/data_comuna.json

Uso como módulo (desde notebook):
    import proceso
    import comunas
    df_comunas = comunas.df3          # DataFrame resultante

Uso como script independiente:
    python comunas.py                 # usa proceso.py para obtener df3 de STOP

Propósito:
    Consolida los indicadores clave de TODAS las comunas en la última semana
    disponible, para comparación inter-comunal en vista26 y vista27:
      - ¿Qué tan efectivos somos comparados con otras comunas?
      - ¿Nuestra carga delictual es proporcional a nuestra población?

Salida:
    data/comunas/data_comuna.json  (orient='records', compression='gzip', date_format='iso')
    Una fila por comuna · última semana disponible · solo filas delito='Total'
"""

import pandas as pd
import numpy as np
import warnings
import os
import sys

warnings.filterwarnings('ignore')

# ──────────────────────────────────────────
# CONFIG DE RUTAS
# ──────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR  = os.path.join(ROOT_DIR, 'data', 'comunas')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'data_comuna.json')

COLUMNAS_SALIDA = [
    # Identificadores
    'codcom', 'Comuna', 'Región', 'Codreg', 'Provincia',
    # Demografía
    'clase_poblacion', 'poblacion', 'factor_poblacion',
    # Temporalidad
    'id_semana', 'semana_detalle', 'año', 'fecha',
    # Carga delictual
    'frecuencia_total',
    'acumulado_anual',
    'proyeccion_anual',
    # Tasas x100k
    'tasa_semanal',
    'tasa_proyectada_anual',
    'tasa_semanal_regional',
    'tasa_proyectada_regional',
    # Rankings
    'ranking_nacional_semanal',
    'ranking_nacional_proy_anual',
    'ranking_comunal_regional',
    'ranking_cluster_semanal',
    'ranking_cluster_proy_anual',
    'ranking_nacional_acum',
    'ranking_nacional_semanal_tasa',
    'ranking_cluster_semanal_tasa',
    # IDI
    'idi_proy_mes',
    'idi_proy_anual',
    # Tendencia CP
    'media_movil_4s',
    't31_cagr_4s',
    't32_cagr_anual',
    # Concentración
    'aporte_pct_region',
    # Rachas
    'racha_alza',
    'racha_baja',
]


# ──────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────
def build(df_stop: pd.DataFrame) -> pd.DataFrame:
    """
    Recibe el df3 completo de proceso.py (todas las comunas, todos los delitos,
    todas las semanas) y devuelve un DataFrame con una fila por comuna
    correspondiente a la última semana disponible.

    Parámetros
    ----------
    df_stop : pd.DataFrame
        DataFrame completo generado por proceso.py (variable df3).

    Retorna
    -------
    pd.DataFrame
        Una fila por comuna con los KPIs de comparación inter-comunal.
    """
    df = df_stop.copy()
    print(f"📊 comunas.build() · {len(df):,} filas × {len(df.columns)} cols")

    # ── 1. Asegurar tipos base ──
    df['id_semana']  = pd.to_numeric(df['id_semana'],  errors='coerce')
    df['frecuencia'] = pd.to_numeric(df['frecuencia'], errors='coerce').fillna(0)
    df['codcom']     = pd.to_numeric(df['codcom'],      errors='coerce')

    # Normalizar columna año (algunas versiones usan 'year')
    if 'año' not in df.columns or df['año'].isna().all():
        if 'year' in df.columns:
            df['año'] = df['year']

    # Garantizar existencia de columnas opcionales
    for col in COLUMNAS_SALIDA + ['frecuencia', 'delito', 'year', 'semana_numero']:
        if col not in df.columns:
            df[col] = np.nan

    # ── 2. Filtrar solo filas 'Total' ──
    df_total = df[df['delito'].isin(['Total', 'TOTAL'])].copy()

    if df_total.empty:
        raise ValueError(
            "No se encontraron filas con delito='Total'. "
            "Verifica que proceso.py genera esa agrupación."
        )

    # ── 3. Última semana por comuna ──
    df_total = df_total.sort_values(['codcom', 'id_semana'])
    df_ultima = df_total.groupby('codcom').last().reset_index()
    print(f"   Comunas encontradas: {len(df_ultima)}")

    # ── 4. Alias y columnas derivadas ──
    df_ultima['frecuencia_total'] = df_ultima['frecuencia']

    # Población desde factor si no existe
    mask_pob = df_ultima['poblacion'].isna() & df_ultima['factor_poblacion'].notna()
    df_ultima.loc[mask_pob, 'poblacion'] = df_ultima.loc[mask_pob, 'factor_poblacion'] * 100_000

    # Tasa semanal si falta
    mask_t = (
        df_ultima['tasa_semanal'].isna() &
        df_ultima['factor_poblacion'].notna() &
        (df_ultima['factor_poblacion'] > 0)
    )
    df_ultima.loc[mask_t, 'tasa_semanal'] = (
        df_ultima.loc[mask_t, 'frecuencia_total'] /
        df_ultima.loc[mask_t, 'factor_poblacion'] * 100_000
    )

    # Tasa proyectada si falta
    mask_tp = (
        df_ultima['tasa_proyectada_anual'].isna() &
        df_ultima['factor_poblacion'].notna() &
        (df_ultima['factor_poblacion'] > 0)
    )
    df_ultima.loc[mask_tp, 'tasa_proyectada_anual'] = (
        df_ultima.loc[mask_tp, 'proyeccion_anual'] /
        df_ultima.loc[mask_tp, 'factor_poblacion'] * 100_000
    )

    # ── NUEVO: Rankings por Tasa (Mayor tasa = Rank 1) ──
    df_ultima['ranking_nacional_semanal_tasa'] = df_ultima['tasa_semanal'].rank(ascending=False, method='min')
    
    # Ranking Cluster por Tasa
    # (Asegurar que clase_poblacion no sea nulo para agrupar bien, o tratar NaNs)
    df_ultima['ranking_cluster_semanal_tasa'] = df_ultima.groupby('clase_poblacion')['tasa_semanal'].rank(ascending=False, method='min')

    # 999 → NaN en rankings (sentinela de "sin datos")
    rank_cols = [
        'ranking_nacional_semanal', 'ranking_nacional_proy_anual',
        'ranking_comunal_regional', 'ranking_cluster_semanal',
        'ranking_cluster_proy_anual', 'ranking_nacional_acum',
        'ranking_nacional_semanal_tasa', 'ranking_cluster_semanal_tasa' # Nuevos
    ]
    for rc in rank_cols:
        if rc in df_ultima.columns:
            df_ultima[rc] = df_ultima[rc].replace(999, np.nan)

    # ── 5. Seleccionar columnas de salida ──
    for col in COLUMNAS_SALIDA:
        if col not in df_ultima.columns:
            df_ultima[col] = np.nan

    df_out = df_ultima[COLUMNAS_SALIDA].copy()

    # ── 6. Log de metadatos ──
    semana_ref = df_out['id_semana'].mode().iloc[0] if not df_out.empty else 'N/A'
    año_ref    = df_out['año'].mode().iloc[0]        if not df_out.empty else 'N/A'
    print(
        f"   ✅ Dataset: {len(df_out)} comunas · "
        f"{df_out['Codreg'].nunique()} regiones · "
        f"semana {int(semana_ref) if pd.notna(semana_ref) else 'N/A'} · "
        f"año {int(año_ref) if pd.notna(año_ref) else 'N/A'}"
    )

    return df_out


def save(df_out: pd.DataFrame) -> None:
    """Guarda el DataFrame en data/comunas/data_comuna.json (gzip)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_out.to_json(OUTPUT_FILE, orient='records', compression='gzip', date_format='iso')
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"💾 Guardado: {OUTPUT_FILE}  ({size_kb:.1f} KB · {len(df_out)} filas)")


# ──────────────────────────────────────────
# VARIABLE DE MÓDULO  →  import comunas; comunas.df3
# ──────────────────────────────────────────
def _init_module():
    """
    Se ejecuta cuando el módulo se importa.
    Construye el DataFrame inter-comunal Y guarda data_comuna.json.
    """
    try:
        proceso_mod = sys.modules.get('proceso')
        if proceso_mod is None:
            # Aquí es donde ocurre la magia (y el side-effect): al importar proceso,
            # se ejecuta todo el script y define proceso.df3
            import proceso as proceso_mod  # noqa: F401

        result = build(proceso_mod.df3)
        save(result)   # ← graba el JSON automáticamente
        return result

    except Exception as e:
        print(f"⚠️ comunas: no se pudo inicializar automáticamente ({e})")
        return pd.DataFrame()


df3 = _init_module()


# ──────────────────────────────────────────
# EJECUCIÓN DIRECTA  →  python comunas.py
# ──────────────────────────────────────────
if __name__ == '__main__':
    print("🚀 comunas.py — modo script independiente")

    # Si df3 ya está construido (proceso importado en _init_module), reusar
    if df3.empty:
        print("   Cargando proceso.py...")
        if SCRIPT_DIR not in sys.path:
            sys.path.insert(0, SCRIPT_DIR)
        import proceso  # noqa: F401
        df3 = build(proceso.df3)

    if df3.empty:
        print("❌ df3 vacío — revisa proceso.py")
        sys.exit(1)

    save(df3)
    print("\n🎯 comunas.py finalizado.")
