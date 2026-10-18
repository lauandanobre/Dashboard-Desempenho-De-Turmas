"""Estado da análise atual (um arquivo importado + resultados)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.models.analysis_result import (
    AttentionCriteria, ColumnMapping, ImportedTable, QualityReport, ValidationConfig,
)


@dataclass
class Session:
    source_path: Path
    table: ImportedTable
    mapping: ColumnMapping
    config: ValidationConfig
    long: pd.DataFrame                      # dados tratados (formato longo)
    quality: QualityReport
    criteria: AttentionCriteria = field(default_factory=AttentionCriteria)
    unexported: bool = True                 # há resultados ainda não exportados?

    @property
    def unit(self) -> str:
        return "%" if self.config.max_value == 100 else ""

    @property
    def value_range(self) -> tuple[float, float] | None:
        lo, hi = self.config.min_value, self.config.max_value
        return (lo, hi) if lo is not None and hi is not None else None
