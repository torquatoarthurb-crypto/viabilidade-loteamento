# Manual do Usuário — Sistema de Viabilidade Econômica de Loteamento
**Versão 0.7.0**

---

## Como ler este manual

Este manual explica **cada tela e cada funcionalidade** do sistema, na ordem em que você usaria para analisar um loteamento do zero. Não é preciso ser especialista em finanças nem em tecnologia — basta seguir os passos e preencher os dados do seu empreendimento.

---

## 1. Como abrir o sistema

1. Abra o **Prompt de Comando** (aperte `Win + R`, digite `cmd`, Enter)
2. Navegue até a pasta do sistema:
   ```
   cd C:\Users\arthu\OneDrive\Desktop\Viabilidade\Rev_03
   ```
3. Digite o comando abaixo e pressione Enter:
   ```
   python -m streamlit run app.py
   ```
4. Uma página abrirá automaticamente no seu navegador (geralmente em `http://localhost:8501`)
5. Para fechar: volte ao Prompt de Comando e pressione `Ctrl + C`

> **Atalho importante:** Com o sistema aberto, pressione `Ctrl + Enter` em qualquer momento para calcular o fluxo de caixa.

---

## 2. Visão geral da interface

### Barra lateral (esquerda)
A barra lateral é o painel de controle principal. Ela contém:
- **Ações do projeto**: Novo, Abrir, Salvar, Calcular e Exportar
- **Menu de módulos**: 13 módulos de navegação com ícones de status
- **Resumo em tempo real**: VGV, custo total e margem bruta atualizados instantaneamente
- **Painel de pendências**: lista de erros, avisos e dicas por módulo

### Status dos módulos (ícones)
| Ícone | Significado |
|---|---|
| ✅ | Dados preenchidos corretamente |
| ⚠️ | Aviso — pode calcular, mas verifique |
| ❌ | Erro — corrija antes de calcular |

### Salvamento automático
**Não existe botão "Salvar Aba".** Cada campo que você edita é salvo automaticamente. O único botão de salvar que existe é o `💾 Salvar JSON`, que grava o arquivo do projeto no seu computador para uso futuro.

---

## 3. Módulo 0 — Visão Geral (Dashboard de Entrada)

### Para que serve
É a tela principal do sistema após o cálculo. Mostra um resumo executivo completo do empreendimento.

### O que você encontra aqui

**Estimativas pré-cálculo** (quando o fluxo ainda não foi calculado):
Mesmo sem calcular, o sistema mostra estimativas do VGV, custo de obras, custo do terreno e margem bruta com base nos dados já preenchidos. Um aviso amarelo indica que são apenas estimativas.

**Cards de KPIs** (após o cálculo):
| Indicador | O que significa |
|---|---|
| **VPL** | Valor Presente Líquido — quanto o projeto vale hoje, descontando a TMA |
| **TIR** | Taxa Interna de Retorno — a rentabilidade anual real do investimento |
| **Payback** | Quantos meses até recuperar o capital investido |
| **Exposição Máxima** | O maior "buraco" de caixa — capital máximo necessário |
| **VGV** | Valor total de venda de todos os lotes |
| **Margem Líquida** | Lucro como percentual do VGV |
| **Resultado** | Lucro líquido em reais |
| **Custo Total** | Soma de todas as saídas do projeto |

**Painel de Saúde do Modelo**: checklist visual mostrando se os dados do projeto estão completos e consistentes (verde/amarelo/vermelho por módulo).

**Linha do Tempo**: representação visual em 4 trilhas horizontais mostrando as fases do projeto (Pré-obra, Obras, Vendas, Repasse).

---

## 4. Módulo 1 — Empreendimento

### Para que serve
Aqui você identifica o empreendimento, informa as áreas, as datas e as tipologias de lote. É a base de todo o cálculo.

