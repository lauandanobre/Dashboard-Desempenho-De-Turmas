"""Indicadores estatísticos. Funções puras sobre DataFrames (sem Qt, sem Plotly).

Entrada: DataFrame longo gerado por validation_service.build_clean_dataset
(colunas: linha, turma, id, periodo, area, valor).

Definições (explícitas para a equipe e para o usuário):
- "registros" de um grupo = quantidade de valores válidos do grupo.
- "média geral" = média de TODOS os valores válidos do recorte (não é média das médias).
- "registros analisados" (dashboard) = linhas da planilha com ao menos um valor válido.
"""
from __future__ import annotations

import re

import pandas as pd

from src.models.analysis_result import AttentionCriteria, Filters, OverallStats
from src.utils.formatting import format_number
from src.services.validation_service import parse_number

SUMMARY_COLUMNS = ["registros", "media", "mediana", "minimo", "maximo", "desvio_padrao"]


def _natural_key(text) -> list:
    return [int(p) if p.isdigit() else p.casefold() for p in re.split(r"(\d+)", str(text))]


def natural_sorted(values) -> list:
    return sorted(values, key=_natural_key)


def apply_filters(long: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    out = long
    if filters.turmas is not None:
        out = out[out["turma"].isin(filters.turmas)]
    if filters.area is not None:
        out = out[out["area"] == filters.area]
    if filters.period is not None:
        out = out[out["periodo"] == filters.period]
    return out


def summarize(long: pd.DataFrame, by: tuple[str, ...] = ("turma", "area")) -> pd.DataFrame:
    cols = list(by)
    if long.empty:
        return pd.DataFrame(columns=cols + SUMMARY_COLUMNS)
    out = (long.groupby(cols, sort=False)["valor"]
           .agg(registros="count", media="mean", mediana="median",
                minimo="min", maximo="max", desvio_padrao="std")
           .reset_index())
    area_order = {a: i for i, a in enumerate(long["area"].unique())}

    def key(i: int):
        return [area_order[out[c].iat[i]] if c == "area" else _natural_key(out[c].iat[i]) for c in cols]

    return out.iloc[sorted(range(len(out)), key=key)].reset_index(drop=True)


def overall_stats(long: pd.DataFrame) -> OverallStats:
    if long.empty:
        return OverallStats(0, 0, 0, None, None, None)
    by_turma = long.groupby("turma")["valor"].mean()
    best = by_turma.idxmax()
    return OverallStats(n_turmas=int(by_turma.size), n_records=int(long["linha"].nunique()),
                        n_values=len(long), mean=float(long["valor"].mean()),
                        best_turma=str(best), best_mean=float(by_turma.loc[best]))


def describe_criteria(c: AttentionCriteria) -> str:
    parts = []
    if c.below_overall_by is not None:
        parts.append(f"média da turma pelo menos {format_number(c.below_overall_by)} ponto(s) abaixo da "
                     "média geral da mesma área")
    if c.absolute_minimum is not None:
        parts.append(f"média da turma abaixo de {format_number(c.absolute_minimum)}")
    return ("Turma sinalizada quando: " + " OU ".join(parts) + ".") if parts else \
        "Nenhum critério de atenção ativo: nenhuma turma é sinalizada."


def flag_attention(long: pd.DataFrame, criteria: AttentionCriteria) -> pd.DataFrame:
    """Resumo por turma e área com a sinalização de atenção e o motivo (sempre explícito)."""
    s = summarize(long, ("turma", "area"))
    s["media_geral_area"] = pd.Series(dtype=float) if s.empty else s["area"].map(long.groupby("area")["valor"].mean())
    s["diferenca_media_geral"] = s["media"] - s["media_geral_area"]
    flags, reasons = [], []
    for row in s.itertuples():
        r = []
        d = round(float(row.diferenca_media_geral), 6)
        if criteria.below_overall_by is not None and d <= -criteria.below_overall_by:
            r.append(f"{format_number(abs(d))} ponto(s) abaixo da média geral de {row.area}")
        if criteria.absolute_minimum is not None and row.media < criteria.absolute_minimum:
            r.append(f"média {format_number(row.media)} abaixo do mínimo {format_number(criteria.absolute_minimum)}")
        flags.append(bool(r))
        reasons.append("; ".join(r))
    s["atencao"] = flags
    s["motivo"] = reasons
    return s


def pairwise_differences(long: pd.DataFrame, area: str | None = None) -> pd.DataFrame:
    """Matriz de diferenças de média: valor = média(linha) − média(coluna)."""
    data = long if area is None else long[long["area"] == area]
    means = data.groupby("turma")["valor"].mean()
    names = natural_sorted(means.index)
    means = means.loc[names]
    mat = means.to_numpy()[:, None] - means.to_numpy()[None, :]
    return pd.DataFrame(mat, index=names, columns=names)


def order_periods(values) -> list[str]:
    """Ordena períodos: numérico, depois data ISO; caso contrário, ordem de aparição na planilha."""
    vals = list(dict.fromkeys(v for v in values if v is not None and not pd.isna(v)))
    nums = [parse_number(v) for v in vals]
    if vals and all(n is not None for n in nums):
        return [v for _, v in sorted(zip(nums, vals))]
    dates = pd.to_datetime(pd.Series(vals), format="%Y-%m-%d", errors="coerce")
    if vals and dates.notna().all():
        return [v for _, v in sorted(zip(dates, vals))]
    return vals
