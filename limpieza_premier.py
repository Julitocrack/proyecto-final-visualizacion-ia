import pandas as pd

# 1. Lista exacta de tus archivos (sin usar glob)
# Escribimos los nombres exactamente como los tienes guardados
archivos_csv = [
    'premierleague2023-2024.csv',
    'premierleague2024-2025.csv'
]

# 2. Leer y concatenar las temporadas
lista_df = []
for archivo in archivos_csv:
    # Leemos cada archivo de tu lista
    df_temp = pd.read_csv(archivo, encoding='utf-8')
    lista_df.append(df_temp)

# Unimos ambos archivos en un solo dataset
df_premier = pd.concat(lista_df, ignore_index=True)

# 3. Seleccionar columnas clave
# HTHG/HTAG: Goles Medio Tiempo | HST/AST: Tiros a Puerta | HC/AC: Córners | B365: Momios
columnas_clave = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG', 
                  'HST', 'AST', 'HC', 'AC', 'B365H', 'B365D', 'B365A']

# Filtramos y quitamos posibles filas vacías
df_filtrado = df_premier[columnas_clave].dropna()

# 4. El "Filtro Táctico": Identificar al Favorito perdiendo al Medio Tiempo
# CASO A: Local es amplio favorito (momio < 1.80) y va perdiendo al medio tiempo
filtro_local_sufriendo = (df_filtrado['B365H'] < 1.80) & (df_filtrado['HTHG'] < df_filtrado['HTAG'])

# CASO B: Visitante es amplio favorito (momio < 1.80) y va perdiendo al medio tiempo
filtro_visita_sufriendo = (df_filtrado['B365A'] < 1.80) & (df_filtrado['HTAG'] < df_filtrado['HTHG'])

# Unimos ambos escenarios tácticos
df_favoritos_perdiendo_mt = df_filtrado[filtro_local_sufriendo | filtro_visita_sufriendo]

# 5. Exportar el dataset que consumirá tu aplicación Dash
df_favoritos_perdiendo_mt.to_csv('premier_dash_limpio.csv', index=False)

print(f"Limpieza exitosa. Se encontraron {len(df_favoritos_perdiendo_mt)} partidos con este escenario táctico.")
print(df_favoritos_perdiendo_mt.head())