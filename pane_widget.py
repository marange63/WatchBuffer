import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.transforms import blended_transform_factory

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from dialogs import PaneNameDialog, SecuritiesEditorDialog


class WatchPane(QFrame):
    deleted = pyqtSignal(str)
    symbols_changed = pyqtSignal(str)

    def __init__(self, pane_id: str, name: str, symbols: list, parent=None):
        super().__init__(parent)
        self.pane_id = pane_id
        self.pane_name = name
        self.symbols = list(symbols)
        self.aliases = {}
        self._prev_prices = {}

        self.setFixedWidth(360)
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        self.name_label = QLabel(f"<b>{name}</b>")
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.addWidget(self.name_label, stretch=1)

        edit_btn = QPushButton("Edit")
        edit_btn.setFixedWidth(40)
        edit_btn.clicked.connect(self._edit_securities)
        header.addWidget(edit_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setFixedWidth(55)
        rename_btn.clicked.connect(self._rename)
        header.addWidget(rename_btn)

        del_btn = QPushButton("X")
        del_btn.setFixedWidth(24)
        del_btn.clicked.connect(self._delete)
        header.addWidget(del_btn)

        layout.addLayout(header)

        self.figure = Figure(figsize=(3.5, 4), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, stretch=1)

        self._draw_empty()

    def update_aliases(self, aliases: dict):
        self.aliases = aliases

    def _draw_empty(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if self.symbols:
            display = [self.aliases.get(s.upper(), s.upper()) for s in self.symbols]
            ax.set_yticks(range(len(self.symbols)))
            ax.set_yticklabels(display)
            ax.set_xlabel("Daily Return %")
            ax.axvline(0, color="gray", linewidth=0.8)
            ax.set_title("Waiting for data...")
        else:
            ax.set_title("No symbols - click Edit")
            ax.axis("off")
        self.canvas.draw()

    def update_chart(self, data: dict):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not self.symbols:
            ax.set_title("No symbols - click Edit")
            ax.axis("off")
            self.canvas.draw()
            return

        pairs = []
        for sym in self.symbols:
            info = data.get(sym.upper())
            ret = info["return_pct"] if info else None
            pairs.append((sym.upper(), ret))
        pairs.sort(key=lambda p: abs(p[1]) if p[1] is not None else -1, reverse=True)
        labels = [self.aliases.get(p[0], p[0]) for p in pairs]
        returns = [p[1] for p in pairs]

        y_pos = list(range(len(labels)))
        colors = []
        display_returns = []
        for r in returns:
            if r is None:
                colors.append("gray")
                display_returns.append(0.0)
            else:
                colors.append("#2ecc71" if r >= 0 else "#e74c3c")
                display_returns.append(r)

        bars = ax.barh(y_pos, display_returns, color=colors, edgecolor="black", linewidth=0.6, height=0.6)

        for bar, disp_r, orig_r in zip(bars, display_returns, returns):
            if orig_r is None:
                label = "N/A"
            else:
                sign = "+" if orig_r >= 0 else ""
                label = f"{sign}{orig_r:.2f}%"
            x = bar.get_width()
            offset = 0.05 if x >= 0 else -0.05
            ha = "left" if x >= 0 else "right"
            ax.text(x + offset, bar.get_y() + bar.get_height() / 2,
                    label, va="center", ha=ha, fontsize=8, clip_on=False)

        syms_ordered = [p[0] for p in pairs]
        new_prices = {p[0]: (data.get(p[0]) or {}).get("price") for p in pairs}
        trans = blended_transform_factory(ax.transAxes, ax.transData)
        UP = chr(0x25B2)
        DOWN = chr(0x25BC)
        for yp, sym in zip(y_pos, syms_ordered):
            prev = self._prev_prices.get(sym)
            cur = new_prices.get(sym)
            if prev is None or cur is None:
                arrow, acolor = "-", "#888888"
            elif cur > prev:
                arrow, acolor = UP, "#2ecc71"
            elif cur < prev:
                arrow, acolor = DOWN, "#e74c3c"
            else:
                arrow, acolor = "-", "#888888"
            ax.text(1.02, yp, arrow, transform=trans,
                    va="center", ha="left", fontsize=8, color=acolor, clip_on=False)
        self._prev_prices = {sym: p for sym, p in new_prices.items() if p is not None}

        ax.invert_yaxis()
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.axvline(0, color="gray", linewidth=0.8, zorder=0)
        ax.set_xlabel("Daily Return %", fontsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.set_title(self.pane_name, fontsize=10)

        max_abs = max((abs(r) for r in display_returns if r), default=1.0)
        margin = max_abs * 0.65
        ax.set_xlim(-max_abs - margin, max_abs + margin)

        self.canvas.draw()

    def _edit_securities(self):
        dlg = SecuritiesEditorDialog(self, self.symbols)
        if dlg.exec_() == dlg.Accepted:
            self.symbols = dlg.get_symbols()
            self._draw_empty()
            self.symbols_changed.emit(self.pane_id)

    def _rename(self):
        dlg = PaneNameDialog(self, self.pane_name)
        if dlg.exec_() == dlg.Accepted:
            self.pane_name = dlg.get_name()
            self.name_label.setText(f"<b>{self.pane_name}</b>")

    def _delete(self):
        reply = QMessageBox.question(
            self, "Delete Pane",
            "Delete pane "" + self.pane_name + ""?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.deleted.emit(self.pane_id)

    def to_dict(self) -> dict:
        return {"id": self.pane_id, "name": self.pane_name, "symbols": self.symbols}
