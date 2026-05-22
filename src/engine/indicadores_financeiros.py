"""
Implementacao propria de VPL (NPV) e TIR (IRR).

Substitui a dependencia opcional 'numpy_financial', que nem sempre vem
pre-instalado em ambientes corporativos.

Definicoes:
    NPV(rate, fluxo) = sum_i  CF_i / (1 + rate)^i      (i = 0, 1, 2, ...)
    IRR(fluxo)       = rate tal que NPV(rate, fluxo) = 0

A IRR e obtida pelo metodo de Newton-Raphson, com fallback para bisseccao
se a primeira nao convergir.
"""

from __future__ import annotations

from typing import Sequence


def npv(rate: float, fluxo: Sequence[float]) -> float:
    """
    Valor presente liquido.

    Args:
        rate: Taxa de desconto por periodo (em decimal, ex.: 0.01 = 1%)
        fluxo: Sequencia de fluxos de caixa por periodo. fluxo[0] e t=0 (sem desconto).
    """
    if rate <= -1:
        # rate = -100% ou menos faria divisao por zero / inversao de sinal sem sentido
        rate = -0.999999
    return sum(cf / (1 + rate) ** i for i, cf in enumerate(fluxo))


def _npv_derivada(rate: float, fluxo: Sequence[float]) -> float:
    """Derivada parcial de NPV em relacao a rate."""
    if rate <= -1:
        rate = -0.999999
    return sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(fluxo))


def irr(
    fluxo: Sequence[float],
    estimativa_inicial: float = 0.1,
    max_iter: int = 200,
    tolerancia: float = 1e-7,
) -> float | None:
    """
    Calcula a Taxa Interna de Retorno.

    Returns:
        Taxa por periodo em decimal (ex.: 0.0125 = 1.25% ao mes), ou None se
        nao for possivel encontrar (fluxo todo positivo, todo negativo, etc.).
    """
    fluxo = list(fluxo)
    if len(fluxo) < 2:
        return None

    # Verifica que o fluxo tem pelo menos uma entrada negativa e uma positiva
    tem_pos = any(cf > 0 for cf in fluxo)
    tem_neg = any(cf < 0 for cf in fluxo)
    if not (tem_pos and tem_neg):
        return None

    # ===== Newton-Raphson =====
    rate = estimativa_inicial
    for _ in range(max_iter):
        try:
            valor_npv = npv(rate, fluxo)
            if abs(valor_npv) < tolerancia:
                return rate
            derivada = _npv_derivada(rate, fluxo)
            if abs(derivada) < 1e-14:
                break
            rate_novo = rate - valor_npv / derivada
            # Evita rate <= -1 (denominator vira <=0)
            if rate_novo <= -0.99:
                rate_novo = -0.99
            if abs(rate_novo - rate) < tolerancia:
                return rate_novo
            rate = rate_novo
        except (OverflowError, ZeroDivisionError, ValueError):
            break

    # ===== Fallback: bisseccao =====
    return _irr_bisseccao(fluxo, tolerancia)


def _irr_bisseccao(
    fluxo: Sequence[float],
    tolerancia: float = 1e-7,
    max_iter: int = 500,
) -> float | None:
    """Bisseccao classica para encontrar a raiz do NPV."""
    # Limites: -99% (ja considerados muito pessimista) ate 1000% ao periodo
    lo, hi = -0.99, 10.0
    try:
        f_lo = npv(lo, fluxo)
        f_hi = npv(hi, fluxo)
    except (OverflowError, ZeroDivisionError, ValueError):
        return None

    if f_lo * f_hi > 0:
        # Sem mudanca de sinal no intervalo: nao ha raiz
        return None

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        try:
            f_mid = npv(mid, fluxo)
        except (OverflowError, ZeroDivisionError, ValueError):
            return None
        if abs(f_mid) < tolerancia:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    return (lo + hi) / 2
