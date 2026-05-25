"""
Helpers compartilhados das abas da interface.

Funcoes utilitarias que varias abas usam:
- formatar_brl: formatar valor em R$ (1.234,56)
- formatar_pct: formatar percentual (12,34 %)
- get_projeto / set_projeto: acessar o projeto no session_state do Streamlit
- mostrar_erro_validacao: traduzir erros do Pydantic para o usuario
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from ..modelos import Projeto, projeto_novo


# =====================================================================
# INPUT NUMERICO COM MILHAR BR
# =====================================================================

_NBRL_VERSION_KEY = "_nbrl_proj_version"


def limpar_cache_inputs_brl() -> None:
    """Incrementa versao para forcar reformatacao de todos os inputs ao trocar projeto."""
    st.session_state[_NBRL_VERSION_KEY] = st.session_state.get(_NBRL_VERSION_KEY, 0) + 1


def _formatar_milhar(value: float, casas: int = 2) -> str:
    """Formata numero com separador de milhar BR: 1.234.567,89"""
    if casas == 0:
        return f"{int(round(value)):,}".replace(",", ".")
    fmt = f"{value:,.{casas}f}"
    return fmt.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _parsear_brl(texto: str, fallback: float) -> float:
    """Parseia string em formato BR ou numerico puro para float."""
    s = texto.strip().replace("R$", "").replace("%", "").replace("m²", "").strip().replace(" ", "")
    if not s:
        return fallback
    n_p = s.count(".")
    n_v = s.count(",")
    try:
        if n_v >= 1 and n_p >= 1:
            s = s.replace(".", "").replace(",", ".")
        elif n_v == 1 and n_p == 0:
            s = s.replace(",", ".")
        elif n_v > 1 and n_p == 0:
            s = s.replace(",", "")
        elif n_v == 0 and n_p > 1:
            s = s.replace(".", "")
        return float(s)
    except ValueError:
        return fallback


def numero_brl(
    label: str,
    value: float,
    key: str,
    min_value: float | None = None,
    max_value: float | None = None,
    step: float | None = None,
    help: str | None = None,
    casas: int = 2,
    disabled: bool = False,
) -> float:
    """
    Input numerico com separador de milhar BR (1.234.567,89).

    Reformata na inicializacao e ao trocar de projeto (via limpar_cache_inputs_brl).
    Aceita entrada com ou sem formatacao: '1500000', '1.500.000' ou '1.500.000,00'.
    O parametro step e aceito por compatibilidade mas ignorado (usa text_input).
    """
    display_key = f"_nbrl_{key}"
    prev_model_key = f"_nbrlm_{key}"
    version_key = f"_nbrlv_{key}"

    current_version = st.session_state.get(_NBRL_VERSION_KEY, 0)
    last_version = st.session_state.get(version_key, -1)
    last_model = st.session_state.get(prev_model_key)

    if (
        last_version != current_version
        or display_key not in st.session_state
        or (last_model is not None and last_model != value)
    ):
        st.session_state[display_key] = _formatar_milhar(value, casas)
        st.session_state[version_key] = current_version

    st.session_state[prev_model_key] = value

    extra: dict = {}
    if help is not None:
        extra["help"] = help

    texto = st.text_input(label=label, key=display_key, disabled=disabled, **extra)

    if not texto or not texto.strip():
        st.session_state[display_key] = _formatar_milhar(value, casas)
        return value

    resultado = _parsear_brl(texto, value)

    if min_value is not None:
        resultado = max(resultado, min_value)
    if max_value is not None:
        resultado = min(resultado, max_value)
    if casas == 0:
        resultado = float(int(round(resultado)))

    return resultado


# =====================================================================
# FORMATACAO
# =====================================================================

def formatar_brl(valor: float | int | None) -> str:
    """Formata um valor como R$ no padrao brasileiro (1.234,56)."""
    if valor is None:
        return "—"
    if valor < 0:
        return f"-R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_pct(valor: float | None, casas: int = 2) -> str:
    """Formata um decimal como percentual (0.1234 -> 12,34 %)."""
    if valor is None:
        return "—"
    txt = f"{valor * 100:.{casas}f}".replace(".", ",")
    return f"{txt} %"


def formatar_int(valor: int | float | None) -> str:
    """Formata um inteiro com separador de milhar."""
    if valor is None:
        return "—"
    return f"{int(valor):,}".replace(",", ".")


def formatar_num(valor: float | None, casas: int = 2) -> str:
    """Formata um numero com separador brasileiro."""
    if valor is None:
        return "—"
    txt = f"{valor:,.{casas}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


# =====================================================================
# ACESSO AO PROJETO NO SESSION_STATE
# =====================================================================

CHAVE_PROJETO = "projeto_atual"
CHAVE_RESULTADO = "resultado_calculo"
CHAVE_NOME_ARQUIVO = "nome_arquivo_atual"


def garantir_projeto_inicial() -> None:
    """Garante que ha um projeto na sessao. Se nao houver, cria um novo."""
    if CHAVE_PROJETO not in st.session_state:
        st.session_state[CHAVE_PROJETO] = projeto_novo()
    if CHAVE_RESULTADO not in st.session_state:
        st.session_state[CHAVE_RESULTADO] = None
    if CHAVE_NOME_ARQUIVO not in st.session_state:
        st.session_state[CHAVE_NOME_ARQUIVO] = None


def get_projeto() -> Projeto:
    """Devolve o projeto atual da sessao."""
    garantir_projeto_inicial()
    return st.session_state[CHAVE_PROJETO]


def set_projeto(projeto: Projeto) -> None:
    """Substitui o projeto atual e invalida o resultado calculado."""
    st.session_state[CHAVE_PROJETO] = projeto
    st.session_state[CHAVE_RESULTADO] = None  # forca recalculo


def invalidar_resultado() -> None:
    """Marca o resultado calculado como obsoleto (sera recalculado no proximo acesso)."""
    st.session_state[CHAVE_RESULTADO] = None


def get_resultado() -> Any:
    """Devolve o resultado de calculo, ou None se ainda nao calculado."""
    return st.session_state.get(CHAVE_RESULTADO)


def set_resultado(resultado: Any) -> None:
    """Guarda o resultado calculado."""
    st.session_state[CHAVE_RESULTADO] = resultado


# =====================================================================
# UI HELPERS
# =====================================================================

def cabecalho_aba(numero: int, titulo: str, descricao: str = "") -> None:
    """Cabecalho padrao no topo de cada aba."""
    st.markdown(f"### Aba {numero} — {titulo}")
    if descricao:
        st.caption(descricao)
    st.markdown("---")


def aviso_validacao(mensagem: str) -> None:
    """Mostra aviso de erro de validacao."""
    st.error(f"⚠️ {mensagem}")


def sucesso(mensagem: str) -> None:
    """Mostra mensagem de sucesso."""
    st.success(f"✅ {mensagem}")


def info(mensagem: str) -> None:
    """Mostra info."""
    st.info(mensagem)


def renderizar_calcular_cta() -> bool:
    """
    Renderiza um card + botao 'Calcular' quando nenhum resultado existe.
    Retorna True se o resultado ainda e None apos renderizar (o caller deve `return`).
    Retorna False se o calculo foi executado com sucesso (o caller pode continuar).
    """
    from ..engine import calcular_fluxo_caixa

    st.markdown(
        """
        <div class="card" style="text-align:center; padding:40px 20px;">
            <div style="font-size:42px; margin-bottom:12px;">⚡</div>
            <div style="font-size:16px; font-weight:600; color:var(--text-primary);
                        margin-bottom:8px;">
                Nenhum resultado calculado ainda
            </div>
            <div style="color:var(--text-secondary); font-size:13px; margin-bottom:20px;">
                Preencha os dados nas abas 1 a 5 e clique em Calcular.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🧮 Calcular", type="primary", use_container_width=True,
                     key="cta_calcular"):
            try:
                resultado = calcular_fluxo_caixa(get_projeto())
                set_resultado(resultado)
                st.rerun()
            except Exception as e:
                st.error(f"Erro no calculo: {e}")
    return True


