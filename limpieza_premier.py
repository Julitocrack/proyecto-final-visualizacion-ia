"""
Limpieza y transformación de datos · Premier League 2021-22 a 2024-25
Fuente: Football-Data.co.uk
Genera: data/premier_limpio.csv — un registro por cada escenario donde
        un equipo va perdiendo al descanso (perspectiva del equipo que pierde)
"""

import pandas as pd

# ─── 1. CARGAR Y CONCATENAR ───────────────────────────────────────────────────
ARCHIVOS = [
    'data/2021-2022.csv',
    'data/2022-2023.csv',
    'data/premierleague2023-2024.csv',
    'data/premierleague2024-2025.csv',
]

dfs = []
for f in ARCHIVOS:
    tmp = pd.read_csv(f, encoding='utf-8-sig')
    tmp['Temporada'] = f.split('/')[-1].replace('premierleague', '').replace('.csv', '')
    dfs.append(tmp)
    print(f"✅ {f}: {len(tmp) - 1} partidos")

df = pd.concat(dfs, ignore_index=True)
print(f"\nTotal antes de limpiar: {len(df)}")

# ─── 2. LIMPIEZA ──────────────────────────────────────────────────────────────
# Eliminar duplicados: mismo partido presente en más de un archivo
df = df.drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam']).reset_index(drop=True)
print(f"Tras deduplicar:       {len(df)}")

# Columnas necesarias para el análisis
COLS = ['Date', 'HomeTeam', 'AwayTeam', 'Temporada',
        'FTHG', 'FTAG', 'HTHG', 'HTAG',
        'HST', 'AST', 'HC', 'AC']

df = df[COLS].dropna().reset_index(drop=True)
for col in ['FTHG', 'FTAG', 'HTHG', 'HTAG', 'HST', 'AST', 'HC', 'AC']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna().reset_index(drop=True)
print(f"Tras limpiar nulos:    {len(df)}")

# ─── 3. FILTRO DE ESCENARIO ───────────────────────────────────────────────────
# Solo partidos con un equipo perdiendo al descanso (sin empate en el MT)
df = df[df['HTHG'] != df['HTAG']].reset_index(drop=True)
print(f"Con equipo perdiendo al MT: {len(df)}")

# ─── 4. COLUMNAS DESDE LA PERSPECTIVA DEL EQUIPO QUE VA PERDIENDO ────────────
local_pierde = df['HTHG'] < df['HTAG']

df['Equipo_Perdiendo']  = df.apply(lambda r: r['HomeTeam'] if r['HTHG'] < r['HTAG'] else r['AwayTeam'], axis=1)
df['Corners_Perd']      = df.apply(lambda r: r['HC']   if r['HTHG'] < r['HTAG'] else r['AC'],   axis=1)
df['Corners_Rival']     = df.apply(lambda r: r['AC']   if r['HTHG'] < r['HTAG'] else r['HC'],   axis=1)
df['Tiros_Perd']        = df.apply(lambda r: r['HST']  if r['HTHG'] < r['HTAG'] else r['AST'],  axis=1)
df['Tiros_Rival']       = df.apply(lambda r: r['AST']  if r['HTHG'] < r['HTAG'] else r['HST'],  axis=1)
df['Goles_Perd_Final']  = df.apply(lambda r: r['FTHG'] if r['HTHG'] < r['HTAG'] else r['FTAG'], axis=1)
df['Total_Corners']     = df['HC'] + df['AC']

def resultado_final(row):
    local_p = row['HTHG'] < row['HTAG']
    if local_p:
        if row['FTHG'] > row['FTAG']: return 'Remontada (G)'
        if row['FTHG'] == row['FTAG']: return 'Empate (E)'
        return 'Derrota (P)'
    else:
        if row['FTAG'] > row['FTHG']: return 'Remontada (G)'
        if row['FTAG'] == row['FTHG']: return 'Empate (E)'
        return 'Derrota (P)'

df['Resultado_Final'] = df.apply(resultado_final, axis=1)

# ─── 5. EXPORTAR ──────────────────────────────────────────────────────────────
OUTPUT = 'data/premier_limpio.csv'
df.to_csv(OUTPUT, index=False, encoding='utf-8-sig')

print(f"\n✅ Archivo generado: {OUTPUT}")
print(f"   {len(df)} escenarios · {df['Equipo_Perdiendo'].nunique()} equipos · {df['Temporada'].nunique()} temporadas")
print(f"\nColumnas exportadas:\n{list(df.columns)}")
print(f"\nResultados:\n{df['Resultado_Final'].value_counts()}")
