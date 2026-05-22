"""
Modelos de dados da Aba 4 — Custos de Desenvolvimento e Marketing.

Conforme observacao do usuario: TODAS as despesas tem uma tabela de
% de desembolso por mes (referenciada aos marcos do projeto).

Para simplificar, cada despesa pode ser lancada de tres formas:
- 'a_vista': valor inteiro lancado em um mes especifico
- 'parcelado_linear': valor distribuido igualmente entre mes_inicio e mes_fim
- 'distribuicao_customizada': usuario informa % por mes (lista)

Administracao tem modo proprio: pode ser % do VGV mensal, % da receita mensal
ou valor fixo R$/mes durante um periodo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DespesaTemporal(BaseModel):
    """
    Uma despesa que precisa ser distribuida no tempo.

    Use sempre uma das tres formas:
    1. 'a_vista': preencha valor_total e mes_pagamento
    2. 'parcelado_linear': preencha valor_total, mes_inicio e mes_fim
    3. 'distribuicao_customizada': preencha valor_total, mes_inicio e
       distribuicao_percentual (lista de % por mes a partir de mes_inicio)
    """

    nome: str
    categoria: Literal["projetos", "licenciamento", "marketing", "outros"] = "outros"
    valor_total: float = Field(..., gt=0, description="Valor total da despesa em R$")
    # modo_valor: como o usuario definiu o valor (retrocompat com JSONs antigos)
    modo_valor: Literal["fixo", "pct_vgv"] = "fixo"
    percentual_vgv: float = Field(default=0.0, ge=0.0)

    modo: Literal["a_vista", "parcelado_linear", "distribuicao_customizada"]

    mes_pagamento: int | None = Field(default=None, ge=0)  # so para 'a_vista'
    mes_inicio: int | None = Field(default=None, ge=0)
    mes_fim: int | None = Field(default=None, ge=0)
    distribuicao_percentual: list[float] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valida(self) -> "DespesaTemporal":
        if self.modo == "a_vista":
            if self.mes_pagamento is None:
                raise ValueError(f"Despesa '{self.nome}': modo a_vista exige mes_pagamento")
        elif self.modo == "parcelado_linear":
            if self.mes_inicio is None or self.mes_fim is None:
                raise ValueError(
                    f"Despesa '{self.nome}': modo parcelado_linear exige mes_inicio e mes_fim"
                )
            if self.mes_fim < self.mes_inicio:
                raise ValueError(f"Despesa '{self.nome}': mes_fim deve ser >= mes_inicio")
        elif self.modo == "distribuicao_customizada":
            if self.mes_inicio is None or not self.distribuicao_percentual:
                raise ValueError(
                    f"Despesa '{self.nome}': modo customizado exige mes_inicio e distribuicao_percentual"
                )
            soma = sum(self.distribuicao_percentual)
            if abs(soma - 100.0) > 0.01:
                raise ValueError(
                    f"Despesa '{self.nome}': distribuicao_percentual deve somar 100% (atual: {soma:.2f}%)"
                )
        return self


class Administracao(BaseModel):
    """
    Custo de administracao: % sobre a receita mensal do projeto.
    Incide apenas quando ha receita, na mesma logica dos impostos.
    """

    percentual: float = Field(
        default=2.0, ge=0,
        description="% sobre a receita mensal recebida (ex.: 2 = 2%)"
    )

    @model_validator(mode="before")
    @classmethod
    def _migrar_formato_antigo(cls, data):
        """Aceita JSON antigo com campos 'valor', 'modo', 'mes_inicio', 'mes_fim'."""
        if isinstance(data, dict) and "valor" in data and "percentual" not in data:
            modo = data.get("modo", "valor_fixo")
            if modo in ("percentual_receita_mensal", "percentual_vgv"):
                return {"percentual": float(data["valor"])}
            return {"percentual": 2.0}
        return data


class Aba4Desenvolvimento(BaseModel):
    """Aba 4 completa: despesas de desenvolvimento + administracao."""

    despesas: list[DespesaTemporal] = Field(default_factory=list)
    administracao: Administracao
