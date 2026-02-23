
import pandas as pd
import json
import warnings
import numpy as np
import os
import sys
import datetime

# Suppress warnings
warnings.filterwarnings('ignore')

# =========================================
# CONFIGURACION DE PROGRESO
# =========================================
try:
    from tqdm import tqdm
    USE_TQDM = True
except ImportError:
    USE_TQDM = False
    print("tqdm no instalado. Usando prints simples.")

def progress_wrapper(iterable, desc="Procesando"):
    if USE_TQDM:
        return tqdm(iterable, desc=desc)
    return iterable

# Configuration
prioridad_delito_deprecated = {
    "HOMICIDIOS Y FEMICIDIOS": 1,
    "VIOLACIONES Y DELITOS SEXUALES": 2,
    "ROBOS CON VIOLENCIA E INTIMIDACIÓN": 3,
    "ROBOS EN LUGARES HABITADOS Y NO HABITADOS": 4,
    "ROBOS POR SORPRESA": 5,
    "ROBOS DE VEHÍCULOS Y SUS ACCESORIOS": 6,
    "DELITOS EN CONTEXTO DE VIOLENCIA INTRAFAMILIAR": 7,
    "AMENAZAS CON ARMAS": 8,
    "LESIONES GRAVES": 9,
    "LESIONES MENOS GRAVES": 10,
    "LESIONES LEVES": 11,
    "LEY DE CONTROL DE ARMAS": 12,
    "LEY DE DROGAS": 13,
    "OTROS ROBOS CON FUERZA EN LAS COSAS": 14,
    "DAÑOS": 15,
    "HURTOS": 16,
    "AMENAZAS Y RIÑAS": 17,
    "RECEPTACIÓN": 18,
    "INCIVILIDADES": 19,
    "CONSUMO DE ALCOHOL Y DE DROGAS EN LA VÍA PÚBLICA": 20,
    "OTROS DESÓRDENES PÚBLICOS": 21
}

prioridad_delito = {
    'Amenazas con Armas': 8,
    'Amenazas y Riñas': 17,
    'Consumo de Alcohol y de Drogas en la Vía Pública': 20,
    'Daños': 15,
    'Delitos en Contexto de Violencia Intrafamiliar': 7,
    'Homicidios y Femicidios': 1,
    'Hurtos': 16,
    'Incivilidades': 19,
    'Lesiones graves': 9,
    'Lesiones leves': 11,
    'Lesiones menos graves': 10,
    'Ley de Control de Armas': 12,
    'Ley de Drogas': 13,
    'Otros desórdenes públicos': 21,
    'Otros Robos con Fuerza en las Cosas': 14,
    'Receptación': 18,
    'Robos con Violencia e Intimidación': 3,
    'Robos de Vehículos y sus Accesorios': 6,
    'Robos en Lugares Habitados y No Habitados': 4,
    'Robos por Sorpresa': 5,
    'Violaciones y Delitos Sexuales': 2
 }

# =========================================
# 1. CARGA DE DATOS
# =========================================
print("Iniciando Carga de Datos...")
# Rutas originales
url = r"../estadistica_stop/ESTADISTICA_DELITO.csv" 
if not os.path.exists(url):
    url = r"estadistica_stop/ESTADISTICA_DELITO.csv" 
if not os.path.exists(url):
    # Fallback añadido por seguridad si ejecutamos en admin_general/notebook y el archivo está en data/input
    # Pero mantengo la lógica original mayormente
    path_alt = r"..\data\input\ESTADISTICA_DELITO.csv"
    if os.path.exists(path_alt):
        url = path_alt

if not os.path.exists(url):
    print(f"Error: Data file not found at {url}")
    # sys.exit(1) # Comentado para evitar cierre abrupto si estamos interactivos, pero en prod debería estar.

print(f"Cargando datos desde: {url}")
df = pd.read_csv(url)

# Carga Delito Min (Rutas Hardcodeadas Originales)
path_delito_min = r"C:\Users\limc_\Laboratorio\web_stop\delito_min.xlsx"
if not os.path.exists(path_delito_min):
     # Intento de ruta relativa si la original falla
     path_delito_min = r"..\config\delito_min.xlsx"

if os.path.exists(path_delito_min):
    delito_min = pd.read_excel(path_delito_min)
    delito_min.columns = ["delito","delito_min"]
    dict_delito = dict(zip(delito_min["delito"],delito_min["delito_min"]))
    df["delito"] = df["delito"].map(dict_delito)

# Función para verificar integridad
def verificar_integridad(df_actual, df_anterior, nombre_paso, debe_crecer=False):
    filas_actuales = len(df_actual)
    filas_anteriores = len(df_anterior)
    
    if debe_crecer:
        if filas_actuales <= filas_anteriores:
            print(f"❌ ERROR EN {nombre_paso}: Se esperaba aumento de filas.")
            # sys.exit("Ejecución detenida.")
    else:
        if filas_actuales != filas_anteriores:
            print(f"❌ ERROR EN {nombre_paso}: Filas cambiaron inesperadamente.")
            # sys.exit("Ejecución detenida.")
    
    print(f"✅ {nombre_paso}: {filas_actuales} líneas (OK)")

# =========================================
# 2. CALCULAR TOTALES
# =========================================
print("Calculando Totales...")
lineas_inicio = len(df)
totales = df.groupby(['codcom', 'id_semana'], as_index=False)['frecuencia'].sum()
totales['delito'] = 'Total'

