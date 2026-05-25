"""
Aba 2 — Composicao das Receitas e Permuta Fisica.

Refatorada na Fase 2.3:
- "Tipo de permuta" renomeado para "Aquisicao do Terreno"
- Quando aquisicao = "Permuta financeira", mostra aqui mesmo a configuracao
  do permutante (tirou da Aba 5)
- Curva de vendas vira tabela mensal: para cada mes, % do estoque vendido +
  qual fluxo de recebiveis usar
"""

from __future__ import annotations

import streamlit as st

from ...modelos import (
    Aba2Receitas,
    FaixaCurvaVendas,
    FluxoRecebiveis,
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
from ..tabela_mensal import atalhos_por_intervalos


CHAVE_FLUXOS = "aba2_lista_fluxos"
CHAVE_CURVA_MENSAL = "aba2_curva_mensal"        # dict {mes: (pct, fluxo_nome)}
CHAVE_CURVA_SNAPSHOT = "aba2_curva_snapshot"    # A10: snapshot do ultimo estado salvo
CHAVE_FATORES_PRECO = "aba2_fatores_preco"      # dict {mes: fator_preco} — preco progressivo
CHAVE_CENARIO_PENDENTE = "_aba2_cenario_venda_pendente"


# =====================================================================
# CENARIOS PRE-CONFIGURADOS DE VELOCIDADE DE VENDAS
# =====================================================================

_CENARIOS_VENDA = [
    {
        "nome": "🚀 Esgotamento no lançamento — Otimista",
        "descricao": (
            "40% vendidos nos 3 primeiros meses (lançamento impactante), 40% ao longo "
            "do 1º ano e 20% restantes até o fim das obras. Estoque zerado antes da entrega."
        ),
        "fases": [
            ("Lançamento (3 meses)",      "L",    "L+2",  40.0),
            ("1º ano pós-lançamento",     "L+3",  "L+11", 40.0),
            ("Até fim das obras",         "L+12", "T",    20.0),
        ],
    },
    {
        "nome": "📈 Mercado aquecido — Sem estoque pós-obra",
        "descricao": (
            "Lançamento sólido (25% nos 2 primeiros meses) e ritmo sustentado durante "
            "toda a obra (75%). Vendas e entrega ocorrem juntas."
        ),
        "fases": [
            ("Lançamento (2 meses)",      "L",   "L+1", 25.0),
            ("Durante obras",             "L+2", "T",   75.0),
        ],
    },
    {
        "nome": "📊 Padrão de mercado — 15% de estoque pós-obra",
        "descricao": (
            "Lançamento dentro do esperado (20%), vendas constantes durante obras (65%) "
            "e 15% de estoque residual vendido nos 6 meses após a entrega."
        ),
        "fases": [
            ("Lançamento (3 meses)",      "L",   "L+2", 20.0),
            ("Durante obras",             "L+3", "T",   65.0),
            ("Pós-obra (6 meses)",        "T+1", "T+6", 15.0),
        ],
    },
    {
        "nome": "🏗 Conservador — 30% de estoque pós-obra",
        "descricao": (
            "Lançamento moderado (15%), ritmo médio durante obras (55%) e 30% do "
            "estoque vendido ao longo do ano seguinte à entrega."
        ),
        "fases": [
            ("Lançamento (3 meses)",      "L",   "L+2",  15.0),
            ("Durante obras",             "L+3", "T",    55.0),
            ("Pós-obra (12 meses)",       "T+1", "T+12", 30.0),
        ],
    },
    {
        "nome": "📉 Estoque prolongado — Obra + 18 meses",
        "descricao": (
            "Ritmo lento de vendas: 10% no lançamento, 40% durante obras e 50% do "
            "estoque distribuído ao longo dos 18 meses após a entrega. Avalie o financiamento."
        ),
        "fases": [
            ("Lançamento (2 meses)",      "L",   "L+1",  10.0),
            ("Durante obras",             "L+2", "T",    40.0),
            ("Pós-obra (18 meses)",       "T+1", "T+18", 50.0),
        ],
    },
    {
        "nome": "💥 Lançamento impactante + desaceleração",
        "descricao": (
            "Grande evento de lançamento: 50% vendidos nos primeiros 4 meses, "
            "desaceleração gradual durante obras (40%) e 10% de residual pós-entrega."
        ),
        "fases": [
            ("Evento de lançamento (4 meses)", "L",   "L+3", 50.0),
            ("Durante obras",                  "L+4", "T",   40.0),
            ("Pós-obra (6 meses)",             "T+1", "T+6", 10.0),
        ],
    },
]


def _resolver_mes_venda(expr: str, L: int, T: int) -> int:
    """Resolve 'L+3', 'T', 'T+6', etc. para mes absoluto."""
    expr = expr.strip()
    if expr.startswith("L"):
        return max(0, L + (int(expr[1:]) if len(expr) > 1 else 0))
    if expr.startswith("T"):
        return max(0, T + (int(expr[1:]) if len(expr) > 1 else 0))
    return max(0, int(expr))


def _gerar_curva_cenario(
    fases: list[tuple[str, str, str, float]],
    L: int,
    T: int,
    horizonte: int,
    fluxo_nome: str,
) -> dict[int, tuple[float, str]]:
    """Distribui percentuais linearmente em cada fase, sem sobreposicao."""
    resultado: dict[int, tuple[float, str]] = {}
    ultimo_fim = -1
    for (_label, ini_expr, fim_expr, pct_total) in fases:
        ini = max(ultimo_fim + 1, _resolver_mes_venda(ini_expr, L, T))
        fim = min(horizonte - 1, max(ini, _resolver_mes_venda(fim_expr, L, T)))
        if pct_total <= 0 or ini > fim:
            continue
        n = fim - ini + 1
        vals = [round(pct_total / n, 2)] * n
        residuo = round(pct_total - sum(vals), 2)
        vals[-1] = round(vals[-1] + residuo, 2)
        for i, v in enumerate(vals):
            if v > 0:
                resultado[ini + i] = (v, fluxo_nome)
        ultimo_fim = fim
    return resultado


def _renderizar_cenarios_venda(
    curva_estado: dict[int, tuple[float, str]],
    marcos: dict[int, str],
    nomes_fluxos: list[str],
    horizonte: int,
) -> None:
    """Expander com cenarios pre-configurados. Armazena resultado em session_state."""
    L = next((k for k, v in marcos.items() if "Lanc" in v), None)
    T = next(
        (k for k, v in marcos.items() if ("Fim" in v or "fim" in v) and "Obra" in v),
        None,
    )
    if L is None:
        L = 0
    if T is None:
        T = max(1, horizonte // 2)

    fluxo_padrao = nomes_fluxos[0] if nomes_fluxos else ""

    with st.expander("📋 Cenários de velocidade de vendas", expanded=not bool(curva_estado)):
        st.caption(
            "Selecione um cenário como ponto de partida. "
            "Valores são distribuídos linearmente em cada fase — ajuste na tabela mensal abaixo."
        )

        nomes = [c["nome"] for c in _CENARIOS_VENDA]
        sel_idx = st.selectbox(
            "Cenário",
            options=list(range(len(nomes))),
            format_func=lambda i: nomes[i],
            key="aba2_cenario_venda_sel",
            label_visibility="collapsed",
        )
        cen = _CENARIOS_VENDA[sel_idx]
        st.caption(cen["descricao"])

        if len(nomes_fluxos) > 1:
            fluxo_sel = st.selectbox(
                "Fluxo de recebíveis",
                options=nomes_fluxos,
                index=0,
                key="aba2_cenario_fluxo_sel",
                help="Fluxo aplicado a todos os meses do cenário. Ajuste por mês na tabela.",
            )
        else:
            fluxo_sel = fluxo_padrao

        # Preview das fases com barra proporcional
        ref_total = max(1, T + 12 - L)
        cols_hdr = st.columns([3, 1, 4])
        cols_hdr[0].markdown("**Fase**")
        cols_hdr[1].markdown("**%**")
        cols_hdr[2].markdown(f"**Período  (Lanç=M{L} | Fim obras=M{T})**")

        for (_label, ini_expr, fim_expr, pct) in cen["fases"]:
            ini = max(0, _resolver_mes_venda(ini_expr, L, T))
            fim = min(horizonte - 1, max(ini, _resolver_mes_venda(fim_expr, L, T)))
            cols = st.columns([3, 1, 4])
            cols[0].caption(_label)
            cols[1].caption(f"{pct:.0f}%")
            offset = max(0, int((ini - L) / ref_total * 28))
            width  = max(1, int((fim - ini + 1) / ref_total * 28))
            barra  = " " * offset + "█" * width
            cols[2].caption(f"`{barra}` M{ini}–M{fim}")

        st.caption(
            "⚠️ O cenário distribui os percentuais linearmente. "
            "Ajuste mês a mês na tabela conforme sua expectativa de mercado."
        )

        if st.button(
            "▶ Aplicar cenário",
            key="btn_aplicar_cenario_venda",
            type="primary",
        ):
            nova = _gerar_curva_cenario(
                cen["fases"], L, T, horizonte, fluxo_sel or fluxo_padrao
            )
            st.session_state[CHAVE_CENARIO_PENDENTE] = nova


def _carregar_fluxos_do_projeto() -> list[dict]:
    projeto = get_projeto()
    return [
        {
            "nome": f.nome,
            "percentual_sinal": f.percentual_sinal,
            "qtd_parcelas_sinal": f.qtd_parcelas_sinal,
            "percentual_obra": f.percentual_obra,
            "juros_parcelas_obra_am": f.juros_parcelas_obra_am,
            "percentual_baloes": f.percentual_baloes,
            "percentual_financiamento": f.percentual_financiamento,
            "qtd_parcelas_financiamento": f.qtd_parcelas_financiamento,
            "juros_financiamento_am": f.juros_financiamento_am,
        }
        for f in projeto.receitas.fluxos_recebiveis
    ]


def _carregar_curva_mensal_do_projeto() -> dict[int, tuple[float, str]]:
    """
    Converte as faixas atuais para o formato {mes: (pct, fluxo_nome)}.
    Distribui os % de cada faixa linearmente entre mes_inicio e mes_fim.
    """
    projeto = get_projeto()
    out: dict[int, tuple[float, str]] = {}
    for faixa in projeto.receitas.curva_vendas:
        qtd = faixa.mes_fim - faixa.mes_inicio + 1
        if qtd <= 0:
            continue
        pct_por_mes = faixa.percentual_estoque / qtd
        for i in range(qtd):
            mes = faixa.mes_inicio + i
            pct_existente, _ = out.get(mes, (0.0, faixa.fluxo_recebiveis))
            out[mes] = (pct_existente + pct_por_mes, faixa.fluxo_recebiveis)
    return out


def _carregar_fatores_do_projeto() -> dict[int, float]:
    """Carrega o fator_preco por mes a partir das faixas do projeto."""
    projeto = get_projeto()
    fatores: dict[int, float] = {}
    for faixa in projeto.receitas.curva_vendas:
        if abs(faixa.fator_preco - 1.0) < 0.0001:
            continue
        for i in range(faixa.mes_fim - faixa.mes_inicio + 1):
            fatores[faixa.mes_inicio + i] = faixa.fator_preco
    return fatores


def _tem_fatores_progressivos() -> bool:
    """Retorna True se o projeto ja tem algum fator de preco nao unitario."""
    try:
        projeto = get_projeto()
        return any(abs(f.fator_preco - 1.0) > 0.001 for f in projeto.receitas.curva_vendas)
    except Exception:
        return False


def _garantir_estado() -> None:
    if CHAVE_FLUXOS not in st.session_state:
        st.session_state[CHAVE_FLUXOS] = _carregar_fluxos_do_projeto()
    if CHAVE_CURVA_MENSAL not in st.session_state:
        loaded = _carregar_curva_mensal_do_projeto()
        st.session_state[CHAVE_CURVA_MENSAL] = loaded
        st.session_state[CHAVE_CURVA_SNAPSHOT] = dict(loaded)  # A10
    if CHAVE_FATORES_PRECO not in st.session_state:
        st.session_state[CHAVE_FATORES_PRECO] = _carregar_fatores_do_projeto()


def _fluxos_mudaram(fluxos_estado: list[dict], receitas) -> bool:
    """Detecta se os metadados dos fluxos (nao data_editor) mudaram em relacao ao projeto."""
    if len(fluxos_estado) != len(receitas.fluxos_recebiveis):
        return True
    campos_float = [
        "percentual_sinal", "percentual_obra", "percentual_baloes",
        "percentual_financiamento", "juros_parcelas_obra_am", "juros_financiamento_am",
    ]
    campos_int = ["qtd_parcelas_sinal", "qtd_parcelas_financiamento"]
    for fl, fl_obj in zip(fluxos_estado, receitas.fluxos_recebiveis):
        if str(fl.get("nome", "")) != str(fl_obj.nome):
            return True
        for campo in campos_float:
            if abs(float(fl.get(campo, 0) or 0) - float(getattr(fl_obj, campo, 0))) > 0.001:
                return True
        for campo in campos_int:
            if int(fl.get(campo, 0) or 0) != int(getattr(fl_obj, campo, 0)):
                return True
    return False


def _executar_save_aba2(
    fluxos_estado: list[dict],
    curva_estado: dict[int, tuple[float, str]],
    mes_termino_obras: int,
    projeto,
    receitas,
    fatores_estado: dict[int, float] | None = None,
) -> None:
    """Salva fluxos + curva de vendas no projeto."""
    try:
        mes_venda_por_fluxo: dict[str, int] = {}
        for mes, (pct, fluxo_n) in curva_estado.items():
            if pct > 0:
                if fluxo_n not in mes_venda_por_fluxo:
                    mes_venda_por_fluxo[fluxo_n] = mes
                else:
                    mes_venda_por_fluxo[fluxo_n] = min(mes_venda_por_fluxo[fluxo_n], mes)

        fluxos_obj = []
        for fl in fluxos_estado:
            nome_f = str(fl.get("nome", "")).strip()
            if not nome_f:
                continue
            pct_baloes = float(fl.get("percentual_baloes", 0) or 0)
            if pct_baloes > 0:
                mes_venda_ref = mes_venda_por_fluxo.get(nome_f, 0)
                qtd_baloes = max((mes_termino_obras - mes_venda_ref) // 12, 1)
            else:
                qtd_baloes = 0
            try:
                fluxos_obj.append(FluxoRecebiveis(
                    nome=nome_f,
                    percentual_sinal=float(fl.get("percentual_sinal", 0) or 0),
                    qtd_parcelas_sinal=int(fl.get("qtd_parcelas_sinal", 1) or 1),
                    percentual_obra=float(fl.get("percentual_obra", 0) or 0),
                    juros_parcelas_obra_am=float(fl.get("juros_parcelas_obra_am", 0) or 0),
                    percentual_baloes=pct_baloes,
                    qtd_baloes=qtd_baloes,
                    percentual_financiamento=float(fl.get("percentual_financiamento", 0) or 0),
                    qtd_parcelas_financiamento=int(fl.get("qtd_parcelas_financiamento", 0) or 0),
                    juros_financiamento_am=float(fl.get("juros_financiamento_am", 0) or 0),
                ))
            except Exception:
                continue

        _fatores = fatores_estado or {}
        curva_obj = []
        for mes in sorted(curva_estado.keys()):
            pct, fluxo_n = curva_estado[mes]
            if pct > 0:
                fator = max(0.01, float(_fatores.get(mes, 1.0) or 1.0))
                try:
                    curva_obj.append(FaixaCurvaVendas(
                        mes_inicio=mes, mes_fim=mes,
                        percentual_estoque=pct,
                        fluxo_recebiveis=fluxo_n,
                        fator_preco=fator,
                    ))
                except Exception:
                    continue

        if fluxos_obj and curva_obj:
            nova_aba2 = Aba2Receitas(
                tipo_permuta=receitas.tipo_permuta,
                permuta_fisica=list(receitas.permuta_fisica),
                fluxos_recebiveis=fluxos_obj,
                curva_vendas=curva_obj,
            )
            if projeto.receitas.model_dump_json() != nova_aba2.model_dump_json():
                set_projeto(projeto.model_copy(update={"receitas": nova_aba2}))
                invalidar_resultado()
            st.session_state[CHAVE_CURVA_SNAPSHOT] = dict(curva_estado)  # A10
    except Exception:
        pass


def sincronizar_aba2() -> None:
    """Salva estado da Aba 2 no projeto (chamado pelo sidebar antes de Calcular)."""
    fluxos_estado = st.session_state.get(CHAVE_FLUXOS)
    curva_estado = st.session_state.get(CHAVE_CURVA_MENSAL)
    if fluxos_estado is None or curva_estado is None:
        return
    mes_termino_obras = int(st.session_state.get("_aba2_mes_termino_obras", 0))
    projeto = get_projeto()
    receitas = projeto.receitas
    _executar_save_aba2(fluxos_estado, curva_estado, mes_termino_obras, projeto, receitas)


def renderizar() -> None:
    cabecalho_aba(
        2,
        "Composicao das Receitas",
        "Fluxos de recebiveis e curva de vendas mensal.",
    )

    projeto = get_projeto()
    receitas = projeto.receitas
    tipologias = projeto.terreno.tipologias

    if not tipologias:
        aviso_validacao("Cadastre tipologias em Identificação (sidebar → Dados) antes de configurar receitas.")
        return

    horizonte = horizonte_visual_projeto(projeto)
    marcos = marcos_projeto(projeto)

    _garantir_estado()

    # ============================================================
    # CARD 1 — FLUXOS DE RECEBIVEIS
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 💳 Fluxos de Recebiveis")
        st.caption(
            "Cada fluxo descreve como o pagamento de uma venda e distribuido. "
            "Os 4 percentuais (sinal + parcelas obra + baloes + financiamento) devem somar 100%. "
            "Quantidade de baloes e calculada automaticamente (1 a cada 12 meses ate o termino das obras)."
        )

        fluxos_estado = st.session_state[CHAVE_FLUXOS]

        col_add, _ = st.columns([1, 4])
        with col_add:
            if st.button("➕ Adicionar fluxo em branco", use_container_width=True, key="aba2_btn_add_fluxo"):
                fluxos_estado.append({
                    "nome": f"Fluxo {len(fluxos_estado)+1}",
                    "percentual_sinal": 10.0,
                    "qtd_parcelas_sinal": 1,
                    "percentual_obra": 30.0,
                    "juros_parcelas_obra_am": 0.5,
                    "percentual_baloes": 10.0,
                    "percentual_financiamento": 50.0,
                    "qtd_parcelas_financiamento": 120,
                    "juros_financiamento_am": 1.0,
                })
                st.rerun()

        indices_remover_fluxo = []
        indices_duplicar_fluxo = []
        for idx, fluxo in enumerate(fluxos_estado):
            soma = (
                float(fluxo.get("percentual_sinal", 0) or 0)
                + float(fluxo.get("percentual_obra", 0) or 0)
                + float(fluxo.get("percentual_baloes", 0) or 0)
                + float(fluxo.get("percentual_financiamento", 0) or 0)
            )
            status = "✅" if abs(soma - 100.0) < 0.01 else "⚠️"
            titulo = f"{status} **{fluxo.get('nome', f'Fluxo {idx+1}')}** (soma: {soma:.2f}%)"

            with st.expander(titulo, expanded=False, key=f"exp_fluxo_{idx}"):
                col_n, col_dup, col_x = st.columns([4, 1, 1])
                with col_n:
                    fluxo["nome"] = st.text_input(
                        "Nome do fluxo",
                        value=fluxo.get("nome", f"Fluxo {idx+1}"),
                        key=f"fluxo_{idx}_nome",
                    )
                with col_dup:
                    st.markdown("&nbsp;")
                    if st.button("📋", key=f"fluxo_{idx}_duplicar",
                                 use_container_width=True, help="Duplicar este fluxo — cria uma cópia com todos os percentuais e juros"):
                        indices_duplicar_fluxo.append(idx)
                with col_x:
                    st.markdown("&nbsp;")
                    if st.button("🗑️", key=f"fluxo_{idx}_remover",
                                 use_container_width=True, help="Remover fluxo"):
                        indices_remover_fluxo.append(idx)

                # Copiar valores de outro fluxo
                _outros = [
                    f["nome"] for i, f in enumerate(fluxos_estado)
                    if i != idx and f.get("nome", "").strip()
                ]
                if _outros:
                    col_cpy_sel, col_cpy_btn = st.columns([3, 1])
                    with col_cpy_sel:
                        _fonte_sel = st.selectbox(
                            "Copiar percentuais de",
                            options=_outros,
                            key=f"fluxo_{idx}_copia_sel",
                        )
                    with col_cpy_btn:
                        st.markdown('<div style="padding-top:26px;"></div>', unsafe_allow_html=True)
                        if st.button("Copiar", key=f"fluxo_{idx}_btn_copia", use_container_width=True,
                                     help="Copia os percentuais e juros do fluxo selecionado"):
                            _fonte = next((f for f in fluxos_estado if f.get("nome") == _fonte_sel), None)
                            if _fonte:
                                for _campo in [
                                    "percentual_sinal", "qtd_parcelas_sinal",
                                    "percentual_obra", "juros_parcelas_obra_am",
                                    "percentual_baloes",
                                    "percentual_financiamento", "qtd_parcelas_financiamento",
                                    "juros_financiamento_am",
                                ]:
                                    fluxo[_campo] = _fonte.get(_campo, 0)
                                st.rerun()

                cs1, cs2 = st.columns(2)
                with cs1:
                    st.markdown("**Sinal**")
                    fluxo["percentual_sinal"] = numero_brl(
                        "% Sinal",
                        value=float(fluxo.get("percentual_sinal", 0)),
                        key=f"fluxo_{idx}_sinal_pct",
                        min_value=0.0, max_value=100.0,
                    )
                    fluxo["qtd_parcelas_sinal"] = numero_brl(
                        "Qtd parcelas do sinal",
                        value=float(fluxo.get("qtd_parcelas_sinal", 1)),
                        key=f"fluxo_{idx}_sinal_qtd",
                        min_value=1.0, casas=0,
                    )
                    st.markdown("**Baloes (a cada 12 meses)**")
                    fluxo["percentual_baloes"] = numero_brl(
                        "% Baloes",
                        value=float(fluxo.get("percentual_baloes", 0)),
                        key=f"fluxo_{idx}_baloes",
                        min_value=0.0, max_value=100.0,
                        help="Quantidade de baloes calculada automaticamente.",
                    )

                with cs2:
                    st.markdown("**Parcelas durante obra**")
                    fluxo["percentual_obra"] = numero_brl(
                        "% Obra",
                        value=float(fluxo.get("percentual_obra", 0)),
                        key=f"fluxo_{idx}_obra_pct",
                        min_value=0.0, max_value=100.0,
                    )
                    fluxo["juros_parcelas_obra_am"] = numero_brl(
                        "Juros das parcelas (% a.m.)",
                        value=float(fluxo.get("juros_parcelas_obra_am", 0)),
                        key=f"fluxo_{idx}_obra_juros",
                        min_value=0.0,
                        help="Pratica de mercado MG: 0,3-0,8% a.m. "
                             "(parcelas corrigidas pelo INCC ou tabela Price durante a obra).",
                    )
                    st.markdown("**Financiamento pos-obra**")
                    fluxo["percentual_financiamento"] = numero_brl(
                        "% Financiamento",
                        value=float(fluxo.get("percentual_financiamento", 0)),
                        key=f"fluxo_{idx}_fin_pct",
                        min_value=0.0, max_value=100.0,
                    )
                    col_qtd, col_jur = st.columns(2)
                    with col_qtd:
                        fluxo["qtd_parcelas_financiamento"] = numero_brl(
                            "Qtd parcelas",
                            value=float(fluxo.get("qtd_parcelas_financiamento", 0)),
                            key=f"fluxo_{idx}_fin_qtd",
                            min_value=0.0, casas=0,
                        )
                    with col_jur:
                        fluxo["juros_financiamento_am"] = numero_brl(
                            "Juros (% a.m.)",
                            value=float(fluxo.get("juros_financiamento_am", 0)),
                            key=f"fluxo_{idx}_fin_juros",
                            min_value=0.0,
                            help="Juros do financiamento pos-obra (tabela Price). "
                                 "Pratica de mercado: 0,6-1,0% a.m.",
                        )

                # A6: barra visual de distribuicao dos percentuais
                _s = float(fluxo.get("percentual_sinal", 0) or 0)
                _o = float(fluxo.get("percentual_obra", 0) or 0)
                _b = float(fluxo.get("percentual_baloes", 0) or 0)
                _f = float(fluxo.get("percentual_financiamento", 0) or 0)
                _tot = _s + _o + _b + _f
                _cor_tot = "#22C55E" if abs(_tot - 100) < 0.01 else "#F59E0B" if _tot < 100 else "#EF4444"
                _bw = min(_tot, 100)
                st.markdown(
                    f'<div style="margin:10px 0 2px 0;font-size:12px;color:#9CA3AF;">'
                    f'Sinal <b style="color:#60A5FA">{_s:.0f}%</b>'
                    f' + Obra <b style="color:#FBBF24">{_o:.0f}%</b>'
                    f' + Balões <b style="color:#A78BFA">{_b:.0f}%</b>'
                    f' + Financiamento <b style="color:#34D399">{_f:.0f}%</b>'
                    f' = <b style="color:{_cor_tot}">{_tot:.0f}%</b></div>'
                    f'<div style="background:#1F2937;border-radius:4px;height:8px;overflow:hidden;margin-bottom:6px;">'
                    f'<div style="background:{_cor_tot};width:{_bw:.1f}%;height:100%;border-radius:4px;"></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if indices_duplicar_fluxo:
            for idx in sorted(indices_duplicar_fluxo, reverse=True):
                fonte = fluxos_estado[idx]
                copia = {**fonte, "nome": f"{fonte.get('nome', f'Fluxo {idx+1}')} (copia)"}
                fluxos_estado.insert(idx + 1, copia)
            st.rerun()

        if indices_remover_fluxo:
            for idx in sorted(indices_remover_fluxo, reverse=True):
                fluxos_estado.pop(idx)
            st.rerun()

        # Lista de nomes de fluxos para usar na curva
        nomes_fluxos = [f["nome"] for f in fluxos_estado if f.get("nome", "").strip()]

    # ============================================================
    # CARD 2 — CURVA DE VENDAS
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 📈 Curva de Vendas")
        st.caption(
            "Para cada mes, informe o **% do estoque vendido naquele mes** e o **fluxo de recebiveis** "
            "que se aplica a essas vendas. A soma das vendas mensais deve ser 100% do estoque."
        )

        if not nomes_fluxos:
            aviso_validacao("Cadastre pelo menos um fluxo de recebiveis antes de configurar a curva.")
            return

        curva_estado = st.session_state[CHAVE_CURVA_MENSAL]

        # Cenarios pre-configurados
        aplicar_cenario_venda = False
        if CHAVE_CENARIO_PENDENTE in st.session_state:
            nova_curva = st.session_state.pop(CHAVE_CENARIO_PENDENTE)
            curva_estado.clear()
            curva_estado.update(nova_curva)
            aplicar_cenario_venda = True

        _renderizar_cenarios_venda(curva_estado, marcos, nomes_fluxos, horizonte)

        st.markdown("---")

        # Atalhos por intervalos para a curva de vendas
        st.markdown("**Atalhos por faixa:**")
        st.caption("Defina faixas com % de estoque e fluxo, clique Aplicar.")
        chave_atl_curva = "_ativ_result_curva_vendas"
        aplicar_atalho_curva = False
        if chave_atl_curva in st.session_state:
            novo_estado = st.session_state.pop(chave_atl_curva)
            curva_estado.clear()
            curva_estado.update(novo_estado)
            aplicar_atalho_curva = True

        atalhos_por_intervalos("curva_vendas", horizonte, chave_atl_curva, nomes_fluxos=nomes_fluxos)

        # Grafico de vendas acima da tabela
        if curva_estado:
            _meses_venda = sorted(m for m, (p, _) in curva_estado.items() if p > 0)
            if _meses_venda:
                try:
                    import plotly.graph_objects as _go
                    _ys_venda = [curva_estado[m][0] for m in _meses_venda]
                    _acum = []
                    _soma_ac = 0.0
                    for _v in _ys_venda:
                        _soma_ac += _v
                        _acum.append(_soma_ac)
                    _fig_venda = _go.Figure()
                    _fig_venda.add_trace(_go.Bar(
                        x=_meses_venda, y=_ys_venda,
                        name="% vendida no mes",
                        marker_color="#3D8B5E",
                        hovertemplate="M%{x}: %{y:.1f}%<extra></extra>",
                        yaxis="y",
                    ))
                    _fig_venda.add_trace(_go.Scatter(
                        x=_meses_venda, y=_acum,
                        name="% acumulada",
                        mode="lines+markers",
                        line=dict(color="#4A7FA5", width=2),
                        marker=dict(size=4),
                        hovertemplate="M%{x}: %{y:.1f}% acum.<extra></extra>",
                        yaxis="y2",
                    ))
                    _fig_venda.update_layout(
                        height=220,
                        margin=dict(l=40, r=40, t=10, b=40),
                        paper_bgcolor="#F5F3EE",
                        plot_bgcolor="#ECEAE4",
                        font=dict(color="#5A5650", size=10),
                        legend=dict(orientation="h", x=0, y=1.1, font=dict(size=10, color="#1A1916")),
                        xaxis=dict(title="Mes do projeto", gridcolor="#D8D4C8", tickmode="auto", nticks=12),
                        yaxis=dict(title="% no mes", gridcolor="#D8D4C8", rangemode="tozero"),
                        yaxis2=dict(
                            title="% acumulada", overlaying="y", side="right",
                            gridcolor="#D8D4C8", rangemode="tozero",
                        ),
                    )
                    st.plotly_chart(_fig_venda, use_container_width=True, key="aba2_grafico_curva_vendas")
                    st.caption("Distribuicao mensal de vendas — barras: % no mes | linha: % acumulada")
                except Exception:
                    pass

        # Preco progressivo por fase
        st.markdown("---")
        aplicar_fatores = _renderizar_preco_progressivo(curva_estado, horizonte)
        st.markdown("---")

        # Tabela mensal customizada
        st.markdown("**Tabela mensal de vendas:**")
        _renderizar_tabela_curva_vendas(curva_estado, horizonte, marcos, nomes_fluxos)

        # Verificacao da soma
        soma_curva = sum(pct for pct, _ in curva_estado.values())
        if abs(soma_curva - 100.0) < 0.01:
            st.success(f"✅ Soma da curva: {soma_curva:.2f}%")
        elif soma_curva == 0:
            st.info(f"Soma da curva: {soma_curva:.2f}% (nada preenchido ainda)")
        else:
            st.warning(f"⚠️ Soma da curva: {soma_curva:.2f}% (deve ser 100%)")

        # A10: indicador de alteracoes nao salvas
        _snapshot_curva = st.session_state.get(CHAVE_CURVA_SNAPSHOT, {})
        _curva_suja = dict(curva_estado) != dict(_snapshot_curva) and bool(curva_estado)

        col_sv, col_ind, _ = st.columns([1, 1, 2])
        with col_sv:
            salvar_curva = st.button("💾 Salvar curva", key="aba2_salvar_curva", use_container_width=True)
        with col_ind:
            if _curva_suja:
                st.markdown(
                    '<div style="color:#F59E0B;font-size:12px;padding-top:8px;">● Alterações não salvas</div>',
                    unsafe_allow_html=True,
                )

    # ============================================================
    # NAVEGACAO
    # ============================================================
    btn_proximo_modulo("Obras")

    # ============================================================
    # AUTO-SAVE TRIGGER
    # ============================================================
    fluxo_mudou = _fluxos_mudaram(fluxos_estado, receitas)

    from ...engine.utilidades import meses_entre as _me
    _mes_to = _me(projeto.terreno.datas.inicio_projeto, projeto.terreno.datas.termino_obras)
    st.session_state["_aba2_mes_termino_obras"] = _mes_to

    if not (salvar_curva or fluxo_mudou or aplicar_atalho_curva or aplicar_fatores or aplicar_cenario_venda):
        return

    _executar_save_aba2(
        fluxos_estado, curva_estado, _mes_to, projeto, receitas,
        fatores_estado=st.session_state.get(CHAVE_FATORES_PRECO),
    )


def _renderizar_preco_progressivo(curva_estado: dict, horizonte: int) -> bool:
    """
    Secao de preco progressivo por fase.

    Permite ao usuario definir bandas de tempo com multiplicadores de preco.
    Retorna True quando o usuario clicar em Aplicar (para triggerar o save).
    """
    import pandas as pd
    from ..helpers import formatar_num as _fn

    ativo = st.toggle(
        "🔀 Preco progressivo por fase",
        value=st.session_state.get("aba2_preco_progressivo_ativo", _tem_fatores_progressivos()),
        key="aba2_preco_progressivo_ativo",
        help=(
            "Aplica um multiplicador de preco diferente em cada fase de vendas. "
            "Ex.: 0,95x no lancamento (-5%) e 1,10x no estoque (+10%). "
            "Impacta diretamente a receita e a margem do empreendimento."
        ),
    )

    if not ativo:
        if st.session_state.get(CHAVE_FATORES_PRECO):
            st.session_state[CHAVE_FATORES_PRECO] = {}
            return True
        return False

    # Bandas: [Fase, Inicio, Fim, Fator]
    CHAVE_BANDAS = "aba2_preco_bandas"
    if CHAVE_BANDAS not in st.session_state:
        fatores = st.session_state.get(CHAVE_FATORES_PRECO, {})
        if fatores:
            # Reconstruir bandas a partir dos fatores existentes
            meses_ord = sorted(fatores.keys())
            bandas: list[dict] = []
            ini = meses_ord[0]
            fator_ant = fatores[ini]
            for m in meses_ord[1:]:
                if abs(fatores[m] - fator_ant) > 0.001:
                    bandas.append({"Fase": f"Fase {len(bandas)+1}", "Inicio (M)": ini, "Fim (M)": m - 1, "Fator": fator_ant})
                    ini = m
                    fator_ant = fatores[m]
            bandas.append({"Fase": f"Fase {len(bandas)+1}", "Inicio (M)": ini, "Fim (M)": meses_ord[-1], "Fator": fator_ant})
        else:
            meses_com_venda = sorted(m for m, (p, _) in curva_estado.items() if p > 0)
            ini_v = meses_com_venda[0] if meses_com_venda else 0
            fim_v = meses_com_venda[-1] if meses_com_venda else horizonte
            dur = max(1, fim_v - ini_v)
            terco = dur // 3
            bandas = [
                {"Fase": "Lancamento", "Inicio (M)": ini_v, "Fim (M)": ini_v + terco, "Fator": 0.95},
                {"Fase": "Maturacao", "Inicio (M)": ini_v + terco + 1, "Fim (M)": ini_v + 2 * terco, "Fator": 1.00},
                {"Fase": "Estoque", "Inicio (M)": ini_v + 2 * terco + 1, "Fim (M)": fim_v, "Fator": 1.10},
            ]
        st.session_state[CHAVE_BANDAS] = bandas

    df_bandas = pd.DataFrame(st.session_state[CHAVE_BANDAS])

    st.caption(
        "Defina faixas de tempo com multiplicadores de preco. "
        "Fator 1,00 = preco padrao | 0,95 = -5% | 1,10 = +10%. "
        "Meses fora das faixas usam fator 1,00 (preco padrao)."
    )

    df_edit = st.data_editor(
        df_bandas,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Fase": st.column_config.TextColumn(
                "Fase",
                help="Nome da fase de vendas",
            ),
            "Inicio (M)": st.column_config.NumberColumn(
                "Inicio (M)", min_value=0, max_value=horizonte, step=1, format="%d",
            ),
            "Fim (M)": st.column_config.NumberColumn(
                "Fim (M)", min_value=0, max_value=horizonte, step=1, format="%d",
            ),
            "Fator": st.column_config.NumberColumn(
                "Fator (× preco base)", min_value=0.1, max_value=5.0, step=0.01, format="%.2f",
                help="1,00 = preco padrao | 0,95 = 5% desconto | 1,10 = 10% agio",
            ),
        },
        key="aba2_bandas_editor",
    )

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        aplicar = st.button("▶ Aplicar fatores", key="btn_aplicar_fatores_preco",
                            use_container_width=True, type="primary")
    with col_info:
        fatores_atuais = st.session_state.get(CHAVE_FATORES_PRECO, {})
        if fatores_atuais and curva_estado:
            soma_pct = sum(p for p, _ in curva_estado.values())
            if soma_pct > 0:
                fator_medio = sum(
                    p * fatores_atuais.get(m, 1.0)
                    for m, (p, _) in curva_estado.items()
                ) / soma_pct
                delta_pct = (fator_medio - 1.0) * 100
                projeto = get_projeto()
                vgv_base = projeto.terreno.vgv_bruto
                st.caption(
                    f"Fator medio ponderado: **{fator_medio:.3f}×** "
                    f"→ Δ VGV ≈ **{delta_pct:+.1f}%** "
                    f"({_fn(vgv_base * fator_medio, 0)} vs base {_fn(vgv_base, 0)})"
                )

    if aplicar:
        novos_fatores: dict[int, float] = {}
        for _, row in df_edit.iterrows():
            ini = int(row.get("Inicio (M)", 0) or 0)
            fim = int(row.get("Fim (M)", 0) or 0)
            fator = float(row.get("Fator", 1.0) or 1.0)
            for m in range(ini, fim + 1):
                novos_fatores[m] = max(0.01, fator)
        st.session_state[CHAVE_FATORES_PRECO] = novos_fatores
        st.session_state[CHAVE_BANDAS] = df_edit.to_dict(orient="records")
        return True

    return False


def _renderizar_tabela_curva_vendas(
    curva_estado: dict[int, tuple[float, str]],
    horizonte: int,
    marcos: dict[int, str],
    nomes_fluxos: list[str],
) -> None:
    """
    Renderiza a tabela mensal da curva de vendas.

    Diferente da tabela mensal padrao porque cada mes tem 2 valores:
    % do estoque vendido + qual fluxo de recebiveis.
    Colunas extras (read-only): % acumulado vendido e saldo de estoque.
    """
    import pandas as pd

    # Pre-computar cumulativo para as colunas de leitura
    _acum: dict[int, float] = {}
    _running = 0.0
    for _m in range(horizonte):
        pct_m, _ = curva_estado.get(_m, (0.0, ""))
        _running += pct_m
        _acum[_m] = _running

    meses_por_bloco = 20
    qtd_blocos = (horizonte + meses_por_bloco - 1) // meses_por_bloco

    fluxo_padrao = nomes_fluxos[0] if nomes_fluxos else ""

    cols = st.columns(qtd_blocos)
    dfs_editados: dict[int, pd.DataFrame] = {}

    for bloco_idx in range(qtd_blocos):
        with cols[bloco_idx]:
            mes_inicio_bloco = bloco_idx * meses_por_bloco
            mes_fim_bloco = min((bloco_idx + 1) * meses_por_bloco, horizonte)
            st.caption(f"**M{mes_inicio_bloco}–M{mes_fim_bloco - 1}**")

            linhas = []
            for mes in range(mes_inicio_bloco, mes_fim_bloco):
                marco_nome = marcos.get(mes, "")
                label = f"M{mes} 🏁 {marco_nome}" if marco_nome else f"M{mes}"
                pct_atual, fluxo_atual = curva_estado.get(mes, (0.0, fluxo_padrao))
                if fluxo_atual not in nomes_fluxos:
                    fluxo_atual = fluxo_padrao
                linhas.append({
                    "Mes": label,
                    "%": pct_atual,
                    "Acum.%": round(_acum.get(mes, 0.0), 1),
                    "Saldo%": round(max(0.0, 100.0 - _acum.get(mes, 0.0)), 1),
                    "Fluxo": fluxo_atual,
                    "_mes_num": mes,
                })

            df = pd.DataFrame(linhas)

            df_edit = st.data_editor(
                df[["Mes", "%", "Acum.%", "Saldo%", "Fluxo"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mes": st.column_config.TextColumn("Mes", disabled=True, width="small"),
                    "%": st.column_config.NumberColumn(
                        "%", min_value=0.0, max_value=100.0, step=1.0, format="%.2f",
                    ),
                    "Acum.%": st.column_config.NumberColumn("Acum.%", disabled=True, format="%.1f"),
                    "Saldo%": st.column_config.NumberColumn("Saldo%", disabled=True, format="%.1f"),
                    "Fluxo": st.column_config.SelectboxColumn(
                        "Fluxo", options=nomes_fluxos, required=True,
                    ),
                },
                key=f"curva_bloco_{bloco_idx}",
            )
            df_edit["_mes_num"] = df["_mes_num"].values
            dfs_editados[bloco_idx] = df_edit

    # Reconstruir curva_estado a partir dos blocos editados
    curva_estado.clear()
    for bloco_idx, df in dfs_editados.items():
        for _, row in df.iterrows():
            mes = int(row["_mes_num"])
            pct = float(row["%"] or 0)
            fluxo_n = str(row["Fluxo"]) if row["Fluxo"] else fluxo_padrao
            if pct > 0:
                curva_estado[mes] = (pct, fluxo_n)
