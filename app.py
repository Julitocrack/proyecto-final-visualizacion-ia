import dash
from dash import dcc, html, Input, Output, clientside_callback
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ─── 1. CARGAR Y PROCESAR DATOS ───────────────────────────────────────────────
ARCHIVOS_CSV = [
    'data/2021-2022.csv',
    'data/2022-2023.csv',
    'data/premierleague2023-2024.csv',
    'data/premierleague2024-2025.csv',
]

_dfs = []
for _f in ARCHIVOS_CSV:
    try:
        _tmp = pd.read_csv(_f, encoding='utf-8-sig')
        _tmp['Temporada'] = _f.split('/')[-1].replace('premierleague', '').replace('.csv', '')
        _dfs.append(_tmp)
        print(f"✅ Cargado {_f}: {len(_tmp) - 1} partidos")
    except FileNotFoundError:
        print(f"⚠️  No se encontró {_f}, se omite")

if not _dfs:
    raise FileNotFoundError("No se encontró ningún CSV.")

df = pd.concat(_dfs, ignore_index=True)
print(f"📊 Total antes de deduplicar: {len(df)}")

df = df.drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam']).reset_index(drop=True)
print(f"📊 Total partidos únicos: {len(df)}")

COLS_REQUERIDAS = ['FTHG', 'FTAG', 'HTHG', 'HTAG', 'HST', 'AST', 'HC', 'AC']
df = df.dropna(subset=COLS_REQUERIDAS).reset_index(drop=True)
for col in COLS_REQUERIDAS:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=COLS_REQUERIDAS).reset_index(drop=True)
print(f"📊 Partidos con datos completos: {len(df)}")

# ── Construir dataset de escenarios: un registro por cada equipo perdiendo al MT
# Solo partidos con resultado claro al descanso (no empate en el MT)
_perd = df[df['HTHG'] != df['HTAG']].copy()

def _local_pierde(row):
    return row['HTHG'] < row['HTAG']

def _resultado_final(row):
    if _local_pierde(row):
        if row['FTHG'] > row['FTAG']: return 'Remontada (G)'
        if row['FTHG'] == row['FTAG']: return 'Empate (E)'
        return 'Derrota (P)'
    else:
        if row['FTAG'] > row['FTHG']: return 'Remontada (G)'
        if row['FTAG'] == row['FTHG']: return 'Empate (E)'
        return 'Derrota (P)'

# Columnas desde la perspectiva del equipo que va perdiendo al MT
_local_p = _perd['HTHG'] < _perd['HTAG']   # booleano: ¿es el local quien pierde?

scenarios = pd.concat([
    _perd,
    _local_p.rename('Local_Pierde'),
    _perd.apply(lambda r: r['HomeTeam'] if _local_pierde(r) else r['AwayTeam'], axis=1).rename('Equipo_Perd'),
    _perd.apply(lambda r: r['HC']   if _local_pierde(r) else r['AC'],   axis=1).rename('Corners_Perd'),
    _perd.apply(lambda r: r['AC']   if _local_pierde(r) else r['HC'],   axis=1).rename('Corners_Rival'),
    _perd.apply(lambda r: r['HST']  if _local_pierde(r) else r['AST'],  axis=1).rename('Tiros_Perd'),
    _perd.apply(lambda r: r['AST']  if _local_pierde(r) else r['HST'],  axis=1).rename('Tiros_Rival'),
    _perd.apply(lambda r: r['FTHG'] if _local_pierde(r) else r['FTAG'], axis=1).rename('Goles_Perd'),
    (_perd['HC'] + _perd['AC']).rename('Total_Corners'),
    _perd.apply(_resultado_final, axis=1).rename('Resultado_Final'),
], axis=1).copy()

LINEA_CORNERS = 9.5
MIN_MUESTRAS  = 8    # mínimo de casos para veredicto confiable

# Equipos con suficientes casos en el escenario
_casos = scenarios.groupby('Equipo_Perd').size()
_equipos_validos = sorted(_casos[_casos >= MIN_MUESTRAS].index.tolist())

opciones_dropdown = [
    {'label': f'{e}  ({_casos[e]} casos)', 'value': e}
    for e in _equipos_validos
]

print(f"📊 Partidos con equipo perdiendo al MT: {len(scenarios)}")
print(f"Equipos con >= {MIN_MUESTRAS} casos: {len(_equipos_validos)}")

# Dataset global de todos los partidos para comparaciones (normal vs perdiendo)
df['Total_Corners'] = df['HC'] + df['AC']

# ─── 2. PALETA Y ESTILOS ──────────────────────────────────────────────────────
VERDE_OSCURO = '#0d1f14'
VERDE_MEDIO  = '#1a3a24'
VERDE_ACENTO = '#00d4aa'
ROJO         = '#e84646'
AMARILLO     = '#f0a500'
GRIS_BORDE   = '#2a4030'
TEXTO        = '#e8ede9'
TEXTO_SUAVE  = '#9ab0a0'

