"""
Aba Terreno — Forma de Aquisicao do Terreno.

Tres opcoes mutuamente exclusivas:
1. Aquisicao Direta  — compra com desembolso (a vista, parcelado ou fluxo livre)
2. Permuta Financeira — terrenista recebe % das receitas (com descontos e fluxo personalizado)
3. Permuta Fisica    — terrenista recebe lotes de cada tipologia
"""

from __future__ import annotations

import streamlit as st

from ...modelos import (
    Aba2Receitas,
    Aba5Impostos,
    AquisicaoTerreno,
    DescontosPermuta,
    PermutaFinanceira,
    PermutaFisicaTipologia,
    RetencaoPermuta,
)
from ..helpers import (
    aviso_validacao,
    btn_proximo_modulo,
    cabecalho_aba,
    formatar_brl,
    get_projeto,
    horizonte_visual_projeto,
    invalidar_resultado,
    marcos_projeto,
    numero_brl,
    set_projeto,
)
from ..tabela_mensal import (
    gerar_distribuicao_linear,
    tabela_mensal_distribuicao,
)


CHAVE_FLUXO = "aba_terreno_fluxo_distrib"

_MODO_LABEL = {
    "sem_pagamento": "Sem Pagamento de Terreno (permuta total ou doacao)",
    "direta": "Aquisicao Direta (compra em dinheiro)",
    "permuta_financeira": "Permuta Financeira (% das receitas ao terrenista)",
    "permuta_fisica": "Permuta Fisica (lotes ao terrenista)",
}

_TIPO_PERMUTA_PARA_MODO = {
    "sem_permuta": "direta",
    "financeira": "permuta_financeira",
    "fisica": "permuta_fisica",
}
_MODO_PARA_TIPO_PERMUTA = {v: k for k, v in _TIPO_PERMUTA_PARA_MODO.items()}
_MODO_PARA_TIPO_PERMUTA["sem_pagamento"] = "sem_permuta"


def _garantir_estado(projeto) -> None:
    if CHAVE_FLUXO not in st.session_state:
        acq = projeto.aquisicao
        if acq.forma_pagamento == "customizado" and acq.fluxo_percentuais:
            distrib = {
                acq.fluxo_mes_inicio + k: pct
                for k, pct in enumerate(acq.fluxo_percentuais)
                if pct > 0
            }
        else:
            distrib = {}
        st.session_state[CHAVE_FLUXO] = distrib


def _distrib_dict_para_lista(distrib: dict) -> tuple[int, list[float]]:
    if not distrib:
        return 0, []
    mes_min = min(distrib.keys())
    mes_max = max(distrib.keys())
    lista = [distrib.get(mes_min + k, 0.0) for k in range(mes_max - mes_min + 1)]
    return mes_min, lista


# ============================================================
# OPCAO 1 — AQUISICAO DIRETA
# ============================================================

