"""
Engine de despesas: distribui as saidas de caixa no tempo.

Modulos cobertos:
- Aquisicao do terreno (a vista, parcelado, sem desembolso)
- Custos de obra (resumido ou detalhado, com curvas linear/S/customizada)
- Despesas de desenvolvimento (projetos, licencas, marketing)
- Administracao
- Comissao de venda (sobre venda, sobre recebimento ou misto)
- Impostos (regime caixa ou competencia)
- Permuta financeira
"""

from __future__ import annotations

import numpy as np

from ..modelos import (
    Aba3Obras,
    Aba4Desenvolvimento,
    Aba5Impostos,
    AquisicaoTerreno,
    EtapaObra,
    QuadroAreas,
)
from .utilidades import gerar_curva_linear, gerar_curva_s


# =====================================================================
# TERRENO
# =====================================================================

def calcular_desembolso_terreno(
    aquisicao: AquisicaoTerreno,
    horizonte: int,
    reajustes=None,
) -> dict[str, np.ndarray]:
    """
    Calcula o desembolso da aquisicao do terreno + cartorio.

    Returns:
        dict com:
        - 'terreno': pagamento do valor de compra (R$/mes)
        - 'cartorio': custos de cartorio (R$/mes)
    """
    terreno = np.zeros(horizonte + 1)
    cartorio = np.zeros(horizonte + 1)

    # Pagamento do terreno
    if aquisicao.forma_pagamento == "a_vista":
        if 0 <= aquisicao.mes_pagamento <= horizonte:
            terreno[aquisicao.mes_pagamento] += aquisicao.valor_total
    elif aquisicao.forma_pagamento == "parcelado":
        parcela = aquisicao.valor_total / aquisicao.qtd_parcelas
        for k in range(aquisicao.qtd_parcelas):
            mes = aquisicao.mes_inicio_parcelas + k
            if 0 <= mes <= horizonte:
                terreno[mes] += parcela
    elif aquisicao.forma_pagamento == "customizado":
        for k, pct in enumerate(aquisicao.fluxo_percentuais):
            mes = aquisicao.fluxo_mes_inicio + k
            if 0 <= mes <= horizonte and pct > 0:
                terreno[mes] += aquisicao.valor_total * (pct / 100)
    # 'sem_desembolso': nada e lancado no fluxo de caixa

    # Cartorio
    if aquisicao.custo_cartorio > 0 and 0 <= aquisicao.mes_pagamento_cartorio <= horizonte:
        cartorio[aquisicao.mes_pagamento_cartorio] += aquisicao.custo_cartorio

    # Correcao monetaria do terreno parcelado (B1)
    if (
        reajustes is not None
        and reajustes.ativo
        and reajustes.aplicar_correcao_terreno
        and aquisicao.forma_pagamento in ("parcelado", "customizado")
    ):
        corr_m = reajustes.taxa_mensal_indice(reajustes.indice_terreno)
        if corr_m > 0:
            for mes in range(horizonte + 1):
                if terreno[mes] > 0:
                    terreno[mes] *= (1 + corr_m) ** mes

    return {"terreno": terreno, "cartorio": cartorio}


# =====================================================================
# OBRAS
# =====================================================================

def _distribuir_etapa(etapa: EtapaObra, horizonte: int) -> np.ndarray:
    """Distribui uma etapa de obra no tempo conforme sua curva."""
    vetor = np.zeros(horizonte + 1)

    if etapa.curva == "linear":
        pesos = gerar_curva_linear(etapa.duracao_meses)
    elif etapa.curva == "s_curve":
        pesos = gerar_curva_s(etapa.duracao_meses)
    else:  # customizada
        pesos = [p / 100 for p in etapa.curva_customizada]

    for k, peso in enumerate(pesos):
        mes = etapa.mes_inicio + k
        if 0 <= mes <= horizonte:
            vetor[mes] += etapa.valor_total * peso

    return vetor


