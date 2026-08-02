# indicators.py
# Pure indicator math. No network calls live here so it can be unit tested
# in isolation from the Binance API.

import pandas as pd


def calculate_ema(closes, period):
    """
    Calculate an Exponential Moving Average series.

    closes: list[float] of closing prices, oldest first.
    period: EMA period (e.g. 140).

    Returns a pandas Series aligned with the input closes.
    """
    series = pd.Series(closes, dtype="float64")
    return series.ewm(span=period, adjust=False).mean()


def calculate_bollinger_bands(closes, period, std_dev):
    """
    Calculate Bollinger Bands (upper and lower) for a series of closes.

    closes: list[float] of closing prices, oldest first.
    period: rolling window length (e.g. 20).
    std_dev: standard deviation multiplier (e.g. 2.0).

    Returns (upper_band, lower_band) as pandas Series aligned with input.
    """
    series = pd.Series(closes, dtype="float64")
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std(ddof=0)
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return upper, lower


def count_valid_candles(closes, ema_period, bb_period, bb_std, lookback):
    """
    Given a full history of closing prices, calculate EMA and Bollinger
    Bands across the whole series, then check the most recent `lookback`
    candles for the condition:

        lower_band <= EMA <= upper_band

    Returns the integer count of candles (within the lookback window)
    where the condition holds true. Candles where indicators are not yet
    defined (NaN, due to insufficient warm-up history) count as invalid.
    """
    ema = calculate_ema(closes, ema_period)
    upper, lower = calculate_bollinger_bands(closes, bb_period, bb_std)

    valid = (lower <= ema) & (ema <= upper)
    valid = valid.fillna(False)

    recent = valid.iloc[-lookback:]
    return int(recent.sum())
