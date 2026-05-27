"""
Aba 3 — Custos de Obras.

Refatorada na Fase 2.3:
- Cada etapa tem sua propria tabela mensal de % (em vez de curva linear/S/customizada antiga)
- Etapas em expanders com atalhos: linear, curva-S aproximada, limpar
- Modo resumido continua: 1 valor R$/m² + 1 distribuicao mensal
- Internamente, tudo vira modo='detalhado' com curva='customizada'
"""

from __future__ import annotations

import streamlit as st

from ...modelos import Aba3Obras, EtapaObra, OrcamentoResumido
from ..helpers import (
    aviso_validacao,
    btn_proximo_modulo,
    cabecalho_aba,
    formatar_brl,
    formatar_num,
    get_projeto,
    horizonte_visual_projeto,
    invalidar_resultado,
    marcos_projeto,
    numero_brl,
    set_projeto,
)
from ..tabela_mensal import (
    atalhos_por_intervalos,
    distribuicao_lista_para_dict,
    gerar_distribuicao_linear,
    tabela_mensal_distribuicao,
)


CHAVE_ETAPAS = "aba3_lista_etapas"

# Etapas individuais como opcoes para o botao "+ Adicionar etapa".
_ETAPAS_INDIVIDUAIS: list[str] = [
    "Personalizado",
    "Servicos Preliminares",
    "Terraplenagem",
    "Drenagem Pluvial",
    "Redes de Agua",
    "Redes de Esgoto",
    "Pavimentacao",
    "Rede Eletrica e Iluminacao",
    "Paisagismo e Areas Verdes",
    "Cerca e Portaria",
    "Sinalizacao e Demarcacao",
]

_TEMPLATES_OBRA: dict[str, list[dict]] = {
    "Loteamento 18 meses — Infraestrutura basica": [
        {"nome": "Servicos Preliminares",      "pct":  3, "m_ini":  0, "dur":  2, "curva": "linear"},
        {"nome": "Terraplenagem",              "pct": 24, "m_ini":  1, "dur":  5, "curva": "s_curve"},
        {"nome": "Drenagem Pluvial",           "pct": 17, "m_ini":  3, "dur":  7, "curva": "s_curve"},
        {"nome": "Redes de Agua",              "pct": 11, "m_ini":  4, "dur":  7, "curva": "s_curve"},
        {"nome": "Redes de Esgoto",            "pct": 14, "m_ini":  4, "dur":  8, "curva": "s_curve"},
        {"nome": "Pavimentacao",               "pct": 24, "m_ini":  8, "dur":  8, "curva": "s_curve"},
        {"nome": "Rede Eletrica e Iluminacao", "pct":  7, "m_ini": 13, "dur":  5, "curva": "linear"},
    ],
    "Loteamento 24 meses — Infraestrutura media": [
        {"nome": "Servicos Preliminares",      "pct":  3, "m_ini":  0, "dur":  2, "curva": "linear"},
        {"nome": "Terraplenagem",              "pct": 22, "m_ini":  1, "dur":  6, "curva": "s_curve"},
        {"nome": "Drenagem Pluvial",           "pct": 16, "m_ini":  4, "dur":  9, "curva": "s_curve"},
        {"nome": "Redes de Agua",              "pct": 11, "m_ini":  5, "dur": 10, "curva": "s_curve"},
        {"nome": "Redes de Esgoto",            "pct": 13, "m_ini":  5, "dur": 11, "curva": "s_curve"},
        {"nome": "Pavimentacao",               "pct": 24, "m_ini":  9, "dur": 11, "curva": "s_curve"},
        {"nome": "Rede Eletrica e Iluminacao", "pct":  8, "m_ini": 16, "dur":  7, "curva": "s_curve"},
        {"nome": "Paisagismo e Areas Verdes",  "pct":  3, "m_ini": 21, "dur":  3, "curva": "linear"},
    ],
    "Loteamento 30 meses — Infraestrutura completa": [
        {"nome": "Servicos Preliminares",      "pct":  3, "m_ini":  0, "dur":  3, "curva": "linear"},
        {"nome": "Terraplenagem",              "pct": 22, "m_ini":  1, "dur":  7, "curva": "s_curve"},
        {"nome": "Drenagem Pluvial",           "pct": 16, "m_ini":  4, "dur": 10, "curva": "s_curve"},
        {"nome": "Redes de Agua Potavel",      "pct": 10, "m_ini":  5, "dur": 12, "curva": "s_curve"},
        {"nome": "Redes de Esgoto",            "pct": 13, "m_ini":  6, "dur": 14, "curva": "s_curve"},
        {"nome": "Pavimentacao",               "pct": 23, "m_ini":  9, "dur": 14, "curva": "s_curve"},
        {"nome": "Rede Eletrica e Iluminacao", "pct":  9, "m_ini": 18, "dur":  9, "curva": "s_curve"},
        {"nome": "Paisagismo e Areas Verdes",  "pct":  4, "m_ini": 24, "dur":  5, "curva": "linear"},
    ],
}


