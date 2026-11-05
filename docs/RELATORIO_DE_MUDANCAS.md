# Relatório de mudanças — Métricas das Turmas

Projeto do cursinho popular da UFABC · versão original → versão atual · 29/10/2026

## 1. Resumo

A versão original já tinha uma base sólida (serviços separados da interface, importação robusta, privacidade). Ao testá-la com os **dados reais de um simulado** (243 alunos, 5 turmas), encontramos problemas que distorciam os resultados. A versão atual corrige esses problemas, adiciona análise por questão e alertas, padroniza a planilha, reescreve a documentação e inclui testes automatizados.

Em números: **36 arquivos alterados (incluindo este relatório) · +2.212 linhas · −434 linhas · 17 testes automatizados (antes: 0) · 2 novos gráficos (de 5 para 7)**.

## 2. O que descobrimos com os dados reais

| Achado | Impacto | Como ficou |
|---|---|---|
| 100 de 243 alunos (41%) eram **ausentes** e apareciam como 0% | A média geral caía de **58,1%** para **34,2%**. A turma VESPSBC ia de 58,5% para 29,9%. | Ausente fica em branco e fora das médias. Presença virou gráfico próprio. |
| O app sugeria `Respostas` e `Acertos` como colunas de nota | Valores como 69 ou 90 passam no filtro de 0–100 e entravam como se fossem porcentagem. | Contagens não são mais sugeridas como nota. |
| O **PDF corta** a coluna "Questões Erradas" (em 39 erros) | 46 dos 143 alunos presentes tinham a lista incompleta; as últimas questões pareciam "fáceis". | Detectado automaticamente e esses alunos saem do ranking de questões. Aviso para exportar em `.xlsx`. |
| Percentual do sistema inconsistente (IDs 209 e 240) | O sistema usou o nº de respostas, e não 90, como denominador. Os dois ainda ficaram abaixo do acaso (~15%). | Recalculado, anotado em `observacao` e listado em Alertas. |
| Planilha real é **Linguagens + Humanas** | O README e os exemplos falavam em "exatas". | Código, exemplos e documentação atualizados. |
| Q89 (87% de erro) e Q18 (78%) no topo do ranking | Podem ser questões difíceis ou **erro de gabarito**. | Aparecem em Alertas para a coordenação conferir. |
| Aluno 220 com 68% dos erros na letra C | Possível cartão preenchido sem leitura. | Alerta de "mesma alternativa em excesso". |
| T2VESPSA parecia pior em Humanas (−6,8 pontos) | Com ~26 presentes, a diferença está **dentro da margem de erro**. | Não é mais sinalizada como "atenção" por acaso. |

## 3. Antes × depois

| Aspecto | Versão original | Versão atual |
|---|---|---|
| Layouts aceitos | Qualquer tabela, com mapeamento manual | Reconhece sozinho o **layout do sistema de correção** e o **modelo do projeto**; mapeamento manual continua valendo para qualquer outra planilha |
| Ausentes | Contavam como nota 0 | Fora das médias; coluna `presente`; opção "tratar 0 como ausente" para planilhas genéricas |
| Áreas | Exatas / Humanas | Linguagens (Q1–45) / Humanas (Q46–90), configurável |
| Análise por questão | Inexistente | Ranking de questões, gabarito deduzido, alternativa errada mais marcada |
| Alertas | Apenas qualidade da importação | Nova aba **Alertas**: abaixo do acaso, mesma letra, percentual inconsistente, lista incompleta, questão com erro alto |
| Turma em atenção | Só diferença de pontos | + amostra mínima (10) + margem de erro de 95%; sempre explica o motivo |
| Gráficos | 5 | **7** (novos: Presença e Questões mais erradas); barras de erro de 95% nas médias |
| Exportação | Dados, resumo e PDF | + planilha **convertida para o padrão**; PDF com presença e questões difíceis (sem IDs) |
| Planilha | Sem padrão definido | **Modelo oficial** com fórmulas, validação de dados e aba LEIA-ME |
| Testes | Nenhum (o README citava pytest) | 17 testes, só com dados fictícios |
| Exemplos | CSV fictício "exatas/humanas" | CSV e XLSX fictícios no layout real, reproduzíveis |
| Documentação | README vago, com anotações informais | README completo: guia para professores, planilha, gráficos, problemas comuns, desenvolvedores |
| Licença / ícone | Sem LICENSE; ícone citado mas não usado | LICENSE (MIT); janela usa `assets/icon.ico` se existir |
| Atalhos | — | `abrir.bat` (Windows) e `.vscode/launch.json` (F5 no VS Code) |

