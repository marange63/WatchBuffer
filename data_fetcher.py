import threading
import yfinance as yf
from PyQt5.QtCore import QThread, pyqtSignal


class DataFetcher(QThread):
    data_ready = pyqtSignal(dict)

    def __init__(self, symbols: list, interval: int = 60):
        super().__init__()
        self.symbols = symbols
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        self._stop_event.clear()
        while not self._stop_event.is_set():
            if self.symbols:
                data = self._fetch()
                if data:
                    self.data_ready.emit(data)
            self._stop_event.wait(self.interval)

    def stop(self):
        self._stop_event.set()

    def _fetch(self) -> dict:
        result = {}
        try:
            symbols_str = " ".join(self.symbols)
            tickers = yf.Tickers(symbols_str)
            for symbol in self.symbols:
                try:
                    info = tickers.tickers[symbol.upper()].fast_info
                    last_price = info.last_price
                    prev_close = info.regular_market_previous_close
                    if last_price is None or prev_close is None or prev_close == 0:
                        continue
                    return_pct = (last_price - prev_close) / prev_close * 100
                    result[symbol.upper()] = {
                        "price": last_price,
                        "prev_close": prev_close,
                        "return_pct": return_pct,
                    }
                except Exception:
                    pass
        except Exception:
            pass
        return result