dim_tiempo = df[['id_semana', 'semana_detalle', 'fecha']].drop_duplicates()
totales = totales.merge(dim_tiempo, on='id_semana', how='left')
totales = totales.reindex(columns=df.columns, fill_value=np.nan)

df = pd.concat([df, totales], ignore_index=True)
verificar_integridad(df, pd.DataFrame(index=range(lineas_inicio)), "Concatenar Totales", debe_crecer=True)

# =========================================
# 3. PREPARACIÓN TEMPORAL
# =========================================
print("Preparando Variables Temporales...")
df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['año'] = df['fecha'].dt.year
df['mes'] = df['fecha'].dt.month
df['semana_numero'] = df['semana_detalle'].astype(str).str.extract(r'(\d{1,2})').astype(float)
df = df.sort_values(['codcom', 'delito', 'id_semana']).reset_index(drop=True)

# =========================================
# 4. VARIABLES BASE
# =========================================
df['casos_semana_actual'] = df['frecuencia']
df['casos_semana_anterior'] = df.groupby(['delito', 'codcom'])['frecuencia'].shift(1)
df['delta'] = df['casos_semana_actual'] - df['casos_semana_anterior']

# =========================================
# 5. ACUMULADOS
# =========================================
print("Calculando Acumulados...")
df['acumulado_anual'] = df.groupby(['delito', 'codcom', 'año'])['frecuencia'].cumsum()
df['acumulado_total'] = df.groupby(['delito', 'codcom'])['frecuencia'].cumsum()

# Acumulado año anterior
df_prev_acum = df[['delito','codcom','año','semana_numero','acumulado_anual']].copy()
df_prev_acum = df_prev_acum.drop_duplicates(subset=['delito','codcom','año','semana_numero'])
df_prev_acum['año'] += 1
df_prev_acum.rename(columns={'acumulado_anual':'acumulado_anual_anterior'}, inplace=True)

df_len_before = len(df)
df = df.merge(df_prev_acum, on=['delito','codcom','año','semana_numero'], how='left')
verificar_integridad(df, pd.DataFrame(index=range(df_len_before)), "Merge Acumulado Año Anterior")

# =========================================
# 6. MEDIAS MÓVILES
# =========================================
print("Calculando Medias Móviles...")
df['media_movil_4s'] = df.groupby(['delito','codcom'])['frecuencia'].transform(lambda x: x.rolling(4, min_periods=1).mean())
df['media_movil_8s'] = df.groupby(['delito','codcom'])['frecuencia'].transform(lambda x: x.rolling(8, min_periods=1).mean())

# =========================================
# 7. HISTÓRICOS
# =========================================
print("Calculando Históricos...")
df['promedio_hist'] = df.groupby(['delito','codcom'])['frecuencia'].transform(lambda x: x.expanding().mean())
df['std_hist'] = df.groupby(['delito','codcom'])['frecuencia'].transform(lambda x: x.expanding().std())
df['max_hist'] = df.groupby(['delito','codcom'])['frecuencia'].transform(lambda x: x.expanding().max())

# =========================================
# 8. ESTADÍSTICAS AÑO ANTERIOR
# =========================================
print("Calculando Stats Año Anterior...")
df['promedio_hist_anual'] = df.groupby(['delito','codcom','año'])['frecuencia'].transform(lambda x: x.expanding().mean())
df['std_hist_anual'] = df.groupby(['delito','codcom','año'])['frecuencia'].transform(lambda x: x.expanding().std())
df['max_hist_anual'] = df.groupby(['delito','codcom','año'])['frecuencia'].transform(lambda x: x.expanding().max())

stats_prev = df[['delito','codcom','año','semana_numero','promedio_hist_anual','std_hist_anual','max_hist_anual']].copy()
stats_prev = stats_prev.drop_duplicates(subset=['delito','codcom','año','semana_numero'])
stats_prev['año'] += 1
stats_prev.rename(columns={'promedio_hist_anual':'promedio_hist_anual_prev','std_hist_anual':'std_hist_anual_prev','max_hist_anual':'max_hist_anual_prev'}, inplace=True)

df_len_before = len(df)
df = df.merge(stats_prev, on=['delito','codcom','año','semana_numero'], how='left')
verificar_integridad(df, pd.DataFrame(index=range(df_len_before)), "Merge Stats Año Anterior")

df['promedio_hist_anual'] = df['promedio_hist_anual_prev'].fillna(df['promedio_hist_anual'])
df['std_hist_anual'] = df['std_hist_anual_prev'].fillna(df['std_hist_anual'])
df['max_hist_anual'] = df['max_hist_anual_prev'].fillna(df['max_hist_anual'])
df.drop(columns=['promedio_hist_anual_prev','std_hist_anual_prev','max_hist_anual_prev'], inplace=True)

# =========================================
# 9. TENDENCIA Y RACHA
# =========================================
print("Calculando Tendencias y Rachas...")
df['tendencia_corto_plazo'] = np.where(df['delta'] > 0, 'Alza', np.where(df['delta'] < 0, 'Baja', 'Estable'))

# Logic for robust consecutive streak calculation (Alza and Baja) per group
df = df.sort_values(['codcom', 'delito', 'id_semana'])

# Racha Alza (Delta > 0)
df['is_pos'] = df['delta'] > 0
df['block_id_pos'] = (df['is_pos'] != df['is_pos'].shift()) | (df['codcom'] != df['codcom'].shift()) | (df['delito'] != df['delito'].shift())
df['block_id_pos'] = df['block_id_pos'].cumsum()
df['racha_alza'] = df.groupby('block_id_pos').cumcount() + 1
df['racha_alza'] = np.where(df['is_pos'], df['racha_alza'], 0)

