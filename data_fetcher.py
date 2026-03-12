import threading
import queue
from datetime import datetime, time as dtime
import numpy as np
import yfinance as yf
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:
    import pytz
    _ET = pytz.timezone("America/New_York")

HIST_WINDOW = 200  # trading days minimum for realized vol calculation
_EXTENDED_INTERVAL = 300  # seconds between extended-hours fetches (5 min)
_CLOSED_INTERVAL   = 60   # seconds to sleep when market is closed (recheck session)


def _get_session() -> str:
    """Return 'pre', 'regular', 'post', or 'closed' based on US/Eastern time."""
    now = datetime.now(_ET)
    if now.weekday() >= 5:          # Saturday / Sunday
        return "closed"
    t = now.time()
    if dtime(4, 0) <= t < dtime(9, 30):
        return "pre"
    if dtime(9, 30) <= t < dtime(16, 0):
        return "regular"
    if dtime(16, 0) <= t < dtime(20, 0):
        return "post"
    return "closed"


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
        first_run = True
        while not self._stop_event.is_set():
            if not self._pause_event.wait(timeout=0.5):
                continue  # still paused; loop to recheck stop_event
            if self._stop_event.is_set():
                return

            # On launch always do one regular fetch so the UI populates immediately
            # regardless of the current market session.
            if first_run:
                session = "regular"
                first_run = False
            else:
                session = _get_session()

            if self.symbols and session != "closed":
                print(f"[fetcher] session={session}, fetching {len(self.symbols)} symbols...", flush=True)
                if session == "regular":
                    data = self._fetch()
                    wait_secs = self.interval
                else:
                    data = self._fetch_extended(session)
                    wait_secs = _EXTENDED_INTERVAL
                print(f"[fetcher] got {len(data)} results", flush=True)
                if data:
                    data["__session__"] = session
                    self._queue.put(data)
            else:
                wait_secs = _CLOSED_INTERVAL

            self._stop_event.wait(wait_secs)

    # ------------------------------------------------------------------
    # Regular-hours fetch  (fast_info + realized vol)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Extended-hours fetch  (ticker.info, equities/ETFs only)
    # ------------------------------------------------------------------
    def _fetch_extended(self, session: str) -> dict:
        """Fetch pre- or post-market prices via ticker.info.

        Indices (symbols starting with '^') are skipped — they don't trade
        extended hours. Regular-session data from the initial fetch is already
        in the UI; this only updates equity/ETF prices.
        """
        result = {}
        equity_symbols = [s for s in self.symbols if not s.startswith("^")]
        for symbol in equity_symbols:
            try:
                info = yf.Ticker(symbol).info
                if session == "pre":
                    price = info.get("preMarketPrice")
                    ref   = info.get("regularMarketPreviousClose") or info.get("previousClose")
                else:  # post
                    price = info.get("postMarketPrice")
                    ref   = info.get("regularMarketPrice") or info.get("regularMarketPreviousClose")

                if price is None or ref is None or ref == 0:
                    print(f"[fetcher] {symbol}: no {session} price", flush=True)
                    continue
                if not (np.isfinite(price) and np.isfinite(ref)):
                    continue

                return_pct = (price - ref) / ref * 100
                result[symbol.upper()] = {
                    "price": price,
                    "prev_close": ref,
                    "return_pct": return_pct,
                    "sigma_move": None,
                }
            except Exception as e:
                print(f"[fetcher] {symbol} extended error: {e}", flush=True)
        return result
