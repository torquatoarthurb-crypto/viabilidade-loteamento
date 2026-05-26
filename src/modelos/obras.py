"""
Modelos de dados da Aba 3 — Custos de Obras.

Suporta duas formas de inserir o orcamento:
- Resumido: um valor unico R$/m2, aplicado sobre area de sistema viario OU
  sobre area de lotes (escolha do usuario).
- Detalhado: lista de etapas (terraplenagem, drenagem, pavimentacao, etc.),
  cada uma com seu valor, mes de inicio, duracao e curva de desembolso.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EtapaObra(BaseModel):
    """
    Uma etapa da obra (ex.: 'Terraplenagem').

    A curva de desembolso pode ser:
    - 'linear': valor / duracao por mes
    - 's_curve': curva S padrao (mais lento no inicio e fim, mais rapido no meio)
    - 'customizada': usuario passa lista de % por mes (deve somar 100)
    """

    nome: str
    valor_total: float = Field(..., ge=0, description="Custo total da etapa em R$")
    mes_inicio: int = Field(..., ge=0, description="Mes relativo a M0 em que a etapa comeca")
    duracao_meses: int = Field(..., ge=1)
    curva: Literal["linear", "s_curve", "customizada"] = "linear"
    curva_customizada: list[float] = Field(
        default_factory=list,
        description="Se curva='customizada', % por mes (tamanho = duracao_meses, soma = 100)",
    )

    @model_validator(mode="after")
    def _valida_curva_customizada(self) -> "EtapaObra":
        if self.curva == "customizada":
            if len(self.curva_customizada) != self.duracao_meses:
                raise ValueError(
                    f"Etapa '{self.nome}': curva_customizada deve ter {self.duracao_meses} valores "
                    f"(tem {len(self.curva_customizada)})"
                )
            soma = sum(self.curva_customizada)
            if abs(soma - 100.0) > 0.01:
                raise ValueError(
                    f"Etapa '{self.nome}': curva_customizada deve somar 100% (atual: {soma:.2f}%)"
                )
        return self


class OrcamentoResumido(BaseModel):
    """Orcamento resumido por R$/m2."""

    base_calculo: Literal["sistema_viario", "area_lotes"] = Field(
        ..., description="Aplicar valor_m2 sobre area de sistema viario OU sobre area de lotes"
    )
    valor_por_m2: float = Field(..., gt=0)
    mes_inicio: int = Field(..., ge=0, description="Mes em que a obra comeca")
    duracao_meses: int = Field(..., ge=1)
    curva: Literal["linear", "s_curve"] = "s_curve"


class Aba3Obras(BaseModel):
    """
    Aba 3 completa.

    Use 'resumido' OU 'etapas' (nao os dois ao mesmo tempo).
    """

    modo: Literal["resumido", "detalhado"] = "detalhado"
    resumido: OrcamentoResumido | None = None
    etapas: list[EtapaObra] = Field(default_factory=list)

    bdi_percentual: float = Field(default=0, ge=0, description="BDI sobre custo direto (%)")
    contingencia_percentual: float = Field(
        default=0, ge=0, description="Reserva de contingencia sobre o total (%)"
    )

    @model_validator(mode="after")
    def _valida(self) -> "Aba3Obras":
        if self.modo == "resumido" and self.resumido is None:
            raise ValueError("modo='resumido' exige preencher o objeto 'resumido'")
        return self