### Seção: Identificação
- **Nome do empreendimento**: o nome do projeto (ex.: "Loteamento Bela Vista")
- **Cidade**: nome do município. O sistema tem autocomplete com todos os municípios brasileiros — ao digitar, aparece uma lista de sugestões
- **UF**: selecionada automaticamente ao escolher a cidade

**Localização no mapa (opcional):** você pode colar um link do Google Maps e o sistema extrai automaticamente as coordenadas e exibe um mapa do entorno do terreno. Útil para apresentações.

### Seção: Quadro de Áreas
Preencha as áreas em metros quadrados com base no levantamento topográfico:

| Campo | Definição |
|---|---|
| **Área da Gleba** | Área total do terreno bruto |
| **Sistema Viário** | Ruas, calçadas e avenidas internas |
| **Área Verde** | Praças, parques, áreas de lazer |
| **Área Institucional** | Reserva para escola, UBS, etc. |
| **APP** | Área de Preservação Permanente |
| **Área de Lotes** | Área vendável — o que resta após as demais destinações |

O sistema valida automaticamente se a soma fecha com a gleba e exibe o **aproveitamento** (área de lotes ÷ gleba). Aproveitamento típico em loteamentos urbanos: 55–65%.

### Seção: Datas do Projeto
Defina o calendário do empreendimento. O sistema valida a sequência cronológica automaticamente:

| Data | Significado |
|---|---|
| **M0 — Início** | Quando os estudos começam (mês 0 do projeto) |
| **Aprovação** | Previsão de aprovação junto à prefeitura |
| **Lançamento de Vendas** | Quando as vendas começam |
| **Início das Obras** | Quando a obra começa de fato |
| **Término das Obras** | Entrega da infraestrutura |

Essas datas determinam automaticamente as faixas temporais dos gráficos e as curvas sugeridas de despesas.

### Seção: Tipologias de Lote
Cadastre os diferentes tipos de lote do seu empreendimento. Para cada tipologia:

| Campo | O que preencher |
|---|---|
| **Nome** | Ex.: "Compacto", "Padrão", "Premium", "Esquina" |
| **Quantidade** | Número de lotes dessa tipologia |
| **Área (m²)** | Área média do lote em m² |
| **Modo de preço** | Escolha entre R$/m² ou R$ por lote |
| **Valor unitário** | O preço de venda (por m² ou por lote) |

O sistema calcula em tempo real o VGV por tipologia e o VGV total.

**Barra de aproveitamento**: mostra graficamente a relação entre a área total das tipologias e a área de lotes disponível. Fica vermelha se você exceder a área.

---

## 5. Módulo 9 — Terreno

### Para que serve
Configura como o terreno foi (ou será) adquirido — quanto custa e como será pago. Isso determina o desembolso de caixa para a compra do terreno.

### Formas de pagamento disponíveis

**À vista**: o valor total é pago em um único mês (definido no campo "Mês de pagamento").

**Parcelado**: o valor é dividido em parcelas iguais mensais entre um mês inicial e um mês final que você define.

**Sem desembolso**: o terreno já pertence ao empreendedor (não gera saída de caixa), mas o valor ainda entra na margem como custo implícito.

**Customizado**: você define livre mente a distribuição percentual do pagamento mês a mês.

### Permuta Física
Se parte do pagamento for feita em lotes (permuta física), configure aqui. Os lotes de permuta são excluídos da receita de vendas (eles "saem" do estoque sem gerar receita para o empreendedor).

### Custo de Cartório
Inclua os custos de escritura e registro (ITBI, cartório). São tratados como uma saída separada no fluxo de caixa.

---

## 6. Módulo 2 — Receitas (VGV)

### Para que serve
Define **como** os compradores pagam pelos lotes: qual é a composição do pagamento (entrada, parcelas, balões, financiamento) e **quando** as vendas acontecem ao longo do projeto.

