"""
Modelos de dados da Aba 2 — Composicao das Receitas e Permuta Fisica.

Aqui ficam:
- Configuracao de permuta (sem permuta, fisica ou financeira)
- Estrutura de recebiveis (sinal, parcelas mensais, baloes anuais, financiamento)
- Curva de vendas (% do estoque vendido em cada mes)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PermutaFisicaTipologia(BaseModel):
    """% de uma tipologia destinada a permuta fisica (sai do estoque vendavel)."""

    tipologia: str = Field(..., description="Nome da tipologia (deve bater com Aba 1)")
    percentual: float = Field(..., ge=0, le=100, description="% de lotes para permuta")


class FluxoRecebiveis(BaseModel):
    """
    Estrutura de recebiveis aplicada a uma venda.

    Logica:
    - Sinal: percentual_sinal e dividido em qtd_parcelas_sinal (a partir do mes da venda)
    - Parcelas durante obra: percentual_obra dividido pelas parcelas mensais ate
      o termino de obras (calculado automaticamente pela engine)
    - Baloes anuais: percentual_baloes dividido em qtd_baloes (a cada 12 meses)
    - Financiamento pos-obra: percentual_financiamento parcelado em qtd_parcelas_financiamento
      pelo sistema Price com taxa juros_financiamento_am

    Os percentuais devem somar 100%.
    """

    nome: str = Field(..., description="Nome desse fluxo, ex.: 'Padrao Lancamento'")

    percentual_sinal: float = Field(..., ge=0, le=100)
    qtd_parcelas_sinal: int = Field(default=1, ge=1)

    percentual_obra: float = Field(..., ge=0, le=100)
    juros_parcelas_obra_am: float = Field(
        default=0.0, ge=0, description="Juros mensais aplicados nas parcelas durante obra (% a.m., ex.: 0.5 = 0.5%)"
    )

    percentual_baloes: float = Field(default=0, ge=0, le=100)
    qtd_baloes: int = Field(default=0, ge=0)

    percentual_financiamento: float = Field(default=0, ge=0, le=100)
    qtd_parcelas_financiamento: int = Field(default=0, ge=0)
    juros_financiamento_am: float = Field(
        default=0.0, ge=0, description="Juros mensais do financiamento pos-obra (% a.m.)"
    )

    @model_validator(mode="after")
    def _valida_soma(self) -> "FluxoRecebiveis":
        soma = (
            self.percentual_sinal
            + self.percentual_obra
            + self.percentual_baloes
            + self.percentual_financiamento
        )
        if abs(soma - 100.0) > 0.01:
            raise ValueError(
                f"Os percentuais do fluxo '{self.nome}' devem somar 100% (atual: {soma:.2f}%)"
            )
        if self.percentual_baloes > 0 and self.qtd_baloes == 0:
            raise ValueError("Se ha % de baloes, qtd_baloes deve ser >= 1")
        if self.percentual_financiamento > 0 and self.qtd_parcelas_financiamento == 0:
            raise ValueError(
                "Se ha % de financiamento, qtd_parcelas_financiamento deve ser >= 1"
            )
        return self


class FaixaCurvaVendas(BaseModel):
    """
    Uma faixa da curva de vendas.

    Indica que entre os meses [mes_inicio, mes_fim] (relativos ao M0),
    sera vendido um certo % do estoque, usando o fluxo de recebiveis indicado.
    """

    mes_inicio: int = Field(..., ge=0, description="Mes relativo a M0 onde a faixa comeca")
    mes_fim: int = Field(..., ge=0, description="Mes relativo a M0 onde a faixa termina")
    percentual_estoque: float = Field(
        ..., ge=0, le=100, description="% do estoque vendido nesta faixa (distribuido linearmente)"
    )
    fluxo_recebiveis: str = Field(..., description="Nome do FluxoRecebiveis a aplicar")
    fator_preco: float = Field(
        default=1.0, gt=0,
        description="Multiplicador de preco nesta faixa. Ex.: 0.95 = -5% (lancamento), 1.10 = +10% (estoque). Retrocompat: 1.0 = preco padrao.",
    )

    @model_validator(mode="after")
    def _valida(self) -> "FaixaCurvaVendas":
        if self.mes_fim < self.mes_inicio:
            raise ValueError("mes_fim deve ser >= mes_inicio")
        return self


class Aba2Receitas(BaseModel):
    """Aba 2 completa: permuta + fluxos de recebiveis + curva de vendas."""

    tipo_permuta: Literal["sem_permuta", "fisica", "financeira"] = "sem_permuta"

    # So usado quando tipo_permuta = "fisica"
    permuta_fisica: list[PermutaFisicaTipologia] = Field(default_factory=list)

    # Fluxos de recebiveis disponiveis (referenciados pela curva de vendas)
    fluxos_recebiveis: list[FluxoRecebiveis] = Field(..., min_length=1)

    # Curva de vendas: como o estoque e distribuido no tempo
    curva_vendas: list[FaixaCurvaVendas] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _valida(self) -> "Aba2Receitas":
        # Soma dos % da curva = 100
        soma = sum(f.percentual_estoque for f in self.curva_vendas)
        if abs(soma - 100.0) > 0.01:
            raise ValueError(
                f"A soma dos percentuais da curva de vendas deve ser 100% (atual: {soma:.2f}%)"
            )

        # Toda faixa referencia um fluxo existente
        nomes_fluxos = {f.nome for f in self.fluxos_recebiveis}
        for faixa in self.curva_vendas:
            if faixa.fluxo_recebiveis not in nomes_fluxos:
                raise ValueError(
                    f"Faixa de venda referencia fluxo '{faixa.fluxo_recebiveis}' que nao existe"
                )

        # Permuta fisica so faz sentido se tipo_permuta = fisica
        if self.tipo_permuta != "fisica" and self.permuta_fisica:
            raise ValueError(
                "permuta_fisica so deve ser preenchida quando tipo_permuta = 'fisica'"
            )

        return self
