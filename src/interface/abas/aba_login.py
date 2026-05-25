"""
Tela de Login e Cadastro — layout dois paineis (hero + form).

Painel esquerdo: identidade Altiplano sobre fundo Stone 900.
Painel direito: formularios de login e cadastro nativos Streamlit.
"""

from __future__ import annotations

import base64
import streamlit as st

from ...auth import autenticar, cadastrar, salvar_sessao


# =====================================================================
# Logo como data URI — st.markdown não renderiza SVG inline confiável
# =====================================================================
_LOGO_SVG = (
    '<svg width="44" height="36" viewBox="0 0 64 52" '
    'xmlns="http://www.w3.org/2000/svg" fill="none">'
    '<ellipse cx="32" cy="26" rx="29" ry="13" stroke="#F5F3EE" '
    'stroke-width="1.2" opacity="0.18"/>'
    '<ellipse cx="32" cy="26" rx="21" ry="9" stroke="#F5F3EE" '
    'stroke-width="1.5" opacity="0.38"/>'
    '<ellipse cx="32" cy="26" rx="13" ry="5.5" stroke="#F5F3EE" '
    'stroke-width="1.9" opacity="0.65"/>'
    '<ellipse cx="32" cy="26" rx="5.5" ry="2.2" fill="#B07D2E"/>'
    '</svg>'
)
_LOGO_IMG = (
    '<img src="data:image/svg+xml;base64,'
    + base64.b64encode(_LOGO_SVG.encode()).decode()
    + '" width="44" height="36" style="display:block;">'
)

_CSS_LOGIN = """
<style>
/* Oculta sidebar na tela de login */
section[data-testid="stSidebar"] { display: none !important; }

.main .block-container {
    max-width: 860px !important;
    padding-top: 64px !important;
    padding-bottom: 64px !important;
    margin: 0 auto !important;
}

/* ---- Painel hero (esquerdo) ---- */
.login-hero {
    background: #1A1916;
    border-radius: 14px;
    padding: 36px 32px 28px;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    height: 100%;
}

.login-hero-logo {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 24px;
}

.login-hero-wordmark {
    font-family: 'DM Serif Display', serif;
    font-size: 21px;
    color: #F5F3EE;
    line-height: 1.1;
}

.login-hero-wordmark small {
    display: block;
    font-family: 'Inter', sans-serif;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #6B6860;
    margin-top: 4px;
}

.login-hero h2 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 24px !important;
    font-weight: 400 !important;
    color: #F5F3EE !important;
    line-height: 1.35 !important;
    margin: 0 0 10px !important;
    padding: 0 !important;
}

.login-hero-sub {
    font-size: 12.5px;
    color: #8A8880;
    line-height: 1.6;
    margin-bottom: 20px;
}

.login-bullet {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 9px;
}

.login-bullet-dot {
    color: #B07D2E;
    font-size: 13px;
    flex-shrink: 0;
    margin-top: 2px;
}

.login-bullet-text {
    font-size: 12.5px;
    color: #C4C1B8;
    line-height: 1.45;
}

.login-hero-spacer { flex: 1; }

.login-hero-footer {
    font-size: 11px;
    color: #3A3835;
    border-top: 0.5px solid #2A2825;
    padding-top: 14px;
    margin-top: 20px;
}

/* ---- Painel form (direito) ---- */
/* O div wrapper foi removido — cada st.markdown vira seu próprio bloco no DOM  */
/* Estilizamos a coluna diretamente via seletor Streamlit                         */
[data-testid="stColumn"]:nth-child(2) > div {
    background: #FFFFFF;
    border: 0.5px solid #ECEAE4;
    border-radius: 14px;
    padding: 32px 24px 24px !important;
    box-shadow: 0 2px 12px rgba(26,25,22,0.05);
    box-sizing: border-box;
}

.login-form-header {
    padding-bottom: 16px;
}

.login-form-title {
    font-family: 'DM Serif Display', serif;
    font-size: 20px;
    color: #1A1916;
    margin: 0 0 4px;
}

.login-form-sub {
    font-size: 12px;
    color: #8A8880;
    margin: 0;
}

.login-privacy {
    text-align: center;
    color: #8A8880;
    font-size: 11px;
    margin-top: 16px;
    line-height: 1.6;
}

/* Ajustes de tab na tela de login */
.main .stTabs [data-baseweb="tab"] {
    font-size: 13px !important;
    padding: 6px 14px !important;
}
</style>
"""

# =====================================================================
# HTML do painel hero (sem estado — renderizado apenas uma vez)
# =====================================================================
_HTML_HERO = (
    f'<div class="login-hero">'
    f'<div>'
    f'<div class="login-hero-logo">'
    f'{_LOGO_IMG}'
    f'<div class="login-hero-wordmark">'
    f'Altiplano'
    f'<small>Viabilidade</small>'
    f'</div>'
    f'</div>'
    f'<h2>Estruture negócios imobiliários com embasamento técnico.</h2>'
    f'<p class="login-hero-sub">'
    f'Plataforma de viabilidade econômico-financeira para '
    f'incorporação e loteamento.'
    f'</p>'
    f'<div class="login-bullet">'
    f'<span class="login-bullet-dot">✓</span>'
    f'<span class="login-bullet-text">'
    f'Modelagem completa: TIR, VPL, payback, exposição de caixa e financiamento'
    f'</span>'
    f'</div>'
    f'<div class="login-bullet">'
    f'<span class="login-bullet-dot">✓</span>'
    f'<span class="login-bullet-text">'
    f'Comparador de cenários e análise de sensibilidade'
    f'</span>'
    f'</div>'
    f'<div class="login-bullet">'
    f'<span class="login-bullet-dot">✓</span>'
    f'<span class="login-bullet-text">'
    f'Relatório executivo em PDF para apresentação ao comitê'
    f'</span>'
    f'</div>'
    f'</div>'
    f'<div class="login-hero-spacer"></div>'
    f'<div class="login-hero-footer">'
    f'Altiplano Real Estate Advisory &nbsp;·&nbsp; 2026'
    f'</div>'
    f'</div>'
)


def renderizar() -> None:
    """Renderiza a tela de login/cadastro em layout dois paineis."""
    st.markdown(_CSS_LOGIN, unsafe_allow_html=True)

    col_hero, col_form = st.columns([1, 1], gap="large")

    # ----------------------------------------------------------------
    # Painel esquerdo — hero
    # ----------------------------------------------------------------
    with col_hero:
        st.markdown(_HTML_HERO, unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Painel direito — formularios
    # ----------------------------------------------------------------
    with col_form:
        st.markdown(
            '<div class="login-form-header">'
            '<div class="login-form-title">Bem-vindo de volta</div>'
            '<div class="login-form-sub">Acesse sua conta ou crie uma nova.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        tab_entrar, tab_cadastrar = st.tabs(["  Entrar  ", "  Criar conta  "])

        # ============================================================
        # ABA ENTRAR
        # ============================================================
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

        # ============================================================
        # ABA CRIAR CONTA
        # ============================================================
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

        # Nota de privacidade
        st.markdown(
            '<div class="login-privacy">'
            '🔒 Seus dados ficam armazenados localmente.<br>'
            'A Altiplano não acessa informações dos seus projetos.'
            '</div>',
            unsafe_allow_html=True,
        )