### Seção: Fluxo de Recebíveis
O fluxo de recebíveis define a composição do pagamento de cada venda. Você pode criar **vários fluxos** diferentes para diferentes fases de vendas (ex.: um fluxo de lançamento com desconto, um fluxo para o estoque).

Para cada fluxo, os percentuais **sempre devem somar 100%**. O sistema avisa em tempo real se a soma não fechar.

| Componente | Definição |
|---|---|
| **Sinal (Entrada)** | % pago na data da venda. Número de parcelas do sinal (normalmente 1) |
| **Parcelas durante a Obra** | % pago em parcelas mensais enquanto a obra está em andamento. Define a taxa de juros mensal dessas parcelas |
| **Balões** | % pago em parcelas maiores a cada 12 meses durante a obra |
| **Financiamento** | % financiado após a entrega das obras (ex.: banco). Define prazo em meses e taxa mensal |

> **Referências de mercado** (aparece como tooltip nos campos):
> - Parcelas durante obra: 0,3% a 0,8% a.m.
> - Financiamento pós-obra: 0,6% a 1,0% a.m.
> - Sinal típico: 10% a 20%

O botão **"Duplicar Fluxo"** cria uma cópia do fluxo atual, facilitando criar variações.

### Seção: Curva de Vendas
Define **quando** as vendas acontecem — quantos % do estoque é vendido em cada mês.

**Atalhos por intervalos**: em vez de preencher mês a mês, você define faixas:
1. Clique em `➕` para adicionar uma faixa
2. Defina o mês inicial, mês final e o % do estoque vendido nesse período
3. Selecione qual fluxo de recebíveis se aplica a essa faixa
4. Clique em `▶️ Aplicar`

A soma de todos os intervalos **deve ser 100%**.

**Gerador de Curva S**: clique em "Gerar Curva S" para criar automaticamente uma curva de vendas com formato de sino — vendas lentas no início, pico no meio, desaceleração no final. Esse é o padrão de mercado para lançamentos de loteamento.

**Mini gráfico**: enquanto você preenche a curva, um gráfico de barras mostra visualmente o ritmo de vendas mês a mês.

---

## 7. Módulo 3 — Obras

### Para que serve
Define o custo de implantação da infraestrutura (terraplenagem, saneamento, pavimentação, urbanização) e como esses gastos se distribuem ao longo do tempo.

### Modos de entrada

**Modo Resumido**: informe o custo em R$ por m² e o sistema calcula o total automaticamente. Escolha se a base de cálculo é a área de lotes ou o sistema viário.

**Modo Detalhado**: crie etapas separadas de obra (ex.: Terraplenagem, Rede de Esgoto, Pavimentação, Urbanização). Para cada etapa, defina:
- Nome e valor total
- Distribuição temporal usando os **atalhos por intervalos** (mesma ferramenta da curva de vendas)

### BDI e Contingência
| Campo | Significado | Referência de mercado |
|---|---|---|
| **BDI** | Benefícios e Despesas Indiretas — percentual sobre o custo direto que cobre overhead, lucro do executor, seguros | 15% a 25% |
| **Contingência** | Reserva para imprevistos — percentual sobre o total já com BDI | 5% a 10% |

O custo final de obras = custo direto × (1 + BDI/100) × (1 + contingência/100).

### Cards de benchmark
O sistema mostra automaticamente: custo por m² de lote, custo por m² de gleba e custo por lote — com comparação ao que é praticado no mercado.

### Gráfico de distribuição
Cada etapa tem um gráfico de barras azuis mostrando o desembolso mensal previsto, com faixas coloridas indicando as fases do projeto (pré-obra em amarelo, obras em verde).

---

## 8. Módulo 4 — Despesas de Incorporação

### Para que serve
Cadastra todas as despesas da fase de incorporação (não são obras de infraestrutura, são os custos de desenvolver o projeto): projetos, licenças, marketing, jurídico, etc.

