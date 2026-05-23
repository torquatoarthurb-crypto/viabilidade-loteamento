"""
Modulo 14 — Reajustes Monetarios.

Permite aplicar correcao por indices (INCC, IPCA, IGP-M) sobre:
- Custo de obras (INCC)
- Parcelas durante a obra do comprador (INCC/IPCA/IGP-M)
- Terreno parcelado (IGP-M/IPCA)

Modelo B1: taxa anual constante projetada.
"""

from __future__ import annotations

import streamlit as st

from ...modelos import ConfigReajustes
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

_INDICE_LABEL = {
    "incc": "INCC — Índice Nacional de Custo da Construção",
    "ipca": "IPCA — Índice de Preços ao Consumidor Amplo",
    "igpm": "IGP-M — Índice Geral de Preços do Mercado",
}

_INDICE_REFERENCIA = {
    "incc": "Histórico recente: 3–8% a.a. (2020–2024 média ~5,5%)",
    "ipca": "Meta Banco Central: 3–4,5% a.a. (meta 2024: 3%)",
    "igpm": "Histórico recente: 3–10% a.a. (volátil, segue câmbio e commodities)",
}


def _autosave(projeto, cfg: dict) -> None:
    try:
        nova = ConfigReajustes(**cfg)
        if projeto.reajustes != nova:
            set_projeto(projeto.model_copy(update={"reajustes": nova}))
            invalidar_resultado()
    except Exception:
        pass


def _taxa_mensal(taxa_aa: float) -> float:
    if taxa_aa <= 0:
        return 0.0
    return (1 + taxa_aa / 100) ** (1 / 12) - 1


