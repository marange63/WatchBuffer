import uuid
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QToolBar, QAction, QScrollArea, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel
)
from PyQt5.QtCore import Qt

import persistence
from data_fetcher import DataFetcher
from dialogs import PaneNameDialog, AliasEditorDialog
from pane_widget import WatchPane
from market_bar import MarketBar, BENCHMARK_SYMBOLS


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WatchBuffer")
        self.resize(1100, 600)

        self._panes = []
        self._fetcher = None
        self._aliases = {}
        self._mode = "return"

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

        self._load_panes()
        self._aliases = persistence.load_aliases()
        self._apply_aliases()
        self._restart_fetcher()

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        self.addToolBar(tb)
        add_action = QAction("+ Add Pane", self)
        add_action.triggered.connect(self._add_pane)
        tb.addAction(add_action)
        alias_action = QAction("Aliases", self)
        alias_action.triggered.connect(self._edit_aliases)
        tb.addAction(alias_action)
        self._mode_action = QAction("Mode: % Return", self)
        self._mode_action.triggered.connect(self._toggle_mode)
        tb.addAction(self._mode_action)

    def _build_central(self):
        self._market_bar = MarketBar()

        self._scroll = QScrollArea()
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setWidgetResizable(True)

        self._container = QWidget()
        self._layout = QHBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        self._scroll.setWidget(self._container)

        central = QWidget()
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self._market_bar)
        vbox.addWidget(self._scroll)
        self.setCentralWidget(central)

    def _build_statusbar(self):
        self._status_label = QLabel("No data yet")
        self.statusBar().addWidget(self._status_label)

    def _load_panes(self):
        for pd in persistence.load():
            self._create_pane(pd["id"], pd["name"], pd.get("symbols", []), save=False)

    def _create_pane(self, pane_id, name, symbols, save=True):
        pane = WatchPane(pane_id, name, symbols)
        pane.deleted.connect(self._on_pane_deleted)
        pane.symbols_changed.connect(self._on_symbols_changed)
        self._panes.append(pane)
        self._layout.addWidget(pane, stretch=1)
        pane.update_aliases(self._aliases)
        pane.set_mode(self._mode)
        if save:
            self._save()

    def _add_pane(self):
        dlg = PaneNameDialog(self)
        if dlg.exec_() != dlg.Accepted:
            return
        self._create_pane(str(uuid.uuid4()), dlg.get_name(), [])
        self._restart_fetcher()

    def _on_pane_deleted(self, pane_id):
        pane = next((p for p in self._panes if p.pane_id == pane_id), None)
        if pane is None:
            return
        self._layout.removeWidget(pane)
        pane.deleteLater()
        self._panes.remove(pane)
        self._save()
        self._restart_fetcher()

    def _on_symbols_changed(self, pane_id):
        self._save()
        self._restart_fetcher()

    def _save(self):
        persistence.save([p.to_dict() for p in self._panes])

    def _all_symbols(self):
        seen = set()
        result = []
        for sym in BENCHMARK_SYMBOLS:
            seen.add(sym)
            result.append(sym)
        for p in self._panes:
            for sym in p.symbols:
                upper = sym.upper()
                if upper not in seen:
                    seen.add(upper)
                    result.append(upper)
        return result

    def _all_known_symbols(self):
        seen = set()
        result = []
        for sym in BENCHMARK_SYMBOLS:
            seen.add(sym)
            result.append(sym)
        for p in self._panes:
            for sym in p.symbols:
                upper = sym.upper()
                if upper not in seen:
                    seen.add(upper)
                    result.append(upper)
        return result

    def _apply_aliases(self):
        self._market_bar.set_aliases(self._aliases)
        for pane in self._panes:
            pane.update_aliases(self._aliases)
        pane.set_mode(self._mode)

    def _edit_aliases(self):
        dlg = AliasEditorDialog(self, self._all_known_symbols(), self._aliases)
        if dlg.exec_() != dlg.Accepted:
            return
        self._aliases = dlg.get_aliases()
        persistence.save_aliases(self._aliases)
        self._apply_aliases()
        for pane in self._panes:
            if hasattr(pane, '_last_data'):
                pane.update_chart(pane._last_data)

    def _toggle_mode(self):
        self._mode = "sigma" if self._mode == "return" else "return"
        label = "Mode: % Return" if self._mode == "return" else "Mode: σ Move"
        self._mode_action.setText(label)
        for pane in self._panes:
            pane.set_mode(self._mode)
            if hasattr(pane, "_last_data"):
                pane.update_chart(pane._last_data)
        self._market_bar.set_mode(self._mode)
        if hasattr(self, "_last_data"):
            self._market_bar.refresh(self._last_data)

    def _restart_fetcher(self):
        if self._fetcher is not None:
            self._fetcher.stop()
            self._fetcher.wait(3000)
        self._fetcher = DataFetcher(self._all_known_symbols(), interval=60)
        self._fetcher.data_ready.connect(self.on_data_ready)
        self._fetcher.start()

    def on_data_ready(self, data):
        self._last_data = data
        self._market_bar.refresh(data)
        for pane in self._panes:
            pane._last_data = data
            pane.update_chart(data)
        ts = datetime.now().strftime("%H:%M:%S")
        self._status_label.setText(f"Last update: {ts}  |  {len(data)} symbols loaded")

    def closeEvent(self, event):
        if self._fetcher is not None:
            self._fetcher.stop()
            self._fetcher.wait(5000)
        event.accept()
