# Roadmap de Melhorias — Sistema de Viabilidade Econômica de Loteamento
**Base: v0.7.0 | Elaborado em: 2026-05-22**

> Este documento lista melhorias futuras identificadas a partir de simulação de uso real do sistema e pesquisa sobre as necessidades do incorporador imobiliário brasileiro. Cada item é classificado por **impacto para o usuário** e **esforço de desenvolvimento**.

---

## Prioridade Alta — Implementar primeiro

Essas funcionalidades resolvem as maiores dores do dia a dia. São itens que geram mais valor com custo de desenvolvimento relativamente baixo.

---

### 1. Preço Progressivo por Fase de Vendas

**O problema hoje**: o sistema usa um preço fixo por tipologia durante todo o projeto. Na prática, todo loteamento de sucesso sobe o preço conforme o estoque diminui.

**O que implementar**: em cada faixa da curva de vendas, permitir definir um multiplicador de preço. Exemplo:
- Fase 1 (lançamento, M6-M12): fator 0,95× — preço de lançamento com desconto
- Fase 2 (maturação, M13-M18): fator 1,00× — preço cheio
- Fase 3 (estoque, M19-M30): fator 1,10× — preço de estoque com ágio

**Impacto**: subestimar a receita por ignorar o aumento de preço pode distorcer a margem em 3-5 pontos percentuais.

---

### 2. Histórico de Versões com Comparativo

**O problema hoje**: ao calcular novamente com parâmetros diferentes, o resultado anterior é perdido. Não há como recuperar um estado sem ter salvo o JSON com outro nome.

**O que implementar**: automaticamente ao clicar em "Calcular", salvar um snapshot completo (parâmetros + resultado) com data/hora e nome editável. Na sidebar, exibir os últimos N snapshots com botão para restaurar.

**Impacto**: elimina o processo manual de "salvar cópia como Pessimista_v2.json" que hoje é obrigatório para qualquer comparação.

---

### 3. Solver Integrado de Viabilidade (Painel Único)

**O problema hoje**: para responder "Qual o preço mínimo?" o usuário vai ao Módulo 10 → Ferramentas → Solver Preço. Para "Qual o terreno máximo?" vai para outro tab. As ferramentas funcionam, mas ficam dispersas.

**O que implementar**: uma tela de "Calculadora de Negociação" com 4 perguntas em paralelo:
1. Preço mínimo por m² para TIR alvo
2. Custo máximo de obras para TIR alvo
3. Terreno máximo para TIR alvo
4. Velocidade mínima de vendas para TIR alvo

**Impacto**: as perguntas de negociação mais frequentes respondidas em uma única tela.

---

### 4. Importação de Tipologias via Planilha (CSV/Excel)

**O problema hoje**: para um projeto com 6-10 tipologias, preencher a tabela na interface uma a uma é trabalhoso e sujeito a erro.

**O que implementar**: botão "Importar planilha" na tela de tipologias. Formato esperado: nome, quantidade, área m², preço. O sistema valida e importa automaticamente.

**Impacto**: reduz em 80% o tempo de entrada de dados de projetos com muitas tipologias.

---

### 5. Exportação PDF Executivo (Relatório de Comitê)

**O problema hoje**: o botão "Exportar PDF" existe no sistema mas não está completamente conectado. O usuário precisa exportar o HTML e imprimir manualmente, ou formatar o Excel para apresentação.

**O que implementar**: gerar um PDF de 4-6 páginas com: capa (nome, data, foto), DRE resumida, KPIs, Curva de Caixa, Composição de Custos. Layout profissional, pronto para enviar a banco, sócio ou comitê.

**Impacto**: é o pedido mais frequente após calcular a viabilidade. Economiza horas de formatação.

---

### 6. Modo "Comparar com Cenário" em Tempo Real

**O problema hoje**: comparar "e se mudar o preço?" exige: alterar → calcular → anotar → desfazer → comparar. É feito mentalmente.

**O que implementar**: um botão "Fixar como base" que salva os KPIs atuais. Enquanto o usuário experimenta novas configurações, os KPIs mostram dois valores: base e atual (com delta verde/vermelho). Sem precisar navegar para o Módulo 11.

**Impacto**: torna a análise de sensibilidade instantânea e intuitiva.

---

## Prioridade Média — Segunda fase

Itens com alto valor estratégico, mas que demandam mais esforço de desenvolvimento.

---

### 7. Financiamento Bancário de Obras (CCB/CCI)

**O que é**: o usuário informa que vai financiar parte das obras via linha bancária. O sistema identifica os meses de caixa negativo, saca automaticamente da linha, aplica juros e amortiza quando o caixa volta ao positivo.

**Status atual**: o Módulo 13 já tem a interface e o modelo de dados (ConfigFinanciamento). O que falta é integrar o cálculo na engine (`fluxo_caixa.py`) para que o impacto apareça nos indicadores principais.

