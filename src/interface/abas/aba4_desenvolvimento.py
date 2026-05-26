"""
Aba 4 — Custos de Desenvolvimento e Marketing.

Refatorada na Fase 2.4:
- Auto-save: alteracoes salvam ao mudar de campo (sem botao "Salvar Aba")
- Atalhos contextuais por categoria (ex.: para "marketing" sugere "linear
  do lancamento ao fim das obras")
- Filtro de meses preenchidos (mostra so os meses com %, mais 3 antes/depois)
- Labels em linguagem mais imobiliaria
"""

from __future__ import annotations

import streamlit as st

from ...modelos import (
    Aba4Desenvolvimento,
    Administracao,
    Aba5Impostos,
    ComissaoVenda,
    DespesaTemporal,
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
    atalhos_contextuais,
    atalhos_por_intervalos,
    distribuicao_lista_para_dict,
    gerar_distribuicao_a_vista,
    gerar_distribuicao_linear,
    tabela_mensal_distribuicao,
)


CHAVE_DESPESAS = "aba4_lista_despesas"
CHAVE_FILTRO_MESES = "aba4_filtro_meses"

# Opcoes para o seletor "+ Adicionar despesa"
_OPCOES_DESPESA = [
    "Personalizado",
    "Levantamento Topografico e Sondagem",
    "Projeto Urbanistico Completo",
    "Projetos Complementares (Drenagem, Pavimentacao, Eletrico, Agua/Esgoto)",
    "Licenciamento Ambiental (LP / LI / LO)",
    "Aprovacao do Parcelamento na Prefeitura",
    "Registro do Loteamento em Cartorio",
    "Medida Compensatoria Urbana e Ambiental",
    "Marketing e Vendas (Stand, Material, Publicidade)",
    "Assessoria Juridica",
]

_CATEGORIA_DESPESA = {
    "Levantamento Topografico e Sondagem": "projetos",
    "Projeto Urbanistico Completo": "projetos",
    "Projetos Complementares (Drenagem, Pavimentacao, Eletrico, Agua/Esgoto)": "projetos",
    "Licenciamento Ambiental (LP / LI / LO)": "licenciamento",
    "Aprovacao do Parcelamento na Prefeitura": "licenciamento",
    "Registro do Loteamento em Cartorio": "licenciamento",
    "Medida Compensatoria Urbana e Ambiental": "licenciamento",
    "Marketing e Vendas (Stand, Material, Publicidade)": "marketing",
    "Assessoria Juridica": "outros",
}


def _carregar_despesas_do_projeto() -> list[dict]:
    projeto = get_projeto()
    out = []
    for d in projeto.desenvolvimento.despesas:
        if d.modo == "a_vista" and d.mes_pagamento is not None:
            distrib = gerar_distribuicao_a_vista(d.mes_pagamento)
        elif d.modo == "parcelado_linear" and d.mes_inicio is not None and d.mes_fim is not None:
            distrib = gerar_distribuicao_linear(d.mes_inicio, d.mes_fim)
        elif d.modo == "distribuicao_customizada" and d.mes_inicio is not None:
            distrib = distribuicao_lista_para_dict(d.distribuicao_percentual, d.mes_inicio)
        else:
            distrib = {}

        out.append({
            "nome": d.nome,
            "categoria": d.categoria,
            "valor_total": d.valor_total,
            "modo_valor": d.modo_valor,
            "percentual_vgv": d.percentual_vgv,
            "distribuicao": distrib,
        })
    return out


