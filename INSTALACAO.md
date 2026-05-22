# Guia de Instalação — Windows

Este guia foi escrito para quem nunca programou. Siga os passos na ordem.

## Passo 1 — Instalar o Python

O Python é a linguagem em que o sistema foi feito. Ele precisa estar instalado no seu computador.

1. Acesse o site oficial: **https://www.python.org/downloads/**
2. Clique no botão grande amarelo **"Download Python 3.12.x"** (ou versão mais recente que aparecer)
3. Quando o instalador baixar, **abra-o**
4. **MUITO IMPORTANTE:** na primeira tela do instalador, marque a caixinha **"Add Python to PATH"** (fica embaixo, fácil de não ver)
5. Clique em **"Install Now"** e espere terminar
6. Clique em **"Close"** quando aparecer "Setup was successful"

### Verificar se instalou certo

1. Aperte a tecla **Windows** e digite `cmd`
2. Abra o **"Prompt de Comando"** (a janela preta)
3. Digite: `python --version` e aperte Enter
4. Deve aparecer algo como `Python 3.12.5`

Se aparecer **"python não é reconhecido"**, é porque você esqueceu de marcar "Add Python to PATH". Desinstale o Python pelo Painel de Controle e reinstale, marcando a caixinha desta vez.

## Passo 2 — Descompactar o sistema

1. Você recebeu um arquivo `viabilidade_loteamento.zip` (ou pasta)
2. Descompacte em um local fácil, por exemplo: **`C:\viabilidade_loteamento\`**
3. Dentro dela você verá: `README.md`, `rodar.py`, `requirements.txt`, pastas `src/`, `exemplos/`, etc.

## Passo 3 — Instalar as bibliotecas Python

O sistema usa algumas bibliotecas (pacotes prontos) que precisam ser instaladas uma única vez.

1. Abra o **Prompt de Comando** novamente
2. Navegue até a pasta do sistema. Se você descompactou em `C:\viabilidade_loteamento\`, digite:
   ```
   cd C:\viabilidade_loteamento
   ```
   e aperte Enter
3. Digite o comando abaixo e aperte Enter:
   ```
   pip install -r requirements.txt
   ```
4. Aguarde. Vão aparecer várias linhas baixando coisas. No final deve aparecer **"Successfully installed pydantic numpy pandas openpyxl..."**

Pronto. Você só precisa fazer isso uma vez.

## Passo 4 — Rodar o sistema pela primeira vez

Ainda no Prompt de Comando, na pasta do sistema, digite:

```
python rodar.py
```

Você verá no terminal:

```
============================================================
VIABILIDADE ECONOMICA DE LOTEAMENTO
============================================================
Carregando projeto: ...projeto_exemplo.json
Projeto: Loteamento Vila Verde
Cidade:  Belo Horizonte/MG
Lotes:   224
VGV:     R$ 49,300,000.00
...
RESUMO DO CALCULO
...
Resultado exportado para: ...projeto_exemplo_resultado.xlsx
```

Abra o Excel gerado em `exemplos/projeto_exemplo_resultado.xlsx`. Ele tem 4 abas:
- **Resumo:** quadro de áreas, tipologias, VGV, custos, indicadores
- **Fluxo de Caixa:** tabela mês a mês com todas as entradas e saídas
- **Indicadores:** VPL, TIR, payback, exposição
- **Simulação Lote:** o cronograma de pagamentos de 1 lote por tipologia

## Passo 5 — Adaptar para seu projeto

1. Faça uma cópia de `exemplos/projeto_exemplo.json` (clique direito → Copiar; cole na mesma pasta e renomeie, ex.: `meu_loteamento.json`)
2. Abra o arquivo no **Bloco de Notas** (clique direito → Abrir com → Bloco de Notas) ou em qualquer editor de texto
3. Altere os valores conforme seu projeto, prestando atenção em:
   - Datas no formato `"AAAA-MM-DD"` (ano-mês-dia)
   - Valores monetários como número puro: `12000000` para R$ 12.000.000,00 (use ponto, não vírgula, para decimais)
   - Percentuais como número direto: `6.73` significa 6,73%
   - Meses contados a partir de M0=0 (mês 0 é o início do projeto). Mês 12 = um ano depois, mês 24 = dois anos depois.
4. Salve o arquivo
5. Rode: `python rodar.py exemplos/meu_loteamento.json`

## Erros comuns

### "ModuleNotFoundError: No module named 'pydantic'"
Você não rodou o `pip install -r requirements.txt`. Volte ao Passo 3.

### "ERRO de validacao no projeto"
O sistema encontrou algum erro nos dados do JSON. A mensagem mostra exatamente qual campo. Os erros mais comuns:
- Soma das áreas não bate com a área da gleba (tolerância: 0,5%)
- Soma dos % do fluxo de recebíveis (sinal + obra + balões + financiamento) não dá 100%
- Soma dos % da curva de vendas não dá 100%
- Data de término de obras anterior ao início de obras

### "FileNotFoundError"
Você está rodando o comando em outra pasta. Use `cd C:\viabilidade_loteamento` antes de `python rodar.py`.

### Erro ao abrir o JSON no Bloco de Notas com formatação ruim
Use o **Notepad++** (gratuito, https://notepad-plus-plus.org/) ou o **VS Code** (gratuito, https://code.visualstudio.com/). Eles dão coloração de sintaxe e fica muito mais fácil editar.

## Validar a engine matemática (opcional)

Se quiser ter certeza de que os cálculos matemáticos estão corretos, rode:

```
python auto_teste.py
```

Ele faz 7 testes (sistema Price, curvas, NPV, TIR, etc.) e deve terminar com **"TODOS OS TESTES PASSARAM"**.
