# app.py
# Crypto Scanner - Flask web application.
#
# IMPORTANT: This application does NOT generate buy/sell signals and is
# NOT a trading bot. It only scans Binance Futures USDT perpetual coins
# and displays the names of coins matching a purely technical condition
# (EMA140 staying inside its Bollinger Band envelope on recent closed
# candles). See README.md for full rules.

import threading
import time
import datetime

from flask import Flask, render_template, jsonify

import config
from scanner import run_scan

app = Flask(__name__)

# ---------------------------------------------------------------------
# In-memory application state.
# A single lock guards all reads/writes since the app runs as a single
# gunicorn worker (see Procfile) with multiple threads.
# ---------------------------------------------------------------------
state_lock = threading.Lock()
state = {
    "status": "idle",          # "idle" | "scanning"
    "last_scan_time": None,    # ISO 8601 UTC string
    "daily": [],
    "h4": [],
    "progress": {"completed": 0, "total": 0},
    "error": None,
}


def do_scan():
    """Run one full scan and update the shared state. Safe to call from
    the scheduler thread or a manually-triggered refresh thread."""
    with state_lock:
        if state["status"] == "scanning":
            return
        state["status"] = "scanning"
        state["error"] = None
        state["progress"] = {"completed": 0, "total": 0}

    def progress_cb(completed, total):
        with state_lock:
            state["progress"] = {"completed": completed, "total": total}

    try:
        daily, h4 = run_scan(progress_callback=progress_cb)
        with state_lock:
            state["daily"] = daily
            state["h4"] = h4
            state["last_scan_time"] = datetime.datetime.utcnow().isoformat() + "Z"
            state["status"] = "idle"
    except Exception as exc:
        with state_lock:
            state["error"] = str(exc)
            state["status"] = "idle"


def scheduler_loop():
    """Background loop: scan immediately on startup, then every
    SCAN_INTERVAL_MINUTES minutes, forever. No manual restart required."""
    while True:
        do_scan()
        time.sleep(config.SCAN_INTERVAL_MINUTES * 60)


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/results")
def api_results():
    """Polled by the dashboard to display current results / progress."""
    with state_lock:
        return jsonify({
            "status": state["status"],
            "last_scan_time": state["last_scan_time"],
            "daily": state["daily"],
            "h4": state["h4"],
            "progress": state["progress"],
            "error": state["error"],
        })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Manually trigger a fresh scan. Non-blocking: starts a background
    thread and returns immediately so the UI can show a loading state
    while polling /api/results."""
    with state_lock:
        if state["status"] == "scanning":
            return jsonify({"started": False, "message": "A scan is already in progress."})

    threading.Thread(target=do_scan, daemon=True).start()
    return jsonify({"started": True})


# ---------------------------------------------------------------------
# Start the automatic background scheduler as soon as the module loads,
# so it runs both under `python app.py` and under gunicorn.
# ---------------------------------------------------------------------
_scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
_scheduler_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
