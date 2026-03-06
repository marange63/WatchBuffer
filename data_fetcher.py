import threading
import numpy as np
import yfinance as yf
from PyQt5.QtCore import QThread, pyqtSignal

HIST_WINDOW = 252  # trading days used for realized vol (~1 year)


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
                    ticker = tickers.tickers[symbol.upper()]
                    info = ticker.fast_info
                    last_price = info.last_price
                    prev_close = info.regular_market_previous_close
                    if last_price is None or prev_close is None or prev_close == 0:
                        continue
                    return_pct = (last_price - prev_close) / prev_close * 100
                    today_log_ret = np.log(last_price / prev_close)

                    sigma_move = None
                    try:
                        hist = ticker.history(period="1y", auto_adjust=True)
                        if len(hist) >= HIST_WINDOW:
                            closes = hist["Close"]
                            log_rets = np.log(closes / closes.shift(1)).dropna()
                            daily_std = log_rets.std()
                            if daily_std > 0:
                                sigma_move = today_log_ret / daily_std
                    except Exception:
                        pass

                    result[symbol.upper()] = {
                        "price": last_price,
                        "prev_close": prev_close,
                        "return_pct": return_pct,
                        "sigma_move": sigma_move,
                    }
                except Exception:
                    pass
        except Exception:
            pass
        return result
