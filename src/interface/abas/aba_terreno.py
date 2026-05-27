"""
Aba Terreno — Forma de Aquisicao do Terreno.

Tres formas independentes, selecionaveis em qualquer combinacao (multi-select):
1. Permuta Fisica    — terrenista recebe lotes de cada tipologia
2. Permuta Financeira — terrenista recebe % das receitas
3. Torna             — pagamento em dinheiro ao terrenista
Se nenhuma opcao for marcada, o terreno nao tem custo de aquisicao.
"""

from __future__ import annotations

import streamlit as st

from ...modelos import (
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


CHAVE_FLUXO_ENTRADA = "aba_terreno_fluxo_entrada_cash"


def _garantir_estado(projeto) -> None:
    acq = projeto.aquisicao
    if CHAVE_FLUXO_ENTRADA not in st.session_state:
        if acq.forma_pagamento == "customizado" and acq.fluxo_percentuais:
            _d = {
                acq.fluxo_mes_inicio + k: pct
                for k, pct in enumerate(acq.fluxo_percentuais)
                if pct > 0
            }
        else:
            _d = {}
        st.session_state[CHAVE_FLUXO_ENTRADA] = _d


def _distrib_dict_para_lista(distrib: dict) -> tuple[int, list[float]]:
    if not distrib:
        return 0, []
    mes_min = min(distrib.keys())
    mes_max = max(distrib.keys())
    lista = [distrib.get(mes_min + k, 0.0) for k in range(mes_max - mes_min + 1)]
    return mes_min, lista


def _construir_acq_dinheiro(entrada: dict | None, acq_atual) -> AquisicaoTerreno:
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
    return AquisicaoTerreno(
        valor_total=d["valor_entrada"],
        forma_pagamento="a_vista",
        mes_pagamento=d["mes_pgto"],
        custo_cartorio=d["custo_cartorio"],
        mes_pagamento_cartorio=d["mes_cartorio"],
    )


# ============================================================
# TORNA (pagamento em dinheiro)
# ============================================================

def _renderizar_torna(aquisicao, horizonte: int, marcos: dict) -> dict:
    col1, col2, col3 = st.columns(3)
    with col1:
        _valor_default = float(aquisicao.valor_total) if aquisicao.forma_pagamento != "sem_desembolso" else 1.0
        valor_entrada = numero_brl(
            "Valor em dinheiro (R$)",
            value=max(_valor_default, 0.01),
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
        "Forma de pagamento",
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
# PERMUTA FINANCEIRA
# ============================================================

def _renderizar_opcao_permuta_financeira(projeto) -> dict:
    pf_atual = projeto.impostos.permuta_financeira

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

    st.markdown("**Descontos sobre a base de calculo:**")

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

    ret_atual = pf_atual.retencao if pf_atual else RetencaoPermuta()

    if fluxo_tipo == "personalizado":
        st.markdown("**Periodo de Retencao e Quitacao:**")

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
            f"sendo quitado em **{int(qtd_quit)} parcelas** a partir do mes {int(meses_ret)}."
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
# PERMUTA FISICA
# ============================================================

def _renderizar_opcao_permuta_fisica(projeto) -> list:
    tipologias = projeto.terreno.tipologias
    if not tipologias:
        aviso_validacao("Cadastre tipologias em Identificação (sidebar → Dados) antes de configurar a permuta física.")
        return []

    def _vgv_tip(t) -> float:
        return t.vgv_total

    mapa_atual = {p.tipologia: p.percentual for p in projeto.receitas.permuta_fisica}

    _col_w = [2, 1, 1.2, 1.2, 1.8, 1.8]
    _hcols = st.columns(_col_w)
    for _hc, _hl in zip(_hcols, ["Tipologia", "Lotes total", "% ao terrenista", "Lotes ao terrenista", "VGV tipologia", "VGV ao terrenista"]):
        with _hc:
            st.markdown(
                f'<div style="font-size:11px;color:#9CA3AF;font-weight:600;padding-bottom:2px;">{_hl}</div>',
                unsafe_allow_html=True,
            )

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

def _renderizar_socio_terrenista(projeto) -> dict:
    acq = projeto.aquisicao
    pct_atual = float(getattr(acq, "pct_socio_terrenista", 0.0))

    col1, col2 = st.columns([1, 2])
    with col1:
        pct = numero_brl(
            "Participação no resultado (%)",
            value=pct_atual,
            key="ater_st_pct",
            min_value=0.01,
            max_value=99.0,
            help=(
                "% do resultado líquido do negócio que o terrenista receberá como sócio. "
                "Pago somente após término de obras, caixa positivo e quitação total do financiamento bancário."
            ),
        )
    with col2:
        st.info(
            f"O terrenista recebe **{pct:.1f}% do resultado líquido** do negócio. "
            "O pagamento é progressivo, iniciando apenas após: "
            "**1)** término de obras, **2)** caixa positivo e **3)** quitação total do financiamento bancário."
        )
    return {"pct_socio_terrenista": pct}


def _autosave_multi(tem_fisica: bool, tem_financeira: bool, tem_torna: bool, tem_st: bool, result: dict, projeto) -> None:
    try:
        # tipo_permuta: "fisica" tem prioridade pois afeta VGV vendavel (exigido pelo validador do modelo)
        if tem_fisica:
            tipo_permuta = "fisica"
            nova_permuta_fisica = result.get("permuta_items") or []
        else:
            tipo_permuta = "financeira" if tem_financeira else "sem_permuta"
            nova_permuta_fisica = []

        # permuta financeira — independente de tipo_permuta, engine le de impostos.permuta_financeira
        if tem_financeira and "percentual_vgv" in result:
            nova_pf = PermutaFinanceira(
                percentual_vgv=result["percentual_vgv"],
                modo_pagamento="sobre_recebimento",
                descontos=DescontosPermuta(**result["descontos"]),
                fluxo=result["fluxo"],
                retencao=RetencaoPermuta(**result["retencao"]),
            )
        else:
            nova_pf = None

        # torna (cash)
        if tem_torna and result.get("entrada_dinheiro"):
            nova_acq = _construir_acq_dinheiro(result["entrada_dinheiro"], projeto.aquisicao)
        else:
            nova_acq = AquisicaoTerreno(
                valor_total=max(float(projeto.aquisicao.valor_total), 1.0),
                forma_pagamento="sem_desembolso",
            )

        # socio terrenista — sobrescreve os campos de socio mantendo o resto da aquisicao
        pct_st = float(result.get("pct_socio_terrenista", 0.0)) if tem_st else 0.0
        nova_acq = nova_acq.model_copy(update={
            "ativo_socio_terrenista": tem_st,
            "pct_socio_terrenista": pct_st,
        })

        nova_aba2 = projeto.receitas.model_copy(update={
            "tipo_permuta": tipo_permuta,
            "permuta_fisica": nova_permuta_fisica,
        })
        nova_aba5 = projeto.impostos.model_copy(update={
            "permuta_financeira": nova_pf,
        })

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
        pass


# ============================================================
# RENDERIZAR (ponto de entrada)
# ============================================================

def renderizar() -> None:
    cabecalho_aba(9, "Terreno")

    projeto = get_projeto()
    _garantir_estado(projeto)

    horizonte = horizonte_visual_projeto(projeto)
    marcos = marcos_projeto(projeto)

    # Inferir estado inicial dos checkboxes a partir do projeto salvo
    _fisica_default = bool(projeto.receitas.permuta_fisica)
    _financeira_default = projeto.impostos.permuta_financeira is not None
    _torna_default = projeto.aquisicao.forma_pagamento != "sem_desembolso"
    _st_default = bool(getattr(projeto.aquisicao, "ativo_socio_terrenista", False))

    with st.container(border=True):
        st.markdown("#### Forma de Aquisição")
        col_f, col_fin, col_t, col_st = st.columns(4)
        with col_f:
            tem_fisica = st.checkbox(
                "Permuta Física",
                value=_fisica_default,
                key="ater_tem_fisica",
                help="Terrenista recebe lotes como parte do pagamento.",
            )
        with col_fin:
            tem_financeira = st.checkbox(
                "Permuta Financeira",
                value=_financeira_default,
                key="ater_tem_financeira",
                help="Terrenista recebe % das receitas do empreendimento.",
            )
        with col_t:
            tem_torna = st.checkbox(
                "Torna",
                value=_torna_default,
                key="ater_tem_torna",
                help="Pagamento em dinheiro ao terrenista, além das permutas.",
            )
        with col_st:
            tem_st = st.checkbox(
                "Sócio Terrenista",
                value=_st_default,
                key="ater_tem_st",
                help="Terrenista recebe % do resultado líquido do negócio, pago após quitação do financiamento bancário.",
            )

    result: dict = {}

    if tem_fisica:
        with st.container(border=True):
            st.markdown("#### Permuta Física")
            try:
                result["permuta_items"] = _renderizar_opcao_permuta_fisica(projeto)
            except Exception:
                result["permuta_items"] = []
    else:
        result["permuta_items"] = []

    if tem_financeira:
        with st.container(border=True):
            st.markdown("#### Permuta Financeira")
            try:
                r = _renderizar_opcao_permuta_financeira(projeto)
                result.update(r)
            except Exception:
                pass

    if tem_torna:
        with st.container(border=True):
            st.markdown("#### Torna")
            try:
                result["entrada_dinheiro"] = _renderizar_torna(
                    projeto.aquisicao, horizonte, marcos
                )
            except Exception:
                result["entrada_dinheiro"] = None
    else:
        result["entrada_dinheiro"] = None

    if tem_st:
        with st.container(border=True):
            st.markdown("#### Sócio Terrenista")
            try:
                r_st = _renderizar_socio_terrenista(projeto)
                result.update(r_st)
            except Exception:
                pass

    # Salvar aba
    st.markdown("---")
    _col_sv_terr, _ = st.columns([1, 3])
    with _col_sv_terr:
        if st.button(
            "Salvar aba",
            key="aba_terreno_salvar_aba",
            type="primary",
            width="stretch",
            icon=":material/save:",
        ):
            _autosave_multi(tem_fisica, tem_financeira, tem_torna, tem_st, result, projeto)
            st.rerun()

    try:
        btn_proximo_modulo("Receitas")
    except Exception:
        pass

    _autosave_multi(tem_fisica, tem_financeira, tem_torna, tem_st, result, projeto)
