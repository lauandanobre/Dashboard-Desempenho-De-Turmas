"""Tela de relatórios: resumo, atenção, diferenças, qualidade dos dados e exportações."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from src.models.analysis_result import AttentionCriteria
from src.models.session import Session
from src.services import analysis_service as an
from src.services import export_service as ex
from src.ui.data_view import PandasTableModel, make_table


class ReportsPage(QWidget):
    exported = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self._session: Session | None = None
        self._flagged = None

        self.empty = QLabel("Nenhum arquivo carregado. Use “Importar planilha” para começar.")
        self.empty.setObjectName("muted")

        # critérios configuráveis
        self.use_rel, self.use_abs = QCheckBox("Média da turma abaixo da média geral da área em pelo menos"), \
            QCheckBox("Média da turma abaixo de")
        self.rel_spin, self.abs_spin = QDoubleSpinBox(), QDoubleSpinBox()
        for spin, val in ((self.rel_spin, 5.0), (self.abs_spin, 50.0)):
            spin.setRange(0, 1e6)
            spin.setDecimals(1)
            spin.setValue(val)
        self.rel_spin.setSuffix(" ponto(s)")
        self.use_rel.setChecked(True)
        for w in (self.use_rel, self.use_abs):
            w.toggled.connect(self._criteria_changed)
        for w in (self.rel_spin, self.abs_spin):
            w.valueChanged.connect(self._criteria_changed)
        self.criteria_text = QLabel("")
        self.criteria_text.setObjectName("muted")
        self.criteria_text.setWordWrap(True)

        self.criteria_box = QGroupBox("Critérios de atenção (definidos por você; nada é aprovado ou reprovado)")
        cl = QVBoxLayout(self.criteria_box)
        r1, r2 = QHBoxLayout(), QHBoxLayout()
        r1.addWidget(self.use_rel); r1.addWidget(self.rel_spin); r1.addStretch(1)
        r2.addWidget(self.use_abs); r2.addWidget(self.abs_spin); r2.addStretch(1)
        cl.addLayout(r1); cl.addLayout(r2); cl.addWidget(self.criteria_text)

        self.summary_model, self.attention_model = PandasTableModel(), PandasTableModel()
        self.diff_model = PandasTableModel()
        self.diff_area = QComboBox()
        self.diff_area.currentIndexChanged.connect(self._fill_diff)
        self.quality_list = QListWidget()

        diff_page = QWidget()
        dl = QVBoxLayout(diff_page)
        top = QHBoxLayout()
        top.addWidget(QLabel("Área:")); top.addWidget(self.diff_area); top.addStretch(1)
        dl.addLayout(top)
        dl.addWidget(QLabel("Cada célula = média da turma da linha − média da turma da coluna."))
        dl.addWidget(make_table(self.diff_model))

        self.tabs = QTabWidget()
        self.tabs.addTab(make_table(self.summary_model), "Resumo por turma")
        self.tabs.addTab(make_table(self.attention_model), "Turmas que necessitam de atenção")
        self.tabs.addTab(diff_page, "Diferenças entre médias")
        self.tabs.addTab(self.quality_list, "Qualidade dos dados")

        b_data, b_sum, b_pdf = QPushButton("Exportar dados tratados…"), QPushButton("Exportar resumo…"), \
            QPushButton("Gerar relatório em PDF…")
        b_pdf.setObjectName("primary")
        b_data.clicked.connect(self._export_data)
        b_sum.clicked.connect(self._export_summary)
        b_pdf.clicked.connect(self._export_pdf)
        buttons = QHBoxLayout()
        for b in (b_data, b_sum, b_pdf):
            buttons.addWidget(b)
        buttons.addStretch(1)
        self.content = [self.criteria_box, self.tabs]
        self.button_row = [b_data, b_sum, b_pdf]

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(self.empty)
        lay.addWidget(self.criteria_box)
        lay.addWidget(self.tabs, 1)
        lay.addLayout(buttons)
        self.set_session(None)

    # ------------------------------------------------------------------
    def set_session(self, session: Session | None) -> None:
        self._session = session
        has = session is not None
        self.empty.setVisible(not has)
        for w in (*self.content, *self.button_row):
            w.setVisible(has)
        if not has:
            return
        c = session.criteria
        for w in (self.use_rel, self.use_abs, self.rel_spin, self.abs_spin):
            w.blockSignals(True)
        self.use_rel.setChecked(c.below_overall_by is not None)
        self.use_abs.setChecked(c.absolute_minimum is not None)
        self.rel_spin.setValue(c.below_overall_by if c.below_overall_by is not None else 5.0)
        self.abs_spin.setValue(c.absolute_minimum if c.absolute_minimum is not None else 50.0)
        for w in (self.use_rel, self.use_abs, self.rel_spin, self.abs_spin):
            w.blockSignals(False)
        self.diff_area.blockSignals(True)
        self.diff_area.clear()
        self.diff_area.addItem("Todas as áreas", None)
        for a in session.long["area"].unique():
            self.diff_area.addItem(str(a), str(a))
        self.diff_area.blockSignals(False)
        self.quality_list.clear()
        names = {"info": "Info", "warning": "Aviso", "error": "Erro"}
        for note in session.table.notes:
            self.quality_list.addItem(f"Info: {note}")
        for i in session.quality.issues:
            self.quality_list.addItem(f"{names[i.severity]}: {i.message}")
        self._recompute()

    def _criteria_changed(self, *_) -> None:
        if self._session is None:
            return
        self._session.criteria = AttentionCriteria(
            below_overall_by=self.rel_spin.value() if self.use_rel.isChecked() else None,
            absolute_minimum=self.abs_spin.value() if self.use_abs.isChecked() else None)
        self._recompute()

    def _recompute(self) -> None:
        s = self._session
        self.criteria_text.setText(an.describe_criteria(s.criteria) +
                                   " A comparação usa todas as turmas importadas, sem filtros do dashboard.")
        self._flagged = an.flag_attention(s.long, s.criteria)
        shown = ex.display_summary(self._flagged)
        self.summary_model.set_dataframe(shown)
        self.attention_model.set_dataframe(shown[shown["Atenção"] == "Sim"][["Turma", "Área", "Média", "Motivo"]])
        self._fill_diff()

    def _fill_diff(self, *_) -> None:
        if self._session is None:
            return
        self.diff_model.set_dataframe(an.pairwise_differences(self._session.long, self.diff_area.currentData())
                                      .round(2).reset_index().rename(columns={"index": "Turma"}))

    # ------------------------------------------------------------------ exportações
    def _ask(self, title: str, default: str, filters: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, title, default, filters)
        return path or None

    def _run(self, action) -> None:
        try:
            action()
        except ex.ExportError as exc:
            QMessageBox.warning(self, "Não foi possível exportar", str(exc))
            return
        except Exception:
            QMessageBox.warning(self, "Não foi possível exportar", "Ocorreu um erro ao gravar o arquivo.")
            return
        self._session.unexported = False
        self.exported.emit()
        QMessageBox.information(self, "Exportação concluída", "Arquivo gerado com sucesso. A planilha original não foi alterada.")

    def _export_data(self) -> None:
        if (p := self._ask("Exportar dados tratados", "dados_tratados.xlsx", "Excel (*.xlsx);;CSV (*.csv)")):
            self._run(lambda: ex.export_table(self._session.long, p, self._session.source_path))

    def _export_summary(self) -> None:
        if not (p := self._ask("Exportar resumo", "resumo_turmas.xlsx", "Excel (*.xlsx);;CSV (*.csv)")):
            return
        shown = ex.display_summary(self._flagged)
        if p.lower().endswith(".csv"):
            self._run(lambda: ex.export_table(shown, p, self._session.source_path))
        else:
            sheets = {"Resumo": shown, "Atenção": shown[shown["Atenção"] == "Sim"],
                      "Diferenças": an.pairwise_differences(self._session.long, self.diff_area.currentData())
                      .round(2).reset_index().rename(columns={"index": "Turma"})}
            self._run(lambda: ex.export_workbook(sheets, p, self._session.source_path))

    def _export_pdf(self) -> None:
        if not (p := self._ask("Gerar relatório", "relatorio_turmas.pdf", "PDF (*.pdf)")):
            return
        s = self._session

        def action():
            html = ex.build_report_html(self._flagged, s.criteria, an.overall_stats(s.long), s.quality, s.table.file_name)
            ex.write_pdf(html, p, s.source_path)

        self._run(action)