**Mantido da versão original:** a arquitetura (serviços sem Qt), a importação tolerante (formatos numéricos, separadores, codificações), a proteção contra injeção de fórmulas, os logs sem dados pessoais, o PDF sem IDs e o uso 100% offline.

## 4. Mudanças por arquivo

**Novos (18 arquivos)**

| Arquivo | Função |
|---|---|
| `src/services/schema.py` | Define o padrão de planilha (fonte única de verdade) |
| `src/services/ingest_service.py` | Reconhece o layout e converte para o padrão; regras de ausência e consistência |
| `src/services/item_service.py` | Gabarito, ranking de questões, completude da lista de erros e alertas |
| `src/services/standard_workbook.py` | Gera o modelo e a planilha padronizada (fórmulas e validação) |
| `src/services/demo_data.py` | Dados fictícios reproduzíveis para exemplos e testes |
| `src/models/dataset.py` | Estrutura dos dados já padronizados |
| `src/ui/alerts_view.py` | Tela de Alertas |
| `scripts/converter_planilha.py`, `scripts/gerar_modelo.py` | Linha de comando: converter e gerar o modelo |
| `tests/` (3 arquivos) | 17 testes automatizados |
| `LICENSE`, `abrir.bat`, `.vscode/launch.json` | Licença MIT e atalhos |
| `assets/modelo_planilha_turmas.xlsx`, `assets/exemplo_ficticio.xlsx` | Modelo e exemplo |

**Alterados (16 arquivos)**

| Arquivo | O que mudou |
|---|---|
| `validation_service.py` | Presença, "0 = ausente", nomes de área amigáveis, sugestão de colunas corrigida |
| `analysis_service.py` | Erro padrão, regra de atenção com amostra mínima e significância, tabela de presença |
| `chart_builder.py` | Barras de erro; gráficos de presença e de questões |
| `export_service.py` | PDF com presença e questões difíceis |
| `analysis_result.py`, `session.py` | Novos campos de configuração e o `Dataset` na sessão |
| `dashboard.py`, `dialogs.py`, `main_window.py`, `reports.py` | Novas abas, coluna de presença, página Alertas, controles de amostra mínima e botão "Exportar no padrão" |
| `main.py` | Ícone da janela |
| `README.md`, `assets/README.md`, `.gitignore`, `gerar_dados_ficticios.py`, `exemplo_ficticio.csv` | Documentação, ignorar dados reais, exemplos no layout real |

**Removido (1):** `src/ui/reports_view.py`, código antigo que não era usado por nenhuma tela.

## 5. Como a planilha deve ser

```
Sistema de correção → Google Sheets → Arquivo > Fazer download > .xlsx → Importar no app
                                              (nunca PDF)
```

Regras: ausente = `presente: NAO` com notas **em branco** (nunca 0); notas de 0 a 100 **sem o símbolo %**; código de turma sempre igual; um arquivo por simulado (`AAAA-MM_simulado_S#D#.xlsx`). O modelo está em `assets/modelo_planilha_turmas.xlsx`; o detalhamento está no README.

## 6. Como usar

**Instalação (uma vez, Windows)**

