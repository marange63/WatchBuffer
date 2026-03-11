import uuid
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QToolBar, QAction, QScrollArea, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QComboBox
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
        self._vol_period = "2y"
        self._sort_mode = "abs_desc"

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
        self._vol_combo = QComboBox()
        self._vol_combo.addItems(["Vol: 1Y", "Vol: 2Y", "Vol: 3Y"])
        self._vol_combo.setCurrentIndex(1)
        self._vol_combo.currentIndexChanged.connect(self._on_vol_changed)
        tb.addWidget(self._vol_combo)
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Sort: |Δ| Desc", "Sort: Desc"])
        self._sort_combo.setCurrentIndex(0)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        tb.addWidget(self._sort_combo)
        self._pause_action = QAction("Pause", self)
        self._pause_action.triggered.connect(self._toggle_pause)
        tb.addAction(self._pause_action)

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
        pane.set_sort_mode(self._sort_mode)
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
                try:
                    pane.update_chart(pane._last_data)
                except Exception:
                    import traceback
                    print(f"[toggle_mode] {pane.pane_name} error:", flush=True)
                    traceback.print_exc()
        self._market_bar.set_mode(self._mode)
        if hasattr(self, "_last_data"):
            self._market_bar.refresh(self._last_data)

    def _toggle_pause(self):
        if self._fetcher is None:
            return
        if self._fetcher.paused:
            self._fetcher.resume()
            self._pause_action.setText("Pause")
        else:
            self._fetcher.pause()
            self._pause_action.setText("Resume")

    def _on_sort_changed(self, index):
        self._sort_mode = ["abs_desc", "desc"][index]
        for pane in self._panes:
            pane.set_sort_mode(self._sort_mode)
            if hasattr(pane, "_last_data"):
                try:
                    pane.update_chart(pane._last_data)
                except Exception:
                    import traceback
                    traceback.print_exc()

    def _on_vol_changed(self, index):
        self._vol_period = ["1y", "2y", "3y"][index]
        self._restart_fetcher()

    def _restart_fetcher(self):
        if self._fetcher is not None:
            self._fetcher.stop()
            self._fetcher.wait(3000)
        self._fetcher = DataFetcher(self._all_known_symbols(), interval=60, vol_period=self._vol_period)
        self._fetcher.data_ready.connect(self.on_data_ready)
        self._fetcher.start()
        self._pause_action.setText("Pause")

    def on_data_ready(self, data):
        self._last_data = data
        try:
            self._market_bar.refresh(data)
        except Exception as e:
            print(f"[market_bar] refresh error: {e}", flush=True)
        for pane in self._panes:
            pane._last_data = data
            try:
                pane.update_chart(data)
            except Exception as e:
                import traceback
                print(f"[pane {pane.pane_name}] update_chart error:", flush=True)
                traceback.print_exc()
        ts = datetime.now().strftime("%H:%M:%S")
        self._status_label.setText(f"Last update: {ts}  |  {len(data)} symbols loaded")

    def closeEvent(self, event):
        if self._fetcher is not None:
            self._fetcher.stop()
            self._fetcher.wait(5000)
        event.accept()
