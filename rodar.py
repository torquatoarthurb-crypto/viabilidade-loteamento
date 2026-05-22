"""
Script principal: roda o calculo de viabilidade de um projeto.

Uso:
    python rodar.py                              # roda o exemplo
    python rodar.py exemplos/meu_projeto.json    # roda um projeto especifico

O resultado e exportado para um arquivo Excel.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que conseguimos importar de src/
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.engine import calcular_fluxo_caixa
from src.io_projeto import carregar_projeto, exportar_para_excel


def main() -> None:
    # 1. Determina qual arquivo de projeto usar
    if len(sys.argv) > 1:
        caminho_projeto = Path(sys.argv[1])
    else:
        caminho_projeto = ROOT / "exemplos" / "projeto_exemplo.json"

    if not caminho_projeto.exists():
        print(f"ERRO: arquivo nao encontrado: {caminho_projeto}")
        sys.exit(1)

    print("=" * 60)
    print("VIABILIDADE ECONOMICA DE LOTEAMENTO")
    print("=" * 60)
    print(f"Carregando projeto: {caminho_projeto}")

    # 2. Carrega e valida o projeto (Pydantic faz toda a validacao)
    try:
        projeto = carregar_projeto(caminho_projeto)
    except Exception as e:
        print(f"\nERRO de validacao no projeto:\n{e}")
        sys.exit(1)

    print(f"Projeto: {projeto.terreno.info.nome}")
    print(f"Cidade:  {projeto.terreno.info.cidade}/{projeto.terreno.info.uf}")
    print(f"Lotes:   {projeto.terreno.total_lotes}")
    print(f"VGV:     R$ {projeto.terreno.vgv_bruto:,.2f}")
    print()

    # 3. Roda o calculo
    print("Calculando fluxo de caixa...")
    resultado = calcular_fluxo_caixa(projeto)

    # 4. Imprime resumo no terminal
    print()
    print("=" * 60)
    print("RESUMO DO CALCULO")
    print("=" * 60)
    r = resultado.resumo
    ind = resultado.indicadores
    print(f"Horizonte do projeto:        {resultado.horizonte} meses")
    print(f"VGV bruto:                   R$ {r['vgv_bruto']:>20,.2f}")
    print(f"VGV vendavel:                R$ {r['vgv_vendavel']:>20,.2f}")
    print(f"  Receita nominal venda:     R$ {r['receita_nominal_venda']:>20,.2f}")
    print(f"  Receita financeira (juros):R$ {r['receita_financeira']:>20,.2f}")
    print(f"  Receita total recebida:    R$ {r['vgv_total_recebido']:>20,.2f}")
    print(f"Custo total (saidas):        R$ {r['total_saidas']:>20,.2f}")
    print(f"Lucro liquido:               R$ {r['lucro_liquido']:>20,.2f}")
    if r.get("margem_sobre_vgv_bruto") is not None:
        print(f"Margem / VGV bruto:          {r['margem_sobre_vgv_bruto']*100:>20.2f} %")
    print()
    print(f"VPL:                         R$ {ind['vpl']:>20,.2f}")
    if ind.get("tir_anual") is not None:
        print(f"TIR (a.a.):                  {ind['tir_anual']*100:>20.2f} %")
        print(f"TIR (a.m.):                  {ind['tir_mensal']*100:>20.4f} %")
    print(f"Exposicao maxima:            R$ {ind['exposicao_maxima']:>20,.2f}")
    print(f"Mes da exposicao maxima:     {ind['mes_exposicao_maxima']:>20} (M{ind['mes_exposicao_maxima']})")
    print(f"Payback simples:             {str(ind.get('payback_simples_meses')):>20} meses")
    print(f"Payback descontado:          {str(ind.get('payback_descontado_meses')):>20} meses")
    print()

    # 5. Exporta para Excel
    nome_saida = caminho_projeto.stem + "_resultado.xlsx"
    caminho_saida = ROOT / "exemplos" / nome_saida
    exportar_para_excel(projeto, resultado, caminho_saida)
    print(f"Resultado exportado para: {caminho_saida}")
    print()


if __name__ == "__main__":
    main()
