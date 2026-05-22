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
from ...io_projeto.exportar_html import gerar_relatorio_html


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
    "Receita Nominal Venda":      "#EEF6F0",
    "Receita Financeira (Juros)": "#EEF6F0",
    "Total Entradas":             "#D4EAD9",
    "Aquisicao Terreno":          "#FBF0F0",
    "Cartorio":                   "#FBF0F0",
    "Obras":                      "#FBF0F0",
    "Projetos":                   "#FBF0F0",
    "Licenciamento":              "#FBF0F0",
    "Marketing":                  "#FBF0F0",
    "Outros Desenvolvimento":     "#FBF0F0",
    "Administracao":              "#FBF0F0",
    "Comissao":                   "#FBF0F0",
    "Impostos":                   "#FBF0F0",
    "Permuta Financeira":         "#FBF0F0",
    "Total Saidas":               "#F5D0D0",
    "Saldo do Mes":               "#F5F3EE",
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
    if av >= 1_000_000:
        return f"R$ {v / 1_000_000:.1f}M".replace(".", ",")
    if av >= 1_000:
        return f"R$ {v / 1_000:.0f}k"
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

    renderizar_saude_modelo(checks)


# =====================================================================
# PRE-CALC ESTIMATIVAS (ABA 0 — D3)
# =====================================================================

def _renderizar_pre_calc(projeto) -> None:
    st.markdown(
        '<div style="background:rgba(30,58,138,0.08);border-left:3px solid #2B50A8;'
        'padding:8px 12px;border-radius:0 4px 4px 0;font-size:12px;color:#1E3A8A;'
        'margin:12px 0;">'
        '⚠️ Estimativas antes do calculo — dados precisos apos Calcular</div>',
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
        "💡 Clique em **'Calcular fluxo'** nas Ações do projeto (sidebar) "
        "para ver os indicadores completos.  \n"
        "🏡 Lembre-se de configurar a **aquisição do terreno** no Módulo 9 "
        "antes de calcular."
    )


# =====================================================================
# KPIs TOPO — VERSAO COMPLETA COM VEREDITO TIR/TMA (ABA 0)
# =====================================================================

