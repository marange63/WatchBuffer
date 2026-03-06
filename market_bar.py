from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

BENCHMARK_SYMBOLS = ["SPY", "QQQ", "IWM", "^DJI"]
DISPLAY_NAMES = {"SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "^DJI": "DJIA"}


class MarketBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: #1e1e2e;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(32)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        bold = QFont()
        bold.setBold(True)

        self._labels = {}
        for sym in BENCHMARK_SYMBOLS:
            lbl = QLabel(f"{DISPLAY_NAMES[sym]}  --")
            lbl.setFont(bold)
            lbl.setStyleSheet("color: #aaaaaa; font-size: 16px; background-color: #3a3a3a; padding: 4px 10px; border-radius: 4px;")
            layout.addWidget(lbl)
            self._labels[sym] = lbl

        layout.addStretch()
        self._aliases = {}

    def set_aliases(self, aliases: dict):
        self._aliases = aliases

    def refresh(self, data: dict):
        for sym in BENCHMARK_SYMBOLS:
            info = data.get(sym)
            lbl = self._labels[sym]
            name = self._aliases.get(sym) or DISPLAY_NAMES[sym]
            if info is None:
                lbl.setText(f"{name}  --")
                lbl.setStyleSheet("color: #aaaaaa; font-size: 16px; background-color: #3a3a3a; padding: 4px 10px; border-radius: 4px;")
            else:
                price = info["price"]
                ret = info["return_pct"]
                sign = "+" if ret >= 0 else ""
                color = "#2ecc71" if ret >= 0 else "#e74c3c"
                price_str = f"{price:,.2f}" if price >= 100 else f"{price:.2f}"
                lbl.setText(f"{name}  {price_str}  {sign}{ret:.2f}%")
                lbl.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; background-color: #3a3a3a; padding: 4px 10px; border-radius: 4px;")