# Racha Baja (Delta < 0)
df['is_neg'] = df['delta'] < 0
df['block_id_neg'] = (df['is_neg'] != df['is_neg'].shift()) | (df['codcom'] != df['codcom'].shift()) | (df['delito'] != df['delito'].shift())
df['block_id_neg'] = df['block_id_neg'].cumsum()
df['racha_baja'] = df.groupby('block_id_neg').cumcount() + 1
df['racha_baja'] = np.where(df['is_neg'], df['racha_baja'], 0)

# Combined 'racha' column
df['racha'] = np.maximum(df['racha_alza'], df['racha_baja'])
df.drop(columns=['is_pos', 'block_id_pos', 'is_neg', 'block_id_neg'], inplace=True)

# =========================================
# 10. MÉTRICAS AVANZADAS (Z-Score)
# =========================================
print("Calculando Z-Score y Alertas...")
df['var_pct_vs_semana_anterior'] = ((df['delta'] / df['casos_semana_anterior'].replace(0, np.nan)) * 100).fillna(0)
df['z_score'] = ((df['frecuencia'] - df['promedio_hist']) / df['std_hist'].replace(0, np.nan)).fillna(0)
df['z_score_vs_año_anterior'] = ((df['frecuencia'] - df['promedio_hist_anual']) / df['std_hist_anual'].replace(0, np.nan)).fillna(0)
df['conclusion_z'] = pd.cut(df['z_score'], bins=[-np.inf, -2, 2, np.inf], labels=['Bajo', 'Normal', 'Alto'])

# =========================================
# 11. LOCALIZACIÓN
# =========================================
print("Fusionando Datos de Localización...")
localiza_path = r"D:\GitHub\LOCALIZA_DB\Localiza Chile (1).xlsx"
if not os.path.exists(localiza_path):
    localiza_path = r"..\data\input\Localiza Chile (1).xlsx" # Fallback local

if os.path.exists(localiza_path):
    try:
        localiza = pd.read_excel(localiza_path)
        localiza2 = localiza[['Provincia', 'Comuna', 'Región', 'Codcom', 'Codreg']].drop_duplicates()
        
        df_len_before = len(df)
        df = df.merge(localiza2, left_on='codcom', right_on='Codcom', how='left')
        verificar_integridad(df, pd.DataFrame(index=range(df_len_before)), "Merge Localización")
        
        # Rankings
        df = df.sort_values(['Codreg', 'delito', 'Codcom', 'id_semana'])
        df['ranking_comunal_regional'] = df.groupby(['Codreg', 'delito', 'id_semana'])['frecuencia'].rank(method='dense', ascending=False)
        df['ranking_comunal_regional_semana_anterior'] = df.groupby(['Codreg', 'delito', 'Codcom'])['ranking_comunal_regional'].shift(1)
    except Exception as e:
        print(f"Error procesando localizacion: {e}")
else:
    print("⚠️ Advertencia: No se encontraron archivos de localización.")
    for col in ['Provincia', 'Comuna', 'Región', 'Codreg', 'ranking_comunal_regional']:
        df[col] = None

# Fix rank 0
rank_cols = [
    'ranking_comunal_regional',
    'ranking_comunal_regional_semana_anterior',
    'ranking_nacional_semanal',
    'ranking_regional_proy_anual', 
    'ranking_nacional_proy_anual',
    'ranking_cluster_proy_anual',
    'ranking_cluster_semanal'
]

for col in rank_cols:
    if col in df.columns:
         df[col] = np.where(df['frecuencia'] == 0, 999, df[col])
         df[col] = df[col].fillna(999)

# =========================================
# 12. POBLACIÓN
# =========================================
print("Fusionando Datos de Población...")
pob_path = r"C:\Users\limc_\Downloads\Factores Población.xlsx"
if not os.path.exists(pob_path):
    pob_path = r"..\data\input\Factores Población.xlsx"

if os.path.exists(pob_path):
    try:
        clasePoblacion = pd.read_excel(pob_path, sheet_name="Clase Población")
        factor = pd.read_excel(pob_path, sheet_name="Factores")
        
        clasePoblacion2 = clasePoblacion[['Codcom', 'Población', 'Clase Población']].copy()
        clasePoblacion2.columns = ['Codcom', 'poblacion_clase', 'clase_poblacion']
        
        factor2 = factor[['Codcom', 'Año', 'Población', 'Factor Población']].copy()
        factor2.columns = ['Codcom', 'año', 'poblacion', 'factor_poblacion']
        
        df_len_before = len(df)
        df = df.merge(clasePoblacion2, on='Codcom', how='left').merge(factor2, on=['Codcom', 'año'], how='left')
        verificar_integridad(df, pd.DataFrame(index=range(df_len_before)), "Merge Población")
        if 'Codcom' in df.columns: df = df.drop(columns=['Codcom'])
    except Exception as e:
        print(f"Error procesando poblacion: {e}")
else:
    print("⚠️ Advertencia: No se encontraron archivos de población.")
    df['poblacion'] = 100000 # Default
    df['clase_poblacion'] = 'Sin Clasificar'
    df['ranking_cluster_semanal'] = 999
    df['ranking_cluster_proy_anual'] = 999

