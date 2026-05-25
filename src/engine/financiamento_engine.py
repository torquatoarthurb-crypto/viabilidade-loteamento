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
    pct_vendas_acum: np.ndarray | None = None,
    pct_obras_acum: np.ndarray | None = None,
) -> dict:
    """
    Simula uso automatico de linha de credito bancaria.

    Args:
        fluxo_base: saldo mensal sem financiamento (array de horizonte+1 elementos)
        config: parametros da linha de credito
        horizonte: numero de meses do projeto
        pct_vendas_acum: % acumulado do VGV vendavel contratado por mes (0-100)
        pct_obras_acum: % acumulado do custo de obras desembolsado por mes (0-100)

    Returns:
        dict com:
        - saques: entradas de caixa da linha (R$/mes)
        - amortizacoes: saidas de amortizacao do principal (R$/mes)
        - juros_banco: saidas de juros ao banco (R$/mes)
        - saldo_devedor: saldo devedor ao final de cada mes
        - comissao_abertura: valor escalar da comissao (R$)
        - saldo_devedor_final: saldo devedor remanescente ao fim do horizonte
        - mes_gatilho: primeiro mes em que o gatilho foi atingido (-1 se nao ativo)
    """
    n = horizonte + 1
    saques = np.zeros(n)
    amortizacoes = np.zeros(n)
    juros_banco = np.zeros(n)
    saldo_devedor_vec = np.zeros(n)

    taxa_m = config.taxa_juros_am / 100
    limite = config.limite_credito_valor  # 0 = sem limite
    caixa_min = max(0.0, config.caixa_minimo)
    saldo_devedor = 0.0
    saldo_caixa = 0.0

    # Comissao de abertura: cobrada em M0 se houver limite definido
    comissao = 0.0
    if config.comissao_abertura_pct > 0 and limite > 0:
        comissao = limite * config.comissao_abertura_pct / 100

    # Pre-calcula se ha gatilho ativo
    gatilho_tipo = getattr(config, "gatilho_tipo", "nenhum")
    gatilho_vendas = getattr(config, "gatilho_vendas_pct", 20.0)
    gatilho_obras = getattr(config, "gatilho_obras_pct", 30.0)
    mes_gatilho = -1  # -1 = sem gatilho ou gatilho nunca atingido

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

        # 4) Verificar gatilho de liberacao do financiamento
        if gatilho_tipo == "nenhum":
            linha_liberada = True
        else:
            v = float(pct_vendas_acum[mes]) if pct_vendas_acum is not None and mes < len(pct_vendas_acum) else 0.0
            o = float(pct_obras_acum[mes]) if pct_obras_acum is not None and mes < len(pct_obras_acum) else 0.0
            ok_vendas = v >= gatilho_vendas
            ok_obras = o >= gatilho_obras
            if gatilho_tipo == "vendas":
                linha_liberada = ok_vendas
            elif gatilho_tipo == "obras":
                linha_liberada = ok_obras
            else:  # "ambos"
                linha_liberada = ok_vendas and ok_obras
            if linha_liberada and mes_gatilho < 0:
                mes_gatilho = mes

        # 5) Se caixa abaixo do minimo e linha liberada: sacar da linha
        if linha_liberada and saldo_caixa < caixa_min - 0.01:
            necessario = caixa_min - saldo_caixa
            if limite <= 0:
                saque = necessario
            else:
                disponivel = max(0.0, limite - saldo_devedor)
                saque = min(necessario, disponivel)

            if saque > 0:
                iof = saque * (config.iof_pct / 100)
                saldo_devedor += saque + iof
                saques[mes] = saque
                saldo_caixa += saque

        # 6) Se caixa acima do minimo e passou carencia: amortizar so o excedente
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
        "mes_gatilho": mes_gatilho,
    }
