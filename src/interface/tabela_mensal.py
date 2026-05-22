"""
Componente reusavel: tabela mensal de distribuicao percentual.

Renderiza uma tabela com uma linha por mes (M0, M1, M2, ...) onde o usuario
informa a % do valor total que cai naquele mes. Com marcos do projeto
destacados em cor diferente para facilitar a identificacao.

Layout: blocos de 20 meses lado a lado (5 colunas para 100 meses).

Uso tipico:
    distribuicao = tabela_mensal_distribuicao(
        nome_unico="despesa_marketing",
        horizonte_meses=60,
        valores_iniciais={9: 10.0, 10: 20.0, ...},
        marcos={9: "Lanc.", 18: "Ini.Obras", 36: "Fim Obras"},
    )
    # distribuicao = {9: 10.0, 10: 20.0, ...}
"""

from __future__ import annotations

import streamlit as st


def tabela_mensal_distribuicao(
    nome_unico: str,
    horizonte_meses: int,
    valores_iniciais: dict[int, float] | None = None,
    marcos: dict[int, str] | None = None,
    mostrar_resumo: bool = True,
    filtrar_meses_zerados: bool = False,
    margem_meses: int = 3,
) -> dict[int, float]:
    """
    Exibe grafico de barras Plotly da distribuicao mensal (somente leitura).

    Sempre visivel — mesmo sem dados mostra o horizonte completo do projeto
    com fases e marcos, servindo como linha do tempo de referencia para
    o usuario se orientar ao preencher os intervalos.

    A edicao e feita exclusivamente via atalhos_por_intervalos.
    Retorna valores_iniciais sem alteracao.
    """
    valores_iniciais = valores_iniciais or {}
    marcos = marcos or {}

    try:
        import plotly.graph_objects as go

        # Horizonte completo — nao zoom sobre os dados
        x_min = 0
        x_max = horizonte_meses - 1

        all_meses = list(range(x_min, x_max + 1))
        tem_dados = bool(valores_iniciais)
        valores = [valores_iniciais.get(m, 0.0) for m in all_meses]
        cores = ["#4A7FA5" if v > 0 else "rgba(0,0,0,0)" for v in valores]

        fig = go.Figure()

        # ----- Fases do projeto -----
        mes_lancamento = next((m for m, n in marcos.items() if "Lanc" in n), None)
        mes_inicio_obras = next(
            (m for m, n in marcos.items() if "Ini.Obras" in n or "Ini Obras" in n), None
        )
        mes_fim_obras = next((m for m, n in marcos.items() if "Fim Obras" in n), None)

        if mes_inicio_obras is not None and mes_fim_obras is not None:
            fig.add_vrect(
                x0=mes_inicio_obras - 0.5, x1=mes_fim_obras + 0.5,
                fillcolor="rgba(43,80,168,0.08)", line_width=0,
                annotation_text="Obras", annotation_position="top left",
                annotation_font_color="#2B50A8", annotation_font_size=9,
            )

        if mes_lancamento is not None and mes_fim_obras is not None:
            fig.add_vrect(
                x0=mes_lancamento - 0.5, x1=mes_fim_obras + 0.5,
                fillcolor="rgba(60,140,90,0.06)", line_width=0,
                annotation_text="Vendas", annotation_position="top right",
                annotation_font_color="#3D8B5E", annotation_font_size=9,
            )

        # ----- Linhas dos marcos -----
        for mes_marco, nome_marco in sorted(marcos.items()):
            fig.add_vline(
                x=mes_marco, line_dash="dash", line_color="#C4C1B8", line_width=1,
                annotation_text=nome_marco,
                annotation_position="top",
                annotation_font_color="#8A8880",
                annotation_font_size=8,
            )

        # ----- Barras de distribuicao -----
        if tem_dados:
            fig.add_trace(go.Bar(
                x=all_meses,
                y=valores,
                marker_color=cores,
                hovertemplate="M%{x}: %{y:.1f}%<extra></extra>",
            ))
        else:
            # Trace fantasma para manter eixos; anotacao orientativa
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip", showlegend=False,
            ))
            fig.add_annotation(
                x=(x_min + x_max) / 2,
                y=5,
                text="Use os intervalos acima para definir a distribuição",
                showarrow=False,
                font=dict(color="#8A8880", size=11),
                xanchor="center",
            )

        # ----- Layout -----
        # Densidade de ticks: ~12-15 ticks no eixo X independente do horizonte
        dtick = max(1, round(horizonte_meses / 12))

        y_max = max(15.0, max(valores) * 1.25) if tem_dados and max(valores) > 0 else 15.0

        fig.update_layout(
            height=210,
            margin=dict(l=35, r=10, t=35, b=30),
            paper_bgcolor="#F5F3EE",
            plot_bgcolor="#ECEAE4",
            font=dict(color="#5A5650", size=10),
            showlegend=False,
            bargap=0.05,
            xaxis=dict(
                title="Mês", gridcolor="#D8D4C8",
                range=[x_min - 0.5, x_max + 0.5],
                dtick=dtick,
                tickmode="linear",
                tick0=0,
                tickfont=dict(color="#5A5650"),
            ),
            yaxis=dict(
                title="%", gridcolor="#D8D4C8",
                range=[0, y_max],
                ticksuffix="%",
                tickfont=dict(color="#5A5650"),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"tabela_mensal_chart_{nome_unico}")

    except Exception:
        if valores_iniciais:
            soma_fb = sum(v for v in valores_iniciais.values() if v > 0)
            n_meses = sum(1 for v in valores_iniciais.values() if v > 0)
            st.caption(f"Distribuicao: {n_meses} meses preenchidos — Soma: {soma_fb:.1f}%")
        else:
            st.caption("📊 Use a ferramenta de intervalos acima para distribuir o desembolso por mes.")

    if mostrar_resumo:
        soma = sum(valores_iniciais.values())
        cols_resumo = st.columns([1, 3])
        with cols_resumo[0]:
            if abs(soma - 100.0) < 0.01:
                st.success(f"✅ Soma: {soma:.2f}%")
            elif soma == 0:
                st.info("Soma: 0,00%")
            else:
                st.warning(f"⚠️ Soma: {soma:.2f}% (deve ser 100%)")
        with cols_resumo[1]:
            st.progress(min(soma / 100, 1.0))

    return dict(valores_iniciais)


def distribuicao_lista_para_dict(
    distribuicao_pct: list[float],
    mes_inicio: int,
) -> dict[int, float]:
    """
    Converte uma lista [10, 20, 30] (a partir de mes_inicio) em {mes: %}.

    Util para migrar do formato antigo (modo='distribuicao_customizada') para o novo.
    """
    return {
        mes_inicio + i: pct
        for i, pct in enumerate(distribuicao_pct)
        if pct > 0
    }


def gerar_distribuicao_a_vista(mes: int) -> dict[int, float]:
    """Despesa a vista: 100% num mes so."""
    return {int(mes): 100.0}


def gerar_distribuicao_linear(mes_inicio: int, mes_fim: int) -> dict[int, float]:
    """Despesa parcelada linear: 1/N% por mes entre mes_inicio e mes_fim."""
    ini = int(mes_inicio)
    fim = int(mes_fim)
    qtd = fim - ini + 1
    if qtd <= 0:
        return {}
    pct = 100.0 / qtd
    return {ini + i: pct for i in range(qtd)}


def atalhos_por_intervalos(
    nome_unico: str,
    horizonte: int,
    chave_resultado: str,
    nomes_fluxos: list[str] | None = None,
) -> None:
    """
    UI de atalhos multi-intervalo com % customizavel por faixa.

    Cada linha: mes_inicio, mes_fim, % do total (+ Fluxo se nomes_fluxos fornecido).
    Ao clicar Aplicar, distribui cada % linearmente e escreve em
    st.session_state[chave_resultado]. Quem chamou deve checar essa chave
    no inicio do proximo render para aplicar ao estado local.
    """
    from .helpers import numero_brl  # importacao local — helpers nao importa tabela_mensal

    chave_lista = f"_ativ_{nome_unico}_lista"
    chave_ctr = f"_ativ_{nome_unico}_ctr"
    fluxo_default = nomes_fluxos[0] if nomes_fluxos else ""

    if chave_lista not in st.session_state:
        st.session_state[chave_ctr] = 1
        st.session_state[chave_lista] = [{
            "id": "i0",
            "mes_ini": 0,
            "mes_fim": min(11, max(0, horizonte - 1)),
            "pct": 100.0,
            "fluxo": fluxo_default,
        }]

    intervalos: list[dict] = st.session_state[chave_lista]
    indices_remover: list[int] = []

    for i, iv in enumerate(intervalos):
        uid = iv["id"]
        colunas = [2, 2, 2, 2, 1] if nomes_fluxos else [2, 2, 2, 1]
        cols = st.columns(colunas)
        with cols[0]:
            iv["mes_ini"] = int(numero_brl(
                "Mes inicio", value=float(iv["mes_ini"]),
                key=f"_ativ_{nome_unico}_{uid}_ini",
                min_value=0.0, max_value=float(max(0, horizonte - 1)), casas=0,
            ))
        with cols[1]:
            iv["mes_fim"] = int(numero_brl(
                "Mes fim", value=float(iv["mes_fim"]),
                key=f"_ativ_{nome_unico}_{uid}_fim",
                min_value=0.0, max_value=float(max(0, horizonte - 1)), casas=0,
            ))
        with cols[2]:
            iv["pct"] = numero_brl(
                "% do total", value=float(iv["pct"]),
                key=f"_ativ_{nome_unico}_{uid}_pct",
                min_value=0.0, max_value=100.0,
            )
        if nomes_fluxos:
            with cols[3]:
                idx_fl = (
                    nomes_fluxos.index(iv.get("fluxo", fluxo_default))
                    if iv.get("fluxo") in nomes_fluxos
                    else 0
                )
                iv["fluxo"] = st.selectbox(
                    "Fluxo", options=nomes_fluxos, index=idx_fl,
                    key=f"_ativ_{nome_unico}_{uid}_fluxo",
                )
        with cols[-1]:
            st.markdown("&nbsp;")
            if st.button(
                "🗑️", key=f"_ativ_{nome_unico}_{uid}_rm",
                use_container_width=True, help="Remover intervalo",
            ):
                indices_remover.append(i)

    if indices_remover:
        for i in sorted(indices_remover, reverse=True):
            intervalos.pop(i)
        st.rerun()

    soma = sum(float(iv["pct"]) for iv in intervalos)
    col_add, col_soma, col_aplic, col_clr = st.columns([1, 2, 1, 1])

    with col_add:
        if st.button("➕ Intervalo", key=f"_ativ_{nome_unico}_add", use_container_width=True):
            ctr = st.session_state.get(chave_ctr, len(intervalos))
            st.session_state[chave_ctr] = ctr + 1
            intervalos.append({
                "id": f"i{ctr}",
                "mes_ini": 0,
                "mes_fim": min(11, max(0, horizonte - 1)),
                "pct": 0.0,
                "fluxo": fluxo_default,
            })
            st.rerun()

    with col_soma:
        if abs(soma - 100.0) < 0.01:
            st.success(f"✅ Soma: {soma:.1f}%")
        elif soma == 0:
            st.info(f"Soma: {soma:.1f}%")
        else:
            st.warning(f"⚠️ Soma: {soma:.1f}% (deve ser 100%)")

    with col_aplic:
        if st.button(
            "▶️ Aplicar", key=f"_ativ_{nome_unico}_apply",
            use_container_width=True, type="primary",
        ):
            resultado: dict = {}
            for iv in intervalos:
                ini = int(iv["mes_ini"])
                fim = int(iv["mes_fim"])
                pct = float(iv["pct"])
                n = fim - ini + 1
                if n <= 0 or pct <= 0:
                    continue
                pct_por_mes = pct / n
                for j in range(n):
                    m = ini + j
                    if nomes_fluxos:
                        fluxo = iv.get("fluxo") or fluxo_default
                        resultado[m] = (pct_por_mes, fluxo)
                    else:
                        resultado[m] = pct_por_mes
            st.session_state[chave_resultado] = resultado
            st.rerun()

    with col_clr:
        if st.button("🧹 Limpar", key=f"_ativ_{nome_unico}_clr", use_container_width=True):
            st.session_state[chave_resultado] = {}
            st.rerun()


def atalhos_contextuais(categoria: str, marcos: dict[int, str], horizonte: int) -> dict[str, dict[int, float]]:
    """
    Devolve presets contextuais para uma categoria de despesa.

    Args:
        categoria: 'projetos' | 'licenciamento' | 'marketing' | 'outros'
        marcos: dict {mes: nome_marco} do projeto
        horizonte: horizonte total em meses

    Returns:
        dict {nome_atalho: distribuicao}, ex.:
        {"À vista no mês 0": {0: 100.0}, "Linear até a aprovação": {...}}
    """
    # Encontrar meses dos marcos
    mes_aprovacao = next((m for m, n in marcos.items() if "Aprov" in n), None)
    mes_lancamento = next((m for m, n in marcos.items() if "Lanc" in n), None)
    mes_inicio_obras = next((m for m, n in marcos.items() if "Ini.Obras" in n or "Ini Obras" in n), None)
    mes_fim_obras = next((m for m, n in marcos.items() if "Fim Obras" in n), None)

    presets: dict[str, dict[int, float]] = {}

    if categoria == "projetos":
        presets["À vista no início (M0)"] = gerar_distribuicao_a_vista(0)
        if mes_aprovacao:
            presets[f"Linear de M0 até aprovação (M{mes_aprovacao})"] = (
                gerar_distribuicao_linear(0, mes_aprovacao)
            )

    elif categoria == "licenciamento":
        if mes_aprovacao:
            presets[f"À vista na aprovação (M{mes_aprovacao})"] = (
                gerar_distribuicao_a_vista(mes_aprovacao)
            )
            presets[f"Linear de M0 a M{mes_aprovacao}"] = (
                gerar_distribuicao_linear(0, mes_aprovacao)
            )
        if mes_inicio_obras:
            presets[f"À vista no início das obras (M{mes_inicio_obras})"] = (
                gerar_distribuicao_a_vista(mes_inicio_obras)
            )

    elif categoria == "marketing":
        if mes_lancamento and mes_fim_obras:
            presets[f"Linear do lançamento (M{mes_lancamento}) ao fim das obras (M{mes_fim_obras})"] = (
                gerar_distribuicao_linear(mes_lancamento, mes_fim_obras)
            )
        if mes_lancamento:
            # Lançamento concentrado: 30% no lançamento, 70% diluído
            distrib_lanc = {mes_lancamento: 30.0}
            if mes_fim_obras and mes_fim_obras > mes_lancamento:
                qtd = mes_fim_obras - mes_lancamento
                pct_diluido = 70.0 / qtd
                for i in range(1, qtd + 1):
                    distrib_lanc[mes_lancamento + i] = pct_diluido
            presets[f"30% no lançamento + 70% diluído"] = distrib_lanc

    elif categoria == "outros":
        presets["À vista no início (M0)"] = gerar_distribuicao_a_vista(0)
        if mes_lancamento:
            presets[f"À vista no lançamento (M{mes_lancamento})"] = (
                gerar_distribuicao_a_vista(mes_lancamento)
            )

    return presets


