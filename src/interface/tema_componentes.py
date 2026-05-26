"""
Componentes visuais Altiplano:
- Logo (4 elipses concentricas) + wordmark na sidebar
- Header com breadcrumb
- Cards de KPI com 4 estados semanticos
- Grade de KPIs
- Saude do modelo
- Resumo tempo real
"""

from __future__ import annotations

import streamlit as st


# =====================================================================
# LOGO — elipses concentricas (SVG inline)
# =====================================================================

_LOGO_SVG_CLARO = (
    '<svg width="46" height="38" viewBox="0 0 32 26" fill="none">'
    '<ellipse cx="16" cy="13" rx="14.5" ry="6.5" stroke="#F5F3EE" stroke-width="0.9" opacity="0.22"/>'
    '<ellipse cx="16" cy="13" rx="10.5" ry="4.5" stroke="#F5F3EE" stroke-width="1.1" opacity="0.45"/>'
    '<ellipse cx="16" cy="13" rx="6" ry="2.5" stroke="#F5F3EE" stroke-width="1.5" opacity="0.75"/>'
    '<ellipse cx="16" cy="13" rx="2.2" ry="0.9" fill="#FFFFFF"/>'
    '</svg>'
)

_LOGO_SVG_ESCURO = (
    '<svg width="40" height="32" viewBox="0 0 32 26" fill="none">'
    '<ellipse cx="16" cy="13" rx="14.5" ry="6.5" stroke="#1A1916" stroke-width="0.9" opacity="0.18"/>'
    '<ellipse cx="16" cy="13" rx="10.5" ry="4.5" stroke="#1A1916" stroke-width="1.1" opacity="0.38"/>'
    '<ellipse cx="16" cy="13" rx="6" ry="2.5" stroke="#1A1916" stroke-width="1.5" opacity="0.65"/>'
    '<ellipse cx="16" cy="13" rx="2.2" ry="0.9" fill="#B07D2E"/>'
    '</svg>'
)

def _svg_img(svg: str) -> str:
    return svg

_LOGO_IMG_CLARO  = _svg_img(_LOGO_SVG_CLARO)
_LOGO_IMG_ESCURO = _svg_img(_LOGO_SVG_ESCURO)


def renderizar_logo_sidebar() -> None:
    """Renderiza o logo Altiplano + wordmark no topo da sidebar."""
    html = (
        '<div style="display:flex;align-items:center;gap:12px;'
        'padding:20px 14px 16px;border-bottom:0.5px solid #2A2825;margin-bottom:4px;">'
        + _LOGO_IMG_CLARO
        + '<div>'
        '<div style="font-family:\'DM Serif Display\',serif;font-size:22px;'
        'color:#F5F3EE;letter-spacing:0.02em;line-height:1.1;">Altiplano</div>'
        '<div style="font-size:10px;font-weight:500;color:#8A8880;'
        'letter-spacing:0.12em;text-transform:uppercase;margin-top:2px;">Viabilidade</div>'
        '</div></div>'
    )
    st.sidebar.markdown(html, unsafe_allow_html=True)


# =====================================================================
# HEADER — breadcrumb + salvo automaticamente
# =====================================================================

def renderizar_header_principal(projeto, modulo_atual: str) -> None:
    nome_projeto = projeto.terreno.info.nome

    html = f"""
    <div class="header-principal">
        <div class="breadcrumb">
            {_LOGO_IMG_ESCURO}
            <span style="color:#C4C1B8;">›</span>
            <span class="item-ativo">{nome_projeto}</span>
            <span style="color:#C4C1B8;">›</span>
            <span>{modulo_atual}</span>
        </div>
        <div class="salvo-automaticamente">Salvo automaticamente</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def renderizar_titulo_modulo(titulo: str, numero: int, total: int = 9) -> None:
    html = f"""
    <div class="modulo-titulo">
        <h1>{titulo}</h1>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =====================================================================
# KPI CARDS — 4 estados semanticos
# =====================================================================

def renderizar_kpi_card(
    label: str,
    valor: str,
    sub: str = "",
    cor: str = "neutro",
    help: str = "",
) -> str:
    """
    Devolve HTML de um card KPI Altiplano.
    cor: 'verde' | 'vermelho' | 'atencao' | 'neutro' | 'neutro-azul'
    help: texto de tooltip exibido ao passar o mouse sobre o card.
    """
    _alias = {"neutro": "neutro", "azul": "neutro-azul"}
    cor_cls = _alias.get(cor, cor)

    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    title_attr = f' title="{help}"' if help else ""
    return (
        f'<div class="kpi-card {cor_cls}"{title_attr}>'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-valor">{valor}</div>'
        f'{sub_html}'
        f'</div>'
    )


