"""
Pre-Breakout Scanner v2 — Advanced Multi-Signal Engine
=======================================================
Runs every 15 minutes via GitHub Actions.

NEW vs v1:
  • 9 technical indicators (was 4): RSI, MACD, BB Squeeze, OBV, ATR,
    Stochastic RSI, CMF, Williams %R, Donchian, ADL+Chaikin, Lin Reg, EMA Trend
  • Multi-timeframe: 15m scan + 1h confirmation
  • Cross-exchange validation (KuCoin primary + Binance check)
  • BTC market context filter (skip altcoin longs during BTC bear)
  • Alert cooldown (no re-alerting same symbol within 60 min)
  • ATR-based Stop Loss & Take Profit suggestion in every alert
  • TradingView chart link in every alert
  • New listing detection (unchanged from v1)
  • Composite score 0-100 with labeled reasons
"""

import ccxt
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

import config as cfg
from indicators import (
    calc_volume_explosion,
    calc_close_location_value,
    calc_rsi,
    calc_macd,
    calc_bollinger,
    calc_atr,
    calc_obv,
    calc_stoch_rsi,
    calc_cmf,
    calc_williams_r,
    calc_adl_chaikin,
    calc_donchian,
    calc_linear_regression,
    calc_trend,
    htf_confirmation,
    build_score,
)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{ts}] {msg}", flush=True)


def ohlcv_to_dicts(raw: list) -> list:
    return [
        {"ts": r[0], "open": r[1], "high": r[2], "low": r[3],
         "close": r[4], "volume": r[5]}
        for r in raw
    ]


# ─────────────────────────────────────────────────────────────────
# STATE (known symbols + alert cooldown)
# ─────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if os.path.exists(cfg.STATE_FILE):
        try:
            with open(cfg.STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "known_symbols": [], "last_run": None, "alert_history": {},
        "pending_outcomes": [], "stats": {"wins": 0, "losses": 0, "expired": 0},
    }


