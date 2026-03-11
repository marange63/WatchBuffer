import math
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

SIGMA = chr(0x03c3)
UP = chr(0x25b2)
DOWN = chr(0x25bc)


class WatchPane(QFrame):
    deleted = pyqtSignal(str)
    symbols_changed = pyqtSignal(str)

    def __init__(self, pane_id: str, name: str, symbols: list, parent=None):
        super().__init__(parent)
        self.pane_id = pane_id
        self.pane_name = name
        self.symbols = list(symbols)
        self.aliases = {}
        self._price_history = {}
        self.mode = "return"
        self.sort_mode = "abs_desc"

        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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

    def set_mode(self, mode: str):
        self.mode = mode

    def set_sort_mode(self, sort_mode: str):
        self.sort_mode = sort_mode

    def _xlabel(self) -> str:
        return "Daily Return %" if self.mode == "return" else f"Sigma Move ({SIGMA})"

    def _draw_empty(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if self.symbols:
            display = [self.aliases.get(s.upper(), s.upper()) for s in self.symbols]
            ax.set_yticks(range(len(self.symbols)))
            ax.set_yticklabels(display)
            ax.set_xlabel(self._xlabel())
            ax.axvline(0, color="gray", linewidth=0.8)
            ax.set_title("Waiting for data...")
        else:
            ax.set_title("No symbols - click Edit")
            ax.axis("off")
        self.canvas.draw()

    def update_chart(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not self.symbols:
            ax.set_title("No symbols - click Edit")
            ax.axis("off")
            self.canvas.draw()
            return

        use_sigma = self.mode == "sigma"

        rows = []
        for sym in self.symbols:
            sym = sym.upper()
            info = data.get(sym) or {}
            ret_pct  = info.get("return_pct")
            sigma_mv = info.get("sigma_move")
            price    = info.get("price")
            if use_sigma and sigma_mv is not None:
                val, has_sigma = sigma_mv, True
            else:
                val, has_sigma = ret_pct, False
            rows.append({"sym": sym, "val": val, "ret": ret_pct,
                         "sigma": sigma_mv, "price": price, "has_sigma": has_sigma})

        if self.sort_mode == "desc":
            rows.sort(key=lambda r: r["val"] if r["val"] is not None else float("-inf"), reverse=True)
        else:
            rows.sort(key=lambda r: abs(r["val"]) if r["val"] is not None else -1, reverse=True)

        labels, display_vals, colors = [], [], []
        for r in rows:
            name = self.aliases.get(r["sym"], r["sym"])
            p = r["price"]
            if p is not None:
                ps = f"{p:,.2f}" if p >= 100 else f"{p:.2f}"
                labels.append(f"{name} ({ps})")
            else:
                labels.append(name)
            v = r["val"]
            display_vals.append(v if v is not None else 0.0)
            colors.append("gray" if v is None else ("#2ecc71" if v >= 0 else "#e74c3c"))

        y_pos = list(range(len(rows)))
        ax.barh(y_pos, display_vals, color=colors,
                edgecolor="black", linewidth=0.6, height=0.6)

        for i, (r, dv) in enumerate(zip(rows, display_vals)):
            v = r["val"]
            if v is None:
                ann = "N/A"
            elif use_sigma and r["has_sigma"]:
                sign = "+" if v >= 0 else ""
                ann = f"{sign}{v:.2f}{SIGMA}"
            else:
                ret = r["ret"] or 0
                sign = "+" if ret >= 0 else ""
                ann = f"{sign}{ret:.2f}%"
            ha = "left" if dv >= 0 else "right"
            offset = 0.05 if dv >= 0 else -0.05
            ax.text(dv + offset, i, ann,
                    va="center", ha=ha, fontsize=8, clip_on=False)

        trans = blended_transform_factory(ax.transAxes, ax.transData)
        for yp, r in enumerate(rows):
            sym = r["sym"]
            cur = r["price"]
            hist = self._price_history.get(sym, [])
            full = hist + ([cur] if cur is not None else [])
            streak, direction = 0, None
            for i in range(len(full) - 1, 0, -1):
                d = (1 if full[i] > full[i-1] else
                     -1 if full[i] < full[i-1] else 0)
                if d == 0:
                    break
                if direction is None:
                    direction, streak = d, 1
                elif d == direction:
                    streak += 1
                else:
                    break
            streak = min(streak, 3)
            if direction == 1:
                arrow_str, acolor = UP * streak, "#2ecc71"
            elif direction == -1:
                arrow_str, acolor = DOWN * streak, "#e74c3c"
            else:
                arrow_str, acolor = "-", "#888888"
            ax.text(1.02, yp, arrow_str, transform=trans,
                    va="center", ha="left", fontsize=8, color=acolor, clip_on=False)
            if cur is not None:
                self._price_history[sym] = (hist + [cur])[-4:]

        ax.invert_yaxis()
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.axvline(0, color="gray", linewidth=0.8, zorder=0)
        ax.set_xlabel(self._xlabel(), fontsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.set_title(self.pane_name, fontsize=10)
        max_abs = max((abs(v) for v in display_vals if math.isfinite(v)), default=1.0)
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
