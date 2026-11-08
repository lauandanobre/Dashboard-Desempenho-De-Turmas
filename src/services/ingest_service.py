"""Converte qualquer layout reconhecido para o PADRÃO do projeto (Dataset).

Layouts aceitos:
1. "padrao" — pasta de trabalho do modelo (abas Alunos / Gabarito / Erros / Config) ou uma única
   tabela com as colunas de schema.STANDARD_COLUMNS (ex.: CSV).
2. "legado" — exportação do sistema de correção: ID, TURMA, Respostas, Acertos, Percentual,
   %Linguagens, %Humanas, Questões Erradas ("Q1(B/C)" = marcou B, correta C).
3. Qualquer outro formato continua funcionando pelo fluxo genérico (mapeamento manual de colunas).

Princípio: nada é descartado em silêncio. Tudo que foi corrigido/ignorado vira uma nota
em português, mostrada ao usuário na importação.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from src.models.analysis_result import ImportedTable
from src.models.dataset import Dataset
from src.services import import_service, item_service, schema
from src.services.import_service import ImportServiceError
from src.services.validation_service import _clean_label, is_missing, norm_text, parse_number

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ utilidades
def _to_int(value) -> int | None:
    n = parse_number(value)
    if n is None:
        return None
    r = round(n)
    return int(r) if abs(n - r) < 1e-6 else None


def _header_key(name) -> str:
    return norm_text(name).replace(" ", "_")


def _strip_cell(value):
    if isinstance(value, str):
        value = value.strip()
        return None if value == "" else value
    return value


def guess_simulado(file_name: str) -> str:
    """'s2d1 - epufabc 2026.pdf' -> 'S2D1' (vazio se o nome não seguir o padrão S#D#)."""
    m = re.search(r"(?<![a-z0-9])s\d+d\d+(?![a-z0-9])", file_name, flags=re.IGNORECASE)
    return m.group(0).upper() if m else ""


def legacy_columns(columns) -> dict[str, str] | None:
    """{papel: nome original da coluna} se o cabeçalho for o da exportação do sistema."""
    roles: dict[str, str] = {}
    for col in columns:
        role = schema.LEGACY_KEYS.get(norm_text(col))
        if role and role not in roles:
            roles[role] = col
    return roles if schema.LEGACY_REQUIRED <= set(roles) else None


def detect_layout(columns) -> str | None:
    keys = {_header_key(c) for c in columns}
    if set(schema.REQUIRED_COLUMNS) <= keys:
        return "padrao"
    if legacy_columns(columns):
        return "legado"
    return None


def _percent_values(series: pd.Series) -> pd.Series:
    """Converte a coluna em % (0-100). Se vier em fração (Excel com formato %), multiplica por 100."""
    vals = pd.to_numeric(series.map(parse_number), errors="coerce")
    present = vals.dropna()
    if not present.empty and present.max() <= 1.0 and (present % 1 != 0).any():
        vals = vals * 100
    return vals


# ------------------------------------------------------------------ padronização da aba Alunos
def standardize_alunos(raw: pd.DataFrame, n_ling: int = schema.N_LINGUAGENS,
                       n_hum: int = schema.N_HUMANAS) -> tuple[pd.DataFrame, list[str]]:
    """Valida e completa a tabela de alunos. Recalcula totais e porcentagens (não confia em fórmulas
    sem valor gravado). Ausente = notas em branco, nunca 0."""
    notes: list[str] = []
    n_total = n_ling + n_hum
    col = lambda name: raw[name] if name in raw.columns else pd.Series([None] * len(raw), index=raw.index)  # noqa: E731

    df = pd.DataFrame(index=raw.index)
    df["turma"] = col("turma").map(_clean_label)
    df["id_aluno"] = col("id_aluno").map(_clean_label)
    df["simulado"] = col("simulado").map(_clean_label).fillna("")
    no_turma = df["turma"].isna()
    if no_turma.any():
        notes.append(f"{int(no_turma.sum())} linha(s) sem turma foram ignoradas.")
    keep = ~no_turma
    df, raw = df[keep], raw[keep]
    col = lambda name: raw[name] if name in raw.columns else pd.Series([None] * len(raw), index=raw.index)  # noqa: E731

    resp, al, ah = col("respostas").map(_to_int), col("acertos_linguagens").map(_to_int), col("acertos_humanas").map(_to_int)
    for name, ser, lim in (("respostas", resp, n_total), ("acertos_linguagens", al, n_ling),
                           ("acertos_humanas", ah, n_hum)):
        raw_has = col(name).map(lambda v: not is_missing(v))
        bad = raw_has & (ser.isna() | (ser < 0) | (ser > lim))
        if bad.any():
            notes.append(f"Coluna '{name}': {int(bad.sum())} valor(es) inválido(s) (esperado inteiro de 0 a {lim}) foram ignorados.")
            ser[bad] = None

    def parse_presence(v):
        if is_missing(v):
            return None
        t = norm_text(v).upper()
        return "SIM" if t in schema.PRESENT_TOKENS else "NAO" if t in schema.ABSENT_TOKENS else "?"

    pres = col("presente").map(parse_presence)
    invalid = pres == "?"
    if invalid.any():
        notes.append(f"Coluna 'presente': {int(invalid.sum())} valor(es) diferentes de SIM/NAO foram "
                     "interpretados pelas notas (com nota = presente).")
    infer = pres.isna() | invalid
    has_any = resp.notna() & (resp > 0) | al.notna() | ah.notna()
    pres = pres.mask(infer, has_any.map({True: "SIM", False: "NAO"}))
    if infer.any() and not invalid.any():
        notes.append(f"{int(infer.sum())} linha(s) sem 'presente': presença deduzida das notas.")

    zero_resp = (pres == "SIM") & (resp == 0)
    if zero_resp.any():
        notes.append(f"{int(zero_resp.sum())} aluno(s) marcados como presentes têm 0 respostas: tratados como ausentes.")
        pres[zero_resp] = "NAO"
    absent = pres == "NAO"
    filled = absent & ((resp.fillna(0) > 0) | (al.fillna(0) > 0) | (ah.fillna(0) > 0))
    if filled.any():
        notes.append(f"{int(filled.sum())} aluno(s) ausentes (NAO) tinham nota preenchida: a nota foi ignorada.")
    for ser in (resp, al, ah):
        ser[absent] = None

    present = ~absent
    missing_score = present & (al.isna() | ah.isna())
    if missing_score.any():
        notes.append(f"{int(missing_score.sum())} aluno(s) presentes sem nota de Linguagens e/ou Humanas "
                     "(não entram nas médias dessa área).")

    df["presente"] = pres
    df["respostas"] = resp.astype(float)
    df["acertos_linguagens"] = al.astype(float)
    df["acertos_humanas"] = ah.astype(float)
    df["acertos_total"] = (al + ah).astype(float)
    df["pct_linguagens"] = (al / n_ling * 100).round(2).astype(float)
    df["pct_humanas"] = (ah / n_hum * 100).round(2).astype(float)
    df["pct_total"] = (df["acertos_total"] / n_total * 100).round(2)
    df["observacao"] = col("observacao").map(_clean_label)

    dup = df.duplicated(subset=item_service.KEY, keep=False) & df["id_aluno"].notna()
    if dup.any():
        notes.append(f"{int(dup.sum())} linha(s) repetem o mesmo aluno (turma + id + simulado). "
                     "Foram mantidas; confira se não há aluno duplicado.")
    return df[schema.STANDARD_COLUMNS], notes


# ------------------------------------------------------------------ layout legado
def legacy_to_dataset(df: pd.DataFrame, file_name: str = "", n_ling: int = schema.N_LINGUAGENS,
                      n_hum: int = schema.N_HUMANAS) -> Dataset:
    roles = legacy_columns(df.columns)
    if roles is None:
        raise ImportServiceError("A planilha não tem as colunas do sistema de correção "
                                 "(ID, TURMA, Respostas, Acertos, %Linguagens, %Humanas, Questões Erradas).")
    n_total = n_ling + n_hum
    pct_l, pct_h = _percent_values(df[roles["pct_linguagens"]]), _percent_values(df[roles["pct_humanas"]])
    pct_total_orig = _percent_values(df[roles["percentual"]]) if "percentual" in roles else pd.Series(
        [None] * len(df), index=df.index, dtype=float)
    resp = df[roles["respostas"]].map(_to_int)
    acertos = df[roles["acertos"]].map(_to_int)
    present = resp.fillna(0) > 0

    al = (pct_l * n_ling / 100).round()
    ah = (acertos - al).where(acertos.notna(), (pct_h * n_hum / 100).round())
    obs = pd.Series([None] * len(df), index=df.index, dtype=object)
    sys_ah = pct_h * n_hum / 100
    calc_pct = acertos / n_total * 100
    inconsistent = present & (((pct_total_orig - calc_pct).abs() > 0.05) | ((ah - sys_ah).abs() > 0.6))
    for i in df.index[inconsistent]:
        obs[i] = (f"Percentual do sistema ({pct_total_orig[i]:.2f}%) inconsistente com {int(acertos[i])} acertos; "
                  f"recalculado ({calc_pct[i]:.2f}%).")

    raw = pd.DataFrame({
        "turma": df[roles["turma"]], "id_aluno": df[roles["id"]],
        "simulado": guess_simulado(file_name) or None,
        "presente": present.map({True: "SIM", False: "NAO"}),
        "respostas": resp, "acertos_linguagens": al.where(present), "acertos_humanas": ah.where(present),
        "observacao": obs}, index=df.index)
    alunos, notes = standardize_alunos(raw, n_ling, n_hum)

    erros = item_service.erros_from_text(alunos[item_service.KEY], df.loc[alunos.index, roles["erradas"]])
    gabarito, conflicts = item_service.infer_gabarito(erros)
    erros["correta"] = erros["questao"].map(gabarito)
    comp = item_service.completeness(alunos, erros)
    incomplete = comp[~comp["completo"]]
    if not incomplete.empty:
        for r in incomplete.itertuples():
            msg = f"Lista de erros incompleta ({r.registrado} de {int(r.esperado) if pd.notna(r.esperado) else '?'})."
            m = (alunos["turma"] == r.turma) & (alunos["id_aluno"] == r.id_aluno) & (alunos["simulado"] == r.simulado)
            alunos.loc[m, "observacao"] = alunos.loc[m, "observacao"].map(lambda o: msg if is_missing(o) else f"{o} {msg}")
        notes.append(f"{len(incomplete)} de {len(comp)} alunos presentes têm a lista de questões erradas incompleta "
                     "(provável corte da exportação, comum em PDF). Eles ficam fora do ranking de questões; "
                     "exporte a planilha em .xlsx para ter a lista inteira.")
    if conflicts:
        notes.append("Gabarito deduzido com conflito nas questões: " + ", ".join(map(str, conflicts)) + ".")
    missing_q = sorted(set(range(1, n_total + 1)) - set(gabarito))
    if missing_q:
        notes.append(f"Gabarito não deduzido para {len(missing_q)} questão(ões) (ninguém errou): "
                     + ", ".join(map(str, missing_q[:10])) + ("…" if len(missing_q) > 10 else "") + ".")

    sim = guess_simulado(file_name)
    head = "Layout reconhecido: exportação do sistema de correção (convertida para o padrão do projeto)."
    if sim:
        head += f" Simulado identificado pelo nome do arquivo: {sim}."
    return Dataset(alunos=alunos.reset_index(drop=True), erros=erros, gabarito=gabarito or None, layout="legado",
                   n_linguagens=n_ling, n_humanas=n_hum, notes=[head, *notes])


# ------------------------------------------------------------------ layout padrão
def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [_header_key(c) for c in out.columns]
    out = out.apply(lambda c: c.map(_strip_cell))
    content = [c for c in out.columns if c not in schema.FORMULA_COLUMNS]   # fórmulas não contam como "conteúdo"
    return out[~out[content].isna().all(axis=1)]


def _drop_examples(df: pd.DataFrame, notes: list[str], sheet: str) -> pd.DataFrame:
    tag = schema.EXAMPLE_TAG
    is_ex = pd.Series(False, index=df.index)
    for c in ("turma", "observacao"):
        if c in df:
            is_ex |= df[c].map(lambda v: isinstance(v, str) and v.strip().upper().startswith(tag))
    if is_ex.any():
        notes.append(f"Aba {sheet}: {int(is_ex.sum())} linha(s) de exemplo do modelo foram ignoradas.")
    return df[~is_ex]


def _require_students(alunos: pd.DataFrame) -> None:
    if alunos.empty:
        raise ImportServiceError("Nenhum aluno encontrado na aba 'Alunos'. Preencha a planilha "
                                 "(a linha amarela de exemplo é ignorada).")


def dataset_from_standard_df(df: pd.DataFrame, n_ling: int = schema.N_LINGUAGENS,
                             n_hum: int = schema.N_HUMANAS) -> Dataset:
    clean = _drop_examples(_clean_frame(df), [], schema.SHEET_ALUNOS)
    missing = [c for c in schema.REQUIRED_COLUMNS if c not in clean.columns]
    if missing:
        raise ImportServiceError("Faltam colunas obrigatórias: " + ", ".join(missing) +
                                 ". Use o modelo assets/modelo_planilha_turmas.xlsx.")
    alunos, notes = standardize_alunos(clean, n_ling, n_hum)
    _require_students(alunos)
    return Dataset(alunos=alunos.reset_index(drop=True), layout="padrao", n_linguagens=n_ling, n_humanas=n_hum,
                   notes=["Layout reconhecido: padrão do projeto.", *notes])


def read_standard_workbook(path: str | Path) -> Dataset:
    path = import_service.check_file(path)
    ext = path.suffix.lower()
    if ext not in import_service.EXCEL_ENGINES:
        raise ImportServiceError("A pasta de trabalho padrão precisa ser .xlsx, .xls ou .ods.")
    notes: list[str] = []
    try:
        with pd.ExcelFile(path, engine=import_service.EXCEL_ENGINES[ext]) as xls:
            names = {n.strip().lower(): n for n in xls.sheet_names}
            if schema.SHEET_ALUNOS.lower() not in names:
                raise ImportServiceError(f"A planilha não tem a aba '{schema.SHEET_ALUNOS}'.")
            read = lambda key: xls.parse(names[key], dtype=object) if key in names else None  # noqa: E731
            alunos_raw = read(schema.SHEET_ALUNOS.lower())
            gab_raw = read(schema.SHEET_GABARITO.lower())
            erros_raw = read(schema.SHEET_ERROS.lower())
            cfg_raw = read(schema.SHEET_CONFIG.lower())
    except ImportServiceError:
        raise
    except ImportError:
        raise import_service._missing_engine(ext)
    except Exception as exc:
        logger.warning("Falha ao ler pasta de trabalho padrão: %s", type(exc).__name__)
        raise import_service._corrupted(ext)

    n_ling, n_hum = schema.N_LINGUAGENS, schema.N_HUMANAS
    if cfg_raw is not None and cfg_raw.shape[1] >= 2:
        cfg = {_header_key(k): _to_int(v) for k, v in zip(cfg_raw.iloc[:, 0], cfg_raw.iloc[:, 1]) if not is_missing(k)}
        n_ling = cfg.get("questoes_linguagens") or n_ling
        n_hum = cfg.get("questoes_humanas") or n_hum

    alunos_clean = _drop_examples(_clean_frame(alunos_raw), notes, schema.SHEET_ALUNOS)
    missing = [c for c in schema.REQUIRED_COLUMNS if c not in alunos_clean.columns]
    if missing:
        raise ImportServiceError("A aba 'Alunos' não tem as colunas obrigatórias: " + ", ".join(missing) +
                                 ". Use o modelo assets/modelo_planilha_turmas.xlsx e não renomeie as colunas.")
    alunos, std_notes = standardize_alunos(alunos_clean, n_ling, n_hum)
    _require_students(alunos)
    notes += std_notes

    gabarito, anuladas = None, set()
    if gab_raw is not None:
        g = _clean_frame(gab_raw)
        if {"questao", "resposta_correta"} <= set(g.columns):
            gab = {}
            for _, r in g.iterrows():
                q, letter = _to_int(r["questao"]), r["resposta_correta"]
                if q and isinstance(letter, str) and letter.strip().upper() in item_service.LETTERS:
                    gab[q] = letter.strip().upper()
                    if "anulada" in g and isinstance(r["anulada"], str) and norm_text(r["anulada"]) in ("sim", "s"):
                        anuladas.add(q)
            gabarito = gab or None
    erros = None
    if erros_raw is not None:
        e = _drop_examples(_clean_frame(erros_raw), notes, schema.SHEET_ERROS)
        if {"turma", "id_aluno", "questao", "marcada"} <= set(e.columns) and not e.empty:
            e = e.assign(turma=e["turma"].map(_clean_label), id_aluno=e["id_aluno"].map(_clean_label),
                         simulado=(e["simulado"].map(_clean_label) if "simulado" in e else None),
                         questao=e["questao"].map(_to_int),
                         marcada=e["marcada"].map(lambda v: str(v).strip().upper()[:1] if not is_missing(v) else None))
            e["simulado"] = e["simulado"].fillna("") if "simulado" in e else ""
            bad = e["questao"].isna() | ~e["marcada"].isin([*item_service.LETTERS, "X"])
            if bad.any():
                notes.append(f"Aba Erros: {int(bad.sum())} linha(s) com questão/alternativa inválida foram ignoradas.")
            e = e[~bad].copy()
            e["correta"] = e["questao"].map(gabarito or {})
            erros = e[[*schema.ERROS_COLUMNS, "correta"]].reset_index(drop=True)
            comp = item_service.completeness(alunos, erros)
            inc = int((~comp["completo"]).sum())
            if inc:
                notes.append(f"{inc} de {len(comp)} alunos presentes têm lista de erros incompleta na aba Erros "
                             "(ficam fora do ranking de questões).")
            if not gabarito:
                notes.append("Aba Gabarito vazia: o ranking de questões não mostrará a alternativa correta.")
    if anuladas:
        notes.append("Questões anuladas (fora do ranking): " + ", ".join(map(str, sorted(anuladas))) + ".")
    return Dataset(alunos=alunos.reset_index(drop=True), erros=erros, gabarito=gabarito, layout="padrao",
                   n_linguagens=n_ling, n_humanas=n_hum, anuladas=anuladas,
                   notes=["Layout reconhecido: padrão do projeto.", *notes])


# ------------------------------------------------------------------ ponto de entrada
def try_load_dataset(path: str | Path, table: ImportedTable | None = None) -> Dataset | None:
    """Dataset padronizado se o arquivo tiver um layout conhecido; None => fluxo genérico."""
    path = Path(path)
    if path.suffix.lower() in import_service.EXCEL_ENGINES:
        sheets = import_service.list_sheets(path)
        if schema.SHEET_ALUNOS.lower() in {s.strip().lower() for s in sheets}:
            return read_standard_workbook(path)
    if table is None:
        table = import_service.read_table(path)
    layout = detect_layout(table.df.columns)
    if layout == "legado":
        return legacy_to_dataset(table.df, path.name)
    if layout == "padrao":
        return dataset_from_standard_df(table.df)
    return None
