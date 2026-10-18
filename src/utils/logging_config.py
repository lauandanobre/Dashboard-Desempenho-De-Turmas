"""Logs locais, sem dados pessoais.

Regra do projeto: NUNCA registrar valores de células, nomes de turmas/alunos
nem mensagens de exceção que possam conter dados. Registre apenas contagens,
extensões de arquivo e tipos de erro.
"""
from __future__ import annotations

import logging
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

logger = logging.getLogger("metricas")


def log_dir() -> Path:
    return Path.home() / ".metricas_das_turmas" / "logs"


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        directory = log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            directory / "app.log", maxBytes=512_000, backupCount=2, encoding="utf-8"
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    root.addHandler(handler)


def log_unhandled(exc_type, tb) -> None:
    """Registra tipo do erro e pilha de chamadas, sem a mensagem (pode conter dados)."""
    logger.error("Erro não tratado: %s\n%s", exc_type.__name__, "".join(traceback.format_tb(tb)))
