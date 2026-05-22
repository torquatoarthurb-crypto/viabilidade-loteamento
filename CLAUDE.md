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
viabilidade_loteamento/
├── app.py                              # Entry point Streamlit
├── rodar.py                            # Modo CLI (alternativo)
├── auto_teste.py                       # 7 testes matemáticos da engine
├── README.md, INSTALACAO.md, INTERFACE.md, GUIA_JSON.md
├── requirements.txt
├── .streamlit/config.toml              # Tema escuro
├── exemplos/
│   └── projeto_exemplo.json            # "Loteamento Vila Verde", 224 lotes
└── src/
    ├── modelos/                        # Pydantic (dados de entrada)
    │   ├── terreno.py                  # Aba1Terreno, Tipologia, QuadroAreas, DatasProjeto, InfoEmpreendimento
    │   │                               # InfoEmpreendimento tem: nome, cidade, uf, latitude, longitude, link_maps
    │   ├── receitas.py                 # Aba2Receitas, FluxoRecebiveis, FaixaCurvaVendas
    │   ├── obras.py                    # Aba3Obras, EtapaObra, OrcamentoResumido
    │   ├── desenvolvimento.py          # Aba4Desenvolvimento, DespesaTemporal, Administracao
    │   │                               # DespesaTemporal tem: modo_valor ("fixo"|"pct_vgv"), percentual_vgv
    │   ├── tributos.py                 # Aba5Impostos, Tributos, ComissaoVenda, PermutaFinanceira
    │   ├── financeiro.py               # AquisicaoTerreno, ParametrosFinanceiros (TMA)
    │   ├── projeto.py                  # Projeto (objeto raiz)
    │   └── construtores.py             # projeto_novo() (template)
    ├── engine/                         # Cálculos matemáticos (sem Streamlit)
    │   ├── utilidades.py               # parcela_price, curva_s, meses_entre, etc.
    │   ├── indicadores_financeiros.py  # NPV, IRR (próprios — sem numpy_financial)
    │   ├── recebimentos.py             # Vendas → fluxo de recebíveis
    │   ├── despesas.py                 # Distribuição temporal de despesas
    │   └── fluxo_caixa.py              # Orquestrador principal → ResultadoCalculo
    ├── io_projeto/
    │   ├── json_io.py                  # Carregar/salvar JSON
    │   ├── exportar_excel.py           # Gerar relatório .xlsx (5 abas: Apresentação + 4)
    │   └── exportar_html.py            # C11: exportação HTML para impressão como PDF
    └── interface/                      # Streamlit (apresentação)
        ├── helpers.py                  # Formatação BRL, marcos, linha_do_tempo SVG (usada só na Aba 0)
        ├── tabela_mensal.py            # Componente: gráfico Plotly (read-only) + atalhos_por_intervalos
        ├── tema.py                     # CSS customizado (tema escuro, variáveis CSS)
        ├── tema_componentes.py         # Header, KPI cards, linha do tempo em trilhas, título módulo
        ├── validacoes.py               # 13 regras de plausibilidade
        ├── sidebar.py                  # Sidebar: Ações + auto-calc + hash cache + histórico + modo apresentação
        └── abas/
            ├── aba0_visao_geral.py     # Módulo 0: KPIs, saúde, linha do tempo + estimativas pré-cálculo (D3)
            ├── aba1_terreno.py         # Módulo 1: Identificação, áreas, tipologias + mapa OSM (E5)
            ├── aba_terreno.py          # Módulo 9: Terreno avançado (aquisição do terreno separada)
            ├── aba2_receitas.py        # Módulo 2: Aquisição terreno, fluxos recebíveis, curva de vendas
            ├── aba3_obras.py           # Módulo 3: Etapas com gráfico Plotly de distribuição
            ├── aba4_desenvolvimento.py # Módulo 4: Despesas com % VGV + gráfico Plotly de distribuição
            ├── aba5_impostos.py        # Módulo 5: Tributos + comissão
            ├── aba6_resultado.py       # Módulo 6: Resultado estático (aba6 separada de placeholders)
            ├── aba7_fluxo.py           # Módulo 7: TMA + indicadores
            ├── aba8_dashboard.py       # Módulo 8: Dashboard com gráficos Plotly
            ├── aba_ferramentas.py      # Módulo 10: Sensibilidade, Solver Preço, Solver Terreno, Faseamento, Benchmarks
            ├── aba_cenarios.py         # Módulo 11: Comparativo de Cenários + Monte Carlo
            └── aba_projetos.py         # Módulo 12: Gestão de múltiplos projetos (biblioteca)
