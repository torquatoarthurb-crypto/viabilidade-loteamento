"""
Pagina Inicial — Biblioteca de Projetos do Usuario.

Exibida apos o login, antes de abrir um projeto.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st

from ...auth import (
    autenticar,
    carregar_projetos_usuario,
    duplicar_projeto_usuario,
    excluir_projeto_usuario,
    limpar_sessao,
    salvar_projeto_usuario,
)
from ...modelos import projeto_novo, Projeto
from ..helpers import (
    formatar_brl,
    get_projeto,
    garantir_projeto_inicial,
    limpar_cache_inputs_brl,
    set_projeto,
)

# =====================================================================
# SVG logo (fundo escuro — elipses brancas + ponto ocre)
# =====================================================================
_LOGO_SVG = (
    '<svg width="36" height="28" viewBox="0 0 64 52" '
    'xmlns="http://www.w3.org/2000/svg" fill="none">'
    '<ellipse cx="32" cy="26" rx="29" ry="13" stroke="#1A1916" '
    'stroke-width="1.2" opacity="0.18"/>'
    '<ellipse cx="32" cy="26" rx="21" ry="9" stroke="#1A1916" '
    'stroke-width="1.5" opacity="0.38"/>'
    '<ellipse cx="32" cy="26" rx="13" ry="5.5" stroke="#1A1916" '
    'stroke-width="1.9" opacity="0.65"/>'
    '<ellipse cx="32" cy="26" rx="5.5" ry="2.2" fill="#B07D2E"/>'
    '</svg>'
)
_LOGO_IMG = (
    '<img src="data:image/svg+xml;base64,'
    + base64.b64encode(_LOGO_SVG.encode()).decode()
    + '" width="36" height="28" style="display:block;">'
)

_CSS_HOME = """
<style>
section[data-testid="stSidebar"] { display: none !important; }
.main .block-container {
    max-width: 1200px !important;
    padding-top: 28px !important;
}

/* ---- Header ---- */
.home-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 18px;
    border-bottom: 0.5px solid #ECEAE4;
    margin-bottom: 24px;
}
.home-header-left {
    display: flex;
    align-items: center;
    gap: 14px;
}
.home-wordmark { line-height: 1.1; }
.home-wordmark-name {
    font-family: 'DM Serif Display', serif;
    font-size: 18px;
    color: #1A1916;
}
.home-wordmark-tag {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #8A8880;
    margin-top: 2px;
}
.home-user-pill {
    background: #F5F3EE;
    border: 0.5px solid #ECEAE4;
    border-radius: 99px;
    padding: 5px 14px;
    font-size: 13px;
    color: #4A4944;
    font-weight: 500;
}

