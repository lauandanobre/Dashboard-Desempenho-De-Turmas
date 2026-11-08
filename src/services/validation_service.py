"""Conversão numérica e tratamento de qualidade dos dados.

Regra de ouro: nada é descartado em silêncio. Tudo que altera as estatísticas
(células vazias, texto inválido, fora do intervalo, duplicatas) gera um
QualityIssue que a interface mostra ao usuário.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict

import numpy as np
import pandas as pd

from src.models.analysis_result import (
    ColumnMapping, QualityIssue, QualityReport, ValidationConfig,
)


class DataValidationError(Exception):
    """Mapeamento de colunas inválido (mensagem em português)."""


# ---------------------------------------------------------------- números
def is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def parse_number(value) -> float | None:
    """Converte número em formato brasileiro ou internacional; None se inválido/vazio.

    Aceita: 75, 75.5, "75,5", "75,5%", "1.234,5", "1,234.5", " 80 %".
    Rejeita (None): texto, "1,2,3" (ambíguo), infinitos.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        f = float(value)
        return f if math.isfinite(f) else None
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if text.endswith("%"):
        text = text[:-1]
    if not text or not re.fullmatch(r"[+-]?[\d.,]+", text):
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if text.count(",") > 1:
            return None
        text = text.replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        f = float(text)
    except ValueError:
        return None
    return f if math.isfinite(f) else None


# ---------------------------------------------------------------- colunas
def classify_columns(df: pd.DataFrame, sample: int = 2000) -> dict[str, str]:
    """'numérica' (>= 80% dos valores convertíveis), 'categórica' ou 'vazia'."""
    kinds: dict[str, str] = {}
    for col in df.columns:
        values = [v for v in df[col].head(sample * 2) if not is_missing(v)][:sample]
        if not values:
            kinds[col] = "vazia"
            continue
        ok = sum(parse_number(v) is not None for v in values) / len(values)
        kinds[col] = "numérica" if ok >= 0.8 else "categórica"
    return kinds


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


norm_text = _norm       # nome público para outros módulos


_COUNT_HINTS = ("respostas", "acertos", "erros", "qtd", "quant", "total de", "questoes", "nº", "n°")
_PCT_HINTS = ("%", "pct", "percent", "nota", "media", "desempenho")
_PRESENCE_HINTS = ("presente", "presenca", "frequencia", "compareceu")


def _is_count_like(name: str) -> bool:
    """'Acertos', 'Respostas'... são contagens (0–90), não notas em %: não devem virar coluna de análise."""
    n = _norm(name)
    return any(h in n for h in _COUNT_HINTS) and not any(h in n for h in _PCT_HINTS)


def guess_mapping(df: pd.DataFrame) -> dict:
    """Sugestão inicial de colunas (o usuário sempre pode alterar)."""
    from src.services import schema

    cols = list(df.columns)
    keys = {_norm(c).replace(" ", "_"): c for c in cols}
    if set(schema.REQUIRED_COLUMNS) <= set(keys):          # planilha no padrão do projeto
        return {"turma": keys["turma"], "id": keys["id_aluno"], "period": keys.get("simulado"),
                "presence": keys["presente"],
                "values": [keys[c] for c in schema.DEFAULT_VALUE_COLUMNS if c in keys],
                "labels": {keys[c]: lab for c, lab in schema.AREA_LABELS.items() if c in keys}}

    kinds = classify_columns(df)
    turma = next((c for c in cols if "turma" in _norm(c)), None)
    ident = next((c for c in cols if c != turma and (
        _norm(c) in {"id", "id aluno", "aluno"} or _norm(c).startswith("id") or "matric" in _norm(c))), None)
    presence = next((c for c in cols if c not in (turma, ident) and any(h in _norm(c) for h in _PRESENCE_HINTS)), None)
    period = next((c for c in cols if c not in (turma, ident, presence) and any(
        k in _norm(c) for k in ("period", "avalia", "simulado", "data", "bimestre", "etapa", "prova", "mes"))), None)
    if turma is None:
        turma = next((c for c in cols if c not in (ident, period, presence) and kinds[c] == "categórica"), None)
    values = [c for c in cols if c not in (turma, ident, period, presence)
              and kinds[c] == "numérica" and not _is_count_like(c)]
    return {"turma": turma, "id": ident, "period": period, "presence": presence, "values": values, "labels": {}}


