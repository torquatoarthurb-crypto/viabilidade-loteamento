"""
Barra lateral da interface — refatorada para o design escuro/profissional.

Estrutura:
1. Topo: link "Todos os projetos" + nome
2. ACOES: Novo/Abrir/Salvar/Calcular/Exportar (em expander para nao poluir)
3. MODULOS: navegacao vertical (renderizada pelo app.py)
4. RESUMO EM TEMPO REAL: rodape (renderizado pelo app.py)

A funcao expoe apenas `renderizar_sidebar_acoes`.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from ..auth import limpar_sessao
from ..engine import calcular_fluxo_caixa
from ..io_projeto import exportar_para_excel
from ..io_projeto.exportar_html import gerar_relatorio_html
from ..modelos import Projeto, projeto_novo
from .helpers import (
    get_projeto,
    get_resultado,
    invalidar_resultado,
    limpar_cache_inputs_brl,
    set_projeto,
    set_resultado,
)
from .tema_componentes import renderizar_logo_sidebar


def _projeto_hash(projeto) -> str:
    """D2: Hash MD5 curto do projeto para detectar mudancas desde o ultimo calculo."""
    return hashlib.md5(projeto.model_dump_json().encode()).hexdigest()[:12]


def _limpar_estado_abas() -> None:
    """Limpa caches de UI das abas para forcar recarga apos novo/abrir projeto."""
    chaves_para_limpar = [
        "aba2_lista_fluxos",
        "aba2_curva_mensal",
        "aba3_lista_etapas",
        "aba3_resumido_distrib",
        "aba4_lista_despesas",
        "aba_terreno_fluxo_distrib",
        # Ferramentas analiticas (resultados ficam obsoletos ao trocar projeto)
        "_sens_cache",
        "_mc_resultados",
        "historico_versoes",
    ]
    for chave in chaves_para_limpar:
        if chave in st.session_state:
            del st.session_state[chave]


def renderizar_sidebar_acoes() -> None:
    """Topo da sidebar: logo, usuario, projeto, botao calcular e aviso de resultado."""
    projeto = get_projeto()
    usuario = st.session_state.get("usuario_logado", {})

    # Logo
    renderizar_logo_sidebar()

    # Botao "Meus Projetos" e usuario logado
    if usuario:
        nome_usuario = usuario.get("nome", "Usuário")
        col_u, col_sair = st.sidebar.columns([3, 1])
        with col_u:
            if st.button(
                "← Meus Projetos",
                key="btn_voltar_home",
                use_container_width=True,
                help="Voltar para a lista de projetos",
            ):
                st.session_state["projeto_path_atual"] = None
                st.rerun()
        with col_sair:
            if st.button("Sair", key="btn_sair_sidebar", use_container_width=True):
                limpar_sessao()
                st.session_state.pop("usuario_logado", None)
                st.session_state.pop("projeto_path_atual", None)
                st.rerun()
        st.sidebar.markdown(
            f'<div style="padding:2px 14px 8px;font-size:11px;color:#6B7280;">'
            f'👤 {nome_usuario}</div>',
            unsafe_allow_html=True,
        )

    # Nome do projeto
    st.sidebar.markdown(
        f'<div style="padding:10px 14px 2px;font-size:13px;font-weight:600;'
        f'color:#F5F3EE;">{projeto.terreno.info.nome}</div>'
        f'<div style="padding:0 14px 10px;font-size:11px;color:#8A8880;">'
        f'{projeto.terreno.info.cidade} · {projeto.terreno.info.uf}</div>',
        unsafe_allow_html=True,
    )

    # Botao Calcular — sempre visivel, fora do expander
    if st.sidebar.button(
        "🧮 Calcular Viabilidade",
        type="primary",
        use_container_width=True,
        key="btn_calcular_topo",
        help="⌨️ Ctrl+Enter",
    ):
        try:
            from .abas.aba2_receitas import sincronizar_aba2
            from .abas.aba3_obras import sincronizar_aba3
            from .abas.aba4_desenvolvimento import sincronizar_aba4
            sincronizar_aba2()
            sincronizar_aba3()
            sincronizar_aba4()
            projeto_atual = get_projeto()
            h = _projeto_hash(projeto_atual)
            if get_resultado() is not None and h == st.session_state.get("_hash_ultimo_calc"):
                st.sidebar.success("✓ Sem mudancas.")
            else:
                resultado = calcular_fluxo_caixa(projeto_atual)
                set_resultado(resultado)
                _adicionar_historico(resultado, projeto_atual)
                st.session_state["_hash_ultimo_calc"] = h
                # Salva meta de indicadores para exibir na home
                usuario_calc = st.session_state.get("usuario_logado")
                if usuario_calc:
                    try:
                        from ..auth import salvar_meta_projeto
                        salvar_meta_projeto(
                            usuario_calc["email"],
                            projeto_atual.terreno.info.nome,
                            resultado,
                        )
                    except Exception:
                        pass
        except Exception as e:
            st.sidebar.error(f"⚠️ {e}")

    # Aviso quando sem resultado
    if get_resultado() is None:
        st.sidebar.markdown(
            '<div style="background:rgba(30,58,138,0.12);border:0.5px solid rgba(30,58,138,0.35);'
            'padding:7px 12px;margin:4px 10px;border-radius:6px;font-size:11px;'
            'color:#93C5FD;">⚠️ Calcule para ver os resultados</div>',
            unsafe_allow_html=True,
        )

    # D1: executar auto-calc se habilitado
    if st.session_state.get("_auto_calc", False):
        _check_auto_calc()


def renderizar_sidebar_rodape() -> None:
    """Rodape da sidebar: acoes do projeto + apresentacao + historico."""
    projeto = get_projeto()
    resultado = get_resultado()
    nome_padrao = (
        projeto.terreno.info.nome.lower()
        .replace(" ", "_")
        .replace("/", "_")
    )

    st.sidebar.markdown(
        '<div style="border-top:0.5px solid #1A1A1A;margin:8px 0 0;"></div>',
        unsafe_allow_html=True,
    )

    with st.sidebar.expander("⚙️ Acoes do projeto", expanded=False):
        if st.button("🆕 Novo projeto", use_container_width=True, key="btn_novo"):
            set_projeto(projeto_novo())
            st.session_state["nome_arquivo_atual"] = None
            st.session_state["projeto_path_atual"] = "__novo__"
            _limpar_estado_abas()
            limpar_cache_inputs_brl()
            st.rerun()

        arquivo = st.file_uploader(
            "📂 Abrir (.json)",
            type=["json"],
            label_visibility="visible",
            key="abrir_arquivo",
        )
        if arquivo is not None:
            try:
                data = json.load(arquivo)
                novo = Projeto.model_validate(data)
                set_projeto(novo)
                st.session_state["nome_arquivo_atual"] = arquivo.name
                _limpar_estado_abas()
                limpar_cache_inputs_brl()
                st.success("✅ Carregado")
            except Exception as e:
                st.error(f"⚠️ Erro: {e}")

        # Salvar na pasta do usuario (principal)
        usuario = st.session_state.get("usuario_logado")
        if usuario:
            if st.button(
                "💾 Salvar Projeto",
                use_container_width=True,
                key="btn_salvar_proj",
                type="primary",
                help="Salva o projeto na sua conta. Aparecerá em 'Meus Projetos'.",
            ):
                try:
                    from ..auth import salvar_projeto_usuario
                    caminho = salvar_projeto_usuario(usuario["email"], projeto)
                    st.session_state["projeto_path_atual"] = str(caminho)
                    st.success("✅ Projeto salvo!")
                except Exception as e:
                    st.error(f"⚠️ Erro ao salvar: {e}")

        # Download JSON (secundario)
        json_str = projeto.model_dump_json(indent=2)
        st.download_button(
            "📥 Baixar JSON",
            data=json_str,
            file_name=f"{nome_padrao}.json",
            mime="application/json",
            use_container_width=True,
            help="Baixa o arquivo JSON no seu computador.",
        )

        st.markdown("---")

        auto_calc = st.checkbox(
            "⚡ Auto-calcular",
            value=st.session_state.get("_auto_calc", False),
            key="cb_auto_calc",
            help="Recalcula automaticamente quando o projeto muda.",
        )
        st.session_state["_auto_calc"] = auto_calc

        if resultado is not None:
            st.markdown("---")
            try:
                tmp_dir = Path(tempfile.gettempdir())
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                arquivo_xlsx = tmp_dir / f"viabilidade_{nome_padrao}_{timestamp}.xlsx"
                exportar_para_excel(projeto, resultado, arquivo_xlsx)
                with arquivo_xlsx.open("rb") as f:
                    st.download_button(
                        "📊 Baixar Excel",
                        data=f.read(),
                        file_name=arquivo_xlsx.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"⚠️ Erro: {e}")

            try:
                html_str = gerar_relatorio_html(projeto, resultado)
                st.download_button(
                    "🖨️ Relatorio PDF (imprimir)",
                    data=html_str.encode("utf-8"),
                    file_name=f"relatorio_{nome_padrao}.html",
                    mime="text/html",
                    use_container_width=True,
                    help="Baixa HTML. Abra no navegador e pressione Ctrl+P para salvar como PDF.",
                )
            except Exception as e:
                st.error(f"⚠️ Erro no relatorio: {e}")

    # D8: modo apresentacao
    if resultado is not None:
        if st.sidebar.button(
            "📋 Apresentacao",
            use_container_width=True,
            key="btn_apresentacao",
            help="Esconde a sidebar e exibe os resultados em tela cheia",
        ):
            st.session_state["modo_apresentacao"] = True
            st.rerun()

    # Historico de versoes (C14)
    _renderizar_historico()


# =====================================================================
# D1 — AUTO-CALCULAR
# =====================================================================

def _check_auto_calc() -> None:
    """D1: Recalcula silenciosamente se o projeto mudou desde o ultimo calculo."""
    try:
        from .abas.aba2_receitas import sincronizar_aba2
        from .abas.aba3_obras import sincronizar_aba3
        from .abas.aba4_desenvolvimento import sincronizar_aba4
        sincronizar_aba2()
        sincronizar_aba3()
        sincronizar_aba4()
        projeto = get_projeto()
        h = _projeto_hash(projeto)
        if h != st.session_state.get("_hash_ultimo_calc"):
            resultado = calcular_fluxo_caixa(projeto)
            set_resultado(resultado)
            _adicionar_historico(resultado, projeto)
            st.session_state["_hash_ultimo_calc"] = h
    except Exception:
        pass


# =====================================================================
# C14 — HISTORICO DE VERSOES
# =====================================================================

def _adicionar_historico(resultado, projeto) -> None:
    """Salva snapshot apos cada calculo (C14)."""
    if "historico_versoes" not in st.session_state:
        st.session_state["historico_versoes"] = []

    ind = resultado.indicadores
    r = resultado.resumo
    historico = st.session_state["historico_versoes"]

    # UX-14: detectar o que mudou em relacao ao snapshot anterior
    mudanca = ""
    if historico:
        prev = historico[-1]
        prev_tir = prev.get("tir_anual")
        cur_tir = ind.get("tir_anual")
        prev_custo = prev.get("custo_total", 0)
        cur_custo = r.get("total_saidas", 0)
        prev_vgv = prev.get("vgv_vendavel", 0)
        cur_vgv = r.get("vgv_vendavel", 0)

        if cur_tir is not None and prev_tir is not None:
            delta_tir = (cur_tir - prev_tir) * 100
            if abs(delta_tir) >= 0.5:
                sinal = "+" if delta_tir > 0 else ""
                mudanca = f"TIR {sinal}{delta_tir:.1f} p.p."
        if not mudanca and abs(cur_custo - prev_custo) > 10_000:
            delta_k = (cur_custo - prev_custo) / 1_000
            sinal = "+" if delta_k > 0 else ""
            mudanca = f"Custo {sinal}{delta_k:.0f}k"
        if not mudanca and abs(cur_vgv - prev_vgv) > 10_000:
            delta_k = (cur_vgv - prev_vgv) / 1_000
            sinal = "+" if delta_k > 0 else ""
            mudanca = f"VGV {sinal}{delta_k:.0f}k"

    historico.append({
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "nome": projeto.terreno.info.nome,
        "tir_anual": ind.get("tir_anual"),
        "vpl": ind.get("vpl"),
        "lucro": r.get("lucro_liquido"),
        "custo_total": r.get("total_saidas", 0),
        "vgv_vendavel": r.get("vgv_vendavel", 0),
        "mudanca": mudanca,
        "projeto_json": projeto.model_dump_json(),
    })
    if len(historico) > 20:
        st.session_state["historico_versoes"] = historico[-20:]


def _renderizar_historico() -> None:
    """Exibe o historico de calculos na sidebar (C14)."""
    historico = st.session_state.get("historico_versoes", [])
    if not historico:
        return

    with st.sidebar.expander(f"📋 Historico ({len(historico)} calculos)", expanded=False):
        for i, v in enumerate(reversed(historico)):
            real_idx = len(historico) - 1 - i
            tir_str = f"{v['tir_anual'] * 100:.1f}%" if v.get("tir_anual") else "—"
            mudanca = v.get("mudanca", "")
            mudanca_html = (
                f'<div style="font-size:10px;color:#93C5FD">{mudanca}</div>'
                if mudanca else ""
            )
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f'<div style="font-size:11px;color:#F5F3EE">{v["timestamp"]}</div>'
                    f'<div style="font-size:10px;color:#8A8880">TIR: {tir_str}</div>'
                    f'{mudanca_html}',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("↩", key=f"btn_hist_{real_idx}",
                             help="Restaurar este estado do projeto"):
                    _restaurar_historico(real_idx)


def _restaurar_historico(idx: int) -> None:
    """Restaura o projeto para um estado anterior do historico."""
    historico = st.session_state.get("historico_versoes", [])
    if idx >= len(historico):
        return
    try:
        v = historico[idx]
        novo_projeto = Projeto.model_validate_json(v["projeto_json"])
        set_projeto(novo_projeto)
        invalidar_resultado()
        limpar_cache_inputs_brl()
        for chave in [
            "aba2_lista_fluxos", "aba2_curva_mensal", "aba3_lista_etapas",
            "aba3_resumido_distrib", "aba4_lista_despesas", "aba_terreno_fluxo_distrib",
        ]:
            if chave in st.session_state:
                del st.session_state[chave]
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao restaurar: {e}")
