"""
Aba 8 — Dashboard.

Integra o conteudo de Visao Geral, Resultado Estatico e graficos interativos:
- Saude do modelo e linha do tempo
- KPIs principais com veredito TIR/TMA
- Graficos: curva de caixa, composicao mensal, curvas acumuladas, obras x vendas
- DRE — Demonstrativo de Resultado em cascata
- Composicao das Saidas (donut)
- Tabela de fluxo com periodicidade Mensal / Trimestral / Anual
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ..helpers import (
    cabecalho_aba,
    formatar_brl,
    formatar_pct,
    get_projeto,
    get_resultado,
    marcos_projeto,
    renderizar_calcular_cta,
)
from ..tema_componentes import (
    renderizar_grade_kpis,
    renderizar_linha_tempo_trilhas,
    renderizar_saude_modelo,
)
from ..validacoes import validar_projeto_completo
from ...engine.utilidades import meses_entre
from ...engine.financiamento_engine import simular_financiamento
from ...io_projeto.exportar_html import gerar_relatorio_html


# =====================================================================
# CONFIG DE EXPORT PNG (barra de ferramenta discreta com icone de camera)
# =====================================================================

_PLOTLY_CONFIG = {
    "displayModeBar": "hover",
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d",
        "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
        "hoverClosestCartesian", "hoverCompareCartesian", "toggleSpikelines",
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "viabilidade",
        "scale": 2,
    },
}


# =====================================================================
# TEMA PLOTLY
# =====================================================================

_LAYOUT_BASE = dict(
    paper_bgcolor="#F5F3EE",
    plot_bgcolor="#ECEAE4",
    font=dict(color="#1A1916", family="Inter, sans-serif", size=12),
    margin=dict(l=60, r=60, t=50, b=50),
    legend=dict(
        bgcolor="#F5F3EE",
        bordercolor="#D8D4C8",
        borderwidth=1,
        font=dict(size=11),
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="left",
        x=0,
    ),
    hoverlabel=dict(bgcolor="#ECEAE4", font_size=12, font_color="#1A1916"),
)


def _layout(**kwargs) -> dict:
    base = dict(_LAYOUT_BASE)
    base.update(kwargs)
    return base


# =====================================================================
# PALETA DE CORES POR CATEGORIA
# =====================================================================

_CORES_SAIDAS: dict[str, str] = {
    "Aquisicao Terreno":      "#2B50A8",
    "Cartorio":               "#7A5520",
    "Obras":                  "#C49A3C",
    "Projetos":               "#4A7FA5",
    "Licenciamento":          "#6265B8",
    "Marketing":              "#7B5EA7",
    "Outros Desenvolvimento": "#9B59B6",
    "Administracao":          "#8A8880",
    "Comissao":               "#D4712B",
    "Impostos":               "#C05454",
    "Permuta Financeira":     "#6B3620",
}

_COR_NOMINAL = "#3D8B5E"
_COR_JUROS   = "#2E6B47"

_BG_LINHAS: dict[str, str] = {
    "Total Entradas":             "#D4EAD9",
    "Total Saidas":               "#F5D0D0",
    "Saldo do Mes":               "#ECEAE4",
    "Saldo Acumulado":            "#ECEAE4",
    "Saldo Descontado Acumulado": "#ECEAE4",
}

_SALDO_LINHAS = {"Saldo do Mes", "Saldo Acumulado", "Saldo Descontado Acumulado"}

_NEGRITO_LINHAS = {"Total Entradas", "Total Saidas", "Saldo Acumulado"}


# =====================================================================
# HELPERS GERAIS
# =====================================================================

def _fmt_m(v: float) -> str:
    av = abs(v)
    sign = "-" if v < 0 else ""
    if av >= 1_000_000:
        return f"{sign}R$ {av / 1_000_000:.1f}M".replace(".", ",")
    if av >= 1_000:
        return f"{sign}R$ {av / 1_000:.0f}k"
    return formatar_brl(v)


def _get_tma_str() -> str:
    try:
        return f"{get_projeto().parametros.tma_anual:.0f}"
    except Exception:
        return "?"


# =====================================================================
# SAUDE DO MODELO (ABA 0)
# =====================================================================

def _renderizar_saude(projeto) -> None:
    checks = []

    soma_vendas = sum(f.percentual_estoque for f in projeto.receitas.curva_vendas)
    checks.append((
        abs(soma_vendas - 100.0) < 0.01,
        f"Velocidade de vendas soma {soma_vendas:.0f}%",
    ))

    todos_fluxos_ok = all(
        abs(f.percentual_sinal + f.percentual_obra
            + f.percentual_baloes + f.percentual_financiamento - 100.0) < 0.01
        for f in projeto.receitas.fluxos_recebiveis
    )
    checks.append((todos_fluxos_ok, "Perfil de pagamento soma 100%"))

    if projeto.obras.etapas:
        todas_obras_ok = True
        for et in projeto.obras.etapas:
            if et.curva == "customizada":
                soma = sum(et.curva_customizada)
                if abs(soma - 100.0) > 0.01:
                    todas_obras_ok = False
                    break
        checks.append((todas_obras_ok, "Curva de obras soma 100%"))
    else:
        checks.append((False, "Curva de obras nao definida"))

    checks.append((True, "Data de repasse >= termino de obras"))

    # Só exibe quando há pelo menos um problema — serve como sinal de atenção
    if not all(ok for ok, _ in checks):
        renderizar_saude_modelo(checks)


# =====================================================================
# PRE-CALC ESTIMATIVAS (ABA 0 — D3)
# =====================================================================

def _renderizar_pre_calc(projeto) -> None:
    st.markdown(
        '<div style="background:rgba(30,58,138,0.08);border-left:3px solid #2B50A8;'
        'padding:8px 12px;border-radius:0 4px 4px 0;font-size:12px;color:#1E3A8A;'
        'margin:12px 0;">'
        'Estimativas antes do cálculo — dados precisos após Calcular</div>',
        unsafe_allow_html=True,
    )
    try:
        def _fmt_est(v: float) -> str:
            if abs(v) >= 1_000_000:
                return f"R$ {v/1_000_000:.2f}M"
            if abs(v) >= 1_000:
                return f"R$ {v/1_000:.0f}k"
            return formatar_brl(v)

        vgv_est = sum(
            float(t.quantidade) * float(t.valor_unitario)
            for t in projeto.terreno.tipologias
        ) if projeto.terreno.tipologias else 0.0
        terreno_est = float(projeto.aquisicao.valor_total)
        obras = projeto.obras
        bdi_mult = (
            (1 + float(obras.bdi_percentual) / 100)
            * (1 + float(obras.contingencia_percentual) / 100)
        )
        if obras.modo == "detalhado" and obras.etapas:
            custo_dir = sum(float(e.valor_total) for e in obras.etapas)
        elif obras.resumido:
            areas = projeto.terreno.areas
            base_m2 = (
                float(areas.area_sistema_viario_m2)
                if obras.resumido.base_calculo == "sistema_viario"
                else float(areas.area_lotes_m2)
            )
            custo_dir = base_m2 * float(obras.resumido.valor_por_m2)
        else:
            custo_dir = 0.0
        obras_est = custo_dir * bdi_mult
        desp_est = (
            sum(float(d.valor_total) for d in projeto.desenvolvimento.despesas)
            if hasattr(projeto.desenvolvimento, "despesas") else 0.0
        )
        margem_est = (
            (vgv_est - obras_est - terreno_est - desp_est) / vgv_est * 100
            if vgv_est > 0 else 0.0
        )
        _c1, _c2, _c3, _c4 = st.columns(4)
        with _c1:
            st.metric("VGV (est.)", _fmt_est(vgv_est) if vgv_est > 0 else "—")
        with _c2:
            st.metric("Obras (est.)", _fmt_est(obras_est) if obras_est > 0 else "—")
        with _c3:
            st.metric("Terreno", _fmt_est(terreno_est) if terreno_est > 0 else "—")
        with _c4:
            st.metric("Margem Bruta (est.)", f"{margem_est:.1f}%" if vgv_est > 0 else "—")
    except Exception:
        pass

    st.info(
        "Clique em **'Calcular viabilidade'** na sidebar "
        "para ver os indicadores completos.  \n"
        "Lembre-se de configurar a **Aquisição do Terreno** (sidebar → Dados) "
        "antes de calcular."
    )


# =====================================================================
# BADGE DE VEREDITO — VIAVEL / MARGINAL / INVIAVEL
# =====================================================================

def _renderizar_badge_veredito(r: dict, ind: dict, projeto) -> None:
    tma = projeto.parametros.tma_anual if projeto else 15.0
    vpl = ind.get("vpl", 0) or 0
    tir = ind.get("tir_anual")
    lucro = r.get("lucro_liquido", 0) or 0
    vgv = r.get("vgv_vendavel", 1) or 1
    margem = lucro / vgv * 100 if vgv > 0 else 0
    tir_pct = tir * 100 if tir else 0

    if vpl > 0 and tir_pct >= tma + 4 and margem >= 15:
        status = "VIÁVEL"
        cor_bg, cor_borda, cor_texto = "rgba(61,139,94,0.10)", "#3D8B5E", "#2E5F47"
        icone = "✓"
        detalhe = f"VPL positivo · TIR {tir_pct:.1f}% (TMA+{tir_pct - tma:.1f} p.p.) · Margem {margem:.1f}%"
    elif vpl > 0 and margem >= 5:
        status = "MARGINAL"
        cor_bg, cor_borda, cor_texto = "rgba(176,125,46,0.10)", "#B07D2E", "#7A5520"
        icone = "!"
        detalhe = f"VPL positivo · Margem {margem:.1f}% — revise premissas ou reduza custos"
    else:
        status = "INVIÁVEL"
        cor_bg, cor_borda, cor_texto = "rgba(192,84,84,0.10)", "#C05454", "#8B2E2E"
        icone = "✕"
        motivo = "VPL negativo" if vpl <= 0 else f"Margem {margem:.1f}% insuficiente"
        detalhe = f"{motivo} — revise preços, custos ou prazo"

    st.markdown(
        f'<div style="background:{cor_bg};border-left:4px solid {cor_borda};'
        f'padding:10px 16px;border-radius:0 6px 6px 0;margin:0 0 16px 0;'
        f'display:flex;align-items:center;gap:12px;">'
        f'<span style="font-size:17px;">{icone}</span>'
        f'<span style="font-family:\'DM Serif Display\',serif;font-size:17px;'
        f'font-weight:400;color:{cor_texto};letter-spacing:0.04em;">{status}</span>'
        f'<span style="font-size:12px;color:{cor_texto};opacity:0.75;margin-left:4px;">'
        f'— {detalhe}</span></div>',
        unsafe_allow_html=True,
    )


# =====================================================================
# KPIs TOPO — HIERARQUIA: 3 HEADLINE + 4 SECUNDARIOS
# =====================================================================

_CSS_KPI_HEADLINE = """
<style>
.kpi-hl-grid{display:flex;gap:14px;margin-bottom:14px;}
.kpi-hl{flex:1;background:#FFFFFF;border:1px solid #C4C1B8;border-radius:10px;
         padding:16px 14px 12px;position:relative;overflow:hidden;}
