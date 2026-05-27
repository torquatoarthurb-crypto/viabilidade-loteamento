"""
Engine de fluxo de caixa: consolida todas as entradas e saidas em uma tabela mensal.

Tambem calcula os indicadores financeiros: VPL, TIR, payback, exposicao maxima.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..modelos import Projeto
from .indicadores_financeiros import irr, npv
from .despesas import (
    calcular_comissao,
    calcular_desembolso_obras,
    calcular_desembolso_terreno,
    calcular_despesas_desenvolvimento,
    calcular_impostos,
    calcular_permuta_financeira,
)
from .financiamento_engine import simular_financiamento
from .recebimentos import calcular_recebimentos
from .utilidades import meses_entre


@dataclass
class ResultadoCalculo:
    """Resultado completo do calculo de viabilidade."""

    # Tabela mestre do fluxo de caixa (DataFrame com colunas por mes)
    fluxo_caixa: pd.DataFrame

    # Resumo numerico (totais consolidados)
    resumo: dict = field(default_factory=dict)

    # Indicadores financeiros
    indicadores: dict = field(default_factory=dict)

    # Detalhamento de etapas de obra (para graficos)
    etapas_obra: dict = field(default_factory=dict)

    # Horizonte (ultimo mes do projeto)
    horizonte: int = 0


def _calcular_horizonte(projeto: Projeto) -> int:
    """
    Calcula o horizonte do projeto em meses (relativo a M0).

    Conforme documento: maior valor entre termino_obras e
    (data ultima parcela + 2 meses).

    Como nao temos uma data fixa de "ultima parcela" (depende da curva e dos fluxos),
    calculamos o ultimo mes em que cada faixa da curva pode gerar um recebimento:
        ultimo_mes_venda + max(qtd_parcelas_sinal,
                                qtd_meses_obra (ate termino),
                                qtd_baloes * 12,
                                qtd_parcelas_financiamento + meses_ate_termino_obra)
    e adicionamos 2 meses de buffer.
    """
    inicio = projeto.terreno.datas.inicio_projeto
    mes_termino_obras = meses_entre(inicio, projeto.terreno.datas.termino_obras)

    # Maior mes de venda (novo formato: fluxos_tipologia; legado: curva_vendas)
    if projeto.receitas.fluxos_tipologia:
        meses_venda_iter = [
            int(m)
            for ft in projeto.receitas.fluxos_tipologia
            for m in ft.curva_mensal.keys()
            if float(ft.curva_mensal[m]) > 0
        ]
        ultimo_mes_venda = max(meses_venda_iter) if meses_venda_iter else mes_termino_obras
    else:
        curva = projeto.receitas.curva_vendas
        ultimo_mes_venda = max(f.mes_fim for f in curva) if curva else mes_termino_obras

    # Maior horizonte de fluxo
    horizonte_fluxo = 0

    if projeto.receitas.fluxos_tipologia:
        for ft in projeto.receitas.fluxos_tipologia:
            try:
                fluxo = ft.as_fluxo_recebiveis()
            except Exception:
                continue
            h_sinal = ultimo_mes_venda + max(fluxo.qtd_parcelas_sinal, 1) - 1
            h_obra = mes_termino_obras
            h_baloes = ultimo_mes_venda + fluxo.qtd_baloes * 12 if fluxo.qtd_baloes > 0 else 0
            h_fin = (mes_termino_obras + fluxo.qtd_parcelas_financiamento
                     if fluxo.qtd_parcelas_financiamento > 0 else 0)
            horizonte_fluxo = max(horizonte_fluxo, h_sinal, h_obra, h_baloes, h_fin)
    else:
        for fluxo in projeto.receitas.fluxos_recebiveis:
            h_sinal = ultimo_mes_venda + max(fluxo.qtd_parcelas_sinal, 1) - 1
            h_obra = mes_termino_obras
            h_baloes = (
                ultimo_mes_venda + fluxo.qtd_baloes * 12 if fluxo.qtd_baloes > 0 else 0
            )
            h_fin = (
                mes_termino_obras + fluxo.qtd_parcelas_financiamento
                if fluxo.qtd_parcelas_financiamento > 0 else 0
            )
            horizonte_fluxo = max(horizonte_fluxo, h_sinal, h_obra, h_baloes, h_fin)

    # Adiciona 2 meses de buffer (conforme regra do documento)
    return max(mes_termino_obras, horizonte_fluxo) + 2


def calcular_fluxo_caixa(projeto: Projeto) -> ResultadoCalculo:
    """
    Funcao principal: recebe um Projeto e devolve o resultado completo.

    Esta e a "porta de entrada" da engine. Tudo o mais e detalhe de calculo.
    """
    horizonte = _calcular_horizonte(projeto)
    n = horizonte + 1
    meses = list(range(n))

    reajustes = projeto.reajustes if projeto.reajustes.ativo else None

    # ----- 1. RECEBIMENTOS -----
    rec_data = calcular_recebimentos(projeto.terreno, projeto.receitas, horizonte, reajustes)
    recebimentos = rec_data["recebimentos"]
    recebimentos_principal = rec_data["recebimentos_principal"]
    recebimentos_juros = rec_data["recebimentos_juros"]
    recebimentos_correcao = rec_data["recebimentos_correcao"]
    recebimentos_com_correcao = rec_data["recebimentos_com_correcao"]
    vendas_vgv = rec_data["vendas_vgv"]
    vgv_vendavel = rec_data["vgv_vendavel"]

    # ----- 2. TERRENO -----
    terreno_data = calcular_desembolso_terreno(projeto.aquisicao, horizonte, reajustes)
    desembolso_terreno = terreno_data["terreno"]
    cartorio = terreno_data["cartorio"]

    # ----- 3. OBRAS -----
    obras_data = calcular_desembolso_obras(
        projeto.obras, projeto.terreno.areas, horizonte, reajustes
    )
    obras_total = obras_data["obras_total"]

    # ----- 4. DESPESAS DE DESENVOLVIMENTO -----
    desenv_data = calcular_despesas_desenvolvimento(
        projeto.desenvolvimento,
        horizonte,
        recebimentos,
    )

    # ----- 5. COMISSAO -----
    # Base de calculo: recebimentos com correcao (se reajuste ativo)
    recebimentos_base_fiscal = recebimentos_com_correcao
    comissao = calcular_comissao(projeto.impostos, vendas_vgv, recebimentos_base_fiscal, horizonte)

    # ----- 6. IMPOSTOS -----
    impostos_vec = calcular_impostos(
        projeto.impostos, vendas_vgv, recebimentos_base_fiscal, horizonte
    )

    # ----- 7. PERMUTA FINANCEIRA -----
    mes_termino_obras = meses_entre(
        projeto.terreno.datas.inicio_projeto, projeto.terreno.datas.termino_obras
    )
    permuta_fin = calcular_permuta_financeira(
        projeto.impostos,
        recebimentos,
        vendas_vgv,
        vgv_vendavel,
        mes_termino_obras,
        horizonte,
    )

    # ----- 8. OUTRAS RECEITAS (aportes, receitas financeiras, etc.) -----
    outras_rec = np.zeros(n)
    for _item in projeto.receitas.outras_receitas:
        if _item.valor_total <= 0:
            continue
        _dur = max(1, _item.mes_fim - _item.mes_inicio + 1)
        _val = _item.valor_total / _dur
        for _m in range(_item.mes_inicio, _item.mes_fim + 1):
            if 0 <= _m < n:
                outras_rec[_m] += _val

    # ----- 9. CONSOLIDAR EM DATAFRAME -----
    df = pd.DataFrame({"Mes": meses})

    # Entradas
    df["Receita Nominal Venda"] = recebimentos_principal
    df["Receita Financeira (Juros)"] = recebimentos_juros
    df["Correcao Monetaria (Parcelas)"] = recebimentos_correcao
    df["Outras Receitas"] = outras_rec
    df["Total Entradas"] = recebimentos_com_correcao + outras_rec

    # Saidas
    df["Aquisicao Terreno"] = desembolso_terreno
    df["Cartorio"] = cartorio
    df["Obras"] = obras_total
    df["Projetos"] = desenv_data["projetos"]
    df["Licenciamento"] = desenv_data["licenciamento"]
    df["Marketing"] = desenv_data["marketing"]
    df["Outros Desenvolvimento"] = desenv_data["outros"]
    df["Administracao"] = desenv_data["administracao"]
    df["Comissao"] = comissao
    df["Impostos"] = impostos_vec
    df["Permuta Financeira"] = permuta_fin

    df["Total Saidas"] = (
        df["Aquisicao Terreno"]
        + df["Cartorio"]
        + df["Obras"]
        + df["Projetos"]
        + df["Licenciamento"]
        + df["Marketing"]
        + df["Outros Desenvolvimento"]
        + df["Administracao"]
        + df["Comissao"]
        + df["Impostos"]
        + df["Permuta Financeira"]
    )

    df["Saldo do Mes"] = df["Total Entradas"] - df["Total Saidas"]
    df["Saldo Acumulado"] = df["Saldo do Mes"].cumsum()

    # ----- 9. INDICADORES BASE (sem financiamento) -----
    fluxo_base = df["Saldo do Mes"].to_numpy()
    tma_mensal = projeto.parametros.tma_mensal
    indicadores_base = _calcular_indicadores(fluxo_base, tma_mensal)

    # ----- 9b. FINANCIAMENTO (banco e/ou investidor-emprestimo) -----
    _inv_emp = (
        getattr(projeto.financiamento, "ativo_investidor", False)
        and getattr(projeto.financiamento, "modo_investidor", "pct_negocio") == "emprestimo"
    )
    fin_data = None
    if projeto.financiamento.ativo or _inv_emp:
        # Vetores acumulados para os gatilhos de liberacao (0-100%)
        _total_obras = float(obras_total.sum())
        _total_vgv = float(vgv_vendavel) if vgv_vendavel > 0 else 1.0
        pct_obras_acum = np.cumsum(obras_total) / max(_total_obras, 1.0) * 100
        pct_vendas_acum = np.cumsum(vendas_vgv) / _total_vgv * 100
        fin_data = simular_financiamento(
            fluxo_base, projeto.financiamento, horizonte,
            pct_vendas_acum=pct_vendas_acum,
            pct_obras_acum=pct_obras_acum,
        )

        comissao_vec = np.zeros(n)
        if fin_data["comissao_abertura"] > 0:
            comissao_vec[0] = fin_data["comissao_abertura"]

        df["Saque Financiamento"] = fin_data["saques"]
        df["Amortizacao Financiamento"] = fin_data["amortizacoes"]
        df["Juros Financiamento Banco"] = fin_data["juros_banco"]
        df["Comissao Abertura Financiamento"] = comissao_vec

        df["Total Entradas"] = df["Total Entradas"] + df["Saque Financiamento"]
        df["Total Saidas"] = (
            df["Total Saidas"]
            + df["Amortizacao Financiamento"]
            + df["Juros Financiamento Banco"]
            + df["Comissao Abertura Financiamento"]
        )

        # Investidor — emprestimo
        if _inv_emp:
            df["Saque Investidor"] = fin_data["saques_investidor"]
            df["Amortizacao Investidor"] = fin_data["amortizacoes_investidor"]
            df["Juros Investidor"] = fin_data["juros_investidor"]
            df["Total Entradas"] = df["Total Entradas"] + df["Saque Investidor"]
            df["Total Saidas"] = (
                df["Total Saidas"]
                + df["Amortizacao Investidor"]
                + df["Juros Investidor"]
            )

        df["Saldo do Mes"] = df["Total Entradas"] - df["Total Saidas"]
        df["Saldo Acumulado"] = df["Saldo do Mes"].cumsum()

    # ----- 9c. INVESTIDOR — % do negocio (retorno progressivo pos-obras) -----
    _inv_pneg = (
        getattr(projeto.financiamento, "ativo_investidor", False)
        and getattr(projeto.financiamento, "modo_investidor", "pct_negocio") == "pct_negocio"
    )
    _lucro_base_bruto: float = float(df["Saldo do Mes"].sum())
    _retorno_inv_pago: float = 0.0
    _retorno_inv_pendente: float = 0.0
    if _inv_pneg:
        pct_inv_v = getattr(projeto.financiamento, "investidor_pct_negocio", 20.0)
        total_retorno = max(0.0, _lucro_base_bruto * pct_inv_v / 100.0)
        saldo_acum_arr = df["Saldo Acumulado"].to_numpy(dtype=float).copy()
        retorno_inv_arr = np.zeros(n)
        restante = total_retorno
        for mes in range(mes_termino_obras, n):
            if saldo_acum_arr[mes] > 0.0 and restante > 0.0:
                pagamento = min(saldo_acum_arr[mes], restante)
                retorno_inv_arr[mes] = pagamento
                restante -= pagamento
                saldo_acum_arr[mes:] -= pagamento
        df["Retorno Investidor"] = retorno_inv_arr
        df["Saldo do Mes"] = df["Saldo do Mes"] - retorno_inv_arr
        df["Saldo Acumulado"] = saldo_acum_arr
        _retorno_inv_pago = total_retorno - restante
        _retorno_inv_pendente = restante

    fluxo = df["Saldo do Mes"].to_numpy()
    indicadores = _calcular_indicadores(fluxo, tma_mensal)

    # Saldo descontado (cada mes descontado a TMA)
    fatores_desconto = np.array([(1 + tma_mensal) ** -m for m in range(n)])
    saldo_desc = (fluxo * fatores_desconto).cumsum()
    df["Saldo Descontado Acumulado"] = saldo_desc

    # ----- 10. RESUMO -----
    resumo = {
        "vgv_bruto": projeto.terreno.vgv_bruto,
        "vgv_vendavel": vgv_vendavel,
        "vgv_efetivo_vendavel": rec_data.get("vgv_efetivo_vendavel", vgv_vendavel),
        "vgv_total_recebido": float(recebimentos.sum()),
        "receita_nominal_venda": float(recebimentos_principal.sum()),
        "receita_financeira": float(recebimentos_juros.sum()),
        "total_lotes": projeto.terreno.total_lotes,

        "custo_terreno": float(desembolso_terreno.sum() + cartorio.sum()),
        "custo_terreno_aquisicao": float(desembolso_terreno.sum()),
        "custo_terreno_cartorio": float(cartorio.sum()),
        "custo_obras": float(obras_total.sum()),
        "custo_obras_direto": obras_data["custo_direto"],
        "custo_obras_total": obras_data["custo_total"],
        "custo_projetos": float(desenv_data["projetos"].sum()),
        "custo_licenciamento": float(desenv_data["licenciamento"].sum()),
        "custo_marketing": float(desenv_data["marketing"].sum()),
        "custo_outros": float(desenv_data["outros"].sum()),
        "custo_administracao": float(desenv_data["administracao"].sum()),
        "custo_comissao": float(comissao.sum()),
        "custo_impostos": float(impostos_vec.sum()),
        "custo_permuta_financeira": float(permuta_fin.sum()),
        "outras_receitas_total": float(outras_rec.sum()),

        "total_saidas": float(df["Total Saidas"].sum()),
        "lucro_liquido": float(df["Saldo do Mes"].sum()),

        "horizonte_meses": horizonte,
        "mes_termino_obras": mes_termino_obras,
    }

    # Margens
    if resumo["vgv_bruto"] > 0:
        resumo["margem_sobre_vgv_bruto"] = resumo["lucro_liquido"] / resumo["vgv_bruto"]
    if resumo["vgv_vendavel"] > 0:
        resumo["margem_sobre_vgv_vendavel"] = (
            resumo["lucro_liquido"] / resumo["vgv_vendavel"]
        )

    # Reajustes monetarios
    resumo["reajustes_ativo"] = projeto.reajustes.ativo
    resumo["receita_correcao_total"] = float(recebimentos_correcao.sum())
    resumo["custo_obras_base_constante"] = obras_data.get("custo_base_constante", resumo["custo_obras"])
    resumo["variacao_custo_obras_incc"] = resumo["custo_obras"] - resumo["custo_obras_base_constante"]

    # Financiamento bancario
    resumo["financiamento_ativo"] = projeto.financiamento.ativo
    if fin_data is not None:
        resumo["custo_financiamento_juros"] = float(fin_data["juros_banco"].sum())
        resumo["custo_financiamento_comissao"] = fin_data["comissao_abertura"]
        resumo["custo_financiamento_total"] = (
            resumo["custo_financiamento_juros"] + resumo["custo_financiamento_comissao"]
        )
        resumo["saldo_devedor_maximo"] = float(fin_data["saldo_devedor"].max())
        resumo["saldo_devedor_final"] = fin_data["saldo_devedor_final"]
        # Indicadores sem financiamento para comparativo
        resumo["tir_anual_sem_fin"] = indicadores_base.get("tir_anual")
        resumo["vpl_sem_fin"] = indicadores_base.get("vpl")
        resumo["exposicao_sem_fin"] = indicadores_base.get("exposicao_maxima")
        lucro_base = float(fluxo_base.sum())
        resumo["margem_sem_fin"] = (
            lucro_base / resumo["vgv_vendavel"]
            if resumo["vgv_vendavel"] > 0 else None
        )
    else:
        resumo["custo_financiamento_juros"] = 0.0
        resumo["custo_financiamento_comissao"] = 0.0
        resumo["custo_financiamento_total"] = 0.0
        resumo["saldo_devedor_maximo"] = 0.0
        resumo["saldo_devedor_final"] = 0.0

    # Investidor
    resumo["investidor_ativo"] = getattr(projeto.financiamento, "ativo_investidor", False)
    resumo["investidor_modo"] = getattr(projeto.financiamento, "modo_investidor", "pct_negocio")
    if resumo["investidor_ativo"] and resumo["investidor_modo"] == "pct_negocio":
        pct_inv = getattr(projeto.financiamento, "investidor_pct_negocio", 20.0)
        resumo["investidor_pct_negocio"] = pct_inv
        resumo["lucro_bruto_antes_investidor"] = _lucro_base_bruto
        resumo["retorno_investidor_pago"] = _retorno_inv_pago
        resumo["retorno_investidor_pendente"] = _retorno_inv_pendente
        resumo["lucro_investidor"] = _retorno_inv_pago
        resumo["lucro_loteadora"] = resumo["lucro_liquido"]
    if resumo["investidor_ativo"] and resumo["investidor_modo"] == "emprestimo" and fin_data is not None:
        resumo["custo_juros_investidor"] = float(fin_data["juros_investidor"].sum())
        resumo["saldo_devedor_investidor_maximo"] = float(fin_data["saldo_devedor_investidor"].max())
        resumo["saldo_devedor_investidor_final"] = fin_data["saldo_devedor_investidor_final"]

    return ResultadoCalculo(
        fluxo_caixa=df,
        resumo=resumo,
        indicadores=indicadores,
        etapas_obra=obras_data["detalhamento_etapas"],
        horizonte=horizonte,
    )


def _calcular_indicadores(fluxo: np.ndarray, tma_mensal: float) -> dict:
    """Calcula indicadores financeiros."""
    indicadores: dict = {}

    # VPL
    indicadores["vpl"] = float(npv(tma_mensal, fluxo.tolist()))

    # TIR mensal -> anual
    tir_mensal = irr(fluxo.tolist())
    if tir_mensal is None:
        indicadores["tir_mensal"] = None
        indicadores["tir_anual"] = None
    else:
        indicadores["tir_mensal"] = float(tir_mensal)
        indicadores["tir_anual"] = float((1 + tir_mensal) ** 12 - 1)

    # Saldo acumulado (para payback e exposicao)
    saldo_acum = fluxo.cumsum()

    # Exposicao maxima de caixa = mais negativo do saldo acumulado
    exp_max = float(saldo_acum.min())
    mes_exp_max = int(saldo_acum.argmin())
    indicadores["exposicao_maxima"] = exp_max
    indicadores["mes_exposicao_maxima"] = mes_exp_max

    # Payback simples: primeiro mes em que saldo_acum >= 0 apos exposicao maxima
    payback_simples = None
    for m in range(mes_exp_max, len(saldo_acum)):
        if saldo_acum[m] >= 0:
            payback_simples = m
            break
    indicadores["payback_simples_meses"] = payback_simples

    # Payback descontado
    fatores = np.array([(1 + tma_mensal) ** -m for m in range(len(fluxo))])
    saldo_desc_acum = (fluxo * fatores).cumsum()
    payback_desc = None
    for m in range(len(saldo_desc_acum)):
        if saldo_desc_acum[m] >= 0:
            payback_desc = m
            break
    indicadores["payback_descontado_meses"] = payback_desc

    # Lucro / Exposicao (multiplicador sobre o capital investido)
    lucro_total = float(fluxo.sum())
    if exp_max < 0:
        indicadores["lucro_sobre_exposicao"] = lucro_total / abs(exp_max)
    else:
        indicadores["lucro_sobre_exposicao"] = None

    indicadores["lucro_liquido"] = lucro_total

    return indicadores
