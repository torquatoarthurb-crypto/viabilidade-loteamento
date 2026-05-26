"""
Engine de recebimentos: calcula as entradas de caixa mes a mes.

Logica geral (novo design — por tipologia):
1. Para cada FluxoTipologia em receitas.fluxos_tipologia:
   a. Calcula VGV vendavel desta tipologia (descontando permuta fisica)
   b. Aplica a curva de vendas mensal da tipologia ({mes: % do estoque})
   c. Para cada mes de venda, gera o fluxo de parcelas usando o fluxo da tipologia
2. Soma todos os vetores de recebimento
"""

from __future__ import annotations

import numpy as np

from ..modelos import Aba1Terreno, Aba2Receitas, FluxoRecebiveis
from .utilidades import meses_entre, parcela_price


def calcular_vgv_vendavel(terreno: Aba1Terreno, receitas: Aba2Receitas) -> float:
    """
    VGV vendavel = VGV bruto - permuta fisica.

    Permuta financeira NAO desconta aqui (e tratada como saida no fluxo de caixa).
    """
    vgv_bruto = terreno.vgv_bruto

    if receitas.tipo_permuta != "fisica" or not receitas.permuta_fisica:
        return vgv_bruto

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

    Returns:
        Tupla (principal, juros, correcao) com arrays de tamanho (horizonte+1,).
    """
    principal = np.zeros(horizonte + 1)
    juros = np.zeros(horizonte + 1)
    correcao = np.zeros(horizonte + 1)

    # 1. SINAL (sem juros)
    valor_sinal = vgv_venda * (fluxo.percentual_sinal / 100)
    if valor_sinal > 0 and fluxo.qtd_parcelas_sinal > 0:
        parcela_sinal = valor_sinal / fluxo.qtd_parcelas_sinal
        for k in range(fluxo.qtd_parcelas_sinal):
            mes = mes_venda + k
            if 0 <= mes <= horizonte:
                principal[mes] += parcela_sinal

    # 2. PARCELAS DURANTE OBRA (Price com juros)
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
                j = saldo * i
                amort = parcela - j
                saldo -= amort
                if 0 <= mes <= horizonte:
                    principal[mes] += amort
                    juros[mes] += j
                    if corr_m > 0:
                        fator = (1 + corr_m) ** k
                        correcao[mes] += (amort + j) * (fator - 1)
        else:
            # Venda apos o termino das obras: concentrar no mes da venda
            mes_concentrado = mes_inicio_parcelas_obra
            if 0 <= mes_concentrado <= horizonte:
                principal[mes_concentrado] += valor_obra

    # 3. BALOES ANUAIS (sem juros)
    valor_baloes = vgv_venda * (fluxo.percentual_baloes / 100)
    if valor_baloes > 0 and fluxo.qtd_baloes > 0:
        valor_balao = valor_baloes / fluxo.qtd_baloes
        for k in range(1, fluxo.qtd_baloes + 1):
            mes = mes_venda + k * 12
            if 0 <= mes <= horizonte:
                principal[mes] += valor_balao

    # 4. FINANCIAMENTO POS-OBRA (Price com juros)
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

    Itera sobre fluxos_tipologia (novo design): cada tipologia tem seu proprio
    fluxo de recebiveis e curva de vendas mensal.

    Returns:
        dict com chaves:
        - 'recebimentos': total recebido em cada mes (R$)
        - 'recebimentos_principal': amortizacao do preco do lote (receita nominal)
        - 'recebimentos_juros': juros embutidos (receita financeira)
        - 'recebimentos_correcao': correcao monetaria sobre parcelas obra
        - 'recebimentos_com_correcao': total incluindo correcao
        - 'vendas_vgv': VGV vendido em cada mes (R$)
        - 'vendas_qtd_lotes': quantidade de lotes vendidos por mes
        - 'vgv_vendavel': total comercializavel (depois da permuta fisica)
        - 'vgv_efetivo_vendavel': soma do VGV efetivamente vendido
        - 'vgv_total_recebido': total recebido ao longo do tempo (com juros)
    """
    mes_termino_obras = meses_entre(terreno.datas.inicio_projeto, terreno.datas.termino_obras)

    recebimentos_principal = np.zeros(horizonte + 1)
    recebimentos_juros = np.zeros(horizonte + 1)
    recebimentos_correcao = np.zeros(horizonte + 1)
    vendas_vgv = np.zeros(horizonte + 1)
    vendas_qtd = np.zeros(horizonte + 1)

    corr_m = 0.0
    if reajustes is not None and reajustes.ativo and reajustes.aplicar_correcao_parcelas:
        corr_m = reajustes.taxa_mensal_indice(reajustes.indice_parcelas)

    if receitas.fluxos_tipologia:
        _calcular_por_tipologia(
            terreno, receitas, horizonte, mes_termino_obras, corr_m,
            recebimentos_principal, recebimentos_juros, recebimentos_correcao,
            vendas_vgv, vendas_qtd,
        )
    else:
        # Fallback: formato legado (fluxos_recebiveis + curva_vendas)
        _calcular_legado(
            terreno, receitas, horizonte, mes_termino_obras, corr_m,
            recebimentos_principal, recebimentos_juros, recebimentos_correcao,
            vendas_vgv, vendas_qtd,
        )

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
        "vgv_vendavel": calcular_vgv_vendavel(terreno, receitas),
        "vgv_efetivo_vendavel": float(vendas_vgv.sum()),
        "vgv_total_recebido": float(recebimentos_total.sum()),
    }