def _kpis_topo(r: dict, ind: dict, projeto=None) -> None:
    tma = projeto.parametros.tma_anual if projeto else 15.0

    vgv_disponivel = r["vgv_vendavel"]
    lucro = r["lucro_liquido"]
    vpl = ind["vpl"]
    tir = ind.get("tir_anual")
    exp_max = abs(ind["exposicao_maxima"])
    mes_exp = ind["mes_exposicao_maxima"]
    pb = ind.get("payback_simples_meses")
    margem = (lucro / vgv_disponivel * 100) if vgv_disponivel > 0 else 0
    horizonte = r.get("horizonte_meses", 0)
    custo_total = r["total_saidas"]
    pe = (custo_total / vgv_disponivel * 100) if vgv_disponivel > 0 else 0

    if tir is not None:
        tir_pct = tir * 100
        if tir_pct >= tma:
            tir_cor = "verde"
            tir_sub = f"✅ Acima da TMA ({tma:.0f}% a.a.)"
        elif tir_pct >= tma * 0.85:
            tir_cor = "neutro"
            tir_sub = f"⚠️ Proxima da TMA ({tma:.0f}% a.a.)"
        else:
            tir_cor = "vermelho"
            tir_sub = f"❌ Abaixo da TMA ({tma:.0f}% a.a.)"
    else:
        tir_cor = "neutro"
        tir_sub = ""

    vpl_cor = "verde" if vpl > 0 else "vermelho"
    vpl_sub = "✅ Projeto viavel" if vpl > 0 else "❌ Projeto inviavel"
    pb_valor = f"Mes {pb}" if pb else "n/d"
    pb_sub = f"de {horizonte} meses no projeto" if (pb and horizonte > 0) else ""

    kpis = [
        {"label": "VGV Disponivel",       "valor": _fmt_m(vgv_disponivel), "cor": "neutro"},
        {"label": "Resultado Bruto",      "valor": _fmt_m(lucro),          "cor": "verde" if lucro > 0 else "vermelho"},
        {"label": "Margem Bruta",         "valor": f"{margem:.2f}%",       "cor": "verde" if margem > 0 else "vermelho"},
        {"label": "TIR Anual",            "valor": f"{tir*100:.2f}%" if tir else "n/d", "sub": tir_sub, "cor": tir_cor},
        {"label": f"VPL ({tma:.0f}% a.a.)", "valor": _fmt_m(vpl),         "sub": vpl_sub, "cor": vpl_cor},
        {"label": "Pico de Exposicao",    "valor": _fmt_m(-exp_max),       "sub": f"Mes {mes_exp}", "cor": "vermelho"},
        {"label": "Payback",              "valor": pb_valor,               "sub": pb_sub, "cor": "neutro"},
        {"label": "Ponto de Equilibrio",  "valor": f"{pe:.2f}%",           "sub": "do VGV", "cor": "neutro"},
    ]

    renderizar_grade_kpis(kpis)


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
        {"label": "Margem s/ VGV Vendavel",       "valor": formatar_pct(margem_vv) if margem_vv is not None else "n/d",    "cor": cor_margem(margem_vv)},
        {"label": "Margem s/ VGV Bruto",          "valor": formatar_pct(margem_vb) if margem_vb is not None else "n/d",    "cor": cor_margem(margem_vb)},
        {"label": "Multiplicador (Lucro/Exp.)",   "valor": f"{multiplicador:.2f}x".replace(".", ",") if multiplicador else "n/d", "cor": "verde" if (multiplicador and multiplicador > 1) else "neutro"},
        {"label": "TIR Anual",                    "valor": formatar_pct(tir) if tir is not None else "n/d",                "cor": "verde" if (tir and tir > 0.10) else "neutro"},
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
        st.plotly_chart(fig, use_container_width=True)

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
            annotation_text="Pre-obra", annotation_position="top left",
            annotation_font=dict(size=9, color="#4A7FA5"),
        )
    if mes_termino > mes_inicio_obras:
        fig.add_vrect(
            x0=mes_inicio_obras, x1=mes_termino,
            fillcolor="rgba(43,80,168,0.07)", line_width=0,
            annotation_text="Obras", annotation_position="top left",
            annotation_font=dict(size=9, color="#2B50A8"),
        )
    if mes_termino > 0:
        fig.add_vline(
            x=mes_termino, line_dash="dash",
            line_color="rgba(43,80,168,0.50)", line_width=1,
            annotation_text=f"Fim obras M{mes_termino}", annotation_position="top right",
            annotation_font=dict(size=9, color="#2B50A8"),
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
        x=[mes_exp], y=[exp_val], mode="markers+text",
        marker=dict(color="#C05454", size=11, symbol="circle", line=dict(color="#F5F3EE", width=1)),
        text=[f"  Pico: {_fmt_m(exp_val)}"], textposition="middle right",
        textfont=dict(color="#C05454", size=10), showlegend=False,
        hovertemplate=f"Pico de exposicao: R$ {exp_val:,.0f}<extra></extra>",
    ))
    if pb:
        fig.add_trace(go.Scatter(
            x=[pb], y=[0], mode="markers+text",
            marker=dict(color="#3D8B5E", size=11, symbol="diamond", line=dict(color="#F5F3EE", width=1)),
            text=[f"  Payback M{pb}"], textposition="top right",
            textfont=dict(color="#3D8B5E", size=10), showlegend=False,
            hovertemplate=f"Payback no mes {pb}<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="rgba(0,0,0,0.15)", line_width=1)
    _adicionar_fases(fig, mes_inicio_obras, mes_termino)
    partes = [f"VPL: {_fmt_m(vpl)}"]
    if tir:
        partes.append(f"TIR: {formatar_pct(tir)} a.a.")
    fig.add_annotation(
        x=0.99, y=0.04, xref="paper", yref="paper",
        text="   ".join(partes), showarrow=False,
        font=dict(size=11, color="#1A1916"),
        bgcolor="#ECEAE4", bordercolor="#C4C1B8", borderwidth=1, align="right",
    )
    fig.update_layout(**_layout(
        title="Curva de Caixa — Saldo Acumulado",
        xaxis=dict(title="Mes", gridcolor="#D8D4C8", zerolinecolor="#C4C1B8"),
        yaxis=dict(title="R$", gridcolor="#D8D4C8", zerolinecolor="#C4C1B8"),
        height=430,
    ))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "🔴 Area vermelha: capital em exposicao. "
        "🟢 Area verde: zona de retorno. "
        "Linha pontilhada azul clara: saldo descontado pela TMA — quando chega ao zero, e o payback descontado."
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
    fig.update_layout(**_layout(
        title="Composicao Mensal — Entradas e Saidas por Categoria",
        barmode="relative",
        xaxis=dict(title="Mes", gridcolor="#D8D4C8"),
        height=500,
    ))
    fig.update_yaxes(title_text="R$ (Entradas / Saidas)", secondary_y=False, gridcolor="#D8D4C8", zerolinecolor="#C4C1B8")
    fig.update_yaxes(title_text="Saldo Mensal (R$)", secondary_y=True, showgrid=False, tickfont=dict(color="#5A5650"), title_font=dict(color="#5A5650"))
    st.plotly_chart(fig, use_container_width=True)
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
        yaxis=dict(title="R$ Acumulado", gridcolor="#D8D4C8"),
        height=400,
    ))
    st.plotly_chart(fig, use_container_width=True)
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
    fig.update_yaxes(title_text="Desembolso de Obras (R$)", secondary_y=False, gridcolor="#D8D4C8", zerolinecolor="#C4C1B8")
    fig.update_yaxes(
        title_text="% Comercializado", secondary_y=True, showgrid=False,
        tickformat=".0f", ticksuffix="%", range=[0, 110],
        tickfont=dict(color="#3D8B5E"), title_font=dict(color="#3D8B5E"),
    )
    st.plotly_chart(fig, use_container_width=True)
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


