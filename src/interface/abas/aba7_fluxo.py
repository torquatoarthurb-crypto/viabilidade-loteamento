"""
Aba 7 — Fluxo de Caixa.

TMA + indicadores rapidos (auto-save).
"""

from __future__ import annotations

import streamlit as st

from ...modelos import ParametrosFinanceiros
from ..helpers import (
    btn_proximo_modulo,
    cabecalho_aba,
    formatar_brl,
    formatar_pct,
    get_projeto,
    get_resultado,
    invalidar_resultado,
    numero_brl,
    renderizar_calcular_cta,
    set_projeto,
)


def _renderizar_memoria_calculo(r: dict, ind: dict, projeto) -> None:
    """Item 2: auditoria das premissas e calculos usados."""
    tma_aa = projeto.parametros.tma_anual
    tma_am = (1 + tma_aa / 100) ** (1 / 12) - 1

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Premissas**")
        st.caption(f"TMA: **{tma_aa:.2f}% a.a.** ({tma_am * 100:.4f}% a.m.)")
        st.caption(f"Horizonte: **{r.get('horizonte_meses', '?')} meses**")
        st.caption(f"Total de lotes: **{r.get('total_lotes', '?')}**")
        st.caption(f"Mes termino obras: **M{r.get('mes_termino_obras', '?')}**")
    with col2:
        st.markdown("**Receitas**")
        vgv_v = r.get("vgv_vendavel", 0)
        perm_fis = r.get("vgv_bruto", 0) - vgv_v
        st.caption(f"VGV Bruto: **{formatar_brl(r.get('vgv_bruto', 0))}**")
        if perm_fis > 0:
            st.caption(f"(-) Permuta fisica: **({formatar_brl(perm_fis)})**")
        st.caption(f"VGV Vendavel: **{formatar_brl(vgv_v)}**")
        rec_fin = r.get("receita_financeira", 0)
        if rec_fin > 0:
            st.caption(f"(+) Juros (Price): **{formatar_brl(rec_fin)}**")
        st.caption(f"Total recebido: **{formatar_brl(r.get('vgv_total_recebido', vgv_v))}**")
    with col3:
        st.markdown("**Custos**")
        st.caption(f"Terreno: **{formatar_brl(r.get('custo_terreno', 0))}**")
        st.caption(f"Obras: **{formatar_brl(r.get('custo_obras', 0))}**")
        desenv = (
            r.get("custo_projetos", 0) + r.get("custo_licenciamento", 0)
            + r.get("custo_marketing", 0) + r.get("custo_outros", 0)
            + r.get("custo_administracao", 0)
        )
        st.caption(f"Desenvolvimento: **{formatar_brl(desenv)}**")
        st.caption(f"Comissao: **{formatar_brl(r.get('custo_comissao', 0))}**")
        st.caption(f"Impostos: **{formatar_brl(r.get('custo_impostos', 0))}**")
        custo_fin = r.get("custo_financiamento_total", 0) or 0
        if custo_fin > 0:
            st.caption(f"Financiamento: **{formatar_brl(custo_fin)}**")

    st.markdown("---")

    col_vpl, col_tir, col_pb = st.columns(3)
    with col_vpl:
        st.markdown("**VPL**")
        vpl = ind.get("vpl", 0)
        st.caption(
            f"VPL = Σ FC_t / (1 + {tma_am * 100:.4f}%)^t\n\n"
            f"Resultado: **{formatar_brl(vpl)}**"
        )
        if vpl > 0:
            st.caption("VPL positivo — projeto cria valor acima da TMA")
        else:
            st.caption("VPL negativo — retorno abaixo da TMA")
    with col_tir:
        st.markdown("**TIR**")
        tir = ind.get("tir_anual")
        if tir is not None:
            st.caption(
                f"TIR = {tir * 100:.4f}% a.a.\n\n"
                f"Metodo: Newton-Raphson + bissecao\n\n"
                f"TMA = {tma_aa:.2f}% a.a."
            )
            diff = tir * 100 - tma_aa
            if diff >= 0:
                st.caption(f"Spread: +{diff:.2f} p.p. acima da TMA")
            else:
                st.caption(f"Spread: {diff:.2f} p.p. abaixo da TMA")
        else:
            st.caption("TIR nao encontrada (fluxo sem inversao de sinal)")
    with col_pb:
        st.markdown("**Payback**")
        pb_s = ind.get("payback_simples_meses")
        pb_d = ind.get("payback_descontado_meses")
        st.caption(f"Simples: **{pb_s} meses**" if pb_s else "Simples: —")
        st.caption(f"Descontado (TMA): **{pb_d} meses**" if pb_d else "Descontado: —")
        exp = ind.get("exposicao_maxima", 0)
        st.caption(f"Exposicao max: **{formatar_brl(exp)}** (M{ind.get('mes_exposicao_maxima', '?')})")


def _autosave_tma(tma: float) -> None:
    projeto = get_projeto()
    try:
        parametros_obj = ParametrosFinanceiros(tma_anual=tma)
        projeto_atualizado = projeto.model_copy(update={"parametros": parametros_obj})
        set_projeto(projeto_atualizado)
        invalidar_resultado()
    except Exception:
        pass


