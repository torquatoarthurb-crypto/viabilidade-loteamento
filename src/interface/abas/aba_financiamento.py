"""
Modulo 13 — Financiamento Bancario da Producao.

Permite simular o uso de uma linha de credito bancaria para cobrir os
periodos de caixa negativo do projeto (A1 — saque automatico).
"""

from __future__ import annotations

import streamlit as st

from ...modelos import ConfigFinanciamento
from ..helpers import (
    btn_proximo_modulo,
    cabecalho_aba,
    formatar_brl,
    get_projeto,
    get_resultado,
    invalidar_resultado,
    numero_brl,
    set_projeto,
)

def _autosave(projeto, ativo, taxa, limite, carencia, comissao, iof) -> None:
    try:
        nova = ConfigFinanciamento(
            ativo=ativo,
            tipo="cce",
            taxa_juros_am=taxa,
            limite_credito_valor=limite,
            periodo_carencia_meses=int(carencia),
            comissao_abertura_pct=comissao,
            iof_pct=iof,
        )
        if projeto.financiamento != nova:
            set_projeto(projeto.model_copy(update={"financiamento": nova}))
            invalidar_resultado()
    except Exception:
        pass


def _renderizar_comparativo(resumo: dict, formatar_brl) -> None:
    """Tabela comparativa sem financiamento x com financiamento."""
    with st.container(border=True):
        st.markdown("#### 📊 Impacto do Financiamento")

        def fmt_pct(v):
            return f"{v * 100:.2f}%" if v is not None else "—"

        def fmt_tir(v):
            return f"{v * 100:.2f}% a.a." if v is not None else "—"

        tir_sem = resumo.get("tir_anual_sem_fin")
        tir_com = resumo.get("tir_anual")
        vpl_sem = resumo.get("vpl_sem_fin")
        vpl_com = resumo.get("vpl")
        marg_sem = resumo.get("margem_sem_fin")
        marg_com = resumo.get("margem_sobre_vgv_vendavel")
        exp_sem = resumo.get("exposicao_sem_fin")
        exp_com = resumo.get("exposicao_maxima")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Sem financiamento**")
            st.metric("TIR", fmt_tir(tir_sem))
            st.metric("VPL", formatar_brl(vpl_sem) if vpl_sem else "—")
            st.metric("Margem Líquida", fmt_pct(marg_sem))
            st.metric("Exposição Máxima", formatar_brl(exp_sem) if exp_sem else "—")
        with col2:
            st.markdown("**Com financiamento**")
            delta_tir = (
                f"{(tir_com - tir_sem) * 100:+.2f} p.p."
                if tir_com is not None and tir_sem is not None else None
            )
            st.metric("TIR", fmt_tir(tir_com), delta=delta_tir)
            delta_vpl = (
                f"{formatar_brl(vpl_com - vpl_sem)}"
                if vpl_com is not None and vpl_sem is not None else None
            )
            st.metric("VPL", formatar_brl(vpl_com) if vpl_com else "—", delta=delta_vpl)
            delta_marg = (
                f"{(marg_com - marg_sem) * 100:+.2f} p.p."
                if marg_com is not None and marg_sem is not None else None
            )
            st.metric("Margem Líquida", fmt_pct(marg_com), delta=delta_marg)
            delta_exp = (
                f"{formatar_brl(exp_com - exp_sem)}"
                if exp_com is not None and exp_sem is not None else None
            )
            st.metric("Exposição Máxima", formatar_brl(exp_com) if exp_com else "—", delta=delta_exp)
        with col3:
            st.markdown("**Custo do financiamento**")
            juros_total = resumo.get("custo_financiamento_juros", 0)
            comissao_val = resumo.get("custo_financiamento_comissao", 0)
            total_fin = resumo.get("custo_financiamento_total", 0)
            devedor_max = resumo.get("saldo_devedor_maximo", 0)
            devedor_final = resumo.get("saldo_devedor_final", 0)

            st.metric("Juros pagos ao banco", formatar_brl(juros_total))
            st.metric("Comissão de abertura", formatar_brl(comissao_val))
            st.metric("Custo total", formatar_brl(total_fin))
            st.metric("Saldo devedor máximo", formatar_brl(devedor_max))
            if devedor_final > 1:
                st.warning(
                    f"⚠️ Saldo devedor remanescente ao fim do horizonte: "
                    f"**{formatar_brl(devedor_final)}**. "
                    f"Aumente o limite ou estenda o horizonte do projeto."
                )
            else:
                st.success("✅ Dívida quitada dentro do horizonte do projeto.")


