"""
Pre-Breakout Scanner — Historical Backtester
===============================================
Walk-forward replay of engine.evaluate_candidate() over real historical
KuCoin OHLCV data. This is what "the system learns what was right and what
went wrong" is built on: every candidate the strategy WOULD have flagged
gets resolved against its own future candles (which we already have, since
it's history) and logged to state/trade_log.jsonl alongside live results.
tuner.py then reads that combined log to find what's working.

Known limitation: the live-only microstructure gates (taker buy/sell ratio,
order book imbalance, Binance/Crypto.com cross-validation) can't be replayed
historically — this backtest only exercises the OHLCV-only half of the
pipeline (engine.evaluate_candidate). Treat its win rates as directionally
useful, not as an exact match to what live alerts would have done.

Run manually:  python backtest.py
Or via the weekly `backtest.yml` GitHub Actions workflow.
"""

import bisect
import sys
import time
from datetime import datetime, timezone

import ccxt

import config as cfg
from engine import evaluate_candidate, evaluate_reversal_candidate, append_trade_log, load_trade_log


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{ts}] {msg}", flush=True)


def ohlcv_to_dicts(raw: list) -> list:
    return [
        {"ts": r[0], "open": r[1], "high": r[2], "low": r[3],
         "close": r[4], "volume": r[5]}
        for r in raw
    ]


def fetch_ohlcv_range(exchange, symbol: str, timeframe: str, since_ms: int, until_ms: int) -> list:
    """Paginated historical fetch covering [since_ms, until_ms]."""
    tf_ms = exchange.parse_timeframe(timeframe) * 1000
    cursor = since_ms
    seen = {}
    while cursor < until_ms:
        try:
            batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=1000)
        except Exception as e:
            log(f"  ⚠️  fetch_ohlcv failed for {symbol} {timeframe} @ {cursor}: {e}")
            break
        if not batch:
            break
        for c in batch:
            seen[c[0]] = c
        last_ts = batch[-1][0]
        if last_ts <= cursor or len(batch) < 2:
            break
        cursor = last_ts + tf_ms
        time.sleep(cfg.RATE_LIMIT_SLEEP)
    merged = sorted(seen.values(), key=lambda c: c[0])
    return [c for c in merged if since_ms <= c[0] <= until_ms]


def _window_ending_at(candles: list, ts_list: list, cutoff_ts: int, size: int) -> list:
    """Returns up to `size` candles from `candles` with ts <= cutoff_ts."""
    idx = bisect.bisect_right(ts_list, cutoff_ts)
    if idx == 0:
        return []
    return candles[max(0, idx - size): idx]


def pick_symbol_universe(exchange) -> list:
    markets = exchange.load_markets()
    tickers = exchange.fetch_tickers()
    excluded_bases = {"BTC", "ETH", "USDC", "BUSD", "DAI", "TUSD", "FDUSD"}
    candidates = []
    for sym, m in markets.items():
        if not (m.get("quote") == cfg.QUOTE and m.get("active", True) and m.get("spot", True) and "/" in sym):
            continue
        base = sym.split("/")[0]
        if base in excluded_bases:
            continue
        t = tickers.get(sym) or {}
        qv = t.get("quoteVolume") or 0
        if qv >= cfg.BACKTEST_MIN_QUOTE_VOL:
            candidates.append((sym, qv))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in candidates[: cfg.BACKTEST_MAX_SYMBOLS]]


def resolve_outcome(future_15m: list, sl: float, tp1: float, tp2: float, max_bars: int) -> tuple:
    """
    Same SL-priority logic as scanner.evaluate_outcome, but resolved
    directly against already-fetched future candles.
    Returns (outcome, resolved_ts).
    """
    for c in future_15m[:max_bars]:
        if c["low"] <= sl:
            return "sl_hit", c["ts"]
        if tp2 is not None and c["high"] >= tp2:
            return "tp2_hit", c["ts"]
        if c["high"] >= tp1:
            return "tp1_hit", c["ts"]
    resolved_ts = future_15m[min(len(future_15m), max_bars) - 1]["ts"] if future_15m else None
    return "expired", resolved_ts


def _log_candidate(symbol: str, pipeline: str, result: dict, window: list, candles_15m: list,
                   i: int, existing_keys: set) -> bool:
    """Resolves one candidate against its own future candles and appends to
    the trade log if not already logged. Returns True if newly logged."""
    alert_ts  = window[-1]["ts"]
    alert_iso = datetime.fromtimestamp(alert_ts / 1000, tz=timezone.utc).isoformat()
    key = (symbol, alert_iso, "backtest", pipeline)
    if key in existing_keys:
        return False

    future = candles_15m[i + 1:]
    outcome, resolved_ts = resolve_outcome(future, result["sl"], result["tp1"], result["tp2"],
                                           cfg.BACKTEST_MAX_HOLD_BARS)
    resolved_iso = (datetime.fromtimestamp(resolved_ts / 1000, tz=timezone.utc).isoformat()
                    if resolved_ts else alert_iso)
    append_trade_log({
        "symbol":        symbol,
        "alert_time":    alert_iso,
        "resolved_time": resolved_iso,
        "score":         result["score"],
        "entry":         result["price"],
        "sl":            result["sl"],
        "tp1":           result["tp1"],
        "tp2":           result["tp2"],
        "outcome":       outcome,
        "components":    result["components"],
        "pipeline":      pipeline,
        "source":        "backtest",
    })
    existing_keys.add(key)
    return True


