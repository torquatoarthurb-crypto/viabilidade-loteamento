"""
Aba 2 — Composicao das Receitas.

Design: cada tipologia tem 1 fluxo de recebiveis + sua propria curva de vendas.
O fluxo de caixa final e a soma de todos os fluxos de tipologias.
"""

from __future__ import annotations

import streamlit as st

from ...modelos import (
    Aba2Receitas,
    FluxoTipologia,
    OutraReceita,
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
from ..tabela_mensal import atalhos_por_intervalos, tabela_mensal_distribuicao


CHAVE_FT_LISTA = "aba2_ft_lista"
CHAVE_OUTRAS_RECEITAS = "aba2_outras_receitas"

_TIPOS_OUTRA_RECEITA = ["aporte", "receita_financeira", "venda_ativo", "outro"]
_LABEL_TIPO_OR = {
    "aporte": "Aporte / Investimento",
    "receita_financeira": "Receita Financeira",
    "venda_ativo": "Venda de Ativo",
    "outro": "Outro",
}


# =====================================================================
# HELPERS
# =====================================================================

def _safe_nome(nome: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in nome)


def _default_ft(nome_tipologia: str) -> dict:
    return {
        "nome_tipologia": nome_tipologia,
        "percentual_sinal": 10.0,
        "qtd_parcelas_sinal": 1,
        "percentual_obra": 30.0,
        "juros_parcelas_obra_am": 0.5,
        "percentual_baloes": 10.0,
        "qtd_baloes": 0,
        "percentual_financiamento": 50.0,
        "qtd_parcelas_financiamento": 120,
        "juros_financiamento_am": 1.0,
        "curva_mensal": {},
        "fatores_preco": {},
    }


# =====================================================================
# CENARIOS PRE-CONFIGURADOS DE VELOCIDADE DE VENDAS
# =====================================================================

_CENARIOS_VENDA = [
    {
        "nome": "Esgotamento no lançamento — Otimista",
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
        "nome": "Mercado aquecido — Sem estoque pós-obra",
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
        "nome": "Padrão de mercado — 15% de estoque pós-obra",
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
        "nome": "Conservador — 30% de estoque pós-obra",
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
        "nome": "Estoque prolongado — Obra + 18 meses",
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
        "nome": "Lançamento impactante + desaceleração",
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


def _resolver_mes(expr: str, L: int, T: int) -> int:
    expr = expr.strip()
    if expr.startswith("L"):
        return max(0, L + (int(expr[1:]) if len(expr) > 1 else 0))
    if expr.startswith("T"):
        return max(0, T + (int(expr[1:]) if len(expr) > 1 else 0))
    return max(0, int(expr))


def _gerar_curva_cenario(fases: list, L: int, T: int, horizonte: int) -> dict[int, float]:
    resultado: dict[int, float] = {}
    ultimo_fim = -1
    for (_label, ini_expr, fim_expr, pct_total) in fases:
        ini = max(ultimo_fim + 1, _resolver_mes(ini_expr, L, T))
        fim = min(horizonte - 1, max(ini, _resolver_mes(fim_expr, L, T)))
        if pct_total <= 0 or ini > fim:
            continue
        n = fim - ini + 1
        vals = [round(pct_total / n, 2)] * n
        residuo = round(pct_total - sum(vals), 2)
        vals[-1] = round(vals[-1] + residuo, 2)
        for i, v in enumerate(vals):
            if v > 0:
                resultado[ini + i] = v
        ultimo_fim = fim
    return resultado


# =====================================================================
# ESTADO
# =====================================================================

def _garantir_estado() -> None:
    if CHAVE_FT_LISTA not in st.session_state:
        projeto = get_projeto()
        receitas = projeto.receitas
        if receitas.fluxos_tipologia:
            st.session_state[CHAVE_FT_LISTA] = [
                {
                    "nome_tipologia": ft.nome_tipologia,
                    "percentual_sinal": ft.percentual_sinal,
                    "qtd_parcelas_sinal": ft.qtd_parcelas_sinal,
                    "percentual_obra": ft.percentual_obra,
                    "juros_parcelas_obra_am": ft.juros_parcelas_obra_am,
                    "percentual_baloes": ft.percentual_baloes,
                    "qtd_baloes": ft.qtd_baloes,
                    "percentual_financiamento": ft.percentual_financiamento,
                    "qtd_parcelas_financiamento": ft.qtd_parcelas_financiamento,
                    "juros_financiamento_am": ft.juros_financiamento_am,
                    "curva_mensal": {int(k): float(v) for k, v in ft.curva_mensal.items()},
                    "fatores_preco": {int(k): float(v) for k, v in ft.fatores_preco.items()},
                }
                for ft in receitas.fluxos_tipologia
            ]
        else:
            st.session_state[CHAVE_FT_LISTA] = [
                _default_ft(tip.nome) for tip in projeto.terreno.tipologias
            ]

    if CHAVE_OUTRAS_RECEITAS not in st.session_state:
        projeto = get_projeto()
        st.session_state[CHAVE_OUTRAS_RECEITAS] = [
            {
                "nome": r.nome,
                "tipo": r.tipo,
                "valor_total": r.valor_total,
                "mes_inicio": r.mes_inicio,
                "mes_fim": r.mes_fim,
            }
            for r in projeto.receitas.outras_receitas
        ]


# =====================================================================
# SAVE
# =====================================================================

def _executar_save_aba2(
    ft_lista: list[dict],
    projeto,
    receitas,
    outras_estado: list[dict] | None = None,
) -> None:
    try:
        ft_objs = []
        for ft in ft_lista:
            nome_tip = str(ft.get("nome_tipologia", "")).strip()
            if not nome_tip:
                continue
            curva = {int(k): float(v) for k, v in ft.get("curva_mensal", {}).items() if float(v) > 0}
            fatores = {int(k): float(v) for k, v in ft.get("fatores_preco", {}).items()}
            try:
                ft_objs.append(FluxoTipologia(
                    nome_tipologia=nome_tip,
                    percentual_sinal=float(ft.get("percentual_sinal", 10) or 10),
                    qtd_parcelas_sinal=max(1, int(ft.get("qtd_parcelas_sinal", 1) or 1)),
                    percentual_obra=float(ft.get("percentual_obra", 30) or 30),
                    juros_parcelas_obra_am=float(ft.get("juros_parcelas_obra_am", 0.5) or 0),
                    percentual_baloes=float(ft.get("percentual_baloes", 0) or 0),
                    qtd_baloes=int(ft.get("qtd_baloes", 0) or 0),
                    percentual_financiamento=float(ft.get("percentual_financiamento", 50) or 50),
                    qtd_parcelas_financiamento=max(0, int(ft.get("qtd_parcelas_financiamento", 120) or 120)),
                    juros_financiamento_am=float(ft.get("juros_financiamento_am", 1.0) or 0),
                    curva_mensal=curva,
                    fatores_preco=fatores,
                ))
            except Exception:
                continue

        outras_obj = []
        for r in (outras_estado or []):
            nome_r = str(r.get("nome", "")).strip()
            if not nome_r:
                continue
            try:
                ini = int(r.get("mes_inicio", 0) or 0)
                fim = max(ini, int(r.get("mes_fim", 0) or 0))
                outras_obj.append(OutraReceita(
                    nome=nome_r,
                    tipo=r.get("tipo", "outro") or "outro",
                    valor_total=float(r.get("valor_total", 0) or 0),
                    mes_inicio=ini,
                    mes_fim=fim,
                ))
            except Exception:
                continue

        nova_aba2 = Aba2Receitas(
            tipo_permuta=receitas.tipo_permuta,
            permuta_fisica=list(receitas.permuta_fisica),
            fluxos_tipologia=ft_objs,
            outras_receitas=outras_obj,
        )
        if projeto.receitas.model_dump_json() != nova_aba2.model_dump_json():
            set_projeto(projeto.model_copy(update={"receitas": nova_aba2}))
            invalidar_resultado()
    except Exception:
        pass


def sincronizar_aba2() -> None:
    """Chamado pelo sidebar antes de Calcular."""
    ft_lista = st.session_state.get(CHAVE_FT_LISTA)
    if ft_lista is None:
        return
    projeto = get_projeto()
    _executar_save_aba2(
        ft_lista, projeto, projeto.receitas,
        outras_estado=st.session_state.get(CHAVE_OUTRAS_RECEITAS),
    )


# =====================================================================
# COMPONENTES POR TIPOLOGIA
# =====================================================================

def _renderizar_campos_fluxo_ft(ft: dict, safe: str) -> bool:
    """Campos do fluxo de recebiveis de UMA tipologia. Retorna True se mudou."""
    mudou = False

    cs1, cs2 = st.columns(2)
    with cs1:
        st.markdown("**Sinal**")
        v = numero_brl(
            "% Sinal", value=float(ft.get("percentual_sinal", 10)),
            key=f"ft_{safe}_sinal_pct", min_value=0.0, max_value=100.0,
        )
        if abs(v - float(ft.get("percentual_sinal", 10))) > 0.001:
            ft["percentual_sinal"] = v
            mudou = True

        v = numero_brl(
            "Qtd parcelas do sinal", value=float(ft.get("qtd_parcelas_sinal", 1)),
            key=f"ft_{safe}_sinal_qtd", min_value=1.0, casas=0,
        )
        if int(v) != int(ft.get("qtd_parcelas_sinal", 1)):
            ft["qtd_parcelas_sinal"] = int(v)
            mudou = True

        st.markdown("**Balões (a cada 12 meses)**")
        v = numero_brl(
            "% Balões", value=float(ft.get("percentual_baloes", 10)),
            key=f"ft_{safe}_baloes", min_value=0.0, max_value=100.0,
            help="Quantidade de balões calculada automaticamente pelo sistema.",
        )
        if abs(v - float(ft.get("percentual_baloes", 10))) > 0.001:
            ft["percentual_baloes"] = v
            mudou = True

    with cs2:
        st.markdown("**Parcelas durante obra**")
        v = numero_brl(
            "% Obra", value=float(ft.get("percentual_obra", 30)),
            key=f"ft_{safe}_obra_pct", min_value=0.0, max_value=100.0,
        )
        if abs(v - float(ft.get("percentual_obra", 30))) > 0.001:
            ft["percentual_obra"] = v
            mudou = True

        v = numero_brl(
            "Juros das parcelas (% a.m.)", value=float(ft.get("juros_parcelas_obra_am", 0.5)),
            key=f"ft_{safe}_obra_juros", min_value=0.0,
            help="Prática de mercado MG: 0,3–0,8% a.m.",
        )
        if abs(v - float(ft.get("juros_parcelas_obra_am", 0.5))) > 0.0001:
            ft["juros_parcelas_obra_am"] = v
            mudou = True

        st.markdown("**Financiamento pós-obra**")
        v = numero_brl(
            "% Financiamento", value=float(ft.get("percentual_financiamento", 50)),
            key=f"ft_{safe}_fin_pct", min_value=0.0, max_value=100.0,
        )
        if abs(v - float(ft.get("percentual_financiamento", 50))) > 0.001:
            ft["percentual_financiamento"] = v
            mudou = True

        col_qtd, col_jur = st.columns(2)
        with col_qtd:
            v = numero_brl(
                "Qtd parcelas", value=float(ft.get("qtd_parcelas_financiamento", 120)),
                key=f"ft_{safe}_fin_qtd", min_value=0.0, casas=0,
            )
            if int(v) != int(ft.get("qtd_parcelas_financiamento", 120)):
                ft["qtd_parcelas_financiamento"] = int(v)
                mudou = True
        with col_jur:
            v = numero_brl(
                "Juros (% a.m.)", value=float(ft.get("juros_financiamento_am", 1.0)),
                key=f"ft_{safe}_fin_juros", min_value=0.0,
                help="Juros do financiamento pós-obra (Price). Prática: 0,6–1,0% a.m.",
            )
            if abs(v - float(ft.get("juros_financiamento_am", 1.0))) > 0.0001:
                ft["juros_financiamento_am"] = v
                mudou = True

    _s = float(ft.get("percentual_sinal", 0) or 0)
    _o = float(ft.get("percentual_obra", 0) or 0)
    _b = float(ft.get("percentual_baloes", 0) or 0)
    _f = float(ft.get("percentual_financiamento", 0) or 0)
    _tot = _s + _o + _b + _f
    _cor = "#22C55E" if abs(_tot - 100) < 0.01 else "#F59E0B" if _tot < 100 else "#EF4444"
    _bw = min(_tot, 100)
    st.markdown(
        f'<div style="margin:10px 0 2px 0;font-size:12px;color:#9CA3AF;">'
        f'Sinal <b style="color:#60A5FA">{_s:.0f}%</b>'
        f' + Obra <b style="color:#FBBF24">{_o:.0f}%</b>'
        f' + Balões <b style="color:#A78BFA">{_b:.0f}%</b>'
        f' + Financiamento <b style="color:#34D399">{_f:.0f}%</b>'
        f' = <b style="color:{_cor}">{_tot:.0f}%</b></div>'
        f'<div style="background:#1F2937;border-radius:4px;height:8px;overflow:hidden;margin-bottom:6px;">'
        f'<div style="background:{_cor};width:{_bw:.1f}%;height:100%;border-radius:4px;"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    return mudou


def _renderizar_cenarios_tipologia(
    curva: dict[int, float],
    marcos: dict[int, str],
    horizonte: int,
    safe: str,
) -> None:
    """Expander com cenarios pre-configurados para UMA tipologia."""
    L = next((k for k, v in marcos.items() if "Lanc" in v), 0)
    T = next(
        (k for k, v in marcos.items() if ("Fim" in v or "fim" in v) and "Obra" in v),
        max(1, horizonte // 2),
    )

    with st.expander("Cenários de velocidade de vendas", expanded=not bool(curva)):
        st.caption(
            "Selecione um cenário como ponto de partida. "
            "Ajuste na tabela mensal conforme a expectativa de mercado."
        )

        nomes = [c["nome"] for c in _CENARIOS_VENDA]
        sel_idx = st.selectbox(
            "Cenário",
            options=list(range(len(nomes))),
            format_func=lambda i: nomes[i],
            key=f"aba2_cenario_sel_{safe}",
            label_visibility="collapsed",
        )
        cen = _CENARIOS_VENDA[sel_idx]
        st.caption(cen["descricao"])

        ref_total = max(1, T + 12 - L)
        cols_hdr = st.columns([3, 1, 4])
        cols_hdr[0].markdown("**Fase**")
        cols_hdr[1].markdown("**%**")
        cols_hdr[2].markdown(f"**Período  (Lanç=M{L} | Fim obras=M{T})**")

        for (_label, ini_expr, fim_expr, pct) in cen["fases"]:
            ini = max(0, _resolver_mes(ini_expr, L, T))
            fim = min(horizonte - 1, max(ini, _resolver_mes(fim_expr, L, T)))
            cols = st.columns([3, 1, 4])
            cols[0].caption(_label)
            cols[1].caption(f"{pct:.0f}%")
            offset = max(0, int((ini - L) / ref_total * 28))
            width  = max(1, int((fim - ini + 1) / ref_total * 28))
            cols[2].caption(f"`{' ' * offset + '█' * width}` M{ini}–M{fim}")

        if st.button(
            "▶ Aplicar cenário",
            key=f"btn_cenario_{safe}",
            type="primary",
        ):
            nova = _gerar_curva_cenario(cen["fases"], L, T, horizonte)
            st.session_state[f"_cenario2_res_{safe}"] = nova
            st.rerun()


def _renderizar_curva_tipologia(
    ft: dict,
    safe: str,
    tip,
    horizonte: int,
    marcos: dict[int, str],
) -> bool:
    """Curva de vendas de UMA tipologia. Retorna True se mudou."""
    mudou = False
    curva: dict[int, float] = ft.setdefault("curva_mensal", {})

    # Cenarios
    _renderizar_cenarios_tipologia(curva, marcos, horizonte, safe)

    st.markdown("---")
    st.markdown("**Atalhos por faixa:**")
    st.caption("Defina faixas com % do estoque, clique Aplicar.")
    atalhos_por_intervalos(f"curva2_{safe}", horizonte, f"_curva2_res_{safe}")

    # Grafico read-only
    tabela_mensal_distribuicao(f"curva2_{safe}", horizonte, dict(curva), marcos)

    # Soma
    soma_curva = sum(float(v) for v in curva.values())
    if abs(soma_curva - 100.0) < 0.01:
        st.success(f"Soma: {soma_curva:.2f}%")
    elif soma_curva == 0:
        st.info("Nenhum mês preenchido ainda.")
    else:
        st.warning(f"Soma: {soma_curva:.2f}% — deve ser 100%")

    # Ajuste manual
    with st.expander("Ajuste manual mês a mês", expanded=False):
        nova_curva = _tabela_manual_curva(curva, safe, horizonte, marcos)
        if nova_curva is not None:
            curva.clear()
            curva.update(nova_curva)
            mudou = True

    return mudou


def _tabela_manual_curva(
    curva: dict[int, float],
    safe: str,
    horizonte: int,
    marcos: dict[int, str],
) -> dict[int, float] | None:
    """
    Tabela mes a mes para ajuste fino da curva de uma tipologia.
    Retorna o novo dict se o usuario clicar Salvar, None caso contrario.
    """
    _CV_HASH_KEY = f"_cv2_{safe}_hash"
    _CV_HASH = str(sorted((k, round(v, 4)) for k, v in curva.items()))
    if st.session_state.get(_CV_HASH_KEY) != _CV_HASH:
        for _k in list(st.session_state.keys()):
            if _k.startswith(f"_cv2m_{safe}_"):
                del st.session_state[_k]
        st.session_state[_CV_HASH_KEY] = _CV_HASH

    meses_por_bloco = 20
    qtd_blocos = max(1, (horizonte + meses_por_bloco - 1) // meses_por_bloco)
    cols = st.columns(qtd_blocos)
    nova_curva: dict[int, float] = {}
    _running_acum = 0.0

    for bloco_idx in range(qtd_blocos):
        with cols[bloco_idx]:
            ini = bloco_idx * meses_por_bloco
            fim = min((bloco_idx + 1) * meses_por_bloco, horizonte)
            st.caption(f"**M{ini}–M{fim - 1}**")

            _hcols = st.columns([1.2, 0.8, 0.8])
            for _hc, _hl in zip(_hcols, ["Mês", "%", "Acum"]):
                _hc.markdown(
                    f'<div style="font-size:10px;color:#9CA3AF;font-weight:600;">{_hl}</div>',
                    unsafe_allow_html=True,
                )

            _running_acum_bloco = sum(curva.get(m, 0.0) for m in range(ini))
            for mes in range(ini, fim):
                marco_nome = marcos.get(mes, "")
                label_mes = f"M{mes}" + (f" {marco_nome[:4]}" if marco_nome else "")
                _row = st.columns([1.2, 0.8, 0.8])
                _row[0].markdown(
                    f'<div style="font-size:11px;padding:6px 0 0;">{label_mes}</div>',
                    unsafe_allow_html=True,
                )
                with _row[1]:
                    _pct = st.number_input(
                        "",
                        value=float(curva.get(mes, 0.0)),
                        min_value=0.0, max_value=100.0,
                        step=1.0, format="%.2f",
                        key=f"_cv2m_{safe}_{mes}",
                        label_visibility="collapsed",
                    )
                _running_acum_bloco += _pct
                _row[2].markdown(
                    f'<div style="font-size:11px;padding:6px 0 0;">{_running_acum_bloco:.1f}</div>',
                    unsafe_allow_html=True,
                )
                if _pct > 0:
                    nova_curva[mes] = _pct

    if st.button("Salvar ajuste manual", key=f"_cv2_{safe}_salvar", icon=":material/save:"):
        return nova_curva

    return None


# =====================================================================
# PRECO PROGRESSIVO GLOBAL
# =====================================================================

def _tem_fatores_progressivos(ft_lista: list[dict]) -> bool:
    return any(
        abs(float(v) - 1.0) > 0.001
        for ft in ft_lista
        for v in ft.get("fatores_preco", {}).values()
    )


def _renderizar_preco_progressivo(ft_lista: list[dict], horizonte: int) -> bool:
    """
    Secao de preco progressivo global (aplicado a todas as tipologias).
    Retorna True quando aplicado.
    """
    from ..helpers import formatar_num as _fn

    st.markdown("#### Preço Progressivo")
    ativo = st.toggle(
        "Ativar preço progressivo por fase",
        value=st.session_state.get("aba2_preco_progressivo_ativo", _tem_fatores_progressivos(ft_lista)),
        key="aba2_preco_progressivo_ativo",
        help=(
            "Aplica um multiplicador de preço diferente em cada fase de vendas. "
            "Ex.: 0,95x no lançamento (–5%) e 1,10x no estoque (+10%). "
            "Aplicado a todas as tipologias."
        ),
    )

    if not ativo:
        if _tem_fatores_progressivos(ft_lista):
            for ft in ft_lista:
                ft["fatores_preco"] = {}
            return True
        return False

    CHAVE_BANDAS = "aba2_preco_bandas"
    if CHAVE_BANDAS not in st.session_state:
        fatores_existentes: dict[int, float] = {}
        for ft in ft_lista:
            for k, v in ft.get("fatores_preco", {}).items():
                fatores_existentes[int(k)] = float(v)

        if fatores_existentes:
            meses_ord = sorted(fatores_existentes.keys())
            bandas: list[dict] = []
            ini_b = meses_ord[0]
            fator_ant = fatores_existentes[ini_b]
            for m in meses_ord[1:]:
                if abs(fatores_existentes[m] - fator_ant) > 0.001:
                    bandas.append({"Fase": f"Fase {len(bandas)+1}", "Inicio (M)": ini_b, "Fim (M)": m - 1, "Fator": fator_ant})
                    ini_b = m
                    fator_ant = fatores_existentes[m]
            bandas.append({"Fase": f"Fase {len(bandas)+1}", "Inicio (M)": ini_b, "Fim (M)": meses_ord[-1], "Fator": fator_ant})
        else:
            meses_com_venda: list[int] = []
            for ft in ft_lista:
                meses_com_venda.extend(int(m) for m, v in ft.get("curva_mensal", {}).items() if float(v) > 0)
            ini_v = min(meses_com_venda) if meses_com_venda else 0
            fim_v = max(meses_com_venda) if meses_com_venda else horizonte
            dur = max(1, fim_v - ini_v)
            terco = dur // 3
            bandas = [
                {"Fase": "Lançamento",  "Inicio (M)": ini_v,              "Fim (M)": ini_v + terco,      "Fator": 0.95},
                {"Fase": "Maturação",   "Inicio (M)": ini_v + terco + 1,  "Fim (M)": ini_v + 2 * terco,  "Fator": 1.00},
                {"Fase": "Estoque",     "Inicio (M)": ini_v + 2*terco+1,  "Fim (M)": fim_v,              "Fator": 1.10},
            ]
        st.session_state[CHAVE_BANDAS] = bandas

    lista_atual: list[dict] = st.session_state[CHAVE_BANDAS]

    st.caption(
        "Fator 1,00 = preço padrão | 0,95 = –5% | 1,10 = +10%. "
        "Aplicado igualmente a todas as tipologias."
    )

    _BR_HASH_KEY = "aba2_br_hash"
    _br_hash = str(sorted(str(b) for b in lista_atual))
    if st.session_state.get(_BR_HASH_KEY) != _br_hash:
        for _k in list(st.session_state.keys()):
            if "_br_" in _k and any(c.isdigit() for c in _k):
                del st.session_state[_k]
        st.session_state[_BR_HASH_KEY] = _br_hash

    _br_col_w = [2.5, 1, 1, 1.2, 0.4]
    if lista_atual:
        _br_hcols = st.columns(_br_col_w)
        for _hc, _hl in zip(_br_hcols, ["Fase", "Início (M)", "Fim (M)", "Fator", ""]):
            _hc.markdown(
                f'<div style="font-size:11px;color:#9CA3AF;font-weight:600;padding-bottom:2px;">{_hl}</div>',
                unsafe_allow_html=True,
            )

    _br_idx_remover: int | None = None
    _br_lista_editada: list[dict] = []

    for _bi, _banda in enumerate(lista_atual):
        _br_rcols = st.columns(_br_col_w)
        with _br_rcols[0]:
            _br_fase = st.text_input(
                "fase", value=str(_banda.get("Fase", "") or ""),
                key=f"_br_{_bi}_fase", label_visibility="collapsed",
            )
        with _br_rcols[1]:
            _br_ini = st.number_input(
                "ini", value=int(_banda.get("Inicio (M)", 0) or 0),
                min_value=0, step=1, key=f"_br_{_bi}_ini", label_visibility="collapsed",
            )
        with _br_rcols[2]:
            _br_fim = st.number_input(
                "fim", value=int(_banda.get("Fim (M)", 0) or 0),
                min_value=0, step=1, key=f"_br_{_bi}_fim", label_visibility="collapsed",
            )
        with _br_rcols[3]:
            _br_fator = numero_brl(
                "fator", value=float(_banda.get("Fator", 1.0) or 1.0),
                key=f"_br_{_bi}_fator", min_value=0.01, max_value=5.0, casas=2,
                label_visibility="collapsed",
            )
        with _br_rcols[4]:
            if st.button("×", key=f"_br_{_bi}_del", icon=":material/delete:",
                         help="Remover banda", width="stretch"):
                _br_idx_remover = _bi

        _br_lista_editada.append({
            "Fase": _br_fase.strip(),
            "Inicio (M)": int(_br_ini),
            "Fim (M)": int(_br_fim),
            "Fator": float(_br_fator),
        })

    if _br_idx_remover is not None:
        _br_lista_apos = [b for i, b in enumerate(_br_lista_editada) if i != _br_idx_remover]
        for _k in list(st.session_state.keys()):
            if "_br_" in _k and any(c.isdigit() for c in _k):
                del st.session_state[_k]
        st.session_state[CHAVE_BANDAS] = _br_lista_apos
        st.session_state[_BR_HASH_KEY] = str(sorted(str(b) for b in _br_lista_apos))
        st.rerun()

    if st.button("+ Adicionar banda", key="aba2_br_add", icon=":material/add:"):
        _nova_banda = {"Fase": f"Fase {len(_br_lista_editada)+1}", "Inicio (M)": 0, "Fim (M)": 0, "Fator": 1.0}
        _nova_lista_br = _br_lista_editada + [_nova_banda]
        for _k in list(st.session_state.keys()):
            if "_br_" in _k and any(c.isdigit() for c in _k):
                del st.session_state[_k]
        st.session_state[CHAVE_BANDAS] = _nova_lista_br
        st.session_state[_BR_HASH_KEY] = str(sorted(str(b) for b in _nova_lista_br))
        st.rerun()

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        aplicar = st.button(
            "▶ Aplicar fatores", key="btn_aplicar_fatores_preco",
            width="stretch", type="primary",
        )
    with col_info:
        if ft_lista:
            curva_all = {}
            for ft in ft_lista:
                for m, v in ft.get("curva_mensal", {}).items():
                    curva_all[int(m)] = curva_all.get(int(m), 0.0) + float(v)
            fatores_atuais: dict[int, float] = {}
            for ft in ft_lista:
                for k, v in ft.get("fatores_preco", {}).items():
                    fatores_atuais[int(k)] = float(v)
            if fatores_atuais and curva_all:
                soma_pct = sum(curva_all.values())
                if soma_pct > 0:
                    fator_medio = sum(
                        pct * fatores_atuais.get(m, 1.0)
                        for m, pct in curva_all.items()
                    ) / soma_pct
                    delta_pct = (fator_medio - 1.0) * 100
                    projeto = get_projeto()
                    vgv_base = projeto.terreno.vgv_bruto
                    st.caption(
                        f"Fator médio ponderado: **{fator_medio:.3f}×** "
                        f"→ Δ VGV ≈ **{delta_pct:+.1f}%** "
                        f"({_fn(vgv_base * fator_medio, 0)} vs base {_fn(vgv_base, 0)})"
                    )

    if aplicar:
        novos_fatores: dict[int, float] = {}
        for _banda in _br_lista_editada:
            _ini = int(_banda.get("Inicio (M)", 0) or 0)
            _fim = int(_banda.get("Fim (M)", 0) or 0)
            _fator = float(_banda.get("Fator", 1.0) or 1.0)
            for m in range(_ini, _fim + 1):
                novos_fatores[m] = max(0.01, _fator)
        for ft in ft_lista:
            ft["fatores_preco"] = dict(novos_fatores)
        st.session_state[CHAVE_BANDAS] = _br_lista_editada
        return True

    return False


# =====================================================================
# RENDERIZADOR PRINCIPAL
# =====================================================================

def renderizar() -> None:
    cabecalho_aba(
        2,
        "Composicao das Receitas",
        "Configure o fluxo de recebiveis e a curva de vendas para cada tipologia.",
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

    ft_lista: list[dict] = st.session_state[CHAVE_FT_LISTA]

    # Sincronizar ft_lista com tipologias (add novos, remove excluidas)
    nomes_existentes = {ft["nome_tipologia"] for ft in ft_lista}
    for tip in tipologias:
        if tip.nome not in nomes_existentes:
            ft_lista.append(_default_ft(tip.nome))
    nomes_tipologias = {tip.nome for tip in tipologias}
    ft_lista[:] = [ft for ft in ft_lista if ft["nome_tipologia"] in nomes_tipologias]

    mudou = False

    # Consumir resultados pendentes de atalhos/cenarios ANTES de renderizar
    for tip in tipologias:
        safe = _safe_nome(tip.nome)
        ft = next((f for f in ft_lista if f["nome_tipologia"] == tip.nome), None)
        if ft is None:
            continue

        chave_atl = f"_curva2_res_{safe}"
        if chave_atl in st.session_state:
            resultado_atl = st.session_state.pop(chave_atl)
            ft["curva_mensal"] = {int(k): float(v) for k, v in resultado_atl.items() if float(v) > 0}
            mudou = True

        chave_cen = f"_cenario2_res_{safe}"
        if chave_cen in st.session_state:
            ft["curva_mensal"] = {int(k): float(v) for k, v in st.session_state.pop(chave_cen).items()}
            mudou = True

    # ============================================================
    # CARD 1 — POR TIPOLOGIA
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Recebíveis e Curva de Vendas por Tipologia")
        st.caption(
            "Cada tipologia tem um fluxo de recebíveis próprio (sinal + parcelas obra + balões + "
            "financiamento, devem somar 100%) e sua curva de vendas mensal (deve somar 100%). "
            "O fluxo de caixa final é a soma de todos os fluxos."
        )

        for i, tip in enumerate(tipologias):
            ft = next((f for f in ft_lista if f["nome_tipologia"] == tip.nome), None)
            if ft is None:
                continue

            safe = _safe_nome(tip.nome)
            soma_fluxo = (
                float(ft.get("percentual_sinal", 0) or 0)
                + float(ft.get("percentual_obra", 0) or 0)
                + float(ft.get("percentual_baloes", 0) or 0)
                + float(ft.get("percentual_financiamento", 0) or 0)
            )
            soma_curva = sum(float(v) for v in ft.get("curva_mensal", {}).values())
            _sf = "✓" if abs(soma_fluxo - 100) < 0.01 else "!"
            _sc = "✓" if abs(soma_curva - 100) < 0.01 else ("✕" if soma_curva < 0.1 else "!")
            _vgv_str = formatar_brl(tip.vgv_total)
            titulo = (
                f"{_sf} **{tip.nome}** — {tip.quantidade} lotes · VGV {_vgv_str} "
                f"| Fluxo {soma_fluxo:.0f}% {_sc} Curva {soma_curva:.1f}%"
            )

            with st.expander(titulo, expanded=False, key=f"exp_tip2_{i}"):
                tab_fl, tab_cv = st.tabs(["Fluxo de Recebíveis", "Curva de Vendas"])

                with tab_fl:
                    mudou |= _renderizar_campos_fluxo_ft(ft, safe)

                with tab_cv:
                    mudou |= _renderizar_curva_tipologia(ft, safe, tip, horizonte, marcos)

    # ============================================================
    # CARD 2 — PRECO PROGRESSIVO
    # ============================================================
    with st.container(border=True):
        mudou |= _renderizar_preco_progressivo(ft_lista, horizonte)

    # ============================================================
    # CARD 3 — OUTRAS RECEITAS
    # ============================================================
    salvar_outras = False
    with st.container(border=True):
        st.markdown("#### Outras Receitas")
        st.caption(
            "Aportes de investidores, receitas financeiras, venda de ativos e outras entradas "
            "não relacionadas à venda de lotes. Incluídas diretamente no fluxo de caixa."
        )

        outras_estado: list[dict] = st.session_state[CHAVE_OUTRAS_RECEITAS]

        _total_outras = sum(float(r.get("valor_total", 0) or 0) for r in outras_estado)
        if _total_outras > 0:
            st.caption(f"Total configurado: **{formatar_brl(_total_outras)}**")

        _OR_LISTA_KEY = "aba2_or_lista"
        _OR_HASH_KEY = "aba2_or_hash"
        _or_hash = str(sorted(str(r) for r in outras_estado))
        if st.session_state.get(_OR_HASH_KEY) != _or_hash:
            for _k in list(st.session_state.keys()):
                if "_or_" in _k and any(c.isdigit() for c in _k):
                    del st.session_state[_k]
            st.session_state[_OR_LISTA_KEY] = list(outras_estado)
            st.session_state[_OR_HASH_KEY] = _or_hash

        _or_lista: list[dict] = st.session_state.get(_OR_LISTA_KEY, list(outras_estado))

        _or_col_w = [3, 1.5, 1.8, 0.8, 0.8, 0.4]
        if _or_lista:
            _or_hcols = st.columns(_or_col_w)
            for _hc, _hl in zip(_or_hcols, ["Descrição", "Tipo", "Valor (R$)", "M. início", "M. fim", ""]):
                _hc.markdown(
                    f'<div style="font-size:11px;color:#9CA3AF;font-weight:600;padding-bottom:2px;">{_hl}</div>',
                    unsafe_allow_html=True,
                )

        _or_idx_remover: int | None = None
        _sync_outras: list[dict] = []

        for _oi, _item in enumerate(_or_lista):
            _or_rcols = st.columns(_or_col_w)
            with _or_rcols[0]:
                _or_nome = st.text_input(
                    "desc", value=str(_item.get("nome", "") or ""),
                    key=f"_or_{_oi}_nome", label_visibility="collapsed",
                )
            with _or_rcols[1]:
                _tipo_opts = _TIPOS_OUTRA_RECEITA
                _tipo_val = str(_item.get("tipo", "outro") or "outro")
                _tipo_idx = _tipo_opts.index(_tipo_val) if _tipo_val in _tipo_opts else 0
                _or_tipo = st.selectbox(
                    "tipo", options=_tipo_opts, index=_tipo_idx,
                    key=f"_or_{_oi}_tipo", label_visibility="collapsed",
                )
            with _or_rcols[2]:
                _or_valor = numero_brl(
                    "valor", value=float(_item.get("valor_total", 0) or 0),
                    key=f"_or_{_oi}_valor", min_value=0.0, casas=2,
                    label_visibility="collapsed",
                )
            with _or_rcols[3]:
                _or_ini = st.number_input(
                    "ini", value=int(_item.get("mes_inicio", 0) or 0),
                    min_value=0, step=1,
                    key=f"_or_{_oi}_ini", label_visibility="collapsed",
                )
            with _or_rcols[4]:
                _or_fim = st.number_input(
                    "fim",
                    value=max(int(_item.get("mes_inicio", 0) or 0), int(_item.get("mes_fim", 0) or 0)),
                    min_value=0, step=1,
                    key=f"_or_{_oi}_fim", label_visibility="collapsed",
                )
            with _or_rcols[5]:
                if st.button("×", key=f"_or_{_oi}_del", icon=":material/delete:",
                             help="Remover receita", width="stretch"):
                    _or_idx_remover = _oi

            _or_nome_s = _or_nome.strip()
            if _or_nome_s:
                _sync_outras.append({
                    "nome": _or_nome_s,
                    "tipo": str(_or_tipo),
                    "valor_total": float(_or_valor),
                    "mes_inicio": int(_or_ini),
                    "mes_fim": max(int(_or_ini), int(_or_fim)),
                })

        if _or_idx_remover is not None:
            _sync_apos = [r for i, r in enumerate(_sync_outras) if i != _or_idx_remover]
            for _k in list(st.session_state.keys()):
                if "_or_" in _k and any(c.isdigit() for c in _k):
                    del st.session_state[_k]
            st.session_state[_OR_LISTA_KEY] = _sync_apos
            st.session_state[_OR_HASH_KEY] = str(sorted(str(r) for r in _sync_apos))
            outras_estado[:] = _sync_apos
            st.rerun()

        if st.button("+ Adicionar receita", key="aba2_or_add", icon=":material/add:"):
            _nova = {"nome": "", "tipo": "outro", "valor_total": 0.0, "mes_inicio": 0, "mes_fim": 0}
            _nova_lista = list(_sync_outras) + [_nova]
            for _k in list(st.session_state.keys()):
                if "_or_" in _k and any(c.isdigit() for c in _k):
                    del st.session_state[_k]
            st.session_state[_OR_LISTA_KEY] = _nova_lista
            st.session_state[_OR_HASH_KEY] = str(sorted(str(r) for r in _nova_lista))
            outras_estado[:] = _nova_lista
            st.rerun()

        outras_estado[:] = _sync_outras

        col_sv_o, _ = st.columns([1, 3])
        with col_sv_o:
            salvar_outras = st.button(
                "Salvar outras receitas",
                key="aba2_salvar_outras",
                width="stretch",
                icon=":material/save:",
            )

    # ============================================================
    # NAVEGACAO
    # ============================================================
    btn_proximo_modulo("Obras")

    # ============================================================
    # AUTO-SAVE
    # ============================================================
    if mudou or salvar_outras:
        _executar_save_aba2(
            ft_lista, projeto, receitas,
            outras_estado=st.session_state.get(CHAVE_OUTRAS_RECEITAS),
        )
