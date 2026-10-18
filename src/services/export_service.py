"""Exportação de tabelas, resumos e relatório. Nunca altera a planilha de origem."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.models.analysis_result import AttentionCriteria, OverallStats, QualityReport
from src.services.analysis_service import describe_criteria
from src.utils.formatting import format_number


class ExportError(Exception):
    """Falha de exportação (mensagem em português)."""


def check_destination(dest: str | Path, source: str | Path | None) -> Path:
    dest = Path(dest)
    if source is not None and dest.resolve() == Path(source).resolve():
        raise ExportError("O destino é o próprio arquivo importado. Escolha outro nome para não sobrescrever a planilha original.")
    if not dest.parent.exists():
        raise ExportError("A pasta de destino não existe.")
    return dest


def _sanitize(value):
    """Evita injeção de fórmulas ao abrir o resultado no Excel/LibreOffice."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@") and not _looks_numeric(value):
        return "'" + value
    return value


def _looks_numeric(text: str) -> bool:
    try:
        float(text.replace(",", "."))
        return True
    except ValueError:
        return False


def _safe_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object or str(out[col].dtype).startswith("str"):
            out[col] = out[col].map(_sanitize)
    return out


def export_table(df: pd.DataFrame, dest: str | Path, source: str | Path | None = None) -> Path:
    """CSV (padrão brasileiro: ';' e vírgula decimal, abre direto no Excel) ou XLSX."""
    dest = check_destination(dest, source)
    safe = _safe_frame(df)
    try:
        if dest.suffix.lower() == ".xlsx":
            safe.to_excel(dest, index=False, engine="openpyxl")
        elif dest.suffix.lower() == ".csv":
            safe.to_csv(dest, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        else:
            raise ExportError("Use a extensão .csv ou .xlsx.")
    except PermissionError:
        raise ExportError("Sem permissão para gravar neste local (o arquivo pode estar aberto em outro programa).")
    except OSError:
        raise ExportError("Não foi possível gravar o arquivo.")
    return dest


def export_workbook(sheets: dict[str, pd.DataFrame], dest: str | Path, source: str | Path | None = None) -> Path:
    dest = check_destination(dest, source)
    if dest.suffix.lower() != ".xlsx":
        raise ExportError("Use a extensão .xlsx.")
    try:
        with pd.ExcelWriter(dest, engine="openpyxl") as writer:
            for name, df in sheets.items():
                _safe_frame(df).to_excel(writer, sheet_name=name[:31], index=False)
    except PermissionError:
        raise ExportError("Sem permissão para gravar neste local (o arquivo pode estar aberto em outro programa).")
    except OSError:
        raise ExportError("Não foi possível gravar o arquivo.")
    return dest


SUMMARY_LABELS = {
    "turma": "Turma", "area": "Área", "registros": "Registros", "media": "Média", "mediana": "Mediana",
    "minimo": "Mínimo", "maximo": "Máximo", "desvio_padrao": "Desvio padrão",
    "media_geral_area": "Média geral da área", "diferenca_media_geral": "Dif. p/ média geral",
    "atencao": "Atenção", "motivo": "Motivo",
}


def display_summary(flagged: pd.DataFrame) -> pd.DataFrame:
    """Tabela do resumo com nomes de colunas em português e números arredondados."""
    out = flagged.copy()
    for c in ("media", "mediana", "minimo", "maximo", "desvio_padrao", "media_geral_area", "diferenca_media_geral"):
        if c in out:
            out[c] = out[c].round(2)
    if "atencao" in out:
        out["atencao"] = out["atencao"].map({True: "Sim", False: "Não"})
    return out.rename(columns=SUMMARY_LABELS)


def build_report_html(flagged: pd.DataFrame, criteria: AttentionCriteria, stats: OverallStats,
                      quality: QualityReport, file_name: str, generated_at: datetime | None = None) -> str:
    """Relatório agregado: não inclui ids nem dados individuais de alunos."""
    e = html.escape
    when = (generated_at or datetime.now()).strftime("%d/%m/%Y %H:%M")
    table = display_summary(flagged.drop(columns=["media_geral_area"], errors="ignore"))
    head = "".join(f"<th>{e(str(c))}</th>" for c in table.columns)
    rows = "".join("<tr>" + "".join(f"<td>{e(_cell(v))}</td>" for v in r) + "</tr>"
                   for r in table.itertuples(index=False))
    attention = flagged[flagged["atencao"]] if "atencao" in flagged else flagged.iloc[0:0]
    att_items = "".join(f"<li><b>{e(str(r.turma))}</b> ({e(str(r.area))}): {e(r.motivo)}</li>"
                        for r in attention.itertuples()) or "<li>Nenhuma turma sinalizada pelos critérios atuais.</li>"
    warns = "".join(f"<li>{e(i.message)}</li>" for i in quality.issues if i.severity != "info") \
        or "<li>Sem avisos de qualidade.</li>"
    return f"""<html><body style="font-family: sans-serif; font-size: 10pt; color: #222;">
<h1>Métricas das Turmas — Relatório de desempenho</h1>
<p>Arquivo: {e(file_name)}<br>Gerado em {when}</p>
<h2>Visão geral</h2>
<p>Turmas: {stats.n_turmas} · Registros analisados: {stats.n_records} · Valores válidos: {stats.n_values}<br>
Média geral: {format_number(stats.mean)} · Maior média entre turmas: {e(str(stats.best_turma))} ({format_number(stats.best_mean)})</p>
<h2>Resumo por turma e área</h2>
<table border="1" cellspacing="0" cellpadding="4" width="100%"><tr>{head}</tr>{rows}</table>
<h2>Turmas que necessitam de atenção</h2>
<p>{e(describe_criteria(criteria))}</p><ul>{att_items}</ul>
<h2>Qualidade dos dados</h2>
<p>Linhas lidas: {quality.rows_in} · Valores usados: {quality.values_used} de {quality.values_in}</p><ul>{warns}</ul>
</body></html>"""


def _cell(v) -> str:
    if isinstance(v, float):
        return format_number(v, 2)
    return str(v)


def write_pdf(html_text: str, dest: str | Path, source: str | Path | None = None) -> Path:
    """Gera PDF com o próprio Qt (sem dependências extras e sem rede)."""
    dest = check_destination(dest, source)
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

    writer = QPdfWriter(str(dest))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
    doc = QTextDocument()
    doc.setHtml(html_text)
    doc.print_(writer)
    return dest