**Impacto**: a maioria dos loteamentos usa algum nível de financiamento de obras. Ignorar isso superestima a exposição máxima e distorce o VPL.

---

### 8. Reajuste Monetário Integrado ao Cálculo (INCC/IPCA)

**O que é**: aplicar correção por INCC nos custos de obras e por IPCA/INCC nas parcelas dos compradores.

**Status atual**: o Módulo 14 tem a interface e o modelo (ConfigReajustes). O que falta é integrar na engine para que os valores reajustados entrem no fluxo de caixa calculado.

**Impacto**: em projetos de 18-24 meses de obra, INCC de 6-8% a.a. pode aumentar o custo em 10-15%. Ignorar isso subestima saídas.

---

### 9. Lotes Especiais com Sobre-Preço

**O que é**: campo opcional por tipologia para cadastrar lotes especiais (esquinas, fundos de vale, próximos ao clube) com um percentual de ágio sobre o preço padrão. Ex.: "30 lotes de esquina com +20% sobre o preço da tipologia Padrão".

**Impacto**: evita criar tipologias separadas para variações de preço dentro do mesmo tipo de lote.

---

### 10. Tabela de Orçamento Detalhado de Obras

**O que é**: em vez de só "valor total por etapa", permitir detalhar o orçamento de cada etapa em itens (ex.: Terraplenagem → Corte 1.500 m³ × R$ 18,50/m³ + Aterro 800 m³ × R$ 22/m³). O sistema calcula o total e permite rastrear desvios de execução vs orçado.

**Impacto**: alinha o sistema com a forma como os engenheiros fazem orçamentos na prática.

---

### 11. Integração com SINAPI/SINAPE para Benchmark de Custos

**O que é**: consulta automática (ou base local atualizada) dos custos de referência do SINAPI/SINAPE para obras de infraestrutura urbana por estado. Mostra ao usuário "sua estimativa de custo está X% acima/abaixo da referência SINAPI para MG".

**Impacto**: bancos e órgãos públicos exigem compatibilidade com SINAPI. Ter esse benchmark integrado aumenta a credibilidade do orçamento.

---

### 12. Modelo de SPE/SCP

**O que é**: configuração do veículo jurídico do empreendimento (SPE, SCP, pessoa física, empresa individual de responsabilidade limitada). Cada estrutura tem tratamento tributário diferente que afeta o lucro líquido.

**Impacto**: para projetos acima de R$ 10 MM de VGV, a escolha do veículo jurídico pode representar diferença de 2-4 pontos percentuais na margem líquida.

---

### 13. Painel de Acompanhamento vs Orçado

**O que é**: campo de "realizado" para cada categoria de custo. O sistema mostra a comparação orçado vs realizado por mês, com indicadores de desvio e previsão de encerramento.

**Impacto**: transforma o sistema de uma ferramenta de viabilidade em uma ferramenta de controle de obra — ampliando muito o tempo de uso e o valor percebido.

---

## Prioridade Baixa — Versões futuras

Funcionalidades de nicho ou de alta complexidade de desenvolvimento.

---

### 14. Velocidade de Vendas Histórica por Região

**O que é**: base de dados com absorção histórica de loteamentos por município/UF. Sugere automaticamente a curva de vendas com base em dados reais do mercado local.

---

### 15. Crédito de Recebíveis (CRI/FIDC)

**O que é**: modela a cessão antecipada da carteira de recebíveis (financiamento pós-obra) com deságio. O incorporador cede os contratos de financiamento para um banco/fundo e recebe o principal antecipado, com desconto.

---

### 16. Regularização Fundiária (REURB)

**O que é**: fluxo específico para projetos de regularização fundiária (REURB-S e REURB-E), com custos e regimes tributários próprios, diferentes do loteamento convencional.

---

### 17. Calculadora de BDI Guiada (ABNT NBR 12721)

**O que é**: wizard interativo para calcular o BDI a partir dos componentes: administração central, seguro, risco, despesas financeiras, lucro, impostos sobre serviço — seguindo a metodologia da ABNT.

---

### 18. Régua de Aproveitamento Paramétrico

**O que é**: dados básicos de zoneamento municipal (cidade, zona) → o sistema sugere automaticamente o aproveitamento máximo permitido, recuos mínimos, lote mínimo e as destinações obrigatórias (verde, institucional, APP).

---

### 19. Versão Web (SaaS) com Autenticação de Usuários

**O que é**: hospedar o sistema em servidor web com login por usuário. Projetos ficam salvos na nuvem (banco de dados), acessíveis de qualquer dispositivo.

**Tecnologias sugeridas**: Streamlit Cloud / Render / Railway + PostgreSQL para persistência de dados. Autenticação via Google OAuth ou e-mail.

**Impacto estratégico**: permite monetização via assinatura mensal, escalando para múltiplos usuários simultaneamente.

---

### 20. App Mobile (Visualização)

**O que é**: versão mobile (React Native ou Flutter) que consome uma API REST do backend Python. Focada em leitura dos indicadores e aprovação de projetos, não em edição.

