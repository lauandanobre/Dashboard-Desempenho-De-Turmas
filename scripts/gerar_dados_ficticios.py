"""Gera assets/exemplo_ficticio.csv com dados 100% fictícios (nenhum aluno real)."""
import random
from pathlib import Path

random.seed(42)
turmas = {"Turma 1": (72, 65), "Turma 2": (58, 61), "Turma 3": (80, 74), "Turma 10": (49, 52)}
linhas = ["turma;id;exatas;humanas"]
n = 0
for turma, (me, mh) in turmas.items():
    for _ in range(30):
        n += 1
        ex = min(100, max(0, random.gauss(me, 12)))
        hu = min(100, max(0, random.gauss(mh, 12)))
        linhas.append(f"{turma};A{n:04d};{ex:.1f}".replace(".", ",") + f";{hu:.1f}".replace(".", ","))
out = Path(__file__).resolve().parent.parent / "assets" / "exemplo_ficticio.csv"
out.write_text("\n".join(linhas) + "\n", encoding="utf-8")
print(f"{n} registros fictícios gravados em {out}")