```

---

## 3. Arquitetura e Decisões de Design

### Fluxo de dados
```
Usuário (interface) → session_state → Pydantic (validação) → engine → resultado → interface
                                                                    ↘ exportador Excel / HTML
```

### Princípios
1. **Engine é pura**: o módulo `engine/` não conhece Streamlit nem JSON. Recebe um `Projeto` e devolve um `ResultadoCalculo`.
2. **Modelos são imutáveis** durante o cálculo: cada mudança gera um novo `Projeto` via `model_copy(update={...})`.
3. **Auto-save em todas as abas**: NÃO há botões "Salvar Aba". Cada alteração é gravada no `session_state` e o `Projeto` é reconstruído silenciosamente. Erros de validação não impedem o salvamento — eles aparecem no painel de pendências da sidebar.
4. **Interface não calcula**: cálculos só rodam quando o usuário clica em "Calcular fluxo de caixa". Se o projeto muda, o resultado é invalidado (`invalidar_resultado()`).
5. **Receita nominal vs receita financeira**: o sistema separa o **principal** (= VGV exato) dos **juros** embutidos nas parcelas Price. Isso é crítico para o cálculo correto de impostos.
6. **Distribuição temporal é sempre lida via gráfico + intervalos**: `tabela_mensal_distribuicao` renderiza um gráfico Plotly read-only; a edição acontece exclusivamente via `atalhos_por_intervalos` (ferramenta de faixas).

### Conceitos do domínio (linguagem do mercado)
- **VGV bruto**: valor geral de vendas (somatório de todos os lotes)
- **VGV vendável**: VGV bruto menos lotes destinados à permuta física
- **Permuta física**: parte do terreno é paga em lotes (não geram receita)
- **Permuta financeira**: parte do VGV vai pro vendedor do terreno em dinheiro
- **Fluxo de recebíveis**: composição do pagamento de uma venda (sinal % + parcelas obra % + balões % + financiamento %). **Sempre soma 100%.**
- **Curva de vendas**: distribuição mês a mês de quantos % do estoque é vendido em cada mês. **Sempre soma 100%.**
- **Sistema Price**: parcelas iguais com decomposição mensal entre principal e juros
- **BDI**: Benefícios e Despesas Indiretas (multiplicador sobre custo direto, ~15-25% típico)
- **Contingência**: reserva sobre o total já com BDI (~5-10% típico)
- **TMA**: Taxa Mínima de Atratividade (custo de oportunidade, ~10-18% a.a. típico)
- **Exposição máxima**: maior valor negativo do saldo acumulado (capital máximo necessário)

---

## 4. Estado Atual (versão 0.7.0)

### O que está pronto e funcionando

#### Engine matemática (100%)
- ✅ Sistema Price com decomposição principal/juros (validado: soma principal = VGV exato)
- ✅ Curva S logística simétrica
- ✅ NPV + IRR (Newton-Raphson com bisseção fallback)
- ✅ Recebimentos: sinal, parcelas obra, balões anuais, financiamento Price pós-obra
- ✅ Quantidade de balões calculada automaticamente (1 a cada 12 meses até término obras)
- ✅ Receita NOMINAL separada de receita FINANCEIRA (juros embutidos)
- ✅ BDI + contingência multiplicativos
- ✅ Comissão (sobre venda / sobre recebimento / misto)
- ✅ Permuta física e financeira
- ✅ Impostos (lucro presumido / lucro real, regime caixa / competência)
- ✅ Indicadores: VPL, TIR, payback simples, payback descontado, exposição máxima

#### Interface — Módulos de entrada (1–5, 7, 9)

**Módulo 0 — Visão Geral** (`aba0_visao_geral.py`)
- KPIs em grid 4×2 (VPL, TIR, Payback, Exposição, VGV, Margem, Resultado, Custo Total)
- Card "Saúde do modelo" com checks de pendências
- Linha do tempo em 4 trilhas horizontais (Pré-obra / Obras / Vendas / Repasse)
- **D3**: Estimativas pré-cálculo quando resultado ainda não existe (4 cards: VGV est., Obras est., Terreno, Margem Bruta est.) com banner amarelo de aviso

**Módulo 1 — Dados do Empreendimento** (`aba1_terreno.py`)
- Identificação: nome, cidade (autocomplete cidades BR — A8), UF
- Quadro de áreas: gleba, sistema viário, verde, institucional, APP, lotes
- **A3**: Validação inline de sobre-utilização da área de lotes
- **A4**: Validação inline de sequência de datas (sem retroceder)
- **B6**: Hint inline de área sem tipologia atribuída
- Tipologias de lote: tabela editável com quantidade, área, modo de preço (R$/m² ou R$/lote), valor
- **A1**: Barra de progresso HTML mostrando área total das tipologias vs área de lotes
- **E5**: Seção "📍 Localização no mapa (opcional)": campo URL Google Maps com extração automática de coordenadas (regex), inputs manuais de lat/lon como fallback, embed OpenStreetMap (sem API key)

**Módulo 9 — Terreno** (`aba_terreno.py`)
- Aquisição do terreno separada da aba de receitas
- Suporte a compra à vista, financiamento, permuta física + financeira

**Módulo 2 — Receitas (VGV)** (`aba2_receitas.py`)
- Aquisição do terreno com permuta financeira embutida
- Fluxos de recebíveis em expanders (sinal, parcelas obra, balões, financiamento) com indicador de soma (**A6**)
- **B4**: Gerador de Curva S na seção de curva de vendas
- **A9**: Mini sparkline da curva de vendas
- **A10**: Indicador de "alterações não salvas" na curva de vendas
- Curva de vendas mensal: atalhos por intervalos + seleção de fluxo por mês
- Tooltips de benchmark nos juros: parcelas obra 0,3–0,8% a.m., financiamento 0,6–1,0% a.m. (**D6**)

**Módulo 3 — Despesas de Obras** (`aba3_obras.py`)
- Modo resumido (R$/m² + distribuição mensal) ou detalhado (etapas com distribuição mensal)
- Cada etapa: ferramenta de intervalos + gráfico Plotly de distribuição (barras azuis, fases Obras/Vendas em vrect, marcos como linhas tracejadas)
- Tooltips de benchmark: BDI 15–25%, contingência 5–10% (**D6**)
- **B1**: Cards de benchmark de custo (R$/m², R$/lote) com comparação ao mercado

**Módulo 4 — Despesas de Incorporação** (`aba4_desenvolvimento.py`)
- Despesas em expanders por item; categorias: Projetos, Licenciamento, Marketing, Outros
- Cada despesa: nome, categoria, valor (**R$ fixo** ou **% do VGV bruto** — toggle radio com cálculo automático)
- Atalhos contextuais por categoria (sugestões de curva vinculadas aos marcos do projeto)
- Ferramenta de intervalos + gráfico Plotly de distribuição (mesmo visual da Aba 3)
- **B3**: Resumo consolidado no topo: 5 cards por categoria + mini gráfico de desembolso mensal total
- Administração: % sobre receita mensal (calculado no fluxo)
- Filtro "mostrar só meses preenchidos"
- Pré-população automática com 9 despesas típicas de loteamento, curvas vinculadas aos marcos reais

**Módulo 5 — Impostos e Comissão** (`aba5_impostos.py`)
- Regime tributário: lucro presumido / lucro real
- Regime de apuração: caixa / competência
- ITBI, registro, outras taxas
- Comissão de venda: % sobre venda ou sobre recebimento ou misto

**Módulo 7 — Fluxo de Caixa** (`aba7_fluxo.py`)
- TMA (Taxa Mínima de Atratividade) com auto-save
- Indicadores rápidos pós-cálculo: VPL, TIR, Payback, Exposição
- **A7**: Slider de período na tabela do fluxo mensal

#### Interface — Módulos analíticos (6, 8, 10, 11, 12)

**Módulo 6 — Resultado Estático** (`aba6_resultado.py`)
- DRE (Demonstrativo de Resultado) completa
- Receitas: VGV bruto, permuta física (dedução), VGV vendável, receita nominal, receita de juros, receita total
- Saídas: terreno, obras (direto + BDI + contingência), despesas por categoria, comissão, impostos
- Resultado bruto e líquido; margens sobre VGV; composição percentual de cada custo
- Comparativo resultado nominal vs VPL
- Tabela de simulação de 1 lote (price por lote/mês)

**Módulo 8 — Dashboard** (`aba8_dashboard.py`)
- Gráfico de fluxo de caixa mensal (entradas vs saídas vs saldo acumulado) — Plotly
- Gráfico de exposição ao longo do tempo
- Gráfico de pizza: composição das saídas
- Gráfico de barras: receitas por origem (sinal, parcelas, balões, financiamento)
- Indicadores principais em destaque

**Módulo 10 — Ferramentas** (`aba_ferramentas.py`)
- **C1 — Análise de Sensibilidade**: tornado chart mostrando impacto de ±N% em cada variável (VGV, custo obras, TMA, comissão, terreno) sobre a TIR
- **C3 — Solver Preço Mínimo**: dado TIR alvo, calcula multiplicador de preço mínimo que viabiliza o projeto (bisseção)
- **C7 — Benchmarks de Mercado**: tabela com faixas de referência de mercado + posição atual do projeto em cada indicador
- **C9 — Solver Terreno Máximo**: dado TIR alvo, calcula valor máximo a pagar pelo terreno
- **C10 — Faseamento**: simulador de 2 fases (divide o projeto em Fase 1 e Fase 2 com datas e VGV próprios)

**Módulo 11 — Cenários e Monte Carlo** (`aba_cenarios.py`)
- **C2 — Comparativo de Cenários**: salva snapshots nomeados do projeto calculado e compara em tabela lado a lado (VGV, custo, TIR, VPL, margem, exposição)
- **C4 — Monte Carlo**: distribui TIR em N simulações variando parâmetros com distribuição normal; histograma de resultados; percentis P10/P50/P90

**Módulo 12 — Gestão de Projetos** (`aba_projetos.py`)
- **C8**: Biblioteca de projetos salvos; listar, abrir, criar, duplicar, excluir projetos
- Cards com resumo de cada projeto (VGV, TIR, margem, data)
- Integração com `json_io.py` para persistência

#### Interface — Sidebar e navegação

- **Navegação vertical por módulos** (13 módulos: 0–9 entrada/resultado, 10–12 ferramentas)
- **Status visual** ✅/⚠️/❌ em cada módulo conforme pendências
- **Resumo em tempo real** no rodapé (VGV, custo total, margem bruta)
- **Header com breadcrumb**: Projetos › Nome › Versão › Módulo + "💾 Salvo automaticamente"
- **D1 — Auto-calcular**: toggle que recalcula automaticamente quando o projeto muda
- **D2 — Cache hash MD5**: skip do recálculo se nada mudou (hash MD5 do JSON do projeto)
- **D7 — Ctrl+Enter → Calcular**: JS injection em `app.py` (height=0) detecta atalho e clica no botão
- **D8 — Modo Apresentação**: botão "📋 Apresentação" esconde a sidebar via CSS, exibe Aba 0 em tela cheia com botão "✕ Sair"
- **C14 — Histórico de versões**: auto-snapshot após cada cálculo; expander na sidebar mostra últimas N versões com diff de TIR/VPL

#### Exportações
- **Excel** (5 abas): Apresentação (DRE resumida + indicadores), Resumo, Fluxo de Caixa, Indicadores, Simulação Lote
  - **B10**: Aba "Apresentação" como primeira aba, formatada para comitê
  - Receita nominal e financeira como colunas separadas
- **HTML** (**C11**): `exportar_html.py` gera relatório HTML self-contained para impressão como PDF; botão na sidebar

### Bugs corrigidos durante o desenvolvimento (importante referência)

1. **`numpy_financial` removido** → implementação própria de NPV/IRR
2. **`cell.font = cell.font`** quebrava `openpyxl` novo (Python 3.14)
3. **NPV com rate=-100%** → divisão por zero (limite ajustado para -99%)
4. **DataFrames vazios sem colunas** → tabelas dinâmicas não mostravam botão "+" (corrigido criando DataFrame com schema mesmo vazio)
5. **🔴 Bug crítico de receita perdida**: vendas após o término das obras perdiam silenciosamente o `percentual_obra` do fluxo (porque `qtd_parcelas_obra` ficava negativo). Correção: pagamento concentrado no mês da venda quando `mes_venda > mes_termino_obras`. Validado: receita nominal = VGV exato. Local: `src/engine/recebimentos.py`, função `_gerar_recebimentos_de_uma_venda`.
6. **PowerShell path escape**: caminhos com `\a`, `\b`, `\i` eram interpretados como escape sequences — sempre usar `/` (forward slash) em `python -c "open('src/...')"`.

### Testes existentes
- `auto_teste.py`: 7 testes matemáticos (parcela Price, curva S, meses_entre, NPV, IRR, simulação 1 lote)
- Validação de invariantes: receita nominal + financeira = total recebido (exato)
- Validação: receita nominal = VGV vendável (exato após bug corrigido)

---

## 5. Próximos Passos Pendentes

### Polimento de módulos existentes
- Aba 6 (Resultado Estático): verificar se a DRE está cobrindo todos os cenários de permuta e comissão
- Aba 8 (Dashboard): adicionar filtro de período nos gráficos do fluxo de caixa
- Botão "Exportar PDF (Comitê)" na Aba 0 ainda não está conectado ao HTML export (C11)

### Funcionalidades em aberto
- Importação de dados de outras fontes (CSV, Excel)
- Relatório de comparativo de cenários em Excel (C2 só compara na tela)
- Filtro temporal no gráfico de fluxo de caixa (Módulo 8)

### Refinamentos de UX solicitados
- Nenhum pendente registrado até esta versão

---

## 6. Convenções e Boas Práticas do Projeto

### Estilo de código
- **Comentários em português** (sem acentos, ex.: `Calcular VPL` em vez de `Cálculo`)
- **Strings de UI em português com acentos** (`"Mês de pagamento"`)
- **Type hints** sempre que possível (Python moderno: `list[int]`, `dict[str, float]`)
- **Pydantic para validação**: nunca confiar em dados crus do JSON ou da interface
- **Nomes descritivos**: `mes_termino_obras` em vez de `mto`, `percentual_estoque` em vez de `pct`

### Streamlit specifics
- **`session_state` é a fonte da verdade** durante a sessão. Carregar do projeto ao iniciar, salvar de volta após cada mudança.
- **Auto-save** acontece no final de cada `renderizar()` da aba — comparar estado atual com o que está em `get_projeto()` e atualizar via `set_projeto()` se mudou.
- **`st.rerun()`** apenas quando estritamente necessário (mudança estrutural na lista, ex.: adicionar/remover item) — para mudanças de valor, deixar o Streamlit re-renderizar naturalmente.
- **`key=` único e descritivo** em todos os widgets para evitar conflitos.

### Distribuição temporal (tabela_mensal.py)
- **`tabela_mensal_distribuicao`** é **somente leitura** (gráfico Plotly). Nunca esperar edição direta dela.
- A edição de distribuição acontece via **`atalhos_por_intervalos`**, cujo botão "▶️ Aplicar" escreve em `st.session_state[chave_resultado]`.
- O caller deve checar `if chave_atl in st.session_state: despesa["distribuicao"] = st.session_state.pop(chave_atl)` no início do render.

### Gráfico de distribuição — visual padrão
- Barras: azul (`#60A5FA`) quando > 0, escuro (`#1F2937`) quando = 0
- Zona Obras: `rgba(234,179,8,0.08)` (amarelo transparente)
- Zona Vendas: `rgba(34,197,94,0.05)` (verde transparente)
- Marcos: linhas tracejadas cinza (`#6B7280`), labels cinza claro (`#9CA3AF`)
- Background: `paper_bgcolor="#0A0E14"`, `plot_bgcolor="#131822"`, `height=200`