### Despesas pré-definidas
O sistema já cria automaticamente **9 despesas típicas** de loteamento com as curvas temporais sugeridas vinculadas às datas do projeto:

| Despesa | Categoria | Quando ocorre |
|---|---|---|
| Projetos Urbanísticos | Projetos | Linear antes da aprovação |
| Projetos Complementares | Projetos | Linear do lançamento ao início das obras |
| Aprovação e Licenciamento | Licenciamento | Linear do início até a aprovação |
| Licença Ambiental | Licenciamento | Linear do início ao início das obras |
| Marketing e Lançamento | Marketing | Concentrado no lançamento |
| Material de Vendas | Marketing | Linear do lançamento ao término das obras |
| Infraestrutura de Canteiro | Outros | No início das obras |
| Despesas Jurídicas | Outros | Linear por todo o projeto |
| Medida Compensatória Urbana e Ambiental | Licenciamento | Antes da aprovação |

Todas começam com **R$ 0,00** — basta preencher o valor de cada uma.

### Tipo de valor
Cada despesa pode ser informada de duas formas (toggle rádio):
- **R$ fixo**: valor em reais (ex.: R$ 350.000)
- **% do VGV bruto**: percentual do total de vendas (ex.: 1,5% do VGV)

### Administração
Percentual sobre a receita mensal recebida, calculado automaticamente ao longo do fluxo de caixa. É o custo de administrar o empreendimento mês a mês.

### Resumo consolidado
Cards no topo da tela mostram o total por categoria (Projetos, Licenciamento, Marketing, Outros) e um mini gráfico do desembolso mensal total de todas as despesas.

---

## 9. Módulo 5 — Impostos e Comissão

### Para que serve
Define a carga tributária do empreendimento e como é paga a comissão de vendas.

### Regime Tributário

**Lucro Presumido**: informe a alíquota efetiva total (soma de IRPJ + CSLL + PIS + COFINS). Para incorporação/loteamento em lucro presumido, a prática típica é **6,73%** sobre a receita bruta.

**Lucro Real**: informe as alíquotas individualmente (IRPJ, CSLL, PIS, COFINS).

### Regime de Apuração
| Opção | Como funciona |
|---|---|
| **Caixa** | Imposto é calculado quando o dinheiro é efetivamente recebido (mais comum em loteamentos) |
| **Competência** | Imposto é calculado na data da venda, independente do recebimento |

### Comissão de Vendas
| Campo | Descrição |
|---|---|
| **% sobre VGV** | Percentual de comissão sobre o valor de venda |
| **Modo de pagamento** | "Integral no mês da venda", "Proporcional ao recebimento" ou "Misto" |

No modo **Misto**, você define que parte da comissão é paga no ato da venda e parte ao longo dos recebimentos.

---

## 10. Módulo 7 — Fluxo de Caixa

### Para que serve
Define a **Taxa Mínima de Atratividade (TMA)** e mostra os indicadores financeiros principais após o cálculo.

### TMA — Taxa Mínima de Atratividade
É o seu custo de oportunidade — a rentabilidade mínima que o projeto precisa superar para valer a pena. Tipicamente, usa-se como referência o CDI ou a rentabilidade de um fundo DI.

- **Referência**: 10% a 18% ao ano para projetos de loteamento no Brasil
- O sistema converte automaticamente de % a.a. para % a.m.

### Indicadores rápidos (pós-cálculo)
Após calcular, esta tela mostra um resumo com VPL, TIR, Payback Simples, Payback Descontado e Exposição Máxima.

### Tabela do Fluxo de Caixa
Tabela completa mês a mês com todas as entradas e saídas do projeto. Colunas = meses, linhas = categorias. Use o botão **"⛶ Tela cheia"** para expandir a tabela em uma janela maior.

---

## 11. Módulo 6 — Resultado Estático (DRE)

### Para que serve
Mostra o **Demonstrativo de Resultado** (DRE) em cascata — a análise estática do projeto, sem considerar o valor do dinheiro no tempo.

