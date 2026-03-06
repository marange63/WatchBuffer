from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QLineEdit, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt


class PaneNameDialog(QDialog):
    def __init__(self, parent=None, current_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Pane Name")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter pane name:"))
        self.name_edit = QLineEdit(current_name)
        self.name_edit.selectAll()
        layout.addWidget(self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.name_edit.returnPressed.connect(self._accept)

    def _accept(self):
        if self.name_edit.text().strip():
            self.accept()

    def get_name(self) -> str:
        return self.name_edit.text().strip()


class SecuritiesEditorDialog(QDialog):
    def __init__(self, parent=None, symbols: list = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Securities")
        self.setMinimumSize(300, 400)
        self._symbols = sorted(symbols or [])

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Symbols:"))

        self.list_widget = QListWidget()
        for sym in self._symbols:
            self.list_widget.addItem(sym)
        layout.addWidget(self.list_widget)

        add_row = QHBoxLayout()
        self.add_edit = QLineEdit()
        self.add_edit.setPlaceholderText("Ticker (e.g. AAPL)")
        self.add_edit.returnPressed.connect(self._add_symbol)
        add_row.addWidget(self.add_edit)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_symbol)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_symbol)
        layout.addWidget(remove_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_symbol(self):
        text = self.add_edit.text().strip().upper()
        if not text:
            return
        existing = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if text in existing:
            QMessageBox.information(self, "Duplicate", f"{text} is already in the list.")
            return
        existing = sorted([self.list_widget.item(i).text() for i in range(self.list_widget.count())] + [text])
        insert_pos = existing.index(text)
        self.list_widget.insertItem(insert_pos, text)
        self.add_edit.clear()

    def _remove_symbol(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def get_symbols(self) -> list:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
