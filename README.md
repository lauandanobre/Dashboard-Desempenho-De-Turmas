# TurmaMetrica

Aplicativo desktop para analisar desempenho de turmas a partir de planilhas de atividade do cursinho. O sistema importa os dados, valida informações, calcula indicadores e gera gráficos e relatórios em um fluxo simples e offline. Claro... sempre pode melhorar...

## Visão geral

O projeto foi pensado para ajudar na leitura e comparação de dados de turmas, com foco em:

- importação de planilhas em formatos comuns;
- validação de dados e identificação de inconsistências;
- cálculo de médias e indicadores por turma;
- geração de gráficos e relatórios;
- exportação de resultados sem depender da internet.

O formato mais comum esperado é algo como:

```text
turma; id; exatas (% de acertos); humanas (% de acertos)
```

Os nomes das colunas podem variar. O app sugere o mapeamento e você confirma na importação.
sim, isso é bem legal, tipo o excel.

## Funcionalidades principais

- Importação de dados em CSV, XLS, XLSX, ODS e TXT;
- validação de valores numéricos e tratamento de inconsistências;
- cálculo de médias gerais e por recorte;
- identificação de turmas com desempenho abaixo do esperado;
- geração de gráficos para análise visual;
- exportação de dados e relatórios;
- uso totalmente local, sem envio de dados para serviços externos.

## Requisitos

- Python 3.10 ou superior;
- ambiente virtual recomendado;
- dependências listadas em `requirements.txt` e `requirements-dev.txt`para quando precisarmos empacotar e criar um executável.

## Instalação

Clone o repositório:

```bash
git clone https://github.com/lauandanobre/TurmaMetrica.git
# em seguida entre na pasta criada com o comando:
cd TurmaMetrica
```

Crie e ative um ambiente virtual, se estiver no linux será python3, ok?, então:

```bash
python -m venv .venv
```
## Ative o ambiente criado:
Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instale as dependências, no linux será pip3:

```bash
pip install -r requirements-dev.txt
```

Execute a aplicação:

```bash
python main.py
```

## Dados de exemplo

Há uma planilha fictícia em `assets/exemplo_ficticio.csv` para testes rápidos.

Também é possível gerar dados fictícios com:

```bash
python scripts/gerar_dados_ficticios.py
```

## Estrutura do projeto

```text
main.py
README.md
requirements.txt
requirements-dev.txt
assets/
  exemplo_ficticio.csv
scripts/
  gerar_dados_ficticios.py
src/
  __init__.py
  charts/
  models/
  services/
  ui/
  utils/
```

### Organização principal

- `main.py`: ponto de entrada da aplicação;
- `src/models/`: estruturas e dados compartilhados;
- `src/services/import_service.py`: leitura e importação de arquivos;
- `src/services/validation_service.py`: validação e qualidade dos dados;
- `src/services/analysis_service.py`: cálculos e indicadores;
- `src/services/export_service.py`: exportação de dados e relatórios;
- `src/charts/`: geração de gráficos;
- `src/ui/`: interface da aplicação;
- `src/utils/`: utilidades gerais.

## Fluxo da aplicação

O fluxo principal é:

```text
arquivo -> importação -> validação -> limpeza -> análise -> gráficos/relatórios -> exportação
```

Em termos de módulos:

```text
read_table -> ImportDialog -> build_clean_dataset -> Session -> UI
```

A interface chama os serviços, e os serviços ficam responsáveis pela lógica de dados e análise.

## Regras de negócio e validação

O sistema considera alguns critérios importantes ao processar os dados:

- valores numéricos aceitos podem vir em diferentes formatos, como `75`, `75.5`, `75,5`, `75,5%` e `1.234,5`;
- textos e valores ambíguos são ignorados e listados para revisão;
- o intervalo padrão aceito é de 0 a 100, mas pode ser ajustado ou desativado na importação;
- linhas sem turma são descartadas com aviso;
- células vazias não entram na média;
- IDs repetidos podem ser mantidos com aviso ou removidos conforme configuração;
- nomes de turmas que diferem apenas por maiúsculas/minúsculas não são unidos automaticamente;
- a média geral é calculada sobre todos os valores válidos do recorte, não sobre médias parciais;
- turmas em atenção são sinalizadas com base em critérios configuráveis.

## Divisão de tarefas

A organização do projeto pode ser separada por área de responsabilidade:

### 1. Coordenação e integração

Responsável por:

- arquitetura geral do projeto;
- definição de regras de negócio;
- integração entre módulos;
- manutenção da documentação e do fluxo principal.

Arquivos principais:

- `src/models/`
- `main.py`
- `src/ui/main_window.py`
- `README.md`

### 2. Importação e validação

Responsável por:

- leitura de arquivos;
- mapeamento de colunas;
- limpeza dos dados;
- validação de qualidade e inconsistências.

Arquivos principais:

- `src/services/import_service.py`
- `src/services/validation_service.py`

### 3. Análise

Responsável por:

- cálculo de médias;
- filtros por turma ou critério;
- indicadores de desempenho;
- comparação entre grupos.

Arquivos principais:

- `src/services/analysis_service.py`

### 4. Interface do usuário

Responsável por:

- telas e navegação;
- visualização de dados;
- relatórios e diálogos;
- interação com o usuário.

Arquivos principais:

- `src/ui/`

### 5. Gráficos e exportação

Responsável por:

- geração de visualizações;
- criação de relatórios;
- exportação para formatos prontos para uso.

Arquivos principais:

- `src/charts/`
- `src/services/export_service.py`
- `installer/`

## Privacidade e segurança

- os dados ficam localmente no computador;
- logs não incluem nomes de alunos ou notas;
- gráficos usam pasta temporária e são limpos ao encerrar a aplicação;
- fórmulas e macros da planilha não são executadas;
- exportações evitam valores com risco de comando, como células iniciadas por `=`, `+`, `-` ou `@`;
- relatórios em PDF não expõem IDs de alunos.

## Empacotamento

Para empacotar a aplicação em um executável futuro, pode ser usado o PyInstaller, lembre-se de baixa a dependencia no arquivo requiremnts-dev.txt, ok?, pois bem:

```bash
pyinstaller --noconsole --name "Métricas das Turmas" main.py
```

A estrutura também pode evoluir para um instalador local em `installer/` com solução como Inno Setup. Assim qualquer um pode baixar o app final em seu pc e usar como quiser. Um icone para o aplicativo é bem vindo.

## Pendências e pontos em revisão

Algumas questões ainda precisam ser confirmadas para fechar regras de negócio:

1. o cabeçalho da planilha está sempre na primeira linha?
2. qual a regra exata para classificar uma turma como "em atenção"?
3. cada linha representa um aluno ou uma avaliação?
4. a planilha real terá período/avaliação ou apenas disciplinas em colunas?
5. existe limite mínimo de registros para uma turma ser considerada confiável?
6. o app precisa de ícone e identidade visual definidos em `assets/`?
7. exportação de gráficos em PNG precisa ser validada em diferentes sistemas operacionais.

## Contribuição

Para colaborar com o projeto, mantenha a organização por responsabilidade, documente mudanças relevantes e preserve o fluxo principal da aplicação.