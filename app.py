"""
Aplicativo principal — interface grafica do sistema de viabilidade.

Design renovado (v0.6): tema escuro profissional, navegacao vertical
por modulos na sidebar, header com breadcrumb, cards de KPI estilizados.

Para rodar:
    python -m streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from src.interface.abas import (
    aba1_terreno,
    aba2_receitas,
    aba3_obras,
    aba4_desenvolvimento,
    aba5_impostos,
    aba7_fluxo,
    aba8_dashboard,
    aba_terreno,
    aba_ferramentas,
    aba_cenarios,
    aba_projetos,
    aba_financiamento,
    aba_reajustes,
)
from src.interface.abas import aba_login, aba_home
from src.auth import carregar_sessao
from src.interface.helpers import garantir_projeto_inicial, get_projeto, get_resultado
from src.interface.sidebar import renderizar_sidebar_acoes, renderizar_sidebar_rodape
from src.interface.tema import aplicar_tema
from src.interface.tema_componentes import (
    renderizar_header_principal,
    renderizar_navegacao_modulos_sidebar,
    renderizar_resumo_tempo_real_sidebar,
)
from src.interface.validacoes import status_aba, validar_projeto_completo


st.set_page_config(
    page_title="Altiplano Viabilidade",
    page_icon="assets/favicon.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURACAO DOS MODULOS
# ============================================================

MODULOS = [
    {"numero": 8,  "nome": "Resultado",           "icone": "📊"},
    {"numero": 1,  "nome": "Identificação",       "icone": "📋"},
    {"numero": 9,  "nome": "Aquisição do Terreno","icone": "🏡"},
    {"numero": 3,  "nome": "Custos de Obra",      "icone": "🏗️"},
    {"numero": 2,  "nome": "Receitas",            "icone": "💰"},
    {"numero": 4,  "nome": "Despesas Indiretas",  "icone": "📎"},
    {"numero": 5,  "nome": "Tributação",          "icone": "📑"},
    {"numero": 7,  "nome": "Fluxo de Caixa",      "icone": "💹"},
    {"numero": 10, "nome": "Ferramentas",         "icone": "🔧"},
    {"numero": 11, "nome": "Cenários",            "icone": "🎲"},
    {"numero": 12, "nome": "Projetos",            "icone": "📁"},
    {"numero": 13, "nome": "Financiamento",       "icone": "🏦"},
    {"numero": 14, "nome": "Reajustes",           "icone": "📈"},
]


def main() -> None:
    # 1) Aplicar tema (CSS global)
    aplicar_tema()

    # ================================================================
    # ROTEAMENTO DE TELAS
    # ================================================================

    # Auto-login: restaura sessao salva em disco se existir
    if not st.session_state.get("usuario_logado"):
        sessao = carregar_sessao()
        if sessao:
            st.session_state["usuario_logado"] = sessao
            if "projeto_path_atual" not in st.session_state:
                st.session_state["projeto_path_atual"] = None

    # Tela 1: Login / Cadastro
    if not st.session_state.get("usuario_logado"):
        aba_login.renderizar()
        return

    # Tela 2: Home (biblioteca de projetos) — sem projeto selecionado
    if not st.session_state.get("projeto_path_atual"):
        aba_home.renderizar()
        return

    # ================================================================
    # Tela 3: Aplicativo principal (projeto aberto)
    # ================================================================

    # Restaura sidebar — o CSS das telas de login/home fica em cache no DOM
    # do navegador entre reruns do Streamlit; este snippet cancela o "display:none"
    st.markdown(
        "<style>"
        "section[data-testid='stSidebar'] { display: flex !important; }"
        "</style>",
        unsafe_allow_html=True,
    )

    # D7: atalho Ctrl+Enter → clica no botao Calcular
    import streamlit.components.v1 as _stc
    _stc.html(
        """<script>
