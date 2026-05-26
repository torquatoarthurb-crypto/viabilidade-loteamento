# Sistema de Viabilidade Econômica de Loteamento

> Este arquivo é o **manual de bordo** do projeto. O Claude Code lê automaticamente quando você abre o repositório no VS Code. Mantenha-o atualizado conforme o projeto evolui.

---

## 1. Visão Geral

### O que é
Sistema para análise de viabilidade econômica de empreendimentos de loteamento (incorporação imobiliária). Calcula fluxo de caixa mensal, indicadores financeiros (VPL, TIR, payback, exposição máxima) e gera relatórios.

### Quem usa
**Arthur** — incorporador imobiliário em Belo Horizonte/MG. Sem experiência em programação. Toda a interação é via interface gráfica (Streamlit). Ele NÃO mexe em Python ou JSON diretamente.

### Stack técnica
- **Linguagem**: Python 3.14
- **Pacotes**: `pydantic` 2 (modelagem), `pandas` + `numpy` (cálculos), `openpyxl` (Excel), `streamlit` (interface), `plotly` (gráficos interativos)
- **NPV/IRR**: implementação própria (Newton-Raphson + bisseção fallback) — **não usar `numpy_financial`** (foi removido por incompatibilidade com Python 3.14)
- **Sem banco de dados**: projetos são salvos como arquivos JSON pelo próprio usuário

### Como rodar
```bash
python -m streamlit run app.py
```
**IMPORTANTE**: usar `python -m streamlit` (não `streamlit` direto) — o PATH do Python não é configurado por padrão no Windows.

---

## 2. Estrutura do Projeto

```
Rev_04/
├── app.py                              # Entry point Streamlit
├── rodar.py                            # Modo CLI: calcula e exporta Excel via terminal
├── auto_teste.py                       # 7 testes matemáticos da engine
├── teste_exportadores.py               # 140 testes de integração (Excel + HTML)
├── requirements.txt
├── .streamlit/config.toml              # Tema escuro
├── assets/
│   ├── favicon.svg
│   ├── logo_dark.svg
│   └── logo_light.svg
├── dados/                              # Projetos salvos dos usuários (JSON)
│   ├── usuarios.json
│   └── projetos/<usuario>/
├── exemplos/
│   ├── projeto_exemplo.json            # "Loteamento Vila Verde", 224 lotes
│   └── projeto_exemplo_resultado.xlsx  # Excel de referência
└── src/
    ├── auth/
    │   └── gerenciador.py              # Autenticação e sessão de usuário
    ├── modelos/                        # Pydantic (dados de entrada)
    │   ├── terreno.py                  # Aba1Terreno, Tipologia, QuadroAreas, DatasProjeto, InfoEmpreendimento
    │   ├── receitas.py                 # Aba2Receitas, FluxoTipologia, FluxoRecebiveis (legado), FaixaCurvaVendas (legado)
    │   ├── obras.py                    # Aba3Obras, EtapaObra, OrcamentoResumido
    │   ├── desenvolvimento.py          # Aba4Desenvolvimento, DespesaTemporal, Administracao
    │   ├── tributos.py                 # Aba5Impostos, Tributos, ComissaoVenda, PermutaFinanceira
    │   ├── financeiro.py               # AquisicaoTerreno, ParametrosFinanceiros (TMA)
    │   ├── reajustes.py                # ConfigReajustes (correção monetária nas parcelas)
    │   ├── projeto.py                  # Projeto (objeto raiz — agrega todos os modelos)
    │   └── construtores.py             # projeto_novo() (template com defaults sensatos)
    ├── engine/                         # Cálculos matemáticos (sem Streamlit)
    │   ├── utilidades.py               # parcela_price, curva_s, meses_entre, etc.
    │   ├── indicadores_financeiros.py  # NPV, IRR (próprios — sem numpy_financial)
    │   ├── recebimentos.py             # Vendas → fluxo de recebíveis por tipologia
    │   ├── despesas.py                 # Distribuição temporal de despesas
    │   ├── financiamento_engine.py     # Financiamento do terreno com caixa mínimo
    │   └── fluxo_caixa.py              # Orquestrador principal → ResultadoCalculo
    ├── io_projeto/
    │   ├── json_io.py                  # Carregar/salvar JSON + _migrar_receitas_v2 (legado)
    │   ├── exportar_excel.py           # 9 abas: Dashboard, Terreno, Receitas, Obras, Desenvolvimento, Impostos, Fluxo, Verificacao, Simulacao
    │   └── exportar_html.py            # Relatório HTML self-contained para impressão/PDF
    └── interface/                      # Streamlit (apresentação)
        ├── helpers.py                  # Formatação BRL, marcos, get/set_projeto, etc.
        ├── tabela_mensal.py            # tabela_mensal_distribuicao (read-only) + atalhos_por_intervalos
        ├── tema.py                     # CSS customizado (tema escuro, variáveis CSS)
        ├── tema_componentes.py         # Header, KPI cards, linha do tempo, título módulo
        ├── validacoes.py               # Regras de plausibilidade (erro/aviso/dica)
        ├── sidebar.py                  # Sidebar: Ações + auto-calc + hash cache + histórico
        └── abas/
            ├── aba_login.py            # Módulo Login
            ├── aba_home.py             # Módulo Home (pós-login)
            ├── aba_projetos.py         # Módulo 12: Biblioteca de projetos (C8)
            ├── aba0_visao_geral.py     # Módulo 0: KPIs, saúde, linha do tempo (D3)
            ├── aba1_terreno.py         # Módulo 1: Identificação, áreas, tipologias, mapa (E5)
            ├── aba_terreno.py          # Módulo 9: Aquisição do terreno
            ├── aba2_receitas.py        # Módulo 2: FluxoTipologia (fluxo + curva por tipologia)
            ├── aba3_obras.py           # Módulo 3: Etapas de obra com Plotly
            ├── aba4_desenvolvimento.py # Módulo 4: Despesas de incorporação + gráfico
            ├── aba5_impostos.py        # Módulo 5: Tributos + comissão
            ├── aba_reajustes.py        # Módulo Reajustes: correção monetária
            ├── aba_financiamento.py    # Módulo Financiamento: financiamento do terreno
            ├── aba6_resultado.py       # Módulo 6: DRE completa
            ├── aba7_fluxo.py           # Módulo 7: TMA + tabela fluxo mensal
            ├── aba8_dashboard.py       # Módulo 8: Dashboard gráficos Plotly
            ├── aba_ferramentas.py      # Módulo 10: Sensibilidade, Solvers, Faseamento, Benchmarks
            └── aba_cenarios.py         # Módulo 11: Comparativo de Cenários + Monte Carlo
```