def _renderizar_opcao_direta(projeto, horizonte, marcos) -> dict:
    aquisicao = projeto.aquisicao

    st.markdown("---")
    st.markdown("#### Aquisicao Direta")

    col1, col2 = st.columns(2)
    with col1:
        valor_total = numero_brl(
            "Valor total do terreno (R$)",
            value=float(aquisicao.valor_total),
            key="ater_valor",
            min_value=0.01,
        )
        custo_cartorio = numero_brl(
            "Cartorio, escritura e registro (R$)",
            value=float(aquisicao.custo_cartorio),
            key="ater_cartorio",
            min_value=0.0,
        )
    with col2:
        mes_cartorio = numero_brl(
            "Mes do cartorio / registro (M0 = mes inicial)",
            value=float(aquisicao.mes_pagamento_cartorio),
            key="ater_mes_cart",
            min_value=0.0,
            max_value=float(horizonte),
            casas=0,
        )
        st.metric("Custo total (terreno + cartorio)", formatar_brl(valor_total + custo_cartorio))

    st.markdown("**Fluxo de aportes:**")
    forma_atual = aquisicao.forma_pagamento
    if forma_atual not in ("a_vista", "parcelado", "customizado"):
        forma_atual = "a_vista"
    forma = st.radio(
        "Forma de pagamento",
        options=["a_vista", "parcelado", "customizado"],
        format_func=lambda x: {
            "a_vista": "A vista (pagamento unico)",
            "parcelado": "Parcelado (N parcelas iguais)",
            "customizado": "Distribuicao personalizada (tabela mensal livre)",
        }[x],
        index=["a_vista", "parcelado", "customizado"].index(forma_atual),
        horizontal=True,
        key="ater_forma",
    )

    mes_pgto = aquisicao.mes_pagamento
    mes_ini_parc = aquisicao.mes_inicio_parcelas
    qtd_parc = max(int(aquisicao.qtd_parcelas), 2)
    distrib: dict = {}

    if forma == "a_vista":
        mes_pgto = numero_brl(
            "Mes de pagamento",
            value=float(aquisicao.mes_pagamento),
            key="ater_mes_pgto",
            min_value=0.0,
            max_value=float(horizonte),
            casas=0,
        )

    elif forma == "parcelado":
        col1, col2 = st.columns(2)
        with col1:
            mes_ini_parc = numero_brl(
                "Mes inicio das parcelas",
                value=float(aquisicao.mes_inicio_parcelas),
                key="ater_ini_parc",
                min_value=0.0,
                max_value=float(horizonte),
                casas=0,
            )
        with col2:
            qtd_parc = numero_brl(
                "Quantidade de parcelas",
                value=float(max(int(aquisicao.qtd_parcelas), 2)),
                key="ater_qtd_parc",
                min_value=2.0,
                casas=0,
            )
        parcela = valor_total / int(qtd_parc) if qtd_parc > 0 else 0
        st.caption(
            f"Parcela mensal: {formatar_brl(parcela)} — de M{int(mes_ini_parc)} a "
            f"M{int(mes_ini_parc) + int(qtd_parc) - 1}"
        )

    elif forma == "customizado":
        st.caption(
            "Distribua o valor total mes a mes. A soma deve ser 100%. "
            "Use o atalho 'Linear' para distribuir igualmente em um intervalo."
        )
        col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
        with col_a:
            mi_lin = numero_brl(
                "Mes inicio",
                value=0.0,
                key="ater_cu_mi",
                min_value=0.0,
                max_value=float(horizonte),
                casas=0,
            )
        with col_b:
            mf_lin = numero_brl(
                "Mes fim",
                value=float(min(11, horizonte)),
                key="ater_cu_mf",
                min_value=0.0,
                max_value=float(horizonte),
                casas=0,
            )
        with col_c:
            st.markdown("&nbsp;")
            if st.button("Linear", key="ater_cu_btn_lin", use_container_width=True):
                st.session_state[CHAVE_FLUXO] = gerar_distribuicao_linear(mi_lin, mf_lin)
                st.rerun()
        with col_d:
            st.markdown("&nbsp;")
            if st.button("🧹 Limpar", key="ater_cu_btn_clear", use_container_width=True):
                st.session_state[CHAVE_FLUXO] = {}
                st.rerun()

        distrib = tabela_mensal_distribuicao(
            nome_unico="terreno_custom",
            horizonte_meses=horizonte,
            valores_iniciais=st.session_state[CHAVE_FLUXO],
            marcos=marcos,
        )
        st.session_state[CHAVE_FLUXO] = distrib

        soma = sum(distrib.values())
        if abs(soma - 100.0) < 0.01:
            st.success(f"✅ Soma: {soma:.2f}%")
        elif soma == 0:
            st.info("Preencha a distribuicao mensal acima.")
        else:
            st.warning(f"⚠️ Soma: {soma:.2f}% (deve ser 100%)")

    return {
        "valor_total": valor_total,
        "forma": forma,
        "mes_pgto": int(mes_pgto),
        "mes_ini_parc": int(mes_ini_parc),
        "qtd_parc": int(qtd_parc),
        "distrib": distrib,
        "custo_cartorio": custo_cartorio,
        "mes_cartorio": int(mes_cartorio),
    }


