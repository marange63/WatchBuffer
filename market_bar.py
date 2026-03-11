from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

BENCHMARK_SYMBOLS = ["SPY", "QQQ", "IWM", "^DJI", "^TNX", "^VIX", "^MOVE"]
DISPLAY_NAMES = {"SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "^DJI": "DJIA", "^TNX": "10Y", "^VIX": "VIX", "^MOVE": "MOVE"}


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
        self._mode = "return"

    def set_aliases(self, aliases: dict):
        self._aliases = aliases

    def set_mode(self, mode: str):
        self._mode = mode

    def refresh(self, data: dict):
        for sym in BENCHMARK_SYMBOLS:
            info = data.get(sym)
            lbl = self._labels[sym]
            name = self._aliases.get(sym) or DISPLAY_NAMES[sym]
            if info is None:
                lbl.setText(f"{name}  --")
                lbl.setStyleSheet("color: #aaaaaa; font-size: 16px; background-color: #3a3a3a; padding: 4px 10px; border-radius: 4px;")
            elif sym in ("^TNX", "^VIX", "^MOVE"):
                price = info["price"]
                change = price - info["prev_close"]
                sign = "+" if change >= 0 else ""
                color = "#e74c3c" if change >= 0 else "#2ecc71"
                if sym == "^TNX":
                    bps = change * 100
                    metric_str = f"{sign}{bps:.1f}bps"
                    price_str = f"{price:.2f}%"
                else:
                    metric_str = f"{sign}{change:.2f}"
                    price_str = f"{price:.2f}"
                lbl.setText(f"{name}  {price_str}  {metric_str}")
                lbl.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; background-color: #3a3a3a; padding: 4px 10px; border-radius: 4px;")
            else:
                price = info["price"]
                color = "#aaaaaa"
                price_str = f"{price:,.2f}" if price >= 100 else f"{price:.2f}"
                if self._mode == "sigma" and info.get("sigma_move") is not None:
                    val = info["sigma_move"]
                    sign = "+" if val >= 0 else ""
                    metric_str = f"{sign}{val:.2f}{chr(0x03c3)}"
                    color = "#2ecc71" if val >= 0 else "#e74c3c"
                else:
                    ret = info["return_pct"]
                    sign = "+" if ret >= 0 else ""
                    metric_str = f"{sign}{ret:.2f}%"
                    color = "#2ecc71" if ret >= 0 else "#e74c3c"
                lbl.setText(f"{name}  {price_str}  {metric_str}")
                lbl.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; background-color: #3a3a3a; padding: 4px 10px; border-radius: 4px;")