1. Instale o Python 3.10 ou mais novo (recomendado 3.12) em python.org, marcando **"Add Python to PATH"**.
2. Baixe o projeto (GitHub → **Code → Download ZIP**) e extraia.
3. Na pasta com o `main.py`, abra o PowerShell e rode:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Uso diário**

1. Dê dois cliques em `abrir.bat` (ou rode `python main.py`).
2. **Importar planilha** → escolha o `.xlsx` do simulado (para testar: `assets/exemplo_ficticio.xlsx`).
3. Confira o resumo da importação e confirme.
4. Use as abas **Dashboard**, **Dados**, **Alertas** e **Relatórios** (PDF para a coordenação).

**Desenvolvimento (VS Code):** instale a extensão Python, escolha o interpretador `.venv` e rode `python -m pytest -q` (esperado: 17 passed). F5 abre o app.

## 7. Como foi verificado — e o que não foi

**Verificado**

- 17 testes automatizados passando (dados fictícios).
- Importação e análise com os dados reais (convertidos do PDF) nos formatos de texto e fração; os totais batem com o PDF original.
- A janela foi aberta em modo automático (sem tela), importando os exemplos fictícios e a planilha real convertida; abas, KPIs, gráficos e PDF foram gerados sem erro.
- Leitura e escrita da planilha padrão (ida e volta) sem perda de dados.

**Não verificado — pedimos ajuda ao grupo**

- Execução completa em **Windows** (a instalação foi iniciada, mas o resultado final precisa ser confirmado por vocês).
- **macOS e Linux** com tela real.
- Aparência visual das telas (alinhamento, fontes, cores) e do PDF.
- Atenção à versão do Python: o log de instalação mostrou pacotes `cp39`, o que indica **Python 3.9**. O projeto pede 3.10 ou superior.

## 8. Decisões para o grupo aprovar

- [ ] O rótulo `S2D1` do simulado foi deduzido do nome do arquivo. Está correto?
- [ ] Significado dos códigos de turma (`T1NOTSA`, `VESPSBC`…) e padrão de nomes a adotar.
- [ ] Limiares dos alertas: acerto abaixo de 20% · mesma letra em 60% dos erros · 6 erros seguidos na mesma letra · questão com 70% de erro · amostra mínima de 10 · confiança de 95%.
- [ ] `X` em "Questões Erradas" tratado como marcação inválida (rasura ou dupla marcação).
- [ ] Licença **MIT** em nome de "Lauanda Nobre": trocar ou acrescentar nomes do grupo?
- [ ] Manter PySide6 + Plotly (mais pesado, mais completo) ou migrar para CustomTkinter + matplotlib (mais leve, exigiria reescrever a interface).
- [ ] Preencher a tabela "Equipe" do README com nomes e papéis.
- [ ] Combinar que **dados reais de alunos nunca vão para o repositório** nem para grupos de mensagem.

## 9. Próximos passos sugeridos

- Executável com instalador (PyInstaller + Inno Setup) para os professores não precisarem instalar o Python.
- Ícone e identidade visual do cursinho em `assets/`.
- Capturas de tela no README (`docs/img/`).
- GitHub Actions rodando os testes a cada *push*.
- Validar exportação de gráficos em PNG no macOS e no Linux.

## 10. Arquivos entregues

| Arquivo | Conteúdo |
|---|---|
| `Dashboard-Desempenho-De-Turmas.zip` | Projeto completo, já com todas as mudanças |
| `README.md` | Documentação nova (também dentro do zip) |
| `RELATORIO_DE_MUDANCAS.md` | Este relatório (também em `docs/` no zip) |
| `melhorias.patch` | Diferença entre a versão antiga e a atual, para aplicar com `git apply` |
| `modelo_planilha_turmas.xlsx` | Planilha vazia no padrão do projeto |
| `s2d1_epufabc_2026_padronizado.xlsx` | Dados reais do simulado já convertidos (**uso interno; não compartilhar nem versionar**) |
