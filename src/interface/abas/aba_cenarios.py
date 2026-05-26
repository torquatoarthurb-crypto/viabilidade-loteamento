"""
Modulo 11 — Cenarios e Simulacoes.

C2 — Comparativo de Cenarios (snapshots nomeados)
C4 — Simulacao de Monte Carlo (distribuicao de TIR)
"""

from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import streamlit as st

from ...engine import calcular_fluxo_caixa
from ...modelos import Projeto
from ..helpers import (
    cabecalho_aba,
    formatar_brl,
    formatar_pct,
    get_projeto,
    get_resultado,
    invalidar_resultado,
    limpar_cache_inputs_brl,
    renderizar_calcular_cta,
    set_projeto,
)
from .aba_ferramentas import _variar_obras, _variar_preco, _variar_terreno

CHAVE_CENARIOS = "_cenarios_lista"
_CHAVES_ABA_CACHE = [
    "aba2_lista_fluxos", "aba2_curva_mensal", "aba3_lista_etapas",
    "aba3_resumido_distrib", "aba4_lista_despesas", "aba_terreno_fluxo_distrib",
]


def renderizar() -> None:
    cabecalho_aba(
        11,
        "Cenarios e Simulacoes",
        "Compare diferentes versoes do projeto e avalie risco com Monte Carlo.",
    )
    tabs = st.tabs(["Comparativo de Cenários", "Monte Carlo"])
    with tabs[0]:
        _renderizar_cenarios()
    with tabs[1]:
        _renderizar_monte_carlo()


# =====================================================================
# C2 — COMPARATIVO DE CENARIOS
# =====================================================================

def _renderizar_cenarios() -> None:
    st.markdown("#### Comparativo de Cenarios")
    st.caption(
        "Salve snapshots do projeto atual para comparar diferentes premissas. "
        "Cada cenario preserva todos os parametros e o resultado calculado."
    )

    resultado = get_resultado()
    projeto = get_projeto()

    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        nome_cenario = st.text_input(
            "Nome do cenario",
            placeholder="Ex.: Base, Otimista, Pessimista, Preco +10%...",
            key="cenario_nome_input",
            label_visibility="collapsed",
        )
    with col2:
        btn_salvar = st.button(
            "Salvar",
            key="btn_salvar_cenario",
            disabled=(resultado is None),
            width="stretch",
            help="Salva o projeto e resultado atual como um cenario nomeado.",
            icon=":material/save:",
        )
    with col3:
        btn_limpar = st.button("Limpar", key="btn_limpar_cenarios",
                               width="stretch",
                               help="Remove todos os cenarios salvos.",
                               icon=":material/delete_sweep:")

    if resultado is None:
        st.warning("Calcule o fluxo de caixa antes de salvar um cenario.")
    else:
        st.caption("Insira um nome e clique em Salvar para registrar o estado atual.")

    if btn_salvar and resultado and nome_cenario.strip():
        _salvar_cenario(nome_cenario.strip(), projeto, resultado)
        st.success(f"Cenário '{nome_cenario.strip()}' salvo.")
        st.rerun()
    elif btn_salvar and not nome_cenario.strip():
        st.error("Informe um nome para o cenario.")

    if btn_limpar:
        st.session_state[CHAVE_CENARIOS] = []
        st.rerun()

    cenarios = st.session_state.get(CHAVE_CENARIOS, [])
    if not cenarios:
        st.info("Nenhum cenario salvo. Calcule o fluxo, defina um nome e clique em Salvar.")
        return

    st.markdown(f"#### {len(cenarios)} cenario(s) salvo(s)")
    _mostrar_tabela_cenarios(cenarios)

    st.markdown("---")
    st.markdown("**Acoes por cenario:**")
    for i, c in enumerate(cenarios):
        tir_str = f"{c['tir'] * 100:.1f}% a.a." if c.get("tir") else "sem TIR"
        col_i, col_l, col_d = st.columns([5, 1, 1])
        with col_i:
            st.markdown(
                f'<span style="color:#E8EAED;font-weight:600">{c["nome"]}</span>'
                f' <span style="color:#9CA3AF;font-size:11px">'
                f'— {c["timestamp"]} — TIR: {tir_str}</span>',
                unsafe_allow_html=True,
            )
        with col_l:
            if st.button("Carregar", key=f"btn_load_cen_{i}",
                         help="Carregar este cenario como projeto ativo",
                         width="stretch",
                         icon=":material/folder_open:"):
                _carregar_cenario(i)
        with col_d:
            if st.button("Remover", key=f"btn_del_cen_{i}",
                         help="Remover este cenario",
                         width="stretch",
                         icon=":material/delete:"):
                cenarios.pop(i)
                st.session_state[CHAVE_CENARIOS] = cenarios
                st.rerun()


