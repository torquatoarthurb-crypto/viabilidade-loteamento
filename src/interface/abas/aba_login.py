"""
Tela de Login e Cadastro.

Exibida quando o usuario nao esta autenticado.
Design fullscreen sem sidebar, alinhado ao tema escuro do sistema.
"""

from __future__ import annotations

import streamlit as st

from ...auth import autenticar, cadastrar, salvar_sessao


_CSS_LOGIN = """
<style>
/* Oculta sidebar na tela de login */
section[data-testid="stSidebar"] { display: none !important; }
.main .block-container {
    max-width: 480px !important;
    padding-top: 60px !important;
    margin: 0 auto !important;
}

/* Card central */
.login-card {
    background: var(--bg-card, #1A1E27);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 40px 36px 32px;
    margin: 0 auto;
}

/* Logo / titulo */
.login-logo {
    text-align: center;
    margin-bottom: 32px;
}
.login-logo .icone {
    font-size: 48px;
    display: block;
    margin-bottom: 8px;
}
.login-logo h1 {
    font-size: 20px;
    font-weight: 700;
    color: #F5F3EE;
    margin: 0 0 4px;
}
.login-logo p {
    font-size: 13px;
    color: #8A8880;
    margin: 0;
}
</style>
"""


def _get_tab() -> str:
    return st.session_state.get("_login_tab", "entrar")


def renderizar() -> None:
    """Renderiza a tela de login/cadastro."""
    st.markdown(_CSS_LOGIN, unsafe_allow_html=True)

    # Logo e titulo
    st.markdown(
        """
        <div class="login-logo">
            <span class="icone">📊</span>
            <h1>Viabilidade de Loteamento</h1>
            <p>Sistema profissional de análise econômica</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_entrar, tab_cadastrar = st.tabs(["🔑  Entrar", "✍️  Cadastrar-se"])

    # ================================================================
    # ABA ENTRAR
    # ================================================================
    with tab_entrar:
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("form_login", clear_on_submit=False):
            email = st.text_input(
                "E-mail",
                placeholder="seu@email.com",
                key="login_email",
            )
            senha = st.text_input(
                "Senha",
                type="password",
                placeholder="••••••••",
                key="login_senha",
            )
            manter = st.checkbox(
                "Manter conectado neste computador",
                value=True,
                key="login_manter",
            )
            st.markdown("<br>", unsafe_allow_html=True)
            entrar = st.form_submit_button(
                "Entrar →",
                type="primary",
                use_container_width=True,
            )

        if entrar:
            if not email or not senha:
                st.error("Preencha e-mail e senha.")
            else:
                ok, msg, dados = autenticar(email, senha)
                if ok:
                    st.session_state["usuario_logado"] = dados
                    st.session_state["projeto_path_atual"] = None
                    if st.session_state.get("login_manter", True):
                        salvar_sessao(dados)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ================================================================
    # ABA CADASTRAR
    # ================================================================
    with tab_cadastrar:
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("form_cadastro", clear_on_submit=True):
            nome = st.text_input(
                "Nome completo",
                placeholder="João Silva",
                key="cad_nome",
            )
            email_cad = st.text_input(
                "E-mail",
                placeholder="seu@email.com",
                key="cad_email",
            )
            senha_cad = st.text_input(
                "Senha (mínimo 6 caracteres)",
                type="password",
                placeholder="••••••••",
                key="cad_senha",
            )
            senha_confirm = st.text_input(
                "Confirmar senha",
                type="password",
                placeholder="••••••••",
                key="cad_senha2",
            )
            st.markdown("<br>", unsafe_allow_html=True)
            cadastrar_btn = st.form_submit_button(
                "Criar conta →",
                type="primary",
                use_container_width=True,
            )

        if cadastrar_btn:
            if not all([nome, email_cad, senha_cad, senha_confirm]):
                st.error("Preencha todos os campos.")
            elif senha_cad != senha_confirm:
                st.error("As senhas não coincidem.")
            else:
                ok, msg = cadastrar(email_cad, nome, senha_cad)
                if ok:
                    st.success(msg)
                    st.info("Agora faça login na aba **Entrar**.")
                else:
                    st.error(msg)

    # Rodape
    st.markdown(
        "<br><div style='text-align:center;color:#4A4845;font-size:11px;'>"
        "Todos os dados ficam salvos localmente no seu computador."
        "</div>",
        unsafe_allow_html=True,
    )
