"""
Utilitarios da engine de calculo.

Funcoes basicas usadas por varios modulos:
- meses_entre: numero de meses entre duas datas
- parcela_price: parcela mensal pelo sistema Price
- gerar_curva_s: curva S padrao (acumulada) para distribuicao de obra
- normalizar_curva: garante que uma lista de % some 100
"""

from __future__ import annotations

from datetime import date

import numpy as np


def meses_entre(d1: date, d2: date) -> int:
    """
    Numero de meses inteiros entre d1 e d2 (d2 - d1).

    Considera diferenca em mes calendario, ignorando dia. Ex.: jan/2026 a
    mar/2026 = 2 meses.
    """
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def parcela_price(pv: float, i: float, n: int) -> float:
    """
    Calcula a parcela mensal pelo sistema Price.

    Args:
        pv: Saldo devedor (Present Value)
        i: Taxa de juros mensal em decimal (ex.: 0.01 = 1% a.m.)
        n: Numero de parcelas

    Returns:
        Valor da parcela mensal (constante).

    Se i = 0, vira parcela fixa = pv / n.
    """
    if n <= 0:
        return 0.0
    if i == 0:
        return pv / n
    fator = (1 + i) ** n
    return pv * (i * fator) / (fator - 1)


def gerar_curva_linear(duracao_meses: int) -> list[float]:
    """Curva linear: cada mes recebe 1/duracao do total. Retorna em decimal."""
    if duracao_meses <= 0:
        return []
    valor = 1.0 / duracao_meses
    return [valor] * duracao_meses


def gerar_curva_s(duracao_meses: int) -> list[float]:
    """
    Curva S padrao para distribuicao de obra.

    Usa funcao logistica simetrica: lenta no inicio, rapida no meio,
    lenta no fim. Retorna distribuicao incremental por mes (em decimal,
    soma = 1).
    """
    if duracao_meses <= 0:
        return []
    if duracao_meses == 1:
        return [1.0]

    # x vai de -3 a 3 ao longo da duracao
    x = np.linspace(-3, 3, duracao_meses + 1)
    # CDF logistica
    cdf = 1 / (1 + np.exp(-x))
    # Normalizar (cdf[0] != 0 e cdf[-1] != 1 com x finito, entao ajustamos)
    cdf = (cdf - cdf[0]) / (cdf[-1] - cdf[0])
    # Distribuicao incremental
    incrementos = np.diff(cdf)
    # Garantir soma = 1
    incrementos = incrementos / incrementos.sum()
    return incrementos.tolist()


def horizonte_recebimentos(
    mes_venda: int,
    qtd_parcelas_sinal: int,
    mes_termino_obras: int,
    qtd_baloes: int,
    qtd_parcelas_financiamento: int,
) -> int:
    """
    Calcula o ultimo mes em que essa venda gera recebimento.

    Logica:
    - Sinal: termina em mes_venda + qtd_parcelas_sinal - 1
    - Parcelas durante obra: terminam em mes_termino_obras
    - Baloes: ultimo balao em mes_venda + qtd_baloes * 12
    - Financiamento: termina em mes_termino_obras + qtd_parcelas_financiamento
    """
    fim_sinal = mes_venda + max(qtd_parcelas_sinal, 1) - 1
    fim_obra = mes_termino_obras
    fim_baloes = mes_venda + qtd_baloes * 12 if qtd_baloes > 0 else 0
    fim_fin = (
        mes_termino_obras + qtd_parcelas_financiamento if qtd_parcelas_financiamento > 0 else 0
    )
    return max(fim_sinal, fim_obra, fim_baloes, fim_fin)