def _salvar_cenario(nome: str, projeto, resultado) -> None:
    if CHAVE_CENARIOS not in st.session_state:
        st.session_state[CHAVE_CENARIOS] = []

    ind = resultado.indicadores
    r = resultado.resumo
    st.session_state[CHAVE_CENARIOS].append({
        "nome": nome,
        "timestamp": datetime.now().strftime("%d/%m %H:%M"),
        "tir": ind.get("tir_anual"),
        "vpl": ind.get("vpl"),
        "lucro": r.get("lucro_liquido"),
        "vgv": r.get("vgv_bruto"),
        "exposicao": ind.get("exposicao_maxima"),
        "payback": ind.get("payback_simples_meses"),
        "margem": r.get("margem_sobre_vgv_vendavel"),
        "custo_financeiro": r.get("custo_financiamento_total", 0),
        "projeto_json": projeto.model_dump_json(),
    })
    if len(st.session_state[CHAVE_CENARIOS]) > 10:
        st.session_state[CHAVE_CENARIOS] = st.session_state[CHAVE_CENARIOS][-10:]


def _carregar_cenario(idx: int) -> None:
    cenarios = st.session_state.get(CHAVE_CENARIOS, [])
    if idx >= len(cenarios):
        return
    try:
        novo_projeto = Projeto.model_validate(json.loads(cenarios[idx]["projeto_json"]))
        set_projeto(novo_projeto)
        invalidar_resultado()
        limpar_cache_inputs_brl()
        for chave in _CHAVES_ABA_CACHE:
            if chave in st.session_state:
                del st.session_state[chave]
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar cenario: {e}")


def _mostrar_tabela_cenarios(cenarios: list) -> None:
    import plotly.graph_objects as go

    def ft(v: float | None) -> str:
        return f"{v * 100:.1f}%" if v else "—"

    def fm(v: float | None) -> str:
        if v is None:
            return "—"
        av = abs(v)
        if av >= 1_000_000:
            return f"R$ {v / 1_000_000:.1f}M"
        return f"R$ {v / 1_000:.0f}k"

    def fexp(v: float | None) -> str:
        if v is None:
            return "—"
        av = abs(v)
        txt = f"R$ {av / 1_000_000:.1f}M" if av >= 1_000_000 else f"R$ {av / 1_000:.0f}k"
        return txt

    def ffin(v) -> str:
        if not v:
            return "—"
        v = float(v)
        if v < 1:
            return "—"
        return f"R$ {v / 1_000_000:.1f}M" if v >= 1_000_000 else f"R$ {v / 1_000:.0f}k"

    thead = (
        "<thead><tr>"
        "<th>Nome</th><th>Salvo</th><th>VGV</th><th>Lucro</th>"
        "<th>Margem</th><th>TIR</th><th>VPL</th><th>Payback</th>"
        "<th>Exposicao</th><th>Custo Fin.</th>"
        "</tr></thead>"
    )
    linhas = ""
    for c in cenarios:
        pb = c.get("payback")
        linhas += (
            f"<tr>"
            f"<td><b>{c['nome']}</b></td>"
            f"<td style='font-size:11px;color:#9CA3AF'>{c['timestamp']}</td>"
            f"<td>{fm(c.get('vgv'))}</td>"
            f"<td>{fm(c.get('lucro'))}</td>"
            f"<td>{ft(c.get('margem'))}</td>"
            f"<td style='color:#34D399'>{ft(c.get('tir'))}</td>"
            f"<td>{fm(c.get('vpl'))}</td>"
            f"<td>{str(pb) + 'm' if pb else '—'}</td>"
            f"<td style='color:#F87171'>{fexp(c.get('exposicao'))}</td>"
            f"<td style='color:#FBBF24'>{ffin(c.get('custo_financeiro'))}</td>"
            f"</tr>"
        )
    st.markdown(
        f'<table class="dre-table"><thead>{thead}</thead><tbody>{linhas}</tbody></table>',
        unsafe_allow_html=True,
    )

    if len(cenarios) >= 2:
        nomes = [c["nome"] for c in cenarios]
        tirs = [(c.get("tir") or 0) * 100 for c in cenarios]
        fig = go.Figure(go.Bar(
            x=nomes, y=tirs,
            marker_color="#4A7FA5",
            text=[f"{t:.1f}%" for t in tirs],
            textposition="outside",
            textfont=dict(color="#1A1916"),
        ))
        fig.update_layout(
            title="TIR por Cenario (%)",
            paper_bgcolor="#F5F3EE", plot_bgcolor="#ECEAE4",
            font=dict(color="#1A1916", size=12),
            xaxis=dict(gridcolor="#D8D4C8"),
            yaxis=dict(gridcolor="#D8D4C8", ticksuffix="%"),
            margin=dict(l=40, r=40, t=50, b=40),
            height=280,
        )
        st.plotly_chart(fig, use_container_width=True, key="fig_cenarios_tir")


