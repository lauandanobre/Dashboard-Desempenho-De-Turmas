"""Gera assets/modelo_planilha_turmas.xlsx (planilha vazia no padrão do projeto)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.services.standard_workbook import write_standard_workbook  # noqa: E402

dest = write_standard_workbook(ROOT / "assets" / "modelo_planilha_turmas.xlsx")
print(f"Modelo gravado em {dest}")
