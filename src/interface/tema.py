"""
Tema visual Altiplano — sistema de design da ferramenta de viabilidade.

Paleta stone + ocre, tipografia DM Serif Display / DM Mono / Inter.
Sidebar escura (#1A1916), conteudo claro (#F5F3EE).
"""

import streamlit as st


CSS_TEMA = """
<style>
/* =====================================================================
   TIPOGRAFIA — Google Fonts
   ===================================================================== */

@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Inter:wght@300;400;500;600&display=swap');

/* =====================================================================
   VARIAVEIS — Paleta Altiplano
   ===================================================================== */

:root {
    /* Stone */
    --stone-900: #1A1916;
    --stone-700: #4A4944;
    --stone-500: #8A8880;
    --stone-300: #C4C1B8;
    --stone-100: #ECEAE4;
    --stone-50:  #F5F3EE;

    /* Azul naval (marca + atencao) */
    --navy-700: #1E2F6E;
    --navy-500: #1E3A8A;
    --navy-300: #4A6FBF;
    --navy-100: #DBEAFE;
    --navy-50:  #EFF6FF;

    /* Semantica financeira */
    --green:     #2D7A4F;
    --green-bg:  #E8F5EE;
    --red:       #B83C2A;
    --red-bg:    #F8EBE8;
    --blue:      #3A6EA8;
    --blue-bg:   #EEF3FA;

    /* Aliases de interface */
    --bg-app:       var(--stone-50);
    --bg-card:      #FFFFFF;
    --bg-sidebar:   #000000;
    --border:       var(--stone-300);
    --border-light: var(--stone-100);
    --text-primary: var(--stone-900);
    --text-secondary: var(--stone-500);
    --text-muted:   var(--stone-300);
    --accent:       var(--navy-500);
    --accent-dark:  var(--navy-700);
}

/* =====================================================================
   BASE — fundo geral e tipografia
   ===================================================================== */

.stApp {
    background-color: var(--bg-app) !important;
    font-family: 'Inter', system-ui, sans-serif !important;
}

.block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
    max-width: 100% !important;
}

/* =====================================================================
   SIDEBAR — escura com acento ocre
   ===================================================================== */

section[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 0.5px solid #1A1A1A !important;
}

section[data-testid="stSidebar"] > div {
    background-color: var(--bg-sidebar) !important;
}

/* Compactar todos os containers da sidebar */
section[data-testid="stSidebar"] .element-container {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

section[data-testid="stSidebar"] .element-container:has(.stButton),
section[data-testid="stSidebar"] .element-container:has(.nav-grupo-header) {
    padding: 0 !important;
}

section[data-testid="stSidebar"] .stMarkdown:has(.nav-grupo-header) {
    margin: 0 !important;
    padding: 0 !important;
}

/* Cabecalho de grupo — label de secao */
section[data-testid="stSidebar"] .nav-grupo-header {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.14em;
    color: var(--stone-500);
    text-transform: uppercase;
    padding: 14px 10px 4px;
}

/* Botoes de navegacao — caixa, alinhado a esquerda */
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.04) !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 6px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    text-align: left !important;
    padding: 7px 12px !important;
    margin: 1px 10px !important;
    color: #9CA3A8 !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    box-shadow: none !important;
    width: calc(100% - 20px) !important;
    transition: background 0.12s, border-color 0.12s, color 0.12s !important;
    line-height: 1.4 !important;
    font-family: 'Inter', sans-serif !important;
}

section[data-testid="stSidebar"] .stButton > button:hover:not(:disabled) {
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.14) !important;
    color: #F5F3EE !important;
}

/* Item ativo — caixa ocre */
section[data-testid="stSidebar"] .stButton > button:disabled {
    background: rgba(30,58,138,0.14) !important;
    border: 0.5px solid rgba(30,58,138,0.35) !important;
    color: #93C5FD !important;
    font-weight: 600 !important;
    opacity: 1 !important;
    cursor: default !important;
}

/* Botoes primarios da sidebar — branco com texto escuro (igual ao Baixar JSON) */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border: 0.5px solid #D1D5DB !important;
    border-radius: 6px !important;
    color: #1A1916 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    width: calc(100% - 20px) !important;
    margin: 4px 10px 6px !important;
    padding: 9px 12px !important;
    justify-content: center !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
}

section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]:hover {
    background: #F3F4F6 !important;
    background-color: #F3F4F6 !important;
    border-color: #9CA3AF !important;
    color: #111111 !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.16) !important;
}

/* Textos na sidebar (markdown, labels) */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown p {
    color: var(--stone-500) !important;
    font-size: 12px !important;
}

/* Separadores na sidebar */
section[data-testid="stSidebar"] hr {
    border-color: #1A1A1A !important;
}

/* Toggles/checkboxes na sidebar */
section[data-testid="stSidebar"] .stToggle label,
section[data-testid="stSidebar"] .stCheckbox label {
    color: var(--stone-300) !important;
}

/* Expanders na sidebar */
section[data-testid="stSidebar"] .streamlit-expanderHeader {
    background: rgba(255,255,255,0.04) !important;
    color: var(--stone-300) !important;
    border: 0.5px solid #1A1A1A !important;
    border-radius: 6px !important;
}

/* Metricas na sidebar */
section[data-testid="stSidebar"] [data-testid="metric-container"] label {
    color: var(--stone-500) !important;
}

section[data-testid="stSidebar"] [data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--stone-100) !important;
}

/* =====================================================================
   RESUMO TEMPO REAL — rodape sidebar
   ===================================================================== */

.resumo-tempo-real {
    margin-top: 24px;
    padding: 14px 14px;
    border-top: 0.5px solid #1A1A1A;
}

.resumo-tempo-real .titulo {
    font-size: 9px;
    letter-spacing: 0.14em;
    color: var(--stone-500);
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 12px;
}

.resumo-tempo-real .item { margin-bottom: 10px; }

.resumo-tempo-real .item-label {
    font-size: 11px;
    color: var(--stone-500);
    margin-bottom: 2px;
}

.resumo-tempo-real .item-valor {
    font-family: 'DM Serif Display', serif;
    font-size: 16px;
    color: var(--stone-100);
}

.resumo-tempo-real .item-valor.verde { color: #5DBF8A; }
.resumo-tempo-real .item-valor.vermelho { color: #E07060; }

/* =====================================================================
   HEADER — breadcrumb
   ===================================================================== */

.header-principal {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0 14px 0;
    margin-bottom: 10px;
    border-bottom: 0.5px solid var(--border);
}

.breadcrumb {
    color: var(--text-secondary);
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Inter', sans-serif;
}

.breadcrumb .item-ativo {
    color: var(--text-primary);
    font-weight: 600;
}

.breadcrumb .versao-tag {
    background: var(--stone-100);
    color: var(--stone-500);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-family: 'DM Mono', monospace;
    border: 0.5px solid var(--border);
}

.salvo-automaticamente {
    color: var(--green);
    font-size: 11px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 500;
}

.salvo-automaticamente::before {
    content: "●";
    font-size: 8px;
}

/* =====================================================================
   CABECALHO DE ABA — eyebrow + titulo
   ===================================================================== */

.modulo-titulo h1 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 26px !important;
    font-weight: 400 !important;
    color: var(--text-primary) !important;
    margin-bottom: 4px !important;
    padding-top: 0 !important;
    line-height: 1.2 !important;
}

.modulo-subtitulo {
    color: var(--text-secondary);
    font-size: 12px;
    margin-bottom: 20px;
    letter-spacing: 0.04em;
}

/* =====================================================================
   CARDS
   ===================================================================== */

.card {
    background: var(--bg-card);
    border: 0.5px solid var(--border);
    border-radius: 14px;
    padding: 22px;
    margin-bottom: 16px;
    box-shadow: 0 2px 12px rgba(26,25,22,0.04);
    transition: box-shadow 0.2s;
}

.card:hover {
    box-shadow: 0 4px 24px rgba(26,25,22,0.07);
}

.card-titulo {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 14px;
    letter-spacing: 0.01em;
}

/* =====================================================================
   KPI CARDS — 4 estados semanticos
   ===================================================================== */

.kpi-card {
    background: var(--bg-card);
    border: 0.5px solid var(--border);
    border-radius: 14px;
    padding: 18px 16px;
    height: 100%;
    transition: box-shadow 0.2s;
}

.kpi-card:hover {
    box-shadow: 0 4px 18px rgba(26,25,22,0.06);
}

/* Verde — viavel, positivo */
.kpi-card.verde {
    background: var(--green-bg);
    border-color: var(--green);
    border-width: 0.5px;
}

/* Ocre — atencao, warning (= cor da marca!) */
.kpi-card.atencao {
    background: var(--navy-50);
    border-color: var(--navy-500);
    border-width: 0.5px;
}

/* Vermelho — inviavel, negativo */
.kpi-card.vermelho {
    background: var(--red-bg);
    border-color: var(--red);
    border-width: 0.5px;
}

/* Azul — dado neutro */
.kpi-card.neutro-azul {
    background: var(--blue-bg);
    border-color: var(--blue);
    border-width: 0.5px;
}

.kpi-label {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.kpi-card.verde  .kpi-label { color: var(--green); }
.kpi-card.atencao .kpi-label { color: var(--navy-700); }
.kpi-card.vermelho .kpi-label { color: var(--red); }
.kpi-card.neutro-azul .kpi-label { color: var(--blue); }

.kpi-valor {
    font-family: 'DM Serif Display', serif;
    font-size: 22px;
    color: var(--text-primary);
    line-height: 1.15;
}

.kpi-card.verde     .kpi-valor { color: #1A5C38; }
.kpi-card.atencao   .kpi-valor { color: var(--navy-700); }
.kpi-card.vermelho  .kpi-valor { color: #8A2A1A; }
.kpi-card.neutro-azul .kpi-valor { color: #1A4A80; }

.kpi-sub {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 5px;
    line-height: 1.4;
}

/* =====================================================================
   SAUDE DO MODELO
   ===================================================================== */

.saude-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.4;
}

.saude-item .check-ok  { color: var(--green); font-size: 15px; }
.saude-item .check-warn { color: var(--navy-500); font-size: 15px; }
.saude-item .check-err { color: var(--red); font-size: 15px; }

/* =====================================================================
   BOTOES — primario ocre, secundario stone
   ===================================================================== */

.stButton > button {
    background-color: var(--bg-card) !important;
    color: var(--stone-700) !important;
    border: 0.5px solid var(--border) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    transition: all 0.15s !important;
    box-shadow: 0 1px 4px rgba(26,25,22,0.06) !important;
}

.stButton > button:hover {
    background-color: var(--stone-100) !important;
    border-color: var(--stone-500) !important;
    color: var(--stone-900) !important;
    box-shadow: 0 2px 8px rgba(26,25,22,0.10) !important;
}

/* Botao primario — ocre */
.stButton > button[kind="primary"] {
    background-color: var(--navy-500) !important;
    border-color: var(--navy-500) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(30,58,138,0.25) !important;
}

.stButton > button[kind="primary"]:hover {
    background-color: var(--navy-700) !important;
    border-color: var(--navy-700) !important;
    box-shadow: 0 4px 14px rgba(30,58,138,0.30) !important;
}

/* =====================================================================
   INPUTS — borda stone, foco ocre
   ===================================================================== */

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background-color: #FFFFFF !important;
    color: var(--stone-900) !important;
    border: 0.5px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--navy-500) !important;
    box-shadow: 0 0 0 2px rgba(30,58,138,0.15) !important;
}

.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    color: var(--stone-900) !important;
    border: 0.5px solid var(--border) !important;
    border-radius: 8px !important;
}

/* Labels dos inputs */
.stTextInput label, .stNumberInput label,
.stSelectbox label, .stDateInput label,
.stRadio label, .stCheckbox label, .stToggle label {
    color: var(--stone-700) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

/* Radio e toggle */
.stRadio [data-testid="stWidgetLabel"] p {
    color: var(--stone-700) !important;
}

/* =====================================================================
   TABS
   ===================================================================== */

.stTabs [data-baseweb="tab-list"] {
    background-color: transparent;
    border-bottom: 0.5px solid var(--border);
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    color: var(--stone-500) !important;
    background: transparent !important;
    border-radius: 6px 6px 0 0 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
}

.stTabs [aria-selected="true"] {
    color: var(--navy-700) !important;
    font-weight: 600 !important;
    border-bottom: 2px solid var(--navy-500) !important;
}

/* =====================================================================
   EXPANDERS
   ===================================================================== */

.streamlit-expanderHeader {
    background-color: var(--stone-100) !important;
    border: 0.5px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--stone-700) !important;
    font-weight: 500 !important;
}

.streamlit-expanderContent {
    border: 0.5px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    background: var(--bg-card) !important;
}

/* =====================================================================
   METRICAS nativas do Streamlit
   ===================================================================== */

[data-testid="metric-container"] label {
    color: var(--stone-500) !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'DM Serif Display', serif !important;
    font-size: 22px !important;
    color: var(--stone-900) !important;
}

[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 12px !important;
}

/* =====================================================================
   DATAFRAMES / TABELAS STREAMLIT
   ===================================================================== */

.stDataFrame {
    border: 0.5px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: hidden;
}

/* =====================================================================
   ALERTAS / MENSAGENS
   ===================================================================== */

.stSuccess {
    background: var(--green-bg) !important;
    border: 0.5px solid var(--green) !important;
    border-radius: 8px !important;
    color: #1A5C38 !important;
}

.stWarning {
    background: var(--navy-50) !important;
    border: 0.5px solid var(--navy-500) !important;
    border-radius: 8px !important;
    color: var(--navy-700) !important;
}

.stError {
    background: var(--red-bg) !important;
    border: 0.5px solid var(--red) !important;
    border-radius: 8px !important;
    color: #8A2A1A !important;
}

.stInfo {
    background: var(--blue-bg) !important;
    border: 0.5px solid var(--blue) !important;
    border-radius: 8px !important;
    color: #1A4A80 !important;
}

/* =====================================================================
   CONTAINERS (st.container border=True)
   ===================================================================== */

[data-testid="stVerticalBlock"] > [data-testid="element-container"] > div[data-testid="stVerticalBlock"] {
    border-radius: 12px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 0.5px solid var(--border) !important;
    border-radius: 12px !important;
    background: var(--bg-card) !important;
    padding: 4px !important;
    box-shadow: 0 1px 8px rgba(26,25,22,0.04) !important;
}

/* =====================================================================
   DRE CASCATA — Resultado Estatico
   ===================================================================== */

.dre-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    color: var(--stone-700);
    margin-bottom: 24px;
    font-family: 'Inter', sans-serif;
}

.dre-table th {
    background: var(--stone-100);
    color: var(--stone-500);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 10px 14px;
    text-align: right;
    border-bottom: 0.5px solid var(--border);
}

.dre-table th:first-child { text-align: left; }

.dre-table td {
    padding: 8px 14px;
    border-bottom: 0.5px solid var(--border-light);
    text-align: right;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
}

.dre-table td:first-child {
    text-align: left;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
}

.dre-row-header td {
    font-weight: 700;
    font-size: 14px;
    color: var(--stone-900);
    font-family: 'Inter', sans-serif;
}

.dre-row-subtotal td {
    font-weight: 600;
    border-top: 0.5px solid var(--border);
    background: var(--stone-100);
    color: var(--stone-900);
    font-family: 'Inter', sans-serif;
}

.dre-row-deduction td { color: var(--stone-500); }

.dre-row-addition td { color: var(--blue); }

.dre-row-separator td {
    height: 6px;
    background: transparent;
    border: none;
    padding: 0;
}

.dre-row-resultado td {
    font-family: 'DM Serif Display', serif;
    font-size: 15px;
    color: #1A5C38;
    background: var(--green-bg);
    border-top: 0.5px solid var(--border);
}

.dre-row-resultado.negativo td {
    color: #8A2A1A;
    background: var(--red-bg);
}

/* =====================================================================
   LINHA DO TEMPO — timeline SVG
   ===================================================================== */

.timeline-container {
    background: var(--bg-card);
    border: 0.5px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
}

/* =====================================================================
   ESCONDER ELEMENTOS DEFAULT DO STREAMLIT
   ===================================================================== */

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* Barra de loading */
.stStatusWidget { visibility: hidden; }

</style>
"""

