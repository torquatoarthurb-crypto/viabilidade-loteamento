"""
Modelo principal Projeto: agrega todas as abas do programa.

Esta classe e o "objeto raiz" do sistema. Quando voce carrega um arquivo .json
de projeto, ele vira uma instancia de Projeto. A engine de calculo recebe um
Projeto e produz o fluxo de caixa.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .desenvolvimento import Aba4Desenvolvimento
from .financeiro import AquisicaoTerreno, ConfigFinanciamento, ParametrosFinanceiros
from .obras import Aba3Obras
from .receitas import Aba2Receitas
from .reajustes import ConfigReajustes
from .terreno import Aba1Terreno
from .tributos import Aba5Impostos


class Projeto(BaseModel):
    """Projeto completo de viabilidade de loteamento."""

    # Aba 1
    terreno: Aba1Terreno

    # Aquisicao (informada na Aba 1 mas tratada separado no fluxo de caixa)
    aquisicao: AquisicaoTerreno

    # Aba 2
    receitas: Aba2Receitas

    # Aba 3
    obras: Aba3Obras

    # Aba 4
    desenvolvimento: Aba4Desenvolvimento

    # Aba 5
    impostos: Aba5Impostos

    # Aba 7 (parametros)
    parametros: ParametrosFinanceiros

    # Modulo 13 — Financiamento bancario (opcional, ativo=False por default)
    financiamento: ConfigFinanciamento = Field(default_factory=ConfigFinanciamento)

    # Modulo 14 — Reajustes monetarios (opcional, ativo=False por default)
    reajustes: ConfigReajustes = Field(default_factory=ConfigReajustes)
