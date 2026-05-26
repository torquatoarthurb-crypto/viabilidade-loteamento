"""
Construtor de projeto novo (com valores default sensatos).

Quando o usuario clica em "Novo Projeto" na interface, chamamos
`projeto_novo()` e recebemos um Projeto valido e vazio, pronto para
ser preenchido aba por aba.

Os defaults foram escolhidos para serem realistas para um loteamento
de medio porte no Brasil.
"""

from __future__ import annotations

from datetime import date

from .desenvolvimento import Aba4Desenvolvimento, Administracao
from .financeiro import AquisicaoTerreno, ParametrosFinanceiros
from .obras import Aba3Obras, EtapaObra
from .projeto import Projeto
from .receitas import Aba2Receitas, FluxoTipologia
from .terreno import (
    Aba1Terreno,
    DatasProjeto,
    InfoEmpreendimento,
    QuadroAreas,
    Tipologia,
)
from .tributos import Aba5Impostos, ComissaoVenda, Tributos


def projeto_novo() -> Projeto:
    """
    Cria um projeto com defaults sensatos para servir como ponto de partida.

    Os valores sao realistas mas devem ser todos editados pelo usuario.
    O projeto retornado JA passa pela validacao do Pydantic — nao tem
    inconsistencias.
    """
    hoje = date.today()
    inicio = date(hoje.year, hoje.month, 1)

    # Datas-padrao: 6 meses para aprovar, 9 para lancar, 10 para iniciar obra,
    # 28 para terminar obra. (~ 18 meses de obra)
    def add_meses(d: date, n: int) -> date:
        ano = d.year + (d.month - 1 + n) // 12
        mes = (d.month - 1 + n) % 12 + 1
        return date(ano, mes, 1)

    return Projeto(
        terreno=Aba1Terreno(
            info=InfoEmpreendimento(
                nome="Novo Projeto",
                cidade="Cidade",
                uf="MG",
            ),
            areas=QuadroAreas(
                area_gleba_m2=100_000,
                area_sistema_viario_m2=22_000,
                area_verde_m2=8_000,
                area_institucional_m2=5_000,
                area_app_m2=0,
                area_lotes_m2=65_000,
            ),
            datas=DatasProjeto(
                inicio_projeto=inicio,
                aprovacao=add_meses(inicio, 6),
                lancamento_vendas=add_meses(inicio, 9),
                inicio_obras=add_meses(inicio, 10),
                termino_obras=add_meses(inicio, 28),
            ),
            tipologias=[
                Tipologia(
                    nome="Lote Padrao",
                    quantidade=100,
                    area_lote_m2=250,
                    modo_preco="por_m2",
                    valor_unitario=800,
                ),
            ],
        ),
        aquisicao=AquisicaoTerreno(
            valor_total=1.0,
            forma_pagamento="sem_desembolso",
        ),
        receitas=Aba2Receitas(
            tipo_permuta="sem_permuta",
            permuta_fisica=[],
            fluxos_tipologia=[
                FluxoTipologia(
                    nome_tipologia="Lote Padrao",
                    percentual_sinal=10,
                    qtd_parcelas_sinal=1,
                    percentual_obra=30,
                    juros_parcelas_obra_am=0.5,
                    percentual_baloes=10,
                    qtd_baloes=2,
                    percentual_financiamento=50,
                    qtd_parcelas_financiamento=120,
                    juros_financiamento_am=1.0,
                    curva_mensal={
                        m: round(60 / 12, 4) for m in range(9, 21)
                        # 60% distribuido entre M9-M20 (lancamento e obras)
                    } | {
                        m: round(40 / 15, 4) for m in range(21, 36)
                        # 40% distribuido entre M21-M35 (fim das obras)
                    },
                ),
            ],
        ),
        obras=Aba3Obras(
            modo="detalhado",
            etapas=[
                EtapaObra(nome="Terraplenagem",              valor_total=0, mes_inicio=10, duracao_meses=6,  curva="linear"),
                EtapaObra(nome="Drenagem Pluvial",           valor_total=0, mes_inicio=12, duracao_meses=8,  curva="linear"),
                EtapaObra(nome="Rede de Agua",               valor_total=0, mes_inicio=14, duracao_meses=6,  curva="linear"),
                EtapaObra(nome="Rede de Esgoto",             valor_total=0, mes_inicio=14, duracao_meses=6,  curva="linear"),
                EtapaObra(nome="Rede Eletrica e Iluminacao", valor_total=0, mes_inicio=18, duracao_meses=6,  curva="linear"),
                EtapaObra(nome="Pavimentacao",               valor_total=0, mes_inicio=20, duracao_meses=8,  curva="s_curve"),
                EtapaObra(nome="Calcadas e Guias",           valor_total=0, mes_inicio=24, duracao_meses=4,  curva="linear"),
                EtapaObra(nome="Paisagismo",                 valor_total=0, mes_inicio=26, duracao_meses=2,  curva="linear"),
            ],
            bdi_percentual=18,
            contingencia_percentual=5,
        ),
        desenvolvimento=Aba4Desenvolvimento(
            despesas=[],
            administracao=Administracao(
                percentual=2.0,
            ),
        ),
        impostos=Aba5Impostos(
            tributos=Tributos(
                regime="lucro_presumido",
                aliquota_efetiva=6.73,
                regime_apuracao="caixa",
            ),
            comissao=ComissaoVenda(
                percentual_vgv=6,
                modo_pagamento="sobre_venda",
            ),
            permuta_financeira=None,
        ),
        parametros=ParametrosFinanceiros(
            tma_anual=14,
        ),
    )
