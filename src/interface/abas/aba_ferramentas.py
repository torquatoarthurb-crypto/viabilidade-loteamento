"""
Modulo 10 — Ferramentas Analiticas.

C1  — Analise de Sensibilidade (tornado chart) — impacto sobre Margem Liquida
C3  — Solver: Preco Minimo para Margem Liquida Alvo
C7  — Benchmarks de Mercado
C9  — Solver: Valor Maximo do Terreno para Margem Liquida Alvo
C10 — Simulador de Faseamento Simplificado
"""

from __future__ import annotations

import streamlit as st

from ...engine import calcular_fluxo_caixa
from ..helpers import (
    cabecalho_aba,
    formatar_brl,
    formatar_pct,
    get_projeto,
    get_resultado,
    renderizar_calcular_cta,
)


def renderizar() -> None:
    cabecalho_aba(
        10,
        "Ferramentas Analiticas",
        "Sensibilidade, solvers de Margem Liquida alvo, benchmarks de mercado e simulador de faseamento.",
    )
    tabs = st.tabs([
        "📊 Sensibilidade",
        "🎯 Preco Minimo",
        "🏗️ Terreno Maximo",
        "📋 Benchmarks",
        "🔀 Faseamento",
    ])
    with tabs[0]:
        _renderizar_sensibilidade()
    with tabs[1]:
        _renderizar_solver_preco()
    with tabs[2]:
        _renderizar_solver_terreno()
    with tabs[3]:
        _renderizar_benchmarks()
    with tabs[4]:
        _renderizar_faseamento()


# =====================================================================
# HELPERS DE VARIACAO DE PARAMETROS (tambem usados por aba_cenarios)
# =====================================================================

def _variar_preco(projeto, fator: float):
    """Multiplica o valor_unitario de todas as tipologias por fator."""
    novas_tips = [
        t.model_copy(update={"valor_unitario": max(t.valor_unitario * fator, 0.01)})
        for t in projeto.terreno.tipologias
    ]
    novo_terreno = projeto.terreno.model_copy(update={"tipologias": novas_tips})
    return projeto.model_copy(update={"terreno": novo_terreno})


def _variar_obras(projeto, fator: float):
    """Multiplica o custo de obras por fator."""
    obras = projeto.obras
    if obras.modo == "resumido" and obras.resumido:
        novo_res = obras.resumido.model_copy(
            update={"valor_por_m2": max(obras.resumido.valor_por_m2 * fator, 0.01)}
        )
        novas_obras = obras.model_copy(update={"resumido": novo_res})
    else:
        novas_etapas = [
            e.model_copy(update={"valor_total": max(e.valor_total * fator, 1.0)})
            for e in obras.etapas
        ]
        novas_obras = obras.model_copy(update={"etapas": novas_etapas})
    return projeto.model_copy(update={"obras": novas_obras})


def _variar_terreno(projeto, fator: float):
    """Multiplica o valor total do terreno por fator."""
    nova_acq = projeto.aquisicao.model_copy(
        update={"valor_total": max(projeto.aquisicao.valor_total * fator, 1.0)}
    )
    return projeto.model_copy(update={"aquisicao": nova_acq})


def _run_margem(projeto) -> float | None:
    """Retorna Margem Liquida (resultado / vgv_vendavel). None se falhar."""
    try:
        res = calcular_fluxo_caixa(projeto)
        return res.resumo.get("margem_sobre_vgv_vendavel")
    except Exception:
        return None


# =====================================================================
# C1 — ANALISE DE SENSIBILIDADE
# =====================================================================