---

## 3. Fluxograma do Sistema

### Jornada do usuário

```
┌─────────────────────────────────────────────────────────────────┐
│  ENTRADA                                                        │
│                                                                 │
│  Login ──► Biblioteca de Projetos ──► Abre/Cria projeto        │
│                                                                 │
│  Módulo 1  Módulo 9   Módulo 2         Módulo 3   Módulo 4     │
│  Terreno   Aquis.     Receitas          Obras      Despesas    │
│  Tipol.    Terreno    FluxoTipologia   Etapas     Incorpor.   │
│    │          │            │               │          │         │
│    └──────────┴────────────┴───────────────┴──────────┘         │
│                           │                                     │
│                    Módulo 5 + 7                                  │
│                    Impostos + TMA                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                     [ Calcular ]  ◄─── Ctrl+Enter
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│  ENGINE (src/engine/)                                           │
│                                                                 │
│  calcular_fluxo_caixa(Projeto) ──► ResultadoCalculo            │
│                                                                 │
│  ┌────────────────────────────────────────────────┐            │
│  │  Para cada FluxoTipologia:                     │            │
│  │  VGV tipologia × curva_mensal[mes] × fator     │            │
│  │  → parcelas (sinal + obra + balões + financ.)  │            │
│  │  → principal separado dos juros (Price)        │            │
│  └────────────────────────────────────────────────┘            │
│                                                                 │
│  + despesas.py  + impostos  + comissão  + permuta              │
│  → saldo mensal → VPL, TIR, Payback, Exposição máxima         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│  RESULTADOS                                                     │
│                                                                 │
│  Módulo 0        Módulo 6      Módulo 7      Módulo 8           │
│  Visão Geral     DRE completa  Fluxo+TIR     Dashboard         │
│  KPIs + saúde    Margens       Tabela        Gráficos          │
│                                                                 │
│  Módulo 10       Módulo 11                                      │
│  Ferramentas     Cenários                                       │
│  Sensib./Solver  Comparativo / Monte Carlo                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                  ┌─────────┴─────────┐
                  │                   │
           [ Excel .xlsx ]    [ HTML → PDF ]
           9 abas auditoria   Relatório comitê
```

