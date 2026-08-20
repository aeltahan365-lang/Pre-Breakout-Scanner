"""
Pre-Breakout Scanner — Live Auto-Trading (Binance, real money)
=================================================================
Everything here is inert unless config.AUTO_TRADING_ENABLED is True. When
it's off (the default), scanner.py never imports a code path that touches
an order endpoint.

Design:
  - Position sizing is risk-based (config.compute_position_size): the
    Stop Loss distance and the signal's score jointly determine quantity,
    never a fixed coin amount.
  - No native OCO order is used. Binance OCO support varies by ccxt
    version/account type, and a silent failure there would leave a
    position with NO protective order at all — worse than the two-order
    approach here. Instead a STOP_LOSS_LIMIT sell and a separate LIMIT
    sell (take-profit) are placed independently, and reconcile_positions()
    — called once per scan cycle (every ~15 min) — checks both, cancels
    whichever didn't fill once the other does, and logs the realized PnL.
    Trade-off: a position's protective orders are only reconciled every
    ~15 minutes, not continuously: this is a batch system, not a
    real-time trading desk.
  - The daily loss circuit breaker and per-position risk caps are the
    actual safety mechanism; read config.py's "Live Auto-Trading" section
    before changing any of this.
"""

import json
import os
from datetime import datetime, timezone

import ccxt

import config as cfg


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{ts}] {msg}", flush=True)


# ─────────────────────────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────────────────────────

def get_trading_client():
    """
    Returns an authenticated ccxt.binance client, or None if trading is
    disabled or credentials are missing. Never raises — callers treat
    None as "trading unavailable this cycle."
    """
    if not cfg.AUTO_TRADING_ENABLED:
        return None
    if not cfg.BINANCE_API_KEY or not cfg.BINANCE_API_SECRET:
        log("⚠️  AUTO_TRADING_ENABLED but BINANCE_API_KEY/SECRET missing — trading disabled this cycle")
        return None
    exchange = ccxt.binance({
        "apiKey": cfg.BINANCE_API_KEY,
        "secret": cfg.BINANCE_API_SECRET,
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })
    if cfg.BINANCE_TESTNET:
        exchange.set_sandbox_mode(True)
        log("🧪 Binance TESTNET mode — no real funds at risk")
    return exchange


# ─────────────────────────────────────────────────────────────────
# STATE (open positions, daily PnL, halt flag)
# ─────────────────────────────────────────────────────────────────

def load_trading_state() -> dict:
    if os.path.exists(cfg.TRADING_STATE_FILE):
        try:
            with open(cfg.TRADING_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"halted": False, "halt_reason": None, "daily": {}, "open_positions": {}}


