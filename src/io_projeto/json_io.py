"""Carregar e salvar projetos em formato JSON."""

from __future__ import annotations

import json
from pathlib import Path

from ..modelos import Projeto


def carregar_projeto(caminho: str | Path) -> Projeto:
    """Carrega um projeto de um arquivo JSON e devolve uma instancia validada."""
    caminho = Path(caminho)
    with caminho.open(encoding="utf-8") as f:
        data = json.load(f)
    data = _migrar_receitas_v2(data)
    return Projeto.model_validate(data)


def salvar_projeto(projeto: Projeto, caminho: str | Path) -> None:
    """Salva um projeto em arquivo JSON."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        f.write(projeto.model_dump_json(indent=2))


def _migrar_receitas_v2(data: dict) -> dict:
    """
    Migra receitas do formato antigo (fluxos_recebiveis + curva_vendas)
    para o novo formato (fluxos_tipologia com curva por tipologia).

    Acessa terreno.tipologias para mapear cada fluxo a uma tipologia.
    """
    if not isinstance(data, dict):
        return data

    receitas = data.get("receitas", {})
    if not isinstance(receitas, dict):
        return data

    # Ja no novo formato — nada a fazer
    if receitas.get("fluxos_tipologia"):
        return data

    fluxos_rec = receitas.get("fluxos_recebiveis", [])
    curva_antiga = receitas.get("curva_vendas", [])
    tipologias = data.get("terreno", {}).get("tipologias", [])

    if not fluxos_rec:
        return data

    # Converter curva antiga (lista de FaixaCurvaVendas) para
    # dict {nome_fluxo: {mes: pct}} e curva_total {mes: pct}
    curva_por_fluxo: dict[str, dict[int, float]] = {}
    curva_total: dict[int, float] = {}

    for faixa in curva_antiga:
        ini = int(faixa.get("mes_inicio", 0))
        fim = int(faixa.get("mes_fim", ini))
        pct = float(faixa.get("percentual_estoque", 0))
        nome_fl = str(faixa.get("fluxo_recebiveis", ""))
        n = max(1, fim - ini + 1)
        pct_mes = pct / n
        for i in range(n):
            m = ini + i
            curva_por_fluxo.setdefault(nome_fl, {})
            curva_por_fluxo[nome_fl][m] = curva_por_fluxo[nome_fl].get(m, 0.0) + pct_mes
            curva_total[m] = curva_total.get(m, 0.0) + pct_mes

    # Mapa de fluxos por nome
    fluxos_map = {str(f.get("nome", "")): f for f in fluxos_rec}

    fluxos_tip = []
    nomes_criados: set[str] = set()

    for tip in tipologias:
        nome_tip = str(tip.get("nome", ""))
        if nome_tip in nomes_criados:
            continue

        # Procura fluxo pelo nome da tipologia; cai no primeiro fluxo se nao encontrar
        fl = fluxos_map.get(nome_tip) or (fluxos_rec[0] if fluxos_rec else None)
        if fl is None:
            continue

        nome_fl = str(fl.get("nome", ""))
        # Curva especifica deste fluxo; se nao houver usa a curva total
        curva_tip = curva_por_fluxo.get(nome_fl) or curva_total or {}

        fluxos_tip.append({
            "nome_tipologia": nome_tip,
            "percentual_sinal": float(fl.get("percentual_sinal", 10.0)),
            "qtd_parcelas_sinal": int(fl.get("qtd_parcelas_sinal", 1)),
            "percentual_obra": float(fl.get("percentual_obra", 30.0)),
            "juros_parcelas_obra_am": float(fl.get("juros_parcelas_obra_am", 0.5)),
            "percentual_baloes": float(fl.get("percentual_baloes", 10.0)),
            "qtd_baloes": int(fl.get("qtd_baloes", 0)),
            "percentual_financiamento": float(fl.get("percentual_financiamento", 50.0)),
            "qtd_parcelas_financiamento": int(fl.get("qtd_parcelas_financiamento", 120)),
            "juros_financiamento_am": float(fl.get("juros_financiamento_am", 1.0)),
            "curva_mensal": {str(m): v for m, v in curva_tip.items()},
            "fatores_preco": {},
        })
        nomes_criados.add(nome_tip)

    # Se nao ha tipologias definidas, criar um FluxoTipologia por fluxo antigo
    if not tipologias:
        for fl in fluxos_rec:
            nome_fl = str(fl.get("nome", ""))
            curva_fl = curva_por_fluxo.get(nome_fl) or curva_total or {}
            ft_dict = {k: v for k, v in fl.items() if k != "nome"}
            ft_dict["nome_tipologia"] = nome_fl
            ft_dict["curva_mensal"] = {str(m): v for m, v in curva_fl.items()}
            ft_dict["fatores_preco"] = {}
            fluxos_tip.append(ft_dict)

    receitas["fluxos_tipologia"] = fluxos_tip
    data["receitas"] = receitas
    return data
