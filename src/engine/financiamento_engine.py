"""
Engine de financiamento bancario (A1 — saque automatico).

O sistema identifica mes a mes os periodos de caixa negativo e saca
automaticamente da linha de credito. Quando o caixa volta ao positivo
(apos o periodo de carencia), amortiza o saldo devedor.

Resultado integrado ao fluxo de caixa como linhas separadas:
  Entradas: Saque Financiamento
  Saidas:   Amortizacao Financiamento | Juros Financiamento Banco | Comissao Abertura
"""

from __future__ import annotations

import numpy as np

from ..modelos.financeiro import ConfigFinanciamento


def simular_financiamento(
    fluxo_base: np.ndarray,
    config: ConfigFinanciamento,
    horizonte: int,
) -> dict:
    """
    Simula uso automatico de linha de credito bancaria.

    Args:
        fluxo_base: saldo mensal sem financiamento (array de horizonte+1 elementos)
        config: parametros da linha de credito
        horizonte: numero de meses do projeto

    Returns:
        dict com:
        - saques: entradas de caixa da linha (R$/mes)
        - amortizacoes: saidas de amortizacao do principal (R$/mes)
        - juros_banco: saidas de juros ao banco (R$/mes)
        - saldo_devedor: saldo devedor ao final de cada mes
        - comissao_abertura: valor escalar da comissao (R$)
        - saldo_devedor_final: saldo devedor remanescente ao fim do horizonte
    """
    n = horizonte + 1
    saques = np.zeros(n)
    amortizacoes = np.zeros(n)
    juros_banco = np.zeros(n)
    saldo_devedor_vec = np.zeros(n)

    taxa_m = config.taxa_juros_am / 100
    limite = config.limite_credito_valor  # 0 = sem limite
    # Caixa minimo que o desenvolvedor mantem sempre disponivel (pode ser 0)
    caixa_min = max(0.0, config.caixa_minimo)
    saldo_devedor = 0.0
    saldo_caixa = 0.0  # saldo acumulado do desenvolvedor com financiamento

    # Comissao de abertura: cobrada em M0 se houver limite definido
    comissao = 0.0
    if config.comissao_abertura_pct > 0 and limite > 0:
        comissao = limite * config.comissao_abertura_pct / 100

    for mes in range(n):
        # 1) Incorporar fluxo base do mes ao caixa do desenvolvedor
        saldo_caixa += fluxo_base[mes]

        # 2) Pagar juros sobre saldo devedor atual
        j = saldo_devedor * taxa_m
        juros_banco[mes] = j
        saldo_caixa -= j

        # 3) Comissao de abertura no M0
        if mes == 0 and comissao > 0:
            saldo_caixa -= comissao

        # 4) Se caixa abaixo do minimo: sacar da linha para atingir caixa_minimo
        #    (sem caixa_minimo, comportamento original: saca so se negativo)
        if saldo_caixa < caixa_min - 0.01:
            necessario = caixa_min - saldo_caixa
            if limite <= 0:
                saque = necessario
            else:
                disponivel = max(0.0, limite - saldo_devedor)
                saque = min(necessario, disponivel)

            if saque > 0:
                # IOF e incorporado ao saldo devedor (banco debita sobre o principal)
                iof = saque * (config.iof_pct / 100)
                saldo_devedor += saque + iof
                saques[mes] = saque
                saldo_caixa += saque  # caixa vai ate caixa_minimo

        # 5) Se caixa acima do minimo e passou carencia: amortizar so o excedente
        #    Respeita sempre o caixa_minimo — nunca amortiza o que e reserva
        excedente = saldo_caixa - caixa_min
        if (
            excedente > 0.01
            and saldo_devedor > 0.01
            and mes >= config.periodo_carencia_meses
        ):
            amort = min(excedente, saldo_devedor)
            amortizacoes[mes] = amort
            saldo_devedor -= amort
            saldo_caixa -= amort

        saldo_devedor_vec[mes] = saldo_devedor

    return {
        "saques": saques,
        "amortizacoes": amortizacoes,
        "juros_banco": juros_banco,
        "saldo_devedor": saldo_devedor_vec,
        "comissao_abertura": comissao,
        "saldo_devedor_final": saldo_devedor,
    }