def renderizar_grade_kpis(kpis: list[dict]) -> None:
    """
    Grade 4xN de cards KPI.
    kpis: lista de dicts {label, valor, sub?, cor?, help?}
    """
    if not kpis:
        return

    linhas = [kpis[i:i+4] for i in range(0, len(kpis), 4)]
    for linha in linhas:
        while len(linha) < 4:
            linha.append(None)

        cards_html = ""
        for kpi in linha:
            if kpi is None:
                cards_html += '<div style="flex:1;"></div>'
            else:
                card = renderizar_kpi_card(
                    kpi["label"],
                    kpi["valor"],
                    kpi.get("sub", ""),
                    kpi.get("cor", "neutro"),
                    kpi.get("help", ""),
                )
                cards_html += f'<div style="flex:1;">{card}</div>'

        st.markdown(
            f'<div style="display:flex;gap:12px;margin-bottom:12px;">{cards_html}</div>',
            unsafe_allow_html=True,
        )


# =====================================================================
# SAUDE DO MODELO
# =====================================================================

def renderizar_saude_modelo(checks: list[tuple[bool, str]]) -> None:
    metade = len(checks) // 2 + len(checks) % 2
    esq = ""
    dir_ = ""
    for i, (passou, msg) in enumerate(checks):
        if passou:
            simb = '<span class="check-ok">⊙</span>'
        else:
            simb = '<span class="check-err">⊗</span>'
        item = f'<div class="saude-item">{simb}<span>{msg}</span></div>'
        if i < metade:
            esq += item
        else:
            dir_ += item

    html = f"""
    <div class="card">
        <div class="card-titulo">Saúde do modelo</div>
        <div style="display:flex;gap:30px;">
            <div style="flex:1;">{esq}</div>
            <div style="flex:1;">{dir_}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =====================================================================
# LINHA DO TEMPO
# =====================================================================

def renderizar_linha_tempo_trilhas(projeto) -> None:
    from .helpers import criar_fig_linha_do_tempo

    st.markdown(
        '<div class="card-titulo">Linha do tempo do empreendimento</div>',
        unsafe_allow_html=True,
    )
    fig = criar_fig_linha_do_tempo(projeto)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# =====================================================================
# RESUMO TEMPO REAL — rodape sidebar
# =====================================================================

def renderizar_resumo_tempo_real_sidebar(projeto, resultado) -> None:
    from .helpers import formatar_brl

    vgv = projeto.terreno.vgv_bruto

    if resultado is not None:
        custo = resultado.resumo.get("total_saidas", 0)
        lucro = resultado.resumo.get("lucro_liquido", 0)
        margem = (lucro / vgv * 100) if vgv > 0 else 0
        cor_margem = "verde" if margem > 0 else "vermelho"
    else:
        custo = None
        margem = None
        cor_margem = ""

    def fmt_curto(valor):
        if valor is None:
            return "—"
        if abs(valor) >= 1_000_000:
            return f"R$ {valor/1_000_000:.1f}M"
        if abs(valor) >= 1_000:
            return f"R$ {valor/1_000:.0f}K"
        return formatar_brl(valor)

    margem_txt = f"{margem:.1f}%" if margem is not None else "—"

    html = f"""
    <div class="resumo-tempo-real">
        <div class="titulo">Resumo</div>
        <div class="item">
            <div class="item-label">VGV bruto</div>
            <div class="item-valor">{fmt_curto(vgv)}</div>
        </div>
        <div class="item">
            <div class="item-label">Custo total</div>
            <div class="item-valor">{fmt_curto(custo)}</div>
        </div>
        <div class="item">
            <div class="item-label">Margem</div>
            <div class="item-valor {cor_margem}">{margem_txt}</div>
        </div>
    </div>
    """
    st.sidebar.markdown(html, unsafe_allow_html=True)


# =====================================================================
# NAVEGACAO DE MODULOS — sidebar
# =====================================================================

def renderizar_navegacao_modulos_sidebar(
    modulos_info: list[dict],
    modulo_atual_idx: int,
) -> int:
    GRUPOS = [
        ("Dados",      {1, 9, 2, 3, 4, 5}, True),
        ("Resultados", {0, 6, 7, 8},        False),
        ("Avançado",   {13, 14},             False),
        ("Análise",    {10, 11, 12},         False),
    ]

    def _simb(status: str) -> str:
        return {"ok": " ✓", "warn": " ⚠", "err": " ✗"}.get(status, "")

    novo_idx = modulo_atual_idx

    for grupo_nome, grupo_numeros, numerado in GRUPOS:
        indices = [
            i for i, m in enumerate(modulos_info)
            if m["numero"] in grupo_numeros
        ]
        if not indices:
            continue

        st.sidebar.markdown(
            f'<div class="nav-grupo-header">{grupo_nome}</div>',
            unsafe_allow_html=True,
        )

        for passo, i in enumerate(indices, start=1):
            m = modulos_info[i]
            nome = m["nome"]
            icone = m.get("icone", "·")
            simb = _simb(m.get("status", "neutro"))
            prefixo = f"{passo}. " if numerado else ""
            label = f"{prefixo}{nome}{simb}"
            is_active = (i == modulo_atual_idx)

            if is_active:
                st.sidebar.button(
                    label,
                    key=f"nav_btn_{m['numero']}",
                    width="stretch",
                    disabled=True,
                    icon=icone,
                )
            else:
                if st.sidebar.button(
                    label,
                    key=f"nav_btn_{m['numero']}",
                    width="stretch",
                    icon=icone,
                ):
                    novo_idx = i

    return novo_idx