def _renderizar_sensibilidade() -> None:
    st.markdown("#### Analise de Sensibilidade")
    st.caption(
        "Avalia o impacto de variacoes nos parametros principais sobre a Margem Liquida. "
        "O grafico Tornado mostra quais parametros tem maior influencia no resultado."
    )

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    margem_base = resultado.resumo.get("margem_sobre_vgv_vendavel")
    if margem_base is None:
        st.warning("Margem Liquida nao disponivel. Verifique se o projeto possui receitas e custos calculados.")
        return

    projeto = get_projeto()

    col1, col2 = st.columns(2)
    with col1:
        parametros_sel = st.multiselect(
            "Parametros a analisar",
            options=["Preco de venda", "Custo de obras", "Custo do terreno"],
            default=["Preco de venda", "Custo de obras", "Custo do terreno"],
            key="sens_params",
        )
    with col2:
        variacao_pct = st.slider(
            "Amplitude da variacao (%)",
            min_value=5, max_value=40, value=20, step=5,
            key="sens_amplitude",
            help="Varia cada parametro de -X% a +X% em relacao ao valor base.",
        )

    if st.button("▶ Calcular Sensibilidade", key="btn_sens_calc", type="primary"):
        if not parametros_sel:
            st.warning("Selecione ao menos um parametro.")
        else:
            _calcular_sensibilidade(projeto, margem_base, parametros_sel, variacao_pct)

    cache = st.session_state.get("_sens_cache")
    if cache and abs(cache.get("margem_base", -1) - margem_base) < 1e-6:
        _mostrar_tornado(cache["resultados"], margem_base)
    elif cache:
        st.info("O projeto foi recalculado. Clique em Calcular Sensibilidade para atualizar.")


