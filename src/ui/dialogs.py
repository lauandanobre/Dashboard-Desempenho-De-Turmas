"""Diálogos: importação (aba, prévia, colunas, regras) e relatório de qualidade."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QTextBrowser, QVBoxLayout,
)

from src.models.analysis_result import ColumnMapping, ImportedTable, QualityReport, ValidationConfig
from src.models.dataset import Dataset
from src.services import import_service, ingest_service, schema
from src.services.import_service import ImportServiceError
from src.services.validation_service import classify_columns, guess_mapping
from src.ui.data_view import PandasTableModel, make_table

NONE_LABEL = "(nenhuma)"


class ImportDialog(QDialog):
    """Resultado após exec() == Accepted: .table, .mapping, .config."""

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importar planilha")
        self.resize(900, 700)
        self._path = path
        self.table: ImportedTable | None = None
        self.mapping: ColumnMapping | None = None
        self.config = ValidationConfig()
        self.dataset: Dataset | None = None          # preenchido quando o layout é reconhecido
        self._labels: dict[str, str] = {}

        self.sheet_combo = QComboBox()
        self.sheet_combo.currentIndexChanged.connect(self._load)
        self.notes = QLabel("")
        self.notes.setWordWrap(True)
        self.notes.setObjectName("muted")
        self.preview_model = PandasTableModel()
        self.preview = make_table(self.preview_model)

        self.turma_combo, self.id_combo, self.period_combo = QComboBox(), QComboBox(), QComboBox()
        self.presence_combo = QComboBox()
        self.presence_combo.currentIndexChanged.connect(self._presence_changed)
        self.values_list = QListWidget()
        self.values_list.setMaximumHeight(120)

        self.use_min, self.use_max = QCheckBox("Mínimo:"), QCheckBox("Máximo:")
        self.min_spin, self.max_spin = QDoubleSpinBox(), QDoubleSpinBox()
        for spin, val in ((self.min_spin, 0.0), (self.max_spin, 100.0)):
            spin.setRange(-1e9, 1e9)
            spin.setDecimals(2)
            spin.setValue(val)
        self.use_min.setChecked(True)
        self.use_max.setChecked(True)
        self.zero_absent = QCheckBox("Tratar linhas com todas as notas iguais a 0 como aluno ausente (fora das médias)")
        self.zero_absent.setToolTip("Ausente não é nota zero. Use quando a planilha não tem coluna de presença.")
        self.fraction = QCheckBox("Os valores estão em fração (0–1): multiplicar por 100")
        self.dedupe = QCheckBox("Remover linhas com id repetido na mesma turma/período (mantém a primeira)")

        form = QFormLayout()
        form.addRow("Aba:", self.sheet_combo)
        form.addRow("Coluna da turma:", self.turma_combo)
        form.addRow("Coluna do id (opcional):", self.id_combo)
        form.addRow("Coluna de período/avaliação (opcional):", self.period_combo)
        form.addRow("Coluna de presença SIM/NAO (opcional):", self.presence_combo)
        form.addRow("Colunas numéricas a analisar:", self.values_list)

        rules = QGroupBox("Regras de tratamento")
        rl = QVBoxLayout(rules)
        row = QHBoxLayout()
        for w in (self.use_min, self.min_spin, self.use_max, self.max_spin):
            row.addWidget(w)
        row.addStretch(1)
        rl.addLayout(row)
        rl.addWidget(QLabel("Valores fora do intervalo ou não numéricos são ignorados e listados no relatório."))
        rl.addWidget(self.zero_absent)
        rl.addWidget(self.fraction)
        rl.addWidget(self.dedupe)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Importar")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Arquivo: {path.name}"))
        lay.addLayout(form)
        lay.addWidget(self.notes)
        lay.addWidget(QLabel("Prévia (primeiras 50 linhas — o arquivo original não é modificado):"))
        lay.addWidget(self.preview, 1)
        lay.addWidget(rules)
        lay.addWidget(buttons)

        self.ok_to_open = self._init_sheets()

    # -- carregamento
    def _init_sheets(self) -> bool:
        try:
            sheets = import_service.list_sheets(self._path)
        except ImportServiceError as exc:
            QMessageBox.warning(self, "Não foi possível importar", str(exc))
            return False
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(sheets or ["(arquivo de texto)"])
        self.sheet_combo.setEnabled(len(sheets) > 1)
        preferred = next((i for i, n in enumerate(sheets) if n.strip().lower() == schema.SHEET_ALUNOS.lower()), None)
        if preferred is not None:                    # pasta de trabalho no padrão: começa pela aba Alunos
            self.sheet_combo.setCurrentIndex(preferred)
        self.sheet_combo.blockSignals(False)
        return self._load()

    def _load(self, *_) -> bool:
        sheet = self.sheet_combo.currentText() if self._is_excel() else None
        self.dataset = None
        try:
            table = import_service.read_table(self._path, sheet=sheet)
            self.dataset = ingest_service.try_load_dataset(self._path, table)
        except ImportServiceError as exc:
            QMessageBox.warning(self, "Não foi possível importar", str(exc))
            return False
        if self.dataset is not None:                 # layout conhecido: trabalha com a tabela já padronizada
            table = ImportedTable(df=self.dataset.alunos, file_name=self._path.name,
                                  sheet=schema.SHEET_ALUNOS if self._is_excel() else None,
                                  notes=list(self.dataset.notes))
        self.table = table
        info = list(table.notes)
        if table.delimiter:
            info.append(f"Separador detectado: {'tabulação' if table.delimiter == chr(9) else table.delimiter!r} · "
                        f"codificação: {table.encoding}")
        self.notes.setText("\n".join(info))
        self.preview_model.set_dataframe(table.df.head(50))
        self._fill_columns()
        return True

    def _is_excel(self) -> bool:
        return self._path.suffix.lower() in import_service.EXCEL_ENGINES

    def _fill_columns(self) -> None:
        df = self.table.df
        kinds = classify_columns(df)
        guess = guess_mapping(df)
        cols = list(df.columns)
        self._labels = guess.get("labels", {})
        for combo, key, optional in ((self.turma_combo, "turma", False), (self.id_combo, "id", True),
                                     (self.period_combo, "period", True), (self.presence_combo, "presence", True)):
            combo.clear()
            if optional:
                combo.addItem(NONE_LABEL, None)
            for c in cols:
                combo.addItem(f"{c}  ({kinds[c]})", c)
            idx = combo.findData(guess[key]) if guess[key] is not None else 0
            combo.setCurrentIndex(max(idx, 0))
        self.values_list.clear()
        for c in cols:
            item = QListWidgetItem(f"{c}  ({kinds[c]})")
            item.setData(Qt.ItemDataRole.UserRole, c)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if c in guess["values"] else Qt.CheckState.Unchecked)
            self.values_list.addItem(item)
        self._presence_changed()

    def _presence_changed(self, *_) -> None:
        has = self.presence_combo.currentData() is not None
        self.zero_absent.setEnabled(not has)
        if has:
            self.zero_absent.setChecked(False)

    # -- confirmação
    def _accept(self) -> None:
        values = tuple(self.values_list.item(i).data(Qt.ItemDataRole.UserRole)
                       for i in range(self.values_list.count())
                       if self.values_list.item(i).checkState() == Qt.CheckState.Checked)
        turma, ident, period, presence = (self.turma_combo.currentData(), self.id_combo.currentData(),
                                          self.period_combo.currentData(), self.presence_combo.currentData())
        chosen = [c for c in (turma, ident, period, presence, *values) if c]
        if not values:
            QMessageBox.warning(self, "Colunas", "Marque ao menos uma coluna numérica para analisar.")
            return
        if len(set(chosen)) != len(chosen):
            QMessageBox.warning(self, "Colunas", "A mesma coluna foi escolhida para funções diferentes.")
            return
        lo = self.min_spin.value() if self.use_min.isChecked() else None
        hi = self.max_spin.value() if self.use_max.isChecked() else None
        if lo is not None and hi is not None and lo >= hi:
            QMessageBox.warning(self, "Intervalo", "O mínimo precisa ser menor que o máximo.")
            return
        labels = tuple((c, self._labels[c]) for c in values if c in self._labels)
        self.mapping = ColumnMapping(turma=turma, value_columns=values, id_column=ident, period_column=period,
                                     presence_column=presence, area_labels=labels)
        self.config = ValidationConfig(min_value=lo, max_value=hi, scale=100.0 if self.fraction.isChecked() else 1.0,
                                       remove_duplicate_ids=self.dedupe.isChecked(),
                                       zero_is_absent=self.zero_absent.isChecked())
        self.accept()


class QualityDialog(QDialog):
    """Mostra o que foi encontrado/tratado na importação. Aparece sempre."""

    def __init__(self, report: QualityReport, import_notes: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resultado da importação")
        self.resize(640, 460)
        prefix = {"info": "Info", "warning": "Aviso", "error": "Erro"}
        lines = [f"<b>{report.rows_analyzed}</b> de {report.rows_in} linhas entraram nas médias"
                 + (f" ({report.n_absent} ausentes)" if report.n_absent else "") + " · "
                 f"<b>{report.values_used}</b> de {report.values_in} valores preenchidos foram usados.<br>"
                 "Nenhum dado foi descartado sem aparecer nesta lista.<br>"]
        items = [("info", n) for n in import_notes] + [(i.severity, i.message) for i in report.issues]
        if not items:
            lines.append("Nenhum problema encontrado.")
        for sev, msg in sorted(items, key=lambda x: ("error", "warning", "info").index(x[0])):
            lines.append(f"<p><b>{prefix[sev]}:</b> {msg}</p>")
        browser = QTextBrowser()
        browser.setHtml("".join(lines))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        lay = QVBoxLayout(self)
        lay.addWidget(browser)
        lay.addWidget(buttons)
