"""
Pre-Breakout Scanner v3 — Institutional-Grade Multi-Signal Engine
===================================================================
Runs every 15 minutes via GitHub Actions.

NEW vs v2:
  • Golden Cross / Death Cross regime filter (1h, 50/200 EMA)
  • RSI + MACD momentum divergence detection (the main defense against
    alerting after a move has already topped and is rolling over)
  • Relative Strength vs BTC (never reads an altcoin move in isolation)
  • Fear & Greed Index — raises the bar during euphoric/extreme-greed markets
  • Keyless news layer: hard-blocks alerts on coin-specific negative
    catalysts (hack/delist/lawsuit), pauses the whole cycle on market-wide
    risk-off news, and gives a small bonus for positive catalysts
  • Tightened "early move" bonus window (0.3-3% instead of 0.3-8%) and
    reduced weight on lagging confirmations (Donchian breakout) — both
    aimed directly at the "alerts fire after the pump already happened"
    problem

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
from indicators import calc_volume_explosion, calc_rsi, calc_trend, calc_atr
from engine import evaluate_candidate, append_trade_log
from news import (
    fetch_fear_greed,
    fetch_latest_news,
    check_coin_news,
    check_market_wide_news,
    match_symbols_to_news,
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
    gc       = data.get("golden_cross") or {}
    rs       = data.get("rel_strength")
    fng      = data.get("fng")
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

    if atr is not None and sl is not None and tp1 is not None:
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

    # ── Institutional context block ──
    gc_event = gc.get("event")
    if gc_event == "golden_cross":
        gc_line = "🌟 Golden Cross (1h, 50/200 EMA) — fresh"
    elif gc.get("trend") == "bullish":
        gc_line = "🟢 Bullish regime (1h, 50 EMA > 200 EMA)"
    elif gc_event == "death_cross":
        gc_line = "☠️ Death Cross (1h, 50/200 EMA) — against trend"
    elif gc.get("trend") == "bearish":
        gc_line = "🔴 Bearish regime (1h, 50 EMA < 200 EMA)"
    else:
        gc_line = "⚪ Regime unknown (insufficient 1h history)"

    inst_lines = [f"  Regime:  {gc_line}"]
    if rs and rs.get("rs_spread") is not None:
        arrow = "▲" if rs["leading"] else "▼"
        inst_lines.append(f"  RS vs BTC: {arrow} {rs['rs_spread']:+.2f}pp  (coin {rs['coin_pct']:+.2f}% | BTC {rs['btc_pct']:+.2f}%)")
    if fng and fng.get("value") is not None:
        inst_lines.append(f"  Fear & Greed: {fng['value']} ({fng.get('classification')})")

    lines += [f"", f"🏛 <b>Institutional Context</b>"] + inst_lines

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
# NEWS-CATALYST ALERTS — news as the trigger, not just a filter
# ─────────────────────────────────────────────────────────────────

def analyze_news_catalyst(exchange, symbol: str, news_info: dict) -> dict | None:
    """
    Lighter-weight check for a news-driven candidate: instead of requiring
    the main pipeline's full 3.5x volume explosion, this only confirms the
    coin is showing SOME positive price/volume reaction to a fresh positive
    headline. News is the trigger here — the price/volume check is just
    confirmation it isn't a dead story nobody's trading on.
    """
    try:
        raw = exchange.fetch_ohlcv(symbol, timeframe=cfg.TIMEFRAME_PRIMARY, limit=cfg.VOLUME_LOOKBACK + 5)
        if not raw or len(raw) < cfg.VOLUME_LOOKBACK + 2:
            return None
        candles = ohlcv_to_dicts(raw)
        lookback = candles[-(cfg.VOLUME_LOOKBACK + 1):-1]
        avg_vol = sum(c["volume"] for c in lookback) / len(lookback) if lookback else 0
        cur = candles[-1]
        vol_ratio = (cur["volume"] / avg_vol) if avg_vol > 0 else 0
        price_chg = ((cur["close"] - cur["open"]) / cur["open"] * 100) if cur["open"] else 0
        if vol_ratio < cfg.NEWS_CATALYST_MIN_VOL_RATIO or price_chg <= 0:
            return None

        atr_val = calc_atr(candles) if len(candles) > cfg.ATR_PERIOD else None
        price = cur["close"]
        sl = tp1 = tp2 = None
        if atr_val is not None:
            sl  = price - 1.5 * atr_val
            tp1 = price + 2.0 * atr_val
            tp2 = price + 3.5 * atr_val

        return {
            "symbol":        symbol,
            "price":         price,
            "vol_ratio":     round(vol_ratio, 2),
            "price_chg_pct": round(price_chg, 2),
            "headline":      news_info["headline"],
            "url":           news_info.get("url"),
            "atr":           atr_val,
            "sl":            sl,
            "tp1":           tp1,
            "tp2":           tp2,
        }
    except Exception as e:
        log(f"  ⚠️  news-catalyst check failed for {symbol}: {e}")
        return None


def format_news_catalyst_alert(data: dict) -> str:
    sym  = data["symbol"]
    base = sym.replace("/USDT", "").replace(":", "_")
    price, sl, tp1, tp2 = data["price"], data.get("sl"), data.get("tp1"), data.get("tp2")
    tv_link = cfg.TV_BASE.format(exchange="KUCOIN", base=base)

    lines = [
        f"📰 <b>NEWS CATALYST — {sym}</b>",
        f"",
        f"💰 Price:  <code>{price}</code>",
        f"📊 Volume: <b>{data['vol_ratio']}x</b> avg  |  Candle: <b>{data['price_chg_pct']:+.2f}%</b>",
        f"",
        f"<b>Headline:</b> {data['headline']}",
    ]
    if data.get("url"):
        lines.append(f'<a href="{data["url"]}">Read more</a>')

    if sl is not None and tp1 is not None:
        lines += [
            f"",
            f"📐 <b>Risk Management</b>",
            f"  🔴 Stop Loss:  <code>{round(sl, 8)}</code>",
            f"  🟡 Target 1:   <code>{round(tp1, 8)}</code>",
        ]
        if tp2:
            lines.append(f"  🟢 Target 2:   <code>{round(tp2, 8)}</code>")

    lines += [
        f"",
        f'📈 <a href="{tv_link}">Open on TradingView</a>',
        f"<i>News-driven — NOT the volume-spike pipeline. Confirm before sizing.</i>",
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

def analyze_symbol(exchange, symbol: str, cryptocom=None,
                   btc_candles: list = None, news_items: list = None) -> dict | None:
    """
    Full analysis pipeline for one symbol.
    Returns alert dict if signal qualifies, else None.
    """
    try:
        base = symbol.split("/")[0]

        # ── GATE: coin-specific negative news (hack/delist/lawsuit/etc) ──
        if cfg.USE_NEWS_FILTER and news_items:
            coin_news = check_coin_news(base, news_items, max_age_hours=cfg.NEWS_LOOKBACK_HOURS)
            if coin_news.get("negative"):
                log(f"  🚫 {symbol} blocked — negative news: {coin_news.get('headline')}")
                return None
        else:
            coin_news = None

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

        # ── GATE: volume explosion required first (cheap, no extra API call) ──
        # Checked here too, ahead of the 1h fetch below, so the 1h call only
        # happens for the small subset of symbols that actually have a shot —
        # not all ~850 pairs every cycle.
        explosion, _, _ = calc_volume_explosion(candles)
        if not explosion:
            return None

        # ── Higher-TF (1h) candles, for the shared engine's golden-cross/HTF check ──
        candles_1h = None
        try:
            raw_1h = exchange.fetch_ohlcv(symbol, timeframe=cfg.TIMEFRAME_CONFIRM, limit=cfg.CANDLES_CONFIRM)
            candles_1h = ohlcv_to_dicts(raw_1h)
        except Exception:
            pass

        # ── Shared OHLCV-only scoring pass (identical code path used by the backtester) ──
        result = evaluate_candidate(candles, candles_1h=candles_1h,
                                    btc_candles_15m=btc_candles, coin_news=coin_news)
        if result is None:
            return None   # volume-explosion / CLV gate failed
        vol_ratio = result["vol_ratio"]

        if result["clv"] is not None and result["clv"] < cfg.MIN_CLV:
            log(f"  🚫 {symbol} vol={vol_ratio}x but CLV={result['clv']} — closed near the low, "
                f"likely selling/distribution. Skipped.")
            return None

        # ── GATE: live-only volume direction confirmation (taker buy/sell split) ──
        # A volume spike alone isn't a buy signal — it has to be BUYING volume.
        # This needs live trade data, so it can't be replayed in the backtester.
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

        reasons = result["reasons"]
        if result["clv"] is not None or buy_ratio is not None:
            clv_str = f"CLV={result['clv']}" if result["clv"] is not None else "CLV=n/a"
            buy_str = f"Buy ratio={buy_ratio}" if buy_ratio is not None else "Buy ratio=n/a"
            reasons.append(f"✅ Volume confirmed buy-side ({clv_str} | {buy_str})")

        if cc_buy_ratio is not None:
            tag = "✅" if cc_buy_ratio >= cfg.MIN_TAKER_BUY_RATIO else "⚠️"
            reasons.append(f"{tag} Crypto.com cross-check: buy ratio={cc_buy_ratio}")

        if ob is not None:
            reasons.append(f"✅ Order book clear (bid_ratio={ob['bid_ratio']}, ±{int(cfg.ORDER_BOOK_DEPTH_PCT*100)}% depth)")

        if result["score"] < cfg.SCORE_THRESHOLD:
            return None

        return {
            "symbol":        symbol,
            "score":         result["score"],
            "price":         result["price"],
            "vol_ratio":     vol_ratio,
            "price_chg_pct": result["price_chg_pct"],
            "reasons":       reasons,
            "atr":           result["atr"],
            "sl":            result["sl"],
            "tp1":           result["tp1"],
            "tp2":           result["tp2"],
            "htf_confirmed": result["htf_confirmed"],
            "golden_cross":  result["golden_cross"],
            "rel_strength":  result["rel_strength"],
            "components":    result["components"],
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
        final_outcome = None

        if outcome == "sl_hit":
            stats["losses"] += 1
            resolved.append(f"❌ {p['symbol']}: SL hit (score {p['score']})")
            final_outcome = "sl_hit"
        elif outcome in ("tp1_hit", "tp2_hit"):
            stats["wins"] += 1
            label = "TP2" if outcome == "tp2_hit" else "TP1"
            resolved.append(f"✅ {p['symbol']}: {label} hit (score {p['score']})")
            final_outcome = outcome
        elif outcome == "open":
            if age_hours < OUTCOME_EXPIRY_HOURS:
                still_open.append(p)
            else:
                stats["expired"] += 1
                resolved.append(f"⌛ {p['symbol']}: expired, no level hit (score {p['score']})")
                final_outcome = "expired"
        else:  # 'error' — retry next cycle, but don't track forever
            if age_hours < OUTCOME_EXPIRY_HOURS:
                still_open.append(p)

        if final_outcome:
            try:
                append_trade_log({
                    "symbol":        p["symbol"],
                    "alert_time":    p["alert_time"],
                    "resolved_time": datetime.now(timezone.utc).isoformat(),
                    "score":         p["score"],
                    "entry":         p.get("entry"),
                    "sl":            p.get("sl"),
                    "tp1":           p.get("tp1"),
                    "tp2":           p.get("tp2"),
                    "outcome":       final_outcome,
                    "components":    p.get("components", {}),
                    "source":        "live",
                })
            except Exception as e:
                log(f"  ⚠️  failed to write trade log entry for {p['symbol']}: {e}")

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

    # ── BTC 15m candles (for relative-strength comparisons) ──
    btc_15m = []
    if cfg.USE_RELATIVE_STRENGTH:
        try:
            btc_15m = ohlcv_to_dicts(kucoin.fetch_ohlcv("BTC/USDT", timeframe=cfg.TIMEFRAME_PRIMARY,
                                                          limit=cfg.RS_LOOKBACK + 5))
        except Exception as e:
            log(f"⚠️  BTC 15m fetch failed: {e} — relative-strength check disabled this cycle")

    # ── Market sentiment: Fear & Greed + news (fetched once per run) ──
    fng = fetch_fear_greed() if cfg.USE_FEAR_GREED else None
    if fng:
        log(f"🌡️  Fear & Greed Index: {fng['value']} ({fng['classification']})")

    news_items = fetch_latest_news() if cfg.USE_NEWS_FILTER else []
    if cfg.USE_NEWS_FILTER:
        if news_items:
            log(f"📰 Fetched {len(news_items)} news item(s) from CryptoCompare")
        else:
            log("⚠️  Fetched 0 news items (CryptoCompare unreachable or empty response) — "
                "coin/market news gates and catalyst pass are no-ops this cycle")

    market_news_risk_off, market_news_headline = False, None
    if cfg.USE_NEWS_FILTER:
        mw = check_market_wide_news(news_items, max_age_hours=cfg.NEWS_MARKET_LOOKBACK_HOURS)
        market_news_risk_off, market_news_headline = mw["risk_off"], mw["headline"]
        if market_news_risk_off:
            log(f"🛑 Market-wide risk-off news: {market_news_headline} — pausing new signals this cycle")
            send_telegram(
                f"🛑 <b>Scanner paused this cycle</b>\n"
                f"Reason: {market_news_headline}\n"
                f"No new long signals will be generated until conditions clear.",
                silent=True,
            )

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

    effective_threshold = cfg.SCORE_THRESHOLD
    if not btc_ctx["bullish"]:
        log("⚠️  BTC context is BEARISH — applying stricter score threshold (+10)")
        effective_threshold += 10
    if cfg.USE_FEAR_GREED and fng and fng.get("value", 0) >= cfg.FEAR_GREED_EXTREME_GREED:
        log(f"⚠️  Fear&Greed EXTREME GREED ({fng['value']}) — raising threshold by {cfg.FEAR_GREED_THRESHOLD_BUMP} (euphoria = high reversal risk)")
        effective_threshold += cfg.FEAR_GREED_THRESHOLD_BUMP

    if market_news_risk_off:
        log("⏸️  Skipping scan loop this cycle due to market-wide risk-off news")
    else:
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

            result = analyze_symbol(kucoin, symbol, cryptocom, btc_candles=btc_15m, news_items=news_items)
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

            result["fng"] = fng
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
            "components": a.get("components", {}),
        })
        sent += 1
        time.sleep(1)   # small delay between Telegram messages

    if sent == 0 and not is_first_run and not new_listings:
        log("💤 No qualifying signals this cycle — Telegram silent")

    # ── News-Catalyst pass — news as the trigger, not just a filter on ──
    # ── the volume-spike pipeline above. Separate cooldown-respecting scan. ──
    news_catalyst_sent = 0
    if not cfg.USE_NEWS_CATALYST_ALERTS:
        pass
    elif market_news_risk_off:
        log("📰 News-catalyst pass: skipped (market-wide risk-off news this cycle)")
    elif not news_items:
        log("📰 News-catalyst pass: skipped (0 news items fetched this cycle)")
    else:
        catalyst_matches = match_symbols_to_news(usdt_symbols, news_items,
                                                  max_age_hours=cfg.NEWS_CATALYST_MAX_AGE_HOURS)
        for base, news_info in catalyst_matches.items():
            if news_catalyst_sent >= cfg.MAX_NEWS_CATALYST_ALERTS_PER_RUN:
                break
            symbol = f"{base}/{cfg.QUOTE}"
            if symbol not in current_symbols or is_on_cooldown(symbol, alert_history):
                continue
            result = analyze_news_catalyst(kucoin, symbol, news_info)
            if result is None:
                time.sleep(cfg.RATE_LIMIT_SLEEP)
                continue
            msg = format_news_catalyst_alert(result)
            send_telegram(msg)
            alert_history[symbol] = datetime.now(timezone.utc).isoformat()
            if result.get("sl") is not None:
                state.setdefault("pending_outcomes", []).append({
                    "symbol":     symbol,
                    "alert_time": datetime.now(timezone.utc).isoformat(),
                    "score":      None,
                    "entry":      result["price"],
                    "sl":         result["sl"],
                    "tp1":        result["tp1"],
                    "tp2":        result["tp2"],
                    "components": {"news_catalyst": True},
                })
            news_catalyst_sent += 1
            log(f"  📰 NEWS CATALYST: {symbol} — {news_info['headline'][:80]}")
            time.sleep(cfg.RATE_LIMIT_SLEEP)

        log(f"📰 News-catalyst pass: {len(catalyst_matches)} headline match(es), {news_catalyst_sent} alert(s) sent")

    # Summary ping (every cycle, silent notification)
    btc_rsi_str = f"RSI {btc_ctx['rsi']}" if btc_ctx["rsi"] else ""
    fng_str = f" | F&G: {fng['value']} ({fng['classification']})" if fng else ""
    pause_str = " | ⏸️ paused (news risk-off)" if market_news_risk_off else ""
    summary = (
        f"🔍 Scan complete — {checked} pairs checked\n"
        f"Signals: {sent} | News catalysts: {news_catalyst_sent} | BTC: {btc_ctx['trend']} {btc_rsi_str}{fng_str}{pause_str}\n"
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
