"""Janela principal: cabeçalho, navegação lateral e páginas."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from src.models.session import Session
from src.services.validation_service import DataValidationError, build_clean_dataset
from src.ui.dashboard import DashboardPage
from src.ui.data_view import DataPage
from src.ui.dialogs import ImportDialog, QualityDialog
from src.ui.reports import ReportsPage
from src.utils.logging_config import logger

APP_NAME = "Métricas das Turmas"


class MainWindow(QMainWindow):
    def __init__(self, runtime_dir: Path):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        self.session: Session | None = None

        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        self.file_label = QLabel("Nenhum arquivo carregado")
        self.file_label.setObjectName("fileName")
        import_btn = QPushButton("Importar planilha")
        import_btn.setObjectName("primary")
        import_btn.clicked.connect(self.import_file)
        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 10, 16, 10)
        hl.addWidget(title)
        hl.addSpacing(20)
        hl.addWidget(self.file_label, 1)
        hl.addWidget(import_btn)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(180)
        self.nav.addItems(["Dashboard", "Dados", "Relatórios"])
        self.dashboard = DashboardPage(runtime_dir)
        self.data_page = DataPage()
        self.reports = ReportsPage()
        self.stack = QStackedWidget()
        for page in (self.dashboard, self.data_page, self.reports):
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        self.dashboard.import_requested.connect(self.import_file)
        self.dashboard.exported.connect(self._noop)
        self.reports.exported.connect(self._noop)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.nav)
        body.addWidget(self.stack, 1)
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(header)
        lay.addLayout(body, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Pronto. Os dados são processados somente neste computador.")

    def _noop(self) -> None:
        self.statusBar().showMessage("Exportação concluída.", 5000)

    # ------------------------------------------------------------------
    def _confirm_discard(self) -> bool:
        if self.session is None or not self.session.unexported:
            return True
        answer = QMessageBox.question(
            self, "Resultados não exportados",
            "A análise atual ainda não foi exportada. Se continuar, ela será descartada.\n\nDeseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        return answer == QMessageBox.StandardButton.Yes

    def import_file(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar planilha", "", "Planilhas (*.xlsx *.xls *.ods *.csv *.txt);;Todos os arquivos (*)")
        if not path:
            return
        dialog = ImportDialog(Path(path), self)
        if not dialog.ok_to_open or dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            long, quality = build_clean_dataset(dialog.table.df, dialog.mapping, dialog.config)
        except DataValidationError as exc:
            QMessageBox.warning(self, "Mapeamento inválido", str(exc))
            return
        logger.info("Análise criada: registros=%d valores=%d", quality.rows_analyzed, quality.values_used)
        QualityDialog(quality, dialog.table.notes, self).exec()
        if quality.has_errors:
            return
        self.session = Session(source_path=Path(path), table=dialog.table, mapping=dialog.mapping,
                               config=dialog.config, long=long, quality=quality)
        self.file_label.setText(f"Arquivo: {Path(path).name}" +
                                (f" · aba: {dialog.table.sheet}" if dialog.table.sheet else ""))
        self.dashboard.set_session(self.session)
        self.data_page.set_session(self.session)
        self.reports.set_session(self.session)
        self.nav.setCurrentRow(0)

    def closeEvent(self, event) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
