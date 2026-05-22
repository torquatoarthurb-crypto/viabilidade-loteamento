"""
Modelos de dados da Aba 5 — Impostos, Comissoes e Permuta Financeira.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Tributos(BaseModel):
    """
    Tributos sobre a receita.

    Modos:
    - 'lucro_presumido': aplica aliquota_efetiva (% sobre receita bruta).
      Valor padrao tipico: 6.73%
    - 'lucro_real': preenche cada tributo separado e a engine soma
    """

    regime: Literal["lucro_presumido", "lucro_real"] = "lucro_presumido"
    aliquota_efetiva: float = Field(default=6.73, ge=0, description="% sobre receita")

    # Usado se regime = lucro_real
    irpj: float = Field(default=0, ge=0, description="% IRPJ sobre receita")
    csll: float = Field(default=0, ge=0, description="% CSLL sobre receita")
    pis: float = Field(default=0, ge=0, description="% PIS sobre receita")
    cofins: float = Field(default=0, ge=0, description="% COFINS sobre receita")

    regime_apuracao: Literal["caixa", "competencia"] = Field(
        default="caixa",
        description="Caixa: imposto sobre o que foi recebido. Competencia: sobre o que foi vendido.",
    )

    @property
    def aliquota_total(self) -> float:
        """Soma das aliquotas que incidem sobre a receita."""
        if self.regime == "lucro_presumido":
            return self.aliquota_efetiva
        return self.irpj + self.csll + self.pis + self.cofins


class ComissaoVenda(BaseModel):
    """
    Comissao de corretagem.

    Modos:
    - 'sobre_venda': pago integralmente no mes da venda
    - 'sobre_recebimento': pago proporcionalmente conforme cada parcela e recebida
    - 'misto': X% no ato da venda, (100-X)% diluido nas N primeiras parcelas
    """

    percentual_vgv: float = Field(..., ge=0, le=20, description="% comissao sobre VGV")
    modo_pagamento: Literal["sobre_venda", "sobre_recebimento", "misto"] = "sobre_venda"

    # Para modo 'misto'
    misto_percentual_no_ato: float = Field(default=50, ge=0, le=100)
    misto_qtd_parcelas: int = Field(default=6, ge=1)


class DescontosPermuta(BaseModel):
    """Percentuais deduzidos da receita bruta antes de calcular a base da permuta financeira."""

    impostos: float = Field(default=0.0, ge=0)
    comissao: float = Field(default=0.0, ge=0)
    marketing: float = Field(default=0.0, ge=0)
    gestao_carteira: float = Field(default=0.0, ge=0)
    outros: float = Field(default=0.0, ge=0)

    @property
    def total(self) -> float:
        return self.impostos + self.comissao + self.marketing + self.gestao_carteira + self.outros


class RetencaoPermuta(BaseModel):
    """Fluxo personalizado: retencao por N meses + quitacao corrigida posterior."""

    meses_retencao: int = Field(default=6, ge=1)
    percentual_retencao: float = Field(default=50.0, ge=0, le=100)
    correcao_aa: float = Field(default=12.0, ge=0)
    qtd_parcelas_quitacao: int = Field(default=12, ge=1)


class PermutaFinanceira(BaseModel):
    """
    Permuta financeira: % do VGV pago ao permutante (dono original do terreno).

    So e usada se Aba 2 tipo_permuta = 'financeira'.

    Modos de pagamento:
    - 'sobre_recebimento': proporcional a cada R$ recebido
    - 'apos_marco': comeca a pagar so depois de atingir um marco (ex.: % de vendas)

    Descontos: percentuais deduzidos da receita bruta antes de calcular a parcela.
    Fluxo 'personalizado': retencao parcial nos primeiros N meses + quitacao posterior.
    """

    percentual_vgv: float = Field(..., ge=0, le=100)
    modo_pagamento: Literal["sobre_recebimento", "apos_marco"] = "sobre_recebimento"

    # Para modo 'apos_marco'
    marco_tipo: Literal["percentual_vendas", "termino_obras"] = "percentual_vendas"
    marco_percentual_vendas: float = Field(
        default=50, ge=0, le=100, description="% de vendas necessarias para iniciar pagamento"
    )

    # Descontos sobre a base de calculo (novos)
    descontos: DescontosPermuta = Field(default_factory=DescontosPermuta)

    # Fluxo personalizado com retencao (novo)
    fluxo: Literal["padrao", "personalizado"] = "padrao"
    retencao: RetencaoPermuta = Field(default_factory=RetencaoPermuta)

    @model_validator(mode="after")
    def _valida(self) -> "PermutaFinanceira":
        if self.percentual_vgv == 0:
            raise ValueError("Permuta financeira com 0% nao faz sentido")
        return self


class Aba5Impostos(BaseModel):
    """Aba 5 completa: tributos + comissao + (permuta financeira opcional)."""

    tributos: Tributos
    comissao: ComissaoVenda
    permuta_financeira: PermutaFinanceira | None = None
