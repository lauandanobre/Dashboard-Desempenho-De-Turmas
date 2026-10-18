"""Widget que mostra um gráfico Plotly dentro da janela (QtWebEngine, 100% local)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.charts.chart_builder import write_figure_html


class ChartView(QWebEngineView):
    def __init__(self, runtime_dir: Path, name: str, parent=None):
        super().__init__(parent)
        self._dir = Path(runtime_dir)
        self._name = name
        self._counter = 0
        self._current: Path | None = None
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)

    def show_figure(self, fig) -> None:
        self._counter += 1
        path = write_figure_html(fig, self._dir, f"{self._name}_{self._counter}.html")
        old, self._current = self._current, path
        self.load(QUrl.fromLocalFile(str(path)))
        if old:
            old.unlink(missing_ok=True)

    def clear(self) -> None:
        self.setHtml("<html><body style='background:#fff'></body></html>")

    def save_png(self, dest: str) -> bool:
        return self.grab().save(dest, "PNG")