.kpi-hl::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;border-radius:10px 10px 0 0;}
.kpi-hl.verde::before{background:#3D8B5E;}
.kpi-hl.vermelho::before{background:#C05454;}
.kpi-hl.atencao::before{background:#B07D2E;}
.kpi-hl.neutro::before{background:#C4C1B8;}
.kpi-hl-label{font-size:10px;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;
               color:#8A8880;margin-bottom:10px;}
.kpi-hl-valor{font-family:'DM Serif Display',serif;font-size:22px;font-weight:400;
               color:#1A1916;line-height:1.1;margin-bottom:6px;}
.kpi-hl.verde .kpi-hl-valor{color:#2E5F47;}
.kpi-hl.vermelho .kpi-hl-valor{color:#8B2E2E;}
.kpi-hl.atencao .kpi-hl-valor{color:#7A5520;}
.kpi-hl-sub{font-size:12px;color:#5A5650;line-height:1.4;}
</style>
"""


def _kpis_topo(r: dict, ind: dict, projeto=None) -> None:
    tma = projeto.parametros.tma_anual if projeto else 15.0
    lucro = r["lucro_liquido"]
    vgv = r["vgv_vendavel"]
    margem = (lucro / vgv * 100) if vgv > 0 else 0
    vpl = ind["vpl"]
    tir = ind.get("tir_anual")
    exp_max = abs(ind["exposicao_maxima"])
    mes_exp = ind["mes_exposicao_maxima"]
    pb = ind.get("payback_simples_meses")
    custo_total = r["total_saidas"]
    horizonte = r.get("horizonte_meses", 0)

    tir_pct = tir * 100 if tir else 0
    if tir is not None:
        if tir_pct >= tma:
            tir_cor, tir_sub = "verde", f"Acima da TMA ({tma:.0f}% a.a.)"
        elif tir_pct >= tma * 0.85:
            tir_cor, tir_sub = "atencao", f"Próxima da TMA ({tma:.0f}% a.a.)"
        else:
            tir_cor, tir_sub = "vermelho", f"Abaixo da TMA ({tma:.0f}% a.a.)"
    else:
        tir_cor, tir_sub = "neutro", "TIR não convergiu"

    vpl_cor = "verde" if vpl > 0 else "vermelho"
    vpl_sub = "Projeto viável" if vpl > 0 else "Projeto inviável"
    marg_cor = "verde" if margem >= 15 else ("atencao" if margem > 0 else "vermelho")
    marg_sub = f"Resultado / VGV Vendável · R$ {lucro / 1e6:.1f}M".replace(".", ",")

    _TIP_TIR = (
        "Taxa Interna de Retorno — taxa que zera o VPL do projeto, equivalente ao "
        "rendimento anual do investimento. Compare com a TMA: TIR > TMA = projeto viável."
    )
    _TIP_VPL = (
        "Valor Presente Líquido — soma de todas as entradas e saídas trazidas a valor "
        "de hoje pela TMA. Positivo = projeto rende mais do que o custo de oportunidade."
    )
    _TIP_MARG = (
        "Lucro líquido ÷ VGV vendável. Loteamentos de alto padrão buscam 20–30%. "
        "Abaixo de 15% o projeto é considerado marginal; abaixo de 5% é inviável."
    )

    def _hl(label, valor, sub, cor, tip=""):
        title_attr = f' title="{tip}"' if tip else ""
        return (
            f'<div class="kpi-hl {cor}"{title_attr}>'
            f'<div class="kpi-hl-label">{label}</div>'
            f'<div class="kpi-hl-valor">{valor}</div>'
            f'<div class="kpi-hl-sub">{sub}</div>'
            f'</div>'
        )

    cards_html = (
        _hl("TIR Anual",          f"{tir_pct:.1f}%" if tir else "—", tir_sub, tir_cor, _TIP_TIR)
        + _hl(f"VPL ({tma:.0f}% a.a.)", _fmt_m(vpl),              vpl_sub, vpl_cor, _TIP_VPL)
        + _hl("Margem s/ VGV",   f"{margem:.1f}%",                 marg_sub, marg_cor, _TIP_MARG)
    )
    st.markdown(_CSS_KPI_HEADLINE, unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-hl-grid">{cards_html}</div>', unsafe_allow_html=True)

    pb_val = f"M{pb}" if pb else "—"
    pb_sub = f"de {horizonte} meses no projeto" if (pb and horizonte > 0) else ""
    kpis_sec = [
        {
            "label": "VGV Vendável",
            "valor": _fmt_m(vgv),
            "cor": "neutro",
            "help": "VGV Bruto menos lotes destinados à permuta física. Base de cálculo da margem e dos impostos.",
        },
        {
            "label": "Custo Total",
            "valor": _fmt_m(custo_total),
            "cor": "neutro",
            "help": "Soma de todas as saídas: terreno + obras (com BDI e contingência) + incorporação + comissão + impostos.",
        },
        {
            "label": "Pico de Exposição",
            "valor": _fmt_m(-exp_max),
            "sub": f"no M{mes_exp}",
            "cor": "vermelho",
            "help": "Maior saldo acumulado negativo — capital próprio máximo que precisa estar disponível ao mesmo tempo. Quanto menor, menor o risco de falta de caixa.",
        },
        {
            "label": "Payback",
            "valor": pb_val,
            "sub": pb_sub,
            "cor": "neutro",
            "help": "Mês em que o saldo acumulado cruza o zero — quando as receitas totais superam as saídas e o investimento começa a ser recuperado.",
        },
    ]
    renderizar_grade_kpis(kpis_sec)


# =====================================================================
# DRE EM CASCATA (ABA 6)
# =====================================================================

def _renderizar_cascata_dre(r: dict) -> None:
    vgv_bruto = r["vgv_bruto"]
    vgv_vendavel = r["vgv_vendavel"]
    permuta_fisica = vgv_bruto - vgv_vendavel

    def pct_vv(v: float) -> str:
        return formatar_pct(v / vgv_vendavel) if vgv_vendavel > 0 else "—"

    def pct_vb(v: float) -> str:
        return formatar_pct(v / vgv_bruto) if vgv_bruto > 0 else "—"

    def linha_header(label: str, valor: float) -> str:
        return (
            f'<tr class="dre-row-header">'
            f'<td>{label}</td><td>{formatar_brl(valor)}</td>'
            f'<td>{pct_vv(valor)}</td><td>{pct_vb(valor)}</td></tr>'
        )

    def linha_deducao(label: str, valor: float) -> str:
        if valor == 0:
            return ""
        return (
            f'<tr class="dre-row-deduction">'
            f'<td>&nbsp;&nbsp;&nbsp;{label}</td>'
            f'<td>({formatar_brl(valor)})</td>'
            f'<td>({pct_vv(valor)})</td>'
            f'<td>({pct_vb(valor)})</td></tr>'
        )

    def linha_adicao(label: str, valor: float) -> str:
        if valor == 0:
            return ""
        return (
            f'<tr class="dre-row-addition">'
            f'<td>&nbsp;&nbsp;&nbsp;{label}</td>'
            f'<td>+ {formatar_brl(valor)}</td>'
            f'<td>+ {pct_vv(valor)}</td>'
            f'<td>+ {pct_vb(valor)}</td></tr>'
        )

    def linha_subtotal(label: str, valor: float) -> str:
        return (
            f'<tr class="dre-row-subtotal">'
            f'<td>{label}</td><td>{formatar_brl(valor)}</td>'
            f'<td>{pct_vv(valor)}</td><td>{pct_vb(valor)}</td></tr>'
        )

    def separador() -> str:
        return '<tr class="dre-row-separator"><td colspan="4"></td></tr>'

    lucro = r["lucro_liquido"]
    classe_resultado = "dre-row-resultado" + ("" if lucro >= 0 else " negativo")
    linha_resultado = (
        f'<tr class="{classe_resultado}">'
        f'<td>Resultado Bruto (Lucro Liquido)</td>'
        f'<td>{formatar_brl(lucro)}</td>'
        f'<td>{pct_vv(lucro)}</td>'
        f'<td>{pct_vb(lucro)}</td></tr>'
    )

    partes = [
        linha_header("VGV Bruto", vgv_bruto),
        linha_deducao("(-) Permuta Fisica", permuta_fisica),
        linha_subtotal("VGV Vendavel (base de calculo)", vgv_vendavel),
        linha_adicao("(+) Receita Financeira (Juros)", r["receita_financeira"]),
        linha_subtotal("Receita Total", r["vgv_total_recebido"]),
        separador(),
        linha_deducao("(-) Aquisicao do Terreno",    r["custo_terreno_aquisicao"]),
        linha_deducao("(-) Cartorio",                 r["custo_terreno_cartorio"]),
        linha_deducao("(-) Obras",                    r["custo_obras"]),
        linha_deducao("(-) Projetos",                 r["custo_projetos"]),
        linha_deducao("(-) Licenciamento",             r["custo_licenciamento"]),
        linha_deducao("(-) Marketing",                r["custo_marketing"]),
        linha_deducao("(-) Outros",                   r["custo_outros"]),
        linha_deducao("(-) Administracao",            r["custo_administracao"]),
        linha_deducao("(-) Comissao de Vendas",       r["custo_comissao"]),
        linha_deducao("(-) Impostos / Tributacao",    r["custo_impostos"]),
        linha_deducao("(-) Permuta Financeira",       r["custo_permuta_financeira"]),
        separador(),
        linha_subtotal("Total de Saidas", r["total_saidas"]),
        separador(),
        linha_resultado,
    ]
    tbody = "".join(p for p in partes if p)
    thead = (
        '<thead><tr>'
        '<th style="width:40%;">Descricao</th>'
        '<th style="width:20%;">Valor (R$)</th>'
        '<th style="width:20%;">% VGV Vendavel</th>'
        '<th style="width:20%;">% VGV Bruto</th>'
        '</tr></thead>'
    )
    st.markdown(f'<table class="dre-table">{thead}<tbody>{tbody}</tbody></table>', unsafe_allow_html=True)


def _renderizar_cards_margem(r: dict, ind: dict) -> None:
    margem_vv = r.get("margem_sobre_vgv_vendavel")
    margem_vb = r.get("margem_sobre_vgv_bruto")
    multiplicador = ind.get("lucro_sobre_exposicao")
    tir = ind.get("tir_anual")

    def cor_margem(v) -> str:
        if v is None:
            return "neutro"
        return "verde" if v > 0 else "vermelho"

    kpis = [
        {"label": "Margem s/ VGV Vendavel",       "valor": formatar_pct(margem_vv) if margem_vv is not None else "—",    "cor": cor_margem(margem_vv)},
        {"label": "Margem s/ VGV Bruto",          "valor": formatar_pct(margem_vb) if margem_vb is not None else "—",    "cor": cor_margem(margem_vb)},
        {"label": "Multiplicador (Lucro/Exp.)",   "valor": f"{multiplicador:.2f}x".replace(".", ",") if multiplicador else "—", "cor": "verde" if (multiplicador and multiplicador > 1) else "neutro"},
        {"label": "TIR Anual",                    "valor": formatar_pct(tir) if tir is not None else "—",                "cor": "verde" if (tir and tir > 0.10) else "neutro"},
    ]
    st.markdown("#### Indicadores de Rentabilidade")
    renderizar_grade_kpis(kpis)


def _renderizar_composicao_saidas(r: dict) -> None:
    st.markdown("#### Composicao das Saidas")

    categorias_raw = [
        ("Terreno",      r["custo_terreno_aquisicao"] + r["custo_terreno_cartorio"]),
        ("Obras",        r["custo_obras"]),
        ("Projetos",     r["custo_projetos"]),
        ("Licenciamento", r["custo_licenciamento"]),
        ("Marketing",    r["custo_marketing"]),
        ("Outros / Admin", r["custo_outros"] + r["custo_administracao"]),
        ("Comissao",     r["custo_comissao"]),
        ("Impostos",     r["custo_impostos"]),
        ("Permuta Fin.", r["custo_permuta_financeira"]),
    ]
    pares = [(l, v) for l, v in categorias_raw if v > 0]
    if not pares:
        st.info("Nenhum custo calculado.")
        return

    labels, values = zip(*pares)
    total = sum(values)
    cores = [
        "#4A7FA5", "#2B50A8", "#3D8B5E", "#6265B8",
        "#7B5EA7", "#8A8880", "#C49A3C", "#C05454", "#2E6B47",
    ]

    col_grafico, col_tabela = st.columns([2, 3])

    with col_grafico:
        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            marker=dict(colors=cores[:len(labels)]),
            textinfo="percent",
            textfont=dict(color="#F5F3EE", size=11),
            hovertemplate="%{label}<br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="#F5F3EE",
            plot_bgcolor="#F5F3EE",
            font=dict(color="#1A1916", family="Inter, sans-serif", size=12),
            margin=dict(l=10, r=10, t=30, b=10),
            showlegend=True,
            legend=dict(bgcolor="#F5F3EE", bordercolor="#D8D4C8", borderwidth=1, font=dict(size=11), orientation="v"),
            hoverlabel=dict(bgcolor="#ECEAE4", font_size=12, font_color="#1A1916"),
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)

    with col_tabela:
        linhas: list[str] = []
        for (label, valor), cor in zip(pares, cores):
            pct = valor / total * 100 if total > 0 else 0
            por_lote = valor / r["total_lotes"] if r.get("total_lotes", 0) > 0 else 0
            dot = (
                f'<span style="display:inline-block;width:10px;height:10px;'
                f'border-radius:50%;background:{cor};margin-right:8px;"></span>'
            )
            linhas.append(
                f'<tr><td>{dot}{label}</td>'
                f'<td style="text-align:right;">{formatar_brl(valor)}</td>'
                f'<td style="text-align:right;">{pct:.1f}%</td>'
                f'<td style="text-align:right;">{formatar_brl(por_lote)}</td></tr>'
            )
        por_lote_total = (
            formatar_brl(total / r["total_lotes"]) if r.get("total_lotes", 0) > 0 else "—"
        )
        linha_total = (
            f'<tr class="dre-row-subtotal"><td>Total Saidas</td>'
            f'<td style="text-align:right;">{formatar_brl(total)}</td>'
            f'<td style="text-align:right;">100,0%</td>'
            f'<td style="text-align:right;">{por_lote_total}</td></tr>'
        )
        thead_comp = (
            '<thead><tr>'
            '<th style="text-align:left;">Categoria</th>'
            '<th style="text-align:right;">Total (R$)</th>'
            '<th style="text-align:right;">% Saidas</th>'
            '<th style="text-align:right;">Por Lote</th>'
            '</tr></thead>'
        )
        tbody_comp = "".join(linhas) + linha_total
        st.markdown(
            f'<table class="dre-table">{thead_comp}<tbody>{tbody_comp}</tbody></table>',
            unsafe_allow_html=True,
        )


def _renderizar_nominal_vs_financeiro(r: dict) -> None:
    receita_nominal = r.get("receita_nominal_venda", 0)
    receita_financeira = r.get("receita_financeira", 0)
    total_recebido = r.get("vgv_total_recebido", 0)
    if receita_financeira < 1:
        return

    st.markdown("#### Receita Nominal vs Receita Financeira")
    st.caption(
        "A receita financeira sao os juros embutidos nas parcelas (sistema Price). "
        "O resultado nominal e o lucro sobre o VGV; o resultado total inclui esses juros."
    )
    pct_fin = receita_financeira / total_recebido * 100 if total_recebido > 0 else 0
    kpis = [
        {"label": "Receita Nominal de Venda", "valor": formatar_brl(receita_nominal),    "sub": "Principal (= VGV vendavel)", "cor": "neutro"},
        {"label": "Receita Financeira (Juros)", "valor": formatar_brl(receita_financeira), "sub": f"{pct_fin:.1f}% da receita total", "cor": "neutro"},
        {"label": "Total Recebido",            "valor": formatar_brl(total_recebido),    "sub": "Nominal + Juros", "cor": "verde"},
    ]
    renderizar_grade_kpis(kpis)


# =====================================================================
# HELPER: FAIXAS DE FASE NOS GRAFICOS
# =====================================================================

def _adicionar_fases(fig: go.Figure, mes_inicio_obras: int, mes_termino: int) -> None:
    if mes_inicio_obras > 0:
        fig.add_vrect(
            x0=0, x1=mes_inicio_obras,
            fillcolor="rgba(74,127,165,0.06)", line_width=0,
            annotation_text="Pre-obra", annotation_position="inside top left",
            annotation_font=dict(size=8, color="#4A7FA5"),
        )
    if mes_termino > mes_inicio_obras:
        fig.add_vrect(
            x0=mes_inicio_obras, x1=mes_termino,
            fillcolor="rgba(43,80,168,0.07)", line_width=0,
            annotation_text="Obras", annotation_position="inside top left",
            annotation_font=dict(size=8, color="#2B50A8"),
        )
    if mes_termino > 0:
        fig.add_vline(
            x=mes_termino, line_dash="dash",
            line_color="rgba(43,80,168,0.50)", line_width=1,
            annotation_text=f"M{mes_termino}", annotation_position="top left",
            annotation_font=dict(size=8, color="#2B50A8"),
        )


# =====================================================================
# GRAFICOS (TABS 1-4)
# =====================================================================

def _grafico_curva_caixa(df, ind: dict, mes_inicio_obras: int, mes_termino: int) -> None:
    meses = df["Mes"].tolist()
    saldo = df["Saldo Acumulado"].tolist()
    saldo_desc = df["Saldo Descontado Acumulado"].tolist()
    mes_exp = ind["mes_exposicao_maxima"]
    exp_val = ind["exposicao_maxima"]
    pb = ind.get("payback_simples_meses")
    vpl = ind["vpl"]
    tir = ind.get("tir_anual")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=meses, y=[min(s, 0.0) for s in saldo],
        fill="tozeroy", fillcolor="rgba(192,84,84,0.12)",
        line=dict(width=0, color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip", name="_neg",
    ))
    fig.add_trace(go.Scatter(
        x=meses, y=[max(s, 0.0) for s in saldo],
        fill="tozeroy", fillcolor="rgba(61,139,94,0.10)",
        line=dict(width=0, color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip", name="_pos",
    ))
    fig.add_trace(go.Scatter(
        x=meses, y=saldo_desc,
        name=f"Saldo Descontado (TMA {_get_tma_str()}%)",
        mode="lines", line=dict(color="#6A9EC2", width=1.5, dash="dot"),
        hovertemplate="M%{x}<br>Descontado: R$ %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=meses, y=saldo, name="Saldo Acumulado",
        mode="lines", line=dict(color="#1E5F8A", width=3),
        hovertemplate="M%{x}<br>Saldo Acumulado: R$ %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[mes_exp], y=[exp_val], mode="markers",
        marker=dict(color="#C05454", size=11, symbol="circle", line=dict(color="#F5F3EE", width=1)),
        name=f"Exposicao maxima ({_fmt_m(exp_val)})",
        hovertemplate=f"Pico de exposicao: R$ {exp_val:,.0f}<extra></extra>",
    ))
    if pb:
        fig.add_trace(go.Scatter(
            x=[pb], y=[0], mode="markers",
            marker=dict(color="#3D8B5E", size=11, symbol="diamond", line=dict(color="#F5F3EE", width=1)),
            name=f"Payback M{pb}",
            hovertemplate=f"Payback no mes {pb}<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="rgba(0,0,0,0.15)", line_width=1)
    _adicionar_fases(fig, mes_inicio_obras, mes_termino)
    partes = [f"VPL: {_fmt_m(vpl)}"]
    if tir:
        partes.append(f"TIR: {tir * 100:.1f}% a.a.")
    fig.add_annotation(
        x=0.99, y=0.04, xref="paper", yref="paper",
        text="  |  ".join(partes), showarrow=False,
        font=dict(size=11, color="#1A1916"),
        bgcolor="#ECEAE4", bordercolor="#C4C1B8", borderwidth=1,
        xanchor="right", yanchor="bottom",
    )
    fig.update_layout(**_layout(
        title="Curva de Caixa — Saldo Acumulado",
        xaxis=dict(title="Mes", gridcolor="#D8D4C8", zerolinecolor="#C4C1B8"),
        yaxis=dict(title="R$", tickformat=".3s", gridcolor="#D8D4C8", zerolinecolor="#C4C1B8"),
        height=430,
    ))
    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)
    st.caption(
        "Area vermelha: capital em exposição. "
        "Area verde: zona de retorno. "
        "Linha pontilhada azul clara: saldo descontado pela TMA — quando chega ao zero, é o payback descontado."
    )


def _grafico_composicao_mensal(df, mes_inicio_obras: int, mes_termino: int) -> None:
    meses = df["Mes"].tolist()
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=meses, y=df["Receita Nominal Venda"], name="Receita Nominal",
        marker_color=_COR_NOMINAL, opacity=0.9,
        hovertemplate="M%{x}<br>Rec. Nominal: R$ %{y:,.0f}<extra></extra>",
    ), secondary_y=False)

    juros = df["Receita Financeira (Juros)"]
    if juros.sum() > 1:
        fig.add_trace(go.Bar(
            x=meses, y=juros, name="Juros (Rec. Financeira)",
            marker_color=_COR_JUROS, opacity=0.9,
            hovertemplate="M%{x}<br>Juros: R$ %{y:,.0f}<extra></extra>",
        ), secondary_y=False)

    for col, cor in _CORES_SAIDAS.items():
        if col not in df.columns:
            continue
        vals = df[col]
        if vals.sum() < 1:
            continue
        fig.add_trace(go.Bar(
            x=meses, y=-vals, name=col, marker_color=cor, opacity=0.85,
            hovertemplate=f"M%{{x}}<br>{col}: R$ %{{customdata:,.0f}}<extra></extra>",
            customdata=vals,
        ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=meses, y=df["Saldo do Mes"], name="Saldo do Mes",
        mode="lines", line=dict(color="#1A1916", width=1.5, dash="dot"), opacity=0.5,
        hovertemplate="M%{x}<br>Saldo: R$ %{y:,.0f}<extra></extra>",
    ), secondary_y=True)

    fig.add_hline(y=0, line_color="rgba(0,0,0,0.15)", line_width=1, secondary_y=False)
    _adicionar_fases(fig, mes_inicio_obras, mes_termino)
    layout = _layout(
        title="Composicao Mensal — Entradas e Saidas por Categoria",
        barmode="relative",
        xaxis=dict(title="Mes", gridcolor="#D8D4C8"),
        height=520,
        margin=dict(l=60, r=170, t=50, b=50),
        legend=dict(
            bgcolor="#F5F3EE",
            bordercolor="#D8D4C8",
            borderwidth=1,
            font=dict(size=10),
            orientation="v",
            xanchor="left",
            x=1.02,
            y=1,
            yanchor="top",
        ),
    )
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="R$", tickformat=".3s", secondary_y=False, gridcolor="#D8D4C8", zerolinecolor="#C4C1B8")
    fig.update_yaxes(title_text="Saldo Mensal", tickformat=".3s", secondary_y=True, showgrid=False, tickfont=dict(color="#5A5650"), title_font=dict(color="#5A5650"))
    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)
    st.caption(
        "Barras acima do zero: receitas. Barras abaixo do zero: saidas por categoria. "
        "Linha pontilhada branca: saldo liquido do mes."
    )


def _grafico_curvas_acumuladas(df, mes_inicio_obras: int, mes_termino: int) -> None:
    meses = df["Mes"].tolist()
    rec_acum = df["Total Entradas"].cumsum().tolist()
    sai_acum = df["Total Saidas"].cumsum().tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=meses + meses[::-1], y=rec_acum + sai_acum[::-1],
        fill="toself", fillcolor="rgba(52,211,153,0.07)",
        line=dict(width=0, color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip", name="_gap",
    ))
    fig.add_trace(go.Scatter(
        x=meses, y=sai_acum, name="Saidas Acumuladas",
        mode="lines", line=dict(color="#C05454", width=2.5),
        fill="tozeroy", fillcolor="rgba(192,84,84,0.06)",
        hovertemplate="M%{x}<br>Saidas Acum.: R$ %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=meses, y=rec_acum, name="Receitas Acumuladas",
        mode="lines", line=dict(color="#3D8B5E", width=2.5),
        hovertemplate="M%{x}<br>Receitas Acum.: R$ %{y:,.0f}<extra></extra>",
    ))
    crossover = None
    for i in range(1, len(meses)):
        if rec_acum[i] >= sai_acum[i] and rec_acum[i - 1] < sai_acum[i - 1]:
            crossover = meses[i]
            break
    if crossover is not None:
        fig.add_vline(
            x=crossover, line_dash="dash", line_color="rgba(61,139,94,0.6)", line_width=1.5,
            annotation_text=f"Break-even M{crossover}", annotation_position="top right",
            annotation_font=dict(size=10, color="#3D8B5E"),
        )
    _adicionar_fases(fig, mes_inicio_obras, mes_termino)
    fig.update_layout(**_layout(
        title="Curvas S — Receitas e Saidas Acumuladas",
        xaxis=dict(title="Mes", gridcolor="#D8D4C8"),
        yaxis=dict(title="R$ Acumulado", tickformat=".3s", gridcolor="#D8D4C8"),
        height=400,
    ))
    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)
    st.caption(
        "Linha verde: receitas totais acumuladas. "
        "Linha vermelha: saidas totais acumuladas. "
        "O ponto de cruzamento (break-even) e quando as receitas superam o total de saidas."
    )


def _pct_comercializado_mensal(projeto, horizonte: int) -> list[float]:
    pct: list[float] = [0.0] * (horizonte + 1)
    for faixa in projeto.receitas.curva_vendas:
        n = faixa.mes_fim - faixa.mes_inicio + 1
        pct_por_mes = faixa.percentual_estoque / n if n > 0 else faixa.percentual_estoque
        for m in range(faixa.mes_inicio, min(faixa.mes_fim + 1, horizonte + 1)):
            pct[m] += pct_por_mes
    return pct


def _grafico_obras_vs_comercializacao(df, projeto, horizonte: int, mes_termino: int) -> None:
    meses = df["Mes"].tolist()
    n = len(meses)
    pct_mensal = _pct_comercializado_mensal(projeto, horizonte)
    pct_acum = list(np.cumsum(pct_mensal[:n]))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=meses, y=df["Obras"], name="Desembolso Obras (Mensal)",
        marker_color="#C49A3C", opacity=0.85,
        hovertemplate="M%{x}<br>Obras: R$ %{y:,.0f}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=meses, y=pct_acum, name="% Comercializado (Acumulado)",
        mode="lines", line=dict(color="#3D8B5E", width=2.5),
        hovertemplate="M%{x}<br>Comercializado: %{y:.1f}%%<extra></extra>",
    ), secondary_y=True)
    if meses:
        fig.add_trace(go.Scatter(
            x=[meses[0], meses[-1]], y=[100.0, 100.0],
            name="100% vendido", mode="lines",
            line=dict(color="#3D8B5E", width=1, dash="dot"), hoverinfo="skip",
        ), secondary_y=True)
    if mes_termino > 0:
        fig.add_vline(
            x=mes_termino, line_dash="dash", line_color="rgba(43,80,168,0.5)", line_width=1.5,
            annotation_text=f"Fim Obras M{mes_termino}", annotation_position="top right",
            annotation_font=dict(color="#2B50A8"),
        )
    fig.update_layout(**_layout(
        title="Desembolso de Obras vs % Empreendimento Comercializado",
        xaxis=dict(title="Mes", gridcolor="#D8D4C8", zerolinecolor="#C4C1B8"),
        height=400,
    ))
    fig.update_yaxes(title_text="Desembolso de Obras (R$)", tickformat=".3s", secondary_y=False, gridcolor="#D8D4C8", zerolinecolor="#C4C1B8")
    fig.update_yaxes(
        title_text="% Comercializado", secondary_y=True, showgrid=False,
        tickformat=".0f", ticksuffix="%", range=[0, 110],
        tickfont=dict(color="#3D8B5E"), title_font=dict(color="#3D8B5E"),
    )
    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)
    st.caption(
        "Barras (amarelo): desembolso mensal de obras. "
        "Linha (verde): % do empreendimento comercializado acumulado. "
        "Quando a linha verde sobe mais rapido que as barras, as vendas estao financiando as obras."
    )


# =====================================================================
# TABELA MENSAL — COM PERIODICIDADE MENSAL / TRIMESTRAL / ANUAL
# =====================================================================

def _agregar_df(df, periodo: str):
    """Agrega o dataframe de fluxo mensal em trimestres ou anos."""
    if periodo == "Mensal":
        return df.copy()

    n = 3 if periodo == "Trimestral" else 12
    label_prefix = "T" if periodo == "Trimestral" else "Ano "

    cols_acum = {"Saldo Acumulado", "Saldo Descontado Acumulado"}
    cols_val = [c for c in df.columns if c != "Mes"]
    cols_sum = [c for c in cols_val if c not in cols_acum]
    cols_last = [c for c in cols_val if c in cols_acum]

    col_idx = {c: i for i, c in enumerate(df.columns)}
    linhas = df.values.tolist()

    grupos: list[dict] = []
    i = 0
    periodo_idx = 1
    while i < len(linhas):
        chunk = linhas[i:i + n]
        row: dict = {"Mes": f"{label_prefix}{periodo_idx}"}
        for c in cols_sum:
            if c in col_idx:
                row[c] = sum(r[col_idx[c]] for r in chunk)
        for c in cols_last:
            if c in col_idx:
                row[c] = chunk[-1][col_idx[c]]
        if "Total Entradas" in row and "Total Saidas" in row:
            row["Saldo do Mes"] = row["Total Entradas"] - row["Total Saidas"]
        grupos.append(row)
        i += n
        periodo_idx += 1

    return pd.DataFrame(grupos)


def _fmt_int_brl(v) -> str:
    try:
        n = int(round(float(v) / 1000))
        if n == 0:
            return ""
        s = f"{abs(n):,}".replace(",", ".")
        return f"-{s}" if n < 0 else s
    except Exception:
        return ""


def _agrupar_marcos_por_periodo(
    marcos: dict[int, str], n: int, prefix: str, meses: list
) -> dict[str, str]:
    """Maps monthly marcos {mes: label} to period labels {period_col: labels}."""
    result: dict[str, str] = {}
    i = 0
    periodo_idx = 1
    while i < len(meses):
        chunk = meses[i : i + n]
        labels = [marcos[m] for m in chunk if m in marcos]
        if labels:
            result[f"{prefix}{periodo_idx}"] = " / ".join(labels)
        i += n
        periodo_idx += 1
    return result


_MES_NOMES_CAL = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]


def _cal_label_from_inicio(mes_int: int, inicio) -> str:
    """Converte offset de mes inteiro em 'set/26', dado o inicio do projeto."""
    try:
        _total = inicio.month - 1 + mes_int
        _y = inicio.year + _total // 12
        _mo = _total % 12 + 1
        return f"{_MES_NOMES_CAL[_mo - 1]}/{str(_y)[2:]}"
    except Exception:
        return f"M{mes_int}"


def _transpor_df_formatado(df, marcos: dict[str, str] | None = None, inicio_projeto=None):
    cols_val = [c for c in df.columns if c != "Mes"]
    df_m = df[df[cols_val].abs().sum(axis=1) > 0].copy()
    df_m = df_m.set_index("Mes")

    def _fmt_mes_label(mes) -> str:
        if inicio_projeto is not None:
            try:
                return _cal_label_from_inicio(int(mes), inicio_projeto)
            except Exception:
                pass
        try:
            return f"M{int(mes)}"
        except (ValueError, TypeError):
            return str(mes)

    df_m.index = [_fmt_mes_label(mes) for mes in df_m.index]
    df_t = df_m.T
    df_t = df_t[(df_t.abs() > 0.5).any(axis=1)]
    df_fmt = df_t.copy()
    for col in df_fmt.columns:
        df_fmt[col] = df_fmt[col].map(_fmt_int_brl)
    df_fmt.index.name = "Item"

    # Prepend Marcos row when provided (keys are column labels)
    if marcos:
        marcos_row = {col: marcos.get(col, "") for col in df_fmt.columns}
        if any(marcos_row.values()):
            df_marcos = pd.DataFrame([marcos_row], index=pd.Index(["Marcos"], name="Item"))
            df_fmt = pd.concat([df_marcos, df_fmt])

    return df_fmt


def _estilizar_tabela(df_fmt):
    def row_style(row):
        nome = row.name
        # Linha de marcos: estilo especial ocre, italic, centralizado
        if nome == "Marcos":
            return [
                "background-color: #EFF6FF; color: #1E3A8A; font-size: 10px; "
                "text-align: center; font-style: italic; "
                "padding: 2px 4px; border: 1px solid #D8D4C8;"
            ] * len(row)
        bg = _BG_LINHAS.get(nome, "#F5F3EE")
        bold = "bold" if nome in _NEGRITO_LINHAS else "normal"
        # Linhas de saldo: cor do texto depende do sinal de cada celula
        if nome in _SALDO_LINHAS:
            styles = []
            for v in row:
                if isinstance(v, str) and v.startswith("-"):
                    cor_texto = "#C05454"
                elif isinstance(v, str) and v != "":
                    cor_texto = "#2E6B47"
                else:
                    cor_texto = "#1A1916"
                styles.append(
                    f"background-color: {bg}; font-weight: {bold}; "
                    f"color: {cor_texto}; font-size: 12px; text-align: right; "
                    f"padding: 2px 8px; border: 1px solid #D8D4C8;"
                )
            return styles
        return [
            f"background-color: {bg}; font-weight: {bold}; "
            f"color: #1A1916; font-size: 12px; text-align: right; "
            f"padding: 2px 8px; border: 1px solid #D8D4C8;"
        ] * len(row)

    styler = (
        df_fmt.style
        .apply(row_style, axis=1)
        .set_table_styles([
            {"selector": "th", "props": [
                ("background-color", "#ECEAE4"), ("color", "#1A1916"),
                ("text-align", "center"), ("padding", "3px 8px"),
                ("font-size", "11px"), ("border", "1px solid #D8D4C8"),
            ]},
            {"selector": "th.row_heading", "props": [
                ("text-align", "left"), ("background-color", "#F5F3EE"),
                ("min-width", "210px"), ("font-size", "11px"),
                ("padding", "2px 8px"), ("border", "1px solid #D8D4C8"),
            ]},
            {"selector": "th.col_heading", "props": [
                ("min-width", "70px"), ("max-width", "100px"),
            ]},
        ])
    )
    return styler


@st.dialog("Fluxo de Caixa — Visao Completa", width="large")
def _dlg_fluxo_tela_cheia(df_agg, marcos_labels: dict[str, str] | None = None, inicio_projeto=None) -> None:
    df_t = _transpor_df_formatado(df_agg, marcos=marcos_labels, inicio_projeto=inicio_projeto)
    st.dataframe(_estilizar_tabela(df_t), use_container_width=True, height=700)
    st.caption(f"Valores em R$ mil.   {len(df_t)} linhas · {len(df_t.columns)} periodos com movimentacao.")


_LINHAS_COMPACTAS = frozenset({
    "Receita Nominal Venda", "Total Entradas", "Total Saidas",
    "Saldo do Mes", "Saldo Acumulado", "Saldo Descontado Acumulado",
    "Marcos",
})


def _tabela_fluxo_mensal(df) -> None:
    st.markdown("---")

    col_h, col_p, col_c, col_b = st.columns([2, 2, 1, 1])
    with col_h:
        st.markdown("#### Tabela de Fluxo de Caixa")
    with col_p:
        periodo = st.radio(
            "Periodicidade",
            ["Mensal", "Trimestral", "Anual"],
            index=1,
            horizontal=True,
            key="tabela_fluxo_periodo_tipo",
            label_visibility="collapsed",
        )
    with col_c:
        compacto = st.toggle("Compacto", value=False, key="tabela_fluxo_compacto",
                             help="Exibe apenas as linhas de totais e saldo, ocultando o detalhe por categoria.")
    with col_b:
        if st.button("⛶ Tela cheia", key="btn_tela_cheia_fluxo", width="stretch"):
            _dlg_fluxo_tela_cheia(
                _agregar_df(df, periodo),
                st.session_state.get("_fluxo_marcos_labels_cache"),
                inicio_projeto=st.session_state.get("_fluxo_inicio_projeto_cache"),
            )

    df_agg = _agregar_df(df, periodo)

    # Compute marcos e inicio_projeto para labels de calendario
    _marcos_labels: dict[str, str] | None = None
    _inicio_projeto = None
    try:
        projeto = get_projeto()
        _inicio_projeto = projeto.terreno.datas.inicio_projeto
        _marcos_raw = marcos_projeto(projeto)
        meses_list = [int(m) for m in df["Mes"].tolist()]
        if periodo == "Mensal":
            # Usa datas do calendario como chave para coincidir com os headers
            _marcos_labels = {
                _cal_label_from_inicio(k, _inicio_projeto): v
                for k, v in _marcos_raw.items()
            }
        elif periodo == "Trimestral":
            _marcos_labels = _agrupar_marcos_por_periodo(_marcos_raw, 3, "T", meses_list)
        else:
            _marcos_labels = _agrupar_marcos_por_periodo(_marcos_raw, 12, "Ano ", meses_list)
    except Exception:
        _marcos_labels = None

    st.session_state["_fluxo_marcos_labels_cache"] = _marcos_labels
    st.session_state["_fluxo_inicio_projeto_cache"] = _inicio_projeto if periodo == "Mensal" else None

    if periodo == "Mensal":
        _todos_meses = [int(m) for m in df["Mes"].tolist()]
        if len(_todos_meses) >= 2:
            _m_min, _m_max = _todos_meses[0], _todos_meses[-1]
            col_sl, _ = st.columns([3, 2])
            with col_sl:
                _sel = st.slider(
                    "Periodo exibido (meses)",
                    min_value=_m_min,
                    max_value=_m_max,
                    value=(_m_min, _m_max),
                    key="tabela_fluxo_periodo",
                )
            df_vis = df_agg[(df_agg["Mes"] >= _sel[0]) & (df_agg["Mes"] <= _sel[1])]
        else:
            df_vis = df_agg
    else:
        df_vis = df_agg

    # Passa inicio_projeto apenas no modo mensal (para labels de calendario)
    _inicio_para_fmt = _inicio_projeto if periodo == "Mensal" else None
    df_t = _transpor_df_formatado(df_vis, marcos=_marcos_labels, inicio_projeto=_inicio_para_fmt)
    if compacto:
        df_t = df_t[df_t.index.isin(_LINHAS_COMPACTAS)]
    altura = min(580, (len(df_t) + 1) * 36 + 38)
    st.dataframe(_estilizar_tabela(df_t), use_container_width=True, height=altura)
    legenda_periodo = {"Mensal": "meses", "Trimestral": "trimestres", "Anual": "anos"}[periodo]
    st.caption(
        "Valores em **R$ mil**.   "
        f"{len(df_t)} linhas · {len(df_t.columns)} {legenda_periodo} com movimentacao."
    )


# =====================================================================
# PREVIEW DE CUSTO FINANCEIRO (quando financiamento inativo)
# =====================================================================

def _renderizar_preview_financiamento(df, resultado, projeto) -> None:
    """Estima o custo financeiro sem alterar o fluxo de caixa calculado."""
    taxa = projeto.financiamento.taxa_juros_am
    if taxa <= 0:
        return
    try:
        fluxo_base = df["Saldo do Mes"].to_numpy()
        sim = simular_financiamento(fluxo_base, projeto.financiamento, resultado.horizonte)
        custo_proj = float(sim["juros_banco"].sum())
        pico_saldo = float(sim["saldo_devedor"].max())
        mes_pico = int(np.argmax(sim["saldo_devedor"]))

        if custo_proj < 1 and pico_saldo < 1:
            return

        taxa_aa = (1 + taxa / 100) ** 12 - 1
        st.markdown(
            f'<div style="background:rgba(43,80,168,0.07);border-left:3px solid #4A7FA5;'
            f'padding:10px 14px;border-radius:0 6px 6px 0;margin:16px 0 4px 0;">'
            f'<b>Estimativa de custo financeiro</b> '
            f'<span style="font-size:12px;color:#6B7280;">— se usar linha de crédito a '
            f'{taxa:.2f}% a.m. ({taxa_aa * 100:.1f}% a.a.). '
            f'Fluxo de caixa não é alterado.</span></div>',
            unsafe_allow_html=True,
        )
        kpis_fin = [
            {
                "label": "Juros Estimados (CCB/CCE)",
                "valor": _fmt_m(custo_proj),
                "sub": "Total do projeto sem limite de crédito",
                "cor": "vermelho",
            },
            {
                "label": "Pico do Saldo Devedor",
                "valor": _fmt_m(pico_saldo),
                "sub": f"No mês M{mes_pico}",
                "cor": "neutro",
            },
            {
                "label": "Taxa Configurada",
                "valor": f"{taxa:.2f}% a.m.",
                "sub": f"{taxa_aa * 100:.1f}% a.a. — ajuste em Financiamento (sidebar)",
                "cor": "neutro",
            },
        ]
        renderizar_grade_kpis(kpis_fin)
        st.caption(
            "Estimativa informativa gerada com a taxa configurada em Financiamento e sem limite de crédito. "
            "Ative o **Financiamento** (sidebar → Avançado) para incluir o custo no fluxo real."
        )
    except Exception:
        pass


# =====================================================================
# RENDERIZADOR PRINCIPAL
# =====================================================================

def renderizar() -> None:
    cabecalho_aba(
        8,
        "Resultado do Projeto",
        "Indicadores, gráficos e análise de viabilidade.",
    )

    projeto = get_projeto()
    resultado = get_resultado()

    # Botao PDF no canto superior direito
    _, col_pdf = st.columns([5, 1])
    with col_pdf:
        if resultado is not None:
            try:
                nome_padrao = (
                    projeto.terreno.info.nome.lower()
                    .replace(" ", "_").replace("/", "_")
                )
                html_bytes = gerar_relatorio_html(projeto, resultado).encode("utf-8")
                st.download_button(
                    "PDF",
                    data=html_bytes,
                    file_name=f"relatorio_{nome_padrao}.html",
                    mime="text/html",
                    width="stretch",
                    help="Baixa HTML. Abra no navegador e pressione Ctrl+P para salvar como PDF.",
                )
            except Exception:
                pass

    # Saude do modelo
    _renderizar_saude(projeto)

    # Linha do tempo
    renderizar_linha_tempo_trilhas(projeto)

    # Se nao calculado: estimativas pre-calculo e hint
    if resultado is None:
        _renderizar_pre_calc(projeto)
        return

    r = resultado.resumo
    ind = resultado.indicadores
    df = resultado.fluxo_caixa
    mes_termino = r.get("mes_termino_obras", 0)

    try:
        mes_inicio_obras = meses_entre(
            projeto.terreno.datas.inicio_projeto,
            projeto.terreno.datas.inicio_obras,
        )
    except Exception:
        mes_inicio_obras = 0

    # Badge de veredito
    _renderizar_badge_veredito(r, ind, projeto)

    # KPIs hierárquicos: 3 headline + 4 secundários
    _kpis_topo(r, ind, projeto)

    # Preview de custo financeiro quando financiamento nao esta ativo
    if not r.get("financiamento_ativo"):
        _renderizar_preview_financiamento(df, resultado, projeto)

    # Aviso de reajustes — colapsado por padrão, aparece uma vez acima dos tabs
    try:
        if not projeto.reajustes.ativo:
            with st.expander("Reajustes monetários não ativados", expanded=False):
                st.markdown(
                    "O custo de obras pode estar **subestimado** sem a correção pelo INCC ao longo do prazo de construção.  \n"
                    "Configure em **Reajustes** (sidebar → Avançado → Reajustes) para simular o impacto da inflação setorial."
                )
    except Exception:
        pass

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Curva de Caixa",
        "Mensal e Receitas",
        "Obras e Vendas",
        "DRE",
    ])

    with tab1:
        st.caption("Quando o projeto precisa de capital e quando começa a retornar — saldo acumulado ao longo do tempo.")
        _grafico_curva_caixa(df, ind, mes_inicio_obras, mes_termino)

    with tab2:
        st.caption("Entradas e saídas mês a mês por categoria — identifique picos de desembolso e recebimento.")
        _grafico_composicao_mensal(df, mes_inicio_obras, mes_termino)
        st.markdown("---")
        st.caption("Receitas e saídas acumuladas — o projeto fica positivo quando a linha verde ultrapassa a vermelha.")
        _grafico_curvas_acumuladas(df, mes_inicio_obras, mes_termino)

    with tab3:
        st.caption("Desembolso de obras x velocidade de vendas — sincronize os picos para otimizar o caixa.")
        _grafico_obras_vs_comercializacao(df, projeto, resultado.horizonte, mes_termino)

    with tab4:
        st.caption("DRE — Demonstrativo de Resultado em cascata: VGV → deduções → custos → resultado.")
        _renderizar_cascata_dre(r)
        st.markdown("---")
        _renderizar_cards_margem(r, ind)
        st.markdown("---")
        _renderizar_nominal_vs_financeiro(r)
        st.markdown("---")
        with st.expander("Composição de Saídas por Categoria", expanded=False):
            st.caption("Participação de cada categoria de custo no total de saídas.")
            _renderizar_composicao_saidas(r)

    # Tabela de fluxo com seletor de periodicidade
    _tabela_fluxo_mensal(df)
