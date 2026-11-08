"""Análise por questão: gabarito, taxa de erro, alternativas mais marcadas e alertas.

Funções puras sobre DataFrames (sem Qt). Entradas:
- alunos: DataFrame no padrão (schema.STANDARD_COLUMNS);
- erros : DataFrame com colunas turma, id_aluno, simulado, questao, marcada, correta.

Limite importante: a planilha só lista as questões ERRADAS. Por isso, só entram no ranking
os alunos cuja lista está COMPLETA (nº de erros listados == respostas − acertos). Listas
cortadas (ex.: PDF exportado do Google Sheets) deixariam as questões do fim da prova
artificialmente "fáceis".
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import pandas as pd

from src.services import schema

KEY = ["turma", "id_aluno", "simulado"]
ERRO_RE = re.compile(r"Q\s*(\d+)\s*\(\s*([A-Za-z])\s*/\s*([A-Ea-e])\s*\)")
LETTERS = "ABCDE"

# limiares dos alertas (documentados no README)
CHANCE_LEVEL = 20.0          # % de acerto esperado ao chutar em 5 alternativas
MIN_RUN_SAME_LETTER = 8      # nº de questões seguidas (certas ou erradas) com a mesma letra
MIN_DOMINANT_SHARE = 0.60     # fração dos erros com a mesma letra (típico: 25–35%)
MIN_DOMINANT_ERRORS = 20     # mínimo de erros listados para avaliar a fração
MIN_WRONG_RUN = 6            # nº de questões seguidas ERRADAS marcadas com a mesma letra
HARD_QUESTION_RATE = 70.0    # % de erro a partir da qual a questão merece revisão


def area_of(question: int, n_ling: int = schema.N_LINGUAGENS) -> str:
    return "Linguagens" if question <= n_ling else "Humanas"


# ------------------------------------------------------------------ leitura do texto "Q1(B/C);Q3(C/A)"
def parse_erradas(text) -> list[tuple[int, str, str]]:
    """'Q1(B/C);Q3(X/A)' -> [(1,'B','C'), (3,'X','A')]. Texto vazio/inválido -> []."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return []
    return [(int(q), m.upper(), c.upper()) for q, m, c in ERRO_RE.findall(str(text))]


def erros_from_text(keys: pd.DataFrame, texts: pd.Series) -> pd.DataFrame:
    """Expande a coluna de texto em formato longo. `keys` tem turma, id_aluno, simulado."""
    rows = []
    for (_, k), text in zip(keys.iterrows(), texts):
        for q, marcada, correta in parse_erradas(text):
            rows.append((k["turma"], k["id_aluno"], k["simulado"], q, marcada, correta))
    return pd.DataFrame(rows, columns=[*schema.ERROS_COLUMNS, "correta"])


def infer_gabarito(erros: pd.DataFrame) -> tuple[dict[int, str], list[int]]:
    """Gabarito deduzido dos pares (marcada/correta). Devolve (gabarito, questões conflitantes)."""
    votes: dict[int, Counter] = defaultdict(Counter)
    for q, c in zip(erros["questao"], erros["correta"]):
        if isinstance(c, str) and c in LETTERS:
            votes[int(q)][c] += 1
    gab = {q: cnt.most_common(1)[0][0] for q, cnt in votes.items()}
    conflicts = sorted(q for q, cnt in votes.items() if len(cnt) > 1)
    return gab, conflicts


# ------------------------------------------------------------------ completude
def completeness(alunos: pd.DataFrame, erros: pd.DataFrame | None) -> pd.DataFrame | None:
    """Por aluno presente: erros esperados (respostas − acertos) x erros registrados."""
    if erros is None:
        return None
    pres = alunos[alunos["presente"] == "SIM"].copy()
    pres["esperado"] = pres["respostas"] - pres["acertos_total"]
    got = erros.groupby(KEY).size().rename("registrado")
    pres = pres.merge(got, how="left", left_on=KEY, right_index=True)
    pres["registrado"] = pres["registrado"].fillna(0).astype(int)
    pres["completo"] = pres["esperado"].notna() & (pres["registrado"] == pres["esperado"])
    return pres[[*KEY, "esperado", "registrado", "completo"]].reset_index(drop=True)


# ------------------------------------------------------------------ ranking de questões
def question_stats(alunos: pd.DataFrame, erros: pd.DataFrame, gabarito: dict[int, str] | None = None,
                   n_ling: int = schema.N_LINGUAGENS, n_total: int = schema.N_LINGUAGENS + schema.N_HUMANAS,
                   anuladas: set[int] | None = None, turmas: tuple[str, ...] | None = None,
                   simulado: str | None = None) -> pd.DataFrame:
    """Taxa de erro por questão, só com alunos presentes de lista completa (e das turmas escolhidas).

    Colunas: questao, area, gabarito, base, erros, taxa_erro (0-100), alt_errada (letra mais marcada
    entre os erros) e alt_errada_pct (% dos erros que escolheram essa letra).
    """
    cols = ["questao", "area", "gabarito", "base", "erros", "taxa_erro", "alt_errada", "alt_errada_pct"]
    comp = completeness(alunos, erros)
    if comp is None or comp.empty:
        return pd.DataFrame(columns=cols)
    ok = comp[comp["completo"]]
    if turmas is not None:
        ok = ok[ok["turma"].isin(turmas)]
    if simulado is not None:
        ok = ok[ok["simulado"] == simulado]
    base = len(ok)
    if base == 0:
        return pd.DataFrame(columns=cols)
    sel = erros.merge(ok[KEY], on=KEY, how="inner")
    gab = gabarito or {}
    anuladas = anuladas or set()
    rows = []
    for q in range(1, n_total + 1):
        if q in anuladas:
            continue
        sub = sel[sel["questao"] == q]
        n_err = len(sub)
        marks = Counter(m for m in sub["marcada"] if m)
        alt, alt_n = (marks.most_common(1)[0] if marks else (None, 0))
        rows.append({"questao": q, "area": area_of(q, n_ling), "gabarito": gab.get(q), "base": base,
                     "erros": n_err, "taxa_erro": n_err / base * 100,
                     "alt_errada": alt, "alt_errada_pct": (alt_n / n_err * 100) if n_err else None})
    return pd.DataFrame(rows, columns=cols)


