import pandas as pd
import pytest

from src.services import ingest_service as ig
from src.services import item_service as it
from src.services import schema
from src.services.demo_data import make_legacy_frame
from src.services.import_service import ImportServiceError
from src.services.standard_workbook import write_standard_workbook
from src.services.validation_service import build_clean_dataset, guess_mapping
from src.models.analysis_result import ColumnMapping


def mapping_for(ds_df):
    g = guess_mapping(ds_df)
    return ColumnMapping(g["turma"], tuple(g["values"]), g["id"], g["period"], g["presence"], tuple(g["labels"].items()))


def test_detect_layouts():
    legacy = make_legacy_frame()
    assert ig.detect_layout(legacy.columns) == "legado"
    assert ig.detect_layout(schema.STANDARD_COLUMNS) == "padrao"
    assert ig.detect_layout(["turma", "id", "exatas", "humanas"]) is None


def test_legacy_conversion_and_absent_not_zero():
    legacy = make_legacy_frame()
    ds = ig.legacy_to_dataset(legacy, "S2D1 teste.xlsx")
    a = ds.alunos
    assert len(a) == len(legacy)
    absent = a[a.presente == "NAO"]
    assert len(absent) == int((legacy["Respostas"] == 0).sum()) > 0
    assert absent[["pct_linguagens", "pct_humanas", "pct_total"]].isna().all().all()
    assert (a.simulado == "S2D1").all()
    # médias sem ausentes (o bug original contava 0%)
    long, rep = build_clean_dataset(a, mapping_for(a))
    assert rep.n_absent == len(absent)
    assert long["valor"].min() >= 0 and long["valor"].mean() > 40


def test_percent_as_fraction_is_detected():
    legacy = make_legacy_frame(seed=1)
    frac = legacy.copy()
    for c in ("Percentual", "%Linguagens", "%Humanas"):
        frac[c] = legacy[c].str.replace("%", "").str.replace(",", ".").astype(float) / 100
    a1, a2 = ig.legacy_to_dataset(legacy).alunos, ig.legacy_to_dataset(frac).alunos
    pd.testing.assert_frame_equal(a1, a2)


def test_truncated_error_list_is_flagged_and_excluded_from_ranking():
    legacy = make_legacy_frame(seed=3, truncate_at=10)
    ds = ig.legacy_to_dataset(legacy)
    assert any("incompleta" in n for n in ds.notes)
    comp = it.completeness(ds.alunos, ds.erros)
    assert (~comp["completo"]).sum() > 0
    stats = it.question_stats(ds.alunos, ds.erros, ds.gabarito, turmas=None)
    full = it.question_stats(*(lambda d: (d.alunos, d.erros, d.gabarito))(ig.legacy_to_dataset(make_legacy_frame(seed=3))))
    assert stats.empty or stats["base"].iloc[0] < full["base"].iloc[0]


def test_inconsistent_percent_is_recalculated():
    legacy = make_legacy_frame(seed=5)
    i = legacy.index[legacy["Respostas"] > 0][0]
    legacy.loc[i, "Percentual"] = "99,00%"
    a = ig.legacy_to_dataset(legacy).alunos
    assert "inconsistente" in a.loc[i, "observacao"]
    assert a.loc[i, "pct_total"] == round(a.loc[i, "acertos_total"] / 90 * 100, 2)


def test_standard_workbook_roundtrip(tmp_path):
    ds = ig.legacy_to_dataset(make_legacy_frame(seed=7), "S1D1.xlsx")
    path = write_standard_workbook(tmp_path / "padrao.xlsx", ds)
    back = ig.try_load_dataset(path)
    assert back.layout == "padrao"
    cols = ["turma", "id_aluno", "presente", "respostas", "acertos_total", "pct_total"]
    pd.testing.assert_frame_equal(ds.alunos[cols].reset_index(drop=True), back.alunos[cols].reset_index(drop=True))
    assert back.gabarito == ds.gabarito
    assert len(back.erros) == len(ds.erros)


def test_empty_template_is_rejected(tmp_path):
    path = write_standard_workbook(tmp_path / "modelo.xlsx")
    with pytest.raises(ImportServiceError):
        ig.try_load_dataset(path)


def test_standard_rules_absent_with_score_and_out_of_range():
    raw = pd.DataFrame({
        "turma": ["A", "A", "A", "A"], "id_aluno": [1, 2, 3, 4], "presente": ["SIM", "NAO", "SIM", "SIM"],
        "respostas": [90, 90, 90, 90], "acertos_linguagens": [30, 40, 99, 20], "acertos_humanas": [30, 40, 10, 20]})
    a, notes = ig.standardize_alunos(raw)
    assert a.loc[1, "pct_total"] != a.loc[1, "pct_total"]         # NaN: ausente com nota -> ignorada
    assert pd.isna(a.loc[2, "pct_linguagens"])                     # 99 > 45 -> inválido
    assert any("ausentes" in n for n in notes) and any("inválido" in n for n in notes)


def test_guess_mapping_does_not_offer_counts_as_scores():
    df = pd.DataFrame({"TURMA": ["A"], "Respostas": [90], "Acertos": [69], "Percentual": ["76,67%"]})
    assert guess_mapping(df)["values"] == ["Percentual"]


def test_formula_injection_is_neutralized(tmp_path):
    raw = pd.DataFrame({"turma": ["=CMD()"], "id_aluno": [1], "presente": ["SIM"], "respostas": [90],
                        "acertos_linguagens": [10], "acertos_humanas": [10]})
    a, _ = ig.standardize_alunos(raw)
    from src.models.dataset import Dataset
    path = write_standard_workbook(tmp_path / "x.xlsx", Dataset(alunos=a))
    from openpyxl import load_workbook
    cell = load_workbook(path)["Alunos"]["A2"]
    assert not str(cell.value).startswith("=")
