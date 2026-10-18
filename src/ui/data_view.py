"""Tela de dados: tabela paginada, ordenável, com destaque para valores ausentes."""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QTableView,
    QVBoxLayout, QWidget,
)

from src.models.session import Session
from src.services.validation_service import classify_columns, is_missing, parse_number

_MISSING_BG = QBrush(QColor("#FFF1CC"))
_MISSING_FG = QBrush(QColor("#8A8F98"))


def format_cell(value) -> str:
    if is_missing(value):
        return "(vazio)"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(value)


class PandasTableModel(QAbstractTableModel):
    """Modelo somente leitura; com page_size mostra só uma página por vez."""

    def __init__(self, df: pd.DataFrame | None = None, page_size: int | None = None, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame() if df is None else df.reset_index(drop=True)
        self._page_size = page_size
        self._page = 0

    # -- API própria
    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df.reset_index(drop=True)
        self._page = 0
        self.endResetModel()

    @property
    def total_rows(self) -> int:
        return len(self._df)

    @property
    def page(self) -> int:
        return self._page

    @property
    def page_count(self) -> int:
        if not self._page_size:
            return 1
        return max(1, -(-len(self._df) // self._page_size))

    def set_page(self, page: int) -> None:
        page = max(0, min(page, self.page_count - 1))
        if page != self._page:
            self.beginResetModel()
            self._page = page
            self.endResetModel()

    def _start(self) -> int:
        return self._page * self._page_size if self._page_size else 0

    # -- API do Qt
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        start = self._start()
        end = min(len(self._df), start + self._page_size) if self._page_size else len(self._df)
        return max(0, end - start)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else self._df.shape[1]

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        value = self._df.iat[self._start() + index.row(), index.column()]
        missing = is_missing(value)
        if role == Qt.ItemDataRole.DisplayRole:
            return format_cell(value)
        if role == Qt.ItemDataRole.BackgroundRole and missing:
            return _MISSING_BG
        if role == Qt.ItemDataRole.ForegroundRole and missing:
            return _MISSING_FG
        if role == Qt.ItemDataRole.TextAlignmentRole and isinstance(value, (int, float)):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(self._start() + section + 1)


def make_table(model: QAbstractTableModel) -> QTableView:
    table = QTableView()
    table.setModel(model)
    table.setAlternatingRowColors(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().setDefaultSectionSize(24)
    return table


class DataPage(QWidget):
    PAGE_SIZE = 500

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self._session: Session | None = None
        self._base = pd.DataFrame()     # após filtros
        self._kinds: dict[str, str] = {}
        self._sort_col = -1
        self._ascending = True

        self.turma_filter = QComboBox()
        self.turma_filter.currentIndexChanged.connect(self._apply_filter)
        self.only_missing = QCheckBox("Mostrar apenas linhas com valores vazios")
        self.only_missing.toggled.connect(self._apply_filter)
        self.info = QLabel("")
        self.info.setObjectName("muted")
        self.empty = QLabel("Nenhum arquivo carregado. Use “Importar planilha” para começar.")
        self.empty.setObjectName("muted")

        self.model = PandasTableModel(page_size=self.PAGE_SIZE)
        self.table = make_table(self.model)
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._sort_by)

        self.prev_btn, self.next_btn = QPushButton("‹ Anterior"), QPushButton("Próxima ›")
        self.prev_btn.clicked.connect(lambda: self._go(-1))
        self.next_btn.clicked.connect(lambda: self._go(1))
        self.page_label = QLabel("")

        top = QHBoxLayout()
        top.addWidget(QLabel("Turma:"))
        top.addWidget(self.turma_filter)
        top.addWidget(self.only_missing)
        top.addStretch(1)
        bottom = QHBoxLayout()
        bottom.addWidget(self.info)
        bottom.addStretch(1)
        bottom.addWidget(self.prev_btn)
        bottom.addWidget(self.page_label)
        bottom.addWidget(self.next_btn)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(self.empty)
        lay.addLayout(top)
        lay.addWidget(self.table, 1)
        lay.addLayout(bottom)
        self.set_session(None)

    def set_session(self, session: Session | None) -> None:
        self._session = session
        has = session is not None
        for w in (self.table, self.turma_filter, self.only_missing, self.prev_btn, self.next_btn,
                  self.page_label, self.info):
            w.setVisible(has)
        self.empty.setVisible(not has)
        if not has:
            self.model.set_dataframe(pd.DataFrame())
            return
        df = session.table.df
        self._kinds = classify_columns(df)
        self.turma_filter.blockSignals(True)
        self.turma_filter.clear()
        self.turma_filter.addItem("Todas as turmas", None)
        for t in sorted(df[session.mapping.turma].dropna().astype(str).unique()):
            self.turma_filter.addItem(t, t)
        self.turma_filter.blockSignals(False)
        self.only_missing.blockSignals(True)
        self.only_missing.setChecked(False)
        self.only_missing.blockSignals(False)
        self._sort_col = -1
        self._apply_filter()

    def _apply_filter(self, *_):
        if self._session is None:
            return
        df = self._session.table.df
        turma = self.turma_filter.currentData()
        if turma is not None:
            df = df[df[self._session.mapping.turma].astype(str) == turma]
        if self.only_missing.isChecked():
            df = df[df.map(is_missing).any(axis=1)]
        self._base = df
        self._sort_col = -1
        self.model.set_dataframe(df)
        self.table.horizontalHeader().setSortIndicatorShown(False)
        self._update_pager()

    def _sort_by(self, col: int):
        if col == self._sort_col:
            self._ascending = not self._ascending
        else:
            self._sort_col, self._ascending = col, True
        name = self._base.columns[col]
        series = self._base[name]
        keys = series.map(parse_number) if self._kinds.get(name) == "numérica" else \
            series.map(lambda v: None if is_missing(v) else str(v).casefold())
        ordered = self._base.assign(_k=keys).sort_values("_k", ascending=self._ascending,
                                                         na_position="last", kind="stable").drop(columns="_k")
        self.model.set_dataframe(ordered)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSortIndicator(
            col, Qt.SortOrder.AscendingOrder if self._ascending else Qt.SortOrder.DescendingOrder)
        self._update_pager()

    def _go(self, step: int):
        self.model.set_page(self.model.page + step)
        self._update_pager()

    def _update_pager(self):
        m = self.model
        self.page_label.setText(f"Página {m.page + 1} de {m.page_count}")
        self.prev_btn.setEnabled(m.page > 0)
        self.next_btn.setEnabled(m.page < m.page_count - 1)
        total = len(self._session.table.df) if self._session else 0
        self.info.setText(f"{m.total_rows} de {total} linhas · células vazias em amarelo · "
                          "clique no cabeçalho para ordenar")