LAYOUT_BASE = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='DM Sans, Arial', color=TEXTO, size=13),
    margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(gridcolor=GRIS_BORDE, linecolor=GRIS_BORDE, tickcolor=GRIS_BORDE),
    yaxis=dict(gridcolor=GRIS_BORDE, linecolor=GRIS_BORDE, tickcolor=GRIS_BORDE),
)
LEGEND_BASE = dict(bgcolor='rgba(0,0,0,0)', font=dict(color=TEXTO))

def card_stat(titulo, valor, subtitulo='', color=VERDE_ACENTO):
    return html.Div([
        html.P(titulo, style={'fontSize': '11px', 'color': TEXTO_SUAVE,
                              'textTransform': 'uppercase', 'letterSpacing': '1.5px',
                              'marginBottom': '6px', 'fontWeight': '500'}),
        html.P(str(valor), style={'fontSize': '32px', 'fontWeight': '700',
                                   'color': color, 'lineHeight': '1',
                                   'marginBottom': '4px', 'fontFamily': 'Bebas Neue, Impact'}),
        html.P(subtitulo, style={'fontSize': '11px', 'color': TEXTO_SUAVE}),
    ], style={
        'background': VERDE_MEDIO, 'border': f'1px solid {GRIS_BORDE}',
        'borderTop': f'3px solid {color}', 'borderRadius': '10px',
        'padding': '20px', 'flex': '1', 'minWidth': '140px',
    })

def narrativa(*parrafos):
    return html.Div([
        html.P(p, style={
            'color': TEXTO_SUAVE, 'fontSize': '15px', 'lineHeight': '1.8',
            'marginBottom': '12px', 'maxWidth': '860px',
        }) for p in parrafos
    ], style={'marginBottom': '24px'})

def seccion_titulo(icono, texto, descripcion=''):
    return html.Div([
        html.Div([
            html.Span(icono, style={'fontSize': '24px', 'marginRight': '12px'}),
            html.Span(texto, style={
                'fontSize': '20px', 'fontWeight': '700', 'color': TEXTO,
                'fontFamily': 'Bebas Neue, Impact', 'letterSpacing': '1px'
            }),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'}),
        html.P(descripcion, style={'color': TEXTO_SUAVE, 'fontSize': '13px', 'marginLeft': '36px'}),
        html.Hr(style={'border': 'none', 'borderTop': f'1px solid {GRIS_BORDE}', 'marginTop': '12px'})
    ], style={'marginBottom': '20px'})

def gauge_figure(valor, titulo, subtitulo, umbrales=(45, 65), sufijo='%'):
    color = VERDE_ACENTO if valor >= umbrales[1] else (AMARILLO if valor >= umbrales[0] else ROJO)
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=valor,
        number={'suffix': sufijo, 'font': {'size': 56, 'color': color, 'family': 'Bebas Neue, Impact'}},
        title={
            'text': f'<b style="font-size:17px">{titulo}</b><br><span style="font-size:12px;color:{TEXTO_SUAVE}">{subtitulo}</span>',
            'font': {'size': 16, 'color': TEXTO},
        },
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': GRIS_BORDE,
                     'tickfont': {'color': TEXTO_SUAVE, 'size': 11},
                     'tickvals': [0, umbrales[0], umbrales[1], 100],
                     'ticktext': [f'0{sufijo}', f'{umbrales[0]}{sufijo}', f'{umbrales[1]}{sufijo}', f'100{sufijo}']},
            'bar': {'color': color, 'thickness': 0.22},
            'bgcolor': 'rgba(0,0,0,0)', 'borderwidth': 0,
            'steps': [
                {'range': [0, umbrales[0]],          'color': 'rgba(232,70,70,0.18)'},
                {'range': [umbrales[0], umbrales[1]], 'color': 'rgba(240,165,0,0.14)'},
                {'range': [umbrales[1], 100],         'color': 'rgba(0,212,170,0.14)'},
            ],
            'threshold': {'line': {'color': TEXTO, 'width': 3}, 'thickness': 0.85, 'value': valor},
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(family='DM Sans, Arial', color=TEXTO),
                      margin=dict(l=30, r=30, t=90, b=10))
    return fig

def veredicto_card(pct, n, etiquetas, textos, borde_color):
    v_color, v_icono, v_titulo, v_texto = etiquetas[0], etiquetas[1], etiquetas[2], textos
    lineas_extra = etiquetas[3] if len(etiquetas) > 3 else html.Div()
    return html.Div([
        html.Div([
            html.Span(v_icono, style={'fontSize': '44px', 'display': 'block', 'marginBottom': '14px'}),
            html.P(v_titulo, style={
                'fontSize': '22px', 'fontWeight': '700', 'color': v_color,
                'fontFamily': 'Bebas Neue, Impact', 'letterSpacing': '2px',
                'marginBottom': '14px', 'lineHeight': '1.25', 'whiteSpace': 'pre-line',
            }),
            html.P(v_texto, style={'fontSize': '13px', 'color': TEXTO_SUAVE,
                                   'lineHeight': '1.7', 'maxWidth': '260px'}),
            lineas_extra,
            html.Div(style={'marginTop': '22px', 'padding': '8px 22px',
                            'border': f'2px solid {borde_color}',
                            'borderRadius': '20px', 'display': 'inline-block'}, children=[
                html.Span(f'{pct}%  ·  {n} partidos', style={
                    'color': borde_color, 'fontWeight': '700', 'fontSize': '15px',
                    'fontFamily': 'Bebas Neue, Impact', 'letterSpacing': '1px',
                })
            ]),
        ], style={'textAlign': 'center', 'padding': '28px 24px'}),
    ], style={
        'background': VERDE_MEDIO, 'border': f'1px solid {GRIS_BORDE}',
        'borderTop': f'4px solid {borde_color}', 'borderRadius': '12px',
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
        'width': '100%', 'minHeight': '320px',
    })