### Fluxo técnico de dados

```
Usuário edita campo
        │
        ▼
session_state (fonte da verdade da sessão)
        │
        ▼  (auto-save a cada mudança)
Pydantic valida → Projeto imutável
        │
        ▼  (somente ao clicar Calcular)
engine/fluxo_caixa.py
        │
   ┌────┴────┐
   │         │
recebimentos  despesas
.py           .py
   │         │
   └────┬────┘
        │
   fluxo de caixa mensal (DataFrame)
        │
   indicadores_financeiros.py
        │
   ResultadoCalculo
        │
   ┌────┴────────────┐
   │                 │
interface         exportar_
(leitura)         excel/html
```

### Modelo de dados central (`FluxoTipologia`)

Cada tipologia de lote possui **um objeto único** que concentra:

```
FluxoTipologia
├── nome_tipologia          → vincula à Tipologia do Módulo 1
├── Fluxo de recebíveis     → sinal% + obra% + balões% + financiamento% = 100%
│   ├── percentual_sinal / qtd_parcelas_sinal
│   ├── percentual_obra / juros_parcelas_obra_am
│   ├── percentual_baloes / qtd_baloes
│   └── percentual_financiamento / qtd_parcelas_financiamento / juros_financiamento_am
├── curva_mensal            → {mes: % do estoque desta tipologia} — soma 100%
└── fatores_preco           → {mes: multiplicador} — preço progressivo (opcional)
```

O fluxo de caixa final é **a soma dos fluxos de todas as tipologias**.

---

## 4. Arquitetura e Decisões de Design

### Princípios
1. **Engine é pura**: o módulo `engine/` não conhece Streamlit nem JSON. Recebe um `Projeto` e devolve um `ResultadoCalculo`.
2. **Modelos são imutáveis** durante o cálculo: cada mudança gera um novo `Projeto` via `model_copy(update={...})`.
3. **Auto-save em todas as abas**: NÃO há botões "Salvar Aba". Cada alteração é gravada no `session_state` e o `Projeto` é reconstruído silenciosamente. Erros de validação não impedem o salvamento — aparecem no painel de pendências da sidebar.
4. **Interface não calcula**: cálculos só rodam quando o usuário clica em "Calcular fluxo de caixa". Se o projeto muda, o resultado é invalidado (`invalidar_resultado()`).
5. **Receita nominal vs receita financeira**: o sistema separa o **principal** (= VGV exato) dos **juros** embutidos nas parcelas Price. Crítico para cálculo correto de impostos.
6. **Distribuição temporal via gráfico + intervalos**: `tabela_mensal_distribuicao` renderiza gráfico Plotly read-only; edição exclusivamente via `atalhos_por_intervalos`.

### Retrocompatibilidade (JSONs antigos)
`json_io.py` possui `_migrar_receitas_v2()` que converte automaticamente o formato antigo (`fluxos_recebiveis + curva_vendas`) para o novo (`fluxos_tipologia`) antes da validação Pydantic. Os campos legado são mantidos como opcionais em `Aba2Receitas`.

### Conceitos do domínio (linguagem do mercado)
- **VGV bruto**: valor geral de vendas (somatório de todos os lotes)
- **VGV vendável**: VGV bruto menos lotes destinados à permuta física
- **Permuta física**: parte do terreno paga em lotes (não geram receita)
- **Permuta financeira**: parte do VGV vai pro vendedor do terreno em dinheiro
- **Fluxo de recebíveis**: composição do pagamento de uma venda (sinal + obra + balões + financiamento). **Sempre soma 100%.**
- **Curva de vendas**: distribuição mensal de % do estoque vendido. **Sempre soma 100% por tipologia.**
- **Sistema Price**: parcelas iguais com decomposição mensal entre principal e juros
- **BDI**: Benefícios e Despesas Indiretas (~15-25% sobre custo direto)
- **Contingência**: reserva sobre custo com BDI (~5-10%)
- **TMA**: Taxa Mínima de Atratividade (~10-18% a.a. típico)
- **Exposição máxima**: maior valor negativo do saldo acumulado (capital necessário)

