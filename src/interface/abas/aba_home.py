"""
Pagina Inicial — Biblioteca de Projetos do Usuario.

Exibida apos o login, antes de abrir um projeto.
Mostra:
- Metricas consolidadas da carteira
- Grade de cards de projetos
- Acoes: Novo Projeto, Abrir JSON, Abrir projeto existente
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ...auth import (
    autenticar,
    carregar_projetos_usuario,
    duplicar_projeto_usuario,
    excluir_projeto_usuario,
    limpar_sessao,
    pasta_projetos,
)
from ...modelos import projeto_novo, Projeto
from ..helpers import (
    formatar_brl,
    get_projeto,
    garantir_projeto_inicial,
    limpar_cache_inputs_brl,
    set_projeto,
)


_CSS_HOME = """
<style>
section[data-testid="stSidebar"] { display: none !important; }
.main .block-container {
    max-width: 1200px !important;
    padding-top: 32px !important;
}

.home-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
}
.home-title { font-size: 22px; font-weight: 700; color: #F5F3EE; }
.home-sub   { font-size: 13px; color: #8A8880; }

/* Cards de projeto */
.proj-card {
    background: #1A1E27;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 20px;
    height: 100%;
    transition: border-color .2s;
}
.proj-card:hover { border-color: rgba(255,255,255,0.18); }
.proj-nome   { font-size: 15px; font-weight: 700; color: #F5F3EE; margin-bottom: 2px; }
.proj-local  { font-size: 12px; color: #8A8880; margin-bottom: 12px; }
.proj-vgv    { font-size: 13px; color: #60A5FA; font-weight: 600; }
.proj-lotes  { font-size: 12px; color: #8A8880; margin-bottom: 8px; }
.proj-data   { font-size: 11px; color: #4A4845; margin-top: 10px; }

/* Badge TIR */
.badge-tir {
    display:inline-block;
    background:rgba(52,199,89,0.15);
    color:#34C759;
    border:1px solid rgba(52,199,89,0.3);
    border-radius:99px;
    font-size:11px;
    font-weight:700;
    padding:2px 10px;
    margin-bottom: 6px;
}
.badge-sem {
    display:inline-block;
    background:rgba(255,255,255,0.05);
    color:#6B7280;
    border:1px solid rgba(255,255,255,0.08);
    border-radius:99px;
    font-size:11px;
    padding:2px 10px;
    margin-bottom: 6px;
}

/* Metricas da carteira */
.metr-card {
    background: #1A1E27;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metr-label { font-size: 11px; color: #8A8880; text-transform: uppercase;
              letter-spacing: .04em; margin-bottom: 4px; }
.metr-valor { font-size: 20px; font-weight: 700; color: #F5F3EE; }
.metr-sub   { font-size: 11px; color: #6B7280; margin-top: 2px; }
</style>
"""


def _abrir_projeto(caminho: str) -> None:
    """Carrega projeto do disco e entra na tela principal."""
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
    """Cria projeto vazio e entra na tela principal."""
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


def _renderizar_metricas(projetos: list[dict]) -> None:
    """Renderiza os cards de métricas consolidadas da carteira."""
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

    c1, c2, c3, c4 = st.columns(4)
    metricas = [
        (c1, "Projetos na Carteira", str(total_proj), ""),
        (c2, "VGV Total", formatar_brl(total_vgv) if total_vgv > 0 else "—", "soma dos projetos"),
        (
            c3,
            "TIR Média",
            f"{tir_media * 100:.1f}% a.a." if tir_media else "—",
            f"{len(tirs)} projeto(s) calculado(s)" if tirs else "calcule os projetos",
        ),
        (c4, "Total de Lotes", f"{total_lotes:,}".replace(",", ".") if total_lotes else "—", ""),
    ]
    for col, label, valor, sub in metricas:
        with col:
            st.markdown(
                f'<div class="metr-card">'
                f'<div class="metr-label">{label}</div>'
                f'<div class="metr-valor">{valor}</div>'
                f'<div class="metr-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _renderizar_card(proj: dict, email: str, idx: int) -> None:
    """Renderiza o card de um projeto com ações."""
    meta = proj.get("meta")
    nome = proj["nome"]
    local = f"{proj['cidade']} / {proj['uf']}" if proj.get("cidade") else "—"
    vgv_str = formatar_brl(proj["vgv_bruto"]) if proj["vgv_bruto"] > 0 else "—"
    lotes_str = f"{proj['total_lotes']} lotes" if proj["total_lotes"] > 0 else "—"

    if meta and meta.get("tir_anual") is not None:
        tir_pct = meta["tir_anual"] * 100
        badge = f'<span class="badge-tir">TIR {tir_pct:.1f}% a.a.</span>'
        calc_info = f"Calculado em {meta.get('calculado_em', '')}"
    else:
        badge = '<span class="badge-sem">Não calculado</span>'
        calc_info = ""

    st.markdown(
        f'<div class="proj-card">'
        f'<div class="proj-nome">{nome}</div>'
        f'<div class="proj-local">📍 {local}</div>'
        f'{badge}'
        f'<div class="proj-vgv">{vgv_str}</div>'
        f'<div class="proj-lotes">{lotes_str}</div>'
        f'<div class="proj-data">💾 Salvo: {proj["ultima_modificacao"]}</div>'
        f'{f"<div class=\'proj-data\'>{calc_info}</div>" if calc_info else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Botoes de acao
    col_a, col_b, col_c = st.columns([2, 1, 1])
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
            "Copiar",
            key=f"btn_dup_{idx}",
            use_container_width=True,
            help="Duplicar projeto",
        ):
            novo_nome = duplicar_projeto_usuario(email, nome)
            if novo_nome:
                st.success(f"Projeto duplicado: {novo_nome}")
                st.rerun()
            else:
                st.error("Não foi possível duplicar.")
    with col_c:
        if st.button(
            "🗑️",
            key=f"btn_del_{idx}",
            use_container_width=True,
            help="Excluir projeto",
        ):
            st.session_state[f"_confirmar_del_{idx}"] = True

    if st.session_state.get(f"_confirmar_del_{idx}"):
        st.warning(f"Excluir **{nome}**? Digite sua senha para confirmar.")
        senha_del = st.text_input(
            "Senha",
            type="password",
            placeholder="••••••••",
            key=f"senha_del_{idx}",
            label_visibility="collapsed",
        )
        ca, cb = st.columns(2)
        with ca:
            if st.button("Excluir definitivamente", key=f"btn_conf_del_{idx}", type="primary"):
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


def renderizar() -> None:
    """Renderiza a pagina inicial (home) do sistema."""
    st.markdown(_CSS_HOME, unsafe_allow_html=True)

    usuario = st.session_state.get("usuario_logado", {})
    email = usuario.get("email", "")
    nome_usuario = usuario.get("nome", "Usuário")

    # ----------------------------------------------------------------
    # HEADER
    # ----------------------------------------------------------------
    col_titulo, col_acoes = st.columns([3, 2])
    with col_titulo:
        st.markdown(
            f'<div class="home-title">📊 Olá, {nome_usuario}!</div>'
            f'<div class="home-sub">Seus projetos de viabilidade de loteamento</div>',
            unsafe_allow_html=True,
        )
    with col_acoes:
        ca, cb, cc = st.columns([2, 2, 1])
        with ca:
            if st.button(
                "➕ Novo Projeto",
                use_container_width=True,
                type="primary",
                key="home_novo",
            ):
                _novo_projeto()
        with cb:
            arquivo = st.file_uploader(
                "Importar JSON",
                type=["json"],
                key="home_upload",
                label_visibility="collapsed",
            )
            if arquivo is not None:
                try:
                    data = json.load(arquivo)
                    projeto = Projeto.model_validate(data)
                    # Salva na pasta do usuario antes de abrir
                    from ...auth import salvar_projeto_usuario
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
                    "📂 Importar JSON",
                    use_container_width=True,
                    key="home_btn_upload_label",
                    disabled=True,
                    help="Clique acima para selecionar um arquivo",
                )
        with cc:
            if st.button("Sair", key="home_sair", use_container_width=True):
                limpar_sessao()
                st.session_state.pop("usuario_logado", None)
                st.session_state.pop("projeto_path_atual", None)
                st.rerun()

    st.markdown("---")

    # ----------------------------------------------------------------
    # METRICAS DA CARTEIRA
    # ----------------------------------------------------------------
    projetos = carregar_projetos_usuario(email)
    _renderizar_metricas(projetos)

    st.markdown("<br>", unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # GRADE DE PROJETOS
    # ----------------------------------------------------------------
    if not projetos:
        st.markdown(
            """
            <div style="text-align:center;padding:60px 20px;color:#6B7280;">
                <div style="font-size:48px;margin-bottom:16px;">📁</div>
                <div style="font-size:16px;font-weight:600;color:#8A8880;margin-bottom:8px;">
                    Nenhum projeto ainda
                </div>
                <div style="font-size:13px;">
                    Clique em <b>➕ Novo Projeto</b> para começar a primeira análise.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div style="font-size:13px;color:#8A8880;margin-bottom:16px;">'
        f'{len(projetos)} projeto(s) encontrado(s)</div>',
        unsafe_allow_html=True,
    )

    # 3 colunas de cards
    COLS = 3
    for row_start in range(0, len(projetos), COLS):
        row = projetos[row_start: row_start + COLS]
        cols = st.columns(COLS)
        for i, (col, proj) in enumerate(zip(cols, row)):
            with col:
                _renderizar_card(proj, email, row_start + i)
        st.markdown("<br>", unsafe_allow_html=True)
