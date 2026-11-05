import pandas as pd

from src.models.analysis_result import AttentionCriteria, ColumnMapping, ValidationConfig
from src.services import analysis_service as an
from src.services import ingest_service as ig
from src.services import item_service as it
from src.services.demo_data import make_legacy_frame
from src.services.validation_service import build_clean_dataset


def test_parse_erradas():
    assert it.parse_erradas("Q1(B/C);Q12(X/A)") == [(1, "B", "C"), (12, "X", "A")]
    assert it.parse_erradas(None) == [] and it.parse_erradas("") == []


def test_gabarito_inferred_and_hard_questions_found():
    ds = ig.legacy_to_dataset(make_legacy_frame(seed=42))
    assert len(ds.gabarito) == 90
    stats = it.question_stats(ds.alunos, ds.erros, ds.gabarito)
    hard = it.hard_questions(stats)
    assert {18, 89} <= set(hard["questao"])           # as duas questões difíceis plantadas nos dados fictícios
    assert stats["taxa_erro"].between(0, 100).all()


def test_dominant_letter_alert():
    ds = ig.legacy_to_dataset(make_legacy_frame(seed=42))
    e = ds.erros.copy()
    sizes = e.groupby(it.KEY).size()
    victim = sizes.idxmax()                                          # aluno com mais erros listados
    assert sizes.max() >= it.MIN_DOMINANT_ERRORS
    mask = (e.turma == victim[0]) & (e.id_aluno == victim[1]) & (e.simulado == victim[2])
    e.loc[mask, "marcada"] = "C"                                     # todos os erros na mesma letra
    alerts = it.student_alerts(ds.alunos, e, ds.gabarito)
    assert ((alerts.id_aluno == victim[1]) & alerts.tipo.str.startswith("Mesma")).any()


def test_attendance_table():
    ds = ig.legacy_to_dataset(make_legacy_frame(seed=42))
    att = an.attendance_table(ds.alunos)
    assert (att["matriculados"] == att["presentes"] + att["ausentes"]).all()
    assert att["presenca_pct"].between(0, 100).all()


def _long(means, n, sd=3.0, seed=0):
    import numpy as np
    rng = np.random.default_rng(seed)
    rows = [(t, "Linguagens", float(v)) for t, m in means.items() for v in rng.normal(m, sd, n[t])]
    return pd.DataFrame(rows, columns=["turma", "area", "valor"])


def test_small_sample_not_flagged():
    long = _long({"A": 70, "B": 70, "C": 40}, {"A": 30, "B": 30, "C": 4})
    f = an.flag_attention(long, AttentionCriteria(below_overall_by=5, min_records=10))
    c = f[f.turma == "C"].iloc[0]
    assert not c.atencao and "Amostra pequena" in c.motivo


def test_significance_required():
    long = _long({"A": 70, "B": 70, "C": 60}, {"A": 30, "B": 30, "C": 30}, sd=3)
    strict = an.flag_attention(long, AttentionCriteria(below_overall_by=3, min_records=10, require_significance=True))
    assert strict[strict.turma == "C"].iloc[0].atencao            # diferença grande e clara: sinaliza
    noisy = _long({"A": 60, "B": 60, "C": 55}, {"A": 8, "B": 8, "C": 8}, sd=20, seed=1)
    f = an.flag_attention(noisy, AttentionCriteria(below_overall_by=2, min_records=5, require_significance=True))
    assert not f.atencao.any()                                     # diferença dentro do ruído: não sinaliza
    f2 = an.flag_attention(noisy, AttentionCriteria(below_overall_by=2, min_records=5, require_significance=False))
    assert f2.atencao.any()


def test_presence_column_and_zero_as_absent():
    df = pd.DataFrame({"turma": ["A"] * 4, "nota": ["80", "0", "60", "0"], "presente": ["SIM", "NAO", "SIM", "SIM"]})
    m = ColumnMapping("turma", ("nota",), presence_column="presente")
    long, rep = build_clean_dataset(df, m)
    assert len(long) == 3 and rep.n_absent == 1                    # o 0 de quem está SIM continua sendo nota real
    m2 = ColumnMapping("turma", ("nota",))
    long2, rep2 = build_clean_dataset(df, m2, ValidationConfig(zero_is_absent=True))
    assert len(long2) == 2 and rep2.n_absent == 2
