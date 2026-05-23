"""
Modelos auxiliares: aquisicao do terreno e parametros financeiros.

Aquisicao do terreno e uma despesa importante mas nao se encaixa em nenhuma
das 8 abas: ela aparece na Aba 1 (info) mas o pagamento entra no fluxo de
caixa (Aba 7). Por isso modelamos separadamente.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConfigFinanciamento(BaseModel):
    """
    Financiamento bancario da producao (A1 — saque automatico).

    O sistema identifica os meses de caixa negativo e saca automaticamente
    da linha de credito. Amortiza quando o caixa volta ao positivo (apos carencia).
    Retrocompat: ativo=False por default.
    """

    ativo: bool = False

    tipo: Literal["cce", "sfh", "sfi", "cri"] = "cce"

    taxa_juros_am: float = Field(
        default=1.5, ge=0.0, le=10.0,
        description="Taxa de juros mensal % a.m. (ex.: 1.5 = 1,5% a.m.)",
    )
    limite_credito_valor: float = Field(
        default=0.0, ge=0.0,
        description="Limite da linha em R$ (0 = sem limite definido)",
    )
    periodo_carencia_meses: int = Field(
        default=0, ge=0,
        description="Meses iniciais sem amortizacao de principal",
    )
    comissao_abertura_pct: float = Field(
        default=0.5, ge=0.0, le=5.0,
        description="Comissao de abertura % sobre o limite",
    )
    iof_pct: float = Field(
        default=0.38, ge=0.0, le=5.0,
        description="IOF sobre cada saque %",
    )
    caixa_minimo: float = Field(
        default=0.0, ge=0.0,
        description=(
            "Reserva de caixa minimo que o sistema mantem sempre disponivel. "
            "O banco saca quando o caixa cair abaixo desse valor (nao so quando for negativo). "
            "O sistema so amortiza o que exceder esse valor. "
            "Ex.: 500000 = manter sempre R$ 500k em caixa. Retrocompat: 0 = comportamento antigo."
        ),
    )


class AquisicaoTerreno(BaseModel):
    """
    Aquisicao do terreno (gleba).

    Forma de pagamento:
    - 'a_vista': valor inteiro no mes_pagamento
    - 'parcelado': N parcelas iguais a partir do mes_inicio
    - 'sem_desembolso': terreno ja pertencia ao empreendedor (nao gera saida de caixa,
      mas o valor ainda entra no calculo de margem como custo)
    """

    valor_total: float = Field(..., gt=0)
    forma_pagamento: Literal["a_vista", "parcelado", "sem_desembolso", "customizado"] = "a_vista"

    mes_pagamento: int = Field(default=0, ge=0)  # so para a_vista
    mes_inicio_parcelas: int = Field(default=0, ge=0)
    qtd_parcelas: int = Field(default=1, ge=1)

    # Para forma 'customizado': distribuicao mensal livre (lista de percentuais, soma=100)
    fluxo_mes_inicio: int = Field(default=0, ge=0)
    fluxo_percentuais: list[float] = Field(default_factory=list)

    custo_cartorio: float = Field(default=0, ge=0, description="Escritura e registro (R$)")
    mes_pagamento_cartorio: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _valida(self) -> "AquisicaoTerreno":
        if self.forma_pagamento == "parcelado" and self.qtd_parcelas < 2:
            raise ValueError("Forma 'parcelado' exige qtd_parcelas >= 2")
        return self


class ParametrosFinanceiros(BaseModel):
    """
    Parametros financeiros gerais (Aba 7 — Fluxo de Caixa).
    """

    tma_anual: float = Field(
        ..., ge=0, description="Taxa Minima de Atratividade (% a.a., ex.: 15 = 15%)"
    )

    @property
    def tma_mensal(self) -> float:
        """TMA convertida para taxa mensal equivalente."""
        return (1 + self.tma_anual / 100) ** (1 / 12) - 1