def _despesas_padrao_loteamento(projeto) -> list[dict]:
    """
    Despesas tipicas de loteamento com distribuicao temporal vinculada aos marcos
    reais do projeto (aprovacao, inicio/fim de obras, lancamento de vendas).
    Valores zerados — o usuario preenche; as curvas ja estao prontas.
    """
    from ...engine.utilidades import meses_entre

    inicio  = projeto.terreno.datas.inicio_projeto
    m_aprov = meses_entre(inicio, projeto.terreno.datas.aprovacao)
    m_lanc  = meses_entre(inicio, projeto.terreno.datas.lancamento_vendas)
    m_ini   = meses_entre(inicio, projeto.terreno.datas.inicio_obras)
    m_fim   = meses_entre(inicio, projeto.terreno.datas.termino_obras)

    def _lin(ini: int, fim: int, pct: float = 100.0) -> dict[int, float]:
        """Distribui pct% linearmente de ini ate fim (ambos inclusive)."""
        ini = max(0, int(ini))
        fim = max(ini, int(fim))
        n   = fim - ini + 1
        ppc = pct / n
        r   = {ini + i: ppc for i in range(n)}
        # Ajusta ultimo mes para soma exata
        soma = sum(r.values())
        if abs(soma - pct) > 1e-9:
            r[fim] += pct - soma
        return r

    def _av(mes: int, pct: float = 100.0) -> dict[int, float]:
        """Concentra pct% em um unico mes."""
        return {max(0, int(mes)): pct}

    def _merge(*dists: dict) -> dict[int, float]:
        r: dict[int, float] = {}
        for d in dists:
            for m, p in d.items():
                r[m] = r.get(m, 0.0) + p
        return r

    # ------------------------------------------------------------------ #
    # PROJETOS                                                             #
    # ------------------------------------------------------------------ #

    # Levantamento Topografico: execucao no inicio, precede a aprovacao
    levant = _lin(0, max(0, m_aprov - 1))

    # Projeto Urbanistico: desenvolvido desde M0 ate a aprovacao
    proj_urb = _lin(0, m_aprov)

    # Projetos Complementares: detalhamento entre aprovacao e inicio das obras
    proj_comp = _lin(m_aprov, max(m_aprov, m_ini))

    # ------------------------------------------------------------------ #
    # LICENCIAMENTO                                                        #
    # ------------------------------------------------------------------ #

    # Licenciamento Ambiental:
    #   50% fase LP (M0 ate mes anterior a aprovacao)
    #   30% fase LI (aprovacao ate mes anterior ao inicio de obras)
    #   20% fase LO (no termino das obras — emissao da LO)
    lic_amb = _merge(
        _lin(0,       max(0, m_aprov - 1),        50.0),
        _lin(m_aprov, max(m_aprov, m_ini - 1),    30.0),
        _av(m_fim,                                 20.0),
    )

    # Aprovacao na Prefeitura: custos distribuidos ate a aprovacao
    aprov_pref = _lin(0, m_aprov)

    # Registro em Cartorio: apos aprovacao, ate lancamento
    registro = _lin(m_aprov, max(m_aprov, m_lanc))

    # Medida Compensatoria:
    #   60% na aprovacao (condicao de LP/LI — valor calculado e pago nesse momento)
    #   40% linearmente entre aprovacao e inicio das obras (parcelas/compensacoes fisicas)
    med_comp = _merge(
        _av(m_aprov,                                             60.0),
        _lin(max(0, m_aprov + 1), max(m_aprov + 1, m_ini),     40.0),
    )

    # ------------------------------------------------------------------ #
    # MARKETING                                                            #
    # ------------------------------------------------------------------ #

    # Marketing e Vendas:
    #   20% pre-lancamento (preparacao do stand, 2 meses antes do lancamento)
    #   80% do lancamento ate o fim das obras (publicidade durante periodo de vendas)
    m_pre = max(0, m_lanc - 2)
    marketing = _merge(
        _lin(m_pre,  max(m_pre, m_lanc - 1), 20.0),
        _lin(m_lanc, max(m_lanc, m_fim),     80.0),
    )

    # ------------------------------------------------------------------ #
    # OUTROS                                                               #
    # ------------------------------------------------------------------ #

    # Assessoria Juridica: acompanhamento ao longo de todo o ciclo
    juridica = _lin(0, m_fim)

    return [
        {"nome": "Levantamento Topografico e Sondagem",                           "categoria": "projetos",       "valor_total": 0.0, "distribuicao": levant},
        {"nome": "Projeto Urbanistico Completo",                                   "categoria": "projetos",       "valor_total": 0.0, "distribuicao": proj_urb},
        {"nome": "Projetos Complementares (Drenagem, Pavimentacao, Eletrico, Agua/Esgoto)", "categoria": "projetos", "valor_total": 0.0, "distribuicao": proj_comp},
        {"nome": "Licenciamento Ambiental (LP / LI / LO)",                        "categoria": "licenciamento",  "valor_total": 0.0, "distribuicao": lic_amb},
        {"nome": "Aprovacao do Parcelamento na Prefeitura",                        "categoria": "licenciamento",  "valor_total": 0.0, "distribuicao": aprov_pref},
        {"nome": "Registro do Loteamento em Cartorio",                             "categoria": "licenciamento",  "valor_total": 0.0, "distribuicao": registro},
        {"nome": "Medida Compensatoria Urbana e Ambiental",                        "categoria": "licenciamento",  "valor_total": 0.0, "distribuicao": med_comp},
        {"nome": "Marketing e Vendas (Stand, Material, Publicidade)",              "categoria": "marketing",      "valor_total": 0.0, "distribuicao": marketing},
        {"nome": "Assessoria Juridica",                                            "categoria": "outros",         "valor_total": 0.0, "distribuicao": juridica},
    ]