def renderizar() -> None:
    cabecalho_aba(
        13,
        "Financiamento da Exposicao",
        "Simule o uso de linha de credito bancaria (CCB/CCE) para cobrir o caixa negativo do projeto.",
    )

    projeto = get_projeto()
    fin = projeto.financiamento
    resultado = get_resultado()

    # ============================================================
    # CARD 0 — CONTEXTO: EXPOSICAO DO PROJETO (sem financiamento)
    # ============================================================
    if resultado is not None:
        ind = resultado.indicadores
        r = resultado.resumo
        exp_max = abs(ind.get("exposicao_maxima", 0) or 0)
        mes_exp = ind.get("mes_exposicao_maxima", 0)
        horizonte = r.get("horizonte_meses", 0)

        with st.container(border=True):
            st.markdown("#### 🔍 Por que usar financiamento?")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(
                    "Exposição máxima do projeto",
                    formatar_brl(-exp_max),
                    help="Capital próprio máximo necessário sem financiamento bancário.",
                )
            with c2:
                st.metric("Mês da exposição máxima", f"M{mes_exp}")
            with c3:
                st.metric("Horizonte do projeto", f"{horizonte} meses")

            if exp_max > 500_000:
                nivel = "alta" if exp_max > 5_000_000 else "moderada"
                st.info(
                    f"💡 A exposição de capital é **{nivel}** ({formatar_brl(-exp_max)}). "
                    "Financiar parte desse montante pode melhorar o retorno sobre o "
                    "capital próprio (ROE) e reduzir o risco do projeto."
                )
    else:
        st.info(
            "💡 Calcule o fluxo de caixa primeiro para ver a exposição do projeto "
            "e entender o quanto o financiamento pode ajudar."
        )

    st.markdown("---")

    # ============================================================
    # TOGGLE PRINCIPAL
    # ============================================================
    ativo = st.toggle(
        "Simular financiamento bancário",
        value=fin.ativo,
        key="fin_ativo",
        help=(
            "Quando ativo, o sistema identifica automaticamente os meses de caixa "
            "negativo e simula o uso de uma linha de crédito. Os resultados (TIR, VPL, "
            "Margem, Exposição) são recalculados com o custo do financiamento."
        ),
    )

    if not ativo:
        st.info(
            "Ative o financiamento para simular o impacto de uma linha de crédito "
            "bancária na viabilidade do projeto."
        )
        _autosave(projeto, False, fin.taxa_juros_am,
                  fin.limite_credito_valor, fin.periodo_carencia_meses,
                  fin.comissao_abertura_pct, fin.iof_pct)
        btn_proximo_modulo("Reajustes")
        return

    # ============================================================
    # CARD 1 — CONFIGURACAO DA LINHA DE CREDITO
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 🏦 Configuração da linha de crédito — CCB/CCE")
        st.caption("Taxa típica: CDI + 3–6% a.a. (~1,5–2,0% a.m.). Disponível em bancos privados com menos burocracia.")

        col1, col2 = st.columns(2)
        with col1:
            taxa = numero_brl(
                "Taxa de juros (% a.m.)",
                value=float(fin.taxa_juros_am),
                key="fin_taxa",
                min_value=0.0,
                max_value=10.0,
                help="Taxa mensal efetiva cobrada sobre o saldo devedor.",
            )
            limite = numero_brl(
                "Limite da linha de crédito (R$) — 0 = sem limite",
                value=float(fin.limite_credito_valor),
                key="fin_limite",
                min_value=0.0,
                help=(
                    "Valor máximo que pode ser sacado. "
                    "Use 0 para simular crédito ilimitado (sem restrição de teto)."
                ),
            )
        with col2:
            carencia = numero_brl(
                "Período de carência (meses)",
                value=float(fin.periodo_carencia_meses),
                key="fin_carencia",
                min_value=0.0,
                max_value=60.0,
                casas=0,
                help="Meses iniciais sem amortização de principal. Juros continuam sendo cobrados.",
            )
            comissao = numero_brl(
                "Comissão de abertura (% sobre o limite)",
                value=float(fin.comissao_abertura_pct),
                key="fin_comissao",
                min_value=0.0,
                max_value=5.0,
                help="Cobrada no M0 sobre o valor do limite contratado.",
            )

        iof = numero_brl(
            "IOF sobre cada saque (%)",
            value=float(fin.iof_pct),
            key="fin_iof",
            min_value=0.0,
            max_value=5.0,
            help="Percentual adicionado ao saldo devedor a cada saque.",
        )

        taxa_aa = (1 + taxa / 100) ** 12 - 1
        st.caption(f"Equivalência: **{taxa_aa * 100:.2f}% a.a.** — recalcule após configurar.")

    # Auto-save
    _autosave(projeto, ativo, taxa, limite, carencia, comissao, iof)

    # Navegacao
    btn_proximo_modulo("Reajustes")

    # ============================================================
    # RESULTADOS (apos calcular)
    # ============================================================
    if resultado is None:
        st.info("Clique em **Calcular fluxo de caixa** na sidebar para ver o impacto do financiamento.")
        return

    st.markdown("---")
    _renderizar_comparativo(resultado.resumo, formatar_brl)