(function() {
    if (window.parent._calc_shortcut_attached) return;
    window.parent._calc_shortcut_attached = true;
    window.parent.document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            var btns = Array.from(window.parent.document.querySelectorAll('button'));
            var btn = btns.find(function(b) {
                return b.textContent.trim().indexOf('Calcular') !== -1;
            });
            if (btn) btn.click();
        }
    });
})();
</script>""",
        height=0,
        scrolling=False,
    )

    # 2) Garantir projeto inicial
    garantir_projeto_inicial()

    # Mapa numero_modulo -> indice na lista MODULOS (usado pelas pendencias clicareis)
    st.session_state["_modulo_numero_para_idx"] = {m["numero"]: i for i, m in enumerate(MODULOS)}

    # 3) Calcular pendencias para mostrar status nos modulos
    projeto = get_projeto()
    resultado = get_resultado()
    pendencias = validar_projeto_completo(projeto)

    # 4) Renderizar sidebar (acoes + modulos + resumo)
    renderizar_sidebar_acoes()

    # Status de cada modulo
    modulos_com_status = []
    for m in MODULOS:
        n = m["numero"]
        if n in (8, 9, 10, 11, 12, 13, 14):
            status = "neutro"
        else:
            stat = status_aba(pendencias, n)
            status = {"✅": "ok", "⚠️": "warn", "❌": "err"}.get(stat, "neutro")
        modulos_com_status.append({**m, "status": status})

    # Indice do modulo atual (na session_state)
    if "modulo_atual_idx" not in st.session_state:
        st.session_state["modulo_atual_idx"] = 0

    idx_selecionado = renderizar_navegacao_modulos_sidebar(
        modulos_com_status, st.session_state["modulo_atual_idx"]
    )
    if idx_selecionado is None:
        idx_selecionado = 0
    st.session_state["modulo_atual_idx"] = idx_selecionado

    # 5) Resumo em tempo real no rodape da sidebar
    renderizar_resumo_tempo_real_sidebar(projeto, resultado)

    # 5b) Acoes do projeto + historico (rodape, abaixo do menu)
    renderizar_sidebar_rodape()

    # D8: modo apresentacao — sidebar oculta, apenas resultados
    if st.session_state.get("modo_apresentacao", False):
        st.markdown(
            "<style>"
            "section[data-testid='stSidebar'] { display: none !important; }"
            ".main .block-container { max-width: 100% !important; "
            "padding-left: 3rem !important; padding-right: 3rem !important; }"
            "</style>",
            unsafe_allow_html=True,
        )
        col_nome, col_sair = st.columns([4, 1])
        with col_nome:
            st.markdown(f"## {projeto.terreno.info.nome}")
            st.caption(
                f"Modo Apresentacao — "
                f"{projeto.terreno.info.cidade}/{projeto.terreno.info.uf}"
            )
        with col_sair:
            st.markdown('<div style="padding-top:24px;"></div>', unsafe_allow_html=True)
            if st.button("✕ Sair", use_container_width=True, key="btn_sair_apres"):
                st.session_state["modo_apresentacao"] = False
                st.rerun()
        aba8_dashboard.renderizar()
        return

    # 6) Header principal (breadcrumb)
    modulo_ativo = MODULOS[idx_selecionado]
    renderizar_header_principal(projeto, modulo_ativo["nome"])

    # 7) Renderizar o modulo selecionado
    renderizadores = {
        8:  aba8_dashboard.renderizar,
        1:  aba1_terreno.renderizar,
        9:  aba_terreno.renderizar,
        2:  aba2_receitas.renderizar,
        3:  aba3_obras.renderizar,
        4:  aba4_desenvolvimento.renderizar,
        5:  aba5_impostos.renderizar,
        7:  aba7_fluxo.renderizar,
        10: aba_ferramentas.renderizar,
        11: aba_cenarios.renderizar,
        12: aba_projetos.renderizar,
        13: aba_financiamento.renderizar,
        14: aba_reajustes.renderizar,
    }
    renderizadores[modulo_ativo["numero"]]()


if __name__ == "__main__":
    main()
