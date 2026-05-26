"""
Modelos de dados da Aba 2 — Composicao das Receitas.

Cada tipologia tem seu proprio fluxo de recebiveis e curva de vendas mensal.
O fluxo de caixa final e a soma dos fluxos de todas as tipologias.
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

    Mantido para retrocompatibilidade com a engine e exportar_excel.
    No novo design, use FluxoTipologia.as_fluxo_recebiveis() para gerar este objeto.
    """

    nome: str = Field(..., description="Nome desse fluxo")

    percentual_sinal: float = Field(..., ge=0, le=100)
    qtd_parcelas_sinal: int = Field(default=1, ge=1)

    percentual_obra: float = Field(..., ge=0, le=100)
    juros_parcelas_obra_am: float = Field(default=0.0, ge=0)

    percentual_baloes: float = Field(default=0, ge=0, le=100)
    qtd_baloes: int = Field(default=0, ge=0)

    percentual_financiamento: float = Field(default=0, ge=0, le=100)
    qtd_parcelas_financiamento: int = Field(default=0, ge=0)
    juros_financiamento_am: float = Field(default=0.0, ge=0)

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
            raise ValueError("Se ha % de financiamento, qtd_parcelas_financiamento deve ser >= 1")
        return self


class FaixaCurvaVendas(BaseModel):
    """Mantido para retrocompatibilidade de loading de JSONs antigos."""

    mes_inicio: int = Field(..., ge=0)
    mes_fim: int = Field(..., ge=0)
    percentual_estoque: float = Field(..., ge=0, le=100)
    fluxo_recebiveis: str = Field(default="")
    fator_preco: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def _valida(self) -> "FaixaCurvaVendas":
        if self.mes_fim < self.mes_inicio:
            raise ValueError("mes_fim deve ser >= mes_inicio")
        return self


class FluxoTipologia(BaseModel):
    """
    Configuracao completa de vendas para UMA tipologia:
    fluxo de recebiveis + curva de vendas mensal + fatores de preco.
    """

    nome_tipologia: str = Field(..., description="Nome da tipologia (deve bater com Aba 1)")

    # Fluxo de recebiveis
    percentual_sinal: float = Field(default=10.0, ge=0, le=100)
    qtd_parcelas_sinal: int = Field(default=1, ge=1)
    percentual_obra: float = Field(default=30.0, ge=0, le=100)
    juros_parcelas_obra_am: float = Field(default=0.5, ge=0)
    percentual_baloes: float = Field(default=10.0, ge=0, le=100)
    qtd_baloes: int = Field(default=0, ge=0)
    percentual_financiamento: float = Field(default=50.0, ge=0, le=100)
    qtd_parcelas_financiamento: int = Field(default=120, ge=0)
    juros_financiamento_am: float = Field(default=1.0, ge=0)

    # Curva de vendas mensal: {mes: % do estoque DESTA tipologia}
    # A soma deve ser ~100. Chaves sao inteiros (mes relativo a M0).
    curva_mensal: dict[int, float] = Field(default_factory=dict)

    # Fatores de preco progressivo: {mes: multiplicador} — padrao 1.0
    fatores_preco: dict[int, float] = Field(default_factory=dict)

    def as_fluxo_recebiveis(self) -> FluxoRecebiveis:
        """Constroi FluxoRecebiveis para uso direto na engine."""
        pct_b = self.percentual_baloes
        qtd_b = max(self.qtd_baloes, 1) if pct_b > 0 else 0
        pct_f = self.percentual_financiamento
        qtd_f = max(self.qtd_parcelas_financiamento, 1) if pct_f > 0 else 0
        return FluxoRecebiveis(
            nome=self.nome_tipologia,
            percentual_sinal=self.percentual_sinal,
            qtd_parcelas_sinal=self.qtd_parcelas_sinal,
            percentual_obra=self.percentual_obra,
            juros_parcelas_obra_am=self.juros_parcelas_obra_am,
            percentual_baloes=pct_b,
            qtd_baloes=qtd_b,
            percentual_financiamento=pct_f,
            qtd_parcelas_financiamento=qtd_f,
            juros_financiamento_am=self.juros_financiamento_am,
        )

    @property
    def soma_fluxo(self) -> float:
        return (
            self.percentual_sinal
            + self.percentual_obra
            + self.percentual_baloes
            + self.percentual_financiamento
        )

    @property
    def soma_curva(self) -> float:
        return sum(self.curva_mensal.values())


class OutraReceita(BaseModel):
    """
    Receita nao relacionada a venda de lotes.

    O valor e distribuido linearmente entre mes_inicio e mes_fim.
    Para receita pontual use mes_fim = mes_inicio.
    """

    nome: str = Field(..., description="Descricao desta receita")
    tipo: Literal["aporte", "receita_financeira", "venda_ativo", "outro"] = Field(default="outro")
    valor_total: float = Field(default=0.0, ge=0.0)
    mes_inicio: int = Field(default=0, ge=0)
    mes_fim: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _valida(self) -> "OutraReceita":
        if self.mes_fim < self.mes_inicio:
            raise ValueError("mes_fim deve ser >= mes_inicio")
        return self


class Aba2Receitas(BaseModel):
    """Aba 2: permuta + fluxos por tipologia + outras receitas."""

    tipo_permuta: Literal["sem_permuta", "fisica", "financeira"] = "sem_permuta"

    # So usado quando tipo_permuta = "fisica"
    permuta_fisica: list[PermutaFisicaTipologia] = Field(default_factory=list)

    # Configuracao por tipologia (design atual)
    fluxos_tipologia: list[FluxoTipologia] = Field(default_factory=list)

    # Campos legacy — mantidos como opcionais para migracao via json_io.py
    # Nao sao usados na engine quando fluxos_tipologia esta preenchido
    fluxos_recebiveis: list[FluxoRecebiveis] = Field(default_factory=list)
    curva_vendas: list[FaixaCurvaVendas] = Field(default_factory=list)

    outras_receitas: list[OutraReceita] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valida(self) -> "Aba2Receitas":
        if self.tipo_permuta != "fisica" and self.permuta_fisica:
            raise ValueError("permuta_fisica so deve ser preenchida quando tipo_permuta = 'fisica'")
        return self