def calcular_desembolso_obras(
    obras: Aba3Obras,
    areas: QuadroAreas,
    horizonte: int,
    reajustes=None,
) -> dict[str, np.ndarray | float]:
    """
    Calcula desembolso de obras mes a mes.

    Aplica BDI e contingencia sobre o custo direto:
        custo_total = custo_direto * (1 + bdi%) * (1 + contingencia%)

    Returns:
        dict com:
        - 'obras_total': desembolso de obras (R$/mes, ja com BDI e contingencia)
        - 'custo_direto': total sem BDI e contingencia
        - 'custo_total': total com BDI e contingencia
        - 'detalhamento_etapas': dict {nome_etapa: vetor mes a mes (com BDI/contingencia)}
    """
    detalhamento: dict[str, np.ndarray] = {}
    custo_direto = 0.0

    if obras.modo == "resumido":
        assert obras.resumido is not None
        # Calcula valor total
        if obras.resumido.base_calculo == "sistema_viario":
            base_m2 = areas.area_sistema_viario_m2
        else:
            base_m2 = areas.area_lotes_m2
        valor_total = base_m2 * obras.resumido.valor_por_m2
        custo_direto = valor_total

        # Cria uma "etapa" virtual para reusar a logica
        etapa_virtual = EtapaObra(
            nome="Obras (resumido)",
            valor_total=valor_total,
            mes_inicio=obras.resumido.mes_inicio,
            duracao_meses=obras.resumido.duracao_meses,
            curva=obras.resumido.curva,
        )
        detalhamento[etapa_virtual.nome] = _distribuir_etapa(etapa_virtual, horizonte)

    else:  # detalhado
        for etapa in obras.etapas:
            custo_direto += etapa.valor_total
            detalhamento[etapa.nome] = _distribuir_etapa(etapa, horizonte)

    # Aplicar BDI e contingencia (multiplicador uniforme em todas as etapas)
    multiplicador = (1 + obras.bdi_percentual / 100) * (1 + obras.contingencia_percentual / 100)
    custo_total = custo_direto * multiplicador

    obras_total = np.zeros(horizonte + 1)
    for nome, vet in detalhamento.items():
        vet_corrigido = vet * multiplicador
        detalhamento[nome] = vet_corrigido
        obras_total += vet_corrigido

    # Correcao por INCC (B1): cada mes e multiplicado por (1+incc_m)^mes
    custo_base_constante = custo_total  # custo em precos constantes
    if reajustes is not None and reajustes.ativo and reajustes.aplicar_incc_obras:
        incc_m = reajustes.taxa_mensal_indice("incc")
        if incc_m > 0:
            for mes in range(horizonte + 1):
                fator = (1 + incc_m) ** mes
                obras_total[mes] *= fator
            for nome in list(detalhamento.keys()):
                det = detalhamento[nome].copy()
                for mes in range(horizonte + 1):
                    det[mes] *= (1 + incc_m) ** mes
                detalhamento[nome] = det
            custo_total = float(obras_total.sum())

    return {
        "obras_total": obras_total,
        "custo_direto": custo_direto,
        "custo_total": custo_total,
        "custo_base_constante": custo_base_constante,
        "detalhamento_etapas": detalhamento,
    }


# =====================================================================
# DESPESAS DE DESENVOLVIMENTO (PROJETOS, LICENCAS, MARKETING)
# =====================================================================

def calcular_despesas_desenvolvimento(
    desenvolvimento: Aba4Desenvolvimento,
    horizonte: int,
    recebimentos: np.ndarray,
) -> dict[str, np.ndarray]:
    """
    Distribui as despesas de desenvolvimento + administracao no tempo.

    Returns:
        dict com:
        - 'projetos': desembolso categoria projetos (R$/mes)
        - 'licenciamento': desembolso categoria licenciamento
        - 'marketing': desembolso categoria marketing
        - 'outros': demais
        - 'administracao': admin
        - 'total': soma de tudo
    """
    categorias = {
        "projetos": np.zeros(horizonte + 1),
        "licenciamento": np.zeros(horizonte + 1),
        "marketing": np.zeros(horizonte + 1),
        "outros": np.zeros(horizonte + 1),
    }

    # Cada despesa vai para o vetor da sua categoria
    for desp in desenvolvimento.despesas:
        vetor = _distribuir_despesa_temporal(desp, horizonte)
        categorias[desp.categoria] += vetor

    # Administracao
    administracao = _calcular_administracao(
        desenvolvimento.administracao, horizonte, recebimentos
    )

    total = (
        categorias["projetos"]
        + categorias["licenciamento"]
        + categorias["marketing"]
        + categorias["outros"]
        + administracao
    )

    return {
        **categorias,
        "administracao": administracao,
        "total": total,
    }


