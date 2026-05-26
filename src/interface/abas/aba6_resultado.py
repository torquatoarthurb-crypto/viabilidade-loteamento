"""
Aba 6 — Resultado Estatico (DRE em Cascata).

Exibe o Demonstrativo de Resultado do Exercicio em formato cascata:
VGV Bruto → deducoes → Receita Total → Custos (por categoria) → Resultado Bruto.
Inclui grafico de composicao das saidas e comparativo nominal vs financeiro.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from ..helpers import (
    cabecalho_aba,
    formatar_brl,
    formatar_pct,
    get_resultado,
    renderizar_calcular_cta,
)
from ..tema_componentes import renderizar_grade_kpis


def renderizar() -> None:
    cabecalho_aba(
        6,
        "Resultado Estatico",
        "DRE — Demonstrativo de Resultado do Exercicio consolidado do projeto.",
    )

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    r = resultado.resumo
    ind = resultado.indicadores

    _renderizar_cascata_dre(r)
    _renderizar_cards_margem(r, ind)

    st.markdown("---")
    _renderizar_composicao_saidas(r)

    st.markdown("---")
    _renderizar_nominal_vs_financeiro(r)


# =====================================================================
# DRE EM CASCATA
# =====================================================================

def _renderizar_cascata_dre(r: dict) -> None:
    vgv_bruto = r["vgv_bruto"]
    vgv_vendavel = r["vgv_vendavel"]
    permuta_fisica = vgv_bruto - vgv_vendavel

    def pct_vv(v: float) -> str:
        if vgv_vendavel > 0:
            return formatar_pct(v / vgv_vendavel)
        return "—"

    def pct_vb(v: float) -> str:
        if vgv_bruto > 0:
            return formatar_pct(v / vgv_bruto)
        return "—"

    def td(texto: str, negrito: bool = False) -> str:
        estilo = " font-weight:700;" if negrito else ""
        return f'<td style="{estilo}">{texto}</td>'

    def linha(classe: str, cols: list[str]) -> str:
        cells = "".join(f"<td>{c}</td>" for c in cols)
        return f'<tr class="{classe}">{cells}</tr>'

    def separador() -> str:
        return '<tr class="dre-row-separator"><td colspan="4"></td></tr>'

    def linha_header(label: str, valor: float) -> str:
        return (
            f'<tr class="dre-row-header">'
            f'<td>{label}</td>'
            f'<td>{formatar_brl(valor)}</td>'
            f'<td>{pct_vv(valor)}</td>'
            f'<td>{pct_vb(valor)}</td>'
            f'</tr>'
        )

    def linha_deducao(label: str, valor: float) -> str:
        if valor == 0:
            return ""
        return (
            f'<tr class="dre-row-deduction">'
            f'<td>&nbsp;&nbsp;&nbsp;{label}</td>'
            f'<td>({formatar_brl(valor)})</td>'
            f'<td>({pct_vv(valor)})</td>'
            f'<td>({pct_vb(valor)})</td>'
            f'</tr>'
        )

    def linha_adicao(label: str, valor: float) -> str:
        if valor == 0:
            return ""
        return (
            f'<tr class="dre-row-addition">'
            f'<td>&nbsp;&nbsp;&nbsp;{label}</td>'
            f'<td>+ {formatar_brl(valor)}</td>'
            f'<td>+ {pct_vv(valor)}</td>'
            f'<td>+ {pct_vb(valor)}</td>'
            f'</tr>'
        )

    def linha_subtotal(label: str, valor: float) -> str:
        return (
            f'<tr class="dre-row-subtotal">'
            f'<td>{label}</td>'
            f'<td>{formatar_brl(valor)}</td>'
            f'<td>{pct_vv(valor)}</td>'
            f'<td>{pct_vb(valor)}</td>'
            f'</tr>'
        )

    lucro = r["lucro_liquido"]
    classe_resultado = "dre-row-resultado" + ("" if lucro >= 0 else " negativo")

    # Construir tbody sem linhas em branco (evita que o parser Markdown termine o bloco HTML)
    linha_resultado = (
        f'<tr class="{classe_resultado}">'
        f'<td>Resultado Bruto (Lucro Liquido)</td>'
        f'<td>{formatar_brl(lucro)}</td>'
        f'<td>{pct_vv(lucro)}</td>'
        f'<td>{pct_vb(lucro)}</td>'
        f'</tr>'
    )
    partes = [
        linha_header("VGV Bruto", vgv_bruto),
        linha_deducao("(-) Permuta Fisica", permuta_fisica),
        linha_subtotal("VGV Vendavel (base de calculo)", vgv_vendavel),
        linha_adicao("(+) Receita Financeira (Juros)", r["receita_financeira"]),
        linha_subtotal("Receita Total", r["vgv_total_recebido"]),
        separador(),
        linha_deducao("(-) Aquisicao do Terreno", r["custo_terreno_aquisicao"]),
        linha_deducao("(-) Cartorio", r["custo_terreno_cartorio"]),
        linha_deducao("(-) Obras", r["custo_obras"]),
        linha_deducao("(-) Projetos", r["custo_projetos"]),
        linha_deducao("(-) Licenciamento", r["custo_licenciamento"]),
        linha_deducao("(-) Marketing", r["custo_marketing"]),
        linha_deducao("(-) Outros", r["custo_outros"]),
        linha_deducao("(-) Administracao", r["custo_administracao"]),
        linha_deducao("(-) Comissao de Vendas", r["custo_comissao"]),
        linha_deducao("(-) Impostos / Tributacao", r["custo_impostos"]),
        linha_deducao("(-) Permuta Financeira", r["custo_permuta_financeira"]),
        separador(),
        linha_subtotal("Total de Saidas", r["total_saidas"]),
        separador(),
        linha_resultado,
    ]

    # Item 9: custo do financiamento bancario na DRE (quando ativo)
    custo_fin = r.get("custo_financiamento_total", 0) or 0
    if custo_fin > 1:
        lucro_com_fin = lucro - custo_fin
        classe_res_fin = "dre-row-resultado" + ("" if lucro_com_fin >= 0 else " negativo")
        partes.extend([
            separador(),
            (
                f'<tr class="dre-row-deduction">'
                f'<td>&nbsp;&nbsp;&nbsp;(-) Custo do Financiamento (Juros + Comissao)</td>'
                f'<td>({formatar_brl(custo_fin)})</td>'
                f'<td>({pct_vv(custo_fin)})</td>'
                f'<td>({pct_vb(custo_fin)})</td>'
                f'</tr>'
            ),
            (
                f'<tr class="{classe_res_fin}">'
                f'<td>Resultado Liquido c/ Financiamento</td>'
                f'<td>{formatar_brl(lucro_com_fin)}</td>'
                f'<td>{pct_vv(lucro_com_fin)}</td>'
                f'<td>{pct_vb(lucro_com_fin)}</td>'
                f'</tr>'
            ),
        ])

    tbody = "".join(p for p in partes if p)

    thead = (
        '<thead><tr>'
        '<th style="width:40%;">Descricao</th>'
        '<th style="width:20%;">Valor (R$)</th>'
        '<th style="width:20%;">% VGV Vendavel</th>'
        '<th style="width:20%;">% VGV Bruto</th>'
        '</tr></thead>'
    )
    html = f'<table class="dre-table">{thead}<tbody>{tbody}</tbody></table>'

    st.markdown(html, unsafe_allow_html=True)


# =====================================================================
# CARDS DE MARGEM
# =====================================================================

def _renderizar_cards_margem(r: dict, ind: dict) -> None:
    margem_vv = r.get("margem_sobre_vgv_vendavel")
    margem_vb = r.get("margem_sobre_vgv_bruto")
    multiplicador = ind.get("lucro_sobre_exposicao")
    tir = ind.get("tir_anual")

    def cor_margem(v: float | None) -> str:
        if v is None:
            return "neutro"
        return "verde" if v > 0 else "vermelho"

    kpis = [
        {
            "label": "Margem s/ VGV Vendavel",
            "valor": formatar_pct(margem_vv) if margem_vv is not None else "—",
            "cor": cor_margem(margem_vv),
        },
        {
            "label": "Margem s/ VGV Bruto",
            "valor": formatar_pct(margem_vb) if margem_vb is not None else "—",
            "cor": cor_margem(margem_vb),
        },
        {
            "label": "Multiplicador (Lucro / Exposicao)",
            "valor": f"{multiplicador:.2f}x".replace(".", ",") if multiplicador else "—",
            "cor": "verde" if (multiplicador and multiplicador > 1) else "neutro",
        },
        {
            "label": "TIR Anual",
            "valor": formatar_pct(tir) if tir is not None else "—",
            "cor": "verde" if (tir and tir > 0.10) else "neutro",
        },
    ]

    st.markdown(
        '<div style="margin:16px 0 8px;font-size:10px;font-weight:600;letter-spacing:0.10em;'
        'text-transform:uppercase;color:var(--stone-500);">Indicadores de Rentabilidade</div>',
        unsafe_allow_html=True,
    )
    renderizar_grade_kpis(kpis)


# =====================================================================
# COMPOSICAO DAS SAIDAS (DONUT)
# =====================================================================

def _renderizar_composicao_saidas(r: dict) -> None:
    st.markdown(
        '<div style="margin:4px 0 8px;font-size:10px;font-weight:600;letter-spacing:0.10em;'
        'text-transform:uppercase;color:var(--stone-500);">Composição das Saídas</div>',
        unsafe_allow_html=True,
    )

    categorias_raw = [
        ("Terreno", r["custo_terreno_aquisicao"] + r["custo_terreno_cartorio"]),
        ("Obras", r["custo_obras"]),
        ("Projetos", r["custo_projetos"]),
        ("Licenciamento", r["custo_licenciamento"]),
        ("Marketing", r["custo_marketing"]),
        ("Outros / Admin", r["custo_outros"] + r["custo_administracao"]),
        ("Comissao", r["custo_comissao"]),
        ("Impostos", r["custo_impostos"]),
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

    col_grafico, col_tabela = st.columns([1, 1])

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
            legend=dict(
                bgcolor="#F5F3EE",
                bordercolor="#D8D4C8",
                borderwidth=0,
                font=dict(size=10),
                orientation="h",
                x=0,
                y=-0.18,
            ),
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
                f'<tr>'
                f'<td>{dot}{label}</td>'
                f'<td style="text-align:right;">{formatar_brl(valor)}</td>'
                f'<td style="text-align:right;">{pct:.1f}%</td>'
                f'<td style="text-align:right;">{formatar_brl(por_lote)}</td>'
                f'</tr>'
            )

        por_lote_total = (
            formatar_brl(total / r["total_lotes"])
            if r.get("total_lotes", 0) > 0 else "—"
        )
        linha_total = (
            f'<tr class="dre-row-subtotal">'
            f'<td>Total Saidas</td>'
            f'<td style="text-align:right;">{formatar_brl(total)}</td>'
            f'<td style="text-align:right;">100,0%</td>'
            f'<td style="text-align:right;">{por_lote_total}</td>'
            f'</tr>'
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
        html = f'<table class="dre-table">{thead_comp}<tbody>{tbody_comp}</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)


# =====================================================================
# COMPARATIVO NOMINAL vs FINANCEIRO
# =====================================================================

def _renderizar_nominal_vs_financeiro(r: dict) -> None:
    receita_nominal = r.get("receita_nominal_venda", 0)
    receita_financeira = r.get("receita_financeira", 0)
    total_recebido = r.get("vgv_total_recebido", 0)

    if receita_financeira < 1:
        return

    st.markdown(
        '<div style="margin:4px 0 8px;font-size:10px;font-weight:600;letter-spacing:0.10em;'
        'text-transform:uppercase;color:var(--stone-500);">Receita Nominal vs Receita Financeira</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "A receita financeira sao os juros embutidos nas parcelas (sistema Price). "
        "O resultado nominal e o lucro sobre o VGV; o resultado total inclui esses juros."
    )

    pct_fin = receita_financeira / total_recebido * 100 if total_recebido > 0 else 0

    kpis = [
        {
            "label": "Receita Nominal de Venda",
            "valor": formatar_brl(receita_nominal),
            "sub": "Principal (= VGV vendavel)",
            "cor": "neutro",
        },
        {
            "label": "Receita Financeira (Juros)",
            "valor": formatar_brl(receita_financeira),
            "sub": f"{pct_fin:.1f}% da receita total",
            "cor": "neutro",
        },
        {
            "label": "Total Recebido",
            "valor": formatar_brl(total_recebido),
            "sub": "Nominal + Juros",
            "cor": "verde",
        },
    ]

    renderizar_grade_kpis(kpis)
