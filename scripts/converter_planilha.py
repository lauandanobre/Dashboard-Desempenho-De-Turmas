"""Converte uma planilha (exportação do sistema de correção OU padrão) para o padrão do projeto.

Uso:  python scripts/converter_planilha.py entrada.xlsx [saida.xlsx]

Sem a saída, grava "<entrada>_padronizado.xlsx" ao lado do arquivo original (que nunca é alterado).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.services.import_service import ImportServiceError  # noqa: E402
from src.services.ingest_service import try_load_dataset  # noqa: E402
from src.services.standard_workbook import write_standard_workbook  # noqa: E402
from src.services.export_service import ExportError  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    src = Path(argv[0])
    dest = Path(argv[1]) if len(argv) > 1 else src.with_name(src.stem + "_padronizado.xlsx")
    try:
        ds = try_load_dataset(src)
        if ds is None:
            print("Layout não reconhecido. Use o modelo em assets/modelo_planilha_turmas.xlsx.")
            return 2
        write_standard_workbook(dest, ds, source=src)
    except (ImportServiceError, ExportError) as exc:
        print(f"Erro: {exc}")
        return 3
    pres = int((ds.alunos["presente"] == "SIM").sum())
    print(f"OK: {len(ds.alunos)} alunos ({pres} presentes) -> {dest}")
    for n in ds.notes:
        print(" -", n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