def _distribuir_despesa_temporal(desp, horizonte: int) -> np.ndarray:
    """Distribui uma DespesaTemporal no tempo conforme seu modo."""
    vetor = np.zeros(horizonte + 1)

    if desp.modo == "a_vista":
        if desp.mes_pagamento is not None and 0 <= desp.mes_pagamento <= horizonte:
            vetor[desp.mes_pagamento] += desp.valor_total

    elif desp.modo == "parcelado_linear":
        if desp.mes_inicio is not None and desp.mes_fim is not None:
            qtd = desp.mes_fim - desp.mes_inicio + 1
            if qtd > 0:
                parcela = desp.valor_total / qtd
                for k in range(qtd):
                    mes = desp.mes_inicio + k
                    if 0 <= mes <= horizonte:
                        vetor[mes] += parcela

    elif desp.modo == "distribuicao_customizada":
        if desp.mes_inicio is not None:
            for k, pct in enumerate(desp.distribuicao_percentual):
                mes = desp.mes_inicio + k
                if 0 <= mes <= horizonte:
                    vetor[mes] += desp.valor_total * (pct / 100)

    return vetor


def _calcular_administracao(
    admin, horizonte: int, recebimentos: np.ndarray
) -> np.ndarray:
    """Calcula o vetor mensal de administracao: % sobre a receita do mes."""
    vetor = np.zeros(horizonte + 1)
    for mes in range(horizonte + 1):
        vetor[mes] = recebimentos[mes] * (admin.percentual / 100)
    return vetor


# =====================================================================
# COMISSAO DE VENDA
# =====================================================================

def calcular_comissao(
    impostos: Aba5Impostos,
    vendas_vgv: np.ndarray,
    recebimentos: np.ndarray,
    horizonte: int,
) -> np.ndarray:
    """
    Calcula a comissao mes a mes conforme o modo de pagamento.

    Args:
        vendas_vgv: VGV vendido em cada mes (do modulo recebimentos)
        recebimentos: total recebido em cada mes
    """
    com = impostos.comissao
    pct = com.percentual_vgv / 100
    comissao = np.zeros(horizonte + 1)

    if com.modo_pagamento == "sobre_venda":
        comissao = vendas_vgv * pct

    elif com.modo_pagamento == "sobre_recebimento":
        # Comissao paga proporcional ao que foi recebido
        # vgv_total recebido pode ser diferente do VGV vendido (juros embutidos)
        # Usamos a logica: comissao_total = pct * VGV_vendido
        # e distribuimos proporcionalmente aos recebimentos
        vgv_vendido_total = float(vendas_vgv.sum())
        recebido_total = float(recebimentos.sum())
        if recebido_total > 0:
            comissao_total = vgv_vendido_total * pct
            comissao = recebimentos * (comissao_total / recebido_total)

    elif com.modo_pagamento == "misto":
        # X% no ato + Y% diluido nas N primeiras parcelas
        no_ato = vendas_vgv * pct * (com.misto_percentual_no_ato / 100)
        comissao += no_ato

        diluido_pct = pct * (1 - com.misto_percentual_no_ato / 100)
        # Para cada mes de venda, distribuir o valor diluido nas N proximas parcelas
        for mes in range(horizonte + 1):
            if vendas_vgv[mes] > 0:
                valor_diluido = vendas_vgv[mes] * diluido_pct
                parcela = valor_diluido / com.misto_qtd_parcelas
                # Distribui a partir do mes seguinte
                for k in range(1, com.misto_qtd_parcelas + 1):
                    m = mes + k
                    if 0 <= m <= horizonte:
                        comissao[m] += parcela

    return comissao


# =====================================================================
# IMPOSTOS
# =====================================================================