def _calcular_sensibilidade(projeto, margem_base: float, params: list[str], amp: int) -> None:
    variadores = {
        "Preco de venda": _variar_preco,
        "Custo de obras": _variar_obras,
        "Custo do terreno": _variar_terreno,
    }
    pontos = [-amp, -(amp // 2), amp // 2, amp]
    resultados: dict[str, dict[int, float | None]] = {}

    with st.spinner("Calculando variacoes..."):
        for param in params:
            resultados[param] = {}
            fn = variadores[param]
            for v in pontos:
                fator = 1 + v / 100
                resultados[param][v] = _run_margem(fn(projeto, fator))

    st.session_state["_sens_cache"] = {"resultados": resultados, "margem_base": margem_base}


def _mostrar_tornado(resultados: dict, margem_base: float) -> None:
    import plotly.graph_objects as go

    dados: list[tuple[str, float, float]] = []
    for param, vars_dict in resultados.items():
        vals = [v for v in vars_dict.values() if v is not None]
        if vals:
            dados.append((param, min(vals), max(vals)))

    if not dados:
        st.warning("Nenhuma variacao retornou Margem Liquida calculavel.")
        return

    dados.sort(key=lambda x: x[2] - x[1], reverse=True)
    base_pct = margem_base * 100

    fig = go.Figure()
    for label, lo, hi in dados:
        lo_pct, hi_pct = lo * 100, hi * 100
        fig.add_trace(go.Bar(
            name=label,
            x=[hi_pct - lo_pct],
            y=[label],
            base=[lo_pct],
            orientation="h",
            marker_color="#4A7FA5",
            marker_opacity=0.85,
            showlegend=False,
            hovertemplate=(
                f"<b>{label}</b><br>"
                f"Minimo: {lo_pct:.1f}%<br>Maximo: {hi_pct:.1f}%<br>"
                f"Amplitude: {hi_pct - lo_pct:.1f} p.p.<extra></extra>"
            ),
        ))
        fig.add_annotation(x=lo_pct - 0.3, y=label, text=f"{lo_pct:.1f}%",
                           showarrow=False, xanchor="right",
                           font=dict(size=10, color="#C05454"))
        fig.add_annotation(x=hi_pct + 0.3, y=label, text=f"{hi_pct:.1f}%",
                           showarrow=False, xanchor="left",
                           font=dict(size=10, color="#3D8B5E"))

    fig.add_vline(x=base_pct, line_dash="dash", line_color="#2B50A8", line_width=2,
                  annotation_text=f"Base: {base_pct:.1f}%",
                  annotation_font_color="#2B50A8", annotation_position="top right")

    fig.update_layout(
        title="Tornado — Impacto sobre a Margem Líquida",
        paper_bgcolor="#F5F3EE", plot_bgcolor="#ECEAE4",
        font=dict(color="#1A1916", family="Inter, sans-serif", size=12),
        xaxis=dict(title="Margem Líquida (%)", gridcolor="#D8D4C8", ticksuffix="%"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=180, r=80, t=50, b=50),
        height=max(200, 80 + len(dados) * 75),
        hoverlabel=dict(bgcolor="#ECEAE4", font_size=12, font_color="#1A1916"),
    )
    st.plotly_chart(fig, use_container_width=True, key="fig_tornado")

    st.markdown("##### Tabela de Impacto")
    linhas = ""
    for param, lo, hi in dados:
        linhas += (
            f"<tr><td>{param}</td>"
            f"<td style='color:#C05454'>{lo*100:.1f}%</td>"
            f"<td style='color:#2B50A8'>{base_pct:.1f}%</td>"
            f"<td style='color:#3D8B5E'>{hi*100:.1f}%</td>"
            f"<td>{(hi - lo)*100:.1f} p.p.</td></tr>"
        )
    thead = (
        "<thead><tr>"
        "<th>Parametro</th><th>Minimo</th><th>Base</th><th>Maximo</th><th>Amplitude</th>"
        "</tr></thead>"
    )
    st.markdown(
        f'<table class="dre-table">{thead}<tbody>{linhas}</tbody></table>',
        unsafe_allow_html=True,
    )


# =====================================================================
# C3 — SOLVER: PRECO MINIMO PARA TIR ALVO
# =====================================================================

def _renderizar_solver_preco() -> None:
    st.markdown("#### Preco Minimo para Margem Liquida Alvo")
    st.caption(
        "Encontra o preco minimo de venda dos lotes para que o projeto atinja "
        "a Margem Liquida desejada (Resultado / VGV Vendavel). "
        "Util para definir o preco de lancamento."
    )

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    projeto = get_projeto()
    margem_base = resultado.resumo.get("margem_sobre_vgv_vendavel")
    margem_pct_base = (margem_base or 0.0) * 100

    col1, col2 = st.columns(2)
    with col1:
        margem_alvo_pct = st.number_input(
            "Margem Liquida alvo (%)",
            min_value=1.0, max_value=100.0,
            value=float(f"{max(margem_pct_base, 20.0):.1f}"),
            step=0.5,
            key="solver_preco_margem_alvo",
            help="Resultado Liquido / VGV Vendavel. Tipico de mercado: 22–30%.",
        )
    with col2:
        st.metric(
            "Margem atual do projeto",
            f"{margem_pct_base:.1f}%" if margem_base is not None else "—",
        )

    if not st.button("🔍 Calcular Preco Minimo", key="btn_solver_preco", type="primary"):
        st.info("Defina a Margem Liquida alvo e clique em Calcular.")
        return

    margem_alvo = margem_alvo_pct / 100
    with st.spinner("Buscando preco minimo..."):
        fator = _bisecao_preco(projeto, margem_alvo)

    if fator is None:
        st.error(
            "Nao foi possivel encontrar um preco para essa Margem. "
            "Verifique se a Margem alvo e tecnicamente atingivel (reduza custos ou aumente prazos)."
        )
        return

    st.success(f"✅ Preco minimo encontrado para Margem Liquida = {margem_alvo_pct:.1f}%")

    vgv_novo = sum(
        t.quantidade * (t.area_lote_m2 if t.modo_preco == "por_m2" else 1)
        * t.valor_unitario * fator
        for t in projeto.terreno.tipologias
    )
    vgv_atual = resultado.resumo.get("vgv_bruto", 0) or 1

    col1, col2, col3 = st.columns(3)
    col2.metric("VGV com preco minimo", formatar_brl(vgv_novo))
    col3.metric("Variacao vs VGV atual",
                f"{(vgv_novo / vgv_atual - 1) * 100:+.1f}%")

    linhas = ""
    for t in projeto.terreno.tipologias:
        novo_val = t.valor_unitario * fator
        unidade = "m²" if t.modo_preco == "por_m2" else "lote"
        linhas += (
            f"<tr><td>{t.nome}</td>"
            f"<td>{formatar_brl(t.valor_unitario)}/{unidade}</td>"
            f"<td style='color:#34D399'>{formatar_brl(novo_val)}/{unidade}</td>"
            f"<td>{(fator - 1) * 100:+.1f}%</td></tr>"
        )
    thead = (
        "<thead><tr><th>Tipologia</th><th>Preco Atual</th>"
        "<th>Preco Minimo</th><th>Variacao</th></tr></thead>"
    )
    st.markdown(
        f'<table class="dre-table">{thead}<tbody>{linhas}</tbody></table>',
        unsafe_allow_html=True,
    )


def _bisecao_preco(projeto, margem_alvo: float, lo: float = 0.05, hi: float = 15.0,
                   max_iter: int = 60) -> float | None:
    m_lo = _run_margem(_variar_preco(projeto, lo))
    m_hi = _run_margem(_variar_preco(projeto, hi))
    if m_lo is None or m_hi is None:
        return None
    if margem_alvo <= m_lo:
        return lo
    if margem_alvo > m_hi:
        return None

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        m_mid = _run_margem(_variar_preco(projeto, mid))
        if m_mid is None:
            return None
        if abs(m_mid - margem_alvo) < 0.0001:
            return mid
        if m_mid < margem_alvo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# =====================================================================
# C9 — SOLVER: VALOR MAXIMO DO TERRENO
# =====================================================================

def _renderizar_solver_terreno() -> None:
    st.markdown("#### Valor Maximo do Terreno para Margem Liquida Alvo")
    st.caption(
        "Calcula qual o valor maximo que pode ser pago pelo terreno (gleba) "
        "para que o projeto ainda atinja a Margem Liquida minima informada "
        "(Resultado Liquido / VGV Vendavel)."
    )

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    projeto = get_projeto()
    margem_base = resultado.resumo.get("margem_sobre_vgv_vendavel")
    margem_pct_base = (margem_base or 0.0) * 100
    valor_atual = projeto.aquisicao.valor_total
    areas = projeto.terreno.areas

    col1, col2 = st.columns(2)
    with col1:
        margem_alvo_pct = st.number_input(
            "Margem Liquida minima aceitavel (%)",
            min_value=1.0, max_value=100.0,
            value=float(f"{max(margem_pct_base, 20.0):.1f}"),
            step=0.5,
            key="solver_terreno_margem_alvo",
            help="Resultado Liquido / VGV Vendavel. Tipico de mercado: 22–30%.",
        )
    with col2:
        st.metric("Margem atual do projeto",
                  f"{margem_pct_base:.1f}%" if margem_base is not None else "—")

    if not st.button("🔍 Calcular Terreno Maximo", key="btn_solver_terreno", type="primary"):
        st.info("Defina a Margem Liquida minima e clique em Calcular.")
        return

    margem_alvo = margem_alvo_pct / 100
    with st.spinner("Buscando valor maximo do terreno..."):
        fator_max = _bisecao_terreno(projeto, margem_alvo)

    if fator_max is None:
        st.error(
            "Nao foi possivel encontrar o valor maximo. "
            "Verifique se a Margem alvo e atingivel (pode ser maior que a Margem atual)."
        )
        return

    valor_max = valor_atual * fator_max
    gleba = areas.area_gleba_m2 or 1.0
    lotes_m2 = areas.area_lotes_m2 or 1.0

    st.success(f"✅ Valor maximo do terreno para Margem Liquida ≥ {margem_alvo_pct:.1f}%")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valor Maximo Total", formatar_brl(valor_max),
              f"{(fator_max - 1) * 100:+.1f}% vs atual")
    c2.metric("R$ / m² de Gleba", formatar_brl(valor_max / gleba),
              f"Atual: {formatar_brl(valor_atual / gleba)}")
    c3.metric("R$ / Hectare", formatar_brl(valor_max / gleba * 10_000),
              help="1 hectare = 10.000 m²")
    c4.metric("R$ / m² de Lotes", formatar_brl(valor_max / lotes_m2),
              help="Custo do terreno rateado por m² de area de lotes")

    st.caption(
        f"Valor atual do terreno: {formatar_brl(valor_atual)} "
        f"({formatar_brl(valor_atual / gleba)}/m² de gleba)"
    )


def _bisecao_terreno(projeto, margem_alvo: float, lo: float = 0.01, hi: float = 30.0,
                     max_iter: int = 60) -> float | None:
    # terreno menor → margem maior; terreno maior → margem menor
    m_hi = _run_margem(_variar_terreno(projeto, lo))
    m_lo = _run_margem(_variar_terreno(projeto, hi))
    if m_hi is None or m_lo is None:
        return None
    if margem_alvo > m_hi:
        return None
    if margem_alvo <= m_lo:
        return hi

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        m_mid = _run_margem(_variar_terreno(projeto, mid))
        if m_mid is None:
            return None
        if abs(m_mid - margem_alvo) < 0.0001:
            return mid
        if m_mid > margem_alvo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# =====================================================================
# C7 — BENCHMARKS DE MERCADO
# =====================================================================

def _renderizar_benchmarks() -> None:
    st.markdown("#### Benchmarks de Mercado — Loteamentos Residenciais")
    st.caption(
        "Referencias tipicas para loteamentos no Brasil. "
        "Variam conforme regiao, porte e padrao do empreendimento."
    )

    benchmarks = [
        ("BDI sobre obras diretas", "10%", "15 – 20%", "25%",
         "Beneficios e Despesas Indiretas do empreiteiro"),
        ("Contingencia de obras", "3%", "5 – 8%", "12%",
         "Reserva para imprevistos sobre total com BDI"),
        ("Comissao de vendas", "3%", "5 – 6%", "8%",
         "Percentual sobre VGV pago ao corretor/imobiliaria"),
        ("Entrada do comprador (sinal)", "5%", "8 – 12%", "20%",
         "% do preco do lote pago no ato da venda"),
        ("Aproveitamento (lotes / gleba)", "45%", "55 – 62%", "70%",
         "% da area total da gleba que vira area de lotes"),
        ("Prazo de obras", "12 meses", "18 – 30 meses", "48 meses",
         "Do inicio ao termino das obras de infraestrutura"),
        ("Periodo de vendas", "12 meses", "24 – 36 meses", "60 meses",
         "Tempo aproximado para vender 100% do estoque"),
        ("Custo obras / m² de vias", "R$ 200", "R$ 300 – 500", "R$ 800",
         "Infraestrutura media: terraplenagem, drenagem, pavimento, redes"),
        ("Custo obras / m² de lotes", "R$ 150", "R$ 200 – 350", "R$ 600",
         "Custo de obras rateado por m² de area de lotes"),
        ("Custo terreno / m² de gleba", "R$ 8", "R$ 25 – 80", "R$ 300",
         "Varia muito: localizacao, municipio, topografia"),
        ("Custo terreno / % VGV", "5%", "10 – 20%", "35%",
         "Custo de aquisicao como percentual do VGV Bruto"),
        ("Margem liquida s/ VGV vendavel", "15%", "22 – 30%", "45%",
         "Lucro liquido / VGV vendavel"),
        ("TIR anual do projeto", "15% a.a.", "25 – 35% a.a.", "60% a.a.",
         "TIR tipica de projetos de loteamento no Brasil"),
        ("TMA / custo de oportunidade", "10% a.a.", "12 – 15% a.a.", "18% a.a.",
         "Selic / CDI + premio de risco do incorporador"),
        ("Impostos — aliquota efetiva", "4%", "6 – 8%", "10%",
         "Lucro presumido: aliquota sobre receita bruta"),
    ]

    linhas = ""
    for param, minimo, tipico, maximo, obs in benchmarks:
        linhas += (
            f"<tr>"
            f"<td><b>{param}</b></td>"
            f"<td style='color:#F87171'>{minimo}</td>"
            f"<td style='color:#34D399'>{tipico}</td>"
            f"<td style='color:#FBBF24'>{maximo}</td>"
            f"<td style='color:#9CA3AF;font-size:11px'>{obs}</td>"
            f"</tr>"
        )
    thead = (
        "<thead><tr>"
        "<th>Parametro</th>"
        "<th style='color:#F87171'>Minimo</th>"
        "<th style='color:#34D399'>Tipico</th>"
        "<th style='color:#FBBF24'>Maximo</th>"
        "<th>Observacao</th>"
        "</tr></thead>"
    )
    st.markdown(
        f'<table class="dre-table">{thead}<tbody>{linhas}</tbody></table>',
        unsafe_allow_html=True,
    )

    resultado = get_resultado()
    if resultado:
        st.markdown("---")
        st.markdown("##### Posicao do Seu Projeto nos Benchmarks")
        _mostrar_posicao_benchmarks(get_projeto(), resultado)


def _mostrar_posicao_benchmarks(projeto, resultado) -> None:
    r = resultado.resumo
    ind = resultado.indicadores

    vgv = r.get("vgv_bruto", 0) or 1
    bdi = projeto.obras.bdi_percentual
    cont = projeto.obras.contingencia_percentual
    comissao = projeto.impostos.comissao.percentual_vgv
    aproveitamento = projeto.terreno.areas.aproveitamento * 100
    margem = (r.get("margem_sobre_vgv_vendavel") or 0) * 100
    tir = (ind.get("tir_anual") or 0) * 100
    terreno_pct = r.get("custo_terreno", 0) / vgv * 100

    def cor_faixa(val: float, lo_ok: float, hi_ok: float) -> str:
        return "#34D399" if lo_ok <= val <= hi_ok else "#FBBF24"

    dados = [
        ("BDI", f"{bdi:.1f}%", cor_faixa(bdi, 15, 20)),
        ("Contingencia", f"{cont:.1f}%", cor_faixa(cont, 5, 8)),
        ("Aproveitamento", f"{aproveitamento:.1f}%", cor_faixa(aproveitamento, 55, 62)),
        ("Margem Liq.", f"{margem:.1f}%", cor_faixa(margem, 22, 30)),
        ("TIR Anual", f"{tir:.1f}%", cor_faixa(tir, 25, 35)),
        ("Terreno / VGV", f"{terreno_pct:.1f}%", cor_faixa(terreno_pct, 10, 20)),
        ("Comissao", f"{comissao:.1f}%", cor_faixa(comissao, 5, 6)),
    ]

    cols = st.columns(len(dados))
    for col, (nome, valor, cor) in zip(cols, dados):
        col.markdown(
            f'<div style="background:#131822;border-radius:8px;padding:10px 6px;text-align:center;">'
            f'<div style="font-size:9px;color:#9CA3AF;margin-bottom:3px;">{nome}</div>'
            f'<div style="font-size:15px;font-weight:700;color:{cor}">{valor}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.caption("Verde = dentro do tipico de mercado | Amarelo = fora do tipico (pode ser ok para o seu contexto)")


# =====================================================================
# C10 — SIMULADOR DE FASEAMENTO
# =====================================================================

def _renderizar_faseamento() -> None:
    st.markdown("#### Simulador de Faseamento")
    st.caption(
        "Simula a divisao do empreendimento em 2 fases com lançamentos em momentos diferentes. "
        "Cada fase usa custos proporcionais e a mesma estrutura de fluxo de recebiveis."
    )

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    projeto = get_projeto()
    total_lotes = projeto.terreno.total_lotes

    col1, col2 = st.columns(2)
    with col1:
        pct_fase1 = st.slider(
            "% de lotes na Fase 1",
            min_value=20, max_value=80, value=50, step=5,
            key="fase_pct1",
            help="Fase 2 tera os lotes restantes.",
        )
    with col2:
        delay_fase2 = st.slider(
            "Intervalo ate o lancamento da Fase 2 (meses)",
            min_value=3, max_value=36, value=12, step=3,
            key="fase_delay2",
            help="Quantos meses depois do lancamento da Fase 1.",
        )

    lotes_f1 = sum(max(1, round(t.quantidade * pct_fase1 / 100)) for t in projeto.terreno.tipologias)
    lotes_f2 = total_lotes - lotes_f1
    st.info(
        f"Fase 1: ~{lotes_f1} lotes ({pct_fase1}%)  |  "
        f"Fase 2: ~{max(lotes_f2, 0)} lotes ({100 - pct_fase1}%) — lancamento {delay_fase2} meses depois"
    )

    if not st.button("▶ Simular Faseamento", key="btn_simular_fase", type="primary"):
        return

    frac1 = pct_fase1 / 100
    frac2 = 1.0 - frac1

    with st.spinner("Simulando fases..."):
        try:
            proj_f1 = _criar_fase(projeto, frac1, delay_months=0)
            res_f1 = calcular_fluxo_caixa(proj_f1)
            proj_f2 = _criar_fase(projeto, frac2, delay_months=delay_fase2)
            res_f2 = calcular_fluxo_caixa(proj_f2)
        except Exception as e:
            st.error(f"Erro na simulacao de faseamento: {e}")
            return

    _mostrar_comparativo_fases(resultado, res_f1, res_f2, pct_fase1, delay_fase2)


def _mostrar_comparativo_fases(res_base, res_f1, res_f2, pct1: int, delay: int) -> None:
    def fmt_tir(r) -> str:
        tir = r.indicadores.get("tir_anual")
        return f"{tir * 100:.1f}% a.a." if tir else "—"

    def fmt_brl_r(r, key: str) -> str:
        return formatar_brl(r.resumo.get(key, 0))

    def fmt_ind(r, key: str) -> str:
        v = r.indicadores.get(key)
        return formatar_brl(v) if v is not None else "—"

    def fmt_pb(r) -> str:
        pb = r.indicadores.get("payback_simples_meses")
        return f"{pb} meses" if pb else "—"

    linhas = [
        ("VGV Bruto",       fmt_brl_r(res_base, "vgv_bruto"),
                            fmt_brl_r(res_f1, "vgv_bruto"),
                            fmt_brl_r(res_f2, "vgv_bruto")),
        ("Lucro Liquido",   fmt_brl_r(res_base, "lucro_liquido"),
                            fmt_brl_r(res_f1, "lucro_liquido"),
                            fmt_brl_r(res_f2, "lucro_liquido")),
        ("TIR Anual",       fmt_tir(res_base), fmt_tir(res_f1), fmt_tir(res_f2)),
        ("VPL",             fmt_ind(res_base, "vpl"),
                            fmt_ind(res_f1, "vpl"),
                            fmt_ind(res_f2, "vpl")),
        ("Exposicao Maxima", fmt_ind(res_base, "exposicao_maxima"),
                             fmt_ind(res_f1, "exposicao_maxima"),
                             fmt_ind(res_f2, "exposicao_maxima")),
        ("Payback Simples", fmt_pb(res_base), fmt_pb(res_f1), fmt_pb(res_f2)),
    ]

    thead = (
        f"<thead><tr>"
        f"<th>Indicador</th>"
        f"<th>Projeto Inteiro</th>"
        f"<th>Fase 1 ({pct1}% dos lotes)</th>"
        f"<th>Fase 2 ({100 - pct1}% dos lotes, +{delay}m)</th>"
        f"</tr></thead>"
    )
    tbody = "".join(
        f"<tr><td><b>{l[0]}</b></td><td>{l[1]}</td><td>{l[2]}</td><td>{l[3]}</td></tr>"
        for l in linhas
    )
    st.markdown(
        f'<table class="dre-table">{thead}<tbody>{tbody}</tbody></table>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Simulacao simplificada: fases usam custos proporcionais e a mesma "
        "curva de vendas / fluxos de recebiveis do projeto original."
    )


def _criar_fase(projeto, frac: float, delay_months: int = 0):
    """Cria sub-projeto representando uma fase com frac dos lotes."""
    import calendar as cal
    from datetime import date
    from ...modelos.obras import Aba3Obras, EtapaObra
    from ...engine.utilidades import meses_entre

    def add_months(d: date, m: int) -> date:
        month = d.month - 1 + m
        year = d.year + month // 12
        month = month % 12 + 1
        day = min(d.day, cal.monthrange(year, month)[1])
        return date(year, month, day)

    datas = projeto.terreno.datas

    novas_tips = [
        t.model_copy(update={"quantidade": max(1, round(t.quantidade * frac))})
        for t in projeto.terreno.tipologias
    ]
    novas_datas = datas.model_copy(update={
        "inicio_projeto": add_months(datas.inicio_projeto, delay_months),
        "aprovacao": add_months(datas.aprovacao, delay_months),
        "lancamento_vendas": add_months(datas.lancamento_vendas, delay_months),
        "inicio_obras": add_months(datas.inicio_obras, delay_months),
        "termino_obras": add_months(datas.termino_obras, delay_months),
    })
    novo_terreno = projeto.terreno.model_copy(update={
        "tipologias": novas_tips,
        "datas": novas_datas,
    })

    nova_acq = projeto.aquisicao.model_copy(update={
        "valor_total": max(projeto.aquisicao.valor_total * frac, 1.0),
        "custo_cartorio": projeto.aquisicao.custo_cartorio * frac,
    })

    obras = projeto.obras
    areas = projeto.terreno.areas
    if obras.modo == "resumido" and obras.resumido:
        base_m2 = (
            areas.area_sistema_viario_m2
            if obras.resumido.base_calculo == "sistema_viario"
            else areas.area_lotes_m2
        )
        custo_bruto = base_m2 * obras.resumido.valor_por_m2
        m_ini = obras.resumido.mes_inicio
        dur = obras.resumido.duracao_meses
    else:
        custo_bruto = sum(e.valor_total for e in obras.etapas) if obras.etapas else 0.0
        m_ini = meses_entre(datas.inicio_projeto, datas.inicio_obras)
        dur = max(1, meses_entre(datas.inicio_projeto, datas.termino_obras) - m_ini)

    novas_obras = Aba3Obras(
        modo="detalhado",
        etapas=[EtapaObra(
            nome="Obras (fase)",
            valor_total=max(custo_bruto * frac, 1.0),
            mes_inicio=m_ini,
            duracao_meses=dur,
            curva="s_curve",
        )],
        bdi_percentual=obras.bdi_percentual,
        contingencia_percentual=obras.contingencia_percentual,
    )

    novas_despesas = [
        d.model_copy(update={"valor_total": max(d.valor_total * frac, 0.01)})
        for d in projeto.desenvolvimento.despesas
    ]
    novo_desenv = projeto.desenvolvimento.model_copy(update={"despesas": novas_despesas})

    return projeto.model_copy(update={
        "terreno": novo_terreno,
        "aquisicao": nova_acq,
        "obras": novas_obras,
        "desenvolvimento": novo_desenv,
    })