def save_trading_state(state: dict):
    os.makedirs(os.path.dirname(cfg.TRADING_STATE_FILE), exist_ok=True)
    with open(cfg.TRADING_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ensure_today(state: dict, start_balance: float) -> dict:
    day = state.setdefault("daily", {})
    if day.get("date") != _today_key():
        day["date"] = _today_key()
        day["realized_pnl"] = 0.0
        day["start_balance"] = start_balance
    return day


def record_realized_pnl(state: dict, pnl: float, balance_for_new_day: float):
    day = _ensure_today(state, balance_for_new_day)
    day["realized_pnl"] = day.get("realized_pnl", 0.0) + pnl


def daily_loss_pct(state: dict) -> float:
    day = state.get("daily", {})
    if day.get("date") != _today_key():
        return 0.0
    start = day.get("start_balance", 0.0)
    if start <= 0:
        return 0.0
    return max(0.0, -day.get("realized_pnl", 0.0) / start * 100)


def halt_trading(state: dict, reason: str):
    state["halted"] = True
    state["halt_reason"] = reason
    state["halt_time"] = datetime.now(timezone.utc).isoformat()
    log(f"🛑 AUTO-TRADING HALTED: {reason}")


# ─────────────────────────────────────────────────────────────────
# POSITION SIZING
# ─────────────────────────────────────────────────────────────────

def compute_position_size(score: float, balance_usdt: float, entry: float, sl: float):
    """
    Risk-based sizing: quantity such that a Stop Loss fill loses exactly
    `risk_pct` of current equity, where risk_pct scales linearly from
    MIN_TRADE_RISK_PCT (at SCORE_THRESHOLD) to MAX_TRADE_RISK_PCT (at 100).
    Also caps notional value at MAX_POSITION_NOTIONAL_PCT of equity so an
    unusually tight stop can't size an outsized position.

    Returns (quantity, risk_pct, notional_usdt). quantity is 0.0 if the
    trade can't be sized (bad inputs or insufficient balance).
    """
    if balance_usdt <= 0 or entry <= 0 or sl <= 0 or sl >= entry:
        return 0.0, 0.0, 0.0

    span = max(1, 100 - cfg.SCORE_THRESHOLD)
    frac = min(1.0, max(0.0, (score - cfg.SCORE_THRESHOLD) / span))
    risk_pct = cfg.MIN_TRADE_RISK_PCT + frac * (cfg.MAX_TRADE_RISK_PCT - cfg.MIN_TRADE_RISK_PCT)

    stop_distance = entry - sl
    risk_amount = balance_usdt * (risk_pct / 100)
    qty = risk_amount / stop_distance

    max_notional = balance_usdt * (cfg.MAX_POSITION_NOTIONAL_PCT / 100)
    notional = qty * entry
    if notional > max_notional:
        qty = max_notional / entry
        notional = max_notional

    # Never try to spend more than what's actually free.
    if notional > balance_usdt * 0.99:
        qty = (balance_usdt * 0.99) / entry
        notional = qty * entry

    return qty, round(risk_pct, 3), notional


# ─────────────────────────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────────────────────────

def maybe_enter_trade(exchange, alert: dict, state: dict) -> dict | None:
    """
    Called once per qualifying alert. Applies every safety gate, and if
    they all pass, places a market buy plus a protective STOP_LOSS_LIMIT
    sell and a LIMIT (take-profit) sell. Returns a summary dict for the
    Telegram notification, or None if no trade was placed (with the
    reason logged).
    """
    symbol = alert["symbol"]

    if state.get("halted"):
        log(f"  ⏸️  auto-trade skipped for {symbol} — trading is halted ({state.get('halt_reason')})")
        return None

    open_positions = state.setdefault("open_positions", {})
    if symbol in open_positions:
        log(f"  ⏸️  auto-trade skipped for {symbol} — position already open")
        return None
    if len(open_positions) >= cfg.MAX_CONCURRENT_POSITIONS:
        log(f"  ⏸️  auto-trade skipped for {symbol} — MAX_CONCURRENT_POSITIONS ({cfg.MAX_CONCURRENT_POSITIONS}) reached")
        return None

    sl, tp1 = alert.get("sl"), alert.get("tp1")
    if not sl or not tp1:
        log(f"  ⏸️  auto-trade skipped for {symbol} — no SL/TP computed")
        return None

    try:
        balance = exchange.fetch_balance()
        free_usdt = float(balance.get("USDT", {}).get("free", 0) or 0)
    except Exception as e:
        log(f"  ⚠️  auto-trade skipped for {symbol} — balance fetch failed: {e}")
        return None

    _ensure_today(state, free_usdt)
    if daily_loss_pct(state) >= cfg.MAX_DAILY_LOSS_PCT:
        halt_trading(state, f"daily loss cap reached ({cfg.MAX_DAILY_LOSS_PCT}%)")
        return None

    entry_price = alert["price"]
    qty, risk_pct, notional = compute_position_size(alert["score"], free_usdt, entry_price, sl)
    if qty <= 0:
        log(f"  ⏸️  auto-trade skipped for {symbol} — sizing came back zero (balance={free_usdt} USDT)")
        return None

    try:
        market = exchange.market(symbol)
        min_notional = (market.get("limits", {}).get("cost", {}) or {}).get("min") or 0
        min_qty = (market.get("limits", {}).get("amount", {}) or {}).get("min") or 0
        qty = float(exchange.amount_to_precision(symbol, qty))
        if qty < min_qty or (min_notional and qty * entry_price < min_notional):
            log(f"  ⏸️  auto-trade skipped for {symbol} — below exchange minimum "
                f"(qty={qty}, min_qty={min_qty}, min_notional={min_notional})")
            return None
    except Exception as e:
        log(f"  ⚠️  auto-trade skipped for {symbol} — market precision lookup failed: {e}")
        return None

    try:
        buy_order = exchange.create_order(symbol, "market", "buy", qty)
    except Exception as e:
        log(f"  ❌ auto-trade BUY failed for {symbol}: {e}")
        return None

    filled_qty = float(buy_order.get("filled") or qty)
    fill_price = float(buy_order.get("average") or buy_order.get("price") or entry_price)

    stop_order_id = tp_order_id = None
    try:
        stop_price = round(sl, 8)
        stop_limit_price = round(sl * 0.995, 8)   # small buffer so the limit actually fills once triggered
        stop_order = exchange.create_order(
            symbol, "STOP_LOSS_LIMIT", "sell", filled_qty, stop_limit_price,
            {"stopPrice": stop_price},
        )
        stop_order_id = stop_order.get("id")
    except Exception as e:
        log(f"  ⚠️  {symbol} bought but STOP order failed: {e} — closing position immediately (no naked risk)")
        try:
            exchange.create_order(symbol, "market", "sell", filled_qty)
        except Exception as e2:
            log(f"  ❌ {symbol} EMERGENCY SELL ALSO FAILED: {e2} — MANUAL INTERVENTION REQUIRED")
        return {"symbol": symbol, "emergency_exit": True, "reason": str(e)}

    try:
        tp_order = exchange.create_order(symbol, "limit", "sell", filled_qty, round(tp1, 8))
        tp_order_id = tp_order.get("id")
    except Exception as e:
        log(f"  ⚠️  {symbol} STOP placed but TP order failed: {e} — position protected by SL only")

    open_positions[symbol] = {
        "qty":            filled_qty,
        "entry_price":    fill_price,
        "sl":             sl,
        "tp1":            tp1,
        "stop_order_id":  stop_order_id,
        "tp_order_id":    tp_order_id,
        "entry_time":     datetime.now(timezone.utc).isoformat(),
        "score":          alert["score"],
        "risk_pct":       risk_pct,
    }

    log(f"  🤖 AUTO-TRADE OPENED {symbol}: qty={filled_qty} @ {fill_price} "
        f"(risk={risk_pct}%, notional=${notional:,.2f}, SL={sl}, TP={tp1})")

    return {
        "symbol": symbol, "qty": filled_qty, "entry_price": fill_price,
        "sl": sl, "tp1": tp1, "risk_pct": risk_pct, "notional": notional,
    }


# ─────────────────────────────────────────────────────────────────
# RECONCILIATION — resolves open positions each cycle
# ─────────────────────────────────────────────────────────────────

def reconcile_positions(exchange, state: dict) -> list:
    """
    For every open auto-trade position, checks whether the stop or the
    take-profit order has filled. Whichever filled first "wins": the
    other order is cancelled, realized PnL is recorded against the daily
    loss cap, and the position is closed out of state. Returns a list of
    human-readable result strings for the Telegram summary.
    """
    open_positions = state.setdefault("open_positions", {})
    results = []

    for symbol, pos in list(open_positions.items()):
        stop_id, tp_id = pos.get("stop_order_id"), pos.get("tp_order_id")
        filled_leg, exit_price = None, None

        try:
            if stop_id:
                o = exchange.fetch_order(stop_id, symbol)
                if o.get("status") == "closed":
                    filled_leg, exit_price = "sl", float(o.get("average") or pos["sl"])
            if filled_leg is None and tp_id:
                o = exchange.fetch_order(tp_id, symbol)
                if o.get("status") == "closed":
                    filled_leg, exit_price = "tp", float(o.get("average") or pos["tp1"])
        except Exception as e:
            log(f"  ⚠️  reconcile failed for {symbol}: {e}")
            continue

        if filled_leg is None:
            continue   # still open, nothing to do this cycle

        # Cancel whichever leg didn't fill.
        other_id = tp_id if filled_leg == "sl" else stop_id
        if other_id:
            try:
                exchange.cancel_order(other_id, symbol)
            except Exception:
                pass   # already filled/cancelled/expired — fine

        pnl = (exit_price - pos["entry_price"]) * pos["qty"]
        try:
            balance = exchange.fetch_balance()
            free_usdt = float(balance.get("USDT", {}).get("free", 0) or 0)
        except Exception:
            free_usdt = 0.0
        record_realized_pnl(state, pnl, free_usdt)

        label = "✅ TP HIT" if filled_leg == "tp" else "❌ SL HIT"
        results.append(f"{label} — {symbol}: {pnl:+.2f} USDT (entry {pos['entry_price']} → exit {exit_price})")
        log(f"  {label} {symbol}: PnL={pnl:+.2f} USDT")
        del open_positions[symbol]

        if daily_loss_pct(state) >= cfg.MAX_DAILY_LOSS_PCT:
            halt_trading(state, f"daily loss cap reached ({cfg.MAX_DAILY_LOSS_PCT}%) after {symbol} closed")

    return results


if __name__ == "__main__":
    import sys
    state = load_trading_state()
    if "--resume" in sys.argv:
        if not state.get("halted"):
            print("Trading is not currently halted — nothing to do.")
        else:
            print(f"Clearing halt (was: {state.get('halt_reason')})")
            state["halted"] = False
            state["halt_reason"] = None
            save_trading_state(state)
            print("Halt cleared. Auto-trading will resume next cycle (if AUTO_TRADING_ENABLED=true).")
    else:
        print(json.dumps(state, indent=2, ensure_ascii=False))