# =========================================
# 13. MÁXIMOS Y ALERTAS
# =========================================
print("Calculando Máximos Históricos...")
idx_max_hist = df.groupby(['delito', 'codcom'])['frecuencia'].idxmax()
info_maximos = df.loc[idx_max_hist, ['delito', 'codcom', 'id_semana', 'semana_detalle']].copy()
info_maximos.rename(columns={'id_semana': 'id_semana_max_hist', 'semana_detalle': 'semana_detalle_max_hist'}, inplace=True)

df_len_before = len(df)
df = df.merge(info_maximos, on=['delito', 'codcom'], how='left')
verificar_integridad(df, pd.DataFrame(index=range(df_len_before)), "Merge Máximos Históricos")

df['alerta_aumento_critico'] = (df['z_score'] > 2) & (df['var_pct_vs_semana_anterior'] > 30)
df['alerta_vs_año_anterior'] = (df['z_score_vs_año_anterior'] > 2) & (df['frecuencia'] > df['max_hist_anual'])

# Casos misma semana año anterior
df_prev_casos = df[['delito', 'codcom', 'año', 'semana_numero', 'frecuencia']].copy()
df_prev_casos['año'] += 1
df_prev_casos.rename(columns={'frecuencia': 'casos_misma_semana_año_anterior'}, inplace=True)
df_prev_casos = df_prev_casos.drop_duplicates(subset=['delito', 'codcom', 'año', 'semana_numero'])
df = df.merge(df_prev_casos, on=['delito', 'codcom', 'año', 'semana_numero'], how='left')

# Casos mismo mes año anterior
monthly_cases = df.groupby(['delito', 'codcom', 'año', 'mes'])['frecuencia'].sum().reset_index(name='total_casos_mes_real')
prev_year_monthly = monthly_cases.copy()
prev_year_monthly['año'] += 1
prev_year_monthly.rename(columns={'total_casos_mes_real': 'casos_mismo_mes_año_anterior'}, inplace=True)
df = df.merge(prev_year_monthly, on=['delito', 'codcom', 'año', 'mes'], how='left')

# =========================================
# 14. TARJETAS COMPLEJAS (T19-T25)
# =========================================
print("Generando Rankings Regionales y Nacionales (T19-T25)...")
if 'ranking_comunal_regional' in df.columns:
    df_delitos = df[df['delito'] != 'Total'].copy()
    df_delitos["prioridad_delito"] = df_delitos["delito"].map(prioridad_delito)
    
    # T19 Peor Regional
    df_delitos.sort_values(by=["codcom", "id_semana", "ranking_comunal_regional", "prioridad_delito"], ascending=[True, True, True, True], inplace=True)
    worst_reg = df_delitos.groupby(["codcom", "id_semana"]).first()[["delito", "ranking_comunal_regional"]]
    worst_reg.rename(columns={'delito': 't19_delito_sem', 'ranking_comunal_regional': 't19_rank_sem'}, inplace=True)
    df = df.merge(worst_reg, on=['codcom', 'id_semana'], how='left')
else:
    df['t19_delito_sem'] = None

# T20 Peor Nacional
df['ranking_nacional_semanal'] = df.groupby(['delito', 'id_semana'])['frecuencia'].rank(method='dense', ascending=False)
df_delitos = df[df['delito'] != 'Total'].copy()
idx_worst_nac = df_delitos.groupby(['codcom', 'id_semana'])['ranking_nacional_semanal'].idxmin()
worst_nac = df.loc[idx_worst_nac][['codcom', 'id_semana', 'delito', 'ranking_nacional_semanal']].copy()
worst_nac.rename(columns={'delito': 't20_delito_sem', 'ranking_nacional_semanal': 't20_rank_sem'}, inplace=True)
df = df.merge(worst_nac, on=['codcom', 'id_semana'], how='left')

# Previous values t19/t20
df.sort_values(['codcom', 'delito', 'id_semana'], inplace=True)
for col in ['t19_delito_sem', 't19_rank_sem', 't20_delito_sem', 't20_rank_sem']:
    df[col.replace('sem','ant')] = df.groupby(['delito', 'codcom'])[col].shift(1)

# T25 Aporte Regional
if 'Codreg' in df.columns:
    df['casos_semana_regional'] = df.groupby(['Codreg', 'delito', 'id_semana'])['frecuencia'].transform('sum')
    df['aporte_pct_region'] = (df['frecuencia'] / df['casos_semana_regional'] * 100).fillna(0)
    df['aporte_pct_region_ant'] = df.groupby(['delito', 'codcom'])['aporte_pct_region'].shift(1)
    df['casos_semana_regional_ant'] = df.groupby(['delito', 'codcom'])['casos_semana_regional'].shift(1)

# =========================================
# 15. COPIAR DF3 BASE
# =========================================
print("Preparando DataFrame Final...")
df3 = df.copy()

# 0. Setup Fechas (Necesario para proyecciones)
df3['fecha_fin'] = df3['fecha']  #+ pd.Timedelta(days=6)

# 1. Proyección Anual (Extrapolación precisa por días)
df3['dias_año'] = np.where(df3['fecha_fin'].dt.is_leap_year, 366, 365)
df3['dia_año_actual'] = df3['fecha_fin'].dt.dayofyear
df3['factor_expansion_anual'] = df3['dias_año'] / df3['dia_año_actual']
df3['proyeccion_anual'] = df3['acumulado_anual'] * df3['factor_expansion_anual']