### DRE em cascata

```
VGV Bruto                         = valor total de todos os lotes
(-) Permuta Física                  = lotes cedidos como pagamento do terreno
= VGV Vendável                    = receita de vendas efetiva
(+) Receita de Juros               = juros das parcelas Price (receita financeira)
= Receita Total                   = tudo que entra no caixa
(-) Aquisição do Terreno
(-) Cartório
(-) Obras (custo direto + BDI + Contingência)
(-) Projetos
(-) Licenciamento
(-) Marketing
(-) Outros / Administração
(-) Comissão de Vendas
(-) Impostos/Tributos
(-) Permuta Financeira
= LUCRO LÍQUIDO
```

### Cards de margem
- **Margem sobre VGV Vendável**: lucro ÷ VGV vendável
- **Margem sobre VGV Bruto**: lucro ÷ VGV bruto
- **Multiplicador**: quanto o capital se multiplica no projeto

### Tabela por componente
Cada custo aparece com o valor total e o **percentual sobre o VGV** e o **valor por lote** — facilitando benchmarks.

### Comparativo Nominal vs Financeiro
Mostra a divisão entre receita do principal dos lotes (= VGV exato) e a receita de juros gerada pelas parcelas Price. Importante para entender a composição real da receita total.

---

## 12. Módulo 8 — Dashboard

### Para que serve
Apresentação visual completa do projeto com gráficos interativos — ideal para reuniões com sócios, apresentações a bancos e comitês de investimento.

### 7 KPI cards no topo
Resultado, Margem VGV Vendável, TIR, VPL, Pico de Exposição, Payback e Multiplicador Lucro/Exposição.

### Tab 1 — Curva de Caixa
O gráfico mais importante do sistema. Mostra o saldo de caixa acumulado ao longo do tempo:
- **Área vermelha**: período de caixa negativo (capital que precisa estar disponível)
- **Área verde**: período de caixa positivo (retorno do investimento)
- **Linha pontilhada**: saldo acumulado descontado pela TMA
- **Marcador de pico**: indica o mês e valor da exposição máxima
- **Marcador de payback**: indica quando o projeto se paga

### Tab 2 — Composição Mensal
Barras empilhadas mostrando entradas e saídas por categoria em cada mês:
- Barras para cima (verde): receitas recebidas (principal + juros)
- Barras para baixo (cores por categoria): cada tipo de saída

### Tab 3 — Receitas vs Saídas
Curvas acumuladas de receitas totais vs saídas totais. O ponto de cruzamento é o **break-even** do projeto — quando o acumulado de entradas supera o de saídas.

### Tab 4 — Obras e Vendas
Combina dois eixos: desembolso mensal de obras (barras) e percentual do estoque vendido acumulado (linha). Útil para verificar se a velocidade de vendas está alinhada com o cronograma de obras.

### Tabela Mensal Detalhada
Tabela completa do fluxo de caixa com hierarquia visual por seção (verde escuro = receitas, tons marrons = custos, azul = resultados). Use o botão **"⛶ Tela cheia"** para abrir em modal expandido.

---

## 13. Módulo 10 — Ferramentas

### Para que serve
Análises avançadas para responder as perguntas mais frequentes em uma negociação: "Qual preço mínimo eu preciso cobrar?", "Quanto posso pagar pelo terreno?", "Qual o impacto se o custo de obras aumentar?".

### Ferramenta 1 — Análise de Sensibilidade
**Pergunta que responde:** "Se o custo de obras aumentar 15%, a TIR cai de quanto para quanto?"

Varia automaticamente os principais parâmetros (VGV, custo obras, TMA, comissão, terreno) em uma faixa de ±X% e mostra o impacto na TIR. O resultado é um **gráfico tornado** — barras horizontais mostrando qual variável tem maior impacto no resultado.