# =====================================================================
# LINHA DO TEMPO DO PROJETO
# =====================================================================

def marcos_projeto(projeto) -> dict[int, str]:
    """
    Devolve um dict {mes: nome_curto_marco} com os marcos do projeto.

    Util para destacar meses-marco em tabelas de input mensal.
    """
    from ..engine.utilidades import meses_entre

    inicio = projeto.terreno.datas.inicio_projeto
    return {
        0: "M0",
        meses_entre(inicio, projeto.terreno.datas.aprovacao): "Aprov.",
        meses_entre(inicio, projeto.terreno.datas.lancamento_vendas): "Lanc.",
        meses_entre(inicio, projeto.terreno.datas.inicio_obras): "Ini.Obras",
        meses_entre(inicio, projeto.terreno.datas.termino_obras): "Fim Obras",
    }


def horizonte_visual_projeto(projeto) -> int:
    """
    Devolve o ultimo mes a mostrar nas tabelas mensais.

    Usa o termino de obras + 12 meses de buffer (para vendas e financiamento
    que continuam apos a obra). Isso e independente do horizonte real do
    calculo, que e bem maior — aqui o usuario nao precisa preencher 120 meses.
    """
    from ..engine.utilidades import meses_entre

    inicio = projeto.terreno.datas.inicio_projeto
    m_termino_obras = meses_entre(inicio, projeto.terreno.datas.termino_obras)
    return m_termino_obras + 36


