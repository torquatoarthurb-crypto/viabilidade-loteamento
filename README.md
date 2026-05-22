# Sistema de Viabilidade Econômica de Loteamento
**Versão 0.7.0**

Sistema completo para análise de viabilidade econômica de empreendimentos de loteamento. Calcula fluxo de caixa mensal, indicadores financeiros (VPL, TIR, payback, exposição máxima) e gera relatório Excel.

---

## Como rodar

```bash
python -m streamlit run app.py
```

> Use `python -m streamlit` (não `streamlit` direto) — o PATH do Python não é configurado automaticamente no Windows.

Acesse em: `http://localhost:8501`

**Atalho:** `Ctrl + Enter` para calcular o fluxo de caixa.

---

## O que o sistema faz

Você descreve seu projeto pelo formulário e o sistema calcula o fluxo de caixa mês a mês com todos os indicadores financeiros. Suporta projetos de loteamento aberto, com modelagem completa de:

- Quadro de áreas, tipologias e VGV
- Aquisição do terreno (à vista, parcelada, permuta física/financeira)
- Fluxo de recebíveis configurável (sinal + parcelas obra + balões + financiamento Price)
- Curva de vendas mensal com gerador automático de curva S
- Orçamento de obras (modo resumido ou detalhado por etapas)
- Despesas de incorporação (9 pré-definidas com curvas sugeridas)
- Regime tributário (lucro presumido / real; regime caixa / competência)
- Comissão de vendas (sobre venda, sobre recebimento ou misto)
- Financiamento bancário de obras (módulo 13)
- Reajuste monetário por INCC/IPCA/IGP-M (módulo 14)

---

## Módulos disponíveis

| Módulo | Nome | Descrição |
|---|---|---|
| 0 | Visão Geral | KPIs, saúde do modelo, linha do tempo |
| 1 | Empreendimento | Áreas, datas, tipologias, mapa |
| 2 | Receitas | Fluxos de recebíveis, curva de vendas |
| 3 | Obras | Orçamento e cronograma de obras |
| 4 | Incorporação | Despesas de desenvolvimento |
| 5 | Impostos | Regime tributário e comissão |
| 6 | Resultado | DRE completa em cascata |
| 7 | Fluxo de Caixa | TMA e tabela mensal completa |
| 8 | Dashboard | Gráficos interativos (4 tabs) |
| 9 | Terreno | Aquisição avançada do terreno |
| 10 | Ferramentas | Sensibilidade, Solvers, Faseamento, Benchmarks |
| 11 | Cenários | Comparativo de cenários e Monte Carlo |
| 12 | Projetos | Biblioteca de projetos |
| 13 | Financiamento | Financiamento bancário de obras |
| 14 | Reajustes | Correção monetária (INCC/IPCA/IGP-M) |

---

## Exportações

- **Excel** (5 abas): Resumo, Fluxo de Caixa, Indicadores, Simulação Lote, Verificação Receitas
- **HTML**: relatório auto-contido para impressão como PDF

---

## Arquivos do projeto

```
Rev_03/
├── app.py                    # Ponto de entrada (Streamlit)
├── auto_teste.py             # 7 testes matemáticos da engine
├── rodar.py                  # Modo CLI: lê JSON e gera Excel
├── requirements.txt          # Dependências Python
├── CLAUDE.md                 # Manual de bordo para o Claude Code
├── MANUAL_USUARIO.md         # Manual completo do usuário (leia este!)
├── ROADMAP.md                # Melhorias futuras planejadas
├── INSTALACAO.md             # Guia de instalação do Python e dependências
├── .streamlit/config.toml    # Tema escuro
├── exemplos/
│   └── projeto_exemplo.json  # "Loteamento Vila Verde" — 224 lotes (exemplo)
└── src/
    ├── modelos/              # Pydantic (estrutura de dados de entrada)
    ├── engine/               # Cálculos matemáticos (sem dependência de UI)
    ├── io_projeto/           # Leitura/escrita JSON e Excel
    └── interface/            # Streamlit (telas e componentes)
```

---

## Stack técnica

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.14 |
| Interface | Streamlit |
| Modelagem | Pydantic v2 |
| Cálculos | NumPy + Pandas |
| Gráficos | Plotly |
| Excel | openpyxl |
| NPV/IRR | Implementação própria (Newton-Raphson + bisseção) — sem numpy_financial |

---

## Testes

```bash
python auto_teste.py
```

7 testes matemáticos cobrindo: parcela Price, curva S, meses_entre, NPV, IRR, simulação de 1 lote e invariante receita nominal = VGV exato.

---

## Documentação

- **[MANUAL_USUARIO.md](MANUAL_USUARIO.md)** — manual completo de uso para não-técnicos
- **[ROADMAP.md](ROADMAP.md)** — lista priorizada de melhorias futuras
- **[INSTALACAO.md](INSTALACAO.md)** — passo a passo de instalação no Windows
- **[CLAUDE.md](CLAUDE.md)** — manual técnico do projeto (para desenvolvimento com Claude Code)
