"""Caminhos de recursos e pastas do usuário (compatível com PyInstaller)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Métricas das Turmas"
APP_FOLDER = "MetricasDasTurmas"


def resource_path(relative: str) -> Path:
    """Localiza arquivos em assets/ tanto no código-fonte quanto no executável."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parents[2]
    return root / relative


def user_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home())
    path = Path(base) / APP_FOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path