# ---------------------------------------------------------------- tratamento
def _clean_label(value) -> str | None:
    if is_missing(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).split())


def _period_label(value) -> str | None:
    if is_missing(value):
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return _clean_label(value)


def _is_present(value) -> bool:
    """Em branco ou desconhecido = presente (só 'NAO', 'AUSENTE'... excluem o aluno)."""
    if is_missing(value):
        return True
    from src.services import schema
    return _norm(value).upper() not in schema.ABSENT_TOKENS


def _check_mapping(df: pd.DataFrame, m: ColumnMapping) -> None:
    if not m.value_columns:
        raise DataValidationError("Selecione ao menos uma coluna numérica para analisar.")
    chosen = [m.turma, *m.value_columns] + [c for c in (m.id_column, m.period_column, m.presence_column) if c]
    missing = [c for c in chosen if c not in df.columns]
    if missing:
        raise DataValidationError(f"Coluna(s) não encontrada(s) na planilha: {', '.join(missing)}.")
    if len(set(chosen)) != len(chosen):
        raise DataValidationError("A mesma coluna foi escolhida para mais de uma função. Revise o mapeamento.")


def build_clean_dataset(
    df: pd.DataFrame, mapping: ColumnMapping, config: ValidationConfig | None = None
) -> tuple[pd.DataFrame, QualityReport]:
    """Devolve (dados tratados em formato longo, relatório de qualidade).

    Colunas do resultado: linha (da planilha, cabeçalho = 1), turma, id, periodo, area, valor.
    Cada coluna numérica escolhida vira uma "área" (ex.: exatas, humanas).
    """
    config = config or ValidationConfig()
    _check_mapping(df, mapping)
    issues: list[QualityIssue] = []
    rows_in = len(df)

    turma = df[mapping.turma].map(_clean_label)
    has_turma = turma.notna()
    n = int((~has_turma).sum())
    if n:
        issues.append(QualityIssue("warning", f"{n} linha(s) sem turma foram excluídas da análise "
                                   "(não dá para atribuí-las a uma turma).", n))

    labels = dict(mapping.area_labels)
    present = pd.Series(True, index=df.index)
    if mapping.presence_column:
        present = df[mapping.presence_column].map(_is_present)
    parsed_cols = {c: pd.to_numeric(df[c].map(parse_number), errors="coerce") for c in mapping.value_columns}
    if config.zero_is_absent:
        allv = pd.DataFrame(parsed_cols)
        zero_row = allv.notna().any(axis=1) & (allv.fillna(0) == 0).all(axis=1)
        present &= ~zero_row
    active = has_turma & present                      # linhas que entram nas médias
    n_absent = int((has_turma & ~present).sum())
    if n_absent:
        how = ("marcadas como ausentes" if mapping.presence_column else "com todas as notas iguais a 0 (tratadas como ausentes)")
        issues.append(QualityIssue("info", f"{n_absent} linha(s) {how} ({n_absent / max(int(has_turma.sum()), 1):.0%} "
                                   "do total) ficaram fora das médias. Ausente não é nota 0.", n_absent))

    blank = pd.Series([None] * rows_in, index=df.index, dtype=object)
    ids = df[mapping.id_column].map(_clean_label) if mapping.id_column else blank
    periods = df[mapping.period_column].map(_period_label) if mapping.period_column else blank
    linha = df.index.to_numpy() + 2

    pieces: list[pd.DataFrame] = []
    values_in = 0
    for col in mapping.value_columns:
        raw = df[col]
        missing = raw.map(is_missing)
        parsed = parsed_cols[col] * config.scale
        invalid = ~missing & parsed.isna()
        lo, hi = config.min_value, config.max_value
        out_range = pd.Series(False, index=df.index)
        if lo is not None:
            out_range |= parsed < lo
        if hi is not None:
            out_range |= parsed > hi
        valid = parsed.notna() & ~out_range & active
        values_in += int((~missing & active).sum())

        if (n := int((missing & active).sum())):
            issues.append(QualityIssue("info", f"'{col}': {n} célula(s) vazia(s) não entram nos cálculos.", n))
        if (n := int((invalid & active).sum())):
            ex = ", ".join(f"'{v}'" for v in raw[invalid & active].astype(str).str.strip().unique()[:3])
            issues.append(QualityIssue("warning", f"'{col}': {n} valor(es) não numérico(s) foram "
                                       f"ignorados (exemplos: {ex}).", n))
        if (n := int((out_range & active).sum())):
            issues.append(QualityIssue("warning", f"'{col}': {n} valor(es) fora do intervalo "
                                       f"[{_fmt(lo)}; {_fmt(hi)}] foram ignorados.", n))
        piece = pd.DataFrame({"linha": linha, "turma": turma, "id": ids, "periodo": periods,
                              "area": labels.get(col, col), "valor": parsed}, index=df.index)
        pieces.append(piece[valid])

    long = pd.concat(pieces) if pieces else pd.DataFrame()
    long = long.reset_index(drop=True)

    if mapping.id_column:
        keys = pd.DataFrame({"t": turma, "i": ids, "p": periods})[active & ids.notna()]
        dup_rows = keys.index[keys.duplicated(keep="first")]
        if len(dup_rows):
            if config.remove_duplicate_ids:
                long = long[~long["linha"].isin(dup_rows.to_numpy() + 2)].reset_index(drop=True)
                issues.append(QualityIssue("warning", f"{len(dup_rows)} linha(s) com id repetido na mesma "
                                           "turma/período foram removidas (mantida a primeira).", len(dup_rows)))
            else:
                issues.append(QualityIssue("warning", f"{len(dup_rows)} linha(s) repetem o id dentro da mesma "
                                           "turma/período. Foram mantidas e podem inflar as contagens.", len(dup_rows)))
        n = int((active & ids.isna()).sum())
        if n:
            issues.append(QualityIssue("info", f"{n} linha(s) sem id.", n))
    else:
        n = int(df.duplicated(subset=[mapping.turma, *mapping.value_columns]).sum())
        if n:
            issues.append(QualityIssue("info", f"{n} linha(s) idênticas a outras (mesma turma e mesmos valores). "
                                       "Foram mantidas; pode ser coincidência legítima.", n))

    for group in _case_variants(turma):
        issues.append(QualityIssue("warning", "Nomes de turma que diferem só em maiúsculas/minúsculas foram "
                                   f"tratados como turmas distintas: {', '.join(group)}.", len(group)))

    if config.scale != 1.0:
        issues.append(QualityIssue("info", f"Valores multiplicados por {_fmt(config.scale)} (conversão de fração)."))
    elif not long.empty and long["valor"].max() <= 1.0:
        issues.append(QualityIssue("warning", "Todos os valores são ≤ 1. Se estiverem em fração (0–1) em vez de "
                                   "porcentagem, marque a opção de conversão na importação."))

    report = QualityReport(rows_in=rows_in, rows_analyzed=int(long["linha"].nunique()) if not long.empty else 0,
                           values_in=values_in, values_used=len(long), n_absent=n_absent, issues=issues)
    if long.empty:
        long = pd.DataFrame({"linha": pd.Series(dtype=int), "turma": pd.Series(dtype=object),
                             "id": pd.Series(dtype=object), "periodo": pd.Series(dtype=object),
                             "area": pd.Series(dtype=object), "valor": pd.Series(dtype=float)})
        issues.append(QualityIssue("error", "Nenhum valor válido encontrado com o mapeamento atual."))
    return long, report


def _case_variants(labels: pd.Series) -> list[list[str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    for v in labels.dropna().unique():
        groups[v.casefold()].add(v)
    return [sorted(g) for g in groups.values() if len(g) > 1]


def _fmt(x) -> str:
    return "—" if x is None else (str(int(x)) if float(x).is_integer() else str(x).replace(".", ","))