Como usar:
1. Escolha o intervalo de variação (ex.: ±20%)
2. Clique em calcular
3. O gráfico mostra quais parâmetros mais afetam a TIR

### Ferramenta 2 — Solver Preço Mínimo
**Pergunta que responde:** "Para ter TIR de 25%, qual o preço mínimo por m²?"

Informe a TIR alvo e o sistema calcula automaticamente o multiplicador de preço que atinge exatamente essa rentabilidade. Você vê: "Precisa cobrar pelo menos 1,12x o preço atual" ou "R$ 580/m² (em vez dos R$ 550/m² atuais)".

### Ferramenta 3 — Solver Terreno Máximo
**Pergunta que responde:** "Com TIR alvo de 22%, quanto posso pagar pelo terreno?"

O sistema calcula o valor máximo do terreno que ainda viabiliza a TIR desejada. Resultado em R$ totais e em R$/m² de gleba — o indicador que o mercado usa para negociar glebas.

### Ferramenta 4 — Faseamento
**Para que serve:** Simular um projeto em 2 fases separadas — cada fase com suas próprias datas, tipologias e VGV.

Loteamentos grandes são frequentemente implantados em fases para reduzir a exposição e testar o mercado. Esta ferramenta permite modelar isso.

### Ferramenta 5 — Benchmarks de Mercado
Tabela com faixas de referência do mercado para os principais indicadores, comparando com a posição atual do seu projeto. Ideal para justificar os parâmetros usados em apresentações a banco ou sócios.

---

## 14. Módulo 11 — Cenários

### Para que serve
Comparar diferentes versões do mesmo projeto lado a lado, e analisar o risco do investimento com simulação de Monte Carlo.

### Comparativo de Cenários
**Para que serve:** Salvar e comparar versões diferentes (ex.: "Cenário Base", "Cenário Otimista", "Cenário Pessimista").

Como usar:
1. Configure e calcule o projeto
2. Dê um nome ao cenário (ex.: "Base — R$ 550/m²") e clique em "Salvar cenário"
3. Altere os parâmetros (ex.: preço para R$ 500/m²) e calcule novamente
4. Salve como "Pessimista — R$ 500/m²"
5. A tabela comparativa mostra TIR, VPL, Margem, Exposição e Payback de todos os cenários salvos

### Monte Carlo
**Para que serve:** Entender o risco do projeto — com que probabilidade a TIR fica acima do seu mínimo aceitável?

Como usar:
1. Defina a variação (%) que cada parâmetro pode ter (ex.: ±10% no custo de obras, ±15% no VGV)
2. Defina o número de simulações (ex.: 1.000)
3. O sistema roda 1.000 cenários aleatórios e exibe a distribuição de TIR
4. Você vê: "Em 90% dos cenários, a TIR ficou acima de X%"

---

## 15. Módulo 12 — Gestão de Projetos

### Para que serve
Gerenciar uma biblioteca de projetos — listar, abrir, criar, duplicar e excluir projetos salvos.

### Como funciona
A tela exibe cards com o resumo de cada projeto salvo (VGV, TIR, margem, data do último cálculo). Você pode:
- **Abrir** um projeto existente
- **Criar** um novo projeto
- **Duplicar** um projeto (para criar variações)
- **Excluir** projetos obsoletos

> **Como salvar projetos**: use o botão `💾 Salvar JSON` na sidebar. Os projetos são salvos como arquivos `.json` no seu computador, em uma pasta à sua escolha. Para reabrir, use `📂 Abrir JSON`.

---

## 16. Módulo 13 — Financiamento Bancário

### Para que serve
Simular o uso de uma linha de crédito bancária (CCB/CCE) para cobrir os períodos de caixa negativo do projeto. Mostra o impacto do financiamento na TIR, VPL, Margem e Exposição.

