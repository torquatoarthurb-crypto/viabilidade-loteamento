"""
Modulo 13 — Financiamento da Exposicao.

Suporta duas modalidades independentes (ambas podem estar ativas):
  • Banco (CCB/CCE): linha de credito com comissao, IOF e gatilhos.
  • Investidor:
      - % do negocio: split do lucro liquido na DRE.
      - Emprestimo: aporte sem comissao/IOF, ativo apenas quando banco bloqueado por gatilho.
"""

from __future__ import annotations

import streamlit as st

from ...modelos import ConfigFinanciamento
from ..helpers import (
    btn_proximo_modulo,
    cabecalho_aba,
    formatar_brl,
    formatar_pct,
    get_projeto,
    get_resultado,
    invalidar_resultado,
    numero_brl,
    set_projeto,
)


# =====================================================================
# SAVE
# =====================================================================

def _autosave(projeto, **kw) -> None:
    try:
        nova = ConfigFinanciamento(**kw)
        if projeto.financiamento != nova:
            set_projeto(projeto.model_copy(update={"financiamento": nova}))
            invalidar_resultado()
    except Exception:
        pass


def _build_config(fin, **overrides) -> dict:
    """Constroi dict com todos os campos de ConfigFinanciamento para _autosave."""
    return {
        "ativo": overrides.get("ativo", fin.ativo),
        "tipo": fin.tipo,
        "taxa_juros_am": overrides.get("taxa_juros_am", fin.taxa_juros_am),
        "limite_credito_valor": overrides.get("limite_credito_valor", fin.limite_credito_valor),
        "periodo_carencia_meses": int(overrides.get("periodo_carencia_meses", fin.periodo_carencia_meses)),
        "comissao_abertura_pct": overrides.get("comissao_abertura_pct", fin.comissao_abertura_pct),
        "iof_pct": overrides.get("iof_pct", fin.iof_pct),
        "caixa_minimo": overrides.get("caixa_minimo", fin.caixa_minimo),
        "gatilho_tipo": overrides.get("gatilho_tipo", getattr(fin, "gatilho_tipo", "nenhum")),
        "gatilho_vendas_pct": overrides.get("gatilho_vendas_pct", getattr(fin, "gatilho_vendas_pct", 20.0)),
        "gatilho_obras_pct": overrides.get("gatilho_obras_pct", getattr(fin, "gatilho_obras_pct", 30.0)),
        "ativo_investidor": overrides.get("ativo_investidor", getattr(fin, "ativo_investidor", False)),
        "modo_investidor": overrides.get("modo_investidor", getattr(fin, "modo_investidor", "pct_negocio")),
        "investidor_pct_negocio": overrides.get("investidor_pct_negocio", getattr(fin, "investidor_pct_negocio", 20.0)),
        "taxa_juros_investidor_am": overrides.get("taxa_juros_investidor_am", getattr(fin, "taxa_juros_investidor_am", 1.5)),
        "limite_investidor": overrides.get("limite_investidor", getattr(fin, "limite_investidor", 0.0)),
        "carencia_investidor": int(overrides.get("carencia_investidor", getattr(fin, "carencia_investidor", 0))),
        "ordem_amortizacao": overrides.get("ordem_amortizacao", getattr(fin, "ordem_amortizacao", "banco_primeiro")),
    }


# =====================================================================
# RESULTADOS
# =====================================================================

