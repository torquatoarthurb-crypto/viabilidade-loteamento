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


def _gerar_distribuicao_curva_s(mes_inicio: int, qtd_meses: int) -> dict[int, float]:
    """Gera dict {mes:pct} aproximando uma curva S (logistica)."""
    import math
    if qtd_meses <= 0:
        return {}
    if qtd_meses == 1:
        return {mes_inicio: 100.0}

    # Usar logistica simetrica
    x_pts = [-3 + (6 * i / qtd_meses) for i in range(qtd_meses + 1)]
    cdf = [1 / (1 + math.exp(-x)) for x in x_pts]
    cdf_norm = [(c - cdf[0]) / (cdf[-1] - cdf[0]) for c in cdf]
    incrementos = [cdf_norm[i+1] - cdf_norm[i] for i in range(qtd_meses)]
    soma = sum(incrementos)
    incrementos = [i / soma for i in incrementos]
    return {mes_inicio + i: round(incrementos[i] * 100, 2) for i in range(qtd_meses)}


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

    # Areas de referencia
    st.info(
        f"**Areas de referencia (Aba 1):**  \n"
        f"Sistema viario = {formatar_num(areas.area_sistema_viario_m2)} m² | "
        f"Area de lotes = {formatar_num(areas.area_lotes_m2)} m² | "
        f"Gleba = {formatar_num(areas.area_gleba_m2)} m²"
    )

    # ============================================================
    # MODO DO ORCAMENTO
    # ============================================================
    st.markdown("#### Modo do Orcamento")
    modo = st.radio(
        "Como voce quer inserir o orcamento?",
        options=["resumido", "detalhado"],
        format_func=lambda x: {
            "resumido": "Resumido (R$/m² + tabela mensal unica)",
            "detalhado": "Detalhado (lista de etapas com tabela mensal)",
        }[x],
        index=0 if obras.modo == "resumido" else 1,
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
        st.markdown("**Distribuicao mensal do desembolso:**")
        st.caption("Defina intervalos com % e clique Aplicar.")

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

        atalhos_por_intervalos("resumido", horizonte, chave_atl_res)

        distrib_resumido = tabela_mensal_distribuicao(
            nome_unico="resumido",
            horizonte_meses=horizonte,
            valores_iniciais=st.session_state[chave_resumido],
            marcos=marcos,
        )
        st.session_state[chave_resumido] = distrib_resumido

        col_sv, _ = st.columns([1, 3])
        with col_sv:
            if st.button("💾 Salvar fluxo", key="aba3_res_salvar", use_container_width=True):
                salvar_fluxo = True

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
        st.caption(
            "Cada etapa tem sua propria tabela mensal. Adicione as etapas necessarias "
            "(terraplenagem, drenagem, pavimentacao, etc.). A soma de cada etapa deve ser 100%."
        )

        _garantir_estado_etapas()
        etapas_estado = st.session_state[CHAVE_ETAPAS]

        col_add, _ = st.columns([1, 3])
        with col_add:
            if st.button("➕ Adicionar etapa", use_container_width=True):
                _marcos_proj = marcos_projeto(projeto)
                _m_ini = next(
                    (k for k, v in _marcos_proj.items() if v == "Ini.Obras"), 0
                )
                _m_fim = next(
                    (k for k, v in _marcos_proj.items() if v == "Fim Obras"), _m_ini + 11
                )
                etapas_estado.append({
                    "nome": f"Etapa {len(etapas_estado)+1}",
                    "valor_total": 0.0,
                    "distribuicao": gerar_distribuicao_linear(_m_ini, _m_fim),
                })
                st.rerun()

        if not etapas_estado:
            st.info("Nenhuma etapa cadastrada. Clique em '➕ Adicionar etapa' para comecar.")

        indices_para_remover = []

        for idx, etapa in enumerate(etapas_estado):
            nome_atual = etapa.get("nome", f"Etapa {idx+1}")
            valor_atual = etapa.get("valor_total", 0.0)
            soma_pct = sum(etapa.get("distribuicao", {}).values())

            if abs(soma_pct - 100.0) < 0.01:
                status = "✅"
            elif soma_pct == 0:
                status = "⬜"
            else:
                status = "⚠️"

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
                        "🗑️", key=f"etapa_{idx}_remover", use_container_width=True,
                        help="Remover esta etapa",
                    ):
                        indices_para_remover.append(idx)

                # Atalhos por intervalos
                chave_atl_etapa = f"_ativ_result_etapa_{idx}"
                if chave_atl_etapa in st.session_state:
                    etapa["distribuicao"] = st.session_state.pop(chave_atl_etapa)
                    salvar_fluxo = True

                st.markdown("**Distribuicao por intervalos:**")
                st.caption("Defina faixas com % e clique Aplicar.")
                atalhos_por_intervalos(f"etapa_{idx}", horizonte, chave_atl_etapa)

                # Tabela mensal
                st.markdown("**Distribuicao mensal:**")
                nova_distrib = tabela_mensal_distribuicao(
                    nome_unico=f"etapa_{idx}",
                    horizonte_meses=horizonte,
                    valores_iniciais=etapa.get("distribuicao", {}),
                    marcos=marcos,
                )

                etapa["nome"] = novo_nome
                etapa["valor_total"] = novo_valor
                etapa["distribuicao"] = nova_distrib

                col_sv, _ = st.columns([1, 3])
                with col_sv:
                    if st.button("💾 Salvar fluxo", key=f"etapa_{idx}_salvar", use_container_width=True):
                        salvar_fluxo = True

        if indices_para_remover:
            for idx in sorted(indices_para_remover, reverse=True):
                etapas_estado.pop(idx)
            st.rerun()

        # Total
        if etapas_estado:
            total = sum(float(e.get("valor_total", 0) or 0) for e in etapas_estado)
            st.metric("Total custo direto (sem BDI/contingencia)", formatar_brl(total))

    # ============================================================
    # BDI E CONTINGENCIA
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 📊 BDI e Contingencia")
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
        st.caption(
            f"Custo total = custo_direto × (1 + {bdi:.2f}%) × (1 + {contingencia:.2f}%) "
            f"= custo_direto × {multiplicador:.4f}"
        )

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

            st.markdown("##### Benchmarks de Custo (com BDI e Contingencia)")
            _bc1, _bc2, _bc3, _bc4 = st.columns(4)
            with _bc1:
                st.metric("Custo total obras", formatar_brl(_custo_total_bdi))
            with _bc2:
                st.metric(
                    "R$/m² de gleba",
                    formatar_num(_custo_total_bdi / _gleba, 2),
                    help="Benchmark: obras de infraestrutura de loteamento tipicamente R$ 80-200/m² de gleba.",
                )
            with _bc3:
                st.metric(
                    "R$/m² de lote",
                    formatar_num(_custo_total_bdi / _lotes, 2),
                    help="Benchmark: R$ 100-250/m² de area de lotes.",
                )
            with _bc4:
                st.metric(
                    "R$/lote",
                    formatar_brl(_custo_total_bdi / _n_lotes),
                    help="Custo medio de obras por unidade.",
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

    # Navegacao para o proximo modulo
    btn_proximo_modulo("Incorporacao")

    # ============================================================
    # AUTO-SAVE (so roda quando Salvar e clicado ou BDI/contingencia mudou)
    # ============================================================
    bdi_mudou = obras.bdi_percentual != bdi
    contingencia_mudou = obras.contingencia_percentual != contingencia

    if not (salvar_fluxo or bdi_mudou or contingencia_mudou):
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
                nova_aba = Aba3Obras(
                    modo="detalhado",
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
            json_atual = projeto.obras.model_dump_json()
            json_novo = nova_aba.model_dump_json()
            if json_atual != json_novo:
                projeto_atualizado = projeto.model_copy(update={"obras": nova_aba})
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
            projeto = get_projeto()
            if projeto.obras.model_dump_json() != nova_aba.model_dump_json():
                set_projeto(projeto.model_copy(update={"obras": nova_aba}))
                invalidar_resultado()
    except Exception:
        pass