def _criar_despesa_preset(nome: str, projeto) -> dict:
    """Retorna um dict de despesa preenchido com a distribuicao correta para o nome dado."""
    templates = {d["nome"]: d for d in _despesas_padrao_loteamento(projeto)}
    if nome in templates:
        base = templates[nome].copy()
        base.setdefault("modo_valor", "fixo")
        base.setdefault("percentual_vgv", 0.0)
        return base
    return {
        "nome": nome,
        "categoria": _CATEGORIA_DESPESA.get(nome, "outros"),
        "valor_total": 0.0,
        "modo_valor": "fixo",
        "percentual_vgv": 0.0,
        "distribuicao": {},
    }


def _garantir_estado_despesas() -> None:
    if CHAVE_DESPESAS not in st.session_state:
        st.session_state[CHAVE_DESPESAS] = _carregar_despesas_do_projeto()
    if CHAVE_FILTRO_MESES not in st.session_state:
        st.session_state[CHAVE_FILTRO_MESES] = True  # default ON


def _autosave_aba4() -> None:
    """
    Salva o estado atual das despesas no projeto (sem precisar de botao).

    Pula despesas invalidas (sem nome, sem distribuicao etc.) silenciosamente
    — quem mostra os erros e o painel de validacao da sidebar.
    """
    projeto = get_projeto()
    despesas_estado = st.session_state[CHAVE_DESPESAS]

    despesas_obj: list[DespesaTemporal] = []
    for desp_estado in despesas_estado:
        nome = str(desp_estado.get("nome", "")).strip()
        if not nome:
            continue
        valor_total = float(desp_estado.get("valor_total", 0) or 0)
        if valor_total <= 0:
            continue
        distrib = desp_estado.get("distribuicao", {})
        if not distrib:
            continue
        soma = sum(distrib.values())
        if abs(soma - 100.0) > 0.01:
            continue

        mes_min = min(distrib.keys())
        mes_max = max(distrib.keys())
        qtd_meses = mes_max - mes_min + 1
        lista_pct = [distrib.get(mes_min + i, 0.0) for i in range(qtd_meses)]

        try:
            despesas_obj.append(DespesaTemporal(
                nome=nome,
                categoria=desp_estado.get("categoria", "outros"),
                valor_total=valor_total,
                modo_valor=desp_estado.get("modo_valor", "fixo"),
                percentual_vgv=float(desp_estado.get("percentual_vgv", 0) or 0),
                modo="distribuicao_customizada",
                mes_inicio=mes_min,
                distribuicao_percentual=lista_pct,
            ))
        except Exception:
            continue  # ignora despesas invalidas

    nova_aba = Aba4Desenvolvimento(
        despesas=despesas_obj,
        administracao=projeto.desenvolvimento.administracao,
    )
    projeto_atualizado = projeto.model_copy(update={"desenvolvimento": nova_aba})
    set_projeto(projeto_atualizado)
    invalidar_resultado()


def _autosave_administracao(percentual: float) -> None:
    """Atualiza so a administracao."""
    projeto = get_projeto()
    try:
        admin_obj = Administracao(percentual=percentual)
        nova_aba = Aba4Desenvolvimento(
            despesas=projeto.desenvolvimento.despesas,
            administracao=admin_obj,
        )
        projeto_atualizado = projeto.model_copy(update={"desenvolvimento": nova_aba})
        set_projeto(projeto_atualizado)
        invalidar_resultado()
    except Exception:
        pass


def _autosave_comissao(comissao_obj: ComissaoVenda) -> None:
    projeto = get_projeto()
    try:
        from ...modelos import Aba5Impostos as _A5
        nova_impostos = _A5(
            tributos=projeto.impostos.tributos,
            comissao=comissao_obj,
            permuta_financeira=projeto.impostos.permuta_financeira,
        )
        set_projeto(projeto.model_copy(update={"impostos": nova_impostos}))
        invalidar_resultado()
    except Exception:
        pass