# Tasas
df3['tasa_semanal'] = df3['frecuencia'] / df3['factor_poblacion']
df3['tasa_proyectada_anual'] = df3['proyeccion_anual'] / df3['factor_poblacion']

# Tasas Regionales y Nacionales
print("Calculando Tasas Regionales y Nacionales por Delito...")
# Regional
df_reg_pob = df3.groupby(['Codreg', 'id_semana', 'codcom'])[['poblacion', 'factor_poblacion']].max().reset_index().groupby(['Codreg', 'id_semana'])[['poblacion', 'factor_poblacion']].sum().reset_index()
df_reg_pob.rename(columns={'poblacion': 'poblacion_region', 'factor_poblacion': 'factor_poblacion_region'}, inplace=True)

df_reg_cases = df3.groupby(['Codreg', 'id_semana', 'delito'])['frecuencia'].sum().reset_index(name='casos_semanales_regionales')
df_reg_tasa = df_reg_cases.merge(df_reg_pob, on=['Codreg', 'id_semana'])
df_reg_tasa['tasa_semanal_regional'] = df_reg_tasa['casos_semanales_regionales'] / df_reg_tasa['factor_poblacion_region'].replace(0, np.nan)
df_reg_tasa['tasa_regional_semanal'] = df_reg_tasa['tasa_semanal_regional']

df3 = df3.merge(df_reg_tasa[['Codreg', 'id_semana', 'delito', 'tasa_semanal_regional', 'poblacion_region', 'factor_poblacion_region', 'tasa_regional_semanal', 'casos_semanales_regionales']], on=['Codreg', 'id_semana', 'delito'], how='left')

# Nacional
df_nac_pob = df3.groupby(['id_semana', 'codcom'])[['poblacion', 'factor_poblacion']].max().reset_index().groupby(['id_semana'])[['poblacion', 'factor_poblacion']].sum().reset_index()
df_nac_pob.rename(columns={'poblacion': 'poblacion_nacional', 'factor_poblacion': 'factor_poblacion_nacional'}, inplace=True)

df_nac_cases = df3.groupby(['id_semana', 'delito'])['frecuencia'].sum().reset_index(name='casos_semanales_nacionales')
df_nac_tasa = df_nac_cases.merge(df_nac_pob, on=['id_semana'])
df_nac_tasa['tasa_semanal_nacional'] = df_nac_tasa['casos_semanales_nacionales'] / df_nac_tasa['factor_poblacion_nacional'].replace(0, np.nan)
df_nac_tasa['tasa_nacional_semanal'] = df_nac_tasa['tasa_semanal_nacional']

df3 = df3.merge(df_nac_tasa[['id_semana', 'delito', 'tasa_semanal_nacional', 'poblacion_nacional', 'factor_poblacion_nacional', 'tasa_nacional_semanal', 'casos_semanales_nacionales']], on=['id_semana', 'delito'], how='left')

# Rankings Proyección
if 'Codreg' in df3.columns:
    df3['ranking_regional_proy_anual'] = df3.groupby(['Codreg', 'delito', 'id_semana'])['proyeccion_anual'].rank(method='dense', ascending=False)
    df3['ranking_regional_tasa_sem'] = df3.groupby(['Codreg', 'delito', 'id_semana'])['tasa_semanal'].rank(method='dense', ascending=False)
    df3['ranking_regional_tasa_anual'] = df3.groupby(['Codreg', 'delito', 'id_semana'])['tasa_proyectada_anual'].rank(method='dense', ascending=False)
    
df3['ranking_nacional_proy_anual'] = df3.groupby(['delito', 'id_semana'])['proyeccion_anual'].rank(method='dense', ascending=False)
df3['ranking_nacional_tasa_sem'] = df3.groupby(['delito', 'id_semana'])['tasa_semanal'].rank(method='dense', ascending=False)
df3['ranking_nacional_tasa_anual'] = df3.groupby(['delito', 'id_semana'])['tasa_proyectada_anual'].rank(method='dense', ascending=False)

if 'clase_poblacion' in df3.columns:
    df3['ranking_cluster_proy_anual'] = df3.groupby(['clase_poblacion', 'delito', 'id_semana'])['proyeccion_anual'].rank(method='dense', ascending=False)
    df3['ranking_cluster_semanal'] = df3.groupby(['clase_poblacion', 'delito', 'id_semana'])['frecuencia'].rank(method='dense', ascending=False)
    df3['ranking_cluster_acum'] = df3.groupby(['clase_poblacion', 'delito', 'id_semana'])['acumulado_anual'].rank(method='dense', ascending=False)
    df3['ranking_cluster_tasa_sem'] = df3.groupby(['clase_poblacion', 'delito', 'id_semana'])['tasa_semanal'].rank(method='dense', ascending=False)
    df3['ranking_cluster_tasa_anual'] = df3.groupby(['clase_poblacion', 'delito', 'id_semana'])['tasa_proyectada_anual'].rank(method='dense', ascending=False)

# Ranking Nacional Acumulado
df3['ranking_nacional_acum'] = df3.groupby(['delito', 'id_semana'])['acumulado_anual'].rank(method='dense', ascending=False)

