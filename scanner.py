# scanner.py
# Handles all communication with the Binance Futures public API and
# orchestrates the concurrent scan across every USDT-M perpetual symbol.
#
# This module never generates buy/sell signals. It only determines,
# per the rules in config.py, whether a coin's EMA(140) has spent enough
# of its recent candles inside its Bollinger Band envelope to be
# considered "matching" on a given timeframe.

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from indicators import count_valid_candles


def get_futures_symbols():
    """
    Fetch every actively trading USDT-margined PERPETUAL futures symbol
    from Binance Futures Exchange Information endpoint.
    """
    url = f"{config.BINANCE_FUTURES_BASE}/fapi/v1/exchangeInfo"
    resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    symbols = []
    for s in data.get("symbols", []):
        if (
            s.get("quoteAsset") == "USDT"
            and s.get("contractType") == "PERPETUAL"
            and s.get("status") == "TRADING"
        ):
            symbols.append(s["symbol"])
    return symbols


def fetch_closes(symbol, interval, limit):
    """
    Fetch kline data for a symbol/interval from Binance Futures and
    return a list of CLOSED candle closing prices, oldest first.

    The most recent candle returned by Binance may still be forming, so
    it is always dropped to guarantee we only ever analyze closed
    candles, as required by the scanning rules.
    """
    url = f"{config.BINANCE_FUTURES_BASE}/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)

            if resp.status_code in (429, 418):
                # Rate limited / banned briefly - back off and retry.
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else 2 * (attempt + 1)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            raw = resp.json()

            if not raw or len(raw) < 2:
                return None

            # Drop the last candle - it may still be forming (unclosed).
            closed = raw[:-1]

            # Kline format: [open_time, open, high, low, close, volume, ...]
            closes = [float(c[4]) for c in closed]
            return closes

        except (requests.RequestException, ValueError, KeyError, IndexError):
            time.sleep(1 * (attempt + 1))

    return None


def analyze_symbol_daily(symbol):
    """Return the symbol if it matches the Daily rule, else None."""
    closes = fetch_closes(symbol, "1d", config.DAILY_FETCH_LIMIT)
    if not closes or len(closes) < config.DAILY_CANDLES:
        return None

    valid_count = count_valid_candles(
        closes,
        config.EMA_PERIOD,
        config.BB_PERIOD,
        config.BB_STD,
        config.DAILY_CANDLES,
    )

    if valid_count >= config.DAILY_MIN_VALID:
        return symbol
    return None


def analyze_symbol_h4(symbol):
    """Return the symbol if it matches the 4H rule, else None."""
    closes = fetch_closes(symbol, "4h", config.H4_FETCH_LIMIT)
    if not closes or len(closes) < config.H4_CANDLES:
        return None

    valid_count = count_valid_candles(
        closes,
        config.EMA_PERIOD,
        config.BB_PERIOD,
        config.BB_STD,
        config.H4_CANDLES,
    )

    if valid_count >= config.H4_MIN_VALID:
        return symbol
    return None


def run_scan(progress_callback=None):
    """
    Run a complete fresh scan across every Binance USDT-M perpetual
    futures symbol, on both the Daily and 4H timeframes.

    progress_callback, if provided, is called as
        progress_callback(completed, total)
    after each symbol/timeframe check finishes, so callers can report
    live progress to a UI.

    Returns (daily_matches, h4_matches) - two sorted lists of unique
    coin symbol strings. Never returns duplicate entries within a
    timeframe.
    """
    symbols = get_futures_symbols()

    daily_matches = []
    h4_matches = []

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_map = {}
        for sym in symbols:
            future_map[executor.submit(analyze_symbol_daily, sym)] = ("daily", sym)
            future_map[executor.submit(analyze_symbol_h4, sym)] = ("h4", sym)

        total = len(future_map)
        completed = 0

        for future in as_completed(future_map):
            timeframe, sym = future_map[future]
            try:
                result = future.result()
                if result:
                    if timeframe == "daily":
                        daily_matches.append(result)
                    else:
                        h4_matches.append(result)
            except Exception:
                # A single symbol failing should never abort the whole scan.
                pass

            completed += 1
            if progress_callback:
                progress_callback(completed, total)

    daily_matches = sorted(set(daily_matches))
    h4_matches = sorted(set(h4_matches))

    return daily_matches, h4_matches
