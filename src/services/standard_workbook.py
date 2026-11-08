"""Gera a pasta de trabalho no PADRÃO do projeto (.xlsx): modelo vazio ou dados convertidos.

Abas: LEIA-ME · Alunos · Gabarito · Config · Erros.
Em "Alunos" só as colunas azuis são digitadas; as cinzas são fórmulas (total e porcentagens),
calculadas a partir da aba Config — assim as porcentagens nunca ficam inconsistentes entre si.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from src.models.dataset import Dataset
from src.services import schema
from src.services.export_service import ExportError, _sanitize, check_destination

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
CALC_FILL = PatternFill("solid", fgColor="F2F2F2")
EXAMPLE_FILL = PatternFill("solid", fgColor="FFF2CC")
_THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
F_HDR = Font(name=FONT, bold=True, color="FFFFFF")
F_IN = Font(name=FONT, color="0000FF")          # azul = digitar
F_CALC = Font(name=FONT, color="000000")        # preto = fórmula

COL_WIDTH = {"turma": 14, "id_aluno": 10, "simulado": 12, "presente": 10, "respostas": 11,
             "acertos_linguagens": 18, "acertos_humanas": 16, "acertos_total": 13,
             "pct_linguagens": 15, "pct_humanas": 13, "pct_total": 11, "observacao": 48}
COL_HELP = {
    "turma": "Código da turma, sempre escrito igual (ex.: T1NOTSA).",
    "id_aluno": "Número do aluno. Único dentro da turma + simulado. Sem nome (LGPD).",
    "simulado": "Rótulo da prova (ex.: S2D1). Permite comparar simulados na aba Evolução.",
    "presente": "SIM ou NAO. Ausente = NAO e notas em BRANCO (nunca 0).",
    "respostas": "Quantas questões o aluno marcou (0 a 90).",
    "acertos_linguagens": "Nº de acertos em Linguagens (inteiro de 0 a 45).",
    "acertos_humanas": "Nº de acertos em Humanas (inteiro de 0 a 45).",
    "acertos_total": "FÓRMULA: linguagens + humanas. Não digitar.",
    "pct_linguagens": "FÓRMULA: acertos ÷ nº de questões da área × 100 (0 a 100, sem %).",
    "pct_humanas": "FÓRMULA: acertos ÷ nº de questões da área × 100 (0 a 100, sem %).",
    "pct_total": "FÓRMULA: acertos totais ÷ total de questões × 100 (0 a 100, sem %).",
    "observacao": "Texto livre. O programa só exibe; não usa nos cálculos.",
}

README_LINES = [
    ("PADRÃO DE PLANILHA — DESEMPENHO DAS TURMAS", True),
    ("", False),
    ("Regras (valem para todas as planilhas do cursinho):", True),
    ("1. Uma linha = um aluno em um simulado. Cabeçalho SEMPRE na linha 1; dados a partir da linha 2.", False),
    ("2. Sem células mescladas, sem linhas em branco no meio, sem totais/médias no rodapé, sem cor como informação.", False),
    ("3. Nomes de coluna fixos (minúsculas, sem acento). Não renomear, não reordenar, não apagar colunas.", False),
    ("4. Notas = números de 0 a 100 SEM o símbolo %. (Formatar como % no Excel guarda 0,69 em vez de 69.)", False),
    ("5. Aluno ausente: presente = NAO e notas em BRANCO. Nunca digite 0: o zero entra na média e derruba a turma.", False),
    ("6. Código de turma sempre igual em todas as planilhas (T1NOTSA, T1VESPSA, T2NOTSA, T2VESPSA, VESPSBC...).", False),
    ("7. Um arquivo por simulado, nomeado AAAA-MM_simulado_S#D#.xlsx (ex.: 2026-10_simulado_S2D1.xlsx).", False),
    ("8. Nunca use PDF como fonte de dados: o PDF corta a coluna de questões erradas. Use .xlsx ou .csv.", False),
    ("", False),
    ("Cores:  texto AZUL = digitar  ·  fundo CINZA = fórmula (não mexer)  ·  fundo AMARELO = exemplo (apague).", False),
    ("", False),
    ("Abas:", True),
    ("Alunos (obrigatória): notas por aluno.   Gabarito: letra correta de cada questão (e se foi anulada).", False),
    ("Config: nº de questões por área (se a prova mudar, só edite aqui).", False),
    ("Erros (opcional): uma linha por questão errada. Habilita o ranking das questões mais erradas.", False),
]


def _header(ws, names, widths=None):
    for j, name in enumerate(names, 1):
        c = ws.cell(1, j, name)
        c.font, c.fill, c.border = F_HDR, HDR_FILL, BOX
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if name in COL_HELP:
            c.comment = Comment(COL_HELP[name], "Padrão")
        ws.column_dimensions[get_column_letter(j)].width = (widths or COL_WIDTH).get(name, 14)
    ws.row_dimensions[1].height = 30


def _put(ws, row, col, value, font=F_IN, fill=None):
    if isinstance(value, float) and pd.isna(value):
        value = None
    elif hasattr(value, "item"):                     # numpy -> python
        value = value.item()
    cell = ws.cell(row, col, _sanitize(value) if isinstance(value, str) else value)
    cell.font, cell.border = font, BOX
    if fill:
        cell.fill = fill
    return cell


def _sheet_alunos(ws, rows: list[dict], n_rows: int, example: bool) -> None:
    cols = schema.STANDARD_COLUMNS
    _header(ws, cols)
    idx = {c: i + 1 for i, c in enumerate(cols)}
    L = lambda c: get_column_letter(idx[c])           # noqa: E731
    for i in range(n_rows):
        r = i + 2
        row = rows[i] if i < len(rows) else {}
        for c in schema.INPUT_COLUMNS:
            _put(ws, r, idx[c], row.get(c), F_IN, EXAMPLE_FILL if (example and i == 0) else None)
        p = f'{L("presente")}{r}="SIM"'
        formulas = {
            "acertos_total": f'=IF({p},{L("acertos_linguagens")}{r}+{L("acertos_humanas")}{r},"")',
            "pct_linguagens": f'=IF({p},ROUND({L("acertos_linguagens")}{r}/Config!$B$2*100,2),"")',
            "pct_humanas": f'=IF({p},ROUND({L("acertos_humanas")}{r}/Config!$B$3*100,2),"")',
            "pct_total": f'=IF({p},ROUND({L("acertos_total")}{r}/(Config!$B$2+Config!$B$3)*100,2),"")',
        }
        for c, f in formulas.items():
            cell = _put(ws, r, idx[c], f, F_CALC, CALC_FILL)
            cell.number_format = "0.00" if c.startswith("pct") else "0"
    last = n_rows + 1
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{last}"
    for formula, rng, msg in (
        ('"SIM,NAO"', f'{L("presente")}2:{L("presente")}{last}', "Use SIM ou NAO."),
    ):
        dv = DataValidation(type="list", formula1=formula, allow_blank=True, showErrorMessage=True,
                            errorTitle="Valor inválido", error=msg)
        dv.add(rng)
        ws.add_data_validation(dv)
    for col, hi in (("respostas", 90), ("acertos_linguagens", 45), ("acertos_humanas", 45)):
        dv = DataValidation(type="whole", operator="between", formula1="0", formula2=str(hi), allow_blank=True,
                            showErrorMessage=True, errorTitle="Valor inválido", error=f"Inteiro de 0 a {hi}.")
        dv.add(f"{L(col)}2:{L(col)}{last}")
        ws.add_data_validation(dv)


def _sheet_gabarito(ws, gabarito: dict[int, str] | None, anuladas: set[int], n_ling: int, n_total: int) -> None:
    _header(ws, schema.GABARITO_COLUMNS, {"questao": 10, "area": 14, "resposta_correta": 18, "anulada": 10})
    for q in range(1, n_total + 1):
        vals = [q, "Linguagens" if q <= n_ling else "Humanas", (gabarito or {}).get(q), "SIM" if q in anuladas else "NAO"]
        for j, v in enumerate(vals, 1):
            _put(ws, q + 1, j, v, F_IN)
    ws.freeze_panes = "A2"
    for formula, col in (('"A,B,C,D,E"', "C"), ('"SIM,NAO"', "D")):
        dv = DataValidation(type="list", formula1=formula, allow_blank=True)
        dv.add(f"{col}2:{col}{n_total + 1}")
        ws.add_data_validation(dv)


def _sheet_config(ws, n_ling: int, n_hum: int) -> None:
    for j, name in enumerate(("parametro", "valor"), 1):
        c = ws.cell(1, j, name)
        c.font, c.fill, c.border = F_HDR, HDR_FILL, BOX
    for i, (k, v) in enumerate((("questoes_linguagens", n_ling), ("questoes_humanas", n_hum),
                                ("questao_inicial_humanas", n_ling + 1)), 2):
        _put(ws, i, 1, k, F_CALC)
        _put(ws, i, 2, v, F_IN)
    ws["A6"] = "Se a prova mudar de tamanho, edite aqui: as porcentagens da aba Alunos se atualizam sozinhas."
    ws["A6"].font = Font(name=FONT, italic=True)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 10


def _sheet_erros(ws, erros: pd.DataFrame | None, example: bool) -> None:
    _header(ws, schema.ERROS_COLUMNS, {"turma": 14, "id_aluno": 10, "simulado": 12, "questao": 10, "marcada": 10})
    ws.freeze_panes = "A2"
    if erros is not None and not erros.empty:
        for i, r in enumerate(erros[schema.ERROS_COLUMNS].itertuples(index=False), 2):
            for j, v in enumerate(r, 1):
                _put(ws, i, j, v, F_IN)
    elif example:
        for j, v in enumerate((f"{schema.EXAMPLE_TAG}", 1, "S2D1", 1, "B"), 1):
            _put(ws, 2, j, v, F_IN, EXAMPLE_FILL)


def _sheet_readme(ws, extra: list[str]) -> None:
    for i, (text, bold) in enumerate([*README_LINES, *[("", False)], *[(t, False) for t in extra]], 1):
        ws.cell(i, 1, text).font = Font(name=FONT, bold=bold, size=13 if i == 1 else 10)
    ws.column_dimensions["A"].width = 125


def _alunos_rows(alunos: pd.DataFrame) -> list[dict]:
    rows = []
    for r in alunos.to_dict("records"):
        row = {c: r.get(c) for c in schema.INPUT_COLUMNS}
        for c in ("respostas", "acertos_linguagens", "acertos_humanas"):
            v = row[c]
            row[c] = None if v is None or pd.isna(v) else int(v)
        rows.append(row)
    return rows


def write_standard_workbook(dest: str | Path, dataset: Dataset | None = None, source: str | Path | None = None,
                            template_rows: int = 400, extra_notes: list[str] | None = None) -> Path:
    """Sem `dataset`: modelo vazio (com linha de exemplo). Com `dataset`: dados convertidos."""
    dest = check_destination(dest, source)
    if dest.suffix.lower() != ".xlsx":
        raise ExportError("Use a extensão .xlsx.")
    wb = Workbook()
    n_ling, n_hum = (dataset.n_linguagens, dataset.n_humanas) if dataset else (schema.N_LINGUAGENS, schema.N_HUMANAS)
    _sheet_readme(wb.active, extra_notes or [])
    wb.active.title = schema.SHEET_README
    if dataset is None:
        example = [{"turma": "T1NOTSA", "id_aluno": 1, "simulado": "S2D1", "presente": "SIM", "respostas": 90,
                    "acertos_linguagens": 31, "acertos_humanas": 38,
                    "observacao": f"{schema.EXAMPLE_TAG} — apague esta linha"}]
        _sheet_alunos(wb.create_sheet(schema.SHEET_ALUNOS), example, template_rows, example=True)
        _sheet_gabarito(wb.create_sheet(schema.SHEET_GABARITO), None, set(), n_ling, n_ling + n_hum)
        _sheet_config(wb.create_sheet(schema.SHEET_CONFIG), n_ling, n_hum)
        _sheet_erros(wb.create_sheet(schema.SHEET_ERROS), None, example=True)
    else:
        rows = _alunos_rows(dataset.alunos)
        _sheet_alunos(wb.create_sheet(schema.SHEET_ALUNOS), rows, len(rows), example=False)
        _sheet_gabarito(wb.create_sheet(schema.SHEET_GABARITO), dataset.gabarito, dataset.anuladas, n_ling, n_ling + n_hum)
        _sheet_config(wb.create_sheet(schema.SHEET_CONFIG), n_ling, n_hum)
        _sheet_erros(wb.create_sheet(schema.SHEET_ERROS), dataset.erros, example=False)
    wb.calculation.fullCalcOnLoad = True              # Excel/LibreOffice calculam as fórmulas ao abrir
    try:
        wb.save(dest)
    except PermissionError:
        raise ExportError("Sem permissão para gravar neste local (o arquivo pode estar aberto em outro programa).")
    except OSError:
        raise ExportError("Não foi possível gravar o arquivo.")
    return dest
