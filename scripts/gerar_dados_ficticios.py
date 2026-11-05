"""Gera dados 100% fictícios no layout do sistema de correção:
assets/exemplo_ficticio.csv e assets/exemplo_ficticio.xlsx (nenhum aluno real)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.services.demo_data import make_legacy_frame  # noqa: E402

df = make_legacy_frame(seed=42)
df.to_csv(ROOT / "assets" / "exemplo_ficticio.csv", sep=";", index=False, encoding="utf-8")
df.to_excel(ROOT / "assets" / "exemplo_ficticio.xlsx", index=False)
print(f"{len(df)} alunos fictícios ({(df['Respostas'] > 0).sum()} presentes) gravados em assets/")