/* ---- Métricas da carteira ---- */
.metr-card {
    background: #FFFFFF;
    border: 0.5px solid #ECEAE4;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
    box-shadow: 0 1px 6px rgba(26,25,22,0.04);
}
.metr-label {
    font-size: 10px;
    font-weight: 600;
    color: #8A8880;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: 6px;
}
.metr-valor {
    font-family: 'DM Serif Display', serif;
    font-size: 22px;
    color: #1A1916;
}
.metr-sub { font-size: 11px; color: #8A8880; margin-top: 3px; }

/* ---- Cards de projeto ---- */
.proj-card {
    background: #FFFFFF;
    border: 0.5px solid #C4C1B8;
    border-radius: 12px;
    padding: 18px 20px 14px;
    height: 100%;
    transition: border-color .15s, box-shadow .15s;
    position: relative;
}
.proj-card:hover {
    border-color: #8A8880;
    box-shadow: 0 4px 18px rgba(26,25,22,0.07);
}
.proj-nome {
    font-family: 'DM Serif Display', serif;
    font-size: 16px;
    color: #1A1916;
    margin-bottom: 2px;
    padding-right: 80px; /* espaço para o badge */
}
.proj-local {
    font-size: 12px;
    color: #8A8880;
    margin-bottom: 10px;
}

/* Status badge (canto superior direito do card) */
.proj-status {
    position: absolute;
    top: 16px;
    right: 16px;
    font-size: 10px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 99px;
}
.proj-status.calc {
    background: #E8F5EE;
    color: #1A5C38;
    border: 0.5px solid #2D7A4F;
}
.proj-status.pend {
    background: #F5F3EE;
    color: #8A8880;
    border: 0.5px solid #C4C1B8;
}

.proj-vgv {
    font-size: 13px;
    color: #1A1916;
    font-weight: 600;
    margin-bottom: 2px;
}
.proj-lotes { font-size: 12px; color: #8A8880; margin-bottom: 8px; }
.proj-data  { font-size: 11px; color: #C4C1B8; margin-top: 10px; }

/* Grade de KPIs no card */
.proj-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 5px;
    margin: 10px 0 6px;
}
.proj-cell {
    background: #F5F3EE;
    border-radius: 6px;
    padding: 7px 9px;
}
.proj-cell-wide { grid-column: span 2; }
.proj-cell-label {
    font-size: 9px;
    color: #8A8880;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: 2px;
    white-space: nowrap;
}
.proj-cell-val {
    font-size: 13px;
    font-weight: 700;
    color: #1A1916;
}
.proj-cell-val.neg { color: #B83C2A; }
.proj-cell-val.pos { color: #2D7A4F; }
.tma-tag {
    font-size: 9px;
    font-weight: 600;
    color: #B07D2E;
    background: rgba(176,125,46,0.12);
    border-radius: 3px;
    padding: 1px 5px;
    margin-left: 4px;
    vertical-align: middle;
}

/* ---- Empty state ---- */
.empty-state {
    padding: 48px 0 16px;
}
.empty-title {
    font-family: 'DM Serif Display', serif;
    font-size: 22px;
    color: #1A1916;
    margin-bottom: 6px;
}
.empty-sub {
    font-size: 14px;
    color: #8A8880;
    margin-bottom: 32px;
}
.empty-card {
    background: #FFFFFF;
    border: 0.5px solid #C4C1B8;
    border-radius: 12px;
    padding: 24px;
    height: 100%;
    transition: border-color .15s, box-shadow .15s;
}
.empty-card:hover {
    border-color: #8A8880;
    box-shadow: 0 4px 18px rgba(26,25,22,0.07);
}
.empty-card.destaque {
    border-color: #B07D2E;
    border-width: 1px;
    background: #FAF3E8;
}
.empty-card-icon { font-size: 28px; margin-bottom: 10px; }
.empty-card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 17px;
    color: #1A1916;
    margin-bottom: 6px;
}
.empty-card-desc { font-size: 13px; color: #8A8880; line-height: 1.5; margin-bottom: 16px; }
</style>
"""

# =====================================================================
# Helpers internos
# =====================================================================

def _abrir_projeto(caminho: str) -> None:
    try:
        with open(caminho, encoding="utf-8") as f:
            data = json.load(f)
        projeto = Projeto.model_validate(data)
        garantir_projeto_inicial()
        set_projeto(projeto)
        st.session_state["projeto_path_atual"] = caminho
        st.session_state["nome_arquivo_atual"] = Path(caminho).name
        limpar_cache_inputs_brl()
        for chave in [
            "aba2_lista_fluxos", "aba2_curva_mensal", "aba3_lista_etapas",
            "aba3_resumido_distrib", "aba4_lista_despesas",
            "aba_terreno_fluxo_distrib", "_sens_cache", "_mc_resultados",
            "historico_versoes", "modulo_atual_idx",
        ]:
            st.session_state.pop(chave, None)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao abrir projeto: {e}")


def _novo_projeto() -> None:
    garantir_projeto_inicial()
    set_projeto(projeto_novo())
    st.session_state["projeto_path_atual"] = "__novo__"
    st.session_state["nome_arquivo_atual"] = None
    for chave in [
        "aba2_lista_fluxos", "aba2_curva_mensal", "aba3_lista_etapas",
        "aba3_resumido_distrib", "aba4_lista_despesas",
        "aba_terreno_fluxo_distrib", "_sens_cache", "_mc_resultados",
        "historico_versoes", "modulo_atual_idx",
    ]:
        st.session_state.pop(chave, None)
    limpar_cache_inputs_brl()
    st.rerun()


def _carregar_demo(email: str) -> None:
    """Carrega o projeto exemplo pré-preenchido."""
    demo_path = Path(__file__).parents[4] / "exemplos" / "projeto_exemplo.json"
    if not demo_path.exists():
        st.error("Arquivo de demonstração não encontrado.")
        return
    try:
        with open(demo_path, encoding="utf-8") as f:
            data = json.load(f)
        projeto = Projeto.model_validate(data)
        caminho = salvar_projeto_usuario(email, projeto)
        garantir_projeto_inicial()
        set_projeto(projeto)
        st.session_state["projeto_path_atual"] = str(caminho)
        st.session_state["nome_arquivo_atual"] = "projeto_exemplo.json"
        limpar_cache_inputs_brl()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar demo: {e}")


# =====================================================================
# Sub-componentes
# =====================================================================

def _renderizar_header(nome_usuario: str) -> None:
    st.markdown(
        f'<div class="home-header">'
        f'  <div class="home-header-left">'
        f'    {_LOGO_IMG}'
        f'    <div class="home-wordmark">'
        f'      <div class="home-wordmark-name">Altiplano</div>'
        f'      <div class="home-wordmark-tag">Viabilidade</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="home-user-pill">👤 {nome_usuario}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _renderizar_metricas(projetos: list[dict]) -> None:
    total_proj = len(projetos)
    total_vgv = sum(p["vgv_bruto"] for p in projetos)
    total_lotes = sum(p["total_lotes"] for p in projetos)

    calculados = [p for p in projetos if p.get("meta")]
    tirs = [
        p["meta"]["tir_anual"]
        for p in calculados
        if p["meta"].get("tir_anual") is not None
    ]
    tir_media = sum(tirs) / len(tirs) if tirs else None

    c1, c2, c3 = st.columns(3)
    dados = [
        (c1, "Projetos", str(total_proj), "na carteira"),
        (
            c2,
            "VGV Total",
            _fmt_val(total_vgv) if total_vgv > 0 else "—",
            "soma dos projetos calculados",
        ),
        (
            c3,
            "TIR Média",
            f"{tir_media * 100:.1f}% a.a." if tir_media else "—",
            f"{len(tirs)} calculado(s)" if tirs else "calcule os projetos",
        ),
    ]
    for col, label, valor, sub in dados:
        with col:
            st.markdown(
                f'<div class="metr-card">'
                f'<div class="metr-label">{label}</div>'
                f'<div class="metr-valor">{valor}</div>'
                f'<div class="metr-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _fmt_pct(v) -> str:
    return f"{v * 100:.1f}%" if v is not None else "—"


def _fmt_val(v) -> str:
    if v is None:
        return "—"
    av = abs(v)
    sinal = "-" if v < 0 else ""
    if av >= 1_000_000:
        return f"{sinal}R$ {av / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"{sinal}R$ {av / 1_000:.0f}k"
    return f"{sinal}R$ {av:.0f}"


def _cls(v) -> str:
    if v is None:
        return ""
    return " neg" if v < 0 else " pos"


def _renderizar_card(proj: dict, email: str, idx: int) -> None:
    meta = proj.get("meta")
    nome = proj["nome"]
    local = f"{proj['cidade']} / {proj['uf']}" if proj.get("cidade") else "—"
    vgv_str = _fmt_val(proj["vgv_bruto"]) if proj["vgv_bruto"] > 0 else "—"
    lotes_str = f"{proj['total_lotes']} lotes" if proj["total_lotes"] > 0 else "—"

    if meta and meta.get("tir_anual") is not None:
        status_badge = '<span class="proj-status calc">✓ Calculado</span>'
    else:
        status_badge = '<span class="proj-status pend">○ Pendente</span>'

    # Grade de KPIs (só quando calculado)
    kpis_html = ""
    if meta:
        mb_v  = meta.get("margem_bruta")
        ml_v  = meta.get("margem")
        exp_v = meta.get("exposicao_maxima")
        res_v = meta.get("lucro_liquido")
        vpl_v = meta.get("vpl")
        tma   = meta.get("tma")
        tma_tag = (
            f'<span class="tma-tag">TMA {tma:.0f}%</span>'
            if tma is not None else ""
        )
        kpis_html = (
            f'<div class="proj-grid">'
            f'<div class="proj-cell">'
            f'<div class="proj-cell-label">Marg. Bruta</div>'
            f'<div class="proj-cell-val{_cls(mb_v)}">{_fmt_pct(mb_v)}</div>'
            f'</div>'
            f'<div class="proj-cell">'
            f'<div class="proj-cell-label">Marg. Líquida</div>'
            f'<div class="proj-cell-val{_cls(ml_v)}">{_fmt_pct(ml_v)}</div>'
            f'</div>'
            f'<div class="proj-cell">'
            f'<div class="proj-cell-label">Resultado</div>'
            f'<div class="proj-cell-val{_cls(res_v)}">{_fmt_val(res_v)}</div>'
            f'</div>'
            f'<div class="proj-cell">'
            f'<div class="proj-cell-label">Exposição</div>'
            f'<div class="proj-cell-val neg">{_fmt_val(exp_v)}</div>'
            f'</div>'
            f'<div class="proj-cell proj-cell-wide">'
            f'<div class="proj-cell-label">VPL {tma_tag}</div>'
            f'<div class="proj-cell-val{_cls(vpl_v)}">{_fmt_val(vpl_v)}</div>'
            f'</div>'
            f'</div>'
        )
    else:
        kpis_html = (
            '<div style="font-size:12px;color:#8A8880;padding:10px 0 4px;">'
            'Calcule para ver os indicadores →'
            '</div>'
        )

    calc_info = meta.get("calculado_em", "") if meta else ""

    st.markdown(
        f'<div class="proj-card">'
        f'{status_badge}'
        f'<div class="proj-nome">{nome}</div>'
        f'<div class="proj-local">📍 {local}</div>'
        f'<div class="proj-vgv">{vgv_str}</div>'
        f'<div class="proj-lotes">{lotes_str}</div>'
        f'{kpis_html}'
        f'<div class="proj-data">💾 {proj["ultima_modificacao"]}'
        f'{(" · Calc.: " + calc_info) if calc_info else ""}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Botões de ação
    col_a, col_b, col_c = st.columns([3, 2, 1])
    with col_a:
        if st.button(
            "Abrir →",
            key=f"btn_abrir_{idx}",
            use_container_width=True,
            type="primary",
        ):
            _abrir_projeto(proj["caminho"])
    with col_b:
        if st.button(
            "Duplicar",
            key=f"btn_dup_{idx}",
            use_container_width=True,
            help="Cria uma cópia deste projeto",
        ):
            novo_nome = duplicar_projeto_usuario(email, nome)
            if novo_nome:
                st.success(f"Duplicado: {novo_nome}")
                st.rerun()
            else:
                st.error("Não foi possível duplicar.")
    with col_c:
        if st.button(
            "🗑",
            key=f"btn_del_{idx}",
            use_container_width=True,
            help="Excluir projeto",
        ):
            st.session_state[f"_confirmar_del_{idx}"] = True

    if st.session_state.get(f"_confirmar_del_{idx}"):
        st.warning(f"⚠ Excluir **{nome}**? Esta ação não pode ser desfeita.")
        senha_del = st.text_input(
            "Confirme sua senha para continuar",
            type="password",
            key=f"senha_del_{idx}",
        )
        ca, cb = st.columns(2)
        with ca:
            if st.button(
                "Excluir permanentemente",
                key=f"btn_conf_del_{idx}",
                type="primary",
            ):
                if not senha_del:
                    st.error("Digite sua senha.")
                else:
                    ok, _, _ = autenticar(email, senha_del)
                    if ok:
                        excluir_projeto_usuario(email, nome)
                        st.session_state.pop(f"_confirmar_del_{idx}", None)
                        st.success("Projeto excluído.")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
        with cb:
            if st.button("Cancelar", key=f"btn_canc_del_{idx}"):
                st.session_state.pop(f"_confirmar_del_{idx}", None)
                st.rerun()


def _renderizar_empty_state(email: str) -> None:
    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-title">Bem-vindo à Altiplano Viabilidade.</div>'
        '<div class="empty-sub">Comece sua primeira análise de viabilidade.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_demo, col_novo = st.columns(2, gap="medium")

    with col_demo:
        st.markdown(
            '<div class="empty-card destaque">'
            '<div class="empty-card-icon">▶</div>'
            '<div class="empty-card-title">Explorar projeto demo</div>'
            '<div class="empty-card-desc">'
            'Loteamento fictício pré-preenchido. Ideal para conhecer a ferramenta '
            'antes de criar seu primeiro projeto.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Carregar demo →",
            key="home_demo",
            use_container_width=True,
            type="primary",
        ):
            _carregar_demo(email)

    with col_novo:
        st.markdown(
            '<div class="empty-card">'
            '<div class="empty-card-icon">＋</div>'
            '<div class="empty-card-title">Criar projeto vazio</div>'
            '<div class="empty-card-desc">'
            'Comece do zero configurando todas as informações do seu empreendimento.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Novo projeto →",
            key="home_novo_empty",
            use_container_width=True,
        ):
            _novo_projeto()

    st.markdown(
        '<div style="text-align:center;margin-top:20px;font-size:12px;color:#8A8880;">'
        'Já tem um projeto salvo? Use <b>Restaurar projeto</b> acima.'
        '</div>',
        unsafe_allow_html=True,
    )


# =====================================================================
# Renderizador principal
# =====================================================================

def renderizar() -> None:
    st.markdown(_CSS_HOME, unsafe_allow_html=True)

    usuario = st.session_state.get("usuario_logado", {})
    email = usuario.get("email", "")
    nome_usuario = usuario.get("nome", "Usuário")

    # ---- Header ----
    _renderizar_header(nome_usuario)

    # ---- Barra de ações ----
    col_novo, col_import, col_sair = st.columns([2, 2, 1])
    with col_novo:
        if st.button(
            "➕ Novo Projeto",
            use_container_width=True,
            type="primary",
            key="home_novo",
        ):
            _novo_projeto()
    with col_import:
        arquivo = st.file_uploader(
            "Restaurar projeto",
            type=["json"],
            key="home_upload",
            label_visibility="collapsed",
            help="Importar arquivo .json de projeto",
        )
        if arquivo is not None:
            try:
                data = json.load(arquivo)
                projeto = Projeto.model_validate(data)
                caminho = salvar_projeto_usuario(email, projeto)
                garantir_projeto_inicial()
                set_projeto(projeto)
                st.session_state["projeto_path_atual"] = str(caminho)
                st.session_state["nome_arquivo_atual"] = arquivo.name
                limpar_cache_inputs_brl()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao importar: {e}")
        else:
            st.button(
                "📂 Restaurar projeto",
                use_container_width=True,
                key="home_btn_upload_label",
                disabled=True,
                help="Clique acima para selecionar um arquivo .json",
            )
    with col_sair:
        if st.button("Sair", key="home_sair", use_container_width=True):
            limpar_sessao()
            st.session_state.pop("usuario_logado", None)
            st.session_state.pop("projeto_path_atual", None)
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Conteúdo principal ----
    projetos = carregar_projetos_usuario(email)

    if not projetos:
        _renderizar_empty_state(email)
        return

    # Métricas da carteira
    _renderizar_metricas(projetos)
    st.markdown("<br>", unsafe_allow_html=True)

    # Contador
    st.markdown(
        f'<div style="font-size:12px;color:#8A8880;margin-bottom:14px;">'
        f'{len(projetos)} projeto(s) na carteira</div>',
        unsafe_allow_html=True,
    )

    # Grade de cards — 3 colunas
    COLS = 3
    for row_start in range(0, len(projetos), COLS):
        row = projetos[row_start: row_start + COLS]
        cols = st.columns(COLS, gap="medium")
        for i, (col, proj) in enumerate(zip(cols, row)):
            with col:
                _renderizar_card(proj, email, row_start + i)
        st.markdown("<br>", unsafe_allow_html=True)
