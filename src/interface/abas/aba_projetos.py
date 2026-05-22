"""
Modulo 12 — Gestao de Projetos.

C8 — Biblioteca de projetos: salvar, carregar e comparar multiplos projetos
     dentro da mesma sessao.
"""

from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from ...modelos import Projeto
from ..helpers import (
    cabecalho_aba,
    formatar_brl,
    get_projeto,
    get_resultado,
    invalidar_resultado,
    limpar_cache_inputs_brl,
    set_projeto,
)

CHAVE_BIBLIOTECA = "_biblioteca_projetos"
_CHAVES_ABA_CACHE = [
    "aba2_lista_fluxos", "aba2_curva_mensal", "aba3_lista_etapas",
    "aba3_resumido_distrib", "aba4_lista_despesas", "aba_terreno_fluxo_distrib",
]


def renderizar() -> None:
    cabecalho_aba(
        12,
        "Gestao de Projetos",
        "Salve, carregue e compare multiplos projetos dentro da mesma sessao.",
    )
    _renderizar_gestao()


def _renderizar_gestao() -> None:
    projeto = get_projeto()
    resultado = get_resultado()
    biblioteca = st.session_state.get(CHAVE_BIBLIOTECA, [])

    # ---- Salvar projeto atual na biblioteca ----
    st.markdown("#### Projeto Atual")

    info = projeto.terreno.info
    vgv = projeto.terreno.vgv_bruto
    tir_atual_str = "—"
    if resultado:
        tir = resultado.indicadores.get("tir_anual")
        if tir:
            tir_atual_str = f"{tir * 100:.1f}% a.a."

    col_info, col_salvar = st.columns([4, 1])
    with col_info:
        st.markdown(
            f'<div style="background:#131822;border-radius:8px;padding:12px 16px;">'
            f'<div style="font-size:15px;font-weight:700;color:#E8EAED">{info.nome}</div>'
            f'<div style="font-size:12px;color:#9CA3AF;margin-top:2px;">'
            f'{info.cidade}/{info.uf}  |  '
            f'VGV: {formatar_brl(vgv)}  |  '
            f'TIR: {tir_atual_str}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with col_salvar:
        st.write("")
        nome_lib = st.text_input(
            "Nome na biblioteca",
            value=info.nome,
            key="lib_nome_input",
            label_visibility="collapsed",
        )

    col_btn1, col_btn2 = st.columns([2, 3])
    with col_btn1:
        if st.button("💾 Salvar na Biblioteca", key="btn_lib_salvar", use_container_width=True):
            _salvar_na_biblioteca(nome_lib.strip() or info.nome, projeto, resultado)
            st.success(f"✅ '{nome_lib or info.nome}' adicionado a biblioteca.")
            st.rerun()

    st.markdown("---")

    # ---- Biblioteca ----
    if not biblioteca:
        st.info(
            "A biblioteca esta vazia. "
            "Salve o projeto atual para iniciar a biblioteca. "
            "Voce pode criar versoes com premissas diferentes (base, otimista, pessimista) "
            "e compara-las aqui."
        )
        return

    st.markdown(f"#### Biblioteca — {len(biblioteca)} Projeto(s)")
    _mostrar_tabela_biblioteca(biblioteca)

    st.markdown("---")
    st.markdown("**Acoes:**")
    for i, p in enumerate(biblioteca):
        tir_str = f"TIR: {p['tir'] * 100:.1f}%" if p.get("tir") else "sem resultado"
        col_i, col_l, col_d = st.columns([5, 1, 1])
        with col_i:
            st.markdown(
                f'<b style="color:#E8EAED">{p["nome"]}</b>'
                f' <span style="color:#9CA3AF;font-size:11px">'
                f'— {p["cidade"]}/{p["uf"]} — {p["data_salvo"]} — {tir_str}'
                f'</span>',
                unsafe_allow_html=True,
            )
        with col_l:
            if st.button(
                "📂", key=f"btn_lib_load_{i}",
                help="Carregar este projeto como projeto ativo",
                use_container_width=True,
            ):
                _carregar_da_biblioteca(i)
        with col_d:
            if st.button(
                "🗑️", key=f"btn_lib_del_{i}",
                help="Remover da biblioteca",
                use_container_width=True,
            ):
                biblioteca.pop(i)
                st.session_state[CHAVE_BIBLIOTECA] = biblioteca
                st.rerun()

    if len(biblioteca) >= 2 and any(p.get("tir") for p in biblioteca):
        st.markdown("---")
        st.markdown("#### Grafico Comparativo — TIR por Projeto")
        _renderizar_grafico_comparativo(biblioteca)

    if len(biblioteca) >= 2:
        _renderizar_consolidado_portfolio(biblioteca)


def _salvar_na_biblioteca(nome: str, projeto, resultado) -> None:
    if CHAVE_BIBLIOTECA not in st.session_state:
        st.session_state[CHAVE_BIBLIOTECA] = []

    entry: dict = {
        "nome": nome,
        "cidade": projeto.terreno.info.cidade,
        "uf": projeto.terreno.info.uf,
        "data_salvo": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "projeto_json": projeto.model_dump_json(),
        "tir": None,
        "vpl": None,
        "lucro": None,
        "vgv": projeto.terreno.vgv_bruto,
        "margem": None,
        "exposicao": None,
    }

    if resultado:
        ind = resultado.indicadores
        r = resultado.resumo
        entry.update({
            "tir": ind.get("tir_anual"),
            "vpl": ind.get("vpl"),
            "lucro": r.get("lucro_liquido"),
            "vgv": r.get("vgv_bruto"),
            "margem": r.get("margem_sobre_vgv_vendavel"),
            "exposicao": ind.get("exposicao_maxima"),
        })

    st.session_state[CHAVE_BIBLIOTECA].append(entry)

    if len(st.session_state[CHAVE_BIBLIOTECA]) > 20:
        st.session_state[CHAVE_BIBLIOTECA] = st.session_state[CHAVE_BIBLIOTECA][-20:]


def _carregar_da_biblioteca(idx: int) -> None:
    biblioteca = st.session_state.get(CHAVE_BIBLIOTECA, [])
    if idx >= len(biblioteca):
        return
    try:
        entry = biblioteca[idx]
        novo_projeto = Projeto.model_validate(json.loads(entry["projeto_json"]))
        set_projeto(novo_projeto)
        invalidar_resultado()
        limpar_cache_inputs_brl()
        for chave in _CHAVES_ABA_CACHE:
            if chave in st.session_state:
                del st.session_state[chave]
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar projeto: {e}")


def _mostrar_tabela_biblioteca(biblioteca: list) -> None:
    def ft(v: float | None) -> str:
        return f"{v * 100:.1f}%" if v else "—"

    def fm(v: float | None) -> str:
        if v is None:
            return "—"
        if abs(v) >= 1_000_000:
            return f"R$ {v / 1_000_000:.1f}M"
        return f"R$ {v / 1_000:.0f}K"

    thead = (
        "<thead><tr>"
        "<th>Nome</th><th>Local</th><th>Salvo</th>"
        "<th>VGV</th><th>Lucro</th><th>Margem</th><th>TIR</th><th>VPL</th>"
        "</tr></thead>"
    )
    linhas = ""
    for p in biblioteca:
        linhas += (
            f"<tr>"
            f"<td><b>{p['nome']}</b></td>"
            f"<td>{p['cidade']}/{p['uf']}</td>"
            f"<td style='font-size:11px;color:#9CA3AF'>{p['data_salvo']}</td>"
            f"<td>{fm(p.get('vgv'))}</td>"
            f"<td>{fm(p.get('lucro'))}</td>"
            f"<td>{ft(p.get('margem'))}</td>"
            f"<td style='color:#34D399'>{ft(p.get('tir'))}</td>"
            f"<td>{fm(p.get('vpl'))}</td>"
            f"</tr>"
        )
    st.markdown(
        f'<table class="dre-table"><thead>{thead}</thead><tbody>{linhas}</tbody></table>',
        unsafe_allow_html=True,
    )


def _renderizar_consolidado_portfolio(biblioteca: list) -> None:
    """Item 12: consolidado agregado de todos os projetos da biblioteca."""
    def _fm(v: float | None) -> str:
        if v is None:
            return "—"
        if abs(v) >= 1_000_000:
            return f"R$ {v / 1_000_000:.1f}M"
        return f"R$ {v / 1_000:.0f}K"

    com_resultado = [p for p in biblioteca if p.get("tir") is not None]

    total_vgv = sum(p.get("vgv") or 0 for p in biblioteca)
    total_lucro = sum(p.get("lucro") or 0 for p in com_resultado)
    total_exp = sum(abs(p.get("exposicao") or 0) for p in com_resultado)

    tir_media = None
    soma_pond = sum((p.get("vgv") or 0) * (p.get("tir") or 0) for p in com_resultado)
    soma_vgv_pond = sum(p.get("vgv") or 0 for p in com_resultado)
    if soma_vgv_pond > 0:
        tir_media = soma_pond / soma_vgv_pond

    with st.container(border=True):
        st.markdown("#### 🗂️ Consolidado do Portfólio")
        st.caption(
            f"{len(biblioteca)} projeto(s) na biblioteca — "
            f"{len(com_resultado)} calculado(s). TIR média ponderada pelo VGV."
        )
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("VGV Total", _fm(total_vgv))
        with c2:
            st.metric("Lucro Total", _fm(total_lucro))
        with c3:
            st.metric(
                "TIR Média (pond.)",
                f"{tir_media * 100:.1f}% a.a." if tir_media is not None else "—",
            )
        with c4:
            st.metric("Exposição Total", _fm(-total_exp) if total_exp > 0 else "—")

        if total_vgv > 0 and total_lucro:
            margem_port = total_lucro / total_vgv
            cor = "✅" if margem_port > 0.15 else "⚠️" if margem_port > 0 else "❌"
            st.caption(
                f"{cor} Margem consolidada sobre VGV: **{margem_port * 100:.1f}%**"
            )


def _renderizar_grafico_comparativo(biblioteca: list) -> None:
    import plotly.graph_objects as go

    com_tir = [(p["nome"], p["tir"] * 100) for p in biblioteca if p.get("tir")]
    if not com_tir:
        return

    nomes, tirs = zip(*com_tir)
    fig = go.Figure(go.Bar(
        x=list(nomes),
        y=list(tirs),
        marker_color=["#3D8B5E" if t > 0 else "#C05454" for t in tirs],
        text=[f"{t:.1f}%" for t in tirs],
        textposition="outside",
        textfont=dict(color="#1A1916"),
    ))
    fig.update_layout(
        paper_bgcolor="#F5F3EE", plot_bgcolor="#ECEAE4",
        font=dict(color="#1A1916", size=12),
        xaxis=dict(gridcolor="#D8D4C8"),
        yaxis=dict(gridcolor="#D8D4C8", ticksuffix="%"),
        margin=dict(l=40, r=40, t=20, b=40),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True, key="fig_biblioteca_tir")
