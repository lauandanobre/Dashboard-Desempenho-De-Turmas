"""Definição do PADRÃO de planilha do projeto (fonte única de verdade).

Qualquer layout aceito pelo app é convertido para este padrão logo na importação.
A planilha-modelo (assets/modelo_planilha_turmas.xlsx) é gerada a partir daqui.
"""
from __future__ import annotations

# ------------------------------------------------------------------ abas
SHEET_ALUNOS = "Alunos"
SHEET_GABARITO = "Gabarito"
SHEET_ERROS = "Erros"
SHEET_CONFIG = "Config"
SHEET_README = "LEIA-ME"

# ------------------------------------------------------------------ colunas da aba Alunos
STANDARD_COLUMNS = [
    "turma", "id_aluno", "simulado", "presente", "respostas",
    "acertos_linguagens", "acertos_humanas", "acertos_total",
    "pct_linguagens", "pct_humanas", "pct_total", "observacao",
]
REQUIRED_COLUMNS = ("turma", "id_aluno", "presente", "acertos_linguagens", "acertos_humanas")
INPUT_COLUMNS = ("turma", "id_aluno", "simulado", "presente", "respostas",
                 "acertos_linguagens", "acertos_humanas", "observacao")
FORMULA_COLUMNS = ("acertos_total", "pct_linguagens", "pct_humanas", "pct_total")

ERROS_COLUMNS = ["turma", "id_aluno", "simulado", "questao", "marcada"]
GABARITO_COLUMNS = ["questao", "area", "resposta_correta", "anulada"]

#: nome amigável de cada coluna de nota (aparece nos gráficos)
AREA_LABELS = {"pct_linguagens": "Linguagens", "pct_humanas": "Humanas", "pct_total": "Total"}
DEFAULT_VALUE_COLUMNS = ("pct_linguagens", "pct_humanas")   # "Total" não entra: duplicaria as médias

# ------------------------------------------------------------------ prova (padrão do cursinho)
N_LINGUAGENS = 45          # Q1–Q45
N_HUMANAS = 45             # Q46–Q90
EXAMPLE_TAG = "EXEMPLO"    # linhas de exemplo do modelo começam com isto e são ignoradas na importação

# ------------------------------------------------------------------ presença
PRESENT_TOKENS = {"SIM", "S", "1", "TRUE", "PRESENTE", "P"}
ABSENT_TOKENS = {"NAO", "N", "0", "FALSE", "AUSENTE", "A", "FALTOU"}

# ------------------------------------------------------------------ layout legado (exportação do sistema)
LEGACY_KEYS = {          # chave normalizada (minúsculas, sem acento) -> papel
    "id": "id", "turma": "turma", "respostas": "respostas", "acertos": "acertos",
    "percentual": "percentual", "%linguagens": "pct_linguagens", "%humanas": "pct_humanas",
    "questoes erradas": "erradas",
}
LEGACY_REQUIRED = {"id", "turma", "respostas", "acertos", "pct_linguagens", "pct_humanas", "erradas"}