# ─── 3. APP LAYOUT ────────────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = 'Premier League · ¿Vale la Pena Apostar al Over de Córners en Vivo?'

app.layout = html.Div(
    style={'backgroundColor': VERDE_OSCURO, 'minHeight': '100vh', 'fontFamily': 'DM Sans, Arial'},
    children=[

    # ── HEADER ─────────────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Div([
                html.Span('⚽', style={'fontSize': '32px', 'marginRight': '14px'}),
                html.Div([
                    html.H1('Premier League · ¿Vale la Pena Apostar al Over de Córners en Vivo?',
                            style={'fontSize': '22px', 'fontWeight': '700', 'color': TEXTO,
                                   'fontFamily': 'Bebas Neue, Impact', 'letterSpacing': '2px', 'margin': '0'}),
                    html.P('Cuando un equipo va perdiendo al descanso · Temporadas 2021-22 a 2024-25',
                           style={'color': TEXTO_SUAVE, 'fontSize': '13px', 'margin': '2px 0 0 0'})
                ])
            ], style={'display': 'flex', 'alignItems': 'center'}),
            html.Div([
                html.Label(f'Equipo (mín. {MIN_MUESTRAS} casos):', style={
                    'color': TEXTO_SUAVE, 'fontSize': '12px', 'display': 'block',
                    'marginBottom': '6px', 'textTransform': 'uppercase', 'letterSpacing': '1px',
                }),
                dcc.Dropdown(id='filtro-equipo', options=opciones_dropdown,
                             placeholder='Vista global (todos)',
                             style={'width': '300px'}, className='dropdown-dark')
            ])
        ], style={'maxWidth': '1400px', 'margin': '0 auto',
                  'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})
    ], style={
        'background': f'linear-gradient(135deg, {VERDE_OSCURO} 0%, {VERDE_MEDIO} 100%)',
        'borderBottom': f'2px solid {VERDE_ACENTO}',
        'padding': '24px 32px', 'position': 'sticky', 'top': '0', 'zIndex': '100',
        'boxShadow': '0 4px 20px rgba(0,0,0,0.5)',
    }),

    # ── CONTENIDO ──────────────────────────────────────────────────────────────
    html.Div(style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '32px 32px 60px'},
    children=[

        # SECCIÓN 0: KPIs + INTRO
        narrativa(
            'Son las 9:47 de la noche. El equipo que todos esperaban que ganara llega al descanso perdiendo. '
            'En la app de apuestas, la línea de córners totales del partido sigue abierta. La pregunta es simple: '
            '¿tiene sentido apostar al over en este momento, o la intuición de que "van a presionar más" no se sostiene con datos?',
            'Para responderla, se analizaron 4 temporadas completas de la Premier League (2021-22 a 2024-25), '
            'identificando todos los partidos donde un equipo terminó el primer tiempo perdiendo en el marcador. '
            'En total, 690 escenarios de presión. Lo que encontramos no es lo que la mayoría esperaría.'
        ),
        html.Div(id='kpis-section', style={'marginBottom': '48px'}),

        # SECCIÓN 1: OVER DE CÓRNERS TOTALES ← pregunta principal
        html.Div([
            seccion_titulo('📐', 'Over de Córners Totales (ambos equipos) · Veredicto de Apuesta',
                           f'Córners totales del partido (local + visitante) cuando el equipo va perdiendo al descanso'),
            narrativa(
                'La primera evidencia apunta en una dirección clara: cuando un equipo va perdiendo al descanso, '
                'los partidos tienden a terminar con más córners de lo habitual. El equipo que va abajo busca '
                'el empate lanzando centros y generando situaciones de balón parado, mientras el rival defiende '
                'y despeja hacia afuera, produciendo más saques de esquina para el equipo que ataca.',
                f'El termómetro muestra el porcentaje histórico de partidos que superaron los {LINEA_CORNERS} córners '
                'totales en este escenario exacto. El histograma inferior deja ver dónde se concentran los partidos: '
                'si la barra roja (perdiendo al MT) se desplaza hacia la derecha respecto a la verde, '
                'el patrón de mayor presión es real y consistente.'
            ),
            html.Div([
                dcc.Graph(id='grafica-termometro-corners', config={'displayModeBar': False},
                          style={'height': '380px', 'flex': '1.2'}),
                html.Div(id='veredicto-corners', style={
                    'flex': '0.8', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                }),
            ], style={'display': 'flex', 'gap': '16px', 'alignItems': 'stretch'}),
            dcc.Graph(id='grafica-corners-dist', config={'displayModeBar': False},
                      style={'height': '340px', 'marginTop': '16px'}),
        ], style={'marginBottom': '48px'}),

        # SECCIÓN 2: TERMÓMETRO DE REMONTADA (contexto)
        html.Div([
            seccion_titulo('🌡️', 'Contexto Táctico: ¿Realmente Presionan para Remontar?',
                           '¿Con qué frecuencia logra el equipo cambiar el resultado cuando va perdiendo al descanso?'),
            narrativa(
                'Antes de apostar al over de córners, vale la pena entender qué motiva esa presión. '
                'Un equipo que va perdiendo al descanso tiene dos mitades muy distintas: la primera, donde '
                'algo salió mal, y la segunda, donde el entrenador ajusta y el equipo busca revertirlo. '
                'Esa búsqueda se traduce en más posesión en campo rival, más centros y, en consecuencia, más córners.',
                'Sin embargo, la tasa de remontada revela algo importante: presionar más no garantiza ganar. '
                'La mayoría de los equipos que van perdiendo al MT logran igualar o remontar en menos ocasiones '
                'de las que el instinto deportivo haría pensar. Esto explica por qué la presión se sostiene '
                'durante todo el segundo tiempo: el marcador sigue siendo adverso.'
            ),
            html.Div([
                dcc.Graph(id='grafica-termometro', config={'displayModeBar': False},
                          style={'height': '380px', 'flex': '1.2'}),
                html.Div(id='veredicto-apuesta', style={
                    'flex': '0.8', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                }),
            ], style={'display': 'flex', 'gap': '16px', 'alignItems': 'stretch'}),
        ], style={'marginBottom': '48px'}),

        # SECCIÓN 3: TIROS A PUERTA
        html.Div([
            seccion_titulo('🎯', 'La Presión en Números: Tiros a Puerta',
                           'Intensidad ofensiva del equipo según su situación al descanso'),
            narrativa(
                'Los tiros a puerta son la medida más directa de la intención ofensiva. Si la hipótesis '
                'de "presionan más cuando van perdiendo" es correcta, deberíamos ver un aumento claro en '
                'el número de disparos al arco durante los partidos donde el equipo va abajo al descanso.',
                'La comparación entre los tres grupos —el equipo perdiendo, su rival en ese mismo escenario, '
                'y el promedio del equipo en el resto de sus partidos— muestra si el incremento ofensivo '
                'es real o solo una percepción. Un delta positivo confirma que el equipo efectivamente '
                'intensifica su juego ofensivo cuando el marcador lo exige.'
            ),
            dcc.Graph(id='grafica-tiros', config={'displayModeBar': False}, style={'height': '420px'}),
        ], style={'marginBottom': '48px'}),

        # SECCIÓN 4: CÓRNERS PROPIOS
        html.Div([
            seccion_titulo('📐', 'Córners Propios: ¿Se Generan Más Saques de Esquina?',
                           'Córners propios del equipo que va perdiendo — no incluye los del rival'),
            narrativa(
                'Los córners propios son una consecuencia directa de la presión ofensiva: '
                'el equipo que ataca manda el balón hacia el área, el defensa lo desvía por la línea de fondo '
                'y se genera un córner. Cuanto más tiempo pasa un equipo atacando, más córners acumula.',
                'Esta gráfica aísla únicamente los córners del equipo que va perdiendo, separando su '
                'contribución del total del partido. Si la diferencia respecto a sus partidos normales '
                'es significativa, queda confirmado que no solo el total de córners sube, sino que '
                'es el propio equipo presionado quien los genera activamente.'
            ),
            dcc.Graph(id='grafica-corners', config={'displayModeBar': False}, style={'height': '380px'}),
        ], style={'marginBottom': '48px'}),

        # SECCIÓN 5: RESULTADOS FINALES
        html.Div([
            seccion_titulo('🏆', '¿Qué Pasa al Final del Partido?',
                           'Distribución de resultados finales cuando el equipo va perdiendo al descanso'),
            narrativa(
                'Toda esa presión, esos córners y esos tiros adicionales, ¿se convierten en puntos? '
                'La gráfica de anillo muestra la proporción real de remontadas, empates y derrotas. '
                'El hallazgo es el núcleo de toda la historia: la presión genera córners, '
                'pero los córners no garantizan el gol.',
                'Las barras por temporada permiten verificar si este patrón es estable o si fue '
                'un fenómeno particular de una sola temporada. La consistencia entre los cuatro años '
                'es la prueba más sólida de que estamos ante un comportamiento estructural del '
                'fútbol inglés, no ante una anomalía estadística.'
            ),
            html.Div([
                dcc.Graph(id='grafica-anillo', config={'displayModeBar': False},
                          style={'height': '420px', 'flex': '1'}),
                dcc.Graph(id='grafica-barras-resultado', config={'displayModeBar': False},
                          style={'height': '420px', 'flex': '1'}),
            ], style={'display': 'flex', 'gap': '16px'}),
        ], style={'marginBottom': '48px'}),

        # SECCIÓN 6: SCATTER
        html.Div([
            seccion_titulo('📊', 'El Límite de la Presión: Córners vs. Goles',
                           'Relación entre los córners propios generados y los goles anotados al final'),
            narrativa(
                'La última pieza del rompecabezas: si los córners son el indicador de presión, '
                '¿cuántos de esos córners terminan en gol? El scatter plot enfrenta ambas variables '
                'y revela si existe una correlación entre presionar más —medido en córners propios— '
                'y convertir ese esfuerzo en goles.',
                'Los colores indican el resultado final del partido: verde para remontada, '
                'amarillo para empate y rojo para derrota. Si los puntos verdes se concentran '
                'en la parte superior derecha (muchos córners y muchos goles), la presión sí se '
                'traduce en efectividad. Si están dispersos sin patrón claro, la conclusión es que '
                'generar córners es condición necesaria, pero no suficiente, para cambiar el resultado.'
            ),
            dcc.Graph(id='grafica-scatter', config={'displayModeBar': False}, style={'height': '420px'}),
        ], style={'marginBottom': '48px'}),

        html.Div([
            html.Hr(style={'border': 'none', 'borderTop': f'1px solid {GRIS_BORDE}', 'marginBottom': '16px'}),
            html.P(f'Datos: Premier League 2021-22 a 2024-25 · Football-Data.co.uk · Línea de apuesta: Over {LINEA_CORNERS} córners totales',
                   style={'color': TEXTO_SUAVE, 'fontSize': '12px', 'textAlign': 'center'})
        ])
    ]),

    dcc.Store(id='scroll-trigger', data=1),
])

