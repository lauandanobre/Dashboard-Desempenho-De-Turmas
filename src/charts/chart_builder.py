"""Construção dos gráficos Plotly (sem Qt). Cada função recebe DataFrames e devolve go.Figure.

Princípios: eixo de porcentagem começa em zero, títulos e rótulos sempre presentes,
sem efeitos decorativos. Tudo funciona offline (plotly.min.js é copiado do pacote).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

from src.services.analysis_service import order_periods
from src.utils.formatting import format_number

PALETTE = ["#3B5B92", "#C77D3A", "#4F8A6B", "#8A5A99", "#7B7F86", "#B0453F", "#2E8C9E", "#9A8C3A"]
FONT = "Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif"
PLOT_CONFIG = {"responsive": True, "displaylogo": False,
               "modeBarButtonsToRemove": ["toImage", "lasso2d", "select2d"]}
_JS_NAME = "plotly.min.js"

ValueRange = tuple[float, float] | None


def _layout(fig: go.Figure, title: str, x_title: str | None, y_title: str | None,
            value_range: ValueRange = None, y_is_value: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_white", title=dict(text=title, x=0.01, xanchor="left"),
        font=dict(family=FONT, size=13, color="#26303B"), colorway=PALETTE, separators=",.",
        margin=dict(l=70, r=30, t=70, b=70), paper_bgcolor="white", plot_bgcolor="white",
        xaxis_title=x_title, yaxis_title=y_title, legend=dict(orientation="h", y=-0.2),
    )
    if value_range and y_is_value:
        fig.update_yaxes(range=list(value_range))
    return fig


def _label(unit: str) -> str:
    return f"Média de acertos ({unit})" if unit else "Média"


def bar_means(summary: pd.DataFrame, overall_by_area: dict[str, float], value_range: ValueRange = None,
              unit: str = "%") -> go.Figure:
    """Barras com a média de cada turma (agrupadas por área quando há mais de uma)."""
    fig = go.Figure()
    areas = list(dict.fromkeys(summary["area"]))
    for area in areas:
        sub = summary[summary["area"] == area]
        fig.add_bar(
            x=sub["turma"], y=sub["media"], name=str(area),
            text=[format_number(v) for v in sub["media"]], textposition="auto",
            customdata=sub[["registros", "minimo", "maximo"]].to_numpy(),
            hovertemplate="<b>%{x}</b><br>Média: %{y:.1f}<br>Registros: %{customdata[0]}"
                          "<br>Mín.: %{customdata[1]:.1f} · Máx.: %{customdata[2]:.1f}<extra>" + str(area) + "</extra>",
        )
    if len(areas) == 1 and areas[0] in overall_by_area:
        fig.add_hline(y=overall_by_area[areas[0]], line=dict(color="#7B7F86", dash="dash", width=1),
                      annotation_text=f"Média geral: {format_number(overall_by_area[areas[0]])}",
                      annotation_position="top left")
    title = "Média por turma" + (f" — {areas[0]}" if len(areas) == 1 else "")
    fig.update_layout(barmode="group", showlegend=len(areas) > 1)
    return _layout(fig, title, "Turma", _label(unit), value_range)


def histogram(long: pd.DataFrame, value_range: ValueRange = None, unit: str = "%") -> go.Figure:
    fig = go.Figure()
    areas = list(dict.fromkeys(long["area"]))
    for area in areas:
        kwargs = {}
        if value_range:
            lo, hi = value_range
            kwargs["xbins"] = dict(start=lo, end=hi, size=(hi - lo) / 10)
        fig.add_histogram(x=long.loc[long["area"] == area, "valor"], name=str(area), opacity=0.7 if len(areas) > 1 else 1,
                          marker_line=dict(width=1, color="white"), **kwargs)
    fig.update_layout(barmode="overlay", showlegend=len(areas) > 1)
    fig.update_xaxes(range=list(value_range) if value_range else None)
    _layout(fig, "Distribuição dos resultados", f"Resultado ({unit})" if unit else "Resultado",
            "Quantidade de registros", y_is_value=False)
    return fig


def boxplot(long: pd.DataFrame, value_range: ValueRange = None, unit: str = "%") -> go.Figure:
    fig = go.Figure()
    for area in dict.fromkeys(long["area"]):
        sub = long[long["area"] == area]
        fig.add_box(x=sub["turma"], y=sub["valor"], name=str(area), boxpoints="outliers")
    fig.update_layout(boxmode="group", showlegend=long["area"].nunique() > 1)
    return _layout(fig, "Dispersão dos resultados por turma", "Turma", f"Resultado ({unit})" if unit else "Resultado",
                   value_range)


def area_comparison(summary: pd.DataFrame, value_range: ValueRange = None, unit: str = "%") -> go.Figure:
    """Comparação entre disciplinas/áreas: uma série por turma."""
    fig = go.Figure()
    for turma in dict.fromkeys(summary["turma"]):
        sub = summary[summary["turma"] == turma]
        fig.add_bar(x=sub["area"], y=sub["media"], name=str(turma),
                    text=[format_number(v) for v in sub["media"]], textposition="auto")
    fig.update_layout(barmode="group")
    return _layout(fig, "Comparação entre áreas", "Área", _label(unit), value_range)


def evolution(long: pd.DataFrame, value_range: ValueRange = None, unit: str = "%") -> go.Figure:
    """Média por período/avaliação, uma linha por turma (e área, se houver mais de uma)."""
    periods = order_periods(long["periodo"].dropna().unique())
    multi_area = long["area"].nunique() > 1
    fig = go.Figure()
    for (turma, area), sub in long.groupby(["turma", "area"], sort=False):
        means = sub.groupby("periodo")["valor"].mean().reindex(periods)
        name = f"{turma} — {area}" if multi_area else str(turma)
        fig.add_scatter(x=periods, y=means.to_numpy(), mode="lines+markers", name=name, connectgaps=False)
    fig.update_xaxes(categoryorder="array", categoryarray=periods, type="category")
    return _layout(fig, "Evolução da média por período", "Período / avaliação", _label(unit), value_range)


# ------------------------------------------------------------- saída em HTML
_TEMPLATE = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
             "<style>html,body{{margin:0;height:100%;background:#fff}}</style>"
             "<script src='" + _JS_NAME + "'></script></head><body>{body}</body></html>")


def write_figure_html(fig: go.Figure, directory: str | Path, filename: str) -> Path:
    """Grava a figura numa página local que usa o plotly.min.js do próprio pacote (offline)."""
    directory = Path(directory)
    js = directory / _JS_NAME
    if not js.exists():
        js.write_text(get_plotlyjs(), encoding="utf-8")
    body = fig.to_html(full_html=False, include_plotlyjs=False, default_width="100%",
                       default_height="100%", config=PLOT_CONFIG)
    path = directory / filename
    path.write_text(_TEMPLATE.format(body=body), encoding="utf-8")
    return path


def save_standalone_html(fig: go.Figure, dest: str | Path) -> Path:
    """HTML único e interativo, com a biblioteca embutida (funciona sem internet)."""
    dest = Path(dest)
    fig.write_html(dest, include_plotlyjs=True, config=PLOT_CONFIG)
    return dest
