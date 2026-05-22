"""
Aba 5 — Impostos e Comissoes.

Refatorada Fase 2.4: auto-save + linguagem mais clara.
"""

from __future__ import annotations

import streamlit as st

from ...modelos import Aba5Impostos, Tributos
from ..helpers import (
    aviso_validacao,
    btn_proximo_modulo,
    cabecalho_aba,
    get_projeto,
    invalidar_resultado,
    numero_brl,
    set_projeto,
)


def _autosave_aba5(tributos_obj) -> None:
    projeto = get_projeto()
    try:
        nova_aba = Aba5Impostos(
            tributos=tributos_obj,
            comissao=projeto.impostos.comissao,
            permuta_financeira=projeto.impostos.permuta_financeira,
        )
        projeto_atualizado = projeto.model_copy(update={"impostos": nova_aba})
        set_projeto(projeto_atualizado)
        invalidar_resultado()
    except Exception:
        pass


def renderizar() -> None:
    cabecalho_aba(
        5,
        "Impostos",
        "Regime tributario do empreendimento. "
        "💾 Alteracoes salvas automaticamente.",
    )

    projeto = get_projeto()
    impostos = projeto.impostos

    # ============================================================
    # CARD 1 — REGIME TRIBUTARIO
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 📑 Regime Tributario")

        col1, col2 = st.columns(2)
        with col1:
            regime = st.radio(
                "Regime de tributacao",
                options=["lucro_presumido", "lucro_real"],
                format_func=lambda x: {
                    "lucro_presumido": "📋 Lucro Presumido (mais simples)",
                    "lucro_real": "📊 Lucro Real (calculo individual de IRPJ/CSLL/PIS/COFINS)",
                }[x],
                index=0 if impostos.tributos.regime == "lucro_presumido" else 1,
                key="aba5_regime",
            )

            if regime == "lucro_presumido":
                aliq_efetiva = numero_brl(
                    "Aliquota efetiva sobre receita (%)",
                    value=float(impostos.tributos.aliquota_efetiva),
                    key="aba5_aliq",
                    min_value=0.0,
                    help="Para incorporacao em lucro presumido, a pratica e ~6,73% "
                         "(IRPJ + CSLL + PIS + COFINS). Confirme com seu contador.",
                )
                irpj = impostos.tributos.irpj
                csll = impostos.tributos.csll
                pis = impostos.tributos.pis
                cofins = impostos.tributos.cofins
            else:
                aliq_efetiva = impostos.tributos.aliquota_efetiva
                st.markdown("**Aliquotas individuais (% sobre receita):**")
                irpj = numero_brl("IRPJ", value=float(impostos.tributos.irpj),
                                  key="aba5_irpj", min_value=0.0)
                csll = numero_brl("CSLL", value=float(impostos.tributos.csll),
                                  key="aba5_csll", min_value=0.0)
                pis = numero_brl("PIS", value=float(impostos.tributos.pis),
                                 key="aba5_pis", min_value=0.0)
                cofins = numero_brl("COFINS", value=float(impostos.tributos.cofins),
                                    key="aba5_cofins", min_value=0.0)
                soma = irpj + csll + pis + cofins
                st.caption(f"Soma das aliquotas: {soma:.2f}%")

        with col2:
            regime_apur = st.radio(
                "Quando o imposto incide?",
                options=["caixa", "competencia"],
                format_func=lambda x: {
                    "caixa": "💰 No recebimento (regime de caixa)",
                    "competencia": "📅 Na venda (regime de competencia)",
                }[x],
                index=0 if impostos.tributos.regime_apuracao == "caixa" else 1,
                help="Caixa: imposto cai quando o dinheiro entra. "
                     "Competencia: imposto cai quando a venda e feita, mesmo se o "
                     "comprador ainda nao pagou tudo.",
                key="aba5_regime_apur",
            )

    # ============================================================
    # NAVEGACAO
    # ============================================================
    btn_proximo_modulo("Fluxo de Caixa")

    # Auto-save
    try:
        tributos_obj = Tributos(
            regime=regime,
            aliquota_efetiva=aliq_efetiva,
            irpj=irpj, csll=csll, pis=pis, cofins=cofins,
            regime_apuracao=regime_apur,
        )
        atual_t = impostos.tributos
        mudou = (
            atual_t.regime != regime or
            atual_t.aliquota_efetiva != aliq_efetiva or
            atual_t.irpj != irpj or atual_t.csll != csll or
            atual_t.pis != pis or atual_t.cofins != cofins or
            atual_t.regime_apuracao != regime_apur
        )
        if mudou:
            _autosave_aba5(tributos_obj)
    except Exception:
        pass
