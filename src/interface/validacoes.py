"""
Helpers de validacao do projeto inteiro.

Funcoes:
- validar_projeto_completo: gera lista de pendencias (erros + avisos) com
  link para a aba onde resolver
- alertas_plausibilidade: detecta valores tecnicamente validos mas fora
  do que costuma ocorrer no mercado de loteamento
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Pendencia:
    """Uma pendencia ou alerta no projeto."""

    tipo: str  # "erro" | "aviso" | "dica"
    aba: int  # numero da aba (1 a 8)
    mensagem: str

    @property
    def icone(self) -> str:
        return {"erro": "✕", "aviso": "!", "dica": "›"}.get(self.tipo, "·")


def validar_projeto_completo(projeto) -> list[Pendencia]:
    """
    Roda todas as validacoes e devolve lista de pendencias.

    Retorna lista vazia se o projeto esta perfeito.
    """
    pendencias: list[Pendencia] = []

    # ---- Aba 1: Terreno ----
    pendencias.extend(_validar_aba1(projeto))

    # ---- Aba 2: Receitas ----
    pendencias.extend(_validar_aba2(projeto))

    # ---- Aba 3: Obras ----
    pendencias.extend(_validar_aba3(projeto))

    # ---- Aba 4: Desenvolvimento ----
    pendencias.extend(_validar_aba4(projeto))

    # ---- Aba 5: Tributos ----
    pendencias.extend(_validar_aba5(projeto))

    # ---- Aba 7: Parametros ----
    pendencias.extend(_validar_aba7(projeto))

    return pendencias


def _validar_aba1(projeto) -> list[Pendencia]:
    out = []
    terreno = projeto.terreno

    if not terreno.tipologias:
        out.append(Pendencia("erro", 1, "Cadastre pelo menos uma tipologia de lote."))
    elif terreno.areas.area_lotes_m2 > 0:
        _area_tip = sum(t.area_total_m2 for t in terreno.tipologias)
        if _area_tip > terreno.areas.area_lotes_m2 * 1.005:
            _saldo = _area_tip - terreno.areas.area_lotes_m2
            out.append(Pendencia(
                "aviso", 1,
                f"Area das tipologias ({_area_tip:.0f} m2) excede "
                f"a area de lotes ({terreno.areas.area_lotes_m2:.0f} m2) "
                f"em {_saldo:.0f} m2. Revise as quantidades ou areas dos lotes."
            ))
        elif _area_tip < terreno.areas.area_lotes_m2 * 0.98:
            _falta = terreno.areas.area_lotes_m2 - _area_tip
            _cobertura = _area_tip / terreno.areas.area_lotes_m2 * 100
            out.append(Pendencia(
                "dica", 1,
                f"Tipologias cobrem {_cobertura:.1f}% da area de lotes "
                f"({_falta:.0f} m2 sem lote designado). "
                "Verifique se faltam tipologias ou ajuste a area de lotes."
            ))

    if terreno.areas.area_lotes_m2 == 0:
        out.append(Pendencia("erro", 1, "Area de lotes esta zerada."))

    # Plausibilidade
    if terreno.areas.aproveitamento < 0.30:
        out.append(Pendencia(
            "dica", 1,
            f"Aproveitamento de {terreno.areas.aproveitamento*100:.1f}% e baixo. "
            "Loteamentos costumam ter 50-70% de area vendavel sobre a gleba."
        ))

    if terreno.vgv_bruto == 0:
        out.append(Pendencia("erro", 1, "VGV total e zero. Verifique tipologias e precos."))

    return out


def _validar_aba2(projeto) -> list[Pendencia]:
    out = []
    receitas = projeto.receitas

    if not receitas.fluxos_tipologia:
        out.append(Pendencia("erro", 2, "Configure o fluxo de recebiveis para cada tipologia."))

    for ft in receitas.fluxos_tipologia:
        # Soma do fluxo
        if abs(ft.soma_fluxo - 100.0) > 0.01:
            out.append(Pendencia(
                "erro", 2,
                f"Tipologia '{ft.nome_tipologia}': percentuais do fluxo somam "
                f"{ft.soma_fluxo:.1f}% (deveria ser 100%)."
            ))

        # Soma da curva de vendas
        if ft.soma_curva < 0.01:
            out.append(Pendencia(
                "erro", 2,
                f"Tipologia '{ft.nome_tipologia}': curva de vendas vazia."
            ))
        elif abs(ft.soma_curva - 100.0) > 0.01:
            out.append(Pendencia(
                "aviso", 2,
                f"Tipologia '{ft.nome_tipologia}': curva de vendas soma "
                f"{ft.soma_curva:.1f}% (esperado 100%)."
            ))

        # Plausibilidade sinal
        if ft.percentual_sinal < 5:
            out.append(Pendencia(
                "dica", 2,
                f"Tipologia '{ft.nome_tipologia}': entrada de {ft.percentual_sinal:.0f}% "
                "e baixa. Praticas de mercado: 5-20%."
            ))
        if ft.percentual_sinal > 30:
            out.append(Pendencia(
                "dica", 2,
                f"Tipologia '{ft.nome_tipologia}': entrada de {ft.percentual_sinal:.0f}% "
                "e alta para loteamentos. Verifique."
            ))

    return out


def _validar_aba3(projeto) -> list[Pendencia]:
    out = []
    obras = projeto.obras

    if obras.modo == "detalhado" and not obras.etapas:
        out.append(Pendencia(
            "erro", 3, "Modo 'detalhado' selecionado mas nao ha etapas cadastradas."
        ))

    # Plausibilidade BDI
    if obras.bdi_percentual == 0:
        out.append(Pendencia(
            "dica", 3,
            "BDI esta em 0%. Pratica de mercado: 15-25%."
        ))
    elif obras.bdi_percentual > 40:
        out.append(Pendencia(
            "dica", 3,
            f"BDI de {obras.bdi_percentual:.1f}% e alto. Pratica de mercado: 15-25%."
        ))

    if obras.contingencia_percentual == 0:
        out.append(Pendencia(
            "dica", 3,
            "Reserva de contingencia em 0%. Recomendado: 5-10% para imprevistos."
        ))

    return out


def _validar_aba4(projeto) -> list[Pendencia]:
    out = []
    desenv = projeto.desenvolvimento

    if not desenv.despesas:
        out.append(Pendencia(
            "aviso", 4,
            "Nao ha despesas cadastradas (projetos, licencas, marketing). "
            "Adicione para um calculo realista."
        ))

    return out


def _validar_aba5(projeto) -> list[Pendencia]:
    out = []
    impostos = projeto.impostos

    # Plausibilidade comissao
    if impostos.comissao.percentual_vgv == 0:
        out.append(Pendencia(
            "aviso", 5,
            "Comissao de venda em 0%. Pratica de mercado: 4-8% sobre VGV."
        ))
    elif impostos.comissao.percentual_vgv > 10:
        out.append(Pendencia(
            "aviso", 5,
            f"Comissao de {impostos.comissao.percentual_vgv:.1f}% e alta. "
            "Mercado tipico: 4-8%."
        ))

    # Plausibilidade aliquota
    if impostos.tributos.regime == "lucro_presumido":
        if impostos.tributos.aliquota_efetiva == 0:
            out.append(Pendencia(
                "erro", 5, "Aliquota efetiva de imposto em 0%."
            ))

    return out


def _validar_aba7(projeto) -> list[Pendencia]:
    out = []
    if projeto.parametros.tma_anual == 0:
        out.append(Pendencia(
            "aviso", 7,
            "TMA em 0% a.a. — VPL sera igual ao lucro nominal. "
            "Recomendado: usar Selic, CDI ou taxa de oportunidade (10-18% a.a.)."
        ))
    elif projeto.parametros.tma_anual > 30:
        out.append(Pendencia(
            "dica", 7,
            f"TMA de {projeto.parametros.tma_anual:.1f}% a.a. e muito alta. "
            "Mercado: 10-18% a.a."
        ))
    return out


def contar_por_aba(pendencias: list[Pendencia]) -> dict[int, dict[str, int]]:
    """
    Devolve {aba: {erro: N, aviso: N, dica: N}} para o painel da sidebar.
    """
    out: dict[int, dict[str, int]] = {}
    for p in pendencias:
        if p.aba not in out:
            out[p.aba] = {"erro": 0, "aviso": 0, "dica": 0}
        out[p.aba][p.tipo] += 1
    return out


def status_aba(pendencias: list[Pendencia], aba: int) -> str:
    """
    Devolve emoji-status de uma aba: ❌ se ha erro, ⚠️ se ha aviso,
    ✅ se ha so dicas/nada.
    """
    da_aba = [p for p in pendencias if p.aba == aba]
    if any(p.tipo == "erro" for p in da_aba):
        return "❌"
    if any(p.tipo == "aviso" for p in da_aba):
        return "⚠️"
    return "✅"