def _gerar_distribuicao_curva_s(mes_inicio: int, qtd_meses: int) -> dict[int, float]:
    """Gera dict {mes:pct} aproximando uma curva S (logistica). Soma exata = 100."""
    import math
    if qtd_meses <= 0:
        return {}
    if qtd_meses == 1:
        return {mes_inicio: 100.0}

    x_pts = [-3 + (6 * i / qtd_meses) for i in range(qtd_meses + 1)]
    cdf = [1 / (1 + math.exp(-x)) for x in x_pts]
    cdf_norm = [(c - cdf[0]) / (cdf[-1] - cdf[0]) for c in cdf]
    incrementos = [cdf_norm[i+1] - cdf_norm[i] for i in range(qtd_meses)]
    soma = sum(incrementos)
    incrementos = [v / soma for v in incrementos]
    vals = [round(v * 100, 2) for v in incrementos]
    # Corrige residuo de arredondamento no valor de pico
    residuo = round(100.0 - sum(vals), 2)
    if residuo != 0.0:
        idx_pico = vals.index(max(vals))
        vals[idx_pico] = round(vals[idx_pico] + residuo, 2)
    return {mes_inicio + i: vals[i] for i in range(qtd_meses)}


def _carregar_etapas_do_projeto() -> list[dict]:
    """Le as etapas do projeto e converte para o formato {mes:pct}."""
    projeto = get_projeto()
    obras = projeto.obras
    out = []
    if obras.modo == "detalhado":
        for e in obras.etapas:
            if e.curva == "linear":
                distrib = gerar_distribuicao_linear(e.mes_inicio, e.mes_inicio + e.duracao_meses - 1)
            elif e.curva == "s_curve":
                distrib = _gerar_distribuicao_curva_s(e.mes_inicio, e.duracao_meses)
            elif e.curva == "customizada":
                distrib = distribuicao_lista_para_dict(e.curva_customizada, e.mes_inicio)
            else:
                distrib = {}
            out.append({
                "nome": e.nome,
                "valor_total": e.valor_total,
                "distribuicao": distrib,
            })
    return out


def _garantir_estado_etapas() -> None:
    if CHAVE_ETAPAS not in st.session_state:
        st.session_state[CHAVE_ETAPAS] = _carregar_etapas_do_projeto()