# ============================================================
# OPCAO 2 — PERMUTA FINANCEIRA
# ============================================================

def _renderizar_opcao_permuta_financeira(projeto) -> dict:
    pf_atual = projeto.impostos.permuta_financeira

    st.markdown("---")
    st.markdown("#### Permuta Financeira")
    st.caption(
        "O terrenista nao recebe pagamento em dinheiro pela terra. Em vez disso, recebe um "
        "percentual das receitas do empreendimento ao longo do tempo."
    )

    col1, col2 = st.columns(2)
    with col1:
        pct_receitas = numero_brl(
            "% das receitas brutas ao terrenista",
            value=float(pf_atual.percentual_vgv) if pf_atual else 15.0,
            key="ater_pf_pct",
            min_value=0.01,
            max_value=100.0,
            help="Percentual bruto aplicado sobre a receita (antes dos descontos abaixo). "
                 "Pratica comum: 15% a 25% do VGV.",
        )
    with col2:
        fluxo_tipo = st.radio(
            "Tipo de fluxo",
            options=["padrao", "personalizado"],
            format_func=lambda x: {
                "padrao": "Padrao (proporcional a cada recebimento)",
                "personalizado": "Personalizado (periodo de retencao + quitacao)",
            }[x],
            index=0 if (not pf_atual or pf_atual.fluxo == "padrao") else 1,
            key="ater_pf_fluxo",
        )

    # Descontos
    st.markdown("---")
    st.markdown("**Descontos sobre a base de calculo:**")
    st.caption(
        "Informe os percentuais que serao deduzidos da receita bruta antes de calcular "
        "a parcela do terrenista. Isso reflete que o terrenista recebe % da "
        "**receita liquida**, ja descontados os custos do empreendimento."
    )

    d = pf_atual.descontos if pf_atual else DescontosPermuta()
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        d_imp = numero_brl("Impostos (%)", value=float(d.impostos), key="ater_d_imp", min_value=0.0)
    with col2:
        d_com = numero_brl("Comissao (%)", value=float(d.comissao), key="ater_d_com", min_value=0.0)
    with col3:
        d_mkt = numero_brl("Marketing (%)", value=float(d.marketing), key="ater_d_mkt", min_value=0.0)
    with col4:
        d_gest = numero_brl("Gest. carteira (%)", value=float(d.gestao_carteira), key="ater_d_gest", min_value=0.0)
    with col5:
        d_out = numero_brl("Outros (%)", value=float(d.outros), key="ater_d_out", min_value=0.0)

    total_desc = d_imp + d_com + d_mkt + d_gest + d_out
    base_efetiva_pct = max(100.0 - total_desc, 0.0)
    efetivo_pct = pct_receitas * base_efetiva_pct / 100.0

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Total de descontos", f"{total_desc:.2f}%")
    with col_m2:
        st.metric("Base efetiva", f"{base_efetiva_pct:.2f}% da receita bruta")
    with col_m3:
        st.metric("% efetivo s/ receita bruta", f"{efetivo_pct:.2f}%",
                  help="O terrenista recebera efetivamente esse % da receita bruta a cada mes.")

    # Fluxo personalizado
    ret_atual = pf_atual.retencao if pf_atual else RetencaoPermuta()

    if fluxo_tipo == "personalizado":
        st.markdown("---")
        st.markdown("**Periodo de Retencao e Quitacao:**")
        st.caption(
            "Durante os primeiros N meses, uma parte da parcela devida ao terrenista "
            "fica retida (para fazer frente a outras despesas do empreendimento). "
            "Ao termino do periodo, o valor retido e corrigido e quitado em parcelas mensais."
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            meses_ret = numero_brl(
                "Meses de retencao",
                value=float(ret_atual.meses_retencao),
                key="ater_ret_m",
                min_value=1.0,
                casas=0,
                help="Quantidade de meses iniciais em que parte do repasse fica retida.",
            )
        with col2:
            pct_ret = numero_brl(
                "% retido por mes",
                value=float(ret_atual.percentual_retencao),
                key="ater_ret_pct",
                min_value=0.0,
                max_value=100.0,
                help="Percentual da parcela devida que NAO e repassada durante o periodo.",
            )
        with col3:
            corr_aa = numero_brl(
                "Correcao a.a. (%)",
                value=float(ret_atual.correcao_aa),
                key="ater_ret_corr",
                min_value=0.0,
                help="Taxa de correcao aplicada sobre o valor acumulado retido.",
            )
        with col4:
            qtd_quit = numero_brl(
                "Parcelas p/ quitacao",
                value=float(ret_atual.qtd_parcelas_quitacao),
                key="ater_ret_quit",
                min_value=1.0,
                casas=0,
                help="Em quantas parcelas mensais o valor retido sera quitado.",
            )

        st.info(
            f"💡 Nos primeiros **{int(meses_ret)} meses**, apenas **{100 - pct_ret:.0f}%** "
            f"da parcela devida sera repassada ao terrenista. "
            f"O **{pct_ret:.0f}%** retido acumula e e corrigido a **{corr_aa:.1f}% a.a.**, "
            f"sendo quitado em **{int(qtd_quit)} parcelas** a partir do mes {int(meses_ret)}. "
            f"Apos esse periodo, o repasse integral retorna normalmente."
        )
    else:
        meses_ret = float(ret_atual.meses_retencao)
        pct_ret = float(ret_atual.percentual_retencao)
        corr_aa = float(ret_atual.correcao_aa)
        qtd_quit = float(ret_atual.qtd_parcelas_quitacao)

    return {
        "percentual_vgv": pct_receitas,
        "fluxo": fluxo_tipo,
        "descontos": {
            "impostos": d_imp,
            "comissao": d_com,
            "marketing": d_mkt,
            "gestao_carteira": d_gest,
            "outros": d_out,
        },
        "retencao": {
            "meses_retencao": int(meses_ret),
            "percentual_retencao": pct_ret,
            "correcao_aa": corr_aa,
            "qtd_parcelas_quitacao": int(qtd_quit),
        },
    }


# ============================================================
# OPCAO 3 — PERMUTA FISICA
# ============================================================

def _renderizar_opcao_permuta_fisica(projeto) -> list:
    import pandas as pd

    tipologias = projeto.terreno.tipologias
    if not tipologias:
        aviso_validacao("Cadastre tipologias na Aba 1 (Dados do Empreendimento) antes de configurar a permuta fisica.")
        return []

    st.markdown("---")
    st.markdown("#### Permuta Fisica")
    st.caption(
        "Informe o percentual de cada tipologia que sera entregue ao terrenista. "
        "Esses lotes sao retirados do estoque comercializavel — apenas o VGV restante "
        "sera a base de calculo das proximas etapas."
    )

    def _vgv_tip(t) -> float:
        if t.modo_preco == "por_m2":
            return t.quantidade * t.area_lote_m2 * t.valor_unitario
        return t.quantidade * t.valor_unitario

    mapa_atual = {p.tipologia: p.percentual for p in projeto.receitas.permuta_fisica}

    linhas = []
    for t in tipologias:
        vgv_t = _vgv_tip(t)
        pct = mapa_atual.get(t.nome, 0.0)
        linhas.append({
            "Tipologia": t.nome,
            "Lotes (total)": t.quantidade,
            "% ao terrenista": pct,
            "Lotes ao terrenista": int(round(t.quantidade * pct / 100)),
            "VGV da tipologia (R$)": vgv_t,
            "VGV ao terrenista (R$)": vgv_t * pct / 100,
        })

    df = pd.DataFrame(linhas)

    df_edit = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Tipologia", "Lotes (total)",
            "Lotes ao terrenista", "VGV da tipologia (R$)", "VGV ao terrenista (R$)",
        ],
        column_config={
            "% ao terrenista": st.column_config.NumberColumn(
                "% ao terrenista", min_value=0.0, max_value=100.0, step=5.0, format="%.1f"
            ),
            "Lotes ao terrenista": st.column_config.NumberColumn(format="%d"),
            "VGV da tipologia (R$)": st.column_config.NumberColumn(format="R$ %.0f"),
            "VGV ao terrenista (R$)": st.column_config.NumberColumn(format="R$ %.0f"),
        },
        key="ater_perm_fisica",
    )

    # Totalizador
    vgv_total = 0.0
    vgv_permuta = 0.0
    lotes_total = 0
    lotes_permuta = 0.0
    permuta_items = []

    for _, row in df_edit.iterrows():
        nome = str(row["Tipologia"])
        pct = float(row.get("% ao terrenista") or 0)
        tip = next((t for t in tipologias if t.nome == nome), None)
        if tip:
            vgv_t = _vgv_tip(tip)
            vgv_total += vgv_t
            vgv_permuta += vgv_t * pct / 100
            lotes_total += tip.quantidade
            lotes_permuta += tip.quantidade * pct / 100
            if pct > 0:
                try:
                    permuta_items.append(PermutaFisicaTipologia(tipologia=nome, percentual=pct))
                except Exception:
                    pass

    vgv_loteadora = vgv_total - vgv_permuta
    pct_permuta_total = vgv_permuta / vgv_total * 100 if vgv_total > 0 else 0.0

    st.markdown("**Resumo da Permuta Fisica:**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("VGV Bruto Total", formatar_brl(vgv_total))
    with col2:
        st.metric(
            "VGV ao Terrenista",
            formatar_brl(vgv_permuta),
            delta=f"{pct_permuta_total:.1f}% do total",
        )
    with col3:
        st.metric(
            "VGV Comercializavel (Loteadora)",
            formatar_brl(vgv_loteadora),
            delta=f"{100 - pct_permuta_total:.1f}% do total",
        )
    with col4:
        st.metric(
            "Lotes ao Terrenista",
            f"{int(lotes_permuta)} / {lotes_total}",
        )

    if vgv_permuta > 0:
        st.info(
            f"💡 Apenas o VGV comercializavel sera base de calculo nas proximas etapas: "
            f"**{formatar_brl(vgv_loteadora)}** ({100 - pct_permuta_total:.1f}% do VGV bruto)."
        )

    return permuta_items


# ============================================================
# AUTO-SAVE
# ============================================================

def _autosave(modo: str, result: dict | list, projeto) -> None:
    try:
        tipo_permuta = _MODO_PARA_TIPO_PERMUTA[modo]

        # --- Reconstruir AquisicaoTerreno ---
        if modo == "sem_pagamento":
            nova_acq = AquisicaoTerreno(
                valor_total=1.0,
                forma_pagamento="sem_desembolso",
            )
            nova_pf = None
            nova_permuta_fisica = []
        elif modo == "direta":
            d = result
            forma = d["forma"]
            if forma == "customizado":
                mes_min, lista_pct = _distrib_dict_para_lista(d["distrib"])
                nova_acq = AquisicaoTerreno(
                    valor_total=d["valor_total"],
                    forma_pagamento="customizado",
                    fluxo_mes_inicio=mes_min,
                    fluxo_percentuais=lista_pct,
                    custo_cartorio=d["custo_cartorio"],
                    mes_pagamento_cartorio=d["mes_cartorio"],
                )
            elif forma == "parcelado":
                nova_acq = AquisicaoTerreno(
                    valor_total=d["valor_total"],
                    forma_pagamento="parcelado",
                    mes_inicio_parcelas=d["mes_ini_parc"],
                    qtd_parcelas=max(d["qtd_parc"], 2),
                    custo_cartorio=d["custo_cartorio"],
                    mes_pagamento_cartorio=d["mes_cartorio"],
                )
            else:  # a_vista
                nova_acq = AquisicaoTerreno(
                    valor_total=d["valor_total"],
                    forma_pagamento="a_vista",
                    mes_pagamento=d["mes_pgto"],
                    custo_cartorio=d["custo_cartorio"],
                    mes_pagamento_cartorio=d["mes_cartorio"],
                )
            nova_pf = None
            nova_permuta_fisica = []
        elif modo in ("permuta_financeira", "permuta_fisica"):
            # Para permutas, sem desembolso de compra
            nova_acq = AquisicaoTerreno(
                valor_total=max(float(projeto.aquisicao.valor_total), 1.0),
                forma_pagamento="sem_desembolso",
            )
            if modo == "permuta_financeira":
                d = result
                nova_pf = PermutaFinanceira(
                    percentual_vgv=d["percentual_vgv"],
                    modo_pagamento="sobre_recebimento",
                    descontos=DescontosPermuta(**d["descontos"]),
                    fluxo=d["fluxo"],
                    retencao=RetencaoPermuta(**d["retencao"]),
                )
                nova_permuta_fisica = []
            else:  # permuta_fisica
                nova_pf = None
                nova_permuta_fisica = list(result)

        # --- Reconstruir Aba2Receitas (preservando fluxos e curva) ---
        nova_aba2 = projeto.receitas.model_copy(update={
            "tipo_permuta": tipo_permuta,
            "permuta_fisica": nova_permuta_fisica,
        })

        # --- Reconstruir Aba5Impostos (preservando tributos e comissao) ---
        nova_aba5 = projeto.impostos.model_copy(update={
            "permuta_financeira": nova_pf,
        })

        # Detectar mudanca
        json_antes = projeto.model_dump_json()
        projeto_atualizado = projeto.model_copy(update={
            "aquisicao": nova_acq,
            "receitas": nova_aba2,
            "impostos": nova_aba5,
        })
        if json_antes != projeto_atualizado.model_dump_json():
            set_projeto(projeto_atualizado)
            invalidar_resultado()

    except Exception:
        pass  # erros ficam visiveis no painel de pendencias


# ============================================================
# RENDERIZAR (ponto de entrada)
# ============================================================

def renderizar() -> None:
    cabecalho_aba(
        9,
        "Terreno",
        "Forma de aquisicao do terreno: compra direta, permuta financeira ou permuta fisica.",
    )

    projeto = get_projeto()
    _garantir_estado(projeto)

    horizonte = horizonte_visual_projeto(projeto)
    marcos = marcos_projeto(projeto)

    # Determinar modo atual a partir do projeto
    if projeto.aquisicao.forma_pagamento == "sem_desembolso" and projeto.receitas.tipo_permuta == "sem_permuta":
        modo_atual = "sem_pagamento"
    else:
        modo_atual = _TIPO_PERMUTA_PARA_MODO.get(projeto.receitas.tipo_permuta, "direta")

    _opcoes_modo = ["sem_pagamento", "direta", "permuta_financeira", "permuta_fisica"]
    st.markdown("#### Forma de Aquisicao")
    modo = st.radio(
        "Como o terreno foi adquirido?",
        options=_opcoes_modo,
        format_func=lambda x: _MODO_LABEL[x],
        index=_opcoes_modo.index(modo_atual) if modo_atual in _opcoes_modo else 0,
        horizontal=False,
        key="ater_modo",
    )

    # Renderizar secao da opcao selecionada
    if modo == "sem_pagamento":
        st.markdown("---")
        st.info(
            "O terreno nao tem custo direto de aquisicao neste cenario "
            "(ex.: doacao, integralizacao de capital, permuta total coberta pelas outras opcoes). "
            "Nenhum desembolso sera lancado no fluxo de caixa."
        )
        result = {}
    elif modo == "direta":
        result = _renderizar_opcao_direta(projeto, horizonte, marcos)
    elif modo == "permuta_financeira":
        result = _renderizar_opcao_permuta_financeira(projeto)
    else:
        result = _renderizar_opcao_permuta_fisica(projeto)

    # Navegacao para o proximo modulo
    btn_proximo_modulo("Receitas")

    # Auto-save
    _autosave(modo, result, projeto)
