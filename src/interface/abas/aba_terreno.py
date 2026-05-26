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
CHAVE_FLUXO_ENTRADA = "aba_terreno_fluxo_entrada_cash"  # customizado do componente dinheiro nas permutas

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
    acq = projeto.aquisicao
    if CHAVE_FLUXO not in st.session_state:
        if acq.forma_pagamento == "customizado" and acq.fluxo_percentuais:
            distrib = {
                acq.fluxo_mes_inicio + k: pct
                for k, pct in enumerate(acq.fluxo_percentuais)
                if pct > 0
            }
        else:
            distrib = {}
        st.session_state[CHAVE_FLUXO] = distrib
    if CHAVE_FLUXO_ENTRADA not in st.session_state:
        # Carrega distribuicao da entrada em dinheiro das permutas (forma customizado)
        _em_permuta = acq.forma_pagamento == "sem_desembolso" or projeto.receitas.tipo_permuta != "sem_permuta"
        if _em_permuta and acq.forma_pagamento == "customizado" and acq.fluxo_percentuais:
            _d = {
                acq.fluxo_mes_inicio + k: pct
                for k, pct in enumerate(acq.fluxo_percentuais)
                if pct > 0
            }
        else:
            _d = {}
        st.session_state[CHAVE_FLUXO_ENTRADA] = _d
    if "ater_tem_entrada_dinheiro" not in st.session_state:
        # True se ha um componente em dinheiro real salvo (nao o placeholder sem_desembolso)
        st.session_state["ater_tem_entrada_dinheiro"] = acq.forma_pagamento != "sem_desembolso"


def _distrib_dict_para_lista(distrib: dict) -> tuple[int, list[float]]:
    if not distrib:
        return 0, []
    mes_min = min(distrib.keys())
    mes_max = max(distrib.keys())
    lista = [distrib.get(mes_min + k, 0.0) for k in range(mes_max - mes_min + 1)]
    return mes_min, lista


# ============================================================
# COMPONENTE EM DINHEIRO (reutilizavel por qualquer modo de permuta)
# ============================================================