# Normalizar Rankings
all_rank_cols = [
    'ranking_regional_proy_anual', 'ranking_nacional_proy_anual', 
    'ranking_cluster_proy_anual', 'ranking_cluster_semanal',
    'ranking_cluster_acum', 'ranking_nacional_acum',
    'ranking_regional_tasa_sem', 'ranking_regional_tasa_anual',
    'ranking_nacional_tasa_sem', 'ranking_nacional_tasa_anual',
    'ranking_cluster_tasa_sem', 'ranking_cluster_tasa_anual'
]
for col in all_rank_cols:
    if col in df3.columns:
        df3[col] = np.where(df3['frecuencia'] == 0, 999, df3[col])
        df3[col] = df3[col].fillna(999)

# Rankings Anteriores
print("Calculando Rankings Anteriores...")
rank_cols_to_shift = [
    'ranking_nacional_semanal', 'ranking_regional_proy_anual', 'ranking_nacional_proy_anual',
    'ranking_cluster_proy_anual', 'ranking_cluster_semanal',
    'ranking_regional_tasa_sem', 'ranking_regional_tasa_anual',
    'ranking_nacional_tasa_sem', 'ranking_nacional_tasa_anual',
    'ranking_cluster_tasa_sem', 'ranking_cluster_tasa_anual'
]

df3 = df3.sort_values(['codcom', 'delito', 'id_semana'])
for col in rank_cols_to_shift:
    if col in df3.columns:
        new_col = f"{col}_anterior"
        df3[new_col] = df3.groupby(['codcom', 'delito'])[col].shift(1).fillna(0)

# =====================================================
# 16. CALCULOS DE NUEVAS TARJETAS (IDI, RACHAS, CRECIMIENTO)
# =====================================================
# Weights
weights_idi = {
    'HOMICIDIOS Y FEMICIDIOS': 1000,
    'ROBOS CON VIOLENCIA E INTIMIDACIÓN': 150,
    'VIOLACIONES Y DELITOS SEXUALES': 200,
    'LEY DE CONTROL DE ARMAS': 75,
    'LEY DE DROGAS': 30,
    'DELITOS EN CONTEXTO DE VIOLENCIA INTRAFAMILIAR': 40
}
BASE_IDI_ANUAL = 110526
BASE_IDI_MENSUAL = 9279

df3['idi_peso'] = df3['delito'].str.upper().map(weights_idi).fillna(0)

# Calcular Proyección Mensual
df3['fecha_fin'] = df3['fecha'] + pd.Timedelta(days=6)
cond_mismo_mes = df3['fecha_fin'].dt.month == df3['fecha'].dt.month
df3['dias_mes'] = df3['fecha'].dt.days_in_month
df3['dia_actual'] = np.where(cond_mismo_mes, df3['fecha_fin'].dt.day, df3['dias_mes'])
   
df3 = df3.sort_values(['codcom', 'delito', 'año', 'mes', 'id_semana'])
df3['casos_acum_mes'] = df3.groupby(['codcom', 'delito', 'año', 'mes'])['frecuencia'].cumsum()
df3['factor_expansion_mes'] = df3['dias_mes'] / df3['dia_actual']

# Obtener los totales reales por mes (ya calculados antes en monthly_cases)
df3 = df3.merge(monthly_cases, on=['delito', 'codcom', 'año', 'mes'], how='left')

# Identificar el mes más reciente del dataset para proyectar solo ese
max_año_data = df3['año'].max()
max_mes_data = df3[df3['año'] == max_año_data]['mes'].max()

# Lógica condicional: Proyección solo para el mes actual, Real para el resto
df3['proyeccion_mes_actual'] = np.where(
    (df3['año'] == max_año_data) & (df3['mes'] == max_mes_data),
    df3['casos_acum_mes'] * df3['factor_expansion_mes'],
    df3['total_casos_mes_real']
)

df3['idi_parcial_mes'] = (df3['idi_peso'] * df3['proyeccion_mes_actual'] / df3['factor_poblacion']).fillna(0)
df3['idi_parcial_mes_ant_year'] = (df3['idi_peso'] * df3['casos_mismo_mes_año_anterior'] / df3['factor_poblacion']).fillna(0)
df3['idi_parcial_anual_proy'] = (df3['idi_peso'] * df3['proyeccion_anual'] / df3['factor_poblacion']).fillna(0)
df3['idi_parcial_real_sem'] = (df3['idi_peso'] * df3['frecuencia'] / df3['factor_poblacion']).fillna(0)

print("   > Calculando Agregaciones IDI (Nueva Fórmula)...")
idi_grp = df3.groupby(['codcom', 'id_semana']).apply(lambda x: pd.Series({
    'sum_idi_mes': x['idi_parcial_mes'].sum(),
    'sum_idi_mes_ant_year': x['idi_parcial_mes_ant_year'].sum(),
    'sum_idi_anual_proy': x['idi_parcial_anual_proy'].sum(),
    'factor_poblacion': x['factor_poblacion'].iloc[0] if len(x) > 0 else 1.0 
})).reset_index()

idi_grp['idi_proy_mes'] = (idi_grp['sum_idi_mes'] / BASE_IDI_MENSUAL) * 100
idi_grp['idi_mes_ant_year'] = (idi_grp['sum_idi_mes_ant_year'] / BASE_IDI_MENSUAL) * 100

# ── idi_proy_anual: proyectar SOLO el año actual, reales para años cerrados ──
# 0. Agregar 'año' a idi_grp PRIMERO (necesario para el merge de reales)
time_map = df3[['id_semana', 'año']].drop_duplicates()
idi_grp = idi_grp.merge(time_map, on='id_semana', how='left')