---

## 5. Estado Atual (versão 0.8.0)

### Engine matemática (100%)
- ✅ Sistema Price com decomposição principal/juros (receita nominal = VGV exato, invariante validada)
- ✅ Curva S logística simétrica
- ✅ NPV + IRR (Newton-Raphson com bisseção fallback)
- ✅ Recebimentos por tipologia: sinal, parcelas obra, balões anuais, financiamento Price pós-obra
- ✅ Fatores de preço progressivo por mês (multiplicador sobre VGV da venda)
- ✅ Receita NOMINAL separada de receita FINANCEIRA (juros)
- ✅ BDI + contingência multiplicativos
- ✅ Comissão (sobre venda / sobre recebimento / misto)
- ✅ Permuta física e financeira
- ✅ Impostos (lucro presumido / lucro real, regime caixa / competência)
- ✅ Indicadores: VPL, TIR, payback simples e descontado, exposição máxima

### Interface — Módulos de entrada

**Módulo 0 — Visão Geral** (`aba0_visao_geral.py`)
- KPIs em grid 4×2 (VPL, TIR, Payback, Exposição, VGV, Margem, Resultado, Custo Total)
- Card "Saúde do modelo" com checks de pendências
- Linha do tempo em 4 trilhas horizontais (Pré-obra / Obras / Vendas / Repasse)
- Estimativas pré-cálculo (D3) com banner de aviso

**Módulo 1 — Dados do Empreendimento** (`aba1_terreno.py`)
- Identificação: nome, cidade (autocomplete cidades BR), UF
- Quadro de áreas: gleba, viário, verde, institucional, APP, lotes
- Tipologias de lote: quantidade, área, modo de preço (R$/m² ou R$/lote), valor
- Barra de progresso de área (A1), validação de datas (A4), mapa OpenStreetMap (E5)

**Módulo 9 — Terreno** (`aba_terreno.py`)
- Aquisição: à vista, parcelada, permuta física + financeira
- Financiamento do terreno com controle de caixa mínimo

**Módulo 2 — Receitas (VGV)** (`aba2_receitas.py`)  
- **Design atual (v0.8.0)**: um expander por tipologia com 2 tabs:
  - **💳 Fluxo de Recebíveis**: sinal, parcelas obra, balões, financiamento (soma 100%)
  - **📈 Curva de Vendas**: cenários pré-configurados + atalhos por faixa + tabela manual
- Preço progressivo global (fases com multiplicador de preço)
- Outras receitas (aportes, receitas financeiras, venda de ativo)

**Módulo 3 — Despesas de Obras** (`aba3_obras.py`)
- Modo resumido (R$/m²) ou detalhado (etapas com distribuição mensal)
- Gráfico Plotly: barras + fases Obras/Vendas + marcos tracejados
- Benchmarks BDI 15–25%, contingência 5–10%

**Módulo 4 — Despesas de Incorporação** (`aba4_desenvolvimento.py`)
- Despesas por categoria: Projetos, Licenciamento, Marketing, Outros
- Valor fixo ou % do VGV bruto; atalhos contextuais por categoria
- Administração: % sobre receita mensal

**Módulo 5 — Impostos e Comissão** (`aba5_impostos.py`)
- Regime tributário: lucro presumido / lucro real; apuração caixa / competência
- ITBI, registro, comissão de venda

**Módulo 7 — Fluxo de Caixa** (`aba7_fluxo.py`)
- TMA com auto-save; indicadores rápidos pós-cálculo; tabela mensal com slider de período

### Interface — Módulos analíticos

**Módulo 6 — Resultado Estático** (`aba6_resultado.py`) — DRE completa, margens, composição de custos

**Módulo 8 — Dashboard** (`aba8_dashboard.py`) — Gráficos Plotly: fluxo mensal, exposição, pizza de custos, receitas por origem

**Módulo 10 — Ferramentas** (`aba_ferramentas.py`) — Sensibilidade (tornado), Solver Preço, Solver Terreno, Faseamento, Benchmarks

**Módulo 11 — Cenários** (`aba_cenarios.py`) — Comparativo de snapshots; Monte Carlo (P10/P50/P90)

**Módulo 12 — Projetos** (`aba_projetos.py`) — Biblioteca de projetos: listar, abrir, criar, duplicar, excluir