# =====================================================================
# LAYOUT PLOTLY PADRAO — Altiplano
# =====================================================================

PLOTLY_PAPER_BG = "#F5F3EE"
PLOTLY_PLOT_BG  = "#FFFFFF"
PLOTLY_GRID     = "#ECEAE4"
PLOTLY_TEXT     = "#8A8880"
PLOTLY_FONT_COLOR = "#4A4944"

PLOTLY_VERDE   = "#2D7A4F"
PLOTLY_OCRE    = "#2B50A8"
PLOTLY_VERMELHO = "#B83C2A"
PLOTLY_AZUL    = "#3A6EA8"
PLOTLY_CINZA   = "#C4C1B8"

PLOTLY_VERDE_BG   = "#E8F5EE"
PLOTLY_OCRE_BG    = "#EFF6FF"
PLOTLY_VERMELHO_BG = "#F8EBE8"


def plotly_layout_padrao(
    height: int = 320,
    margin: dict | None = None,
    title: str = "",
) -> dict:
    """Retorna o dict de layout Plotly com a identidade visual Altiplano."""
    if margin is None:
        margin = dict(l=40, r=20, t=30 if title else 10, b=40)
    return dict(
        paper_bgcolor=PLOTLY_PAPER_BG,
        plot_bgcolor=PLOTLY_PLOT_BG,
        font=dict(
            color=PLOTLY_FONT_COLOR,
            family="Inter, system-ui, sans-serif",
            size=11,
        ),
        title=dict(text=title, font=dict(family="DM Serif Display, serif", size=16, color="#1A1916")) if title else {},
        margin=margin,
        height=height,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor=PLOTLY_CINZA,
            font_size=12,
            font_color="#1A1916",
        ),
        xaxis=dict(
            gridcolor=PLOTLY_GRID,
            zeroline=False,
            tickfont=dict(size=11, color=PLOTLY_TEXT),
            linecolor=PLOTLY_GRID,
        ),
        yaxis=dict(
            gridcolor=PLOTLY_GRID,
            zeroline=False,
            tickfont=dict(size=11, color=PLOTLY_TEXT),
            linecolor=PLOTLY_GRID,
        ),
    )


def aplicar_tema() -> None:
    """Injeta o CSS no Streamlit. Deve ser chamado no inicio do main()."""
    st.markdown(CSS_TEMA, unsafe_allow_html=True)