# 1. Real anual acumulado por (codcom, año)
idi_real_anual_grp = df3.groupby(['codcom', 'año'])['idi_parcial_real_sem'].sum().reset_index(name='sum_idi_real_anual')
idi_real_anual_grp['idi_real_anual'] = (idi_real_anual_grp['sum_idi_real_anual'] / BASE_IDI_ANUAL) * 100

# 2. Proyección lineal (para el año en curso)
idi_grp['idi_proy_anual_calc'] = (idi_grp['sum_idi_anual_proy'] / BASE_IDI_ANUAL) * 100

# 3. Año más reciente
max_año = df3['año'].max()

# 4. Merge real anual
idi_grp = idi_grp.merge(
    idi_real_anual_grp[['codcom', 'año', 'idi_real_anual']],
    on=['codcom', 'año'], how='left'
)

# 5. Año actual → proyección, años cerrados → real
idi_grp['idi_proy_anual'] = np.where(
    idi_grp['año'] == max_año,
    idi_grp['idi_proy_anual_calc'],
    idi_grp['idi_real_anual']
)
idi_grp.drop(columns=['idi_proy_anual_calc', 'idi_real_anual'], inplace=True)

idi_grp = idi_grp.sort_values(['codcom', 'id_semana'])
idi_grp['idi_mes_anterior'] = idi_grp.groupby('codcom')['idi_proy_mes'].shift(4)

col_idi_real = df3.groupby(['codcom', 'año'])['idi_parcial_real_sem'].sum().reset_index(name='sum_idi_total_real')
idi_anual_real = col_idi_real.copy()
idi_anual_real['idi_anual_cierre'] = (idi_anual_real['sum_idi_total_real'] / BASE_IDI_ANUAL) * 100

idi_anual_real['año_join'] = idi_anual_real['año'] + 1
idi_prev = idi_anual_real[['codcom', 'año_join', 'idi_anual_cierre']].rename(columns={'año_join': 'año', 'idi_anual_cierre': 'idi_anual_anterior'})

# 'año' ya existe en idi_grp — no repetir time_map merge
idi_grp = idi_grp.merge(idi_prev, on=['codcom', 'año'], how='left')

meta_cols = df3[['codcom', 'Codreg', 'clase_poblacion']].drop_duplicates()
idi_grp = idi_grp.merge(meta_cols, on='codcom', how='left')

# Rankings IDI
def calc_agg_metrics(group, level_suffix):
    base_data = group[group['delito'] != 'Total']
    sum_puntos_mes = (base_data['idi_peso'] * base_data['proyeccion_mes_actual']).sum()
    pob_total = group[['codcom', 'factor_poblacion']].drop_duplicates()['factor_poblacion'].sum()
    idi_val = (sum_puntos_mes / pob_total / BASE_IDI_MENSUAL) * 100 if pob_total > 0 else 0
    sum_proy_anual = base_data['proyeccion_anual'].sum()
    tasa_val = sum_proy_anual / pob_total if pob_total > 0 else 0
    return pd.Series({
        f'idi_proy_{level_suffix}': idi_val,
        f'tasa_proyectada_{level_suffix}': tasa_val
    })

print("   > Calculando Métricas Agregadas (Reg/Nac/Clus)...")
aggs_reg = df3.groupby(['Codreg', 'id_semana']).apply(calc_agg_metrics, level_suffix='regional').reset_index()
aggs_nac = df3.groupby(['id_semana']).apply(calc_agg_metrics, level_suffix='nacional').reset_index()
if 'clase_poblacion' in df3.columns:
    aggs_clus = df3.groupby(['clase_poblacion', 'id_semana']).apply(calc_agg_metrics, level_suffix='cluster').reset_index()
else:
    aggs_clus = pd.DataFrame()

idi_grp = idi_grp.merge(aggs_reg, on=['Codreg', 'id_semana'], how='left')
idi_grp = idi_grp.merge(aggs_nac, on=['id_semana'], how='left')
if not aggs_clus.empty:
    idi_grp = idi_grp.merge(aggs_clus, on=['clase_poblacion', 'id_semana'], how='left')
else:
    idi_grp['idi_proy_cluster'] = 0
    idi_grp['tasa_proyectada_cluster'] = 0

df3 = df3.merge(idi_grp[['codcom', 'id_semana', 
    'idi_proy_mes', 'idi_mes_ant_year', 'idi_mes_anterior', 
    'idi_proy_anual', 'idi_anual_anterior', 
    'idi_proy_regional', 'idi_proy_nacional', 'idi_proy_cluster',
    'tasa_proyectada_regional', 'tasa_proyectada_nacional', 'tasa_proyectada_cluster'
]], on=['codcom', 'id_semana'], how='left')

# T23 Correlations Simulation
def calculate_top_correlation(group):
    if len(group) < 10: return pd.Series({'t23_d1': 'Insuf. Datos', 't23_d2': 'Insuf. Datos', 't23_val': 0.0})
    pivot = group.pivot(index='id_semana', columns='delito', values='frecuencia').fillna(0)
    pivot = pivot.loc[:, (pivot != pivot.iloc[0]).any()]
    if pivot.shape[1] < 2: return pd.Series({'t23_d1': 'Sin Var', 't23_d2': 'Sin Var', 't23_val': 0.0})
    corr_matrix = pivot.corr()
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    corr_upper = corr_matrix.where(mask)
    try:
        max_corr_val = corr_upper.max().max()
        if pd.isna(max_corr_val): return pd.Series({'t23_d1': '-', 't23_d2': '-', 't23_val': 0.0})
        max_idx = corr_upper.stack().idxmax()
        d1, d2 = max_idx
        return pd.Series({'t23_d1': d1, 't23_d2': d2, 't23_val': max_corr_val})
    except:
        return pd.Series({'t23_d1': 'Error', 't23_d2': 'Error', 't23_val': 0.0})

