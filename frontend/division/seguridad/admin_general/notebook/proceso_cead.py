import pandas as pd
import numpy as np
import os
import sys
import gc
import json
import datetime

# =============================================================================
# proceso_cead.py — Pipeline CEAD optimizado (velocidad + memoria)
# =============================================================================


def ejecutar_proceso():
    """Pipeline principal CEAD. Retorna df3 con métricas calculadas."""
    print(">>> Iniciando Proceso CEAD (Optimizado)...")
    t0 = datetime.datetime.now()

    # -----------------------------------------
    # 0. Utilidades
    # -----------------------------------------
    try:
        from tqdm import tqdm
        USE_TQDM = True
    except ImportError:
        USE_TQDM = False

    def progress_wrapper(iterable, desc="Procesando", total=None):
        if USE_TQDM:
            return tqdm(iterable, desc=desc, total=total, smoothing=0.1)
        return iterable

    def optimize_dtypes(df):
        """Downcast numéricos y convierte strings a category. Opera in-place."""
        start_mem = df.memory_usage(deep=True).sum() / 1024**2

        for col in df.columns:
            dtype = df[col].dtype

            if dtype == object:
                df[col] = df[col].astype('category')
            elif pd.api.types.is_integer_dtype(dtype):
                df[col] = pd.to_numeric(df[col], downcast='integer')
            elif pd.api.types.is_float_dtype(dtype):
                df[col] = pd.to_numeric(df[col], downcast='float')
            # datetime/category/bool: skip

        end_mem = df.memory_usage(deep=True).sum() / 1024**2
        print(f'   > RAM: {start_mem:.1f} → {end_mem:.1f} MB (-{100*(start_mem-end_mem)/max(start_mem,1):.0f}%)')
        return df

    # -----------------------------------------
    # 1. Constantes
    # -----------------------------------------
    START_FILL = "2025-10-01"
    END_FILL   = "2025-12-01"
    LIMIT_DATE = "2025-09-01"
    MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    MESES_CORTOS = {i+1: m for i, m in enumerate(MESES)}  
    TRIMESTRES = {1: 'Enero-Marzo', 2: 'Abril-Junio', 3: 'Julio-Septiembre', 4: 'Octubre-Diciembre'}
    MES_NUM = {m: i+1 for i, m in enumerate(MESES)}
    FILL_PERIODS = pd.date_range(start=START_FILL, end=END_FILL, freq='MS')
    N_FILL = len(FILL_PERIODS)

    def date_to_id(dt): return dt.year * 100 + dt.month

    # -----------------------------------------
    # 2. Funciones Auxiliares
    # -----------------------------------------
    def calc_estacionalidad(group):
        total_rows = group[group['delito'] == 'Total']
        EMPTY = pd.Series({'t22_mes_nombre': 'N/D', 't22_mes_pct': 0.0,
                           't22_trimestre_nombre': 'N/D', 't22_trimestre_pct': 0.0})
        if total_rows.empty:
            return EMPTY
        por_mes = total_rows.groupby('mes')['frecuencia'].sum()
        if por_mes.empty or por_mes.sum() == 0:
            return EMPTY
        prom = por_mes.mean()
        mes_max = por_mes.idxmax()
        mes_pct = ((por_mes[mes_max] - prom) / prom * 100) if prom > 0 else 0
        trimestres = ((total_rows['mes'].values - 1) // 3) + 1
        por_trim = pd.Series(total_rows['frecuencia'].values, index=trimestres).groupby(level=0).sum()
        prom_t = por_trim.mean()
        trim_max = por_trim.idxmax() if not por_trim.empty else 1
        trim_pct = ((por_trim[trim_max] - prom_t) / prom_t * 100) if prom_t > 0 else 0
        return pd.Series({
            't22_mes_nombre': MESES_CORTOS.get(mes_max, str(mes_max)),
            't22_mes_pct': round(mes_pct, 1),
            't22_trimestre_nombre': TRIMESTRES.get(trim_max, f'Q{trim_max}'),
            't22_trimestre_pct': round(trim_pct, 1)
        })

    def calc_correlacion_lp(group):
        EMPTY = pd.Series(
            {f't24_d{i+1}_{j+1}': '-' for i in range(4) for j in range(2)}
            | {f't24_v{i+1}': 0.0 for i in range(4)}
        )
        fam = group[(group['Nivel'] == 'Familia') & (group['delito'] != 'Total')]
        if fam.empty or fam['delito'].nunique() < 2:
            return EMPTY
        pivot = fam.pivot_table(index='id_periodo', columns='delito',
                                values='frecuencia', aggfunc='sum').fillna(0)
        pivot = pivot.loc[:, pivot.std() > 0]
        if pivot.shape[1] < 2 or len(pivot) < 6:
            return pd.Series({'t24_d1_1': 'Insuf. Datos'} | {f't24_v{i+1}': 0.0 for i in range(4)})
        corr = pivot.corr()
        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        pairs = corr.where(mask).stack().sort_values(ascending=False)
        res = {}
        for i in range(min(4, len(pairs))):
            (d1, d2), val = pairs.index[i], pairs.iloc[i]
            res[f't24_d{i+1}_1'] = d1[:35]
            res[f't24_d{i+1}_2'] = d2[:35]
            res[f't24_v{i+1}'] = round(val, 2)
        for i in range(len(pairs), 4):
            res[f't24_d{i+1}_1'] = '-'
            res[f't24_d{i+1}_2'] = '-'
            res[f't24_v{i+1}'] = 0.0
        return pd.Series(res)

    def calculate_top_correlation(group):
        if len(group) < 6:
            return pd.Series({'t23_d1': 'S.D.', 't23_d2': 'S.D.', 't23_val': 0.0})
        pivot = group.pivot_table(index='id_periodo', columns='delito', values='frecuencia', aggfunc='sum').fillna(0)
        pivot = pivot.loc[:, (pivot != pivot.iloc[0]).any()]
        if pivot.shape[1] < 2:
            return pd.Series({'t23_d1': 'S.Var', 't23_d2': 'S.Var', 't23_val': 0.0})
        corr = pivot.corr()
        corr_upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))
        try:
            mv = corr_upper.max().max()
            if pd.isna(mv):
                return pd.Series({'t23_d1': '-', 't23_d2': '-', 't23_val': 0.0})
            idx = corr_upper.stack().idxmax()
            return pd.Series({'t23_d1': idx[0], 't23_d2': idx[1], 't23_val': mv})
        except:
            return pd.Series({'t23_d1': 'Err', 't23_d2': 'Err', 't23_val': 0.0})

    # =================================================================
    # 3. CARGA DE DATOS
    # =================================================================
    url = r"C:\Users\limc_\Laboratorio\cead2\CEAD_FULL.csv"
    if not os.path.exists(url):
        url = r"CEAD_FULL.csv"
    if not os.path.exists(url):
        sys.exit(f"Data file not found: {url}")

    print(f"> Cargando: {url}")
    df_raw = pd.read_csv(url, compression="xz", sep="\t")
    #print(df_raw.columns)
    #df_raw = df_raw[df_raw["Codcom"] == 13101]
    df_raw = df_raw[df_raw["CODIGO"] > 10000].copy()
    df_raw['nivel_original'] = df_raw['Nivel']
    df_raw['is_forecast'] = False

    # =================================================================
    # 4. MELT → formato largo
    # =================================================================
    df = df_raw.melt(
        id_vars=['Codcom', 'Año', 'tipoValCod', 'tipoVal', 'CODIGO',
                 'Descripcion', 'Nivel', 'nivel_original', 'is_forecast'],
        value_vars=MESES, var_name='mes_nombre', value_name='frecuencia'
    )
    del df_raw; gc.collect()

    df['mes'] = df['mes_nombre'].map(MES_NUM).astype(np.int8)
    df['frecuencia'] = pd.to_numeric(df['frecuencia'], errors='coerce').fillna(0).astype(np.int32)
    df.rename(columns={'Codcom': 'codcom', 'Año': 'año', 'Descripcion': 'delito'}, inplace=True)
    df['id_periodo'] = (df['año'] * 100 + df['mes']).astype(np.int32)
    df['fecha'] = pd.to_datetime(df['año'].astype(str) + '-' + df['mes'].astype(str) + '-01')
    df['periodo_detalle'] = df['mes_nombre'].astype(str) + ' ' + df['año'].astype(str)

    df = optimize_dtypes(df)
    print(f"   > Filas post-melt: {len(df):,}")

    delitos_config = df[['delito', 'Nivel', 'nivel_original', 'CODIGO']].drop_duplicates('delito')

    # =================================================================
    # 5. PREDICCIÓN VECTORIZADA (Seasonal Naive + Drift)
    #    Genera predicciones como DataFrame directo, no lista de dicts
    # =================================================================
    print("> Generando predicciones...")
    limit_id = date_to_id(pd.to_datetime(LIMIT_DATE))
    df_train = df[df['id_periodo'] <= limit_id]
    tipoval_map = df_train[['tipoValCod', 'tipoVal']].drop_duplicates().set_index('tipoValCod')['tipoVal'].to_dict()
    df_nototal = df_train[df_train['delito'] != 'Total']

    pred_frames = []  # Acumular DataFrames, no dicts individuales

    for tipo_cod in df_nototal['tipoValCod'].unique():
        df_tipo = df_nototal[df_nototal['tipoValCod'] == tipo_cod]
        tipo_val_nombre = tipoval_map.get(tipo_cod, tipo_cod)

        pivot = df_tipo.pivot_table(
            index='fecha', columns=['codcom', 'delito'],
            values='frecuencia', aggfunc='sum'
        ).sort_index().asfreq('MS').fillna(0)

        n_periodos, n_series = pivot.shape
        if n_periodos == 0 or n_series == 0:
            continue
        print(f"  > tipoValCod={tipo_cod}: {n_periodos} periodos × {n_series:,} series")

        mat = pivot.values.astype(np.float32)  # float32 suficiente

        # Interpolación vectorizada (columnar)
        for c in range(n_series):
            col_vec = mat[:, c]
            nz = np.nonzero(col_vec)[0]
            if len(nz) >= 2:
                seg = col_vec[nz[0]:nz[-1]+1]
                zm = seg == 0
                if zm.any():
                    idx = np.arange(len(seg))
                    seg[zm] = np.interp(idx[zm], idx[~zm], seg[~zm])
                    mat[nz[0]:nz[-1]+1, c] = seg

        # Seasonal Naive + Drift — matricial
        if n_periodos >= 24:
            last12 = mat[-12:]
            prev12 = mat[-24:-12]
            drift = np.clip(last12 - prev12,
                            -np.where(last12 > 0, last12, 1) * 0.5,
                             np.where(last12 > 0, last12, 1) * 0.5)
        elif n_periodos >= 12:
            last12 = mat[-12:]
            drift = np.zeros_like(last12)
        else:
            last12 = None
            w = min(6, n_periodos)
            weights = np.arange(1, w + 1, dtype=np.float32)
            wma = np.maximum(0, np.round(np.average(mat[-w:], axis=0, weights=weights))).astype(np.int32)

        # Construir predicciones como arrays columna → DataFrame de golpe
        cols_multi = pivot.columns.tolist()
        codcoms = np.array([c[0] for c in cols_multi])
        delitos = np.array([c[1] for c in cols_multi])

        for date_f in FILL_PERIODS:
            m_idx = date_f.month - 1
            if last12 is not None:
                pred_vals = np.maximum(0, np.round(last12[m_idx] + drift[m_idx])).astype(np.int32)
            else:
                pred_vals = wma

            pred_df = pd.DataFrame({
                'codcom': codcoms,
                'delito': delitos,
                'tipoValCod': tipo_cod,
                'tipoVal': tipo_val_nombre,
                'año': date_f.year,
                'mes': date_f.month,
                'id_periodo': date_to_id(date_f),
                'fecha': date_f,
                'frecuencia': pred_vals,
                'is_forecast': True
            })
            pred_frames.append(pred_df)

        del mat, pivot
        gc.collect()

    df_preds = pd.concat(pred_frames, ignore_index=True)
    del pred_frames; gc.collect()

    df_preds = df_preds.merge(delitos_config, on='delito', how='left')
    df_preds['mes_nombre'] = df_preds['mes'].map(MESES_CORTOS)
    df_preds['periodo_detalle'] = df_preds['mes_nombre'].astype(str) + ' ' + df_preds['año'].astype(str)

    print(f"> Predicciones: {len(df_preds):,} filas")

    # =================================================================
    # 6. CONCAT train + predicciones (Desactivado para vista Histórica precisa)
    # =================================================================
    # df = pd.concat([df_train, df_preds], ignore_index=True)
    df = df_train.copy()
    del df_train, df_preds; gc.collect()

    df = df.sort_values(['codcom', 'tipoValCod', 'delito', 'id_periodo']).reset_index(drop=True)
    df = optimize_dtypes(df)

    # =================================================================
    # 7. TOTALES
    # =================================================================
    print("> Calculando totales...")
    df_notot = df[df['delito'] != 'Total']
    totales = df_notot.groupby(['codcom', 'id_periodo', 'tipoValCod', 'tipoVal'],
                                as_index=False, observed=True)['frecuencia'].sum()
    totales['delito'] = 'Total'
    totales['CODIGO'] = 0
    totales['Nivel'] = 'Total'
    totales['nivel_original'] = 'Total'
    time_meta = df[['id_periodo', 'año', 'mes', 'fecha', 'mes_nombre', 'periodo_detalle', 'is_forecast']].drop_duplicates('id_periodo')
    totales = totales.merge(time_meta, on='id_periodo', how='left')

    df = pd.concat([df_notot, totales], ignore_index=True)
    del totales, time_meta, df_notot; gc.collect()
    df = df.sort_values(['codcom', 'tipoValCod', 'delito', 'id_periodo']).reset_index(drop=True)
    df = optimize_dtypes(df)

    # =================================================================
    # 8. MÉTRICAS ROLLING/EXPANDING (una sola agrupación, múltiples columnas)
    # =================================================================
    print("> Calculando métricas temporales...")
    grp_key = ['delito', 'codcom', 'tipoValCod']
    df['media_movil_3m'] = df.groupby(grp_key)['frecuencia'].transform(lambda x: x.rolling(3, min_periods=1).mean())
    df['promedio_hist'] = df.groupby(grp_key)['frecuencia'].transform(lambda x: x.expanding().mean())
    df['std_hist'] = df.groupby(grp_key)['frecuencia'].transform(lambda x: x.expanding().std())
    gc.collect()

    df['z_score'] = np.where(
        df['std_hist'] > 0,
        ((df['frecuencia'] - df['promedio_hist']) / df['std_hist']).astype(np.float32),
        np.float32(0)
    )

    df['acumulado_anual'] = df.groupby(['delito', 'codcom', 'tipoValCod', 'año'], observed=True)['frecuencia'].cumsum()
    # Para años pasados o con los 12 meses ya proyectados/completos, el acumulado a mes 12 ya es el total.
    # Si estamos a mitad de año REAl sin el resto de meses, ahí sí se usa 12/mes.
    df['proyeccion_anual'] = np.where(
        df['año'] < pd.to_datetime('today').year,
        df['acumulado_anual'],
        (df['acumulado_anual'] * (np.float32(12.0) / df['mes'])).astype(np.float32)
    )

    # =================================================================
    # 9. LOCALIZACIÓN + POBLACIÓN (merges pequeños)
    # =================================================================
    print("> Fusionando localización y población...")
    localiza_paths = [
        r"D:\GitHub\ALGARROBO_BASE\frontend\division\seguridad\admin_general\data\Localiza Chile (1).xlsx",
        r"D:\GitHub\LOCALIZA_DB\Localiza Chile (1).xlsx"
    ]
    for lp in localiza_paths:
        if os.path.exists(lp):
            try:
                localiza = pd.read_excel(lp, usecols=['Provincia', 'Comuna', 'Región', 'Codcom', 'Codreg']).drop_duplicates()
                df = df.merge(localiza, left_on='codcom', right_on='Codcom', how='left')
                if 'Codcom' in df.columns:
                    df.drop(columns='Codcom', inplace=True)
                break
            except Exception as e:
                print(f"   ⚠️ Error localización ({lp}): {e}")

    pob_paths = [
        r"C:\Users\limc_\Downloads\Factores Población.xlsx",
        r"..\data\input\Factores Población.xlsx"
    ]
    pob_loaded = False
    for pp in pob_paths:
        if os.path.exists(pp):
            try:
                pob = pd.read_excel(pp, sheet_name="Factores",
                                    usecols=['Codcom', 'Año', 'Población', 'Factor Población'])
                pob.rename(columns={'Año': 'año', 'Factor Población': 'factor_poblacion'}, inplace=True)
                df = df.merge(pob, left_on=['codcom', 'año'], right_on=['Codcom', 'año'], how='left')
                if 'Codcom' in df.columns:
                    df.drop(columns='Codcom', inplace=True)
                pob_loaded = True
                break
            except Exception as e:
                print(f"   ⚠️ Error población ({pp}): {e}")
    if not pob_loaded:
        df['factor_poblacion'] = np.float32(100000)

    # =================================================================
    # 10. CLASE POBLACIONAL (vectorizado con pd.cut)
    # =================================================================
    print("> Clasificando población...")
    if 'Población' in df.columns:
        df.rename(columns={'Población': 'poblacion'}, inplace=True)
    if 'poblacion' not in df.columns:
        df['poblacion'] = df['factor_poblacion'] * 100000

    bins = [-np.inf, 1000, 5000, 20000, 50000, 100000, np.inf]
    labels = ['Menos de 1.000', 'Entre 1.000 y 5.000', 'Entre 5.000 y 20.000',
              'Entre 20.000 y 50.000', 'Entre 50.000 y 100.000', 'Más de 100.000']
    df['clase_poblacion'] = pd.cut(df['poblacion'], bins=bins, labels=labels, right=True).astype(str)
    df.loc[df['poblacion'].isna(), 'clase_poblacion'] = 'Sin Clasificar'

    gc.collect()

    # =================================================================
    # 11. RANKINGS (una sola pasada, sin duplicación)
    # =================================================================
    print("> Calculando rankings...")

    # Tasa CEAD (división directa por factor)
    fp = df['factor_poblacion'].replace(0, np.nan)
    df['tasa_cead'] = (df['frecuencia'] / fp).fillna(0).astype(np.float32)
    del fp

    if 'Codreg' in df.columns:
        # Regional por tasa
        df['ranking_comunal_regional'] = df.groupby(['id_periodo', 'delito', 'Codreg'])['tasa_cead'].rank(
            method='min', ascending=False).astype(np.int16)

        # Regional anual: Sumatoria total observada + proyectada (si el año no ha cerrado)
        # Evaluamos el volumen anual sobre la base completa, ya que los periodos forecast llenan el año real.
        ann_stats = df.groupby(['codcom', 'tipoValCod', 'delito', 'año'], observed=True)['frecuencia'].sum().reset_index()
        ann_stats.rename(columns={'frecuencia': 'total_año_real'}, inplace=True)
        
        df = df.merge(ann_stats, on=['codcom', 'tipoValCod', 'delito', 'año'], how='left')

        rk = df[['codcom', 'Codreg', 'tipoValCod', 'delito', 'año', 'total_año_real', 'factor_poblacion']].drop_duplicates()
        rk['tasa_anual_real'] = (rk['total_año_real'] / rk['factor_poblacion'].replace(0, np.nan)).astype(np.float32)
        rk['ranking_regional_anual_metric'] = rk.groupby(['Codreg', 'tipoValCod', 'delito', 'año'])['total_año_real'].rank(method='dense', ascending=False)
        rk['ranking_regional_anual_tasa'] = rk.groupby(['Codreg', 'tipoValCod', 'delito', 'año'])['tasa_anual_real'].rank(method='dense', ascending=False)
        df = df.merge(rk[['codcom', 'tipoValCod', 'delito', 'año', 'ranking_regional_anual_metric', 'ranking_regional_anual_tasa', 'tasa_anual_real']],
                      on=['codcom', 'tipoValCod', 'delito', 'año'], how='left')
        del ann_stats, rk; gc.collect()

        # Infografía V10 — calculada via transform (SIN merge extra)
        print("   > Infografía V10...")
        df['tasa_regional_promedio'] = df.groupby(['id_periodo', 'delito', 'Codreg'])['tasa_cead'].transform('mean')
        df['diff_tasa_regional_pct'] = np.where(
            df['tasa_regional_promedio'] > 0,
            ((df['tasa_cead'] - df['tasa_regional_promedio']) / df['tasa_regional_promedio'] * 100),
            np.float32(0)
        ).astype(np.float32)

        conditions = [
            df['diff_tasa_regional_pct'] > 5,
            df['diff_tasa_regional_pct'] > 3,
            df['diff_tasa_regional_pct'] < -5,
            df['diff_tasa_regional_pct'] < -3,
        ]
        df['infografia_v10'] = np.select(
            conditions,
            ['SOBRE_CRITICO', 'SOBRE_ALERTA', 'BAJO_DESTACADO', 'BAJO_BUENO'],
            default='PROMEDIO'
        )
    else:
        df['ranking_comunal_regional'] = np.int16(0)
        df['infografia_v10'] = 'N/A'

    # Nacional
    df['ranking_nacional_mensual'] = df.groupby(['delito', 'id_periodo'], observed=True)['tasa_cead'].rank(
        method='min', ascending=False).astype(np.int16)

    # =================================================================
    # 12. IDI CEAD (Basado en Union)
    # =================================================================
    print("> Calculando IDI CEAD...")
    try:
        weights_stop = {
            'HOMICIDIOS Y FEMICIDIOS': 1000,
            'ROBOS CON VIOLENCIA E INTIMIDACIÓN': 150,
            'VIOLACIONES Y DELITOS SEXUALES': 200,
            'LEY DE CONTROL DE ARMAS': 75,
            'LEY DE DROGAS': 30,
            'DELITOS EN CONTEXTO DE VIOLENCIA INTRAFAMILIAR': 40
        }
        union_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "config", "union.json")
        if os.path.exists(union_path):
            with open(union_path, 'r', encoding='utf-8') as f:
                union_data = json.load(f)

            map_w, map_n = {}, {}
            for item in union_data:
                su = item.get('Delitos_stop', '').strip()
                sn = item.get('Delitos min_stop', '').strip()
                w = weights_stop.get(su, 0)
                if w > 0:
                    map_w[item['id_subgrupo']] = w
                if sn and sn != 'NO STOP':
                    map_n[item['id_subgrupo']] = sn

            df['idi_peso'] = df['CODIGO'].map(map_w).fillna(0).astype(np.float32)
            df['stop_delito'] = df['CODIGO'].map(map_n).fillna("NO APLICA")
            df['idi_mensual'] = (df['frecuencia'] * df['idi_peso'] / df['factor_poblacion']).fillna(0).astype(np.float32)
            df['idi_acumulado_anual'] = df.groupby(['codcom', 'delito', 'año'], observed=True)['idi_mensual'].cumsum()
            print("   - IDI asignado via union.json")
        else:
            print(f"   ⚠️ union.json no encontrado: {union_path}")
            df['idi_peso'] = np.float32(0)
            df['idi_mensual'] = np.float32(0)
            df['stop_delito'] = "OTRO"
    except Exception as e:
        print(f"   ⚠️ Error IDI: {e}")
        df['idi_peso'] = np.float32(0)
        df['stop_delito'] = "OTRO"

    # =================================================================
    # 13. ESTACIONALIDAD + CORRELACIONES (apply sobre subsets reducidos)
    # =================================================================
    gc.collect()
    df = optimize_dtypes(df)

    # Renombrar df → df3 sin copia (reasignación de referencia)
    df3 = df
    del df  # Libera la referencia 'df', df3 apunta al mismo objeto

    print("> Calculando estacionalidad...")
    est = df3.groupby(['codcom', 'tipoValCod'], observed=True).apply(calc_estacionalidad).reset_index()
    df3 = df3.merge(est, on=['codcom', 'tipoValCod'], how='left')
    del est; gc.collect()

    print("> Calculando correlaciones (t23)...")
    df_c = df3[(df3['delito'] != 'Total') & (df3['Nivel'] != 'Familia')]
    t23 = df_c.groupby('codcom', observed=True).apply(calculate_top_correlation).reset_index()
    df3 = df3.merge(t23, on='codcom', how='left')
    del t23, df_c; gc.collect()

    print("> Calculando correlaciones LP (t24)...")
    t24 = df3.groupby(['codcom', 'tipoValCod'], observed=True).apply(calc_correlacion_lp).reset_index()
    df3 = df3.merge(t24, on=['codcom', 'tipoValCod'], how='left')
    del t24; gc.collect()

    # =================================================================
    # 14. GUARDADO (con groupby directo, sin filtrado repetido)
    # =================================================================
    out = r"D:\GitHub\ALGARROBO_BASE\frontend\division\seguridad\admin_general\data\cead_split"
    os.makedirs(out, exist_ok=True)

    print(f"> Guardando en: {out}")
    grouped = df3.groupby('codcom', observed=True)
    for codcom, sub_df in progress_wrapper(grouped, desc="Guardando", total=grouped.ngroups):
        fpath = os.path.join(out, str(codcom))
        sub_df.to_json(fpath, orient='records', compression='gzip', date_format='iso')

    # =================================================================
    # 15. CONFIGURACIÓN
    # =================================================================
    print("> Generando config/cead.json...")
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    os.makedirs(config_dir, exist_ok=True)

    config_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "source": "proceso_cead.py",
        "rows": len(df3),
        "columns": list(df3.columns),
        "column_types": {col: str(dtype) for col, dtype in df3.dtypes.items()},
        "date_range": {
            "start": df3['fecha'].min().isoformat() if not df3.empty else None,
            "end": df3['fecha'].max().isoformat() if not df3.empty else None
        },
        "limits": {"start_fill": START_FILL, "end_fill": END_FILL, "limit_date": LIMIT_DATE},
        "mapping_hint": {
            "CASOS_ACTUAL": "frecuencia", "CASOS_ANT": "casos_mes_anterior",
            "DELITO": "delito", "ID_PERIODO": "id_periodo"
        }
    }

    config_path = os.path.join(config_dir, "cead.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

    elapsed = (datetime.datetime.now() - t0).total_seconds()
    print(f"✅ Config → {config_path}")
    print(f">>> Completado. {len(df3):,} filas en {elapsed:.1f}s")
    return df3


# =================================================================
# ENTRY POINT
# =================================================================
df3 = None

if __name__ == "__main__":
    df3 = ejecutar_proceso()
else:
    print("Iniciando carga automática de proceso_cead...")
    try:
        df3 = ejecutar_proceso()
    except Exception as e:
        print(f"❌ Error CRÍTICO: {e}")
        raise e
    except SystemExit as e:
        print(f"❌ Proceso detenido: {e}")
