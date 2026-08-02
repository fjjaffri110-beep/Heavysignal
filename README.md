# Crypto Scanner

A Binance Futures USDT-perpetual scanner. **This is not a trading bot and
does not generate buy/sell signals.** It only displays the names of coins
whose EMA(140) has stayed inside its Bollinger Band(20, 2.0) envelope for
enough of the most recent closed candles.

## Rules

**Daily:** of the last 20 CLOSED daily candles, at least 15 must satisfy
`lowerBand <= EMA140 <= upperBand`.

**4 Hour:** of the last 40 CLOSED 4H candles, at least 25 must satisfy the
same condition.

Only matching coin symbols are shown - no entries, stop losses, take
profits, or trade history.

## Project structure

```
crypto-scanner/
├── app.py              # Flask app, routes, background scheduler
├── scanner.py          # Binance API calls + scan orchestration
├── indicators.py       # EMA / Bollinger Band math
├── config.py           # All tunable constants
├── requirements.txt
├── Procfile             # Railway/Heroku start command
├── runtime.txt           # Python version pin
├── templates/
│   └── index.html
└── static/
    └── style.css
```

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in your browser. The first scan starts
automatically on launch and takes a few minutes to cover every USDT
perpetual futures symbol on Binance. After that it re-scans automatically
every 15 minutes, and you can trigger an extra scan any time with the
**Refresh Scanner** button.

## Deploying to Railway

1. Push this folder to a new GitHub repository.
2. In Railway, choose **New Project → Deploy from GitHub repo** and select
   the repository.
3. Railway will detect `requirements.txt` and `Procfile` automatically and
   use them to build and start the app — no manual configuration needed.
4. Once deployed, open the generated Railway URL to view the dashboard.

No environment variables or API keys are required — the app only calls
Binance's public Futures API endpoints.

## How it works

- **`GET /fapi/v1/exchangeInfo`** is used to list every actively trading
  USDT-margined PERPETUAL futures symbol.
- **`GET /fapi/v1/klines`** is used to fetch recent candle data per symbol,
  for both the `1d` and `4h` intervals. The most recent (still-forming)
  candle is always discarded so only fully closed candles are analyzed.
- For each symbol/timeframe, `indicators.py` computes an EMA(140) series
  and Bollinger Bands(20, 2.0) across the fetched history, then counts how
  many of the most recent candles satisfy the "EMA inside the bands"
  condition.
- Symbols that clear the minimum valid-candle threshold are added to that
  timeframe's result list. Results are de-duplicated and sorted
  alphabetically.
- A background thread (`app.py`) re-runs the full scan automatically every
  15 minutes and also supports on-demand refresh via the dashboard button,
  which starts a scan in a separate thread so the UI stays responsive and
  shows a live progress bar while it runs.

## Notes on rate limits

Scanning every futures symbol on two timeframes issues a large number of
requests to Binance. The scanner uses a small thread pool (`MAX_WORKERS`
in `config.py`) and automatically backs off and retries if Binance
responds with a rate-limit status code. If you see scan errors under
heavy load, lower `MAX_WORKERS` in `config.py`.
