"""Tela "Relatórios": pré-visualização do relatório e botões de exportação."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QStackedWidget, QTextBrowser, QVBoxLayout, QWidget


class ReportsView(QWidget):
    exportTable = Signal()
    exportSummary = Signal()
    exportChart = Signal()
    exportPdf = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        title = QLabel("Relatórios e exportação")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        self.stack = QStackedWidget()
        empty = QLabel("Nenhuma planilha carregada.\nImporte um arquivo para gerar relatórios.")
        empty.setObjectName("emptyState")
        empty.setAlignment(Qt.AlignCenter)
        self.stack.addWidget(empty)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 8, 0, 0)
        grid = QGridLayout()
        buttons = [("Exportar tabela tratada…", self.exportTable), ("Exportar resumo estatístico…", self.exportSummary),
                   ("Exportar gráfico atual…", self.exportChart), ("Gerar relatório em PDF…", self.exportPdf)]
        for i, (text, signal) in enumerate(buttons):
            b = QPushButton(text)
            b.clicked.connect(signal)
            grid.addWidget(b, 0, i)
        lay.addLayout(grid)
        note = QLabel("As exportações criam arquivos novos; a planilha original nunca é alterada. "
                      "O PDF não inclui IDs de alunos.")
        note.setObjectName("muted")
        lay.addWidget(note)
        self.browser = QTextBrowser()
        lay.addWidget(self.browser, 1)
        self.stack.addWidget(content)
        root.addWidget(self.stack, 1)

    def clear(self) -> None:
        self.stack.setCurrentIndex(0)

    def set_html(self, html: str) -> None:
        self.browser.setHtml(html)
        self.stack.setCurrentIndex(1)