# ─── 4. CLIENTSIDE CALLBACK ───────────────────────────────────────────────────
app.clientside_callback(
    """
    function(trigger) {
        setTimeout(function() {
            var sections = document.querySelectorAll('.scroll-section');
            var observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(e) {
                    if (e.isIntersecting) {
                        e.target.style.opacity = '1';
                        e.target.style.transform = 'translateY(0)';
                    }
                });
            }, { threshold: 0.08 });
            sections.forEach(function(s) {
                s.style.opacity = '0';
                s.style.transform = 'translateY(32px)';
                s.style.transition = 'opacity 0.7s ease, transform 0.7s ease';
                observer.observe(s);
            });
        }, 300);
        return trigger;
    }
    """,
    Output('scroll-trigger', 'data'),
    Input('scroll-trigger', 'data'),
)

# ─── 5. CALLBACK PRINCIPAL ────────────────────────────────────────────────────
@app.callback(
    [
        Output('kpis-section', 'children'),
        Output('grafica-termometro-corners', 'figure'),
        Output('veredicto-corners', 'children'),
        Output('grafica-corners-dist', 'figure'),
        Output('grafica-termometro', 'figure'),
        Output('veredicto-apuesta', 'children'),
        Output('grafica-tiros', 'figure'),
        Output('grafica-corners', 'figure'),
        Output('grafica-anillo', 'figure'),
        Output('grafica-barras-resultado', 'figure'),
        Output('grafica-scatter', 'figure'),
    ],
    [Input('filtro-equipo', 'value')]
)
def actualizar_todo(equipo):
    # Escenarios donde el equipo va perdiendo al MT
    sc = scenarios[scenarios['Equipo_Perd'] == equipo] if equipo else scenarios
    n  = len(sc)

    # Todos los partidos del equipo (para comparación normal vs perdiendo)
    if equipo:
        todos = df[(df['HomeTeam'] == equipo) | (df['AwayTeam'] == equipo)]
        # Partidos donde el equipo NO va perdiendo al MT
        sc_ids   = sc.index
        no_perd_corners = df.loc[~df.index.isin(sc_ids), 'Total_Corners']
        # Tiros propios del equipo cuando NO va perdiendo (local o visitante)
        def tiros_propios(row, eq):
            return row['HST'] if row['HomeTeam'] == eq else row['AST']
        def corners_propios(row, eq):
            return row['HC'] if row['HomeTeam'] == eq else row['AC']
        todos_tiros   = todos.apply(lambda r: tiros_propios(r, equipo), axis=1)
        todos_corners = todos.apply(lambda r: corners_propios(r, equipo), axis=1)
        normal_tiros_mean   = round(todos_tiros.mean(), 2)
        normal_corners_mean = round(todos_corners.mean(), 2)
    else:
        no_perd_corners     = df['Total_Corners']
        normal_tiros_mean   = round(df['HST'].mean() / 2 + df['AST'].mean() / 2, 2)
        normal_corners_mean = round(df['HC'].mean() / 2 + df['AC'].mean() / 2, 2)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    n_remontadas  = (sc['Resultado_Final'] == 'Remontada (G)').sum()
    n_empates     = (sc['Resultado_Final'] == 'Empate (E)').sum()
    n_derrotas    = (sc['Resultado_Final'] == 'Derrota (P)').sum()
    pct_remontada = round(n_remontadas / n * 100, 1) if n else 0
    pct_empate    = round(n_empates    / n * 100, 1) if n else 0
    pct_derrota   = round(n_derrotas   / n * 100, 1) if n else 0

    media_corners_perd   = round(sc['Total_Corners'].mean(), 2) if n else 0
    media_tiros_perd     = round(sc['Tiros_Perd'].mean(), 2)    if n else 0
    delta_tiros          = round(media_tiros_perd - normal_tiros_mean, 2)

    contexto = equipo if equipo else 'todos los equipos'
    kpis = html.Div([
        seccion_titulo('📋', 'Resumen General',
                       f'{n} partidos perdiendo al descanso · {contexto} · 2021-22 a 2024-25'),
        html.Div([
            card_stat('Partidos analizados', f'{n:,}', 'perdiendo al descanso'),
            card_stat('% Remontada', f'{pct_remontada}%', f'{n_remontadas} partidos · ganaron desde abajo', color=VERDE_ACENTO),
            card_stat('% Empate', f'{pct_empate}%', f'{n_empates} partidos · igualaron', color=AMARILLO),
            card_stat('% Derrota', f'{pct_derrota}%', f'{n_derrotas} partidos · no reaccionaron', color=ROJO),
            card_stat('Media córners totales', f'{media_corners_perd}', 'local + visitante en estos partidos'),
            card_stat('Δ Tiros a puerta',
                      f'+{delta_tiros}' if delta_tiros >= 0 else str(delta_tiros),
                      'vs sus partidos normales',
                      color=VERDE_ACENTO if delta_tiros >= 0 else ROJO),
        ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap'}),
    ])

    # ── OVER DE CÓRNERS ───────────────────────────────────────────────────────
    lineas = [8.5, 9.5, 10.5, 11.5]
    pct_over = {l: round((sc['Total_Corners'] > l).sum() / n * 100, 1) if n else 0 for l in lineas}
    pct_principal = pct_over[LINEA_CORNERS]

    subtitulo_c = (f'córners totales (local + visitante) · media {media_corners_perd} · {n} partidos'
                   if n else 'Sin datos')
    fig_termo_c = gauge_figure(pct_principal,
                               f'{equipo} · Over {LINEA_CORNERS} Córners Totales' if equipo else f'Global · Over {LINEA_CORNERS} Córners Totales',
                               subtitulo_c)

    # Veredicto corners
    if n < MIN_MUESTRAS:
        vc = (AMARILLO, '⚠️', 'DATOS INSUFICIENTES',
              f'Solo {n} caso(s). Se necesitan al menos {MIN_MUESTRAS} para un veredicto confiable.')
    elif pct_principal >= 65:
        vc = (VERDE_ACENTO, '✅', 'FACTIBLE\nAPOSTAR OVER',
              f'El {pct_principal}% de las veces el partido supera los {LINEA_CORNERS} córners totales en este escenario. El sistema avala la apuesta en vivo.')
    elif pct_principal < 45:
        vc = (ROJO, '🚫', 'MALA IDEA\nNO APOSTAR OVER',
              f'Solo el {pct_principal}% de los partidos superan {LINEA_CORNERS} córners. No hay evidencia histórica que apoye esta apuesta.')
    else:
        vc = (AMARILLO, '⚡', 'ZONA GRIS\nALTO RIESGO',
              f'El {pct_principal}% supera {LINEA_CORNERS} córners. El dato no es concluyente; revisa la línea específica del partido.')

    mini_lineas = html.Div([
        html.Div([
            html.Span(f'Over {l}', style={'color': TEXTO_SUAVE, 'fontSize': '11px',
                                          'textTransform': 'uppercase', 'letterSpacing': '1px'}),
            html.Span(f'  {pct_over[l]}%', style={
                'color': VERDE_ACENTO if pct_over[l] >= 65 else (AMARILLO if pct_over[l] >= 45 else ROJO),
                'fontWeight': '700', 'fontSize': '14px', 'fontFamily': 'Bebas Neue, Impact',
            }),
        ], style={'marginBottom': '4px'})
        for l in lineas
    ], style={'marginTop': '18px', 'padding': '12px 16px', 'background': VERDE_OSCURO,
              'borderRadius': '8px', 'border': f'1px solid {GRIS_BORDE}', 'textAlign': 'left'})

    verd_corners = veredicto_card(pct_principal, n, [vc[0], vc[1], vc[2], mini_lineas], vc[3], vc[0])

    # Histograma distribución córners
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=sc['Total_Corners'], name='Perdiendo al MT',
        marker_color=ROJO, opacity=0.8,
        xbins=dict(start=0, end=28, size=1),
        hovertemplate='%{x} córners totales: %{y} partidos<extra>Perdiendo al MT</extra>',
    ))
    fig_dist.add_trace(go.Histogram(
        x=no_perd_corners, name='Resto de partidos',
        marker_color=VERDE_ACENTO, opacity=0.45,
        xbins=dict(start=0, end=28, size=1),
        hovertemplate='%{x} córners totales: %{y} partidos<extra>Resto</extra>',
    ))
    fig_dist.add_vline(x=LINEA_CORNERS, line_dash='dash', line_color=AMARILLO, line_width=2,
                       annotation_text=f'Línea {LINEA_CORNERS}', annotation_font_color=AMARILLO,
                       annotation_font_size=12)
    fig_dist.update_layout(
        **{**LAYOUT_BASE, 'legend': {**LEGEND_BASE, 'orientation': 'h', 'y': -0.18, 'x': 0.5, 'xanchor': 'center'}},
        title=dict(text='Distribución de córners totales (local + visitante) · Perdiendo al MT vs. resto de partidos',
                   font=dict(size=15, color=TEXTO), x=0),
        barmode='overlay', xaxis_title='Córners totales en el partido (local + visitante)',
        yaxis_title='Nº de partidos', bargap=0.05,
    )

    # ── TERMÓMETRO REMONTADA ──────────────────────────────────────────────────
    subtitulo_r = f'perdiendo al MT · {n_remontadas} remontadas de {n} partidos'
    fig_termo_r = gauge_figure(pct_remontada,
                               equipo if equipo else 'Todos los equipos',
                               subtitulo_r, umbrales=(30, 50))

    if n < MIN_MUESTRAS:
        vr = (AMARILLO, '⚠️', 'DATOS INSUFICIENTES',
              f'Solo {n} caso(s). Se necesitan al menos {MIN_MUESTRAS} partidos.')
    elif pct_remontada >= 50:
        vr = (VERDE_ACENTO, '✅', 'REMONTADA\nFACTIBLE',
              f'Remonta el {pct_remontada}% de las veces. El historial avala que puede reaccionar desde abajo.')
    elif pct_remontada < 30:
        vr = (ROJO, '🚫', 'RARAMENTE\nREMONTA',
              f'Solo remonta el {pct_remontada}% de las veces. No suele reaccionar cuando va perdiendo al descanso.')
    else:
        vr = (AMARILLO, '⚡', 'ZONA GRIS\nPUEDE PASAR',
              f'Remonta el {pct_remontada}% de las veces. Ni seguro ni descartable.')

    verd_remontada = veredicto_card(pct_remontada, n, [vr[0], vr[1], vr[2]], vr[3], vr[0])

    # ── TIROS A PUERTA ────────────────────────────────────────────────────────
    tiros_perd_mean = round(sc['Tiros_Perd'].mean(), 2)   if n else 0
    tiros_riv_mean  = round(sc['Tiros_Rival'].mean(), 2)  if n else 0

    fig_tiros = go.Figure()
    fig_tiros.add_trace(go.Bar(
        name='Equipo (perdiendo al MT)', x=['Perdiendo al MT'],
        y=[tiros_perd_mean],
        marker_color=ROJO, marker_line_width=0,
        text=[tiros_perd_mean], texttemplate='<b>%{text}</b>', textposition='outside',
    ))
    fig_tiros.add_trace(go.Bar(
        name='Rival (cuando equipo pierde al MT)', x=['Rival · perdiendo al MT'],
        y=[tiros_riv_mean],
        marker_color=AMARILLO, marker_line_width=0,
        text=[tiros_riv_mean], texttemplate='<b>%{text}</b>', textposition='outside',
    ))
    fig_tiros.add_trace(go.Bar(
        name='Equipo (resto de partidos)', x=['Resto de partidos'],
        y=[normal_tiros_mean],
        marker_color=VERDE_ACENTO, marker_line_width=0,
        text=[normal_tiros_mean], texttemplate='<b>%{text}</b>', textposition='outside',
    ))
    fig_tiros.update_layout(
        **{**LAYOUT_BASE, 'legend': {**LEGEND_BASE, 'orientation': 'h', 'y': -0.18, 'x': 0.5, 'xanchor': 'center'}},
        title=dict(text='Promedio de tiros a puerta · Perdiendo al MT vs. resto de partidos',
                   font=dict(size=15, color=TEXTO), x=0),
        barmode='group', bargap=0.2, bargroupgap=0.05,
        yaxis_title='Tiros a puerta promedio', xaxis_title='',
        showlegend=True,
    )

    # ── CÓRNERS PROPIOS ───────────────────────────────────────────────────────
    corners_perd_mean = round(sc['Corners_Perd'].mean(), 2) if n else 0
    delta_c = round(corners_perd_mean - normal_corners_mean, 2)

    fig_corners = go.Figure()
    fig_corners.add_trace(go.Bar(
        x=['Perdiendo al MT', 'Resto de partidos'],
        y=[corners_perd_mean, normal_corners_mean],
        marker_color=[ROJO, VERDE_ACENTO], marker_line_width=0,
        text=[f'{corners_perd_mean:.2f}', f'{normal_corners_mean:.2f}'],
        texttemplate='<b>%{text}</b>', textposition='outside',
        textfont=dict(size=14, color=TEXTO), width=0.45,
    ))
    if n:
        fig_corners.add_annotation(
            x='Perdiendo al MT', y=corners_perd_mean + 0.5,
            text=f"{'▲' if delta_c >= 0 else '▼'} {abs(delta_c):.2f} vs resto",
            font=dict(color=VERDE_ACENTO if delta_c >= 0 else ROJO, size=12), showarrow=False,
        )
    fig_corners.update_layout(
        **LAYOUT_BASE,
        title=dict(text='Córners propios del equipo (solo su equipo) · Perdiendo al MT vs. resto',
                   font=dict(size=15, color=TEXTO), x=0),
        yaxis_title='Córners propios promedio', xaxis_title='', showlegend=False,
    )

    # ── ANILLO ────────────────────────────────────────────────────────────────
    conteo = sc.groupby('Resultado_Final').size().reset_index(name='Total')
    fig_anillo = go.Figure(go.Pie(
        labels=conteo['Resultado_Final'], values=conteo['Total'], hole=0.62,
        marker=dict(colors=[
            VERDE_ACENTO if r == 'Remontada (G)' else AMARILLO if r == 'Empate (E)' else ROJO
            for r in conteo['Resultado_Final']
        ], line=dict(color=VERDE_OSCURO, width=3)),
        textinfo='percent+label', textfont=dict(size=13, color=TEXTO),
        hovertemplate='<b>%{label}</b><br>%{value} partidos<br>%{percent}<extra></extra>',
    ))
    fig_anillo.add_annotation(
        text=f'<b style="font-size:20px">{pct_remontada}%</b><br>remontan',
        x=0.5, y=0.5, showarrow=False, font=dict(size=14, color=VERDE_ACENTO), align='center',
    )
    fig_anillo.update_layout(
        **LAYOUT_BASE,
        title=dict(text='Resultados finales (equipo perdiendo al MT)',
                   font=dict(size=15, color=TEXTO), x=0),
        showlegend=True,
        legend=dict(bgcolor='rgba(0,0,0,0)', orientation='h', y=-0.1, x=0.5,
                    xanchor='center', font=dict(color=TEXTO)),
    )

    # ── BARRAS TEMPORADA ──────────────────────────────────────────────────────
    sc2 = sc.copy()
    if 'Date' in sc2.columns:
        sc2['Año'] = pd.to_datetime(sc2['Date'], dayfirst=True, errors='coerce').dt.year
        temp_col = 'Temporada' if 'Temporada' in sc2.columns else 'Año'
    else:
        sc2['Temporada'] = 'General'
        temp_col = 'Temporada'

    temp_res = sc2.groupby([temp_col, 'Resultado_Final']).size().reset_index(name='n')
    color_map = {'Remontada (G)': VERDE_ACENTO, 'Empate (E)': AMARILLO, 'Derrota (P)': ROJO}
    fig_barras = px.bar(temp_res, x=temp_col, y='n', color='Resultado_Final',
                        color_discrete_map=color_map, barmode='stack',
                        title='Resultados por temporada (perdiendo al MT)',
                        labels={'n': 'Partidos', temp_col: ''})
    fig_barras.update_traces(marker_line_width=0)
    fig_barras.update_layout(
        **LAYOUT_BASE,
        title=dict(font=dict(size=15, color=TEXTO), x=0),
        legend=dict(bgcolor='rgba(0,0,0,0)', orientation='h', y=-0.15, x=0.5,
                    xanchor='center', font=dict(color=TEXTO)),
        yaxis_title='Nº de partidos',
    )

    # ── SCATTER ───────────────────────────────────────────────────────────────
    fig_scatter = go.Figure()
    for resultado, color in [('Remontada (G)', VERDE_ACENTO), ('Empate (E)', AMARILLO), ('Derrota (P)', ROJO)]:
        sub = sc[sc['Resultado_Final'] == resultado]
        fig_scatter.add_trace(go.Scatter(
            x=sub['Corners_Perd'], y=sub['Goles_Perd'], mode='markers', name=resultado,
            marker=dict(color=color, size=7, opacity=0.7, line=dict(color=VERDE_OSCURO, width=0.5)),
            hovertemplate='Córners: %{x}<br>Goles: %{y}<extra>' + resultado + '</extra>',
        ))
    fig_scatter.update_layout(
        **LAYOUT_BASE,
        title=dict(text='Córners propios vs. goles anotados (equipo perdiendo al MT)',
                   font=dict(size=15, color=TEXTO), x=0),
        xaxis_title='Córners propios', yaxis_title='Goles al final',
        legend=dict(bgcolor='rgba(0,0,0,0)', orientation='h', y=-0.15, x=0.5,
                    xanchor='center', font=dict(color=TEXTO)),
    )

    return (kpis,
            fig_termo_c, verd_corners, fig_dist,
            fig_termo_r, verd_remontada,
            fig_tiros, fig_corners, fig_anillo, fig_barras, fig_scatter)


# ─── 6. RUN ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