def renderizar() -> None:
    cabecalho_aba(
        14,
        "Reajustes Monetários",
        "Configure correcao monetaria por INCC, IPCA ou IGP-M sobre custos e receitas.",
    )

    projeto = get_projeto()
    r = projeto.reajustes

    # --- Toggle principal ---
    ativo = st.toggle(
        "Ativar reajustes monetários",
        value=r.ativo,
        key="raj_ativo",
        help=(
            "Quando ativo, o sistema reajusta custos e/ou parcelas pelo índice configurado. "
            "Todos os valores continuam sendo inseridos em preços de hoje; "
            "o sistema aplica a correção automaticamente no cálculo."
        ),
    )

    if not ativo:
        st.info(
            "Ative os reajustes para simular o impacto da inflação setorial "
            "sobre custos de obras e receitas de parcelas."
        )
        _autosave(projeto, {"ativo": False, **{
            k: getattr(r, k)
            for k in r.model_fields if k != "ativo"
        }})
        btn_proximo_modulo("Dashboard", target_idx=0)
        return

    st.markdown("---")
    resultado = get_resultado()

    # ================================================================
    # SECAO 1 — OBRAS (INCC)
    # ================================================================
    with st.container(border=True):
        st.markdown("#### 🏗️ Custo de obras — INCC")
        st.caption(
            "O custo inserido na Aba de Obras está em preços atuais (constantes). "
            "Com INCC ativo, cada mês de desembolso é multiplicado por `(1 + INCC_m)^mês`, "
            "refletindo o encarecimento dos insumos ao longo do tempo."
        )

        col1, col2 = st.columns([1, 2])
        with col1:
            aplic_obras = st.checkbox(
                "Aplicar INCC nas obras",
                value=r.aplicar_incc_obras,
                key="raj_aplic_obras",
            )
        with col2:
            incc_pct = numero_brl(
                "INCC projetado (% a.a.)",
                value=float(r.incc_anual_pct),
                key="raj_incc",
                min_value=0.0,
                max_value=50.0,
                help=_INDICE_REFERENCIA["incc"],
                disabled=not aplic_obras,
            )
        st.caption(f"Equivalência mensal: {_taxa_mensal(incc_pct) * 100:.4f}% a.m.")

        if resultado and aplic_obras:
            var = resultado.resumo.get("variacao_custo_obras_incc", 0)
            base = resultado.resumo.get("custo_obras_base_constante", 0)
            if var > 0 and base > 0:
                st.info(
                    f"📈 Com INCC de {incc_pct:.1f}% a.a., o custo nominal das obras sobe "
                    f"**{formatar_brl(var)}** acima do orçamento base "
                    f"({var / base * 100:.1f}% a mais)."
                )

    # ================================================================
    # SECAO 2 — PARCELAS DO COMPRADOR
    # ================================================================
    with st.container(border=True):
        st.markdown("#### 📄 Parcelas durante a obra — correção do comprador")
        st.caption(
            "As parcelas mensais pagas pelo comprador durante a obra são corrigidas pelo "
            "índice escolhido. Cada parcela é multiplicada por `(1 + índice_m)^k` onde k "
            "é o número do mês dentro da série. Isso gera receita adicional para o incorporador."
        )

        col1, col2 = st.columns([1, 2])
        with col1:
            aplic_parc = st.checkbox(
                "Aplicar correção nas parcelas",
                value=r.aplicar_correcao_parcelas,
                key="raj_aplic_parc",
            )
        with col2:
            indices = list(_INDICE_LABEL.keys())
            indice_parc = st.selectbox(
                "Índice das parcelas",
                options=indices,
                format_func=lambda x: _INDICE_LABEL[x],
                index=indices.index(r.indice_parcelas) if r.indice_parcelas in indices else 0,
                key="raj_indice_parc",
                disabled=not aplic_parc,
            )

        # Mostrar o campo correto conforme o indice selecionado
        if indice_parc == "incc":
            taxa_parc_input = incc_pct  # reutiliza o INCC já inserido acima
            st.caption(f"Taxa: INCC {incc_pct:.2f}% a.a. (configurado na seção acima)")
        elif indice_parc == "ipca":
            taxa_parc_input = numero_brl(
                "IPCA projetado (% a.a.)",
                value=float(r.ipca_anual_pct),
                key="raj_ipca",
                min_value=0.0,
                max_value=50.0,
                help=_INDICE_REFERENCIA["ipca"],
                disabled=not aplic_parc,
            )
        else:  # igpm
            taxa_parc_input = numero_brl(
                "IGP-M projetado (% a.a.)",
                value=float(r.igpm_anual_pct),
                key="raj_igpm",
                min_value=0.0,
                max_value=50.0,
                help=_INDICE_REFERENCIA["igpm"],
                disabled=not aplic_parc,
            )
            st.caption(f"Equivalência mensal: {_taxa_mensal(taxa_parc_input) * 100:.4f}% a.m.")

        if resultado and aplic_parc:
            corr_total = resultado.resumo.get("receita_correcao_total", 0)
            if corr_total > 0:
                vgv_v = resultado.resumo.get("vgv_vendavel", 1)
                st.success(
                    f"📈 Receita adicional de correção: **{formatar_brl(corr_total)}** "
                    f"({corr_total / vgv_v * 100:.1f}% do VGV vendável)."
                )

    # ================================================================
    # SECAO 3 — TERRENO PARCELADO
    # ================================================================
    with st.container(border=True):
        st.markdown("#### 🏡 Terreno parcelado — correção do custo")
        st.caption(
            "Se o terreno foi adquirido de forma parcelada, as parcelas podem ser "
            "corrigidas por um índice. Aumenta o custo total do terreno em termos nominais."
        )

        forma_terreno = projeto.aquisicao.forma_pagamento
        if forma_terreno not in ("parcelado", "customizado"):
            st.info("Não aplicável: o terreno está configurado como pagamento à vista ou sem desembolso.")
            aplic_terr = False
            indice_terr = r.indice_terreno
        else:
            col1, col2 = st.columns([1, 2])
            with col1:
                aplic_terr = st.checkbox(
                    "Aplicar correção no terreno",
                    value=r.aplicar_correcao_terreno,
                    key="raj_aplic_terr",
                )
            with col2:
                indice_terr = st.selectbox(
                    "Índice do terreno",
                    options=indices,
                    format_func=lambda x: _INDICE_LABEL[x],
                    index=indices.index(r.indice_terreno) if r.indice_terreno in indices else 2,
                    key="raj_indice_terr",
                    disabled=not aplic_terr,
                )

    # ================================================================
    # IPCA e IGP-M — campos consolidados (evita duplicar inputs)
    # Se o indice_parc ja usou ipca ou igpm, reutiliza o valor
    # ================================================================
    ipca_final = taxa_parc_input if indice_parc == "ipca" else float(r.ipca_anual_pct)
    igpm_final = taxa_parc_input if indice_parc == "igpm" else float(r.igpm_anual_pct)

    # Se terreno usa ipca ou igpm e ainda nao foi definido acima, pedir
    if aplic_terr and indice_terr == "ipca" and indice_parc != "ipca":
        ipca_final = numero_brl(
            "IPCA projetado para o terreno (% a.a.)",
            value=float(r.ipca_anual_pct),
            key="raj_ipca_terr",
            min_value=0.0,
            max_value=50.0,
        )
    if aplic_terr and indice_terr == "igpm" and indice_parc != "igpm":
        igpm_final = numero_brl(
            "IGP-M projetado para o terreno (% a.a.)",
            value=float(r.igpm_anual_pct),
            key="raj_igpm_terr",
            min_value=0.0,
            max_value=50.0,
        )

    btn_proximo_modulo("Dashboard", target_idx=0)

    # --- Auto-save ---
    _autosave(projeto, {
        "ativo": ativo,
        "aplicar_incc_obras": aplic_obras,
        "incc_anual_pct": incc_pct,
        "aplicar_correcao_parcelas": aplic_parc,
        "indice_parcelas": indice_parc,
        "ipca_anual_pct": ipca_final,
        "igpm_anual_pct": igpm_final,
        "aplicar_correcao_terreno": aplic_terr,
        "indice_terreno": indice_terr,
    })

    if resultado is None:
        st.info("Clique em **Calcular fluxo de caixa** na sidebar para ver o impacto dos reajustes.")
        return

    # ================================================================
    # SECAO 4 — IMPACTO LIQUIDO DOS REAJUSTES
    # ================================================================
    st.markdown("---")
    with st.container(border=True):
        st.markdown("#### 📊 Impacto Líquido dos Reajustes")

        r_sum = resultado.resumo
        ind   = resultado.indicadores

        receita_corr  = r_sum.get("receita_correcao_total",     0) or 0
        var_incc      = r_sum.get("variacao_custo_obras_incc",  0) or 0
        custo_base    = r_sum.get("custo_obras_base_constante", 0) or 0
        custo_nominal = r_sum.get("custo_obras",                0) or 0
        vgv_vendavel  = r_sum.get("vgv_vendavel",               1) or 1
        lucro         = r_sum.get("lucro_liquido",              0) or 0

        efeito_liquido = receita_corr - var_incc
        cor_efeito = "normal" if efeito_liquido >= 0 else "inverse"

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Receita adicional (correção parcelas)",
                formatar_brl(receita_corr),
                help="Correção monetária recebida nas parcelas durante a obra.",
            )
        with col2:
            st.metric(
                "Acréscimo de custo (INCC obras)",
                formatar_brl(var_incc),
                delta=f"{var_incc / custo_base * 100:.1f}% acima do orçamento" if custo_base > 0 and var_incc > 0 else None,
                delta_color="inverse",
                help="Quanto o INCC aumenta o custo nominal das obras em relação ao orçamento base.",
            )
        with col3:
            st.metric(
                "Efeito líquido no resultado",
                formatar_brl(efeito_liquido),
                delta=f"{efeito_liquido / vgv_vendavel * 100:.2f} p.p. de margem",
                delta_color=cor_efeito,
                help="Receita de correção menos acréscimo de custo = impacto líquido no lucro.",
            )

        # Resumo textual
        if efeito_liquido >= 0:
            st.success(
                f"✅ Os reajustes beneficiam o projeto em **{formatar_brl(efeito_liquido)}** "
                f"— a correção das parcelas supera o encarecimento das obras."
            )
        else:
            st.warning(
                f"⚠️ Os reajustes reduzem o resultado em **{formatar_brl(abs(efeito_liquido))}** "
                f"— o INCC das obras supera a correção recebida nas parcelas. "
                f"Considere repassar mais correção ao comprador ou reduzir o prazo de obra."
            )

        # Tabela de decomposição
        with st.expander("Ver decomposição detalhada"):
            st.caption("Comparativo preços constantes vs preços nominais com reajuste")
            st.table({
                "Item": [
                    "Custo obras (orçamento base — preços constantes)",
                    "Custo obras (nominal com INCC)",
                    "Acréscimo INCC obras",
                    "Receita correção parcelas",
                    "Efeito líquido no resultado",
                    "Lucro líquido (com reajustes)",
                ],
                "Valor (R$)": [
                    formatar_brl(custo_base),
                    formatar_brl(custo_nominal),
                    formatar_brl(var_incc),
                    formatar_brl(receita_corr),
                    formatar_brl(efeito_liquido),
                    formatar_brl(lucro),
                ],
            })