### Linguagem do mercado imobiliário
Usar termos que o usuário entende, não jargão técnico:
- "Entrada" em vez de "Sinal"
- "Parcelas durante a obra" em vez de "Parcelas pré-chaves"
- "% do VGV destinado ao permutante" em vez de só "Permuta financeira"
- Tooltips com práticas de mercado quando relevante

### Validações
Adicionar regras em `src/interface/validacoes.py` quando descobrir novos casos de plausibilidade. Padrão:
- **erro**: bloqueia cálculo coerente (ex.: soma de fluxo ≠ 100%)
- **aviso**: pode calcular, mas resultado pode ser estranho (ex.: sem despesas cadastradas)
- **dica**: valor está fora da prática de mercado mas é tecnicamente válido (ex.: comissão > 10%)

---

## 7. Onde Encontrar as Coisas

| Quero... | Vou em... |
|---|---|
| Adicionar um campo na entrada do usuário | `src/modelos/<area>.py` (Pydantic) + `src/interface/abas/aba<N>_*.py` |
| Mudar como um valor é calculado | `src/engine/<modulo>.py` |
| Adicionar uma regra de validação | `src/interface/validacoes.py` |
| Mexer no visual / cores / cards | `src/interface/tema.py` (CSS) ou `tema_componentes.py` (componentes) |
| Adicionar uma coluna no Excel | `src/io_projeto/exportar_excel.py` |
| Mudar o que aparece na sidebar | `src/interface/sidebar.py` |
| Criar um novo atalho contextual de despesa | `src/interface/tabela_mensal.py`, função `atalhos_contextuais` |
| Adicionar uma nova validação matemática | `auto_teste.py` (já tem 7, padrão é claro) |
| Mudar o relatório HTML | `src/io_projeto/exportar_html.py` |
| Mexer nos módulos de ferramentas | `src/interface/abas/aba_ferramentas.py` (tabs: Sensibilidade, Preço Mínimo, Terreno Máximo, Faseamento, Benchmarks) |
| Mexer nos cenários / Monte Carlo | `src/interface/abas/aba_cenarios.py` |
| Mexer na gestão de projetos | `src/interface/abas/aba_projetos.py` |
| Mudar o estilo do gráfico de distribuição | `src/interface/tabela_mensal.py`, função `tabela_mensal_distribuicao` |
| Adicionar/remover marcos do projeto | `src/interface/helpers.py`, função `marcos_projeto` |

