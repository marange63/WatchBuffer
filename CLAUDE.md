# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WatchBuffer is a Python desktop app that polls Yahoo Finance via yfinance and displays near-live daily returns and sigma moves as color-coded horizontal bar charts in named, persistent watchlist panes.

## Running the Project

```bash
python main.py
```

## Tech Stack

- **GUI:** PyQt5
- **Charts:** matplotlib (Qt5Agg backend via `FigureCanvasQTAgg` -- all-caps QT, not Qt; matplotlib 3.10+ renamed it)
- **Data:** yfinance (`fast_info.last_price`, `fast_info.regular_market_previous_close`, `ticker.history()`)
- **Persistence:** `watchlists.json` (atomic write via `.tmp` rename)
- **Python env:** conda env named `WatchBuffer`

## File Structure

```
main.py           # Entry point
app.py            # MainWindow: toolbar, scroll area, fetcher wiring
pane_widget.py    # WatchPane: matplotlib bar chart + header controls
data_fetcher.py   # Background fetch thread + QTimer queue drain
market_bar.py     # Dark top strip showing SPY/QQQ/IWM/^DJI
dialogs.py        # PaneNameDialog, SecuritiesEditorDialog, AliasEditorDialog
persistence.py    # load/save watchlists.json and aliases
watchlists.json   # Auto-created on first run
```

## Architecture Notes

- **DataFetcher** uses `threading.Thread` (NOT QThread) -- yfinance uses curl_cffi which crashes with
  STATUS_STACK_BUFFER_OVERRUN (0xC0000409) when called from a QThread on Windows. Results pass back
  to Qt via `queue.Queue` drained by a `QTimer` every 500ms.
- **yfinance 1.2.0** requires curl_cffi internally; do NOT pass a `requests.Session` to yfinance calls
  (it raises an explicit error rejecting non-curl sessions).
- **Realized vol:** `HIST_WINDOW = 200` rows minimum (yfinance `period='1y'` returns ~251 rows;
  using 252 caused nearly all symbols to be skipped). Sigma move = `log(last/prev) / daily_std`.
- **Two display modes:** `return` (% daily return) and `sigma` (sigma move). Toggled via toolbar.
  Symbols without enough history fall back to return_pct in sigma mode.
- **Benchmark symbols** (`SPY QQQ IWM ^DJI`) are always fetched regardless of pane contents.
- **`fast_info.regular_market_previous_close`** -- use this for prev close, not `previous_close`
  (which returns wrong values like today's high).
- **Unicode constants** in pane_widget.py use `chr()` calls to avoid cp1252 encoding issues on Windows:
  `SIGMA = chr(0x03c3)`, `UP = chr(0x25b2)`, `DOWN = chr(0x25bc)`.
- **File writes** must specify `encoding='utf-8'`; Windows default is cp1252 which breaks Unicode.
- **Error handling:** wrap all slot callbacks (update_chart, refresh) in try/except -- unhandled
  exceptions in PyQt5 slots abort the loop, leaving later panes unupdated.

## Known Limitations

- OTC/pink-sheet stocks (e.g. CRVW) may show wrong prices -- yfinance data quality issue, not a code bug.
- Symbols with fewer than 200 days of history will not show sigma moves (shown in % return instead).
