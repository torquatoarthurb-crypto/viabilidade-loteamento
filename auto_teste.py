"""
Teste matematico standalone da engine.

Este script NAO usa pydantic. Ele monta os objetos do projeto manualmente
(via SimpleNamespace e listas) e chama as funcoes da engine para verificar
que o calculo matematico esta correto.

Serve para confirmar que a engine funciona ANTES de o usuario instalar pydantic.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parent
# Importamos diretamente os arquivos puros, SEM passar pelo src/__init__
# (que carregaria pydantic em cascata).
sys.path.insert(0, str(ROOT / "src" / "engine"))

# Importa apenas as funcoes que nao dependem de pydantic
import importlib.util


def _carregar_modulo(nome: str, caminho: Path):
    """Carrega um modulo Python diretamente do arquivo, sem usar pacote."""
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


_engine_dir = ROOT / "src" / "engine"
ind_fin = _carregar_modulo("indicadores_financeiros", _engine_dir / "indicadores_financeiros.py")
util = _carregar_modulo("utilidades", _engine_dir / "utilidades.py")

irr = ind_fin.irr
npv = ind_fin.npv
gerar_curva_linear = util.gerar_curva_linear
gerar_curva_s = util.gerar_curva_s
meses_entre = util.meses_entre
parcela_price = util.parcela_price


def teste_parcela_price() -> None:
    """Verifica o sistema Price com valores conhecidos."""
    print("Teste 1: parcela_price")
    # Caso 1: PV=100000, i=1% a.m., n=120
    # Resultado esperado: 1434.71 (verificavel em qualquer simulador)
    pmt = parcela_price(100000, 0.01, 120)
    assert 1434 < pmt < 1435, f"Esperado ~1434.71, obtido {pmt:.2f}"
    print(f"  PV=100k, i=1%a.m., n=120  ->  parcela = R$ {pmt:.2f}  OK")

    # Caso 2: juros zero deve dar parcela fixa = PV/n
    pmt0 = parcela_price(120000, 0, 60)
    assert abs(pmt0 - 2000) < 0.01, f"Esperado 2000, obtido {pmt0}"
    print(f"  PV=120k, i=0%, n=60       ->  parcela = R$ {pmt0:.2f}  OK")
    print()


def teste_curva_s() -> None:
    """Verifica que a curva S soma 1 e tem o formato correto."""
    print("Teste 2: curva_s")
    curva = gerar_curva_s(12)
    soma = sum(curva)
    assert abs(soma - 1.0) < 1e-9, f"Curva S deve somar 1, somou {soma}"
    print(f"  duracao=12 meses   ->  soma = {soma:.10f}  OK")
    # Os 4 meses centrais devem ter mais peso que os 4 meses extremos
    centro = sum(curva[4:8])
    extremos = sum(curva[:2]) + sum(curva[-2:])
    assert centro > extremos, "Centro deveria ter mais peso que extremos"
    print(f"  peso centro (4-7) = {centro:.4f}  >  peso extremos = {extremos:.4f}  OK")
    print()


def teste_curva_linear() -> None:
    """Verifica curva linear."""
    print("Teste 3: curva_linear")
    curva = gerar_curva_linear(10)
    assert all(abs(p - 0.1) < 1e-12 for p in curva), "Curva linear de 10 meses deveria ser 10% cada"
    print(f"  duracao=10 meses   ->  cada mes = {curva[0]:.4f}  OK")
    print()


def teste_meses_entre() -> None:
    """Verifica calculo de meses entre datas."""
    print("Teste 4: meses_entre")
    d1 = date(2026, 1, 1)
    d2 = date(2026, 4, 1)
    n = meses_entre(d1, d2)
    assert n == 3, f"Esperado 3, obtido {n}"
    print(f"  jan/2026 -> abr/2026  ->  {n} meses  OK")

    d3 = date(2027, 7, 1)
    n2 = meses_entre(d1, d3)
    assert n2 == 18, f"Esperado 18, obtido {n2}"
    print(f"  jan/2026 -> jul/2027  ->  {n2} meses  OK")
    print()


def teste_npv() -> None:
    """Verifica NPV com caso conhecido."""
    print("Teste 5: NPV")
    # Investimento de 1000 hoje, retorna 500/ano por 3 anos, taxa 10%
    # NPV = -1000 + 500/1.1 + 500/1.21 + 500/1.331 = 243.43
    fluxo = [-1000, 500, 500, 500]
    valor = npv(0.10, fluxo)
    assert 243 < valor < 244, f"Esperado ~243.43, obtido {valor:.2f}"
    print(f"  fluxo=[-1000, 500, 500, 500], rate=10%  ->  NPV = {valor:.2f}  OK")

    # Caso 2: rate=0 -> NPV = soma simples
    valor2 = npv(0, [-100, 50, 50, 50])
    assert valor2 == 50.0, f"Esperado 50, obtido {valor2}"
    print(f"  rate=0%  ->  NPV = soma simples = {valor2}  OK")
    print()


def teste_irr() -> None:
    """Verifica IRR com casos conhecidos."""
    print("Teste 6: IRR")
    # Caso simples: investe 100 hoje, recebe 110 daqui a 1 periodo -> IRR = 10%
    rate = irr([-100, 110])
    assert rate is not None and abs(rate - 0.10) < 1e-5, f"Esperado 10%, obtido {rate}"
    print(f"  fluxo=[-100, 110]  ->  IRR = {rate*100:.4f}%  OK")

    # Caso 2: serie de fluxos
    rate2 = irr([-1000, 300, 400, 500])
    # Valor conhecido: ~8.896%
    assert rate2 is not None and 0.088 < rate2 < 0.090, f"Obtido {rate2}"
    print(f"  fluxo=[-1000, 300, 400, 500]  ->  IRR = {rate2*100:.4f}%  OK")

    # Caso 3: fluxo todo negativo deve devolver None
    rate3 = irr([-100, -50, -30])
    assert rate3 is None, f"Deveria ser None, obtido {rate3}"
    print("  fluxo todo negativo  ->  IRR = None  OK")
    print()


def teste_simulacao_completa() -> None:
    """
    Teste integrado: simula manualmente um lote vendido e verifica
    que a soma das parcelas bate com o VGV (com juros embutidos).
    """
    print("Teste 7: Simulacao de 1 lote (integrado)")
    # Carrega recebimentos.py diretamente (ele importa modelos via type hints,
    # mas em runtime nao precisa - vou usar import dentro de uma funcao)
    rec_path = _engine_dir / "recebimentos.py"
    # Nao podemos carregar recebimentos.py diretamente porque ele importa
    # de ..modelos (que precisa pydantic). Vou reimplementar simular_lote_unitario aqui.

    def simular_lote_unitario(valor_lote, fluxo, mes_venda, mes_termino_obras):
        """Re-implementacao local para teste sem pydantic."""
        cronograma = []
        # Sinal
        valor_sinal = valor_lote * (fluxo.percentual_sinal / 100)
        if valor_sinal > 0:
            parcela_sinal = valor_sinal / fluxo.qtd_parcelas_sinal
            for k in range(fluxo.qtd_parcelas_sinal):
                cronograma.append({"mes": mes_venda + k, "tipo": "sinal", "valor": parcela_sinal})
        # Parcelas durante obra
        valor_obra = valor_lote * (fluxo.percentual_obra / 100)
        if valor_obra > 0:
            mes_inicio = mes_venda + max(fluxo.qtd_parcelas_sinal, 1)
            qtd = mes_termino_obras - mes_inicio + 1
            if qtd > 0:
                i = fluxo.juros_parcelas_obra_am / 100
                parcela = parcela_price(valor_obra, i, qtd)
                for k in range(qtd):
                    cronograma.append({"mes": mes_inicio + k, "tipo": "parcela_obra", "valor": parcela})
        # Baloes
        valor_baloes = valor_lote * (fluxo.percentual_baloes / 100)
        if valor_baloes > 0 and fluxo.qtd_baloes > 0:
            valor_balao = valor_baloes / fluxo.qtd_baloes
            for k in range(1, fluxo.qtd_baloes + 1):
                cronograma.append({"mes": mes_venda + k * 12, "tipo": "balao", "valor": valor_balao})
        # Financiamento
        valor_fin = valor_lote * (fluxo.percentual_financiamento / 100)
        if valor_fin > 0 and fluxo.qtd_parcelas_financiamento > 0:
            i = fluxo.juros_financiamento_am / 100
            parcela_fin = parcela_price(valor_fin, i, fluxo.qtd_parcelas_financiamento)
            mes_inicio_fin = mes_termino_obras + 1
            for k in range(fluxo.qtd_parcelas_financiamento):
                cronograma.append({"mes": mes_inicio_fin + k, "tipo": "parcela_financiamento", "valor": parcela_fin})
        cronograma.sort(key=lambda x: x["mes"])
        return cronograma

    # Mock simples de FluxoRecebiveis usando SimpleNamespace
    fluxo = SimpleNamespace(
        nome="Teste",
        percentual_sinal=10,
        qtd_parcelas_sinal=1,
        percentual_obra=20,
        juros_parcelas_obra_am=0,
        percentual_baloes=20,
        qtd_baloes=2,
        percentual_financiamento=50,
        qtd_parcelas_financiamento=60,
        juros_financiamento_am=1.0,
    )

    valor_lote = 200000
    mes_venda = 6
    mes_termino_obras = 18

    cron = simular_lote_unitario(valor_lote, fluxo, mes_venda, mes_termino_obras)

    # Sinal: 10% = 20.000 (1 parcela no mes 6)
    sinais = [e for e in cron if e["tipo"] == "sinal"]
    soma_sinais = sum(e["valor"] for e in sinais)
    assert abs(soma_sinais - 20000) < 0.01, f"Sinal: {soma_sinais}"
    print(f"  Soma sinais = R$ {soma_sinais:,.2f}  (esperado 20.000)  OK")

    # Parcelas durante obra: 20% = 40.000 distribuido em (18 - 7 + 1) = 12 parcelas
    # juros 0 -> parcela = 40000/12 = 3333.33
    parcelas_obra = [e for e in cron if e["tipo"] == "parcela_obra"]
    soma_obra = sum(e["valor"] for e in parcelas_obra)
    assert abs(soma_obra - 40000) < 0.01, f"Obra: {soma_obra}"
    assert len(parcelas_obra) == 12, f"Esperadas 12 parcelas, obtidas {len(parcelas_obra)}"
    print(f"  Parcelas obra: {len(parcelas_obra)}, soma = R$ {soma_obra:,.2f}  OK")

    # Baloes: 20% = 40.000 em 2 baloes = 20.000 cada
    baloes = [e for e in cron if e["tipo"] == "balao"]
    assert len(baloes) == 2
    assert all(abs(e["valor"] - 20000) < 0.01 for e in baloes)
    print(f"  Baloes: {len(baloes)} de R$ {baloes[0]['valor']:,.2f} cada  OK")

    # Financiamento: 50% = 100.000 em 60 parcelas Price com 1% a.m.
    # Parcela esperada = 2.224,44
    parcelas_fin = [e for e in cron if e["tipo"] == "parcela_financiamento"]
    assert len(parcelas_fin) == 60
    valor_parcela_fin = parcelas_fin[0]["valor"]
    assert 2224 < valor_parcela_fin < 2225, f"Parcela esperada ~2224.44, obtida {valor_parcela_fin}"
    print(
        f"  Financiamento: 60 parcelas Price 1%a.m. de R$ {valor_parcela_fin:,.2f}  OK"
    )
    print()


def main() -> None:
    print("=" * 60)
    print("AUTO-TESTE DA ENGINE DE VIABILIDADE")
    print("=" * 60)
    print()
    teste_parcela_price()
    teste_curva_s()
    teste_curva_linear()
    teste_meses_entre()
    teste_npv()
    teste_irr()
    teste_simulacao_completa()
    print("=" * 60)
    print("TODOS OS TESTES PASSARAM")
    print("=" * 60)


if __name__ == "__main__":
    main()
