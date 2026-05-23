"""
Engine de recebimentos: calcula as entradas de caixa mes a mes.

Logica geral:
1. Determina VGV vendavel (descontando permuta fisica)
2. Para cada faixa da curva de vendas, distribui o VGV vendido linearmente
   nos meses da faixa
3. Para cada venda mensal, gera o fluxo de parcelas no tempo:
   - Sinal (dividido em N parcelas a partir do mes da venda)
   - Parcelas durante obra (Price com juros, ate o termino de obras)
   - Baloes anuais (a cada 12 meses apos a venda)
   - Financiamento pos-obra (Price, comecando 1 mes apos termino da obra)
4. Soma tudo no vetor 'recebimentos' e tambem rastreia 'vendas' (VGV vendido por mes)
"""

from __future__ import annotations

import numpy as np

from ..modelos import Aba1Terreno, Aba2Receitas, FluxoRecebiveis
from .utilidades import meses_entre, parcela_price


def calcular_vgv_vendavel(terreno: Aba1Terreno, receitas: Aba2Receitas) -> float:
    """
    VGV vendavel = VGV bruto - permuta fisica.

    Permuta financeira NAO desconta aqui (ela e tratada como saida no fluxo de caixa).
    """
    vgv_bruto = terreno.vgv_bruto

    if receitas.tipo_permuta != "fisica" or not receitas.permuta_fisica:
        return vgv_bruto

    # Para cada tipologia, descontar o % destinado a permuta
    desconto = 0.0
    mapa_tipologias = {t.nome: t for t in terreno.tipologias}
    for p in receitas.permuta_fisica:
        if p.tipologia not in mapa_tipologias:
            raise ValueError(
                f"Permuta referencia tipologia '{p.tipologia}' que nao existe na Aba 1"
            )
        tip = mapa_tipologias[p.tipologia]
        desconto += tip.vgv_total * (p.percentual / 100)

    return vgv_bruto - desconto