def _renderizar_comparativo(resumo: dict) -> None:
    with st.container(border=True):
        st.markdown("#### Impacto do Financiamento")

        def fmt_tir(v):
            return f"{v * 100:.2f}% a.a." if v is not None else "—"

        def fmt_pct_v(v):
            return f"{v * 100:.2f}%" if v is not None else "—"

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
            st.metric("Margem Líquida", fmt_pct_v(marg_sem))
            st.metric("Exposição Máxima", formatar_brl(exp_sem) if exp_sem else "—")
        with col2:
            st.markdown("**Com financiamento**")
            delta_tir = (
                f"{(tir_com - tir_sem) * 100:+.2f} p.p."
                if tir_com is not None and tir_sem is not None else None
            )
            st.metric("TIR", fmt_tir(tir_com), delta=delta_tir)
            delta_vpl = (
                formatar_brl(vpl_com - vpl_sem)
                if vpl_com is not None and vpl_sem is not None else None
            )
            st.metric("VPL", formatar_brl(vpl_com) if vpl_com else "—", delta=delta_vpl)
            delta_marg = (
                f"{(marg_com - marg_sem) * 100:+.2f} p.p."
                if marg_com is not None and marg_sem is not None else None
            )
            st.metric("Margem Líquida", fmt_pct_v(marg_com), delta=delta_marg)
            delta_exp = (
                formatar_brl(exp_com - exp_sem)
                if exp_com is not None and exp_sem is not None else None
            )
            st.metric("Exposição Máxima", formatar_brl(exp_com) if exp_com else "—", delta=delta_exp)
        with col3:
            st.markdown("**Custo do financiamento**")
            st.metric("Juros Banco", formatar_brl(resumo.get("custo_financiamento_juros", 0)))
            st.metric("Comissão Banco", formatar_brl(resumo.get("custo_financiamento_comissao", 0)))
            st.metric("Saldo Devedor Máx. (Banco)", formatar_brl(resumo.get("saldo_devedor_maximo", 0)))
            dev_final = resumo.get("saldo_devedor_final", 0)
            if dev_final > 1:
                st.warning(f"Saldo devedor banco remanescente: **{formatar_brl(dev_final)}**.")
            if resumo.get("investidor_modo") == "emprestimo":
                st.metric("Juros Investidor", formatar_brl(resumo.get("custo_juros_investidor", 0)))
                st.metric("Saldo Devedor Máx. (Inv.)", formatar_brl(resumo.get("saldo_devedor_investidor_maximo", 0)))
                dev_i_final = resumo.get("saldo_devedor_investidor_final", 0)
                if dev_i_final > 1:
                    st.warning(f"Saldo devedor investidor remanescente: **{formatar_brl(dev_i_final)}**.")

    # Investidor % do negocio
    if resumo.get("investidor_ativo") and resumo.get("investidor_modo") == "pct_negocio":
        with st.container(border=True):
            st.markdown("#### Resultado para o Investidor (% do Negócio)")
            pct = resumo.get("investidor_pct_negocio", 0)
            lucro_inv = resumo.get("lucro_investidor", 0) or 0  # obrigacao total P&L
            lucro_lot = resumo.get("lucro_loteadora", 0)
            lucro_total = resumo.get("lucro_bruto_antes_investidor", resumo.get("lucro_liquido", 0))
            aporte_total = resumo.get("aporte_investidor_total", 0) or 0
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Resultado Bruto (Projeto)", formatar_brl(lucro_total))
            with col2:
                st.metric(f"Retorno Investidor ({pct:.1f}%)", formatar_brl(lucro_inv))
            with col3:
                st.metric(f"Resultado Loteadora ({100 - pct:.1f}%)", formatar_brl(lucro_lot))
            if aporte_total > 1:
                st.info(
                    f"Aporte do investidor: **{formatar_brl(aporte_total)}** — capital para cobrir "
                    "exposição de caixa não coberta pelo banco."
                )


# =====================================================================
# RENDERIZACAO
# =====================================================================

