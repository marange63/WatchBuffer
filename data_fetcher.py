import threading
import queue
import numpy as np
import yfinance as yf
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

HIST_WINDOW = 200  # trading days minimum for realized vol calculation


class DataFetcher(QObject):
    data_ready = pyqtSignal(dict)

    def __init__(self, symbols: list, interval: int = 60, vol_period: str = "1y"):
        super().__init__()
        self.symbols = symbols
        self.interval = interval
        self.vol_period = vol_period
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # starts unpaused
        self._queue = queue.Queue()
        self._thread = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start(500)

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    @property
    def paused(self) -> bool:
        return not self._pause_event.is_set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # unblock thread so it can exit
        self._timer.stop()

    def wait(self, msecs: int = 3000):
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=msecs / 1000)

    def _drain_queue(self):
        while not self._queue.empty():
            try:
                data = self._queue.get_nowait()
                self.data_ready.emit(data)
            except queue.Empty:
                break

    def _run(self):
        while not self._stop_event.is_set():
            if not self._pause_event.wait(timeout=0.5):
                continue  # still paused; loop to recheck stop_event
            if self._stop_event.is_set():
                return
            if self.symbols:
                print(f"[fetcher] fetching {len(self.symbols)} symbols...", flush=True)
                data = self._fetch()
                print(f"[fetcher] got {len(data)} results", flush=True)
                if data:
                    self._queue.put(data)
            self._stop_event.wait(self.interval)

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
                        print(f"[fetcher] {symbol}: missing price/prev_close", flush=True)
                        continue
                    return_pct = (last_price - prev_close) / prev_close * 100
                    today_log_ret = np.log(last_price / prev_close)

                    sigma_move = None
                    try:
                        hist = ticker.history(period=self.vol_period, auto_adjust=True)
                        if len(hist) >= HIST_WINDOW:
                            closes = hist["Close"]
                            log_rets = np.log(closes / closes.shift(1)).dropna()
                            daily_std = log_rets.std()
                            if daily_std > 0:
                                sigma_move = today_log_ret / daily_std

                    except Exception as e:
                        print(f"[fetcher] {symbol} history error: {e}", flush=True)

                    result[symbol.upper()] = {
                        "price": last_price,
                        "prev_close": prev_close,
                        "return_pct": return_pct,
                        "sigma_move": sigma_move,
                    }
                except Exception as e:
                    print(f"[fetcher] {symbol} error: {e}", flush=True)
        except Exception as e:
            print(f"[fetcher] outer error: {e}", flush=True)
        return result