def _gerar_recebimentos_de_uma_venda(
    vgv_venda: float,
    mes_venda: int,
    fluxo: FluxoRecebiveis,
    mes_termino_obras: int,
    horizonte: int,
    corr_m: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Gera os vetores de recebimentos no tempo para UMA unica venda.

    Args:
        vgv_venda: Valor total da venda (R$)
        mes_venda: Mes (relativo a M0) em que a venda foi feita
        fluxo: Configuracao do fluxo de recebiveis
        mes_termino_obras: Mes (relativo a M0) do termino das obras
        horizonte: Tamanho do vetor de saida

    Returns:
        Tupla (principal, juros, correcao) com tres arrays de tamanho (horizonte+1,):
        - principal: parte do recebimento que amortiza o preco do lote
        - juros: parte do recebimento que e juros embutidos (receita financeira)
        - correcao: adicional de correcao monetaria sobre as parcelas da obra (B1)

        recebimento_total = principal + juros + correcao
    """
    principal = np.zeros(horizonte + 1)
    juros = np.zeros(horizonte + 1)
    correcao = np.zeros(horizonte + 1)

    # ----- 1. SINAL (sem juros: e parte do principal) -----
    valor_sinal = vgv_venda * (fluxo.percentual_sinal / 100)
    if valor_sinal > 0 and fluxo.qtd_parcelas_sinal > 0:
        parcela_sinal = valor_sinal / fluxo.qtd_parcelas_sinal
        for k in range(fluxo.qtd_parcelas_sinal):
            mes = mes_venda + k
            if 0 <= mes <= horizonte:
                principal[mes] += parcela_sinal

    # ----- 2. PARCELAS MENSAIS DURANTE OBRA (Price com juros) -----
    valor_obra = vgv_venda * (fluxo.percentual_obra / 100)
    if valor_obra > 0:
        mes_inicio_parcelas_obra = mes_venda + max(fluxo.qtd_parcelas_sinal, 1)
        qtd_parcelas_obra = mes_termino_obras - mes_inicio_parcelas_obra + 1
        if qtd_parcelas_obra > 0:
            i = fluxo.juros_parcelas_obra_am / 100
            parcela = parcela_price(valor_obra, i, qtd_parcelas_obra)
            saldo = valor_obra
            for k in range(qtd_parcelas_obra):
                mes = mes_inicio_parcelas_obra + k
                # Decomposicao Price: juros = saldo * i ; amortizacao = parcela - juros
                j = saldo * i
                amort = parcela - j
                saldo -= amort
                if 0 <= mes <= horizonte:
                    principal[mes] += amort
                    juros[mes] += j
                    # Correcao monetaria B1: fator cumulativo a partir da 1a parcela
                    if corr_m > 0:
                        fator = (1 + corr_m) ** k
                        correcao[mes] += (amort + j) * (fator - 1)
        else:
            # Venda ocorre apos o termino das obras: nao da para parcelar "durante obra".
            # Pagamento concentrado no proprio mes da venda (sem juros pq nao houve diferimento).
            mes_concentrado = mes_inicio_parcelas_obra
            if 0 <= mes_concentrado <= horizonte:
                principal[mes_concentrado] += valor_obra

    # ----- 3. BALOES ANUAIS (sem juros: parte do principal) -----
    valor_baloes = vgv_venda * (fluxo.percentual_baloes / 100)
    if valor_baloes > 0 and fluxo.qtd_baloes > 0:
        valor_balao = valor_baloes / fluxo.qtd_baloes
        for k in range(1, fluxo.qtd_baloes + 1):
            mes = mes_venda + k * 12
            if 0 <= mes <= horizonte:
                principal[mes] += valor_balao

    # ----- 4. FINANCIAMENTO POS-OBRA (Price com juros) -----
    valor_fin = vgv_venda * (fluxo.percentual_financiamento / 100)
    if valor_fin > 0 and fluxo.qtd_parcelas_financiamento > 0:
        i = fluxo.juros_financiamento_am / 100
        parcela_fin = parcela_price(valor_fin, i, fluxo.qtd_parcelas_financiamento)
        mes_inicio_fin = mes_termino_obras + 1
        saldo = valor_fin
        for k in range(fluxo.qtd_parcelas_financiamento):
            mes = mes_inicio_fin + k
            j = saldo * i
            amort = parcela_fin - j
            saldo -= amort
            if 0 <= mes <= horizonte:
                principal[mes] += amort
                juros[mes] += j

    return principal, juros, correcao


def calcular_recebimentos(
    terreno: Aba1Terreno,
    receitas: Aba2Receitas,
    horizonte: int,
    reajustes=None,
) -> dict[str, np.ndarray]:
    """
    Calcula o fluxo de recebimentos completo do empreendimento.

    Returns:
        dict com chaves:
        - 'recebimentos': total recebido em cada mes (R$) = principal + juros
        - 'recebimentos_principal': parte do recebimento que e amortizacao do preco do lote (receita nominal de venda)
        - 'recebimentos_juros': parte que e juros embutidos (receita financeira)
        - 'vendas_vgv': VGV vendido em cada mes (R$, nao recebido — soma = VGV vendavel)
        - 'vendas_qtd_lotes': quantidade de lotes vendidos em cada mes (estimativa)
        - 'vgv_vendavel': total comercializavel (depois da permuta fisica)
        - 'vgv_total_recebido': total recebido ao longo do tempo (com juros das parcelas)
    """
    vgv_vendavel = calcular_vgv_vendavel(terreno, receitas)
    mes_termino_obras = meses_entre(terreno.datas.inicio_projeto, terreno.datas.termino_obras)

    recebimentos_principal = np.zeros(horizonte + 1)
    recebimentos_juros = np.zeros(horizonte + 1)
    recebimentos_correcao = np.zeros(horizonte + 1)
    vendas_vgv = np.zeros(horizonte + 1)
    vendas_qtd = np.zeros(horizonte + 1)

    # Taxa de correcao mensal para as parcelas durante obra (B1)
    corr_m = 0.0
    if reajustes is not None and reajustes.ativo and reajustes.aplicar_correcao_parcelas:
        corr_m = reajustes.taxa_mensal_indice(reajustes.indice_parcelas)

    # Mapa nome -> fluxo, para acesso rapido
    mapa_fluxos = {f.nome: f for f in receitas.fluxos_recebiveis}

    # Total de lotes vendaveis (descontando permuta fisica)
    total_lotes_vendaveis = _calcular_total_lotes_vendaveis(terreno, receitas)

    # Para cada faixa da curva de vendas
    for faixa in receitas.curva_vendas:
        if faixa.fluxo_recebiveis not in mapa_fluxos:
            raise ValueError(f"Fluxo '{faixa.fluxo_recebiveis}' nao encontrado")
        fluxo = mapa_fluxos[faixa.fluxo_recebiveis]

        # VGV total da faixa — aplica fator de preco progressivo (1.0 = preco base)
        vgv_faixa = vgv_vendavel * (faixa.percentual_estoque / 100) * faixa.fator_preco
        # Lotes da faixa (proporcional)
        lotes_faixa = total_lotes_vendaveis * (faixa.percentual_estoque / 100)

        # Distribuir linearmente entre mes_inicio e mes_fim
        qtd_meses_faixa = faixa.mes_fim - faixa.mes_inicio + 1
        if qtd_meses_faixa <= 0:
            continue

        vgv_por_mes = vgv_faixa / qtd_meses_faixa
        lotes_por_mes = lotes_faixa / qtd_meses_faixa

        # Para cada mes de venda dentro da faixa
        for mes_venda in range(faixa.mes_inicio, faixa.mes_fim + 1):
            if mes_venda < 0 or mes_venda > horizonte:
                continue

            vendas_vgv[mes_venda] += vgv_por_mes
            vendas_qtd[mes_venda] += lotes_por_mes

            # Gerar recebimentos desta venda (principal, juros, correcao)
            principal_venda, juros_venda, correcao_venda = _gerar_recebimentos_de_uma_venda(
                vgv_venda=vgv_por_mes,
                mes_venda=mes_venda,
                fluxo=fluxo,
                mes_termino_obras=mes_termino_obras,
                horizonte=horizonte,
                corr_m=corr_m,
            )
            recebimentos_principal += principal_venda
            recebimentos_juros += juros_venda
            recebimentos_correcao += correcao_venda

    recebimentos_total = recebimentos_principal + recebimentos_juros
    recebimentos_total_com_correcao = recebimentos_total + recebimentos_correcao

    return {
        "recebimentos": recebimentos_total,
        "recebimentos_principal": recebimentos_principal,
        "recebimentos_juros": recebimentos_juros,
        "recebimentos_correcao": recebimentos_correcao,
        "recebimentos_com_correcao": recebimentos_total_com_correcao,
        "vendas_vgv": vendas_vgv,
        "vendas_qtd_lotes": vendas_qtd,
        "vgv_vendavel": vgv_vendavel,
        "vgv_efetivo_vendavel": float(vendas_vgv.sum()),
        "vgv_total_recebido": float(recebimentos_total.sum()),
    }


def _calcular_total_lotes_vendaveis(
    terreno: Aba1Terreno, receitas: Aba2Receitas
) -> float:
    """Total de lotes que entram no estoque vendavel (descontada a permuta fisica)."""
    total = 0.0
    mapa_permuta = {p.tipologia: p.percentual for p in receitas.permuta_fisica}
    for tip in terreno.tipologias:
        pct_permuta = mapa_permuta.get(tip.nome, 0.0) if receitas.tipo_permuta == "fisica" else 0
        total += tip.quantidade * (1 - pct_permuta / 100)
    return total


def simular_lote_unitario(
    valor_lote: float,
    fluxo: FluxoRecebiveis,
    mes_venda: int,
    mes_termino_obras: int,
) -> list[dict]:
    """
    Simula o cronograma de pagamentos de UM lote.

    Util para preencher a 'tabela de simulacao' que o usuario pediu na Aba 2.

    Returns:
        Lista de dicts com chaves:
        - mes: mes relativo a M0
        - tipo: 'sinal' / 'parcela_obra' / 'balao' / 'parcela_financiamento'
        - valor: R$ total da parcela
        - principal: parte que e amortizacao (R$)
        - juros: parte que e juros embutidos (R$)
        - saldo_devedor: saldo devedor apos a parcela (R$, zero se nao aplicavel)
    """
    cronograma: list[dict] = []

    # Sinal (sem juros)
    valor_sinal = valor_lote * (fluxo.percentual_sinal / 100)
    if valor_sinal > 0:
        parcela_sinal = valor_sinal / fluxo.qtd_parcelas_sinal
        for k in range(fluxo.qtd_parcelas_sinal):
            cronograma.append({
                "mes": mes_venda + k,
                "tipo": "sinal",
                "valor": parcela_sinal,
                "principal": parcela_sinal,
                "juros": 0.0,
                "saldo_devedor": 0.0,
            })

    # Parcelas durante obra (Price com juros)
    valor_obra = valor_lote * (fluxo.percentual_obra / 100)
    if valor_obra > 0:
        mes_inicio = mes_venda + max(fluxo.qtd_parcelas_sinal, 1)
        qtd = mes_termino_obras - mes_inicio + 1
        if qtd > 0:
            i = fluxo.juros_parcelas_obra_am / 100
            parcela = parcela_price(valor_obra, i, qtd)
            saldo = valor_obra
            for k in range(qtd):
                j = saldo * i
                amort = parcela - j
                saldo -= amort
                cronograma.append({
                    "mes": mes_inicio + k,
                    "tipo": "parcela_obra",
                    "valor": parcela,
                    "principal": amort,
                    "juros": j,
                    "saldo_devedor": max(saldo, 0.0),
                })

    # Baloes (sem juros)
    valor_baloes = valor_lote * (fluxo.percentual_baloes / 100)
    if valor_baloes > 0 and fluxo.qtd_baloes > 0:
        valor_balao = valor_baloes / fluxo.qtd_baloes
        for k in range(1, fluxo.qtd_baloes + 1):
            cronograma.append({
                "mes": mes_venda + k * 12,
                "tipo": "balao",
                "valor": valor_balao,
                "principal": valor_balao,
                "juros": 0.0,
                "saldo_devedor": 0.0,
            })

    # Financiamento pos-obra (Price com juros)
    valor_fin = valor_lote * (fluxo.percentual_financiamento / 100)
    if valor_fin > 0 and fluxo.qtd_parcelas_financiamento > 0:
        i = fluxo.juros_financiamento_am / 100
        parcela_fin = parcela_price(valor_fin, i, fluxo.qtd_parcelas_financiamento)
        mes_inicio_fin = mes_termino_obras + 1
        saldo = valor_fin
        for k in range(fluxo.qtd_parcelas_financiamento):
            j = saldo * i
            amort = parcela_fin - j
            saldo -= amort
            cronograma.append({
                "mes": mes_inicio_fin + k,
                "tipo": "parcela_financiamento",
                "valor": parcela_fin,
                "principal": amort,
                "juros": j,
                "saldo_devedor": max(saldo, 0.0),
            })

    cronograma.sort(key=lambda x: x["mes"])
    return cronograma