def renderizar() -> None:
    cabecalho_aba(
        13,
        "Financiamento da Exposicao",
        "Simule banco (CCB/CCE) e/ou investidor para cobrir o caixa negativo do projeto.",
    )

    projeto = get_projeto()
    fin = projeto.financiamento
    resultado = get_resultado()

    # ============================================================
    # CARD 0 — EXPOSICAO DO PROJETO
    # ============================================================
    if resultado is not None:
        ind = resultado.indicadores
        r = resultado.resumo
        exp_max = abs(ind.get("exposicao_maxima", 0) or 0)
        mes_exp = ind.get("mes_exposicao_maxima", 0)
        horizonte = r.get("horizonte_meses", 0)
        with st.container(border=True):
            st.markdown("#### Exposição do projeto (sem financiamento)")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Exposição máxima", formatar_brl(-exp_max),
                          help="Capital próprio máximo necessário sem financiamento.")
            with c2:
                st.metric("Mês da exposição", f"M{mes_exp}")
            with c3:
                st.metric("Horizonte", f"{horizonte} meses")
    else:
        st.info("Calcule o fluxo de caixa primeiro para ver a exposição do projeto.")

    st.markdown("---")

    # ============================================================
    # TAXA DE REFERENCIA — sempre visivel (alimenta estimativa do Dashboard)
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Taxa de juros do financiamento")
        col_t, col_eq = st.columns(2)
        with col_t:
            taxa = numero_brl(
                "Taxa de juros (% a.m.)",
                value=float(fin.taxa_juros_am),
                key="fin_taxa",
                min_value=0.0,
                max_value=10.0,
                help=(
                    "Taxa de referência usada para estimar o custo financeiro no Dashboard, "
                    "mesmo sem o financiamento ativado. "
                    "Quando o banco estiver ativo, esta é a taxa cobrada sobre o saldo devedor. "
                    "Típico: CDI + 3–6% a.a. ≈ 1,5–2,0% a.m."
                ),
            )
        with col_eq:
            _taxa_aa = (1 + taxa / 100) ** 12 - 1
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:11px;color:#9CA3AF;">Equivalência anual</div>'
                f'<div style="font-size:13px;font-weight:600;">{_taxa_aa * 100:.2f}% a.a.</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ============================================================
    # TOGGLE PRINCIPAL
    # ============================================================
    simular = st.toggle(
        "Simular financiamento",
        value=fin.ativo or getattr(fin, "ativo_investidor", False),
        key="fin_simular",
    )

    if not simular:
        cfg = _build_config(fin, ativo=False, ativo_investidor=False, taxa_juros_am=taxa)
        _autosave(projeto, **cfg)
        btn_proximo_modulo("Reajustes")
        return

    # ============================================================
    # COLUNAS: BANCO | INVESTIDOR
    # ============================================================
    col_banco, col_sep, col_inv = st.columns([1, 0.03, 1])

    # ---- BANCO ----
    with col_banco:
        with st.container(border=True):
            ativo_banco = st.checkbox(
                "Banco (CCB/CCE)",
                value=fin.ativo,
                key="fin_ativo_banco",
            )

            if ativo_banco:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    limite = numero_brl(
                        "Limite (R$) — 0 = sem limite",
                        value=float(fin.limite_credito_valor),
                        key="fin_limite",
                        min_value=0.0,
                        help="0 = crédito ilimitado.",
                    )
                    comissao = numero_brl(
                        "Comissão abertura (%)",
                        value=float(fin.comissao_abertura_pct),
                        key="fin_comissao",
                        min_value=0.0,
                        max_value=5.0,
                        help="Cobrada no M0 sobre o limite contratado.",
                    )
                with col_b2:
                    carencia = numero_brl(
                        "Carência (meses)",
                        value=float(fin.periodo_carencia_meses),
                        key="fin_carencia",
                        min_value=0.0,
                        max_value=60.0,
                        casas=0,
                        help="Meses sem amortização de principal.",
                    )
                    iof = numero_brl(
                        "IOF sobre cada saque (%)",
                        value=float(fin.iof_pct),
                        key="fin_iof",
                        min_value=0.0,
                        max_value=5.0,
                    )

                # Gatilhos
                st.markdown("**Gatilho de liberação**")
                _gatilho_opts = {
                    "nenhum":  "Sem gatilho — saca a qualquer momento",
                    "vendas":  "% de vendas contratadas",
                    "obras":   "% de obras executadas",
                    "ambos":   "Ambos (vendas e obras)",
                }
                gatilho_tipo = st.selectbox(
                    "Tipo de gatilho",
                    options=list(_gatilho_opts.keys()),
                    format_func=lambda x: _gatilho_opts[x],
                    index=list(_gatilho_opts.keys()).index(getattr(fin, "gatilho_tipo", "nenhum")),
                    key="fin_gatilho_tipo",
                    label_visibility="collapsed",
                )
                gatilho_vendas_pct = getattr(fin, "gatilho_vendas_pct", 20.0)
                gatilho_obras_pct = getattr(fin, "gatilho_obras_pct", 30.0)
                if gatilho_tipo in ("vendas", "ambos"):
                    gatilho_vendas_pct = numero_brl(
                        "% VGV vendido para liberar",
                        value=float(getattr(fin, "gatilho_vendas_pct", 20.0)),
                        key="fin_gatilho_vendas",
                        min_value=0.0,
                        max_value=100.0,
                    )
                if gatilho_tipo in ("obras", "ambos"):
                    gatilho_obras_pct = numero_brl(
                        "% obras executadas para liberar",
                        value=float(getattr(fin, "gatilho_obras_pct", 30.0)),
                        key="fin_gatilho_obras",
                        min_value=0.0,
                        max_value=100.0,
                    )
            else:
                taxa = float(fin.taxa_juros_am)
                limite = float(fin.limite_credito_valor)
                carencia = float(fin.periodo_carencia_meses)
                comissao = float(fin.comissao_abertura_pct)
                iof = float(fin.iof_pct)
                gatilho_tipo = getattr(fin, "gatilho_tipo", "nenhum")
                gatilho_vendas_pct = getattr(fin, "gatilho_vendas_pct", 20.0)
                gatilho_obras_pct = getattr(fin, "gatilho_obras_pct", 30.0)

    # ---- INVESTIDOR ----
    with col_inv:
        with st.container(border=True):
            ativo_inv = st.checkbox(
                "Investidor",
                value=getattr(fin, "ativo_investidor", False),
                key="fin_ativo_investidor",
            )

            if ativo_inv:
                modo_inv = st.radio(
                    "Modalidade",
                    options=["pct_negocio", "emprestimo"],
                    format_func=lambda x: "% do Negócio" if x == "pct_negocio" else "Empréstimo",
                    index=0 if getattr(fin, "modo_investidor", "pct_negocio") == "pct_negocio" else 1,
                    key="fin_modo_investidor",
                    horizontal=True,
                )

                if modo_inv == "pct_negocio":
                    pct_negocio = numero_brl(
                        "% do lucro líquido para o investidor",
                        value=float(getattr(fin, "investidor_pct_negocio", 20.0)),
                        key="fin_pct_negocio",
                        min_value=0.0,
                        max_value=100.0,
                        help=(
                            "Após apurar o lucro líquido do projeto, "
                            "este % é separado para o investidor. "
                            "O restante fica com a loteadora."
                        ),
                    )
                    taxa_inv = getattr(fin, "taxa_juros_investidor_am", 1.5)
                    limite_inv = getattr(fin, "limite_investidor", 0.0)
                    carencia_inv = getattr(fin, "carencia_investidor", 0)
                    if resultado is not None:
                        lucro = resultado.resumo.get(
                            "lucro_bruto_antes_investidor",
                            resultado.resumo.get("lucro_liquido", 0),
                        )
                        if lucro != 0:
                            lucro_inv = lucro * pct_negocio / 100
                            lucro_lot = lucro * (1 - pct_negocio / 100)
                            st.info(
                                f"Investidor: **{formatar_brl(lucro_inv)}** "
                                f"| Loteadora: **{formatar_brl(lucro_lot)}**"
                            )
                else:
                    pct_negocio = getattr(fin, "investidor_pct_negocio", 20.0)
                    taxa_inv = numero_brl(
                        "Taxa de juros (% a.m.)",
                        value=float(getattr(fin, "taxa_juros_investidor_am", 1.5)),
                        key="fin_taxa_inv",
                        min_value=0.0,
                        max_value=10.0,
                        help="Sem comissão e sem IOF.",
                    )
                    taxa_inv_aa = (1 + taxa_inv / 100) ** 12 - 1
                    st.markdown(
                        f'<div style="font-size:11px;color:#9CA3AF;">Equivalência anual</div>'
                        f'<div style="font-size:13px;font-weight:600;">{taxa_inv_aa * 100:.2f}% a.a.</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("")

                    col_i1, col_i2 = st.columns(2)
                    with col_i1:
                        limite_inv = numero_brl(
                            "Limite (R$) — 0 = sem limite",
                            value=float(getattr(fin, "limite_investidor", 0.0)),
                            key="fin_limite_inv",
                            min_value=0.0,
                        )
                    with col_i2:
                        carencia_inv = numero_brl(
                            "Carência (meses)",
                            value=float(getattr(fin, "carencia_investidor", 0)),
                            key="fin_carencia_inv",
                            min_value=0.0,
                            max_value=60.0,
                            casas=0,
                        )

                    if ativo_banco:
                        st.caption(
                            "O investidor aporta apenas enquanto o banco estiver "
                            "bloqueado pelo gatilho. Após o gatilho do banco ser atingido, "
                            "o banco assume os saques."
                        )
                    else:
                        st.caption("Com banco inativo, o investidor aporta livremente quando necessário.")
            else:
                modo_inv = getattr(fin, "modo_investidor", "pct_negocio")
                pct_negocio = getattr(fin, "investidor_pct_negocio", 20.0)
                taxa_inv = getattr(fin, "taxa_juros_investidor_am", 1.5)
                limite_inv = getattr(fin, "limite_investidor", 0.0)
                carencia_inv = getattr(fin, "carencia_investidor", 0)

    # ============================================================
    # CAIXA MINIMO (compartilhado)
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Reserva de caixa mínimo")
        caixa_minimo = numero_brl(
            "Caixa mínimo a manter (R$) — 0 = sem reserva",
            value=float(fin.caixa_minimo),
            key="fin_caixa_minimo",
            min_value=0.0,
            help=(
                "Piso de caixa mantido o tempo todo. "
                "Saques cobrem quedas abaixo desse valor; "
                "amortizações só ocorrem quando o caixa superar esse valor. "
                "Aplica-se a banco e investidor."
            ),
        )

    # ============================================================
    # ORDEM DE AMORTIZACAO (quando ambos ativos em modo emprestimo)
    # ============================================================
    inv_emp_ativo = ativo_inv and (modo_inv == "emprestimo")
    if ativo_banco and inv_emp_ativo:
        with st.container(border=True):
            st.markdown("#### Ordem de amortização")
            ordem_amort = st.radio(
                "Qual dívida é amortizada primeiro?",
                options=["banco_primeiro", "investidor_primeiro"],
                format_func=lambda x: "Banco primeiro" if x == "banco_primeiro" else "Investidor primeiro",
                index=0 if getattr(fin, "ordem_amortizacao", "banco_primeiro") == "banco_primeiro" else 1,
                key="fin_ordem_amort",
                horizontal=True,
            )
    else:
        ordem_amort = getattr(fin, "ordem_amortizacao", "banco_primeiro")

    # ============================================================
    # AUTO-SAVE
    # ============================================================
    cfg = _build_config(
        fin,
        ativo=ativo_banco,
        taxa_juros_am=taxa,
        limite_credito_valor=limite,
        periodo_carencia_meses=carencia,
        comissao_abertura_pct=comissao,
        iof_pct=iof,
        caixa_minimo=caixa_minimo,
        gatilho_tipo=gatilho_tipo,
        gatilho_vendas_pct=gatilho_vendas_pct,
        gatilho_obras_pct=gatilho_obras_pct,
        ativo_investidor=ativo_inv,
        modo_investidor=modo_inv,
        investidor_pct_negocio=pct_negocio,
        taxa_juros_investidor_am=taxa_inv,
        limite_investidor=limite_inv,
        carencia_investidor=carencia_inv,
        ordem_amortizacao=ordem_amort,
    )
    _autosave(projeto, **cfg)

    # ============================================================
    # SALVAR ABA
    # ============================================================
    st.markdown("---")
    _col_sv, _ = st.columns([1, 3])
    with _col_sv:
        if st.button(
            "Salvar aba",
            key="aba_financiamento_salvar_aba",
            type="primary",
            width="stretch",
            icon=":material/save:",
        ):
            _autosave(projeto, **cfg)
            st.rerun()

    btn_proximo_modulo("Reajustes")

    # ============================================================
    # RESULTADOS
    # ============================================================
    if resultado is None:
        st.info("Clique em **Calcular viabilidade** na sidebar para ver o impacto do financiamento.")
        return

    st.markdown("---")
    _renderizar_comparativo(resultado.resumo)