def _transpor_df_formatado(df, marcos: dict[int, str] | None = None):
    cols_val = [c for c in df.columns if c != "Mes"]
    df_m = df[df[cols_val].abs().sum(axis=1) > 0].copy()
    df_m = df_m.set_index("Mes")

    def _fmt_mes_label(mes) -> str:
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

    # Prepend Marcos row when provided
    if marcos:
        marcos_row: dict[str, str] = {}
        for col in df_fmt.columns:
            try:
                mes_idx = int(col[1:])  # strip leading "M"
            except (ValueError, TypeError):
                mes_idx = -1
            marcos_row[col] = marcos.get(mes_idx, "")
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
def _dlg_fluxo_tela_cheia(df_agg) -> None:
    df_t = _transpor_df_formatado(df_agg, marcos=None)
    st.dataframe(_estilizar_tabela(df_t), use_container_width=True, height=700)
    st.caption(f"Valores em R$ mil.   {len(df_t)} linhas · {len(df_t.columns)} periodos com movimentacao.")


def _tabela_fluxo_mensal(df) -> None:
    st.markdown("---")

    col_h, col_p, col_b = st.columns([3, 2, 1])
    with col_h:
        st.markdown("#### Tabela de Fluxo de Caixa")
    with col_p:
        periodo = st.radio(
            "Periodicidade",
            ["Mensal", "Trimestral", "Anual"],
            horizontal=True,
            key="tabela_fluxo_periodo_tipo",
            label_visibility="collapsed",
        )
    with col_b:
        if st.button("⛶ Tela cheia", key="btn_tela_cheia_fluxo", use_container_width=True):
            _dlg_fluxo_tela_cheia(_agregar_df(df, periodo))

    df_agg = _agregar_df(df, periodo)

    # Compute marcos only for Mensal view
    _marcos: dict[int, str] | None = None
    if periodo == "Mensal":
        try:
            projeto = get_projeto()
            _marcos = marcos_projeto(projeto)
        except Exception:
            _marcos = None

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

    df_t = _transpor_df_formatado(df_vis, marcos=_marcos)
    altura = min(580, (len(df_t) + 1) * 36 + 38)
    st.dataframe(_estilizar_tabela(df_t), use_container_width=True, height=altura)
    legenda_periodo = {"Mensal": "meses", "Trimestral": "trimestres", "Anual": "anos"}[periodo]
    st.caption(
        "Valores em **R$ mil**.   "
        f"{len(df_t)} linhas · {len(df_t.columns)} {legenda_periodo} com movimentacao."
    )


# =====================================================================
# RENDERIZADOR PRINCIPAL
# =====================================================================

def renderizar() -> None:
    cabecalho_aba(
        8,
        "Dashboard",
        "Visao geral, indicadores e graficos interativos do projeto.",
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
                    "📄 PDF",
                    data=html_bytes,
                    file_name=f"relatorio_{nome_padrao}.html",
                    mime="text/html",
                    use_container_width=True,
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

    # KPI grid completo (versao Visao Geral)
    _kpis_topo(r, ind, projeto)

    # Aviso de reajustes nao ativados
    try:
        if not projeto.reajustes.ativo:
            st.markdown(
                '<div style="background:rgba(74,127,165,0.08);border-left:3px solid #4A7FA5;'
                'padding:8px 12px;border-radius:0 4px 4px 0;font-size:12px;color:#2E5F80;'
                'margin:16px 0 0 0;">'
                '💡 <b>Reajustes monetários não ativados</b> — o custo de obras pode estar '
                'subestimado sem a correção pelo INCC. Configure no '
                '<b>Módulo 14 — Reajustes</b>.</div>',
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Curva de Caixa",
        "📊 Composicao Mensal",
        "〜 Receitas vs Saidas",
        "🏗 Obras e Vendas",
        "📋 DRE",
        "🍩 Composicao de Saidas",
    ])

    with tab1:
        st.caption("Quando o projeto precisa de capital e quando começa a retornar — saldo acumulado ao longo do tempo.")
        _grafico_curva_caixa(df, ind, mes_inicio_obras, mes_termino)

    with tab2:
        st.caption("Entradas e saídas mês a mês por categoria — identifique picos de desembolso e recebimento.")
        _grafico_composicao_mensal(df, mes_inicio_obras, mes_termino)

    with tab3:
        st.caption("Receitas e saídas acumuladas — o projeto fica positivo quando a linha verde ultrapassa a vermelha.")
        _grafico_curvas_acumuladas(df, mes_inicio_obras, mes_termino)

    with tab4:
        st.caption("Desembolso de obras x velocidade de vendas — sincronize os picos para otimizar o caixa.")
        _grafico_obras_vs_comercializacao(df, projeto, resultado.horizonte, mes_termino)

    with tab5:
        st.caption("DRE — Demonstrativo de Resultado em cascata: VGV → deduções → custos → resultado.")
        _renderizar_cascata_dre(r)
        st.markdown("---")
        _renderizar_cards_margem(r, ind)
        st.markdown("---")
        _renderizar_nominal_vs_financeiro(r)

    with tab6:
        st.caption("Participação de cada categoria de custo no total de saídas.")
        _renderizar_composicao_saidas(r)

    # Tabela de fluxo com seletor de periodicidade
    _tabela_fluxo_mensal(df)