def renderizar() -> None:
    cabecalho_aba(
        7,
        "Fluxo de Caixa",
        "Taxa Mínima de Atratividade (TMA) e fluxo detalhado do projeto.",
    )

    projeto = get_projeto()
    parametros = projeto.parametros

    # ============================================================
    # TMA
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Taxa Mínima de Atratividade (TMA)")
        st.caption(
            "Taxa anual usada para descontar o fluxo no calculo do **VPL** "
            "(Valor Presente Liquido) e do **payback descontado**. "
            "Reflete o custo de oportunidade do capital — quanto voce poderia "
            "ganhar investindo o dinheiro em outro lugar."
        )

        col1, col2 = st.columns(2)
        with col1:
            tma_anual = numero_brl(
                "TMA (% ao ano)",
                value=float(parametros.tma_anual),
                key="aba7_tma",
                min_value=0.0,
                help="Pratica de mercado:\n"
                     "• Conservador: 8-12% a.a. (Selic ou CDI como referencia)\n"
                     "• Moderado: 12-15% a.a.\n"
                     "• Agressivo: 15-20% a.a. (taxa de oportunidade do incorporador)",
            )
        with col2:
            tma_mensal = (1 + tma_anual / 100) ** (1 / 12) - 1
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            st.metric("Equivalente mensal", f"{tma_mensal*100:.4f} % a.m.")

    # Staged + save button
    st.session_state["_aba7_staged"] = tma_anual
    _dirty7 = abs(parametros.tma_anual - tma_anual) > 0.001

    _col_ind7, _col_btn7 = st.columns([3, 1])
    with _col_ind7:
        if _dirty7:
            st.markdown(
                '<div style="color:#F59E0B;font-size:12px;padding-top:6px;">'
                '● Alterações não salvas</div>',
                unsafe_allow_html=True,
            )
    with _col_btn7:
        if st.button(
            "Salvar",
            key="aba7_salvar_tma",
            type="primary" if _dirty7 else "secondary",
            width="stretch",
            icon=":material/save:",
        ):
            _autosave_tma(tma_anual)

    # ============================================================
    # RESULTADO RAPIDO
    # ============================================================
    st.markdown("---")
    st.markdown("#### Resumo do Fluxo")

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    r = resultado.resumo
    ind = resultado.indicadores

    tma = projeto.parametros.tma_anual
    tir_anual = ind.get("tir_anual")
    vpl = ind["vpl"]

    # UX-08: veredito TIR vs TMA
    if tir_anual is not None:
        tir_pct = tir_anual * 100
        if tir_pct >= tma:
            tir_delta = f"+{tir_pct - tma:.1f} p.p. acima da TMA"
        else:
            tir_delta = f"{tir_pct - tma:.1f} p.p. abaixo da TMA"
    else:
        tir_delta = None

    vpl_delta = "Viável" if vpl > 0 else "Inviável"

    st.markdown(
        '<div style="margin:4px 0 8px;font-size:10px;font-weight:600;'
        'letter-spacing:0.10em;text-transform:uppercase;color:var(--stone-500);">'
        'Retorno</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "VGV bruto",
            formatar_brl(r["vgv_bruto"]),
            help="Valor Geral de Vendas — somatório de todos os lotes pelo preço cheio, antes de descontar permutas físicas.",
        )
    with col2:
        st.metric(
            "Lucro liquido",
            formatar_brl(r["lucro_liquido"]),
            help="Receita total recebida menos todas as saídas (terreno, obras, incorporação, comissão, impostos e financiamento).",
        )
    with col3:
        st.metric(
            "VPL",
            formatar_brl(vpl),
            delta=vpl_delta,
            help="Valor Presente Líquido — fluxo de caixa descontado pela TMA. Positivo = projeto gera valor acima do custo de oportunidade.",
        )
    with col4:
        st.metric(
            "TIR (a.a.)",
            formatar_pct(tir_anual) if tir_anual is not None else "—",
            delta=tir_delta,
            help="Taxa Interna de Retorno anual — taxa que zera o VPL. Calculada por Newton-Raphson. Compare com a TMA para decidir a viabilidade.",
        )

    st.markdown(
        '<div style="margin:16px 0 8px;font-size:10px;font-weight:600;'
        'letter-spacing:0.10em;text-transform:uppercase;color:var(--stone-500);">'
        'Risco e Liquidez</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Exposicao maxima",
            formatar_brl(ind["exposicao_maxima"]),
            help="Maior saldo acumulado negativo do projeto — capital próprio máximo que precisa estar disponível simultaneamente.",
        )
    with col2:
        st.metric(
            "Mes da exposicao",
            f"M{ind['mes_exposicao_maxima']}",
            help="Mês em que ocorre o pico de exposição de capital. Útil para planejar o timing do aporte ou do financiamento bancário.",
        )
    with col3:
        pb_s = ind.get("payback_simples_meses")
        st.metric(
            "Payback simples",
            f"{pb_s} meses" if pb_s is not None else "—",
            help="Mês em que o saldo acumulado cruza o zero, sem descontar o custo do capital. Referência rápida de liquidez do projeto.",
        )
    with col4:
        pb_d = ind.get("payback_descontado_meses")
        st.metric(
            "Payback descontado",
            f"{pb_d} meses" if pb_d is not None else "—",
            help="Mês em que o saldo acumulado descontado pela TMA cruza o zero. Mais conservador que o simples — considera o custo de oportunidade do capital ao longo do tempo.",
        )

    with st.expander("Memória de Cálculo", expanded=False):
        _renderizar_memoria_calculo(r, ind, projeto)

    from .aba8_dashboard import _tabela_fluxo_mensal
    _tabela_fluxo_mensal(resultado.fluxo_caixa)

    btn_proximo_modulo("Ferramentas")


def sincronizar_aba7() -> None:
    """Salva a TMA no projeto (chamado pelo sidebar antes de Calcular)."""
    tma = st.session_state.get("_aba7_staged")
    if tma is not None:
        _autosave_tma(float(tma))