# =====================================================================
# C4 — MONTE CARLO
# =====================================================================

def _renderizar_monte_carlo() -> None:
    st.markdown("#### Simulacao de Monte Carlo")
    st.caption(
        "Varia os parametros principais de forma aleatoria (distribuicao normal) "
        "e mostra a distribuicao de TIR possivel. "
        "Quanto mais larga a curva, maior o risco do projeto."
    )

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    projeto = get_projeto()
    tir_base = resultado.indicadores.get("tir_anual")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_sim = st.selectbox(
            "N° de simulacoes",
            options=[100, 200, 500],
            index=1,
            key="mc_n_sim",
        )
    with col2:
        sigma_preco = st.slider(
            "Variacao preco (σ%)",
            min_value=0, max_value=30, value=10, step=1,
            key="mc_sigma_preco",
            help="Desvio padrao da variacao aleatoria do preco de venda",
        )
    with col3:
        sigma_obras = st.slider(
            "Variacao obras (σ%)",
            min_value=0, max_value=30, value=10, step=1,
            key="mc_sigma_obras",
            help="Desvio padrao da variacao aleatoria do custo de obras",
        )
    with col4:
        sigma_terreno = st.slider(
            "Variacao terreno (σ%)",
            min_value=0, max_value=30, value=5, step=1,
            key="mc_sigma_terreno",
            help="Desvio padrao da variacao aleatoria do custo do terreno",
        )

    if tir_base:
        st.info(
            f"TIR base: **{tir_base * 100:.1f}%** a.a.  |  "
            f"Cada simulacao sorteia fatores aleatorios com distribuicao normal "
            f"(media=100%, desvios: preco σ={sigma_preco}%, obras σ={sigma_obras}%, "
            f"terreno σ={sigma_terreno}%)."
        )

    if not st.button("▶ Executar Monte Carlo", key="btn_mc_run", type="primary"):
        return

    with st.spinner(f"Rodando {n_sim} simulacoes..."):
        tirs = _rodar_monte_carlo(
            projeto, n_sim,
            sigma_preco / 100, sigma_obras / 100, sigma_terreno / 100,
        )

    if not tirs:
        st.error("Nenhuma simulacao retornou TIR calculavel. Verifique o projeto.")
        return

    st.session_state["_mc_resultados"] = {
        "tirs": tirs,
        "tir_base": tir_base,
        "n_sim": n_sim,
    }
    _mostrar_resultados_mc(tirs, tir_base)


def _rodar_monte_carlo(
    projeto, n_sim: int,
    sigma_p: float, sigma_o: float, sigma_t: float,
) -> list[float]:
    rng = np.random.default_rng()
    resultados: list[float] = []

    prog = st.progress(0)
    for i in range(n_sim):
        fp = float(np.clip(rng.normal(1.0, sigma_p), 0.1, 5.0)) if sigma_p > 0 else 1.0
        fo = float(np.clip(rng.normal(1.0, sigma_o), 0.1, 5.0)) if sigma_o > 0 else 1.0
        ft = float(np.clip(rng.normal(1.0, sigma_t), 0.1, 10.0)) if sigma_t > 0 else 1.0

        try:
            pv = _variar_preco(projeto, fp)
            pv = _variar_obras(pv, fo)
            pv = _variar_terreno(pv, ft)
            res = calcular_fluxo_caixa(pv)
            tir = res.indicadores.get("tir_anual")
            if tir is not None:
                resultados.append(float(tir * 100))
        except Exception:
            pass

        prog.progress((i + 1) / n_sim)

    return resultados