def save_state(state: dict):
    os.makedirs(os.path.dirname(cfg.STATE_FILE), exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    # Prune old cooldown entries (> 2 hours)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    history = state.get("alert_history", {})
    state["alert_history"] = {
        sym: ts for sym, ts in history.items()
        if datetime.fromisoformat(ts) > cutoff
    }
    with open(cfg.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_on_cooldown(symbol: str, history: dict) -> bool:
    if symbol not in history:
        return False
    last = datetime.fromisoformat(history[symbol])
    return (datetime.now(timezone.utc) - last).total_seconds() < cfg.ALERT_COOLDOWN_MINUTES * 60


# ─────────────────────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────────────────────

def send_telegram(message: str, silent: bool = False):
    if not cfg.TELEGRAM_BOT_TOKEN or not cfg.TELEGRAM_CHAT_ID:
        log("⚠️  Telegram not configured — printing instead")
        print(message)
        return
    url = f"https://api.telegram.org/bot{cfg.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            data={
                "chat_id":                  cfg.TELEGRAM_CHAT_ID,
                "text":                     message,
                "parse_mode":               "HTML",
                "disable_web_page_preview": True,
                "disable_notification":     silent,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            log(f"❌ Telegram error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log(f"❌ Telegram exception: {e}")


def format_alert(data: dict) -> str:
    """
    Build a rich Telegram HTML message for a breakout signal.
    """
    sym      = data["symbol"]
    base     = sym.replace("/USDT", "").replace(":", "_")
    score    = data["score"]
    price    = data["price"]
    vol_r    = data["vol_ratio"]
    pct      = data["price_chg_pct"]
    reasons  = data["reasons"]
    atr      = data.get("atr")
    sl       = data.get("sl")
    tp1      = data.get("tp1")
    tp2      = data.get("tp2")
    htf_ok   = data.get("htf_confirmed", False)
    tv_link  = cfg.TV_BASE.format(exchange="KUCOIN", base=base)

    # Score emoji
    if score >= 85:
        badge = "🟢🟢🟢 STRONG"
    elif score >= 75:
        badge = "🟢🟢 HIGH"
    elif score >= 65:
        badge = "🟡 MODERATE"
    else:
        badge = "🔵 WATCH"

    htf_tag = "✅ 1h confirms" if htf_ok else "⚠️ 1h unconfirmed"

    lines = [
        f"⚡ <b>PRE-BREAKOUT ALERT — {sym}</b>",
        f"Score: <b>{score}/100</b>  {badge}",
        f"",
        f"💰 Price:  <code>{price}</code>",
        f"📊 Volume: <b>{vol_r}x</b> avg  |  Candle: <b>{pct:+.2f}%</b>",
        f"🕐 HTF:    {htf_tag}",
    ]

    if atr and sl and tp1:
        rr1 = abs((tp1 - price) / (price - sl)) if price != sl else 0
        rr2 = abs((tp2 - price) / (price - sl)) if tp2 and price != sl else 0
        lines += [
            f"",
            f"📐 <b>Risk Management (ATR={round(atr, 6)})</b>",
            f"  🔴 Stop Loss:  <code>{round(sl, 8)}</code>",
            f"  🟡 Target 1:   <code>{round(tp1, 8)}</code>  (R/R {rr1:.1f}x)",
        ]
        if tp2:
            lines.append(f"  🟢 Target 2:   <code>{round(tp2, 8)}</code>  (R/R {rr2:.1f}x)")

    lines += [
        f"",
        f"<b>Signals:</b>",
    ]
    for r in reasons:
        lines.append(f"  {r}")

    lines += [
        f"",
        f'📈 <a href="{tv_link}">Open on TradingView</a>',
        f"<i>KuCoin • {datetime.now(timezone.utc).strftime('%H:%M UTC')}</i>",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# BTC MARKET CONTEXT
# ─────────────────────────────────────────────────────────────────

def get_btc_context(exchange) -> dict:
    """
    Fetch BTC/USDT 1h candles and determine if market is risk-on or risk-off.
    Returns dict: {'bullish': bool, 'trend': str, 'rsi': float}
    """
    try:
        raw = exchange.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=60)
        candles = ohlcv_to_dicts(raw)
        trend   = calc_trend(candles)
        rsi_val = calc_rsi(candles)
        # Market is "risk-on" if BTC trend is bullish or sideways (not outright bearish)
        bullish = trend != "bearish"
        log(f"📡 BTC/USDT context: trend={trend}, RSI={rsi_val} → risk_on={bullish}")
        return {"bullish": bullish, "trend": trend, "rsi": rsi_val}
    except Exception as e:
        log(f"⚠️  BTC context fetch failed: {e} — assuming neutral")
        return {"bullish": True, "trend": "sideways", "rsi": None}


# ─────────────────────────────────────────────────────────────────
# CROSS-EXCHANGE VALIDATION
# ─────────────────────────────────────────────────────────────────

def validate_on_binance(binance, symbol: str) -> bool:
    """
    Lightweight check: is there also a volume spike on Binance for this pair?
    Returns True if Binance confirms the signal, False otherwise (or if pair not listed).
    """
    try:
        raw = binance.fetch_ohlcv(symbol, timeframe=cfg.TIMEFRAME_PRIMARY, limit=cfg.CANDLES_PRIMARY)
        if not raw or len(raw) < 22:
            return False
        candles = ohlcv_to_dicts(raw)
        explosion, ratio, _ = calc_volume_explosion(candles)
        return explosion
    except Exception:
        return False   # Pair may not exist on Binance — not a disqualifier


# ─────────────────────────────────────────────────────────────────
# VOLUME DIRECTION (taker buy/sell classification — separates real
# buying volume from selling/distribution volume)
# ─────────────────────────────────────────────────────────────────

def calc_taker_buy_ratio(exchange, symbol: str, limit: int = 150) -> float | None:
    """
    Pulls recent public trades and classifies each as buyer-initiated
    or seller-initiated (the exchange tags this as trade['side']).

    Returns the fraction of traded volume that was buyer-initiated (0-1).
    A high-volume candle dominated by 'sell' trades is distribution,
    not a real breakout — even if price ticked up slightly.

    Returns None if trades are unavailable (not a disqualifier).
    """
    try:
        trades = exchange.fetch_trades(symbol, limit=limit)
        if not trades:
            return None
        buy_vol  = sum(t["amount"] for t in trades if t.get("side") == "buy")
        sell_vol = sum(t["amount"] for t in trades if t.get("side") == "sell")
        total = buy_vol + sell_vol
        return round(buy_vol / total, 3) if total > 0 else None
    except Exception:
        return None


def validate_buy_ratio_cryptocom(cryptocom, symbol: str, limit: int = 150) -> float | None:
    """
    Cross-checks the taker buy/sell ratio on Crypto.com Exchange, when the
    pair happens to be listed there (ccxt symbol 'TOKEN/USDT' -> Crypto.com
    market 'TOKEN/USDT' — ccxt normalizes the format automatically).

    This is a BONUS confirmation, not a hard requirement: many KuCoin
    small/mid-cap listings (e.g. fresh pre-breakout candidates) simply
    aren't listed on Crypto.com, so a None here just means "no extra
    data available," not "rejected."
    """
    if cryptocom is None:
        return None
    try:
        if symbol not in cryptocom.markets:
            return None
        return calc_taker_buy_ratio(cryptocom, symbol, limit=limit)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# ORDER BOOK IMBALANCE (is there a sell wall sitting above price?)
# ─────────────────────────────────────────────────────────────────

def calc_order_book_imbalance(exchange, symbol: str,
                               depth_pct: float = None, limit: int = 50) -> dict | None:
    """
    Looks at live order book depth within `depth_pct` of the best
    bid/ask (default 2%) and measures whether buyers or sellers
    dominate right around the current price.

    Returns dict: {bid_depth, ask_depth, bid_ratio} or None if unavailable.
      bid_ratio -> 1.0  : buyers dominate, thin resistance above price
      bid_ratio -> 0.0  : a sell wall sits just above price —
                          a breakout here is likely to get rejected
                          even if the candle/trade data looks bullish
    """
    depth_pct = depth_pct if depth_pct is not None else cfg.ORDER_BOOK_DEPTH_PCT
    try:
        ob = exchange.fetch_order_book(symbol, limit=limit)
        bids, asks = ob.get("bids") or [], ob.get("asks") or []
        if not bids or not asks:
            return None
        best_bid, best_ask = bids[0][0], asks[0][0]
        bid_floor   = best_bid * (1 - depth_pct)
        ask_ceiling = best_ask * (1 + depth_pct)
        bid_depth = sum(price * qty for price, qty in bids if price >= bid_floor)
        ask_depth = sum(price * qty for price, qty in asks if price <= ask_ceiling)
        total = bid_depth + ask_depth
        if total <= 0:
            return None
        return {
            "bid_depth": round(bid_depth, 2),
            "ask_depth": round(ask_depth, 2),
            "bid_ratio": round(bid_depth / total, 3),
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# SINGLE SYMBOL ANALYSIS
# ─────────────────────────────────────────────────────────────────

def analyze_symbol(exchange, symbol: str, cryptocom=None) -> dict | None:
    """
    Full analysis pipeline for one symbol.
    Returns alert dict if signal qualifies, else None.
    """
    try:
        # ── Quick 24h volume filter ──
        ticker      = exchange.fetch_ticker(symbol)
        quote_24h   = ticker.get("quoteVolume") or 0
        if quote_24h < cfg.MIN_QUOTE_VOLUME_24H:
            return None

        # ── Primary candles (15m) ──
        raw_15m = exchange.fetch_ohlcv(symbol, timeframe=cfg.TIMEFRAME_PRIMARY, limit=cfg.CANDLES_PRIMARY)
        if not raw_15m or len(raw_15m) < cfg.VOLUME_LOOKBACK + 10:
            return None
        candles = ohlcv_to_dicts(raw_15m)

        # ── GATE: volume explosion required first ──
        explosion, vol_ratio, price_chg_pct = calc_volume_explosion(candles)
        if not explosion:
            return None

        # ── GATE: volume direction confirmation ──
        # A volume spike alone isn't a buy signal — it has to be BUYING
        # volume. We check two things: (1) where the candle closed within
        # its range (VSA-style), and (2) the actual taker buy/sell split
        # from recent trades.
        clv = calc_close_location_value(candles)
        if clv is not None and clv < cfg.MIN_CLV:
            log(f"  🚫 {symbol} vol={vol_ratio}x but CLV={clv} — closed near the low, "
                f"likely selling/distribution. Skipped.")
            return None

        buy_ratio = calc_taker_buy_ratio(exchange, symbol)
        if buy_ratio is not None and buy_ratio < cfg.MIN_TAKER_BUY_RATIO:
            log(f"  🚫 {symbol} vol={vol_ratio}x but taker buy_ratio={buy_ratio} — "
                f"sell-dominated. Skipped.")
            return None

        # ── BONUS: cross-check buy ratio on Crypto.com when listed ──
        cc_buy_ratio = None
        if cfg.USE_CRYPTOCOM_VALIDATION:
            cc_buy_ratio = validate_buy_ratio_cryptocom(cryptocom, symbol)

        # ── GATE: order book — reject if a sell wall sits above price ──
        ob = calc_order_book_imbalance(exchange, symbol)
        if ob is not None and ob["bid_ratio"] < cfg.MIN_ORDER_BOOK_BID_RATIO:
            log(f"  🚫 {symbol} sell wall detected (bid_ratio={ob['bid_ratio']}, "
                f"ask_depth=${ob['ask_depth']:,.0f} vs bid_depth=${ob['bid_depth']:,.0f}) "
                f"— breakout likely to get rejected. Skipped.")
            return None

        # ── All indicators ──
        rsi_val  = calc_rsi(candles)
        macd_val = calc_macd(candles)
        bb_val   = calc_bollinger(candles)
        atr_val  = calc_atr(candles)
        obv_val  = calc_obv(candles)
        adl_val  = calc_adl_chaikin(candles)
        don_val  = calc_donchian(candles)
        reg_val  = calc_linear_regression(candles)
        trend    = calc_trend(candles)
        stoch    = calc_stoch_rsi(candles)
        cmf_val  = calc_cmf(candles)
        will_r   = calc_williams_r(candles)

        # ── Higher-TF (1h) confirmation ──
        htf = {"bullish": False, "trend": "unknown", "rsi": None}
        try:
            raw_1h = exchange.fetch_ohlcv(symbol, timeframe=cfg.TIMEFRAME_CONFIRM, limit=cfg.CANDLES_CONFIRM)
            htf    = htf_confirmation(ohlcv_to_dicts(raw_1h))
        except Exception:
            pass

        # ── Composite score ──
        score, reasons = build_score(
            vol_ratio=vol_ratio,
            price_chg_pct=price_chg_pct,
            rsi=rsi_val,
            macd=macd_val,
            bb=bb_val,
            donchian=don_val,
            lin_reg=reg_val,
            trend=trend,
            adl_chai=adl_val,
            obv=obv_val,
            htf=htf,
        )

        # Append extra indicator summaries to reasons (informational)
        extra = []
        if stoch.get("k") is not None:
            extra.append(f"StochRSI K={stoch['k']} ({stoch['zone']})")
        if cmf_val is not None:
            extra.append(f"CMF={cmf_val} ({'▲ buy' if cmf_val > 0 else '▼ sell'})")
        if will_r is not None:
            extra.append(f"Williams%R={will_r}")
        if extra:
            reasons.append("ℹ️  " + "  |  ".join(extra))

        if clv is not None or buy_ratio is not None:
            clv_str = f"CLV={clv}" if clv is not None else "CLV=n/a"
            buy_str = f"Buy ratio={buy_ratio}" if buy_ratio is not None else "Buy ratio=n/a"
            reasons.append(f"✅ Volume confirmed buy-side ({clv_str} | {buy_str})")

        if cc_buy_ratio is not None:
            tag = "✅" if cc_buy_ratio >= cfg.MIN_TAKER_BUY_RATIO else "⚠️"
            reasons.append(f"{tag} Crypto.com cross-check: buy ratio={cc_buy_ratio}")

        if ob is not None:
            reasons.append(f"✅ Order book clear (bid_ratio={ob['bid_ratio']}, ±{int(cfg.ORDER_BOOK_DEPTH_PCT*100)}% depth)")

        if score < cfg.SCORE_THRESHOLD:
            return None

        # ── Risk Management (ATR-based) ──
        price = candles[-1]["close"]
        sl = tp1 = tp2 = None
        if atr_val:
            sl  = price - 1.5 * atr_val
            tp1 = price + 2.0 * atr_val
            tp2 = price + 3.5 * atr_val

        return {
            "symbol":        symbol,
            "score":         score,
            "price":         price,
            "vol_ratio":     vol_ratio,
            "price_chg_pct": price_chg_pct,
            "reasons":       reasons,
            "atr":           atr_val,
            "sl":            sl,
            "tp1":           tp1,
            "tp2":           tp2,
            "htf_confirmed": htf.get("bullish", False),
        }

    except ccxt.BaseError as e:
        log(f"  ⚠️  ccxt error on {symbol}: {e}")
    except Exception as e:
        log(f"  ⚠️  unexpected error on {symbol}: {e}")
    return None


# ─────────────────────────────────────────────────────────────────
# OUTCOME TRACKING — did past alerts actually work?
# ─────────────────────────────────────────────────────────────────
# This is the foundation for any future, data-driven tuning (rebalancing
# indicator weights, adding ML, adjusting thresholds). Without this, any
# change to the scoring logic is a guess. With it, after a few weeks you
# have real win/loss numbers per setup.

OUTCOME_EXPIRY_HOURS = 48   # stop tracking a signal if neither SL nor TP hit within this window


def evaluate_outcome(exchange, pending: dict) -> str:
    """
    Checks 15m candles since the alert was sent to see whether price has
    touched the Stop Loss, Take Profit 1, or Take Profit 2 level.

    Returns one of: 'tp2_hit', 'tp1_hit', 'sl_hit', 'open', 'error'.
    If SL and a TP are both touched within the same 15m candle, SL wins
    (conservative — we can't know the intra-candle order, so we assume
    the worst case).
    """
    symbol = pending["symbol"]
    sl, tp1, tp2 = pending.get("sl"), pending.get("tp1"), pending.get("tp2")
    if not sl or not tp1:
        return "error"
    try:
        since_ms = int(datetime.fromisoformat(pending["alert_time"]).timestamp() * 1000)
        raw = exchange.fetch_ohlcv(symbol, timeframe="15m", since=since_ms, limit=200)
        if not raw:
            return "open"
        for _, _, h, l, _, _ in raw:
            hit_sl  = l <= sl
            hit_tp2 = tp2 is not None and h >= tp2
            hit_tp1 = h >= tp1
            if hit_sl:
                return "sl_hit"
            if hit_tp2:
                return "tp2_hit"
            if hit_tp1:
                return "tp1_hit"
        return "open"
    except Exception as e:
        log(f"  ⚠️  outcome check failed for {symbol}: {e}")
        return "error"


def process_pending_outcomes(exchange, state: dict) -> list:
    """
    Resolves any alerts sent in previous cycles: checks if SL/TP1/TP2 was
    hit, updates running win/loss stats, and returns the list of alerts
    still open (to keep tracking next cycle).
    """
    pending = state.get("pending_outcomes", [])
    stats   = state.setdefault("stats", {"wins": 0, "losses": 0, "expired": 0})
    still_open = []
    resolved   = []

    for p in pending:
        age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(p["alert_time"])).total_seconds() / 3600
        outcome = evaluate_outcome(exchange, p)

        if outcome == "sl_hit":
            stats["losses"] += 1
            resolved.append(f"❌ {p['symbol']}: SL hit (score {p['score']})")
        elif outcome in ("tp1_hit", "tp2_hit"):
            stats["wins"] += 1
            label = "TP2" if outcome == "tp2_hit" else "TP1"
            resolved.append(f"✅ {p['symbol']}: {label} hit (score {p['score']})")
        elif outcome == "open":
            if age_hours < OUTCOME_EXPIRY_HOURS:
                still_open.append(p)
            else:
                stats["expired"] += 1
                resolved.append(f"⌛ {p['symbol']}: expired, no level hit (score {p['score']})")
        else:  # 'error' — retry next cycle, but don't track forever
            if age_hours < OUTCOME_EXPIRY_HOURS:
                still_open.append(p)

    if resolved:
        total = stats["wins"] + stats["losses"]
        win_rate = f"{(stats['wins'] / total * 100):.0f}%" if total else "n/a"
        msg = (
            "📊 <b>Signal Outcomes</b>\n\n" + "\n".join(resolved) +
            f"\n\n<i>Running stats — Wins: {stats['wins']} | Losses: {stats['losses']} | "
            f"Win rate: {win_rate}</i>"
        )
        send_telegram(msg, silent=True)
        log(f"📊 Resolved {len(resolved)} alert(s). Running: {stats}")

    return still_open


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    log("🚀 Pre-Breakout Scanner v2 — starting cycle")

    # ── Connect exchanges ──
    kucoin = ccxt.kucoin({"enableRateLimit": True})
    binance = None
    if cfg.CROSS_VALIDATE:
        try:
            binance = ccxt.binance({"enableRateLimit": True})
            binance.load_markets()
        except Exception as e:
            log(f"⚠️  Binance init failed: {e} — cross-validation disabled")
            binance = None

    cryptocom = None
    if cfg.USE_CRYPTOCOM_VALIDATION:
        try:
            cryptocom = ccxt.cryptocom({"enableRateLimit": True})
            cryptocom.load_markets()
            log(f"📡 Crypto.com connected — {len(cryptocom.markets)} markets (bonus buy-ratio cross-check)")
        except Exception as e:
            log(f"⚠️  Crypto.com init failed: {e} — buy-ratio cross-check disabled")
            cryptocom = None

    try:
        markets = kucoin.load_markets()
    except Exception as e:
        log(f"❌ Failed to load KuCoin markets: {e}")
        sys.exit(1)

    usdt_symbols = sorted([
        s for s, m in markets.items()
        if m.get("quote") == cfg.QUOTE
        and m.get("active", True)
        and m.get("spot", True)
        and "/" in s
    ])
    log(f"📊 Active KuCoin USDT pairs: {len(usdt_symbols)}")

    # ── State ──
    state          = load_state()
    known_symbols  = set(state.get("known_symbols", []))
    alert_history  = state.get("alert_history", {})
    is_first_run   = len(known_symbols) == 0

    # ── Resolve outcomes of previously sent alerts (SL/TP1/TP2 hit?) ──
    state["pending_outcomes"] = process_pending_outcomes(kucoin, state)

    # ── BTC context (skip altcoin longs in BTC bear) ──
    btc_ctx = get_btc_context(kucoin)

    # ── New listing detection ──
    current_symbols = set(usdt_symbols)
    new_listings    = sorted(current_symbols - known_symbols)
    if is_first_run:
        log("ℹ️  First run — recording all symbols, no listing alerts sent")
        new_listings = []

    if new_listings:
        msg = "🆕 <b>New KuCoin Listings</b>\n\n" + "\n".join(f"• <code>{s}</code>" for s in new_listings)
        send_telegram(msg)
        log(f"🆕 {len(new_listings)} new listing(s): {new_listings}")

    # ── Main scan loop ──
    alerts  = []
    checked = 0
    skipped_cooldown = 0

    if not btc_ctx["bullish"]:
        log("⚠️  BTC context is BEARISH — applying stricter score threshold (+10)")
        effective_threshold = cfg.SCORE_THRESHOLD + 10
    else:
        effective_threshold = cfg.SCORE_THRESHOLD

    for symbol in usdt_symbols:
        # Skip BTC and stablecoins
        base = symbol.split("/")[0]
        if base in {"BTC", "ETH", "USDC", "BUSD", "DAI", "TUSD", "FDUSD"}:
            time.sleep(cfg.RATE_LIMIT_SLEEP)
            continue

        # Cooldown check
        if is_on_cooldown(symbol, alert_history):
            skipped_cooldown += 1
            continue

        result = analyze_symbol(kucoin, symbol, cryptocom)
        checked += 1

        if result is None:
            time.sleep(cfg.RATE_LIMIT_SLEEP)
            continue

        # Apply effective threshold
        if result["score"] < effective_threshold:
            time.sleep(cfg.RATE_LIMIT_SLEEP)
            continue

        # Cross-exchange validation
        if binance and cfg.CROSS_VALIDATE:
            confirmed = validate_on_binance(binance, symbol)
            if not confirmed:
                log(f"  ⚡ {symbol} score={result['score']} but NOT confirmed on Binance — downgraded")
                result["score"] = max(0, result["score"] - 10)
                result["reasons"].append("ℹ️  Not confirmed on Binance (−10 pts)")
                if result["score"] < effective_threshold:
                    time.sleep(cfg.RATE_LIMIT_SLEEP)
                    continue

        alerts.append(result)
        log(f"  🎯 SIGNAL: {symbol} score={result['score']} vol={result['vol_ratio']}x")
        time.sleep(cfg.RATE_LIMIT_SLEEP)

    log(f"✅ Scanned {checked} pairs | {skipped_cooldown} on cooldown | {len(alerts)} signal(s)")

    # ── Send alerts (sorted by score, capped) ──
    alerts.sort(key=lambda a: a["score"], reverse=True)
    sent = 0
    for a in alerts[: cfg.MAX_ALERTS_PER_RUN]:
        msg = format_alert(a)
        send_telegram(msg)
        alert_history[a["symbol"]] = datetime.now(timezone.utc).isoformat()
        state.setdefault("pending_outcomes", []).append({
            "symbol":     a["symbol"],
            "alert_time": datetime.now(timezone.utc).isoformat(),
            "score":      a["score"],
            "entry":      a["price"],
            "sl":         a["sl"],
            "tp1":        a["tp1"],
            "tp2":        a["tp2"],
        })
        sent += 1
        time.sleep(1)   # small delay between Telegram messages

    if sent == 0 and not is_first_run and not new_listings:
        log("💤 No qualifying signals this cycle — Telegram silent")

    # Summary ping (every cycle, silent notification)
    btc_rsi_str = f"RSI {btc_ctx['rsi']}" if btc_ctx["rsi"] else ""
    summary = (
        f"🔍 Scan complete — {checked} pairs checked\n"
        f"Signals: {sent} | BTC: {btc_ctx['trend']} {btc_rsi_str}\n"
        f"<i>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>"
    )
    send_telegram(summary, silent=True)

    # ── Persist state ──
    state["known_symbols"] = sorted(current_symbols)
    state["alert_history"] = alert_history
    save_state(state)
    log("💾 State saved. Cycle complete.")


if __name__ == "__main__":
    main()