def criar_fig_linha_do_tempo(projeto):
    """
    Cria e devolve a figura Plotly da linha do tempo do projeto.

    Exibe faixas de fase (Pre-obra / Obras / Pos-obra) e 5 marcos com
    marcadores alternados acima/abaixo para evitar sobreposicao de labels.
    """
    import plotly.graph_objects as go
    from ..engine.utilidades import meses_entre

    inicio = projeto.terreno.datas.inicio_projeto
    aprovacao = projeto.terreno.datas.aprovacao
    lancamento = projeto.terreno.datas.lancamento_vendas
    inicio_obras = projeto.terreno.datas.inicio_obras
    termino_obras = projeto.terreno.datas.termino_obras

    m_aprov = meses_entre(inicio, aprovacao)
    m_lanc = meses_entre(inicio, lancamento)
    m_ini = meses_entre(inicio, inicio_obras)
    m_fim = meses_entre(inicio, termino_obras)
    max_mes = max(m_fim + 3, 12)

    nomes_m = ["jan", "fev", "mar", "abr", "mai", "jun",
               "jul", "ago", "set", "out", "nov", "dez"]

    def fmt(d):
        return f"{nomes_m[d.month - 1]}/{d.year}"

    dtick = (
        1 if max_mes <= 12
        else 3 if max_mes <= 30
        else 6 if max_mes <= 60
        else 12
    )

    fig = go.Figure()

    # Faixas de fase coloridas — paleta Altiplano (tema claro)
    fases = [
        (0, m_ini, "rgba(100,140,180,0.10)", "Pre-obra", "#4A7FA5"),
        (m_ini, m_fim, "rgba(43,80,168,0.12)", "Obras", "#2B50A8"),
        (m_fim, max_mes, "rgba(60,140,90,0.10)", "Pos-obra", "#3D8B5E"),
    ]
    for x0, x1, fillcolor, label, labelcor in fases:
        if x1 > x0:
            fig.add_shape(
                type="rect", x0=x0, x1=x1, y0=-0.28, y1=0.28,
                fillcolor=fillcolor, line=dict(width=0), layer="below",
            )
            fig.add_annotation(
                x=(x0 + x1) / 2, y=0,
                text=label,
                showarrow=False,
                font=dict(size=10, color=labelcor),
                xanchor="center", yanchor="middle",
            )

    # Marcos alternados (acima nos pares, abaixo nos impares)
    milestones = [
        (0,       "Inicio",       fmt(inicio),       "#5A5650"),
        (m_aprov, "Aprovacao",    fmt(aprovacao),    "#4A7FA5"),
        (m_lanc,  "Lancamento",   fmt(lancamento),   "#3D8B5E"),
        (m_ini,   "Inicio Obras", fmt(inicio_obras), "#2B50A8"),
        (m_fim,   "Fim Obras",    fmt(termino_obras),"#C05454"),
    ]

    for i, (mes, nome, data_str, cor) in enumerate(milestones):
        ymark = 0.85 if i % 2 == 0 else -0.85
        ystem = 0.28 if ymark > 0 else -0.28
        fig.add_shape(
            type="line",
            x0=mes, x1=mes, y0=ystem, y1=ymark * 0.72,
            line=dict(color=cor, width=1.5, dash="dot"),
        )
        fig.add_trace(go.Scatter(
            x=[mes], y=[ymark],
            mode="markers+text",
            marker=dict(size=10, color=cor, symbol="circle",
                        line=dict(color="#F5F3EE", width=2)),
            text=[f"<b>M{mes}</b> {data_str}<br>{nome}"],
            textposition="top center" if ymark > 0 else "bottom center",
            textfont=dict(size=9, color=cor),
            hovertemplate=f"<b>{nome}</b><br>Mes {mes} — {data_str}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        paper_bgcolor="#F5F3EE",
        plot_bgcolor="#F5F3EE",
        font=dict(color="#1A1916", family="Inter, sans-serif", size=11),
        margin=dict(l=20, r=20, t=20, b=50),
        height=250,
        xaxis=dict(
            title="Mes do projeto",
            range=[-0.5, max_mes + 0.5],
            dtick=dtick,
            gridcolor="#E8E5DC",
            zeroline=False,
            tickfont=dict(size=11, color="#5A5650"),
        ),
        yaxis=dict(visible=False, range=[-1.6, 1.6]),
        showlegend=False,
        hoverlabel=dict(bgcolor="#ECEAE4", font_size=12, font_color="#1A1916"),
    )
    return fig


def linha_do_tempo(projeto, expandida: bool = True) -> None:
    """Renderiza a linha do tempo do projeto em um expander."""
    with st.expander("📅 Linha do tempo do projeto", expanded=expandida):
        fig = criar_fig_linha_do_tempo(projeto)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(
            "Os numeros 'M' sao os meses relativos ao inicio do projeto. "
            "Use eles ao preencher campos 'Mes inicio' e 'Mes fim' nas demais abas."
        )


def btn_proximo_modulo(label_proximo: str, target_idx: int | None = None) -> None:
    """Botao de navegacao para o proximo modulo."""
    st.markdown("---")
    _, col_btn = st.columns([3, 2])
    with col_btn:
        if st.button(
            f"Continuar — {label_proximo} →",
            type="primary",
            use_container_width=True,
            key=f"btn_nav_{label_proximo}",
        ):
            idx = st.session_state.get("modulo_atual_idx", 0)
            new_idx = target_idx if target_idx is not None else idx + 1
            st.session_state["modulo_atual_idx"] = new_idx
            st.rerun()