---

## 8. Como Eu (Claude Code) Devo Trabalhar Aqui

### Antes de mudar código
1. Ler este CLAUDE.md
2. Ler o(s) arquivo(s) que vou modificar (e os arquivos relacionados)
3. Se for mudança estrutural (novo modelo, novo cálculo), confirmar com o usuário antes
4. Verificar se a mudança quebra algum teste em `auto_teste.py`

### Depois de mudar código
1. Rodar `python auto_teste.py` se mexi na engine
2. Verificar sintaxe com `python -c "import ast; ast.parse(open('arquivo.py', encoding='utf-8').read())"` (usar forward slashes no caminho)
3. Se possível, rodar a interface (`python -m streamlit run app.py`) e fazer um smoke test
4. **Atualizar este CLAUDE.md** se introduzi conceitos novos, novos arquivos, novas decisões

### Princípios de execução
- **Conservar o que funciona**: o sistema tem 7 testes matemáticos passando. Não quebrar invariantes (receita nominal = VGV, soma de fluxos = 100%, etc.).
- **Auto-save é sagrado**: nenhuma mudança pode reintroduzir botões "Salvar Aba".
- **Linguagem imobiliária**: ao adicionar labels/tooltips, usar vocabulário que o Arthur entende.
- **Defensivo na interface**: erros de validação não devem quebrar a tela, devem aparecer no painel de pendências.
- **Tema escuro profissional é a referência**: novos componentes devem usar as cores definidas em `tema.py` (`var(--bg-card)`, `var(--text-primary)`, etc.).
- **Plotly para gráficos**: usar a mesma paleta de cores e configuração de layout já definida em `tabela_mensal.py` e `aba4_desenvolvimento.py` como referência.