def backtest_symbol(exchange, symbol: str, until_ms: int, btc_15m: list, btc_ts: list,
                    existing_keys: set) -> dict:
    """
    Walks forward through history evaluating BOTH pipelines at every step:
      - breakout : evaluate_candidate()          (v2/v3, unchanged)
      - reversal : evaluate_reversal_candidate()  (v4 primary)
    `derivatives` (funding rate / open interest) is live-only and can't be
    replayed against history for free — reversal candidates are backtested
    without that bonus, same documented limitation as the breakout
    pipeline's taker buy/sell ratio and order book checks.
    """
    since_15m = until_ms - (cfg.BACKTEST_DAYS + 4) * 86400 * 1000       # padding for indicator lookback
    since_1h  = until_ms - (cfg.BACKTEST_DAYS + 12) * 86400 * 1000      # padding for 50/200 EMA lookback

    raw_15m = fetch_ohlcv_range(exchange, symbol, cfg.TIMEFRAME_PRIMARY, since_15m, until_ms)
    raw_1h  = fetch_ohlcv_range(exchange, symbol, cfg.TIMEFRAME_CONFIRM, since_1h, until_ms)

    candles_15m = ohlcv_to_dicts(raw_15m)
    candles_1h  = ohlcv_to_dicts(raw_1h)
    ts_1h       = [c["ts"] for c in candles_1h]

    eval_start_ms = until_ms - cfg.BACKTEST_DAYS * 86400 * 1000
    start_idx = next((i for i, c in enumerate(candles_15m)
                      if c["ts"] >= eval_start_ms and i >= cfg.CANDLES_PRIMARY), None)
    if start_idx is None:
        return {"symbol": symbol, "candidates": 0, "logged": 0, "reason": "insufficient history"}

    cooldown_bars = max(1, cfg.ALERT_COOLDOWN_MINUTES // 15)
    candidates = logged = 0
    i = start_idx
    while i < len(candles_15m) - 1:
        window = candles_15m[max(0, i - cfg.CANDLES_PRIMARY + 1): i + 1]
        if (i + 1) % cfg.BACKTEST_STEP_BARS != 0:
            i += 1
            continue

        htf_window = _window_ending_at(candles_1h, ts_1h, window[-1]["ts"], cfg.CANDLES_CONFIRM)
        btc_window = _window_ending_at(btc_15m, btc_ts, window[-1]["ts"], cfg.RS_LOOKBACK + 5)

        any_hit = False

        breakout = evaluate_candidate(window, candles_1h=htf_window or None, btc_candles_15m=btc_window or None)
        if breakout is not None and breakout["score"] >= cfg.BACKTEST_SCORE_FLOOR and breakout["sl"] is not None:
            candidates += 1
            any_hit = True
            if _log_candidate(symbol, "breakout", breakout, window, candles_15m, i, existing_keys):
                logged += 1

        reversal = evaluate_reversal_candidate(window, candles_1h=htf_window or None, btc_candles_15m=btc_window or None)
        if reversal is not None and reversal["score"] >= cfg.BACKTEST_SCORE_FLOOR and reversal["sl"] is not None:
            candidates += 1
            any_hit = True
            if _log_candidate(symbol, "reversal", reversal, window, candles_15m, i, existing_keys):
                logged += 1

        i += cooldown_bars if any_hit else 1   # mirror live's alert cooldown — don't log the same move 20 times

    return {"symbol": symbol, "candidates": candidates, "logged": logged}


def main():
    log("🔬 Pre-Breakout Scanner — Backtest starting")
    exchange = ccxt.kucoin({"enableRateLimit": True})

    symbols = pick_symbol_universe(exchange)
    log(f"📊 Backtest universe: {len(symbols)} symbols (top by 24h volume), {cfg.BACKTEST_DAYS} days")

    until_ms = int(time.time() * 1000)
    since_btc = until_ms - (cfg.BACKTEST_DAYS + 4) * 86400 * 1000
    raw_btc = fetch_ohlcv_range(exchange, "BTC/USDT", cfg.TIMEFRAME_PRIMARY, since_btc, until_ms)
    btc_15m = ohlcv_to_dicts(raw_btc)
    btc_ts  = [c["ts"] for c in btc_15m]
    log(f"📡 BTC/USDT 15m candles loaded: {len(btc_15m)}")

    existing = load_trade_log()
    existing_keys = {(r.get("symbol"), r.get("alert_time"), r.get("source"), r.get("pipeline", "breakout"))
                     for r in existing}
    log(f"🗂️  Existing trade log entries: {len(existing)} (deduping against these)")

    total_candidates = total_logged = 0
    for n, symbol in enumerate(symbols, 1):
        stats = backtest_symbol(exchange, symbol, until_ms, btc_15m, btc_ts, existing_keys)
        total_candidates += stats.get("candidates", 0)
        total_logged += stats.get("logged", 0)
        log(f"  [{n}/{len(symbols)}] {symbol}: {stats.get('candidates', 0)} candidates, "
            f"{stats.get('logged', 0)} newly logged" + (f" ({stats['reason']})" if "reason" in stats else ""))

    log(f"✅ Backtest complete — {total_candidates} candidates evaluated, {total_logged} new trade-log entries")
    return total_logged


if __name__ == "__main__":
    main()