### Exportações
- **Excel** (9 abas): Dashboard, Terreno, Receitas (por tipologia), Obras, Desenvolvimento, Impostos, Fluxo de Caixa, Verificação de Receitas, Simulação de 1 Lote
- **HTML**: relatório self-contained para impressão como PDF

### Testes
- `auto_teste.py`: **7 testes matemáticos** (Price, curva S, NPV, IRR, simulação lote) — `python auto_teste.py`
- `teste_exportadores.py`: **140 testes de integração** (Excel + HTML, invariantes matemáticas, UX) — `python teste_exportadores.py`

### Bugs corrigidos (referência)

1. **`numpy_financial` removido** → implementação própria de NPV/IRR
2. **`cell.font = cell.font`** quebrava `openpyxl` no Python 3.14
3. **NPV com rate=-100%** → divisão por zero (limite ajustado para -99%)
4. **🔴 Bug crítico de receita perdida**: vendas pós-término de obras perdiam o `percentual_obra` silenciosamente (`qtd_parcelas_obra` negativo). Correção: pagamento concentrado no mês da venda. Local: `src/engine/recebimentos.py`, `_gerar_recebimentos_de_uma_venda`.
5. **`fluxo_caixa.py` horizonte zerado**: `_calcular_horizonte` lia `curva_vendas` (legado vazio) ignorando `fluxos_tipologia`. Corrigido para usar `fluxos_tipologia.curva_mensal` como fonte primária.

---

## 6. Próximos Passos Pendentes

- Aba 6 (DRE): verificar cobertura de todos os cenários de permuta e comissão
- Aba 8 (Dashboard): adicionar filtro de período nos gráficos
- Botão "Exportar PDF" na Aba 0 não está conectado ao `exportar_html.py`
- Relatório de comparativo de cenários em Excel (Módulo 11 só compara na tela)

---

## 7. Convenções e Boas Práticas

### Estilo de código
- **Comentários em português** (sem acentos nas variáveis: `mes_termino_obras` e não `mês`)
- **Strings de UI em português com acentos** (`"Mês de pagamento"`)
- **Type hints** sempre que possível (Python moderno: `list[int]`, `dict[str, float]`)
- **Pydantic para validação**: nunca confiar em dados crus do JSON ou da interface

### Streamlit
- **`session_state` é a fonte da verdade** durante a sessão
- **Auto-save** ao final de cada `renderizar()` — comparar com `get_projeto()` e chamar `set_projeto()` se mudou
- **`st.rerun()`** só para mudanças estruturais (adicionar/remover itens de lista)
- **`key=` único e descritivo** em todos os widgets

### Distribuição temporal (`tabela_mensal.py`)
- **`tabela_mensal_distribuicao`** é **somente leitura** (gráfico Plotly)
- Toda edição passa por **`atalhos_por_intervalos`** → escreve em `session_state[chave_resultado]`
- Caller checa `if chave_atl in st.session_state` no início do render para consumir resultado pendente

### Gráfico de distribuição — visual padrão
- Barras: azul (`#60A5FA`) > 0, escuro (`#1F2937`) = 0
- Zona Obras: `rgba(234,179,8,0.08)`, Zona Vendas: `rgba(34,197,94,0.05)`
- Marcos: linhas tracejadas cinza (`#6B7280`), labels `#9CA3AF`
- Background: `paper_bgcolor="#0A0E14"`, `plot_bgcolor="#131822"`, `height=200`

### Validações (`validacoes.py`)
- **erro**: bloqueia cálculo coerente (ex.: soma fluxo ≠ 100%)
- **aviso**: pode calcular, resultado suspeito
- **dica**: fora da prática de mercado mas tecnicamente válido

---

## 8. Onde Encontrar as Coisas

