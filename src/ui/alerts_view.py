"""Tela "Alertas": o que merece conferência antes de confiar nos números.

Mostra IDs de alunos na tela (dados ficam só neste computador). O relatório em PDF NÃO inclui IDs.
"""
from __future__ import annotations

import html

import pandas as pd
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget

from src.models.dataset import Dataset
from src.models.session import Session
from src.services import item_service


def build_alerts_html(dataset: Dataset, quality_issues: list[str] | None = None) -> str:
    e = html.escape
    parts = ["<h2>Alertas e conferências</h2>",
             "<p>Estes itens <b>não</b> são julgamentos sobre alunos ou turmas: são pontos para conferir "
             "o cartão-resposta, o gabarito ou a exportação antes de tirar conclusões.</p>"]

    notes = [n for n in dataset.notes if not n.startswith("Layout reconhecido")]
    notes += quality_issues or []
    parts.append("<h3>Qualidade da importação</h3>")
    parts.append("<ul>" + "".join(f"<li>{e(n)}</li>" for n in notes) + "</ul>" if notes
                 else "<p>Nenhum problema na importação.</p>")

    alerts = item_service.student_alerts(dataset.alunos, dataset.erros, dataset.gabarito, dataset.n_questoes)
    parts.append("<h3>Alunos para conferir o cartão</h3>")
    if alerts.empty:
        parts.append("<p>Nenhum aluno sinalizado.</p>")
    else:
        rows = "".join(f"<tr><td>{e(str(r.turma))}</td><td>{e(str(r.id_aluno))}</td><td>{e(r.tipo)}</td>"
                       f"<td>{e(r.detalhe)}</td></tr>" for r in alerts.itertuples())
        parts.append('<table border="1" cellspacing="0" cellpadding="4"><tr><th>Turma</th><th>ID</th>'
                     f"<th>Tipo</th><th>Detalhe</th></tr>{rows}</table>")

    parts.append("<h3>Questões com taxa de erro alta</h3>")
    if not dataset.has_items:
        parts.append("<p>A planilha não traz a lista de questões erradas (aba Erros); análise por questão indisponível.</p>")
    else:
        stats = item_service.question_stats(dataset.alunos, dataset.erros, dataset.gabarito, dataset.n_linguagens,
                                            dataset.n_questoes, dataset.anuladas)
        hard = item_service.hard_questions(stats)
        if hard.empty:
            parts.append(f"<p>Nenhuma questão com {item_service.HARD_QUESTION_RATE:.0f}% ou mais de erro.</p>")
        else:
            rows = "".join(
                f"<tr><td>Q{int(r.questao)}</td><td>{e(r.area)}</td><td>{e(str(r.gabarito or '—'))}</td>"
                f"<td>{r.taxa_erro:.1f}%</td><td>{e(str(r.alt_errada or '—'))}</td></tr>" for r in hard.itertuples())
            parts.append(f"<p>Base: {int(hard['base'].iloc[0])} alunos presentes com lista de erros completa. "
                         "Taxa muito alta pode indicar questão difícil, <b>erro de gabarito</b> ou necessidade de anulação.</p>"
                         '<table border="1" cellspacing="0" cellpadding="4"><tr><th>Questão</th><th>Área</th>'
                         f"<th>Gabarito</th><th>Erro</th><th>Errada mais marcada</th></tr>{rows}</table>")
    return "".join(parts)


class AlertsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.empty = QLabel("Nenhum arquivo carregado. Use “Importar planilha” para começar.")
        self.empty.setObjectName("muted")
        self.browser = QTextBrowser()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(self.empty)
        lay.addWidget(self.browser, 1)
        self.set_session(None)

    def set_session(self, session: Session | None) -> None:
        has = session is not None
        self.empty.setVisible(not has)
        self.browser.setVisible(has)
        if not has:
            return
        if session.dataset is None:
            self.browser.setHtml("<p>Alertas por aluno e por questão só estão disponíveis para planilhas no padrão "
                                 "do projeto ou na exportação do sistema de correção.</p>"
                                 "<p>Resumo da importação:</p><ul>" +
                                 "".join(f"<li>{html.escape(i.message)}</li>" for i in session.quality.issues) + "</ul>")
        else:
            self.browser.setHtml(build_alerts_html(session.dataset))