def _mostrar_resultados_mc(tirs: list[float], tir_base: float | None) -> None:
    import plotly.graph_objects as go

    arr = np.array(tirs)
    p10 = float(np.percentile(arr, 10))
    p25 = float(np.percentile(arr, 25))
    p50 = float(np.percentile(arr, 50))
    p75 = float(np.percentile(arr, 75))
    p90 = float(np.percentile(arr, 90))
    media = float(np.mean(arr))
    std = float(np.std(arr))
    n_ok = sum(1 for t in tirs if t >= 0)

    # Cards de percentis
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("P10 (pessimista)", f"{p10:.1f}%")
    col2.metric("P25", f"{p25:.1f}%")
    col3.metric("P50 (mediana)", f"{p50:.1f}%", f"Media: {media:.1f}%")
    col4.metric("P75", f"{p75:.1f}%")
    col5.metric("P90 (otimista)", f"{p90:.1f}%")

    # Histograma
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=tirs, nbinsx=35,
        marker_color="#4A7FA5",
        marker_line_color="#F5F3EE",
        marker_line_width=1,
        opacity=0.85,
        name="TIR (%)",
        hovertemplate="TIR: %{x:.1f}%<br>Freq: %{y}<extra></extra>",
    ))

    for pct_v, nome_p, cor_p in [
        (p10, "P10", "#C05454"),
        (p50, "P50", "#2B50A8"),
        (p90, "P90", "#3D8B5E"),
    ]:
        fig.add_vline(x=pct_v, line_dash="dash", line_color=cor_p, line_width=1.5,
                      annotation_text=f"{nome_p}: {pct_v:.1f}%",
                      annotation_font_color=cor_p,
                      annotation_position="top right")

    if tir_base:
        fig.add_vline(x=tir_base * 100, line_dash="solid", line_color="#2B50A8", line_width=2,
                      annotation_text=f"Base: {tir_base * 100:.1f}%",
                      annotation_font_color="#2B50A8",
                      annotation_position="top left")

    fig.update_layout(
        title=f"Distribuicao de TIR — {len(tirs)} simulacoes validas de {st.session_state.get('_mc_resultados', {}).get('n_sim', '?')}  |  σ = {std:.1f}%",
        paper_bgcolor="#F5F3EE", plot_bgcolor="#ECEAE4",
        font=dict(color="#1A1916", size=12),
        xaxis=dict(title="TIR Anual (%)", gridcolor="#D8D4C8", ticksuffix="%"),
        yaxis=dict(title="Frequencia", gridcolor="#D8D4C8"),
        margin=dict(l=50, r=50, t=60, b=50),
        height=380,
        bargap=0.05,
        hoverlabel=dict(bgcolor="#ECEAE4", font_color="#1A1916"),
    )
    st.plotly_chart(fig, use_container_width=True, key="fig_mc_hist")

    # Analise de risco
    st.markdown("---")
    st.markdown("##### Analise de Risco: Probabilidade de Superar TIR Minima")
    col1, col2 = st.columns(2)
    with col1:
        tir_min = st.number_input(
            "TIR minima para analise (%)",
            min_value=0.0, max_value=100.0,
            value=15.0, step=1.0,
            key="mc_tir_min_risco",
        )
    with col2:
        prob = (arr >= tir_min).mean() * 100
        cor_prob = "#34D399" if prob >= 70 else "#FBBF24" if prob >= 40 else "#F87171"
        st.markdown(
            f'<div style="background:#131822;border-radius:8px;padding:16px;margin-top:4px;text-align:center;">'
            f'<div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">'
            f'Prob. de TIR ≥ {tir_min:.0f}%</div>'
            f'<div style="font-size:22px;font-weight:700;color:{cor_prob}">{prob:.0f}%</div>'
            f'<div style="font-size:10px;color:#9CA3AF;margin-top:2px;">'
            f'{int(prob * len(tirs) / 100)} de {len(tirs)} simulacoes</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
