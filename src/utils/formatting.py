"""Formatação de números no padrão brasileiro (vírgula decimal)."""
from __future__ import annotations

import math


def format_number(value, decimals: int = 1) -> str:
    if value is None:
        return "—"
    try:
        if math.isnan(float(value)):
            return "—"
    except (TypeError, ValueError):
        return str(value)
    return f"{float(value):.{decimals}f}".replace(".", ",")