### O que NÃO fazer
- ❌ Não usar `numpy_financial` (incompatível com Python 3.14)
- ❌ Não fazer cálculo dentro de arquivos da interface (`src/interface/`) — sempre delegar pra `src/engine/`
- ❌ Não usar `streamlit` como se fosse `streamlit run` (sempre `python -m streamlit run`)
- ❌ Não criar arquivos JSON ou XLSX no diretório raiz — usar `tempfile.gettempdir()` ou pedir ao usuário
- ❌ Não acentuar nomes de variáveis Python (manter ASCII)
- ❌ Não introduzir dependências novas sem avisar (o usuário não conhece pip e a instalação é manual)
- ❌ Não tornar `tabela_mensal_distribuicao` editável — ela é read-only por design; toda edição passa por `atalhos_por_intervalos`

---

## 9. Histórico de Versões

- **v0.7.0** (atual — 2025-05): Refatoração da distribuição temporal para gráfico Plotly consultivo; % do VGV nas despesas de incorporação; remoção da linha do tempo de todas as abas; consolidação dos blocos A–E implementados
- **v0.6.5**: Bloco E5 (Localização no mapa com OpenStreetMap); Bloco D completo (D1 auto-calc, D2 hash cache, D3 estimativas pré-cálculo, D6 tooltips benchmark, D7 Ctrl+Enter, D8 Modo Apresentação)
- **v0.6.0**: Blocos A (UX), B (Funcional), C (Avançado) implementados; redesign visual completo; novos módulos 9–12 (Terreno, Ferramentas, Cenários, Projetos); exportação HTML
- **v0.5.0**: Melhorias de UX (auto-save, validações de plausibilidade, status visual nas abas, painel de pendências, Aba 0, atalhos contextuais, filtro de meses preenchidos, linguagem imobiliária)
- **v0.4.0**: Tabela mensal como input principal de despesas/etapas/curva de vendas. Reorganização (Aquisição do Terreno → Aba 2; TMA → Aba 7).
- **v0.3.0**: Abas 2-5 funcionais via interface (sem precisar mexer em JSON)
- **v0.2.0**: Aba 1 (Terreno) com auto-save funcional + sidebar com Novo/Abrir/Salvar/Calcular/Exportar
- **v0.1.0**: Engine + relatório Excel funcionando via CLI/JSON

---

## 10. Contato e Contexto

- **Projeto desenvolvido com**: Claude Code (VS Code) em pair programming com Arthur
- **Versão atual**: v0.7.0 — sistema completo com todas as funcionalidades de entrada, análise e ferramentas avançadas
- **Próxima fase**: definir com Arthur quais refinamentos ou funcionalidades novas priorizar