def _renderizar_componente_dinheiro(aquisicao, horizonte: int, marcos: dict) -> dict | None:
    """
    Secao opcional que adiciona um componente de pagamento em dinheiro
    a qualquer tipo de aquisicao (permuta fisica, financeira ou sem pagamento).

    Retorna dict com os dados do pagamento, ou None se o toggle estiver desligado.
    """
    st.markdown("---")
    tem_entrada = st.toggle(
        "Inclui também pagamento em dinheiro",
        key="ater_tem_entrada_dinheiro",
        help=(
            "Adiciona um componente de pagamento em dinheiro ao terrenista, "
            "além da permuta configurada acima. "
            "Ex.: entrada de R$ 200 mil à vista no ato + permuta de lotes."
        ),
    )

    if not tem_entrada:
        return None

    col1, col2, col3 = st.columns(3)
    with col1:
        _valor_default = float(aquisicao.valor_total) if aquisicao.forma_pagamento != "sem_desembolso" else 0.0
        valor_entrada = numero_brl(
            "Valor em dinheiro (R$)",
            value=_valor_default,
            key="ater_entrada_valor",
            min_value=0.01,
        )
    with col2:
        custo_cartorio_e = numero_brl(
            "Cartório / registro (R$)",
            value=float(aquisicao.custo_cartorio),
            key="ater_entrada_cartorio",
            min_value=0.0,
        )
    with col3:
        mes_cartorio_e = int(numero_brl(
            "Mês do cartório",
            value=float(aquisicao.mes_pagamento_cartorio),
            key="ater_entrada_mes_cart",
            min_value=0.0,
            max_value=float(horizonte),
            casas=0,
        ))

    _forma_atual = aquisicao.forma_pagamento if aquisicao.forma_pagamento != "sem_desembolso" else "a_vista"
    forma_e = st.radio(
        "Forma de pagamento em dinheiro",
        options=["a_vista", "parcelado", "customizado"],
        format_func=lambda x: {
            "a_vista": "À vista (pagamento único)",
            "parcelado": "Parcelado (N parcelas iguais)",
            "customizado": "Distribuição personalizada (tabela mensal livre)",
        }[x],
        index=["a_vista", "parcelado", "customizado"].index(_forma_atual),
        horizontal=True,
        key="ater_entrada_forma",
    )

    mes_pgto_e = int(aquisicao.mes_pagamento)
    mes_ini_parc_e = int(aquisicao.mes_inicio_parcelas)
    qtd_parc_e = max(int(aquisicao.qtd_parcelas), 2)
    distrib_e: dict = {}

    if forma_e == "a_vista":
        mes_pgto_e = int(numero_brl(
            "Mês de pagamento",
            value=float(aquisicao.mes_pagamento),
            key="ater_entrada_mes_pgto",
            min_value=0.0,
            max_value=float(horizonte),
            casas=0,
        ))

    elif forma_e == "parcelado":
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            mes_ini_parc_e = int(numero_brl(
                "Mês início das parcelas",
                value=float(aquisicao.mes_inicio_parcelas),
                key="ater_entrada_ini_parc",
                min_value=0.0,
                max_value=float(horizonte),
                casas=0,
            ))
        with col_p2:
            qtd_parc_e = int(numero_brl(
                "Quantidade de parcelas",
                value=float(max(int(aquisicao.qtd_parcelas), 2)),
                key="ater_entrada_qtd_parc",
                min_value=2.0,
                casas=0,
            ))
        _parcela_e = valor_entrada / qtd_parc_e if qtd_parc_e > 0 else 0
        st.caption(
            f"Parcela mensal: {formatar_brl(_parcela_e)} — "
            f"de M{mes_ini_parc_e} a M{mes_ini_parc_e + qtd_parc_e - 1}"
        )

    elif forma_e == "customizado":
        st.caption(
            "Distribua o valor total mês a mês. A soma deve ser 100%. "
            "Use o atalho 'Linear' para distribuir igualmente em um intervalo."
        )
        col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
        with col_a:
            mi_e = int(numero_brl(
                "Mês início",
                value=0.0,
                key="ater_entrada_cu_mi",
                min_value=0.0,
                max_value=float(horizonte),
                casas=0,
            ))
        with col_b:
            mf_e = int(numero_brl(
                "Mês fim",
                value=float(min(11, horizonte)),
                key="ater_entrada_cu_mf",
                min_value=0.0,
                max_value=float(horizonte),
                casas=0,
            ))
        with col_c:
            st.markdown("&nbsp;")
            if st.button("Linear", key="ater_entrada_btn_lin", width="stretch"):
                st.session_state[CHAVE_FLUXO_ENTRADA] = gerar_distribuicao_linear(mi_e, mf_e)
                st.rerun()
        with col_d:
            st.markdown("&nbsp;")
            if st.button("Limpar", key="ater_entrada_btn_clr", width="stretch", icon=":material/delete_sweep:"):
                st.session_state[CHAVE_FLUXO_ENTRADA] = {}
                st.rerun()

        distrib_e = tabela_mensal_distribuicao(
            nome_unico="terreno_entrada_cash",
            horizonte_meses=horizonte,
            valores_iniciais=st.session_state[CHAVE_FLUXO_ENTRADA],
            marcos=marcos,
        )
        st.session_state[CHAVE_FLUXO_ENTRADA] = distrib_e

        _soma_e = sum(distrib_e.values())
        if abs(_soma_e - 100.0) < 0.01:
            st.success(f"Soma: {_soma_e:.2f}%")
        elif _soma_e == 0:
            st.info("Preencha a distribuição mensal acima.")
        else:
            st.warning(f"Soma: {_soma_e:.2f}% — deve ser 100%")

    return {
        "valor_entrada": valor_entrada,
        "forma": forma_e,
        "mes_pgto": mes_pgto_e,
        "mes_ini_parc": mes_ini_parc_e,
        "qtd_parc": qtd_parc_e,
        "distrib": distrib_e,
        "custo_cartorio": custo_cartorio_e,
        "mes_cartorio": mes_cartorio_e,
    }


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
        # U5: valor por m² de gleba e por m² de lotes (unidade que o mercado negocia)
        _a_gleba = float(projeto.terreno.areas.area_gleba_m2) or 1.0
        _a_lotes = float(projeto.terreno.areas.area_lotes_m2) or 1.0
        from ..helpers import formatar_num as _fmt_n
        st.caption(
            f"≈ **R$ {_fmt_n(valor_total / _a_gleba, 2)}/m² de gleba** | "
            f"R$ {_fmt_n(valor_total / _a_lotes, 2)}/m² de lotes"
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
            if st.button("Linear", key="ater_cu_btn_lin", width="stretch"):
                st.session_state[CHAVE_FLUXO] = gerar_distribuicao_linear(mi_lin, mf_lin)
                st.rerun()
        with col_d:
            st.markdown("&nbsp;")
            if st.button("Limpar", key="ater_cu_btn_clear", width="stretch", icon=":material/delete_sweep:"):
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
            st.success(f"Soma: {soma:.2f}%")
        elif soma == 0:
            st.info("Preencha a distribuicao mensal acima.")
        else:
            st.warning(f"Soma: {soma:.2f}% — deve ser 100%")

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
            f"Nos primeiros **{int(meses_ret)} meses**, apenas **{100 - pct_ret:.0f}%** "
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
    tipologias = projeto.terreno.tipologias
    if not tipologias:
        aviso_validacao("Cadastre tipologias em Identificação (sidebar → Dados) antes de configurar a permuta física.")
        return []

    st.markdown("---")
    st.markdown("#### Permuta Fisica")
    st.caption(
        "Informe o percentual de cada tipologia que sera entregue ao terrenista. "
        "Esses lotes sao retirados do estoque comercializavel — apenas o VGV restante "
        "sera a base de calculo das proximas etapas."
    )

    def _vgv_tip(t) -> float:
        return t.vgv_total  # usa a propriedade do modelo, que ja aplica o agio

    mapa_atual = {p.tipologia: p.percentual for p in projeto.receitas.permuta_fisica}

    # Cabecalho da tabela
    _col_w = [2, 1, 1.2, 1.2, 1.8, 1.8]
    _hcols = st.columns(_col_w)
    for _hc, _hl in zip(_hcols, ["Tipologia", "Lotes total", "% ao terrenista", "Lotes ao terrenista", "VGV tipologia", "VGV ao terrenista"]):
        with _hc:
            st.markdown(
                f'<div style="font-size:11px;color:#9CA3AF;font-weight:600;padding-bottom:2px;">{_hl}</div>',
                unsafe_allow_html=True,
            )

    # Totalizador
    vgv_total = 0.0
    vgv_permuta = 0.0
    lotes_total = 0
    lotes_permuta = 0.0
    permuta_items = []

    for i, t in enumerate(tipologias):
        vgv_t = _vgv_tip(t)
        _pct_committed = mapa_atual.get(t.nome, 0.0)

        _rcols = st.columns(_col_w)
        with _rcols[0]:
            st.markdown(
                f'<div style="padding:8px 0 0 0;font-size:13px;">{t.nome}</div>',
                unsafe_allow_html=True,
            )
        with _rcols[1]:
            st.markdown(
                f'<div style="padding:8px 0 0 0;font-size:13px;">{t.quantidade}</div>',
                unsafe_allow_html=True,
            )
        with _rcols[2]:
            pct_widget = numero_brl(
                "", value=float(_pct_committed),
                key=f"_pf_{i}_pct",
                min_value=0.0, max_value=100.0, casas=1,
                label_visibility="collapsed",
            )
        lotes_ter = int(round(t.quantidade * pct_widget / 100))
        vgv_ter = vgv_t * pct_widget / 100
        with _rcols[3]:
            st.markdown(
                f'<div style="padding:8px 0 0 0;font-size:13px;">{lotes_ter}</div>',
                unsafe_allow_html=True,
            )
        with _rcols[4]:
            st.markdown(
                f'<div style="padding:8px 0 0 0;font-size:13px;">{formatar_brl(vgv_t)}</div>',
                unsafe_allow_html=True,
            )
        with _rcols[5]:
            st.markdown(
                f'<div style="padding:8px 0 0 0;font-size:13px;">{formatar_brl(vgv_ter)}</div>',
                unsafe_allow_html=True,
            )

        vgv_total += vgv_t
        vgv_permuta += vgv_ter
        lotes_total += t.quantidade
        lotes_permuta += t.quantidade * pct_widget / 100
        if pct_widget > 0:
            try:
                permuta_items.append(PermutaFisicaTipologia(tipologia=t.nome, percentual=pct_widget))
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
            f"Apenas o VGV comercializavel sera base de calculo nas proximas etapas: "
            f"**{formatar_brl(vgv_loteadora)}** ({100 - pct_permuta_total:.1f}% do VGV bruto)."
        )

    return permuta_items


