# config.py
# Central configuration for the Crypto Scanner application.
# Change values here to tune scanning behaviour without touching logic code.

# Binance Futures public API base URL
BINANCE_FUTURES_BASE = "https://fapi.binance.com"

# ---- Indicator settings ----
EMA_PERIOD = 140
BB_PERIOD = 20
BB_STD = 2.0

# ---- Daily timeframe rules ----
DAILY_CANDLES = 20          # look at the last 20 CLOSED daily candles
DAILY_MIN_VALID = 15        # at least 15 of those must satisfy the condition
# How many raw candles to fetch from Binance for the daily timeframe.
# We fetch extra history so the EMA(140) has enough warm-up data before we
# evaluate the most recent DAILY_CANDLES. +1 is fetched and the last
# (still-forming) candle is dropped so we only ever analyze CLOSED candles.
DAILY_FETCH_LIMIT = 301

# ---- 4 Hour timeframe rules ----
H4_CANDLES = 40             # look at the last 40 CLOSED 4H candles
H4_MIN_VALID = 25           # at least 25 of those must satisfy the condition
H4_FETCH_LIMIT = 301

# ---- Scheduler ----
SCAN_INTERVAL_MINUTES = 15

# ---- Networking / concurrency ----
# Number of concurrent worker threads used to hit the Binance API while
# scanning. Kept modest to avoid tripping Binance's rate limits.
MAX_WORKERS = 8

# Number of retry attempts per API request before giving up on a symbol.
MAX_RETRIES = 3

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 15
