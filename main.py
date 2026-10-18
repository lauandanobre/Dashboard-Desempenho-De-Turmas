"""Ponto de entrada do Métricas das Turmas."""
import atexit
import shutil
import sys
import tempfile
from pathlib import Path

from src.utils.logging_config import log_unhandled, logger, setup_logging


def _fatal(message: str) -> None:
    """Mostra erro de inicialização mesmo se o Qt não carregar."""
    print(message, file=sys.stderr)
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Métricas das Turmas", message)
    except Exception:
        pass


def main() -> int:
    setup_logging()
    try:
        # QtWebEngine precisa ser importado ANTES de criar o QApplication.
        from PySide6 import QtWebEngineWidgets  # noqa: F401
        from PySide6.QtWidgets import QApplication, QMessageBox
        from src.ui.main_window import MainWindow
        from src.ui.styles import QSS
    except Exception as exc:  # dependência ausente ou incompatível
        logger.error("Falha ao iniciar: %s", type(exc).__name__)
        _fatal("Não foi possível iniciar o aplicativo: uma dependência está ausente.\n"
               "Execute: pip install -r requirements.txt")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("Métricas das Turmas")
    app.setStyleSheet(QSS)

    # Pasta temporária (só gráficos locais); removida ao sair.
    runtime_dir = Path(tempfile.mkdtemp(prefix="metricas_"))
    atexit.register(shutil.rmtree, runtime_dir, ignore_errors=True)

    def excepthook(exc_type, exc, tb):
        log_unhandled(exc_type, tb)
        QMessageBox.critical(None, "Métricas das Turmas",
                             "Ocorreu um erro inesperado. A operação foi interrompida, mas o aplicativo "
                             f"continua aberto.\nDetalhes técnicos (sem dados pessoais) em:\n{Path.home() / '.metricas_das_turmas' / 'logs'}")

    sys.excepthook = excepthook
    window = MainWindow(runtime_dir)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
