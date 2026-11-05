"""Dados 100% FICTÍCIOS no layout da exportação do sistema de correção (para exemplos e testes).

Nenhum aluno real: notas e respostas são sorteadas com semente fixa (resultado reproduzível).
"""
from __future__ import annotations

import random

import pandas as pd

LETTERS = "ABCDE"
DEFAULT_TURMAS = (("T1NOTSA", 30, 0.62), ("T1VESPSA", 34, 0.58), ("T2NOTSA", 28, 0.64),
                  ("T2VESPSA", 26, 0.52), ("VESPSBC", 24, 0.58))
HARD_QUESTIONS = {18: -0.45, 89: -0.50}      # questões "problemáticas" de propósito (ex.: gabarito suspeito)


def _pct(x: float) -> str:
    return f"{x:.2f}%".replace(".", ",")


def make_legacy_frame(seed: int = 42, turmas=DEFAULT_TURMAS, absent_rate: float = 0.35, n_ling: int = 45,
                      n_hum: int = 45, truncate_at: int | None = None) -> pd.DataFrame:
    """Planilha no layout: ID, TURMA, Respostas, Acertos, Percentual, %Linguagens, %Humanas, Questões Erradas."""
    rng = random.Random(seed)
    n_total = n_ling + n_hum
    gabarito = {q: rng.choice(LETTERS) for q in range(1, n_total + 1)}
    difficulty = {q: HARD_QUESTIONS.get(q, rng.uniform(-0.2, 0.2)) for q in range(1, n_total + 1)}
    rows, ident = [], 0
    for turma, n_alunos, mean in turmas:
        for _ in range(n_alunos):
            ident += 1
            if rng.random() < absent_rate:
                rows.append([ident, turma, 0, 0, _pct(0), _pct(0), _pct(0), ""])
                continue
            ability = rng.gauss(mean, 0.12)
            right_l = right_h = answered = 0
            wrong = []
            for q in range(1, n_total + 1):
                if rng.random() < 0.01:                       # questão em branco
                    continue
                answered += 1
                if rng.random() < min(0.95, max(0.05, ability + difficulty[q])):
                    if q <= n_ling:
                        right_l += 1
                    else:
                        right_h += 1
                else:
                    wrong.append((q, rng.choice([x for x in LETTERS if x != gabarito[q]]), gabarito[q]))
            right = right_l + right_h
            text = ";".join(f"Q{q}({m}/{c})" for q, m, c in wrong[:truncate_at])
            rows.append([ident, turma, answered, right, _pct(right / n_total * 100),
                         _pct(right_l / n_ling * 100), _pct(right_h / n_hum * 100), text])
    return pd.DataFrame(rows, columns=["ID", "TURMA", "Respostas", "Acertos", "Percentual",
                                       "%Linguagens", "%Humanas", "Questões Erradas"])