**Caso de uso**: sócio que quer ver rapidamente a TIR de um projeto no celular, sem precisar abrir o computador.

---

## Melhorias de Usabilidade (UX)

Refinamentos de interface que melhoram a experiência sem mudar a lógica de cálculo.

| # | Melhoria | Onde | Benefício |
|---|---|---|---|
| U1 | Entrada de áreas em hectares (toggle m²/ha/alq) | Módulo 1 | Elimina conversão manual |
| U2 | Mensagens de validação em português humanizado | Todos os módulos | Reduz confusão com erros técnicos |
| U3 | Botão "Duplicar Fluxo" nos fluxos de recebíveis | Módulo 2 | Economiza tempo ao criar variações |
| U4 | Seletor de período na tabela do fluxo | Módulo 7/8 | Facilita análise de fases específicas |
| U5 | Modo "por m² de gleba" no valor do terreno | Módulo 9 | Usa a unidade que o mercado negocia |
| U6 | Estimativa de custo de obras ao mudar o BDI (sem recalcular) | Módulo 3 | Feedback instantâneo ao ajustar parâmetros |
| U7 | Exportação dos gráficos como imagem (PNG/SVG) | Módulo 8 | Para incluir em apresentações PowerPoint |
| U8 | Tema claro (alternativa ao tema escuro) | Configuração | Preferência de alguns usuários |
| U9 | Onboarding guiado para novos usuários | Tela inicial | Reduz curva de aprendizado |
| U10 | Validação da área de tipologias vs área de lotes | Módulo 1 | Bug silencioso: tipologias podem exceder área disponível |

---

## Resumo Priorizado

| Prioridade | Item | Impacto | Esforço |
|---|---|---|---|
| 🔴 Alta | 1. Preço Progressivo por Fase | Muito alto | Médio |
| 🔴 Alta | 2. Histórico de Versões | Alto | Médio |
| 🔴 Alta | 3. Solver Integrado (Painel Único) | Alto | Baixo |
| 🔴 Alta | 4. Importação de Tipologias (CSV) | Médio | Baixo |
| 🔴 Alta | 5. Exportação PDF Executivo | Muito alto | Médio |
| 🔴 Alta | 6. Comparar com Cenário em Tempo Real | Alto | Médio |
| 🟡 Média | 7. Financiamento Bancário na Engine | Alto | Alto |
| 🟡 Média | 8. Reajuste Monetário na Engine | Alto | Alto |
| 🟡 Média | 9. Lotes Especiais com Ágio | Médio | Baixo |
| 🟡 Média | 10. Orçamento Detalhado de Obras | Alto | Alto |
| 🟡 Média | 11. SINAPI/SINAPE Benchmark | Médio | Alto |
| 🟡 Média | 12. Modelo de SPE/SCP | Médio | Médio |
| 🟡 Média | 13. Painel Orçado vs Realizado | Muito alto | Muito alto |
| 🟢 Baixa | 14-18. Funcionalidades de nicho | Variado | Alto/Muito alto |
| 🟢 Baixa | 19. Versão Web (SaaS) | Muito alto estratégico | Muito alto |
| 🟢 Baixa | 20. App Mobile | Alto | Muito alto |

---

## Notas sobre estratégia de produto

### Para o público-alvo atual (uso interno)
As prioridades altas (1-6) são as que mais impactam a produtividade de quem já usa o sistema. Recomenda-se implementar nessa ordem.

### Para distribuição como SaaS
Para transformar o sistema em produto para outros empreendedores, as prioridades mudam:
1. **Versão Web (item 19)**: é o pré-requisito para distribuição
2. **Exportação PDF (item 5)**: é o output mais solicitado em apresentações
3. **Onboarding guiado (U9)**: reduz o abandono de novos usuários
4. **Preço progressivo (item 1)**: diferencial competitivo vs ferramentas genéricas de viabilidade
5. **Painel orçado vs realizado (item 13)**: aumenta retenção (o usuário usa o sistema durante a execução, não só na viabilidade)

### Diferenciais competitivos do sistema
Comparado a planilhas Excel e outros sistemas de viabilidade no mercado brasileiro:
- **Separação receita nominal vs financeira**: cálculo correto de impostos sobre o principal (não sobre os juros)
- **Fluxo de recebíveis configurável**: suporta combinações de sinal + parcelas obra + balões + financiamento
- **Atalhos por intervalos**: entrada de curva de vendas e distribuição temporal muito mais ágil que tabela linha a linha
- **Engine pura testada**: 7 testes matemáticos automatizados garantem invariantes críticos (receita nominal = VGV exato)
- **Módulo 13 (Financiamento)** e **Módulo 14 (Reajustes)**: funcionalidades raras em ferramentas acessíveis ao pequeno incorporador

---

*Roadmap elaborado em 2026-05-22. Revisão recomendada a cada 3 meses conforme feedback dos usuários.*