def _calcular_por_tipologia(
    terreno, receitas, horizonte, mes_termino_obras, corr_m,
    recebimentos_principal, recebimentos_juros, recebimentos_correcao,
    vendas_vgv, vendas_qtd,
) -> None:
    """Logica principal do novo design: itera sobre FluxoTipologia."""
    mapa_tip = {t.nome: t for t in terreno.tipologias}
    mapa_permuta = (
        {p.tipologia: p.percentual for p in receitas.permuta_fisica}
        if receitas.tipo_permuta == "fisica" else {}
    )

    for ft in receitas.fluxos_tipologia:
        nome_tip = ft.nome_tipologia
        tip = mapa_tip.get(nome_tip)
        if tip is None:
            continue

        pct_permuta = mapa_permuta.get(nome_tip, 0.0)
        vgv_tip_vendavel = tip.vgv_total * (1 - pct_permuta / 100)
        lotes_tip_vendaveis = tip.quantidade * (1 - pct_permuta / 100)

        if vgv_tip_vendavel <= 0 or not ft.curva_mensal:
            continue

        try:
            fluxo = ft.as_fluxo_recebiveis()
        except Exception:
            continue

        for mes_str, pct in ft.curva_mensal.items():
            mes_venda = int(mes_str)
            if pct <= 0 or mes_venda < 0 or mes_venda > horizonte:
                continue

            fator = float(ft.fatores_preco.get(mes_venda, ft.fatores_preco.get(str(mes_venda), 1.0))) if ft.fatores_preco else 1.0
            vgv_venda = vgv_tip_vendavel * (pct / 100) * fator
            lotes_venda = lotes_tip_vendaveis * (pct / 100)

            vendas_vgv[mes_venda] += vgv_venda
            vendas_qtd[mes_venda] += lotes_venda

            p_v, j_v, c_v = _gerar_recebimentos_de_uma_venda(
                vgv_venda=vgv_venda,
                mes_venda=mes_venda,
                fluxo=fluxo,
                mes_termino_obras=mes_termino_obras,
                horizonte=horizonte,
                corr_m=corr_m,
            )
            recebimentos_principal += p_v
            recebimentos_juros += j_v
            recebimentos_correcao += c_v


def _calcular_legado(
    terreno, receitas, horizonte, mes_termino_obras, corr_m,
    recebimentos_principal, recebimentos_juros, recebimentos_correcao,
    vendas_vgv, vendas_qtd,
) -> None:
    """Fallback para projetos antigos ainda com fluxos_recebiveis + curva_vendas."""
    vgv_vendavel = calcular_vgv_vendavel(terreno, receitas)
    mapa_fluxos = {f.nome: f for f in receitas.fluxos_recebiveis}
    total_lotes_vendaveis = _calcular_total_lotes_vendaveis(terreno, receitas)

    for faixa in receitas.curva_vendas:
        if faixa.fluxo_recebiveis not in mapa_fluxos:
            continue
        fluxo = mapa_fluxos[faixa.fluxo_recebiveis]

        vgv_faixa = vgv_vendavel * (faixa.percentual_estoque / 100) * faixa.fator_preco
        lotes_faixa = total_lotes_vendaveis * (faixa.percentual_estoque / 100)

        qtd_meses_faixa = faixa.mes_fim - faixa.mes_inicio + 1
        if qtd_meses_faixa <= 0:
            continue

        vgv_por_mes = vgv_faixa / qtd_meses_faixa
        lotes_por_mes = lotes_faixa / qtd_meses_faixa

        for mes_venda in range(faixa.mes_inicio, faixa.mes_fim + 1):
            if mes_venda < 0 or mes_venda > horizonte:
                continue

            vendas_vgv[mes_venda] += vgv_por_mes
            vendas_qtd[mes_venda] += lotes_por_mes

            p_v, j_v, c_v = _gerar_recebimentos_de_uma_venda(
                vgv_venda=vgv_por_mes,
                mes_venda=mes_venda,
                fluxo=fluxo,
                mes_termino_obras=mes_termino_obras,
                horizonte=horizonte,
                corr_m=corr_m,
            )
            recebimentos_principal += p_v
            recebimentos_juros += j_v
            recebimentos_correcao += c_v


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

    Returns:
        Lista de dicts com: mes, tipo, valor, principal, juros, saldo_devedor.
    """
    cronograma: list[dict] = []

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