def renderizar() -> None:
    cabecalho_aba(
        4,
        "Despesas de Loteamento",
        "Custos com projetos, licenciamento, marketing e estrutura administrativa. "
        "As alterações são salvas automaticamente.",
    )

    projeto = get_projeto()
    desenv = projeto.desenvolvimento

    horizonte = horizonte_visual_projeto(projeto)
    marcos = marcos_projeto(projeto)

    _garantir_estado_despesas()
    despesas_estado = st.session_state[CHAVE_DESPESAS]

    # B3: resumo consolidado no topo
    if despesas_estado:
        st.markdown("---")

    # ============================================================
    # SECAO 1 — DESPESAS
    # ============================================================
    st.markdown("#### 1. Despesas de Loteamento")
    st.caption(
        "Projetos, licenciamento, marketing e outras despesas do empreendimento. "
        "Para cada item: informe o valor total e distribua o desembolso por mes (soma deve ser 100%)."
    )

    # Botoes de acao globais
    col_add, col_sel = st.columns([1, 3])
    with col_sel:
        desp_add_sel = st.selectbox(
            "Tipo de despesa",
            _OPCOES_DESPESA,
            key="aba4_add_sel",
            help="Escolha uma despesa predefinida (com distribuicao temporal automatica "
                 "baseada nos marcos do projeto) ou 'Personalizado' para comecar em branco.",
        )
    with col_add:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        if st.button("+ Adicionar", key="aba4_add_btn", type="primary", width="stretch"):
            if desp_add_sel == "Personalizado":
                nova = {
                    "nome": "Nova despesa",
                    "categoria": "outros",
                    "valor_total": 0.0,
                    "modo_valor": "fixo",
                    "percentual_vgv": 0.0,
                    "distribuicao": {},
                }
            else:
                nova = _criar_despesa_preset(desp_add_sel, projeto)
            despesas_estado.append(nova)
            _autosave_aba4()
            st.rerun()

    st.session_state[CHAVE_FILTRO_MESES] = st.checkbox(
        "Mostrar só meses preenchidos",
        value=st.session_state[CHAVE_FILTRO_MESES],
        help="Quando marcado, esconde meses zerados na tabela mensal "
             "(mostra apenas os meses com % > 0 mais 3 meses de margem). "
             "Util em projetos longos.",
    )

    if not despesas_estado:
        st.info("Nenhuma despesa cadastrada. Selecione o tipo acima e clique em '+ Adicionar'.")

    indices_para_remover = []

    for idx, despesa in enumerate(despesas_estado):
        nome_atual = despesa.get("nome", f"Despesa {idx+1}")
        valor_atual = despesa.get("valor_total", 0.0)
        soma_pct = sum(despesa.get("distribuicao", {}).values())

        # Status
        if abs(soma_pct - 100.0) < 0.01 and valor_atual > 0:
            status = "✓"
        elif soma_pct == 0 or valor_atual == 0:
            status = "○"
        else:
            status = "!"

        titulo = (
            f"{status} **{nome_atual}** "
            f"— {formatar_brl(valor_atual)} "
            f"({despesa.get('categoria', 'outros')})"
        )

        with st.expander(titulo, expanded=False, key=f"exp_desp_{idx}"):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                novo_nome = st.text_input(
                    "Descricao da despesa",
                    value=nome_atual,
                    key=f"desp_{idx}_nome",
                    placeholder="Ex.: Projeto urbanistico",
                )
            with col2:
                cat_opts = ["projetos", "licenciamento", "marketing", "outros"]
                cat_labels = {
                    "projetos": "Projetos tecnicos",
                    "licenciamento": "Licenciamento e taxas",
                    "marketing": "Marketing e vendas",
                    "outros": "Outras despesas",
                }
                nova_cat = st.selectbox(
                    "Categoria",
                    options=cat_opts,
                    format_func=lambda x: cat_labels.get(x, x),
                    index=cat_opts.index(despesa.get("categoria", "outros")),
                    key=f"desp_{idx}_cat",
                )
            with col3:
                modo_v = st.radio(
                    "Tipo de valor",
                    options=["fixo", "pct_vgv"],
                    format_func=lambda x: "R$ fixo" if x == "fixo" else "% do VGV",
                    index=0 if despesa.get("modo_valor", "fixo") == "fixo" else 1,
                    horizontal=True,
                    key=f"desp_{idx}_modo_valor",
                )
                despesa["modo_valor"] = modo_v
                if modo_v == "pct_vgv":
                    pct_vgv = numero_brl(
                        "% do VGV bruto",
                        value=float(despesa.get("percentual_vgv", 0) or 0),
                        key=f"desp_{idx}_pct_vgv",
                        min_value=0.0,
                        max_value=100.0,
                    )
                    despesa["percentual_vgv"] = pct_vgv
                    novo_valor = projeto.terreno.vgv_bruto * pct_vgv / 100
                    st.caption(f"= {formatar_brl(novo_valor)}")
                else:
                    novo_valor = numero_brl(
                        "Valor total (R$)",
                        value=float(valor_atual),
                        key=f"desp_{idx}_valor",
                        min_value=0.0,
                    )
                    despesa["percentual_vgv"] = 0.0
            with col4:
                st.markdown("&nbsp;")
                if st.button(
                    "Remover", key=f"desp_{idx}_remover", width="stretch",
                    help="Remover esta despesa", icon=":material/delete:",
                ):
                    indices_para_remover.append(idx)

            # ----- ATALHOS CONTEXTUAIS POR CATEGORIA -----
            presets = atalhos_contextuais(nova_cat, marcos, horizonte)
            if presets:
                with st.expander(f"Atalhos de distribuição — {cat_labels.get(nova_cat, nova_cat)}", expanded=False):
                    cols_presets = st.columns(min(len(presets), 2))
                    for i, (label, distrib) in enumerate(presets.items()):
                        with cols_presets[i % len(cols_presets)]:
                            if st.button(
                                label, key=f"desp_{idx}_preset_{i}",
                                width="stretch",
                            ):
                                despesa["distribuicao"] = distrib
                                _autosave_aba4()
                                st.rerun()

            # ----- ATALHOS POR INTERVALOS -----
            chave_atl_desp = f"_ativ_result_desp_{idx}"
            if chave_atl_desp in st.session_state:
                despesa["distribuicao"] = st.session_state.pop(chave_atl_desp)
                _autosave_aba4()

            st.markdown(
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
                'text-transform:uppercase;color:var(--stone-500);margin:10px 0 4px;">Distribuição por intervalos</div>',
                unsafe_allow_html=True,
            )
            st.caption("Defina faixas com % e clique Aplicar.")
            atalhos_por_intervalos(f"despesa_{idx}", horizonte, chave_atl_desp)

            st.markdown(
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
                'text-transform:uppercase;color:var(--stone-500);margin:10px 0 4px;">Distribuição mensal</div>',
                unsafe_allow_html=True,
            )
            nova_distrib = tabela_mensal_distribuicao(
                nome_unico=f"despesa_{idx}",
                horizonte_meses=horizonte,
                valores_iniciais=despesa.get("distribuicao", {}),
                marcos=marcos,
                filtrar_meses_zerados=st.session_state[CHAVE_FILTRO_MESES],
            )

            # Atualizar estado em memoria
            mudou_meta = (
                despesa["nome"] != novo_nome or
                despesa["categoria"] != nova_cat or
                despesa["valor_total"] != novo_valor
            )
            despesa["nome"] = novo_nome
            despesa["categoria"] = nova_cat
            despesa["valor_total"] = novo_valor
            despesa["distribuicao"] = nova_distrib

            col_sv, _ = st.columns([1, 3])
            with col_sv:
                if st.button("Salvar fluxo", key=f"desp_{idx}_salvar_fluxo", width="stretch", icon=":material/save:"):
                    _autosave_aba4()

    # Remover despesas marcadas
    if indices_para_remover:
        for idx in sorted(indices_para_remover, reverse=True):
            despesas_estado.pop(idx)
        _autosave_aba4()
        st.rerun()

    # Subtotais
    if despesas_estado:
        with st.container(border=True):
            st.markdown(
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.10em;'
                'text-transform:uppercase;color:var(--stone-500);margin-bottom:8px;">Subtotais por categoria</div>',
                unsafe_allow_html=True,
            )
            agg = {"projetos": 0.0, "licenciamento": 0.0, "marketing": 0.0, "outros": 0.0}
            for d in despesas_estado:
                agg[d["categoria"]] = agg.get(d["categoria"], 0) + float(d["valor_total"] or 0)
            cols = st.columns(5)
            labels = {
                "projetos": "Projetos",
                "licenciamento": "Licenciamento",
                "marketing": "Marketing",
                "outros": "Outras",
            }
            for i, cat in enumerate(["projetos", "licenciamento", "marketing", "outros"]):
                with cols[i]:
                    st.metric(labels[cat], formatar_brl(agg[cat]))
            total = sum(agg.values())
            with cols[4]:
                st.metric("Total", formatar_brl(total))

    # ============================================================
    # CARD 2 — ADMINISTRACAO
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Estrutura Administrativa")
        st.caption(
            "% sobre a receita mensal do projeto. "
            "Incide apenas quando ha receita, na mesma logica dos impostos. "
            "Salvo automaticamente."
        )

        col1, _ = st.columns([2, 3])
        with col1:
            percentual_admin = numero_brl(
                "% sobre a receita mensal",
                value=float(desenv.administracao.percentual),
                key="aba4_admin_pct",
                min_value=0.0,
                help="Ex.: 2% significa que a cada R$100 recebido, R$2 vao para administracao.",
            )

    # ============================================================
    # CARD 3 — COMISSAO DE VENDA
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Comissão de Venda (Corretagem)")

        comissao_atual = projeto.impostos.comissao

        col1, col2 = st.columns(2)
        with col1:
            comissao_pct = numero_brl(
                "% Comissao sobre o VGV",
                value=float(comissao_atual.percentual_vgv),
                key="aba4_comissao_pct",
                min_value=0.0, max_value=20.0,
                help="Pratica de mercado: 4% a 8% sobre o valor da venda.",
            )
            modo_com = st.radio(
                "Quando a comissao e paga ao corretor?",
                options=["sobre_venda", "sobre_recebimento", "misto"],
                format_func=lambda x: {
                    "sobre_venda": "Integral no mês da venda",
                    "sobre_recebimento": "Proporcional ao recebimento",
                    "misto": "Misto (X% no ato + Y% diluído em N parcelas)",
                }[x],
                index=["sobre_venda", "sobre_recebimento", "misto"].index(
                    comissao_atual.modo_pagamento
                ),
                key="aba4_modo_com",
            )

        with col2:
            if modo_com == "misto":
                st.markdown("**Configuracao do modo Misto:**")
                misto_pct_ato = numero_brl(
                    "% pago no ato da venda",
                    value=float(comissao_atual.misto_percentual_no_ato),
                    key="aba4_misto_ato",
                    min_value=0.0, max_value=100.0,
                )
                misto_qtd = numero_brl(
                    "Em quantas parcelas mensais o restante e diluido?",
                    value=float(comissao_atual.misto_qtd_parcelas),
                    key="aba4_misto_qtd",
                    min_value=1.0, casas=0,
                )
                st.info(
                    f"{misto_pct_ato:.0f}% no mês da venda + "
                    f"{100-misto_pct_ato:.0f}% diluído em {int(misto_qtd)} parcelas mensais."
                )
            else:
                misto_pct_ato = comissao_atual.misto_percentual_no_ato
                misto_qtd = comissao_atual.misto_qtd_parcelas

    # ============================================================
    # SALVAR ABA
    # ============================================================
    st.markdown("---")
    _col_sv4, _ = st.columns([1, 3])
    with _col_sv4:
        if st.button(
            "Salvar aba",
            key="aba4_salvar_aba",
            type="primary",
            width="stretch",
            icon=":material/save:",
        ):
            sincronizar_aba4()
            st.rerun()

    # Navegacao para o proximo modulo
    btn_proximo_modulo("Impostos")

    # Staged: persiste valores de admin e comissao para sincronizar_aba4
    try:
        nova_com = ComissaoVenda(
            percentual_vgv=comissao_pct,
            modo_pagamento=modo_com,
            misto_percentual_no_ato=misto_pct_ato,
            misto_qtd_parcelas=misto_qtd,
        )
        st.session_state["_aba4_admin_pct"] = float(percentual_admin)
        st.session_state["_aba4_comissao"] = nova_com
    except Exception:
        pass


def sincronizar_aba4() -> None:
    """Salva o estado em memoria da Aba 4 no projeto (chamado pelo sidebar antes de Calcular)."""
    if CHAVE_DESPESAS in st.session_state:
        _autosave_aba4()

    # Salva administracao e comissao se houver staged
    admin_pct = st.session_state.get("_aba4_admin_pct")
    nova_com = st.session_state.get("_aba4_comissao")
    if admin_pct is not None:
        _autosave_administracao(float(admin_pct))
    if nova_com is not None:
        _autosave_comissao(nova_com)