# ============================================================
# AUTO-SAVE
# ============================================================

def _construir_acq_dinheiro(entrada: dict | None, acq_atual) -> AquisicaoTerreno:
    """
    Constroi um AquisicaoTerreno a partir dos dados do componente em dinheiro.
    Se entrada for None ou valor == 0, retorna sem_desembolso.
    """
    if not entrada or float(entrada.get("valor_entrada", 0) or 0) <= 0:
        return AquisicaoTerreno(
            valor_total=max(float(acq_atual.valor_total), 1.0),
            forma_pagamento="sem_desembolso",
        )
    d = entrada
    forma = d["forma"]
    if forma == "customizado":
        mes_min, lista_pct = _distrib_dict_para_lista(d["distrib"])
        return AquisicaoTerreno(
            valor_total=d["valor_entrada"],
            forma_pagamento="customizado",
            fluxo_mes_inicio=mes_min,
            fluxo_percentuais=lista_pct,
            custo_cartorio=d["custo_cartorio"],
            mes_pagamento_cartorio=d["mes_cartorio"],
        )
    if forma == "parcelado":
        return AquisicaoTerreno(
            valor_total=d["valor_entrada"],
            forma_pagamento="parcelado",
            mes_inicio_parcelas=d["mes_ini_parc"],
            qtd_parcelas=max(d["qtd_parc"], 2),
            custo_cartorio=d["custo_cartorio"],
            mes_pagamento_cartorio=d["mes_cartorio"],
        )
    # a_vista
    return AquisicaoTerreno(
        valor_total=d["valor_entrada"],
        forma_pagamento="a_vista",
        mes_pagamento=d["mes_pgto"],
        custo_cartorio=d["custo_cartorio"],
        mes_pagamento_cartorio=d["mes_cartorio"],
    )


