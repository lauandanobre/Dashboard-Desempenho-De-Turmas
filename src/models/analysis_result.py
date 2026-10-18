"""Estruturas de dados compartilhadas entre serviços, gráficos e interface.

Este módulo não depende de Qt nem de Plotly. É o "contrato" entre as pessoas
da equipe: mudar um campo aqui exige avisar todo mundo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class ColumnMapping:
    """Quais colunas da planilha têm cada papel na análise."""

    turma: str
    value_columns: tuple[str, ...]          # ex.: ("exatas", "humanas")
    id_column: str | None = None
    period_column: str | None = None


@dataclass(frozen=True)
class ValidationConfig:
    """Regras de tratamento. Intervalo None = sem limite."""

    min_value: float | None = 0.0
    max_value: float | None = 100.0
    scale: float = 1.0                      # 100.0 se os valores vierem em fração (0-1)
    remove_duplicate_ids: bool = False


@dataclass(frozen=True)
class AttentionCriteria:
    """Critérios (configuráveis) para sinalizar turmas que pedem atenção.

    Não existe aprovação/reprovação: apenas sinalização explícita.
    """

    below_overall_by: float | None = 5.0    # pontos abaixo da média geral da área
    absolute_minimum: float | None = None   # média mínima absoluta


@dataclass(frozen=True)
class Filters:
    turmas: tuple[str, ...] | None = None   # None = todas
    area: str | None = None                 # None = todas
    period: str | None = None               # None = todos


@dataclass
class ImportedTable:
    df: pd.DataFrame
    file_name: str                          # apenas o nome, sem o caminho
    sheet: str | None = None
    encoding: str | None = None
    delimiter: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class QualityIssue:
    severity: str                           # "info" | "warning" | "error"
    message: str
    count: int = 0


@dataclass
class QualityReport:
    rows_in: int = 0
    rows_analyzed: int = 0
    values_in: int = 0
    values_used: int = 0
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


@dataclass(frozen=True)
class OverallStats:
    n_turmas: int
    n_records: int
    n_values: int
    mean: float | None
    best_turma: str | None
    best_mean: float | None