# ------------------------------------------------------------------ alertas
def _longest_run(letters: list[str]) -> tuple[int, str]:
    best, best_letter, run, prev = 0, "", 0, None
    for x in letters:
        run = run + 1 if x == prev else 1
        prev = x
        if run > best:
            best, best_letter = run, x
    return best, best_letter


def _longest_wrong_run(g: pd.DataFrame) -> tuple[int, str]:
    """Maior sequência de números de questão consecutivos errados com a mesma alternativa marcada."""
    best, best_letter, run, prev_q, prev_m = 0, "", 0, None, None
    for q, m in sorted(zip(g["questao"], g["marcada"])):
        run = run + 1 if (prev_q is not None and q == prev_q + 1 and m == prev_m and m != "X") else 1
        prev_q, prev_m = q, m
        if run > best:
            best, best_letter = run, m
    return best, best_letter


def student_alerts(alunos: pd.DataFrame, erros: pd.DataFrame | None, gabarito: dict[int, str] | None,
                   n_total: int = schema.N_LINGUAGENS + schema.N_HUMANAS) -> pd.DataFrame:
    """Alunos que merecem conferência manual do cartão-resposta (não é julgamento sobre o aluno)."""
    out = []
    pres = alunos[alunos["presente"] == "SIM"]
    low = pres[(pres["respostas"] >= 0.6 * n_total) & (pres["pct_total"] < CHANCE_LEVEL)]
    for r in low.itertuples():
        out.append((r.turma, r.id_aluno, "Abaixo do acaso",
                    f"{r.pct_total:.1f}% de acerto (chute em 5 alternativas daria ~{CHANCE_LEVEL:.0f}%). "
                    "Conferir se o cartão/gabarito da versão está correto."))
    inc = pres[pres["observacao"].astype(str).str.contains("inconsistente", na=False)]
    for r in inc.itertuples():
        out.append((r.turma, r.id_aluno, "Percentual inconsistente", str(r.observacao)))
    if erros is not None:
        flagged: set[tuple] = set()
        # 1) erros consecutivos com a mesma letra (vale mesmo com lista incompleta ou questões em branco)
        for key, g in erros.groupby(KEY):
            run, letter = _longest_wrong_run(g)
            marks = g[g["marcada"] != "X"]["marcada"].value_counts()
            share = (marks.iloc[0] / len(g)) if len(marks) else 0.0
            if len(g) >= MIN_DOMINANT_ERRORS and share >= MIN_DOMINANT_SHARE:
                flagged.add(key)
                out.append((key[0], key[1], "Mesma alternativa em excesso",
                            f"{share:.0%} dos erros foram marcados com {marks.index[0]} (o usual é 25–35%) — "
                            "possível cartão preenchido sem leitura."))
            elif run >= MIN_WRONG_RUN:
                flagged.add(key)
                out.append((key[0], key[1], "Mesma alternativa em sequência",
                            f"{run} questões seguidas erradas, todas marcadas com {letter} — "
                            "possível cartão preenchido sem leitura."))
        # 2) folha reconstruída (prova inteira respondida e lista completa): sequência de qualquer resultado
        if gabarito:
            comp = completeness(alunos, erros)
            full = comp[comp["completo"]].merge(pres[[*KEY, "respostas"]], on=KEY)
            full = full[full["respostas"] == n_total]
            by_student = {k: g for k, g in erros.groupby(KEY)}
            for r in full.itertuples():
                if (r.turma, r.id_aluno, r.simulado) in flagged:
                    continue
                g = by_student.get((r.turma, r.id_aluno, r.simulado))
                wrong = dict(zip(g["questao"], g["marcada"])) if g is not None else {}
                sheet = [wrong.get(q, gabarito.get(q)) for q in range(1, n_total + 1)]
                if None in sheet:
                    continue
                run, letter = _longest_run(sheet)
                if run >= MIN_RUN_SAME_LETTER:
                    out.append((r.turma, r.id_aluno, "Mesma alternativa em sequência",
                                f"{run} questões seguidas marcadas com {letter} — "
                                "possível cartão preenchido sem leitura."))
    return pd.DataFrame(out, columns=["turma", "id_aluno", "tipo", "detalhe"])


def hard_questions(stats: pd.DataFrame, threshold: float = HARD_QUESTION_RATE) -> pd.DataFrame:
    """Questões com taxa de erro alta: candidatas a erro de gabarito ou anulação."""
    if stats.empty:
        return stats
    return stats[stats["taxa_erro"] >= threshold].sort_values("taxa_erro", ascending=False)