def renderizar() -> None:
    cabecalho_aba(
        3,
        "Custos de Obras",
        "Orcamento resumido (R$/m²) ou detalhado por etapa, com BDI e contingencia.",
    )

    projeto = get_projeto()
    obras = projeto.obras
    areas = projeto.terreno.areas

    horizonte = horizonte_visual_projeto(projeto)
    marcos = marcos_projeto(projeto)

    # Areas de referencia — bloco destacado
    def _ref_html(label: str, valor: str) -> str:
        return (
            f'<div style="text-align:center;">'
            f'<div style="font-size:10px;font-weight:700;color:#8A8880;letter-spacing:0.10em;'
            f'text-transform:uppercase;margin-bottom:6px;">{label}</div>'
            f'<div style="font-size:20px;font-weight:800;color:#1A1916;line-height:1;">{valor}</div>'
            f'</div>'
        )
    st.markdown(
        '<div style="background:#F0EEE9;border:1px solid #D8D4C8;border-radius:8px;'
        'padding:14px 20px;margin:0 0 16px;display:grid;'
        'grid-template-columns:1fr 1px 1fr 1px 1fr;align-items:center;gap:0;">'
        + _ref_html("Sistema Viário", f"{formatar_num(areas.area_sistema_viario_m2, 0)} m²")
        + '<div style="background:#D8D4C8;height:36px;"></div>'
        + _ref_html("Área de Lotes", f"{formatar_num(areas.area_lotes_m2, 0)} m²")
        + '<div style="background:#D8D4C8;height:36px;"></div>'
        + _ref_html("Gleba Total", f"{formatar_num(areas.area_gleba_m2, 0)} m²")
        + '</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # MODO DO ORCAMENTO
    # ============================================================
    # Pre-inicializa do modelo para que a volta ao modulo restaure o modo correto.
    # O widget usa session_state["aba3_modo"]; se nao estiver definido, usa obras.modo.
    if "aba3_modo" not in st.session_state:
        st.session_state["aba3_modo"] = "resumido"

    st.markdown("#### Modo do Orcamento")
    modo = st.radio(
        "Como voce quer inserir o orcamento?",
        options=["resumido", "detalhado"],
        format_func=lambda x: {
            "resumido": "Orçamento Paramétrico",
            "detalhado": "Orçamento Executivo",
        }[x],
        horizontal=True,
        key="aba3_modo",
    )

    distrib_resumido = None
    valor_resumido_inputs = None
    salvar_fluxo = False

    # ============================================================
    # MODO RESUMIDO
    # ============================================================
    if modo == "resumido":
        st.markdown("---")
        st.markdown("#### Orcamento Resumido")

        col1, col2 = st.columns(2)
        with col1:
            base = st.radio(
                "Base de calculo",
                options=["sistema_viario", "area_lotes"],
                format_func=lambda x: {
                    "sistema_viario": "Sobre area de sistema viario",
                    "area_lotes": "Sobre area de lotes",
                }[x],
                index=0 if (obras.resumido and obras.resumido.base_calculo == "sistema_viario") else 1,
                key="aba3_base",
            )
            valor_m2 = numero_brl(
                "Valor R$/m²",
                value=float(obras.resumido.valor_por_m2) if obras.resumido else 250.0,
                key="aba3_valor_m2",
                min_value=0.01,
            )

        with col2:
            base_m2 = areas.area_sistema_viario_m2 if base == "sistema_viario" else areas.area_lotes_m2
            valor_estimado = base_m2 * valor_m2
            st.metric("Custo direto estimado", formatar_brl(valor_estimado))

        # Atalhos + tabela mensal para o resumido
        st.markdown(
            '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
            'text-transform:uppercase;color:var(--stone-500);margin:10px 0 4px;">Distribuição mensal do desembolso</div>',
            unsafe_allow_html=True,
        )

        # Ler/inicializar distribuicao do resumido (estado em sessao)
        chave_resumido = "aba3_resumido_distrib"
        if chave_resumido not in st.session_state:
            if obras.resumido:
                st.session_state[chave_resumido] = _gerar_distribuicao_curva_s(
                    obras.resumido.mes_inicio, obras.resumido.duracao_meses
                )
            else:
                st.session_state[chave_resumido] = {}

        # Verificar resultado de atalhos (apply foi clicado no render anterior)
        chave_atl_res = "_ativ_result_resumido"
        if chave_atl_res in st.session_state:
            st.session_state[chave_resumido] = st.session_state.pop(chave_atl_res)
            salvar_fluxo = True

        # ---- Template de curva para o resumido ----
        with st.expander("Preencher com template de curva"):
            _tmpl_dur_opcoes = {
                "18 meses — Curva S (basico)":    18,
                "24 meses — Curva S (medio)":     24,
                "30 meses — Curva S (completo)":  30,
            }
            _tmpl_res_sel = st.selectbox(
                "Horizonte da obra",
                list(_tmpl_dur_opcoes.keys()),
                key="aba3_tmpl_res_sel",
                help="Gera uma curva S sobre o período de obras configurado no projeto.",
            )
            _dur_res = _tmpl_dur_opcoes[_tmpl_res_sel]
            _m_ini_res = next(
                (k for k, v in marcos.items() if "Ini" in v and "Obra" in v), 0
            )
            _m_fim_res = _m_ini_res + _dur_res - 1

            # Preview visual da curva S como blocos ASCII
            import math as _math
            _n = _dur_res
            _xs = [-3 + 6 * i / _n for i in range(_n)]
            _cdf = [1 / (1 + _math.exp(-x)) for x in _xs]
            _c0, _c1 = _cdf[0], _cdf[-1]
            _incrementos = [
                (_cdf[i + 1] - _cdf[i]) / (_c1 - _c0) if i < _n - 1
                else (_cdf[-1] - _cdf[-2]) / (_c1 - _c0)
                for i in range(_n)
            ]
            _max_inc = max(_incrementos) or 1
            _barras = "".join(
                "▁▂▃▄▅▆▇█"[min(7, int(v / _max_inc * 8))]
                for v in _incrementos
            )
            st.caption(
                f"M{_m_ini_res} → M{_m_fim_res}  |  {_dur_res} meses  |  "
                f"desembolso mensal: `{_barras}`"
            )

            if st.button(
                "Aplicar curva",
                key="aba3_tmpl_res_aplicar",
                type="primary",
                width="content",
                help="Preenche a tabela mensal com a curva S gerada.",
            ):
                st.session_state[chave_resumido] = _gerar_distribuicao_curva_s(
                    _m_ini_res, _dur_res
                )
                salvar_fluxo = True
                st.rerun()

        atalhos_por_intervalos("resumido", horizonte, chave_atl_res)

        distrib_resumido = tabela_mensal_distribuicao(
            nome_unico="resumido",
            horizonte_meses=horizonte,
            valores_iniciais=st.session_state[chave_resumido],
            marcos=marcos,
        )
        st.session_state[chave_resumido] = distrib_resumido

        valor_resumido_inputs = {
            "base_calculo": base,
            "valor_por_m2": valor_m2,
        }

    # ============================================================
    # MODO DETALHADO
    # ============================================================
    else:
        st.markdown("---")
        st.markdown("#### Etapas de Obra")

        _garantir_estado_etapas()
        etapas_estado = st.session_state[CHAVE_ETAPAS]

        # ---- Templates pre-configurados (secundario — fechado por padrao) ----
        with st.expander("Carregar conjunto completo de etapas (template)", expanded=False):
            m_ini_obras = next(
                (k for k, v in marcos.items() if "Ini" in v and "Obra" in v), 0
            )

            template_opcoes = list(_TEMPLATES_OBRA.keys())
            template_sel = st.selectbox(
                "Selecione um template",
                template_opcoes,
                key="aba3_template_sel",
                help="Templates baseados em cronogramas reais de loteamentos, com etapas sobrepostas.",
            )

            etapas_tmpl = _TEMPLATES_OBRA[template_sel]
            m_fim_tmpl = m_ini_obras + max(s["m_ini"] + s["dur"] for s in etapas_tmpl) - 1

            st.caption(
                f"{len(etapas_tmpl)} etapas  |  "
                f"M{m_ini_obras} → M{m_fim_tmpl}  |  "
                f"Duração total: {m_fim_tmpl - m_ini_obras + 1} meses"
            )

            # Preview das etapas com barra visual de sobreposição
            cols_hdr = st.columns([3, 1, 4])
            cols_hdr[0].markdown("**Etapa**")
            cols_hdr[1].markdown("**~%custo**")
            cols_hdr[2].markdown("**Período (relativo ao início das obras)**")

            dur_total = max(s["m_ini"] + s["dur"] for s in etapas_tmpl)
            for s in etapas_tmpl:
                cols = st.columns([3, 1, 4])
                m_abs_ini = m_ini_obras + s["m_ini"]
                m_abs_fim = m_abs_ini + s["dur"] - 1
                cols[0].caption(s["nome"])
                cols[1].caption(f"{s['pct']}%")
                # Barra ASCII proporcional
                offset = int(s["m_ini"] / dur_total * 24)
                width  = max(1, int(s["dur"] / dur_total * 24))
                barra  = " " * offset + "█" * width
                cols[2].caption(f"`{barra}` M{m_abs_ini}–M{m_abs_fim}")


            col_sub, col_add_t, _ = st.columns([1, 1, 2])
            with col_sub:
                if st.button(
                    "Substituir etapas",
                    key="aba3_tmpl_substituir",
                    type="primary",
                    width="stretch",
                    help="Apaga as etapas existentes e carrega o template selecionado.",
                ):
                    novas = []
                    for s in etapas_tmpl:
                        m_abs = m_ini_obras + s["m_ini"]
                        dist = (
                            _gerar_distribuicao_curva_s(m_abs, s["dur"])
                            if s["curva"] == "s_curve"
                            else gerar_distribuicao_linear(m_abs, m_abs + s["dur"] - 1)
                        )
                        novas.append({"nome": s["nome"], "valor_total": 0.0, "distribuicao": dist})
                    st.session_state[CHAVE_ETAPAS] = novas
                    st.rerun()
            with col_add_t:
                if st.button(
                    "Adicionar ao projeto",
                    key="aba3_tmpl_adicionar",
                    width="stretch",
                    help="Mantém etapas existentes e acrescenta as do template.",
                ):
                    for s in etapas_tmpl:
                        m_abs = m_ini_obras + s["m_ini"]
                        dist = (
                            _gerar_distribuicao_curva_s(m_abs, s["dur"])
                            if s["curva"] == "s_curve"
                            else gerar_distribuicao_linear(m_abs, m_abs + s["dur"] - 1)
                        )
                        etapas_estado.append({"nome": s["nome"], "valor_total": 0.0, "distribuicao": dist})
                    st.rerun()

        st.markdown("---")
        col_add, col_sel = st.columns([1, 3])
        with col_sel:
            etapa_add_sel = st.selectbox(
                "Tipo de etapa",
                _ETAPAS_INDIVIDUAIS,
                key="aba3_add_sel",
                help="Escolha uma etapa predefinida ou 'Personalizado' para comecar em branco.",
            )
        with col_add:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            if st.button("+ Adicionar", key="aba3_add_btn", type="primary", width="stretch"):
                nome = "Nova etapa" if etapa_add_sel == "Personalizado" else etapa_add_sel
                etapas_estado.append({"nome": nome, "valor_total": 0.0, "distribuicao": {}})
                st.rerun()

        if not etapas_estado:
            st.info("Nenhuma etapa cadastrada. Clique em '+ Adicionar etapa' para comecar.")

        indices_para_remover = []

        for idx, etapa in enumerate(etapas_estado):
            nome_atual = etapa.get("nome", f"Etapa {idx+1}")
            valor_atual = etapa.get("valor_total", 0.0)
            soma_pct = sum(etapa.get("distribuicao", {}).values())

            if abs(soma_pct - 100.0) < 0.01:
                status = "✓"
            elif soma_pct == 0:
                status = "○"
            else:
                status = "!"

            titulo = f"{status} **{nome_atual}** — {formatar_brl(valor_atual)}"

            with st.expander(titulo, expanded=False, key=f"exp_etapa_{idx}"):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    novo_nome = st.text_input(
                        "Nome da etapa", value=nome_atual, key=f"etapa_{idx}_nome"
                    )
                with col2:
                    novo_valor = numero_brl(
                        "Valor total (R$)",
                        value=float(valor_atual),
                        key=f"etapa_{idx}_valor",
                        min_value=0.0,
                    )
                with col3:
                    st.markdown("&nbsp;")
                    if st.button(
                        "Remover", key=f"etapa_{idx}_remover", width="stretch",
                        help="Remover esta etapa", icon=":material/delete:",
                    ):
                        indices_para_remover.append(idx)

                # Atalhos por intervalos
                chave_atl_etapa = f"_ativ_result_etapa_{idx}"
                if chave_atl_etapa in st.session_state:
                    etapa["distribuicao"] = st.session_state.pop(chave_atl_etapa)
                    salvar_fluxo = True

                st.markdown(
                    '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
                    'text-transform:uppercase;color:var(--stone-500);margin:10px 0 4px;">Distribuição por intervalos</div>',
                    unsafe_allow_html=True,
                )
                atalhos_por_intervalos(f"etapa_{idx}", horizonte, chave_atl_etapa)

                # Tabela mensal
                st.markdown(
                    '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
                    'text-transform:uppercase;color:var(--stone-500);margin:10px 0 4px;">Distribuição mensal</div>',
                    unsafe_allow_html=True,
                )
                nova_distrib = tabela_mensal_distribuicao(
                    nome_unico=f"etapa_{idx}",
                    horizonte_meses=horizonte,
                    valores_iniciais=etapa.get("distribuicao", {}),
                    marcos=marcos,
                )

                etapa["nome"] = novo_nome
                etapa["valor_total"] = novo_valor
                etapa["distribuicao"] = nova_distrib

        if indices_para_remover:
            for idx in sorted(indices_para_remover, reverse=True):
                etapas_estado.pop(idx)
            st.rerun()

        # Total
        if etapas_estado:
            total = sum(float(e.get("valor_total", 0) or 0) for e in etapas_estado)
            st.markdown(
                '<div style="margin:8px 0 4px;font-size:10px;font-weight:600;letter-spacing:0.10em;'
                'text-transform:uppercase;color:var(--stone-500);">Total das etapas</div>',
                unsafe_allow_html=True,
            )
            _tc1, _tc2 = st.columns(2)
            with _tc1:
                st.metric("Custo direto (sem BDI/contingência)", formatar_brl(total))

    # ============================================================
    # BDI E CONTINGENCIA
    # ============================================================
    with st.container(border=True):
        st.markdown("#### BDI e Contingência")
        col1, col2 = st.columns(2)
        with col1:
            bdi = numero_brl(
                "BDI (%) sobre custo direto",
                value=float(obras.bdi_percentual),
                key="aba3_bdi",
                min_value=0.0,
                help="Beneficios e Despesas Indiretas (administracao, lucro, impostos da construtora). "
                     "Pratica de mercado: 15-25% para infraestrutura de loteamento.",
            )
        with col2:
            contingencia = numero_brl(
                "Contingencia (%) sobre o total",
                value=float(obras.contingencia_percentual),
                key="aba3_contingencia",
                min_value=0.0,
                help="Reserva para imprevistos, calculada sobre o custo total ja com BDI. "
                     "Pratica de mercado: 5-10%.",
            )

        multiplicador = (1 + bdi / 100) * (1 + contingencia / 100)

        # B1: benchmarks de custo por m² e por lote
        if modo == "resumido":
            _base_m2 = areas.area_sistema_viario_m2 if base == "sistema_viario" else areas.area_lotes_m2
            _custo_dir = _base_m2 * valor_m2
        else:
            _custo_dir = sum(
                float(e.get("valor_total", 0) or 0)
                for e in st.session_state.get(CHAVE_ETAPAS, [])
            )
        _custo_total_bdi = _custo_dir * multiplicador

        if _custo_total_bdi > 0:
            _gleba = float(areas.area_gleba_m2) or 1.0
            _lotes = float(areas.area_lotes_m2) or 1.0
            _n_lotes = projeto.terreno.total_lotes or 1

            def _ind_obra_html(label: str, valor: str) -> str:
                return (
                    f'<div style="text-align:center;">'
                    f'<div style="font-size:10px;font-weight:700;color:#8A8880;letter-spacing:0.10em;'
                    f'text-transform:uppercase;margin-bottom:6px;">{label}</div>'
                    f'<div style="font-size:18px;font-weight:800;color:#1A1916;line-height:1;">{valor}</div>'
                    f'</div>'
                )

            st.markdown(
                '<div style="margin:14px 0 4px;font-size:10px;font-weight:600;'
                'letter-spacing:0.10em;text-transform:uppercase;color:var(--stone-500);">'
                'Índices da Obra</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="background:#F0EEE9;border:1px solid #D8D4C8;border-radius:8px;'
                'padding:14px 20px;margin:0 0 4px;display:grid;'
                'grid-template-columns:1fr 1px 1fr 1px 1fr 1px 1fr;align-items:center;gap:0;">'
                + _ind_obra_html("Custo Total Obras", formatar_brl(_custo_total_bdi))
                + '<div style="background:#D8D4C8;height:36px;"></div>'
                + _ind_obra_html("R$/m² de Gleba", formatar_num(_custo_total_bdi / _gleba, 2))
                + '<div style="background:#D8D4C8;height:36px;"></div>'
                + _ind_obra_html("R$/m² de Lote", formatar_num(_custo_total_bdi / _lotes, 2))
                + '<div style="background:#D8D4C8;height:36px;"></div>'
                + _ind_obra_html("R$/Lote", formatar_brl(_custo_total_bdi / _n_lotes))
                + '</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # ARMAZENAR ESTADO PARA SINCRONIZACAO (sidebar / Calcular)
    # ============================================================
    st.session_state["_aba3_modo"] = modo
    st.session_state["_aba3_bdi"] = bdi
    st.session_state["_aba3_contingencia"] = contingencia
    st.session_state["_aba3_areas"] = {
        "area_sistema_viario_m2": float(areas.area_sistema_viario_m2),
        "area_lotes_m2": float(areas.area_lotes_m2),
    }
    if modo == "resumido":
        st.session_state["_aba3_valor_m2"] = float(valor_m2)
        st.session_state["_aba3_base_calculo"] = str(base)

    # ============================================================
    # SALVAR ABA
    # ============================================================
    st.markdown("---")
    _col_sv3, _ = st.columns([1, 3])
    with _col_sv3:
        if st.button(
            "Salvar aba",
            key="aba3_salvar_aba",
            type="primary",
            width="stretch",
            icon=":material/save:",
        ):
            salvar_fluxo = True

    # Navegacao para o proximo modulo
    btn_proximo_modulo("Incorporacao")

    # ============================================================
    # AUTO-SAVE (so roda quando Salvar e clicado ou BDI/contingencia mudou)
    # ============================================================
    if not salvar_fluxo:
        return

    try:
        if modo == "resumido":
            if distrib_resumido and abs(sum(distrib_resumido.values()) - 100.0) < 0.01:
                mes_min = min(distrib_resumido.keys())
                mes_max = max(distrib_resumido.keys())
                duracao = mes_max - mes_min + 1
                lista_pct = [distrib_resumido.get(mes_min + i, 0.0) for i in range(duracao)]

                base_m2 = (
                    areas.area_sistema_viario_m2
                    if valor_resumido_inputs["base_calculo"] == "sistema_viario"
                    else areas.area_lotes_m2
                )
                valor_total = base_m2 * valor_resumido_inputs["valor_por_m2"]
                etapa_unica = EtapaObra(
                    nome="Obras (resumido)",
                    valor_total=valor_total,
                    mes_inicio=mes_min,
                    duracao_meses=duracao,
                    curva="customizada",
                    curva_customizada=lista_pct,
                )
                # Salva modo="resumido" para que a volta ao modulo restaure o radio.
                # etapas tambem populada para o engine de calculo.
                nova_aba = Aba3Obras(
                    modo="resumido",
                    resumido=OrcamentoResumido(
                        base_calculo=valor_resumido_inputs["base_calculo"],
                        valor_por_m2=valor_resumido_inputs["valor_por_m2"],
                        mes_inicio=mes_min,
                        duracao_meses=duracao,
                        curva="s_curve",
                    ),
                    etapas=[etapa_unica],
                    bdi_percentual=bdi,
                    contingencia_percentual=contingencia,
                )
            else:
                nova_aba = None  # invalido — nao salva

        else:
            etapas_estado = st.session_state.get(CHAVE_ETAPAS, [])
            etapas_obj = []
            for et in etapas_estado:
                nome = str(et.get("nome", "")).strip()
                if not nome:
                    continue
                valor_total = float(et.get("valor_total", 0) or 0)
                if valor_total <= 0:
                    continue
                distrib = et.get("distribuicao", {})
                if not distrib:
                    continue
                soma = sum(distrib.values())
                if abs(soma - 100.0) > 0.01:
                    continue

                mes_min = min(distrib.keys())
                mes_max = max(distrib.keys())
                qtd = mes_max - mes_min + 1
                lista_pct = [distrib.get(mes_min + i, 0.0) for i in range(qtd)]

                try:
                    etapas_obj.append(EtapaObra(
                        nome=nome,
                        valor_total=valor_total,
                        mes_inicio=mes_min,
                        duracao_meses=qtd,
                        curva="customizada",
                        curva_customizada=lista_pct,
                    ))
                except Exception:
                    continue

            if etapas_obj:
                nova_aba = Aba3Obras(
                    modo="detalhado",
                    etapas=etapas_obj,
                    bdi_percentual=bdi,
                    contingencia_percentual=contingencia,
                )
            else:
                nova_aba = None

        if nova_aba is not None:
            from ...engine.utilidades import meses_entre
            projeto_atualizado = projeto
            if projeto.obras.model_dump_json() != nova_aba.model_dump_json():
                projeto_atualizado = projeto_atualizado.model_copy(update={"obras": nova_aba})

            # Atualizar termino_obras se o fluxo ultrapassar a duracao configurada
            m_max: int | None = None
            if nova_aba.modo == "resumido" and nova_aba.resumido:
                m_max = nova_aba.resumido.mes_inicio + nova_aba.resumido.duracao_meses
            elif nova_aba.modo == "detalhado" and nova_aba.etapas:
                m_max = max(e.mes_inicio + e.duracao_meses for e in nova_aba.etapas)

            if m_max is not None:
                datas = projeto.terreno.datas
                m_ini_obras = meses_entre(datas.inicio_projeto, datas.inicio_obras)
                m_fim_atual = meses_entre(datas.inicio_projeto, datas.termino_obras)
                if m_max > m_fim_atual:
                    nova_duracao = m_max - m_ini_obras
                    _ano = datas.inicio_obras.year + (datas.inicio_obras.month - 1 + nova_duracao) // 12
                    _mes = (datas.inicio_obras.month - 1 + nova_duracao) % 12 + 1
                    from datetime import date as _date
                    novo_termino = _date(_ano, _mes, 1)
                    novas_datas = datas.model_copy(update={"termino_obras": novo_termino})
                    novo_terreno = projeto.terreno.model_copy(update={"datas": novas_datas})
                    projeto_atualizado = projeto_atualizado.model_copy(update={"terreno": novo_terreno})
                    st.session_state["_aba1_duracao_obras_override"] = nova_duracao

            if projeto_atualizado is not projeto:
                set_projeto(projeto_atualizado)
                invalidar_resultado()
    except Exception:
        pass


def sincronizar_aba3() -> None:
    """Salva o estado em memoria da Aba 3 no projeto (chamado pelo sidebar antes de Calcular)."""
    modo = st.session_state.get("_aba3_modo")
    if modo is None:
        return

    bdi = float(st.session_state.get("_aba3_bdi", 0.0))
    contingencia = float(st.session_state.get("_aba3_contingencia", 0.0))
    areas_info = st.session_state.get("_aba3_areas", {})
    area_sv = float(areas_info.get("area_sistema_viario_m2", 0.0))
    area_lotes = float(areas_info.get("area_lotes_m2", 0.0))

    try:
        nova_aba = None
        if modo == "resumido":
            distrib = st.session_state.get("aba3_resumido_distrib", {})
            if distrib and abs(sum(distrib.values()) - 100.0) < 0.01:
                mes_min = min(distrib.keys())
                mes_max = max(distrib.keys())
                duracao = mes_max - mes_min + 1
                lista_pct = [distrib.get(mes_min + i, 0.0) for i in range(duracao)]
                base_calculo = st.session_state.get("_aba3_base_calculo", "sistema_viario")
                base_m2 = area_sv if base_calculo != "area_lotes" else area_lotes
                valor_m2 = float(st.session_state.get("_aba3_valor_m2", 250.0))
                valor_total = base_m2 * valor_m2
                etapa_unica = EtapaObra(
                    nome="Obras (resumido)",
                    valor_total=valor_total,
                    mes_inicio=mes_min,
                    duracao_meses=duracao,
                    curva="customizada",
                    curva_customizada=lista_pct,
                )
                nova_aba = Aba3Obras(
                    modo="detalhado",
                    etapas=[etapa_unica],
                    bdi_percentual=bdi,
                    contingencia_percentual=contingencia,
                )
        else:
            etapas_estado = st.session_state.get(CHAVE_ETAPAS, [])
            etapas_obj = []
            for et in etapas_estado:
                nome = str(et.get("nome", "")).strip()
                valor_total = float(et.get("valor_total", 0) or 0)
                distrib = et.get("distribuicao", {})
                if not nome or valor_total <= 0 or not distrib:
                    continue
                if abs(sum(distrib.values()) - 100.0) > 0.01:
                    continue
                mes_min = min(distrib.keys())
                mes_max = max(distrib.keys())
                qtd = mes_max - mes_min + 1
                lista_pct = [distrib.get(mes_min + i, 0.0) for i in range(qtd)]
                try:
                    etapas_obj.append(EtapaObra(
                        nome=nome,
                        valor_total=valor_total,
                        mes_inicio=mes_min,
                        duracao_meses=qtd,
                        curva="customizada",
                        curva_customizada=lista_pct,
                    ))
                except Exception:
                    continue
            if etapas_obj:
                nova_aba = Aba3Obras(
                    modo="detalhado",
                    etapas=etapas_obj,
                    bdi_percentual=bdi,
                    contingencia_percentual=contingencia,
                )

        if nova_aba is not None:
            from ..helpers import get_projeto, set_projeto, invalidar_resultado
            from ...engine.utilidades import meses_entre
            projeto = get_projeto()
            projeto_atualizado = projeto

            if projeto.obras.model_dump_json() != nova_aba.model_dump_json():
                projeto_atualizado = projeto_atualizado.model_copy(update={"obras": nova_aba})

            # Verificar se o fluxo das etapas ultrapassa o termino_obras configurado
            m_max: int | None = None
            if nova_aba.modo == "resumido" and nova_aba.resumido:
                m_max = nova_aba.resumido.mes_inicio + nova_aba.resumido.duracao_meses
            elif nova_aba.modo == "detalhado" and nova_aba.etapas:
                m_max = max(e.mes_inicio + e.duracao_meses for e in nova_aba.etapas)

            if m_max is not None:
                datas = projeto.terreno.datas
                m_ini_obras = meses_entre(datas.inicio_projeto, datas.inicio_obras)
                m_fim_atual = meses_entre(datas.inicio_projeto, datas.termino_obras)
                if m_max > m_fim_atual:
                    nova_duracao = m_max - m_ini_obras
                    _ano = datas.inicio_obras.year + (datas.inicio_obras.month - 1 + nova_duracao) // 12
                    _mes = (datas.inicio_obras.month - 1 + nova_duracao) % 12 + 1
                    from datetime import date as _date
                    novo_termino = _date(_ano, _mes, 1)
                    novas_datas = datas.model_copy(update={"termino_obras": novo_termino})
                    novo_terreno = projeto.terreno.model_copy(update={"datas": novas_datas})
                    projeto_atualizado = projeto_atualizado.model_copy(update={"terreno": novo_terreno})
                    st.session_state["_aba1_duracao_obras_override"] = nova_duracao

            if projeto_atualizado is not projeto:
                set_projeto(projeto_atualizado)
                invalidar_resultado()
    except Exception:
        pass