| Quero... | Vou em... |
|---|---|
| Adicionar campo na entrada do usuário | `src/modelos/<area>.py` + `src/interface/abas/aba<N>_*.py` |
| Mudar como um valor é calculado | `src/engine/<modulo>.py` |
| Adicionar regra de validação | `src/interface/validacoes.py` |
| Mexer no visual / cores / cards | `src/interface/tema.py` ou `tema_componentes.py` |
| Adicionar coluna no Excel | `src/io_projeto/exportar_excel.py` |
| Mudar o que aparece na sidebar | `src/interface/sidebar.py` |
| Criar atalho contextual de despesa | `src/interface/tabela_mensal.py`, função `atalhos_contextuais` |
| Adicionar validação matemática | `auto_teste.py` |
| Mudar o relatório HTML | `src/io_projeto/exportar_html.py` |
| Módulo Ferramentas (sensibilidade, solvers) | `src/interface/abas/aba_ferramentas.py` |
| Cenários / Monte Carlo | `src/interface/abas/aba_cenarios.py` |
| Gestão de projetos (biblioteca) | `src/interface/abas/aba_projetos.py` |
| Estilo do gráfico de distribuição | `src/interface/tabela_mensal.py`, `tabela_mensal_distribuicao` |
| Marcos do projeto (datas chave) | `src/interface/helpers.py`, `marcos_projeto` |
| Migração de JSONs antigos | `src/io_projeto/json_io.py`, `_migrar_receitas_v2` |
| Fluxo de recebíveis por tipologia | `src/modelos/receitas.py`, `FluxoTipologia` |

---

## 9. Como Eu (Claude Code) Devo Trabalhar Aqui

### Antes de mudar código
1. Ler este CLAUDE.md
2. Ler o(s) arquivo(s) que vou modificar (e os arquivos relacionados)
3. Se for mudança estrutural (novo modelo, novo cálculo), confirmar com o usuário antes
4. Verificar se a mudança pode quebrar invariantes (receita nominal = VGV, soma fluxo = 100%)

### Depois de mudar código
1. Rodar `python auto_teste.py` se mexi na engine
2. Verificar sintaxe: `python -c "import ast; ast.parse(open('src/arquivo.py', encoding='utf-8').read())"`
3. Rodar `python teste_exportadores.py` se mexi em exportação ou engine
4. **Atualizar este CLAUDE.md** se introduzi conceitos novos, novos arquivos ou novas decisões

### Princípios de execução
- **Conservar o que funciona**: 7 testes matemáticos + 140 de integração passando. Não quebrar invariantes.
- **Auto-save é sagrado**: nenhuma mudança pode reintroduzir botões "Salvar Aba".
- **Linguagem imobiliária**: ao adicionar labels/tooltips, usar vocabulário que o Arthur entende.
- **Defensivo na interface**: erros de validação não devem quebrar a tela.
- **Plotly para gráficos**: usar a paleta e configuração de `tabela_mensal.py` como referência.

### O que NÃO fazer
- ❌ Não usar `numpy_financial` (incompatível com Python 3.14)
- ❌ Não calcular dentro da interface — sempre delegar para `src/engine/`
- ❌ Não usar `streamlit run` (sempre `python -m streamlit run`)
- ❌ Não criar arquivos JSON/XLSX no diretório raiz — usar `tempfile.gettempdir()`
- ❌ Não acentuar nomes de variáveis Python
- ❌ Não introduzir dependências novas sem avisar
- ❌ Não tornar `tabela_mensal_distribuicao` editável — é read-only por design

---

## 10. Histórico de Versões

- **v0.8.0** (atual — 2026-05): Redesign completo da Aba 2 — `FluxoTipologia` por tipologia (fluxo + curva de vendas + fatores de preço unificados). Migração automática de JSONs antigos. 140 testes de integração. Limpeza de arquivos de documentação estática.
- **v0.7.0**: Refatoração da distribuição temporal para gráfico Plotly consultivo; % do VGV nas despesas; blocos A–E implementados
- **v0.6.5**: Localização no mapa (OpenStreetMap); Auto-calc, hash cache, Modo Apresentação
- **v0.6.0**: Redesign visual completo; módulos 9–12; exportação HTML
- **v0.5.0**: Auto-save, validações de plausibilidade, painel de pendências, Aba 0
- **v0.4.0**: Tabela mensal como input principal; Aquisição do Terreno separada; TMA na Aba 7
- **v0.3.0**: Abas 2–5 funcionais via interface
- **v0.2.0**: Aba 1 com auto-save + sidebar completa
- **v0.1.0**: Engine + Excel via CLI/JSON

---

## 11. Contato e Contexto

- **Desenvolvido com**: Claude Code (VS Code) em pair programming com Arthur
- **Versão atual**: v0.8.0 — sistema completo com arquitetura FluxoTipologia