def calcular_impostos(
    impostos: Aba5Impostos,
    vendas_vgv: np.ndarray,
    recebimentos: np.ndarray,
    horizonte: int,
) -> np.ndarray:
    """
    Calcula impostos sobre receita mes a mes.

    - Regime caixa: aliquota * recebimentos[mes]
    - Regime competencia: aliquota * vendas_vgv[mes]
    """
    aliq = impostos.tributos.aliquota_total / 100

    if impostos.tributos.regime_apuracao == "caixa":
        return recebimentos * aliq
    return vendas_vgv * aliq


# =====================================================================
# PERMUTA FINANCEIRA
# =====================================================================

def calcular_permuta_financeira(
    impostos: Aba5Impostos,
    recebimentos: np.ndarray,
    vendas_vgv: np.ndarray,
    vgv_vendavel: float,
    mes_termino_obras: int,
    horizonte: int,
) -> np.ndarray:
    """
    Calcula pagamentos ao permutante financeiro mes a mes.

    Suporta:
    - descontos: base efetiva = recebimentos * (1 - total_descontos%)
    - fluxo 'padrao': proporcional aos recebimentos (ou apos marco)
    - fluxo 'personalizado': retencao nos primeiros N meses + quitacao corrigida

    Returns:
        Vetor de pagamentos (R$/mes).
    """
    pagamentos = np.zeros(horizonte + 1)
    pf = impostos.permuta_financeira

    if pf is None:
        return pagamentos

    pct = pf.percentual_vgv / 100

    # Aplicar descontos: base = recebimentos apos deducoes
    desconto_frac = min(pf.descontos.total / 100, 1.0)
    base = recebimentos * (1.0 - desconto_frac)

    # --- Calcular vetor de pagamentos normais (sem retencao) ---
    normais = np.zeros(horizonte + 1)

    if pf.modo_pagamento == "sobre_recebimento":
        normais = base * pct

    elif pf.modo_pagamento == "apos_marco":
        if pf.marco_tipo == "termino_obras":
            mes_inicio = mes_termino_obras
            base_apos = base[mes_inicio:].sum()
            if base_apos > 0:
                total = vgv_vendavel * (1.0 - desconto_frac) * pct
                fator = total / base_apos
                for mes in range(mes_inicio, horizonte + 1):
                    normais[mes] = base[mes] * fator

        elif pf.marco_tipo == "percentual_vendas":
            vendas_acum = np.cumsum(vendas_vgv)
            marco_valor = vgv_vendavel * (pf.marco_percentual_vendas / 100)
            mes_inicio = horizonte + 1
            for m in range(horizonte + 1):
                if vendas_acum[m] >= marco_valor:
                    mes_inicio = m
                    break
            if mes_inicio <= horizonte:
                base_apos = base[mes_inicio:].sum()
                if base_apos > 0:
                    total = vgv_vendavel * (1.0 - desconto_frac) * pct
                    fator = total / base_apos
                    for mes in range(mes_inicio, horizonte + 1):
                        normais[mes] = base[mes] * fator

    # --- Aplicar retencao se fluxo personalizado ---
    if pf.fluxo == "personalizado":
        ret = pf.retencao
        total_retido = 0.0
        frac_ret = ret.percentual_retencao / 100

        for mes in range(horizonte + 1):
            normal = normais[mes]
            if mes < ret.meses_retencao:
                pagamentos[mes] = normal * (1.0 - frac_ret)
                total_retido += normal * frac_ret
            else:
                pagamentos[mes] = normal

        # Quitar retido com correcao, em parcelas a partir de mes_retencao
        if total_retido > 0 and ret.qtd_parcelas_quitacao > 0:
            fator_corr = (1 + ret.correcao_aa / 100) ** (ret.meses_retencao / 12)
            total_a_quitar = total_retido * fator_corr
            parcela_quit = total_a_quitar / ret.qtd_parcelas_quitacao
            for k in range(ret.qtd_parcelas_quitacao):
                mes = ret.meses_retencao + k
                if 0 <= mes <= horizonte:
                    pagamentos[mes] += parcela_quit
    else:
        pagamentos = normais

    return pagamentos
