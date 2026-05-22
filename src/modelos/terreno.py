"""
Modelos de dados da Aba 1 — Informacoes do Terreno e do Projeto.

Aqui ficam os inputs basicos do empreendimento: areas, datas e tipologias de lote.
Cada classe usa Pydantic para validar automaticamente os dados (ex.: nao deixa
voce colocar area negativa, datas fora de ordem, etc.).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Tipologia(BaseModel):
    """Uma tipologia de lote (ex.: Lote Padrao, Lote Esquina, Lote Comercial)."""

    nome: str = Field(..., description="Nome da tipologia, ex.: 'Lote Padrao'")
    quantidade: int = Field(..., gt=0, description="Quantidade de lotes desta tipologia")
    area_lote_m2: float = Field(..., gt=0, description="Area media do lote em m2")
    modo_preco: Literal["por_m2", "por_lote"] = Field(
        default="por_m2",
        description="Se o preco e dado em R$/m2 ou em R$ por lote inteiro",
    )
    valor_unitario: float = Field(
        ..., gt=0, description="R$/m2 (se modo_preco=por_m2) ou R$/lote (se por_lote)"
    )

    @property
    def area_total_m2(self) -> float:
        """Area total ocupada pela tipologia (qtd x area do lote)."""
        return self.quantidade * self.area_lote_m2

    @property
    def vgv_lote(self) -> float:
        """VGV de um unico lote desta tipologia."""
        if self.modo_preco == "por_m2":
            return self.area_lote_m2 * self.valor_unitario
        return self.valor_unitario

    @property
    def vgv_total(self) -> float:
        """VGV total da tipologia (qtd x VGV por lote)."""
        return self.quantidade * self.vgv_lote


class QuadroAreas(BaseModel):
    """
    Quadro de areas da gleba.

    Os campos podem ser informados em m2 OU em % da gleba. O modelo aceita
    ambos e o validador garante que a soma feche com a area total.
    """

    area_gleba_m2: float = Field(..., gt=0, description="Area total da gleba em m2")
    area_sistema_viario_m2: float = Field(0, ge=0)
    area_verde_m2: float = Field(0, ge=0)
    area_institucional_m2: float = Field(0, ge=0)
    area_app_m2: float = Field(0, ge=0)
    area_lotes_m2: float = Field(0, ge=0)

    @model_validator(mode="after")
    def _valida_soma(self) -> "QuadroAreas":
        soma_partes = (
            self.area_sistema_viario_m2
            + self.area_verde_m2
            + self.area_institucional_m2
            + self.area_app_m2
            + self.area_lotes_m2
        )
        # Tolerancia de 0.5% para arredondamentos
        if soma_partes > 0 and abs(soma_partes - self.area_gleba_m2) / self.area_gleba_m2 > 0.005:
            raise ValueError(
                f"Soma das areas ({soma_partes:.2f} m2) difere da area da gleba "
                f"({self.area_gleba_m2:.2f} m2) em mais de 0,5%"
            )
        return self

    @property
    def aproveitamento(self) -> float:
        """% da gleba que e area vendavel (lotes)."""
        return self.area_lotes_m2 / self.area_gleba_m2 if self.area_gleba_m2 else 0.0

    @property
    def relacao_lotes_viario(self) -> float:
        """Relacao area de lotes / area de sistema viario."""
        if self.area_sistema_viario_m2 == 0:
            return 0.0
        return self.area_lotes_m2 / self.area_sistema_viario_m2


class DatasProjeto(BaseModel):
    """
    Datas-chave do projeto.

    O termino do projeto NAO e informado: e calculado automaticamente como
    o maior valor entre o termino de obras e (data da ultima parcela + 2 meses).
    """

    inicio_projeto: date = Field(..., description="Mes 0 do projeto (M0)")
    aprovacao: date
    lancamento_vendas: date
    inicio_obras: date
    termino_obras: date

    @model_validator(mode="after")
    def _valida_ordem(self) -> "DatasProjeto":
        if self.aprovacao < self.inicio_projeto:
            raise ValueError("Aprovacao nao pode ser anterior ao inicio do projeto")
        if self.lancamento_vendas < self.inicio_projeto:
            raise ValueError("Lancamento de vendas nao pode ser anterior ao inicio do projeto")
        if self.inicio_obras < self.inicio_projeto:
            raise ValueError("Inicio de obras nao pode ser anterior ao inicio do projeto")
        if self.termino_obras <= self.inicio_obras:
            raise ValueError("Termino de obras deve ser posterior ao inicio de obras")
        return self


class InfoEmpreendimento(BaseModel):
    """Identificacao basica do empreendimento."""

    nome: str
    cidade: str
    uf: str = Field(..., min_length=2, max_length=2)
    tipo_loteamento: str = ""
    # E5: localizacao geografica (opcionais — retrocompat com JSONs antigos)
    latitude: float | None = None
    longitude: float | None = None
    link_maps: str = ""


class Aba1Terreno(BaseModel):
    """Aba 1 completa: identificacao + areas + datas + tipologias."""

    info: InfoEmpreendimento
    areas: QuadroAreas
    datas: DatasProjeto
    tipologias: list[Tipologia] = Field(..., min_length=1)

    @property
    def vgv_bruto(self) -> float:
        """VGV bruto = soma do VGV de todas as tipologias."""
        return sum(t.vgv_total for t in self.tipologias)

    @property
    def total_lotes(self) -> int:
        return sum(t.quantidade for t in self.tipologias)

    @property
    def area_media_lote_ponderada(self) -> float:
        """Area media dos lotes ponderada pela quantidade."""
        if self.total_lotes == 0:
            return 0.0
        soma_areas = sum(t.quantidade * t.area_lote_m2 for t in self.tipologias)
        return soma_areas / self.total_lotes
