"""
Engine de financiamento: banco (CCB/CCE) e investidor (emprestimo ou % do negocio).

Banco:
- Auto-saque quando caixa < minimo e gatilho atingido.
- Amortizacao quando caixa > minimo e passou carencia.
- Tem comissao de abertura e IOF sobre cada saque.

Investidor - Emprestimo:
- Saca APENAS nas janelas em que o banco nao pode sacar (gatilho bancario nao atingido).
- Se so o investidor estiver ativo (sem banco), saca livremente quando necessario.
- Sem comissao e sem IOF. Taxa e carencia proprias.
- Amortizacao segue a ordem configurada (banco_primeiro | investidor_primeiro).

Investidor - % do negocio:
- Nao afeta o fluxo de caixa; calculado no resumo da DRE apos apurar o lucro liquido.
"""

from __future__ import annotations

import numpy as np

from ..modelos.financeiro import ConfigFinanciamento


def _gatilho_banco_ok(
    config: ConfigFinanciamento,
    mes: int,
    pct_vendas_acum,
    pct_obras_acum,
) -> bool:
    """Retorna True se o gatilho do banco esta atingido no mes."""
    tipo = getattr(config, "gatilho_tipo", "nenhum")
    if tipo == "nenhum":
        return True
    v = float(pct_vendas_acum[mes]) if pct_vendas_acum is not None and mes < len(pct_vendas_acum) else 0.0
    o = float(pct_obras_acum[mes]) if pct_obras_acum is not None and mes < len(pct_obras_acum) else 0.0
    ok_v = v >= getattr(config, "gatilho_vendas_pct", 20.0)
    ok_o = o >= getattr(config, "gatilho_obras_pct", 30.0)
    if tipo == "vendas":
        return ok_v
    if tipo == "obras":
        return ok_o
    return ok_v and ok_o  # "ambos"


def simular_financiamento(
    fluxo_base: np.ndarray,
    config: ConfigFinanciamento,
    horizonte: int,
    pct_vendas_acum: np.ndarray | None = None,
    pct_obras_acum: np.ndarray | None = None,
) -> dict:
    """
    Simula banco + investidor-emprestimo conforme config.

    Retorna as chaves originais (banco) mais chaves novas para o investidor,
    mantendo retrocompatibilidade com o fluxo_caixa.py.
    """
    n = horizonte + 1

    # Banco
    saques_b = np.zeros(n)
    amort_b = np.zeros(n)
    juros_b = np.zeros(n)
    saldo_b_vec = np.zeros(n)

    # Investidor emprestimo
    saques_i = np.zeros(n)
    amort_i = np.zeros(n)
    juros_i_vec = np.zeros(n)
    saldo_i_vec = np.zeros(n)

    taxa_b = config.taxa_juros_am / 100
    taxa_i = getattr(config, "taxa_juros_investidor_am", 1.5) / 100
    limite_b = config.limite_credito_valor
    limite_i = getattr(config, "limite_investidor", 0.0)
    car_b = config.periodo_carencia_meses
    car_i = getattr(config, "carencia_investidor", 0)
    caixa_min = max(0.0, config.caixa_minimo)
    ordem = getattr(config, "ordem_amortizacao", "banco_primeiro")

    ativo_inv = getattr(config, "ativo_investidor", False)
    modo_inv = getattr(config, "modo_investidor", "pct_negocio")
    inv_emp = ativo_inv and modo_inv == "emprestimo"

    saldo_b = 0.0
    saldo_i = 0.0
    saldo_caixa = 0.0
    mes_gatilho = -1

    # Comissao de abertura (banco, paga em M0)
    comissao = 0.0
    if config.ativo and config.comissao_abertura_pct > 0 and limite_b > 0:
        comissao = limite_b * config.comissao_abertura_pct / 100

    for mes in range(n):
        saldo_caixa += fluxo_base[mes]

        # Juros sobre saldos devedores
        j_b = saldo_b * taxa_b
        juros_b[mes] = j_b
        saldo_caixa -= j_b

        j_i = saldo_i * taxa_i
        juros_i_vec[mes] = j_i
        saldo_caixa -= j_i

        # Comissao M0
        if mes == 0 and comissao > 0:
            saldo_caixa -= comissao

        # Verificar gatilho do banco
        banco_ok = config.ativo and _gatilho_banco_ok(config, mes, pct_vendas_acum, pct_obras_acum)
        if banco_ok and mes_gatilho < 0:
            mes_gatilho = mes

        # ---- Sacar se caixa abaixo do minimo ----
        if saldo_caixa < caixa_min - 0.01:
            necessario = caixa_min - saldo_caixa

            # Banco saca quando gatilho atingido
            if config.ativo and banco_ok:
                if limite_b <= 0:
                    saque = necessario
                else:
                    saque = min(necessario, max(0.0, limite_b - saldo_b))
                if saque > 0:
                    iof = saque * (config.iof_pct / 100)
                    saldo_b += saque + iof
                    saques_b[mes] = saque
                    saldo_caixa += saque
                    necessario = max(0.0, caixa_min - saldo_caixa)

            # Investidor saca quando banco bloqueado (ou banco inativo)
            inv_pode_sacar = inv_emp and (not config.ativo or not banco_ok)
            if inv_pode_sacar and necessario > 0.01:
                if limite_i <= 0:
                    saque_i = necessario
                else:
                    saque_i = min(necessario, max(0.0, limite_i - saldo_i))
                if saque_i > 0:
                    saldo_i += saque_i  # sem IOF
                    saques_i[mes] = saque_i
                    saldo_caixa += saque_i

        # ---- Amortizar excedente ----
        excedente = saldo_caixa - caixa_min
        if excedente > 0.01 and (saldo_b > 0.01 or saldo_i > 0.01):
            if ordem == "banco_primeiro":
                if saldo_b > 0.01 and mes >= car_b:
                    a = min(excedente, saldo_b)
                    amort_b[mes] = a
                    saldo_b -= a
                    saldo_caixa -= a
                    excedente -= a
                if inv_emp and saldo_i > 0.01 and excedente > 0.01 and mes >= car_i:
                    a = min(excedente, saldo_i)
                    amort_i[mes] = a
                    saldo_i -= a
                    saldo_caixa -= a
            else:  # investidor_primeiro
                if inv_emp and saldo_i > 0.01 and mes >= car_i:
                    a = min(excedente, saldo_i)
                    amort_i[mes] = a
                    saldo_i -= a
                    saldo_caixa -= a
                    excedente -= a
                if saldo_b > 0.01 and excedente > 0.01 and mes >= car_b:
                    a = min(excedente, saldo_b)
                    amort_b[mes] = a
                    saldo_b -= a
                    saldo_caixa -= a

        saldo_b_vec[mes] = saldo_b
        saldo_i_vec[mes] = saldo_i

    return {
        # Banco (retrocompatibilidade)
        "saques": saques_b,
        "amortizacoes": amort_b,
        "juros_banco": juros_b,
        "saldo_devedor": saldo_b_vec,
        "comissao_abertura": comissao,
        "saldo_devedor_final": saldo_b,
        "mes_gatilho": mes_gatilho,
        # Investidor emprestimo
        "saques_investidor": saques_i,
        "amortizacoes_investidor": amort_i,
        "juros_investidor": juros_i_vec,
        "saldo_devedor_investidor": saldo_i_vec,
        "saldo_devedor_investidor_final": saldo_i,
    }
