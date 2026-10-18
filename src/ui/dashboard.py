"""Dashboard: indicadores, filtros e gráficos. A lógica de cálculo fica em src/services."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QStackedLayout, QTabWidget, QVBoxLayout, QWidget,
)

from src.charts import chart_builder as cb
from src.models.analysis_result import Filters
from src.models.session import Session
from src.services import analysis_service as an
from src.ui.chart_view import ChartView
from src.utils.formatting import format_number

TAB_BAR, TAB_HIST, TAB_BOX, TAB_AREA, TAB_EVOL = range(5)
TAB_TITLES = ["Médias por turma", "Distribuição", "Dispersão por turma", "Comparação por área", "Evolução"]


class KpiCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("card")
        self._title = QLabel(title)
        self._title.setObjectName("kpiTitle")
        self._value = QLabel("—")
        self._value.setObjectName("kpiValue")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        lay.addWidget(self._title)
        lay.addWidget(self._value)

    def set(self, title: str | None, value: str) -> None:
        if title:
            self._title.setText(title)
        self._value.setText(value)


class DashboardPage(QWidget):
    import_requested = Signal()
    exported = Signal()

    def __init__(self, runtime_dir: Path, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self._session: Session | None = None
        self._data = None
        self._summary = None
        self._overall_by_area: dict[str, float] = {}
        self._figures: dict[int, object] = {}
        self._stale: set[int] = set()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self.refresh)

        stack = QStackedLayout(self)
        stack.addWidget(self._build_empty())
        stack.addWidget(self._build_content(runtime_dir))
        self._stack = stack
        stack.setCurrentIndex(0)

    # ---------------------------------------------------------- construção
    def _build_empty(self) -> QWidget:
        w = QWidget()
        title = QLabel("Nenhum arquivo carregado")
        title.setObjectName("emptyTitle")
        hint = QLabel("Importe uma planilha com as colunas: turma, id, exatas (% de acertos) e humanas (% de acertos).\n"
                      "Formatos aceitos: .xlsx, .xls, .ods, .csv e .txt. Tudo é processado neste computador.")
        hint.setObjectName("muted")
        btn = QPushButton("Importar planilha")
        btn.setObjectName("primary")
        btn.clicked.connect(self.import_requested)
        lay = QVBoxLayout(w)
        lay.addStretch(1)
        for x in (title, hint):
            lay.addWidget(x, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(8)
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(2)
        return w

    def _build_content(self, runtime_dir: Path) -> QWidget:
        w = QWidget()
        self.kpi_turmas, self.kpi_records = KpiCard("Turmas encontradas"), KpiCard("Registros analisados")
        self.kpi_mean, self.kpi_best = KpiCard("Média geral"), KpiCard("Maior média entre turmas")
        kpis = QHBoxLayout()
        for k in (self.kpi_turmas, self.kpi_records, self.kpi_mean, self.kpi_best):
            kpis.addWidget(k, 1)

        # filtros
        self.turma_list = QListWidget()
        self.turma_list.itemChanged.connect(self._schedule)
        all_btn, none_btn = QPushButton("Todas"), QPushButton("Nenhuma")
        all_btn.clicked.connect(lambda: self._set_all(Qt.CheckState.Checked))
        none_btn.clicked.connect(lambda: self._set_all(Qt.CheckState.Unchecked))
        self.area_combo, self.period_combo = QComboBox(), QComboBox()
        self.area_combo.currentIndexChanged.connect(self._schedule)
        self.period_combo.currentIndexChanged.connect(self._schedule)
        self.period_label = QLabel("Período / avaliação")
        png_btn, html_btn = QPushButton("Salvar gráfico (PNG)"), QPushButton("Salvar gráfico (HTML)")
        png_btn.clicked.connect(self._save_png)
        html_btn.clicked.connect(self._save_html)

        box = QGroupBox("Filtros")
        fl = QVBoxLayout(box)
        fl.addWidget(QLabel("Turmas"))
        fl.addWidget(self.turma_list, 1)
        row = QHBoxLayout()
        row.addWidget(all_btn)
        row.addWidget(none_btn)
        fl.addLayout(row)
        fl.addWidget(QLabel("Coluna numérica / área"))
        fl.addWidget(self.area_combo)
        fl.addWidget(self.period_label)
        fl.addWidget(self.period_combo)
        fl.addSpacing(6)
        fl.addWidget(png_btn)
        fl.addWidget(html_btn)
        box.setFixedWidth(250)

        self.tabs = QTabWidget()
        self._views: dict[int, ChartView] = {}
        for i, title in enumerate(TAB_TITLES):
            view = ChartView(runtime_dir, f"chart{i}")
            self._views[i] = view
            self.tabs.addTab(view, title)
        self.tabs.currentChanged.connect(self._render_if_stale)
        self.no_data = QLabel("Nenhum dado com os filtros atuais.")
        self.no_data.setObjectName("muted")
        self.no_data.setVisible(False)

        right = QVBoxLayout()
        right.addWidget(self.no_data)
        right.addWidget(self.tabs, 1)
        body = QHBoxLayout()
        body.addWidget(box)
        body.addLayout(right, 1)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addLayout(kpis)
        lay.addSpacing(10)
        lay.addLayout(body, 1)
        return w

    # ---------------------------------------------------------- sessão
    def set_session(self, session: Session | None) -> None:
        self._session = session
        if session is None:
            self._stack.setCurrentIndex(0)
            return
        long = session.long
        for widget in (self.turma_list, self.area_combo, self.period_combo):
            widget.blockSignals(True)
        self.turma_list.clear()
        for t in an.natural_sorted(long["turma"].unique()):
            item = QListWidgetItem(str(t))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.turma_list.addItem(item)
        self.area_combo.clear()
        self.area_combo.addItem("Todas as áreas", None)
        for a in long["area"].unique():
            self.area_combo.addItem(str(a), str(a))
        self.period_combo.clear()
        self.period_combo.addItem("Todos os períodos", None)
        periods = an.order_periods(long["periodo"].dropna().unique())
        for p in periods:
            self.period_combo.addItem(p, p)
        has_period = len(periods) > 0
        self.period_combo.setVisible(has_period)       # sem coluna de período: filtro oculto
        self.period_label.setVisible(has_period)
        for widget in (self.turma_list, self.area_combo, self.period_combo):
            widget.blockSignals(False)
        self._stack.setCurrentIndex(1)
        self.refresh()

    def _set_all(self, state) -> None:
        self.turma_list.blockSignals(True)
        for i in range(self.turma_list.count()):
            self.turma_list.item(i).setCheckState(state)
        self.turma_list.blockSignals(False)
        self._schedule()

    def _schedule(self, *_) -> None:
        self._timer.start()

    def _filters(self) -> Filters:
        checked = tuple(self.turma_list.item(i).text() for i in range(self.turma_list.count())
                        if self.turma_list.item(i).checkState() == Qt.CheckState.Checked)
        all_checked = len(checked) == self.turma_list.count()
        return Filters(turmas=None if all_checked else checked, area=self.area_combo.currentData(),
                       period=self.period_combo.currentData() if self.period_combo.isVisible() else None)

    # ---------------------------------------------------------- atualização
    def refresh(self) -> None:
        s = self._session
        if s is None:
            return
        data = an.apply_filters(s.long, self._filters())
        self._data = data
        stats = an.overall_stats(data)
        area = self.area_combo.currentData()
        unit = s.unit
        self.kpi_turmas.set(None, str(stats.n_turmas))
        self.kpi_records.set(None, str(stats.n_records))
        self.kpi_mean.set(f"Média geral — {area or 'todas as áreas'}",
                          "—" if stats.mean is None else format_number(stats.mean) + (unit if unit else ""))
        self.kpi_best.set(None, "—" if stats.best_turma is None else
                          f"{stats.best_turma} — {format_number(stats.best_mean)}{unit}")
        empty = data.empty
        self.no_data.setVisible(empty)
        self.tabs.setVisible(not empty)
        self._figures.clear()
        if empty:
            return
        self._summary = an.summarize(data, ("turma", "area"))
        self._overall_by_area = data.groupby("area")["valor"].mean().to_dict()
        enabled = {TAB_BAR: True, TAB_HIST: True, TAB_BOX: True,
                   TAB_AREA: data["area"].nunique() >= 2,
                   TAB_EVOL: data["periodo"].nunique() >= 2}
        for i, ok in enabled.items():
            self.tabs.setTabEnabled(i, ok)
        if not enabled.get(self.tabs.currentIndex(), False):
            self.tabs.setCurrentIndex(TAB_BAR)
        self._stale = {i for i, ok in enabled.items() if ok}
        self._render_if_stale(self.tabs.currentIndex())

    def _render_if_stale(self, index: int) -> None:
        if index not in self._stale or self._data is None or self._data.empty:
            return
        s, vr, unit, d = self._session, self._session.value_range, self._session.unit, self._data
        if index == TAB_BAR:
            fig = cb.bar_means(self._summary, self._overall_by_area, vr, unit)
        elif index == TAB_HIST:
            fig = cb.histogram(d, vr, unit)
        elif index == TAB_BOX:
            fig = cb.boxplot(d, vr, unit)
        elif index == TAB_AREA:
            fig = cb.area_comparison(self._summary, vr, unit)
        else:
            fig = cb.evolution(d, vr, unit)
        self._figures[index] = fig
        self._views[index].show_figure(fig)
        self._stale.discard(index)

    # ---------------------------------------------------------- exportar gráfico
    def _save_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Salvar gráfico", "grafico.png", "Imagem PNG (*.png)")
        if not path:
            return
        view = self._views[self.tabs.currentIndex()]
        if view.save_png(path):
            self._mark_exported()
            QMessageBox.information(self, "Gráfico salvo", "Imagem salva com sucesso.")
        else:
            QMessageBox.warning(self, "Falha ao salvar", "Não foi possível gerar a imagem. Tente salvar em HTML.")

    def _save_html(self) -> None:
        fig = self._figures.get(self.tabs.currentIndex())
        if fig is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar gráfico", "grafico.html", "Página HTML (*.html)")
        if not path:
            return
        try:
            cb.save_standalone_html(fig, path)
        except OSError:
            QMessageBox.warning(self, "Falha ao salvar", "Não foi possível gravar o arquivo.")
            return
        self._mark_exported()
        QMessageBox.information(self, "Gráfico salvo", "Arquivo salvo. Ele funciona offline.")

    def _mark_exported(self) -> None:
        if self._session:
            self._session.unexported = False
        self.exported.emit()