def _autosave(modo: str, result: dict | list, projeto) -> None:
    try:
        tipo_permuta = _MODO_PARA_TIPO_PERMUTA[modo]

        # --- Reconstruir AquisicaoTerreno ---
        if modo == "sem_pagamento":
            nova_acq = _construir_acq_dinheiro(result.get("entrada_dinheiro"), projeto.aquisicao)
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
            nova_acq = _construir_acq_dinheiro(result.get("entrada_dinheiro"), projeto.aquisicao)
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
                _pf_data = result.get("permuta_items") if isinstance(result, dict) else result
                nova_permuta_fisica = list(_pf_data) if _pf_data else []

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
    result: dict = {}
    _aviso_renderizacao: str | None = None

    try:
        if modo == "sem_pagamento":
            st.markdown("---")
            st.info(
                "O terreno nao tem custo direto de aquisicao neste cenario "
                "(ex.: doacao, integralizacao de capital, permuta total coberta pelas outras opcoes). "
                "Nenhum desembolso sera lancado no fluxo de caixa."
            )
            try:
                result["entrada_dinheiro"] = _renderizar_componente_dinheiro(
                    projeto.aquisicao, horizonte, marcos
                )
            except Exception:
                pass
        elif modo == "direta":
            try:
                r = _renderizar_opcao_direta(projeto, horizonte, marcos)
                if isinstance(r, dict):
                    result = r
            except Exception:
                pass
        elif modo == "permuta_financeira":
            try:
                r = _renderizar_opcao_permuta_financeira(projeto)
                if isinstance(r, dict):
                    result = r
            except Exception:
                pass
            try:
                result["entrada_dinheiro"] = _renderizar_componente_dinheiro(
                    projeto.aquisicao, horizonte, marcos
                )
            except Exception:
                pass
        else:  # permuta_fisica
            _pf_items: list = []
            try:
                _pf_items = _renderizar_opcao_permuta_fisica(projeto)
            except Exception:
                pass
            _dinheiro = None
            try:
                _dinheiro = _renderizar_componente_dinheiro(
                    projeto.aquisicao, horizonte, marcos
                )
            except Exception:
                pass
            result = {"permuta_items": _pf_items, "entrada_dinheiro": _dinheiro}
    except Exception:
        _aviso_renderizacao = (
            "Parte dos campos nao pode ser exibida. "
            "Os dados salvos anteriormente foram preservados. "
            "Tente navegar para outra aba e voltar."
        )

    if _aviso_renderizacao:
        st.warning(_aviso_renderizacao)

    # Navegacao para o proximo modulo
    try:
        btn_proximo_modulo("Receitas")
    except Exception:
        pass

    # Auto-save
    _autosave(modo, result, projeto)
