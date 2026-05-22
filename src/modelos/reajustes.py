"""
Configuracao de reajustes monetarios (B1 — taxa anual constante projetada).

Suporta correcao por INCC, IPCA ou IGP-M em:
- Custo de obras (INCC)
- Parcelas durante a obra do comprador (INCC/IPCA/IGP-M)
- Terreno parcelado (IGP-M/IPCA)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConfigReajustes(BaseModel):
    """
    Reajustes monetarios por indices projetados.

    Modelo B1: usuario informa uma taxa anual esperada por indice.
    O sistema converte para mensal e aplica compound sobre os fluxos.
    Retrocompat: ativo=False por default, projetos antigos nao sao afetados.
    """

    ativo: bool = False

    # --- Obras (custo sobe com INCC) ---
    aplicar_incc_obras: bool = True
    incc_anual_pct: float = Field(
        default=6.0, ge=0.0, le=50.0,
        description="INCC projetado % a.a. (ex.: 6.0 = 6%)",
    )

    # --- Parcelas durante obra — comprador paga reajuste ---
    aplicar_correcao_parcelas: bool = True
    indice_parcelas: Literal["incc", "ipca", "igpm"] = "incc"
    ipca_anual_pct: float = Field(default=4.5, ge=0.0, le=50.0)
    igpm_anual_pct: float = Field(default=5.0, ge=0.0, le=50.0)

    # --- Terreno parcelado ---
    aplicar_correcao_terreno: bool = False
    indice_terreno: Literal["incc", "ipca", "igpm"] = "igpm"

    def taxa_mensal_indice(self, indice: str) -> float:
        """Converte taxa anual projetada em taxa mensal equivalente."""
        mapa = {
            "incc": self.incc_anual_pct,
            "ipca": self.ipca_anual_pct,
            "igpm": self.igpm_anual_pct,
        }
        taxa_anual = mapa.get(indice, self.incc_anual_pct)
        if taxa_anual == 0.0:
            return 0.0
        return (1 + taxa_anual / 100) ** (1 / 12) - 1