### Quando usar
Se a exposição máxima do projeto for alta (acima de R$ 2-3 MM), financiar parte desse montante pode:
- Reduzir o capital próprio necessário
- Aumentar o retorno sobre o capital próprio (ROE)
- Reduzir o risco do projeto para o investidor

### Parâmetros configuráveis
| Campo | Definição | Referência |
|---|---|---|
| **Taxa de juros (% a.m.)** | Juros cobrados sobre o saldo devedor | CDI + 3-6% a.a. (~1,5-2,0% a.m.) |
| **Limite da linha (R$)** | Valor máximo disponível para saque. Use 0 para sem limite | — |
| **Período de carência** | Meses iniciais sem amortização do principal | — |
| **Comissão de abertura** | % sobre o limite, cobrado no M0 | — |
| **IOF sobre cada saque** | % adicionado ao saldo devedor | 0,38% típico |

### Resultado
Após calcular com o financiamento ativo, o sistema exibe uma tabela comparativa **Sem financiamento vs Com financiamento**:
- TIR (com delta em pontos percentuais)
- VPL, Margem Líquida, Exposição Máxima
- Juros totais pagos ao banco, comissão, custo total do financiamento

---

## 17. Módulo 14 — Reajustes Monetários

### Para que serve
Aplicar correção monetária por índices de inflação (INCC, IPCA, IGP-M) sobre custos de obras e parcelas dos compradores.

### Quando usar
Em projetos com prazo de obras acima de 18 meses, a inflação da construção civil (INCC) pode aumentar significativamente os custos. Da mesma forma, contratos de loteamento frequentemente preveem correção das parcelas durante a obra.

### O que pode ser reajustado
| Item | Índice sugerido | Efeito no fluxo |
|---|---|---|
| **Custo de obras** | INCC | Aumenta as saídas mensais de obras |
| **Parcelas do comprador** | INCC, IPCA ou IGP-M | Aumenta as receitas mensais |
| **Terreno parcelado** | IGP-M ou IPCA | Aumenta as saídas do terreno |

> **Importante:** Os valores são inseridos em preços de hoje. O sistema aplica a correção automaticamente no cálculo.

---

## 18. Funcionalidades da Barra Lateral

### Ações do projeto

**`📄 Novo Projeto`**: cria um novo projeto vazio com valores padrão. **Atenção**: todos os dados não salvos serão perdidos.

**`📂 Abrir JSON`**: carrega um projeto previamente salvo. O arquivo `.json` é gerado pelo próprio sistema.

**`💾 Salvar JSON`**: salva o projeto atual como arquivo `.json` no seu computador. Use nomes descritivos (ex.: `bela_vista_v2_pessimista.json`).

**`🧮 Calcular fluxo de caixa`**: roda o cálculo completo do projeto. Tecla de atalho: `Ctrl + Enter`.

**`📥 Exportar Excel`**: gera um relatório `.xlsx` com 5 abas (veja seção abaixo).

**`📋 Modo Apresentação`**: oculta a barra lateral e exibe apenas o Dashboard — ideal para apresentar a tela em reunião.

### Auto-calcular
Toggle que, quando ativado, recalcula automaticamente sempre que você mudar algum dado. Útil durante análises, mas pode ser desativado para ganhar velocidade ao preencher muitos dados de uma vez.

### Histórico de Versões
Após cada cálculo, o sistema salva automaticamente um snapshot. No expander "Histórico" na barra lateral, você pode ver os últimos cálculos realizados e comparar TIR/VPL entre eles.

### Painel de Pendências
Lista todos os erros, avisos e dicas do projeto. Ao clicar em uma pendência, o sistema navega automaticamente para o módulo correspondente.

### Resumo em Tempo Real
No rodapé da barra lateral, exibe continuamente:
- VGV vendável
- Total de saídas estimado
- Margem bruta estimada

---

## 19. Exportação Excel

O relatório Excel gerado pelo sistema tem **5 abas**:

