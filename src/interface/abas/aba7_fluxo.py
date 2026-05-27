"""
Aba 7 — Fluxo de Caixa.

Fluxo detalhado do projeto.
"""

from __future__ import annotations

import streamlit as st

from ..helpers import (
    btn_proximo_modulo,
    cabecalho_aba,
    get_resultado,
    renderizar_calcular_cta,
)


def renderizar() -> None:
    cabecalho_aba(
        7,
        "Fluxo de Caixa",
        "Fluxo detalhado do projeto.",
    )

    resultado = get_resultado()
    if resultado is None:
        renderizar_calcular_cta()
        return

    from .aba8_dashboard import _tabela_fluxo_mensal
    _tabela_fluxo_mensal(resultado.fluxo_caixa)

    btn_proximo_modulo("Ferramentas")


def sincronizar_aba7() -> None:
    """Chamado pelo sidebar antes de Calcular. TMA configurado na Aba 1."""
    pass
