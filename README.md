<div align="center">

# 📊 Métricas das Turmas

**Painel offline e gratuito para acompanhar o desempenho das turmas do cursinho em cada simulado.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/Interface-PySide6-41CD52?logo=qt&logoColor=white)
![Gráficos](https://img.shields.io/badge/Gráficos-Plotly-3F4F75?logo=plotly&logoColor=white)
![Testes](https://img.shields.io/badge/testes-17%20passando-brightgreen)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)
![Offline](https://img.shields.io/badge/100%25-offline-informational)

Projeto de extensão desenvolvido para o **cursinho popular da UFABC**.

[Como baixar e usar](#-guia-rápido-para-professores) ·
[Como preparar a planilha](#-como-preparar-a-planilha) ·
[Como ler os gráficos](#-como-ler-os-resultados) ·
[Para desenvolvedores](#-para-desenvolvedores)

</div>

---

## Sumário

1. [Sobre o projeto](#-sobre-o-projeto)
2. [Funcionalidades](#-funcionalidades)
3. [Guia rápido para professores](#-guia-rápido-para-professores)
4. [Como preparar a planilha](#-como-preparar-a-planilha)
5. [Como ler os resultados](#-como-ler-os-resultados)
6. [Problemas comuns](#-problemas-comuns)
7. [Para desenvolvedores](#-para-desenvolvedores)
8. [Regras de negócio](#-regras-de-negócio)
9. [Privacidade e segurança](#-privacidade-e-segurança)
10. [Equipe](#-equipe)
11. [Limitações e próximos passos](#-limitações-e-próximos-passos)
12. [Licença](#-licença)

---

## 🎯 Sobre o projeto

Depois de cada simulado, o sistema de correção entrega uma planilha com uma linha por aluno. Ler essa planilha à mão para responder perguntas como *"qual turma foi pior em Humanas?"* ou *"quais questões a turma mais errou?"* é lento e sujeito a erro.

O **Métricas das Turmas** lê a planilha, confere os dados e mostra o desempenho de cada turma em gráficos, tudo **no próprio computador, sem internet e sem custo**.

**O que o diferencia de uma planilha com gráficos:**

- **Aluno ausente não vira nota zero.** Nos dados reais do primeiro teste, 41% das linhas eram de ausentes: contá-los como 0% derrubava a média geral de 58% para 34%. O programa separa presença de desempenho.
- **Não acusa turma por acaso.** Turmas pequenas oscilam muito. A sinalização de "atenção" exige amostra mínima e diferença maior que a margem de erro.
- **Avisa quando a planilha tem problema** (lista de erros cortada, percentual inconsistente, cartão suspeito, possível erro de gabarito) em vez de calcular em silêncio.

<!-- Depois de tirar as capturas de tela, coloque os arquivos em docs/img/ e descomente:
![Painel principal](docs/img/dashboard.png)
![Questões mais erradas](docs/img/questoes.png)
-->

---

## ✨ Funcionalidades

| Área | O que faz |
|---|---|
| **Importação** | Lê `.xlsx`, `.xls`, `.ods`, `.csv` e `.txt`. Reconhece sozinho o layout do sistema de correção e o modelo do projeto. Qualquer outra planilha funciona por mapeamento manual de colunas. |
| **Painel** | Médias por turma (com margem de erro de 95%), distribuição das notas, dispersão (boxplot), comparação Linguagens × Humanas, evolução entre simulados, **presença** por turma e **questões mais erradas**. Filtros por turma, área e simulado. |
| **Alertas** | Alunos para conferir o cartão-resposta, questões com taxa de erro muito alta, problemas de qualidade da importação. |
| **Turmas em atenção** | Critério configurável (pontos abaixo da média geral e/ou média mínima), com amostra mínima e teste de margem de erro. O motivo de cada sinalização é sempre explicado. |
| **Exportação** | Dados tratados, resumo por turma (`.xlsx`/`.csv`), **relatório em PDF** (sem IDs de alunos) e a planilha convertida para o padrão do projeto. |
| **Padronização** | Converte qualquer exportação do sistema para uma planilha limpa, com fórmulas e validação de dados. |

---

## 🚀 Guia rápido para professores

> Você só precisa fazer a **instalação uma vez**. Depois, é abrir o programa e importar a planilha.

### Passo 1 — Instalar o Python (uma vez)

1. Acesse [python.org/downloads](https://www.python.org/downloads/) e baixe o **Python 3.12** (ou mais novo; precisa ser 3.10 ou superior).
2. Abra o instalador e, **na primeira tela, marque a caixa “Add Python to PATH”**. Depois clique em *Install Now*.

### Passo 2 — Baixar o programa

1. Abra a página do projeto no GitHub: <https://github.com/lauandanobre/Dashboard-Desempenho-De-Turmas>
2. Clique no botão verde **Code → Download ZIP**.
3. Extraia o ZIP (clique com o botão direito → *Extrair tudo*) em uma pasta fácil de achar, como `C:\Metricas-Turmas`.

### Passo 3 — Instalar as bibliotecas (uma vez)

1. Abra a pasta extraída até ver o arquivo `main.py`.
2. Clique na barra de endereço da pasta, digite `powershell` e aperte **Enter**. Abre uma janela azul/preta.
3. Cole os comandos abaixo, **um de cada vez**, apertando Enter (o segundo e o terceiro demoram alguns minutos):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Passo 4 — Abrir o programa (sempre que for usar)

Na mesma pasta, abra o PowerShell e rode:

```powershell
.venv\Scripts\activate
python main.py
```

A janela do programa abre. Para **testar sem dados reais**, clique em **Importar planilha** e escolha `assets\exemplo_ficticio.xlsx`.

### Passo 5 — Usar com a planilha do simulado

1. No sistema de correção (Google Sheets), vá em **Arquivo → Fazer download → Microsoft Excel (.xlsx)**.
   **⚠ Nunca baixe em PDF:** o PDF corta a coluna “Questões Erradas” e a análise por questão fica errada.
2. No programa, clique em **Importar planilha** e escolha o arquivo.
3. O programa mostra o que reconheceu e o que corrigiu. Confira o resumo e confirme.
4. Navegue pelas abas **Dashboard**, **Dados**, **Alertas** e **Relatórios**.
5. Em **Relatórios**, gere o **PDF** para compartilhar com a coordenação.

> 💡 **Dica:** a pasta já traz o arquivo `abrir.bat`. Depois da instalação, basta dar **dois cliques nele** para abrir o programa (sem digitar comandos).

---

## 📋 Como preparar a planilha

Existem **três jeitos** de os dados entrarem no programa:

```mermaid
flowchart LR
    A[Sistema de correção<br/>Google Sheets] -->|Download .xlsx<br/>nunca PDF| B[Importar no app]
    C[Digitação manual<br/>modelo_planilha_turmas.xlsx] --> B
    D[Outra planilha<br/>colunas diferentes] -->|mapeamento manual| B
    B --> E[Padronização<br/>e validação]
    E --> F[Painel · Alertas · Relatório PDF]
```

### 1. Exportação do sistema de correção (o caminho normal)

O programa reconhece sozinho as colunas `ID, TURMA, Respostas, Acertos, Percentual, %Linguagens, %Humanas, Questões Erradas`. Em *Questões Erradas*, `Q12(B/C)` significa: na questão 12 o aluno marcou **B** e a correta era **C**.

### 2. Modelo do projeto (para digitar ou arquivar)

Use `assets/modelo_planilha_turmas.xlsx`. Na aba **Alunos**, só as colunas em **azul** são digitadas; as **cinzas** são fórmulas.

| Coluna | Digitar? | Regra |
|---|:---:|---|
| `turma` | ✅ | Código sempre igual (`T1NOTSA`, `VESPSBC`…) |
| `id_aluno` | ✅ | Único na turma + simulado. **Sem nome** (LGPD) |
| `simulado` | ✅ | Ex.: `S2D1`. Permite comparar simulados |
| `presente` | ✅ | `SIM` ou `NAO` |
| `respostas` | ✅ | Quantas questões o aluno marcou (0–90) |
| `acertos_linguagens` | ✅ | Inteiro de 0 a 45. **Em branco se ausente** |
| `acertos_humanas` | ✅ | Inteiro de 0 a 45. **Em branco se ausente** |
| `acertos_total`, `pct_linguagens`, `pct_humanas`, `pct_total` | ❌ | Fórmulas (0 a 100, sem `%`) |
| `observacao` | opcional | Texto livre |

Outras abas: **Gabarito** (letra correta de cada questão), **Config** (nº de questões por área) e **Erros** (opcional: uma linha por questão errada).

### Regras de ouro

1. **Ausente = `presente: NAO` e notas em branco. Nunca digite 0.**
2. **Nunca use PDF** como fonte de dados.
3. Notas são números de 0 a 100 **sem o símbolo `%`**.
4. Escreva o código da turma **sempre igual** em todos os arquivos.
5. Um arquivo por simulado, nomeado `AAAA-MM_simulado_S#D#.xlsx` (ex.: `2026-10_simulado_S2D1.xlsx`).
6. Sem células mescladas, linhas em branco no meio ou totais no rodapé.

Para converter uma exportação do sistema para o padrão: no programa, **Relatórios → Exportar no padrão da planilha**, ou pelo terminal:

```bash
python scripts/converter_planilha.py entrada.xlsx saida.xlsx
```

---

## 📈 Como ler os resultados

| Gráfico | Para que serve | Como interpretar |
|---|---|---|
| **Médias por turma** | Comparar turmas | A barra é a média. O “bigode” é a margem de erro de 95%: **se os bigodes de duas turmas se sobrepõem, a diferença pode ser só acaso.** |
| **Distribuição** | Ver como as notas se espalham | Pico à esquerda = muitos alunos com nota baixa. |
| **Dispersão (boxplot)** | Ver variação dentro da turma | A caixa guarda os 50% do meio. Caixa larga = turma desigual. |
| **Comparação por área** | Linguagens × Humanas | Mostra em qual área cada turma está mais fraca. |
| **Evolução** | Acompanhar simulados | Só aparece com 2 ou mais simulados. |
| **Presença** | Ver quem compareceu | Presentes × ausentes por turma. |
| **Questões mais erradas** | Rever conteúdo e gabarito | Passe o mouse para ver o gabarito e a alternativa errada mais marcada. Erro muito alto pode ser questão difícil **ou erro de gabarito**. |

### Aba Alertas

Pontos para **conferir antes de tirar conclusões**. Não são julgamentos sobre alunos ou turmas.

| Alerta | Quando aparece |
|---|---|
| Abaixo do acaso | Respondeu ≥ 60% da prova e acertou < 20% (chutar em 5 alternativas daria ~20%). Confira o cartão ou a versão da prova. |
| Mesma alternativa em excesso | ≥ 60% dos erros na mesma letra (o normal é 25–35%). |
| Sequência | 6 ou mais erros seguidos na mesma letra. |
| Percentual inconsistente | O percentual do sistema não bate com os acertos. O programa recalcula e avisa. |
| Questão com erro alto | 70% ou mais dos alunos erraram. Vale revisar gabarito ou anulação. |
| Lista de erros incompleta | Típico de PDF. Esses alunos ficam fora do ranking de questões. |

---

## 🛠 Problemas comuns

| Sintoma | Solução |
|---|---|
| `python` não é reconhecido | Reinstale o Python marcando **“Add Python to PATH”**, ou use `py` no lugar de `python`. |
| Erro de “execução de scripts desabilitada” ao ativar o ambiente | No PowerShell, rode uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e responda `S`. |
| `ModuleNotFoundError: PySide6` (ou pandas) | O ambiente não está ativo. Rode `.venv\Scripts\activate` e confirme que aparece `(.venv)` no começo da linha. |
| Erro de sintaxe com `\|` ao abrir | Python antigo. Confira com `python --version`: precisa ser **3.10 ou superior**. |
| A janela não aparece | Olhe a barra de tarefas: ela pode abrir atrás de outras janelas. |
| “Arquivo em uso” ao exportar | Feche o arquivo no Excel e exporte de novo. |
| “Layout não reconhecido” / “Faltam colunas” | Use o modelo `assets/modelo_planilha_turmas.xlsx` ou o mapeamento manual de colunas na importação. |
| Médias parecem baixas demais | Confira se ausentes estão com notas em **branco** (não 0) e se há coluna de presença. |

---

## 👩‍💻 Para desenvolvedores

### Instalação

```bash
git clone https://github.com/lauandanobre/Dashboard-Desempenho-De-Turmas.git
cd Dashboard-Desempenho-De-Turmas

python -m venv .venv                 # Linux/macOS: python3 -m venv .venv
.venv\Scripts\activate               # Windows
source .venv/bin/activate            # Linux/macOS

pip install -r requirements-dev.txt  # inclui pytest e pyinstaller
python main.py
```

Para rodar os testes: `python -m pytest -q` (esperado: **17 passed**). Os testes usam apenas dados **fictícios** gerados em código.

No VS Code: instale a extensão **Python**, use `Ctrl+Shift+P → Python: Select Interpreter` e escolha o `.venv`.

### Tecnologias

| Biblioteca | Papel no projeto |
|---|---|
| `PySide6` | Interface gráfica (janelas, abas, botões e diálogos). |
| `pandas` | Leitura, limpeza, validação e cálculo das médias. |
| `plotly` | Gráficos interativos (barras, histograma, boxplot, evolução). |
| `openpyxl` | Leitura e geração de `.xlsx` (inclui o modelo com fórmulas). |
| `xlrd` | Leitura de `.xls` antigos. |
| `odfpy` | Leitura de `.ods` (LibreOffice). |
| `pytest` | Testes automatizados. |
| `pyinstaller` | Empacotar em executável (futuro). |

Tudo é gratuito: PySide6 (LGPL), pandas e openpyxl (BSD/MIT), Plotly (MIT).

### Arquitetura

```mermaid
flowchart LR
    A[Arquivo] --> B[import_service<br/>lê a tabela]
    B --> C[ingest_service<br/>reconhece e padroniza]
    C --> D[Dataset<br/>padrão do projeto]
    D --> E[validation_service<br/>limpeza e qualidade]
    E --> F[analysis_service · item_service<br/>médias, presença, questões, alertas]
    F --> G[chart_builder<br/>gráficos]
    F --> H[export_service<br/>xlsx · csv · PDF]
    G --> I[Interface PySide6]
    H --> I
```

A interface chama os serviços; os serviços ficam responsáveis pela lógica de dados e não dependem de Qt (por isso são testáveis).

### Estrutura de pastas

```text
main.py                         ponto de entrada
abrir.bat                       atalho para abrir o programa no Windows
assets/                         modelo_planilha_turmas.xlsx, exemplo_ficticio.(csv|xlsx)
scripts/                        gerar_modelo.py, gerar_dados_ficticios.py, converter_planilha.py
installer/                      (futuro) instalador local
src/
  models/                       dataset, session, resultados e configurações
  services/
    schema.py                   definição do padrão de planilha (fonte única de verdade)
    import_service.py           leitura de arquivos (csv, xlsx, xls, ods, txt)
    ingest_service.py           reconhece layout e converte para o padrão
    validation_service.py       mapeamento de colunas, limpeza e qualidade
    analysis_service.py         médias, filtros, presença, turmas em atenção
    item_service.py             gabarito, ranking de questões e alertas
    export_service.py           exportação de dados, resumo e PDF
    standard_workbook.py        gera o modelo e a planilha padronizada
    demo_data.py                dados fictícios para exemplos e testes
  charts/                       gráficos Plotly
  ui/                           dashboard, dados, alertas, relatórios, diálogos
  utils/                        caminhos, log e utilidades
tests/                          pytest
```

### Fluxo da aplicação

```text
arquivo → import_service → ingest_service → ImportDialog → build_clean_dataset → Session → UI
```

### Comandos úteis

```bash
python scripts/gerar_modelo.py              # recria assets/modelo_planilha_turmas.xlsx
python scripts/gerar_dados_ficticios.py     # recria os exemplos fictícios
python scripts/converter_planilha.py in.xlsx out.xlsx
python -m pytest -q                         # testes
```

### Empacotamento (futuro)

Para gerar um executável que roda sem Python instalado:

```bash
pyinstaller --noconsole --name "Métricas das Turmas" main.py
```

A pasta `installer/` é reservada para um instalador local (por exemplo, com Inno Setup). Se existir `assets/icon.ico`, a janela o usa como ícone.

### Como contribuir

1. Crie uma branch por tarefa: `git checkout -b feature/nome-da-tarefa`.
2. Rode `python -m pytest -q` antes de abrir o *pull request*.
3. **Nunca versione dados reais de alunos.** O `.gitignore` já bloqueia `dados_reais/`, PDFs e `.xlsx` fora de `assets/`.
4. Mantenha a lógica de dados em `src/services/` e a interface em `src/ui/`.
5. Documente mudanças relevantes neste README.

---

## 📐 Regras de negócio

- **Formatos numéricos aceitos:** `75`, `75.5`, `75,5`, `75,5%` e `1.234,5`. Textos ambíguos são ignorados e listados para revisão.
- **Intervalo válido:** 0 a 100 (ajustável ou desativável na importação).
- **Ausentes:** não entram em nenhuma média. Vêm de `presente = NAO`, de `Respostas = 0` (layout do sistema) ou, em planilhas sem coluna de presença, da opção “tratar notas 0 como ausente”.
- **Linhas sem turma** são descartadas com aviso. **Células vazias** não entram na média.
- **IDs repetidos** podem ser mantidos com aviso ou removidos.
- **Turmas com nomes diferentes só por maiúsculas/minúsculas** não são unidas automaticamente.
- **Média geral** = média de todos os valores válidos do recorte (não é média de médias).
- **Turma em atenção:** média abaixo da geral da mesma área por X pontos (padrão: 5) e/ou abaixo de um mínimo absoluto. Exige no mínimo 10 registros e que a diferença supere a margem de erro de 95% (`±1,96 × erro padrão`).
- **Ranking de questões:** usa apenas alunos presentes com lista de erros completa (`respostas − acertos` = erros listados). O gabarito é deduzido dos pares *marcada/correta* quando a aba Gabarito está vazia.
- **Prova:** 90 questões, sendo Q1–Q45 Linguagens e Q46–Q90 Humanas (ajustável na aba `Config`).

---

## 🔒 Privacidade e segurança

- Tudo roda **localmente**. Nenhum dado é enviado a serviços externos.
- Os logs não gravam nomes, notas nem conteúdo das planilhas.
- Gráficos usam pasta temporária, limpa ao fechar o programa.
- Fórmulas e macros das planilhas **não são executadas**.
- Exportações neutralizam células que começam com `=`, `+`, `-` ou `@` (injeção de fórmulas).
- O relatório em PDF **não mostra IDs de alunos**. Apenas a aba Alertas (na tela) lista IDs.
- A planilha usa **ID numérico, sem nome** (LGPD). Mantenha dados reais fora do repositório.

---

## 👥 Equipe

| Nome | Responsabilidade |
|---|---|
| **[Nome 1]** | Coordenação, arquitetura e integração (`src/models/`, `main.py`, `src/ui/main_window.py`) |
| **[Nome 2]** | Importação e validação (`import_service`, `ingest_service`, `validation_service`) |
| **[Nome 3]** | Análise de dados (`analysis_service`, `item_service`) |
| **[Nome 4]** | Interface do usuário (`src/ui/`) |
| **[Nome 5]** | Gráficos, exportação e empacotamento (`src/charts/`, `export_service`, `installer/`) |

**Orientação / cursinho:** [nome do(a) professor(a) ou coordenação] · **Instituição:** Universidade Federal do ABC (UFABC)

> ✏️ Substitua os campos entre colchetes pelos nomes e papéis reais do grupo.

---

## 🧭 Limitações e próximos passos

**Limitações conhecidas**

- O ranking de questões depende de a planilha trazer a lista completa de erros. Em PDF ela vem cortada.
- Como a planilha lista só as questões **erradas**, questões em branco e acertos não são distinguíveis em alunos que não responderam tudo.
- Com poucos alunos por turma (< 10), o programa não avalia a turma de propósito.
- O significado dos códigos de turma (`T1NOTSA` etc.) e do rótulo `S2D1` do simulado vem do nome dos arquivos; confirme com a coordenação.

**Próximos passos**

- [ ] Executável com instalador (PyInstaller + Inno Setup), para não exigir Python.
- [ ] Ícone e identidade visual do cursinho em `assets/`.
- [ ] Capturas de tela na seção de apresentação (`docs/img/`).
- [ ] Validar exportação de gráficos em PNG no macOS e no Linux.
- [ ] Integração contínua (GitHub Actions) rodando os testes a cada *push*.

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo [`LICENSE`](LICENSE).