| Aba | Conteúdo |
|---|---|
| **Resumo** | Informações do projeto, tipologias, VGV, custos e indicadores principais |
| **Fluxo de Caixa** | Tabela completa mês a mês de todas as entradas e saídas |
| **Indicadores** | KPIs financeiros (VPL, TIR, Payback, Exposição) formatados |
| **Simulação Lote** | Cronograma de pagamento de 1 lote por tipologia — útil para mostrar ao comprador |
| **Verificação Receitas** | Detalhamento completo de cada venda: sinal, parcelas, balões, financiamento, principal e juros mês a mês. Útil para auditoria e banco |

---

## 20. Fluxo de trabalho recomendado

Para analisar um loteamento do zero, siga esta sequência:

1. **Módulo 1 — Empreendimento**: preencha a identificação, áreas, datas e tipologias
2. **Módulo 9 — Terreno**: defina valor e forma de pagamento do terreno
3. **Módulo 2 — Receitas**: configure os fluxos de recebíveis e a curva de vendas
4. **Módulo 3 — Obras**: informe o orçamento de obras e a distribuição temporal
5. **Módulo 4 — Incorporação**: preencha os valores das despesas pré-definidas
6. **Módulo 5 — Impostos**: confirme o regime tributário e a comissão
7. **Módulo 7 — TMA**: defina sua taxa mínima de atratividade
8. **Calcular** (`Ctrl + Enter` ou botão na sidebar)
9. **Módulo 6 — Resultado**: analise a DRE completa
10. **Módulo 8 — Dashboard**: veja os gráficos e KPIs
11. **Módulo 10 — Ferramentas**: use o Solver de Preço ou Terreno conforme necessário
12. **Salvar JSON**: salve o projeto antes de fazer variações
13. **Módulo 11 — Cenários**: compare versões diferentes do projeto
14. **Exportar Excel**: gere o relatório para apresentação

---

## 21. Perguntas frequentes

**P: Perco os dados se fechar o navegador?**
R: Sim, se você não salvou o JSON, perde. Salve com `💾 Salvar JSON` antes de fechar.

**P: Posso ter dois projetos abertos ao mesmo tempo?**
R: Não. O sistema trabalha com um projeto por vez. Para comparar projetos diferentes, use o Módulo 11 (Cenários) ou o Módulo 12 (Projetos).

**P: O que é receita financeira (juros)?**
R: Quando o comprador paga parcelas com juros (sistema Price), o valor total recebido é maior que o preço do lote. A diferença são os juros. O sistema separa os dois componentes porque eles têm tratamento tributário diferente e porque a receita nominal (= VGV exato) é o que entra na base de cálculo dos impostos.

**P: A TIR está muito alta (acima de 50%). É possível?**
R: Em projetos com alta alavancagem, curva de vendas rápida e prazo curto, TIRs altas são matematicamente possíveis. Verifique se a curva de vendas e os fluxos de recebíveis estão corretos. Use a Análise de Sensibilidade (Módulo 10) para testar cenários mais conservadores.

**P: Qual a diferença entre Payback Simples e Payback Descontado?**
R: Payback Simples = quantos meses para o saldo acumulado zerar (sem descontar juros). Payback Descontado = quantos meses para o saldo acumulado descontado pela TMA zerar. O segundo é mais conservador e financeiramente mais correto.

**P: O que é exposição máxima?**
R: É o maior "buraco" de caixa — o momento em que o projeto precisa de mais capital disponível simultaneamente. É o capital mínimo que você ou seus sócios precisam ter aportado para o projeto não travar.

**P: Posso modelar um loteamento com condomínio?**
R: O sistema atual é otimizado para loteamentos abertos. Para condomínio fechado, os custos de guarita, muro perimetral e área de lazer devem ser inseridos manualmente nas despesas de incorporação.

---

*Manual do Usuário — Versão 0.7.0 — Sistema de Viabilidade Econômica de Loteamento*
