"""Conjunto de dados padronizado (independe do layout original da planilha)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Dataset:
    """Dados de um simulado já convertidos para o padrão do projeto.

    alunos   : uma linha por aluno (colunas em schema.STANDARD_COLUMNS).
    erros    : uma linha por questão errada (turma, id_aluno, simulado, questao, marcada, correta)
               ou None quando a planilha não traz esse detalhe.
    gabarito : {nº da questão: letra correta} ou None.
    layout   : "padrao" (modelo do projeto) ou "legado" (exportação do sistema de correção).
    """

    alunos: pd.DataFrame
    erros: pd.DataFrame | None = None
    gabarito: dict[int, str] | None = None
    layout: str = "padrao"
    n_linguagens: int = 45
    n_humanas: int = 45
    anuladas: set[int] = field(default_factory=set)   # questões anuladas (fora do ranking)
    notes: list[str] = field(default_factory=list)

    @property
    def n_questoes(self) -> int:
        return self.n_linguagens + self.n_humanas

    @property
    def has_items(self) -> bool:
        return self.erros is not None and not self.erros.empty