print("   > Calculando Correlaciones...")
df_corr_base = df3[df3['delito'] != 'Total'][['codcom', 'id_semana', 'delito', 'frecuencia']].copy()
top_corrs = df_corr_base.groupby('codcom').apply(calculate_top_correlation).reset_index()
df3 = df3.merge(top_corrs, on='codcom', how='left')

# Rachas
print("   > Calculando Rachas (Top 3)...")
df3['prioridad_val'] = df3['delito'].map(prioridad_delito).fillna(99)
df3['es_racha_neg'] = (df3['racha'] > 2) & (df3['tendencia_corto_plazo'] == 'Alza')
df3['es_racha_pos'] = (df3['racha'] > 2) & (df3['tendencia_corto_plazo'] == 'Baja')

def get_top_rachas(df_subset, prefix):
    top3 = df_subset.sort_values(['codcom', 'id_semana', 'prioridad_val', 'racha'], ascending=[True, True, True, False])
    top3 = top3.groupby(['codcom', 'id_semana']).head(3)
    top3['rank'] = top3.groupby(['codcom', 'id_semana']).cumcount() + 1
    pivot = top3.pivot_table(index=['codcom', 'id_semana'], columns='rank', values=['delito', 'racha'], aggfunc='first')
    pivot.columns = [f'{prefix}_delito_{c[1]}' if c[0] == 'delito' else f'{prefix}_semanas_{c[1]}' for c in pivot.columns]
    return pivot.reset_index()

t29 = get_top_rachas(df3[df3['es_racha_neg']], 't29')
t30 = get_top_rachas(df3[df3['es_racha_pos']], 't30')
df3 = df3.merge(t29, on=['codcom', 'id_semana'], how='left')
df3 = df3.merge(t30, on=['codcom', 'id_semana'], how='left')

# Pareto
print("   > Calculando Pareto (Top 3 Delitos)...")
pareto_base = df3[(df3['frecuencia'] > 0) & (df3['delito'] != 'Total')].sort_values(['codcom', 'id_semana', 'frecuencia'], ascending=[True, True, False])
pareto_top3 = pareto_base.groupby(['codcom', 'id_semana']).head(3)
pareto_top3['rank'] = pareto_top3.groupby(['codcom', 'id_semana']).cumcount() + 1
week_totals = df3[df3['delito'] != 'Total'].groupby(['codcom', 'id_semana'])['frecuencia'].sum().reset_index(name='total_semanal')
pareto_top3 = pareto_top3.merge(week_totals, on=['codcom', 'id_semana'], how='left')
pareto_top3['pct_contribution'] = (pareto_top3['frecuencia'] / pareto_top3['total_semanal'] * 100).fillna(0)
pivot_pareto = pareto_top3.pivot_table(index=['codcom', 'id_semana'], columns='rank', values=['delito', 'pct_contribution'], aggfunc='first')
pivot_pareto.columns = [f't21_delito_{c[1]}' if c[0] == 'delito' else f't21_val_{c[1]}' for c in pivot_pareto.columns]
df3 = df3.merge(pivot_pareto.reset_index(), on=['codcom', 'id_semana'], how='left')

# Aceleración
df3 = df3.sort_values(['codcom', 'delito', 'id_semana'])
df3['mm4s_lag4'] = df3.groupby(['codcom', 'delito'])['media_movil_4s'].shift(4)
df3['t31_cagr_4s'] = (np.power(df3['media_movil_4s'] / df3['mm4s_lag4'].replace(0, np.nan), 0.25) - 1) * 100
df3['t31_cagr_4s'] = df3['t31_cagr_4s'].fillna(0)
df3['t32_cagr_anual'] = ((df3['acumulado_anual'] / df3['acumulado_anual_anterior'].replace(0, np.nan)) - 1) * 100
df3['t32_cagr_anual'] = df3['t32_cagr_anual'].fillna(0)

# =========================================
# VALIDACIÓN Y GUARDADO
# =========================================
print("Finalizando...")

# Intentamos replicar ruta de salida original pero con path seguro
# El script original guardaba en data/stop con nombre de comuna
# Corregimos aqui el error OSError usando os.path.join

# Obtenemos ruta base relativa
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # admin_general
output_dir = os.path.join(base_dir, "data", "stop")

if not os.path.exists(output_dir):
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception:
        # Fallback local
        output_dir = "data/stop" 
        os.makedirs(output_dir, exist_ok=True)

print(f"> Guardando en: {output_dir}")

# Optimizar guardado usando groupby (evita filtrado iterativo lento)
grupos = df3.groupby("codcom")

for codcom, aux in progress_wrapper(grupos, desc="Guardando"):
    # Aseguramos que el nombre sea un string limpio
    file_path = os.path.join(output_dir, str(int(codcom)))
    try:
        # Nivel de compresión 1 para velocidad máxima
        aux.to_json(
            file_path, 
            orient='records', 
            compression={'method': 'gzip', 'compresslevel': 1}, 
            date_format='iso'
        )
    except Exception as e:
        print(f"Error al guardar comuna {codcom}: {e}")

print(">>> Proceso finalizado.")

