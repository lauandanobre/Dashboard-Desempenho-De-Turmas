"""Leitura de planilhas (.xlsx, .xls, .ods, .csv, .txt) com pandas.

- Nunca modifica o arquivo de origem (só abre para leitura).
- Não executa fórmulas nem macros: o openpyxl lê apenas os valores já
  calculados e armazenados na planilha (data_only), e macros nunca são executadas.
- Todas as mensagens de erro (ImportServiceError) são em português e prontas
  para exibir ao usuário.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

import pandas as pd

from src.models.analysis_result import ImportedTable

logger = logging.getLogger(__name__)

EXCEL_ENGINES = {".xlsx": "openpyxl", ".xls": "xlrd", ".ods": "odf"}
TEXT_EXTENSIONS = {".csv", ".txt"}
SUPPORTED_EXTENSIONS = frozenset(EXCEL_ENGINES) | TEXT_EXTENSIONS
ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
DELIMITERS = (";", ",", "\t", "|")
_SAMPLE_BYTES = 64 * 1024


class ImportServiceError(Exception):
    """Erro de importação com mensagem compreensível para o usuário."""


def check_file(path: str | Path) -> Path:
    path = Path(path)
    if not path.exists():
        raise ImportServiceError("O arquivo selecionado não foi encontrado. Ele pode ter sido movido ou apagado.")
    if not path.is_file():
        raise ImportServiceError("O caminho selecionado não é um arquivo.")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ImportServiceError(
            f"Formato '{path.suffix or '(sem extensão)'}' não suportado. "
            "Use .xlsx, .xls, .ods, .csv ou .txt."
        )
    try:
        if path.stat().st_size == 0:
            raise ImportServiceError("O arquivo está vazio.")
        with path.open("rb") as fh:
            fh.read(1)
    except PermissionError:
        raise ImportServiceError("Sem permissão para ler o arquivo. Feche-o em outros programas ou verifique as permissões.")
    except OSError:
        raise ImportServiceError("Não foi possível ler o arquivo.")
    return path


def list_sheets(path: str | Path) -> list[str]:
    """Nomes das abas (lista vazia para CSV/TXT)."""
    path = check_file(path)
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return []
    try:
        with pd.ExcelFile(path, engine=EXCEL_ENGINES[ext]) as xls:
            return [str(n) for n in xls.sheet_names]
    except ImportError:
        raise _missing_engine(ext)
    except Exception as exc:
        logger.warning("Falha ao listar abas (%s): %s", ext, type(exc).__name__)
        raise _corrupted(ext)


def detect_delimiter(path: str | Path) -> str:
    """Escolhe o separador cujo número de colunas é mais consistente nas primeiras linhas."""
    with Path(path).open("rb") as fh:
        raw = fh.read(_SAMPLE_BYTES)
    text = raw.decode("latin-1")  # separadores são ASCII; qualquer decodificação serve aqui
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(raw) == _SAMPLE_BYTES and len(lines) > 1:
        lines = lines[:-1]  # última linha pode estar cortada
    lines = lines[:30]
    best, best_score = ";", (-1.0, 0)
    for delim in DELIMITERS:
        try:
            counts = [len(row) - 1 for row in csv.reader(lines, delimiter=delim)]
        except csv.Error:
            continue
        if not counts:
            continue
        mode = max(set(counts), key=counts.count)
        if mode <= 0:
            continue
        score = (counts.count(mode) / len(counts), mode)
        if score > best_score:
            best, best_score = delim, score
    return best


def read_table(path: str | Path, sheet: str | None = None, nrows: int | None = None) -> ImportedTable:
    """Lê a planilha como texto/valores brutos (a conversão numérica é feita na validação)."""
    path = check_file(path)
    ext = path.suffix.lower()
    notes: list[str] = []
    encoding = delimiter = None

    if ext in TEXT_EXTENSIONS:
        df, encoding, delimiter = _read_text(path, nrows)
    else:
        df = _read_excel(path, ext, sheet, nrows)

    if df.shape[1] == 0 or df.empty:
        raise ImportServiceError("A planilha não contém dados (nenhuma linha abaixo do cabeçalho).")

    df = df.apply(lambda col: col.map(_clean_cell))
    df.columns, header_notes = normalize_headers(list(df.columns))
    notes.extend(header_notes)

    empty_cols = [c for c in df.columns if df[c].isna().all() and str(c).startswith("Coluna ")]
    if empty_cols:
        df = df.drop(columns=empty_cols)
        notes.append(f"{len(empty_cols)} coluna(s) sem cabeçalho e sem dados foram ignoradas.")
    empty_rows = df.isna().all(axis=1)
    if empty_rows.any():
        notes.append(f"{int(empty_rows.sum())} linha(s) totalmente vazias foram ignoradas.")
        df = df[~empty_rows]  # mantém o índice original: linha da planilha = índice + 2
    if df.empty:
        raise ImportServiceError("A planilha não contém dados (todas as linhas estão vazias).")

    logger.info("Importação concluída: ext=%s linhas=%d colunas=%d", ext, len(df), df.shape[1])
    return ImportedTable(df=df, file_name=path.name, sheet=sheet, encoding=encoding,
                         delimiter=delimiter, notes=notes)


def normalize_headers(columns: list) -> tuple[list[str], list[str]]:
    """Trata cabeçalhos vazios e duplicados, devolvendo (nomes, avisos)."""
    notes: list[str] = []
    result: list[str] = []
    seen: dict[str, int] = {}
    for i, col in enumerate(columns, start=1):
        name = "" if col is None else str(col).strip()
        if name == "" or name.lower().startswith("unnamed:") or name.lower() == "nan":
            new = f"Coluna {i}"
            notes.append(f"Cabeçalho vazio na coluna {i}: renomeado para '{new}'.")
            name = new
        if name in seen:
            seen[name] += 1
            new = f"{name} ({seen[name]})"
            notes.append(f"Cabeçalho duplicado '{name}': a repetição foi renomeada para '{new}'.")
            result.append(new)
        else:
            seen[name] = 1
            result.append(name)
    return result, notes


def _clean_cell(value):
    if isinstance(value, str):
        value = value.strip()
        return None if value == "" else value
    return value


def _read_text(path: Path, nrows: int | None):
    delimiter = detect_delimiter(path)
    for enc in ENCODINGS:
        try:
            df = pd.read_csv(path, sep=delimiter, encoding=enc, dtype=str, keep_default_na=False,
                             na_values=[""], skipinitialspace=True, nrows=nrows, on_bad_lines="error")
            return df, enc, delimiter
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            raise ImportServiceError("O arquivo está vazio.")
        except pd.errors.ParserError:
            raise ImportServiceError(
                "Há linhas com número de colunas diferente do cabeçalho. "
                "Verifique o separador e se algum texto contém o separador sem estar entre aspas."
            )
        except OSError:
            raise ImportServiceError("Não foi possível ler o arquivo.")
    raise ImportServiceError("Não foi possível identificar a codificação do arquivo.")


def _read_excel(path: Path, ext: str, sheet: str | None, nrows: int | None) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet if sheet is not None else 0,
                             engine=EXCEL_ENGINES[ext], dtype=object, nrows=nrows)
    except ImportError:
        raise _missing_engine(ext)
    except ValueError as exc:
        if "Worksheet" in str(exc) or "sheet" in str(exc).lower():
            raise ImportServiceError(f"A aba '{sheet}' não foi encontrada no arquivo.")
        logger.warning("Falha de leitura (%s): ValueError", ext)
        raise _corrupted(ext)
    except Exception as exc:
        logger.warning("Falha de leitura (%s): %s", ext, type(exc).__name__)
        raise _corrupted(ext)


def _missing_engine(ext: str) -> ImportServiceError:
    return ImportServiceError(
        f"Falta uma biblioteca para ler arquivos '{ext}' ({EXCEL_ENGINES[ext]}). "
        "Execute: pip install -r requirements.txt"
    )


def _corrupted(ext: str) -> ImportServiceError:
    return ImportServiceError(
        f"Não foi possível abrir o arquivo '{ext}'. Ele pode estar corrompido, "
        "protegido por senha ou em formato incompatível."
    )
