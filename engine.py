"""
Pre-Breakout Scanner — Shared Scoring Engine
==============================================
The OHLCV-only half of the analysis pipeline, factored out of scanner.py so
that the LIVE scanner and the historical BACKTESTER call the exact same
code path. This is what makes the backtest trustworthy: it isn't a
re-implementation of the strategy that could silently drift from what's
actually running in production — it's literally the same function.

What's deliberately NOT in here (because it needs live-only data that
doesn't exist in historical OHLCV): taker buy/sell ratio, order book
imbalance, Binance/Crypto.com cross-validation. Those stay as extra gates
in scanner.py's analyze_symbol(). This means the backtest is an
approximation — it can't replay microstructure gates — and that's
documented wherever backtest results are reported.
"""

import json
import os

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
    calc_golden_death_cross,
    calc_rsi_divergence,
    calc_macd_divergence,
    calc_relative_strength,
    htf_confirmation,
    build_score,
)

# Maps each learnable component -> the config weight it feeds, and whether
# that weight is a bonus (+1) or a penalty (-1, i.e. we WANT this component
# to correlate with losses — if it doesn't, the penalty is miscalibrated).
# The tuner uses this table to turn "component X correlates with wins/losses"
# into "nudge config.WEIGHT_Y up/down".
COMPONENT_WEIGHT_MAP = {
    "rsi_healthy":          ("WEIGHT_RSI",               +1),
    "macd_bullish_cross":   ("WEIGHT_MACD",               +1),
    "bb_squeeze":           ("WEIGHT_BB_SQUEEZE",         +1),
    "donchian_breakout":    ("WEIGHT_DONCHIAN",           +1),
    "trend_bullish":        ("WEIGHT_TREND_EMA",          +1),
    "adl_accumulating":     ("WEIGHT_ADL_CHAIKIN",        +1),
    "obv_rising":           ("WEIGHT_OBV",                +1),
    "htf_confirmed":        ("HTF_CONFIRM_BONUS",         +1),
    "golden_cross_bullish": ("WEIGHT_GOLDEN_CROSS",       +1),
    "death_cross_active":   ("GOLDEN_CROSS_PENALTY",      -1),
    "bullish_divergence":   ("WEIGHT_BULLISH_DIVERGENCE", +1),
    "bearish_divergence":   ("BEARISH_DIVERGENCE_PENALTY", -1),
    "rs_leading":           ("WEIGHT_RELATIVE_STRENGTH",  +1),
    "early_move":           ("EARLY_MOVE_BONUS",          +1),
}


def _extract_components(rsi_val, macd_val, bb_val, don_val, trend, adl_val,
                        obv_val, htf, golden_cross, rsi_div, macd_div,
                        rel_strength, price_chg_pct) -> dict:
    """Boolean snapshot of every learnable signal, keyed to match COMPONENT_WEIGHT_MAP."""
    return {
        "rsi_healthy":          rsi_val is not None and 38 <= rsi_val <= 68,
        "macd_bullish_cross":   bool(macd_val.get("bullish_cross")),
        "bb_squeeze":           bool(bb_val.get("squeeze_detected")),
        "donchian_breakout":    bool(don_val.get("breakout_up")),
        "trend_bullish":        trend == "bullish",
        "adl_accumulating":     adl_val.get("signal") in ("accumulation", "accumulation_accelerating"),
        "obv_rising":           obv_val.get("obv_trend") == "rising",
        "htf_confirmed":        bool(htf.get("bullish")),
        "golden_cross_bullish": golden_cross.get("event") == "golden_cross" or golden_cross.get("trend") == "bullish",
        "death_cross_active":   golden_cross.get("event") == "death_cross" or golden_cross.get("trend") == "bearish",
        "bullish_divergence":   bool(rsi_div.get("bullish") or macd_div.get("bullish")),
        "bearish_divergence":   bool(rsi_div.get("bearish") or macd_div.get("bearish")),
        "rs_leading":           bool(rel_strength and rel_strength.get("leading")),
        "early_move":           cfg.EARLY_MOVE_MIN_PCT <= price_chg_pct <= cfg.EARLY_MOVE_MAX_PCT,
    }


def evaluate_candidate(candles_15m: list, candles_1h: list = None,
                       btc_candles_15m: list = None, coin_news: dict = None) -> dict | None:
    """
    Pure, side-effect-free scoring pass over an already-fetched candle window.
    `candles_15m[-1]` is treated as "now" — this makes it directly reusable
    for a historical walk-forward replay (just slide the window).

    Returns None if the volume-explosion / CLV gates fail (nothing to score).
    Otherwise returns a dict: score, reasons, price, vol_ratio, price_chg_pct,
    atr, sl, tp1, tp2, htf_confirmed, golden_cross, rel_strength, components.

    Does NOT apply cfg.SCORE_THRESHOLD — callers decide what to do with the
    score (live scanner filters immediately; the backtester keeps everything
    so thresholds can be swept after the fact).
    """
    if not candles_15m or len(candles_15m) < cfg.VOLUME_LOOKBACK + 10:
        return None

    explosion, vol_ratio, price_chg_pct = calc_volume_explosion(candles_15m)
    if not explosion:
        return None

    clv = calc_close_location_value(candles_15m)
    if clv is not None and clv < cfg.MIN_CLV:
        return None

    rsi_val  = calc_rsi(candles_15m)
    macd_val = calc_macd(candles_15m)
    bb_val   = calc_bollinger(candles_15m)
    atr_val  = calc_atr(candles_15m)
    obv_val  = calc_obv(candles_15m)
    adl_val  = calc_adl_chaikin(candles_15m)
    don_val  = calc_donchian(candles_15m)
    reg_val  = calc_linear_regression(candles_15m)
    trend    = calc_trend(candles_15m)
    stoch    = calc_stoch_rsi(candles_15m)
    cmf_val  = calc_cmf(candles_15m)
    will_r   = calc_williams_r(candles_15m)

    htf = {"bullish": False, "trend": "unknown", "rsi": None}
    golden_cross = {"event": "none", "fast_ma": None, "slow_ma": None,
                    "trend": "unknown", "bars_since_cross": None}
    if candles_1h:
        htf = htf_confirmation(candles_1h)
        if cfg.USE_GOLDEN_CROSS:
            golden_cross = calc_golden_death_cross(candles_1h)

    rsi_div  = {"bullish": False, "bearish": False, "detail": None}
    macd_div = {"bullish": False, "bearish": False, "detail": None}
    if cfg.USE_DIVERGENCE_DETECTION:
        rsi_div  = calc_rsi_divergence(candles_15m)
        macd_div = calc_macd_divergence(candles_15m)

    rel_strength = None
    if cfg.USE_RELATIVE_STRENGTH and btc_candles_15m:
        rel_strength = calc_relative_strength(candles_15m, btc_candles_15m, lookback=cfg.RS_LOOKBACK)

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
        golden_cross=golden_cross,
        rsi_div=rsi_div,
        macd_div=macd_div,
        rel_strength=rel_strength,
        coin_news=coin_news,
    )

    extra = []
    if stoch.get("k") is not None:
        extra.append(f"StochRSI K={stoch['k']} ({stoch['zone']})")
    if cmf_val is not None:
        extra.append(f"CMF={cmf_val} ({'▲ buy' if cmf_val > 0 else '▼ sell'})")
    if will_r is not None:
        extra.append(f"Williams%R={will_r}")
    if extra:
        reasons.append("ℹ️  " + "  |  ".join(extra))

    price = candles_15m[-1]["close"]
    sl = tp1 = tp2 = None
    if atr_val is not None:
        sl  = price - 1.5 * atr_val
        tp1 = price + 2.0 * atr_val
        tp2 = price + 3.5 * atr_val

    components = _extract_components(rsi_val, macd_val, bb_val, don_val, trend,
                                      adl_val, obv_val, htf, golden_cross,
                                      rsi_div, macd_div, rel_strength, price_chg_pct)

    return {
        "score":         score,
        "price":         price,
        "vol_ratio":     vol_ratio,
        "price_chg_pct": price_chg_pct,
        "reasons":       reasons,
        "atr":           atr_val,
        "sl":            sl,
        "tp1":           tp1,
        "tp2":           tp2,
        "clv":           clv,
        "htf_confirmed": htf.get("bullish", False),
        "golden_cross":  golden_cross,
        "rel_strength":  rel_strength,
        "components":    components,
    }


# ═══════════════════════════════════════════════════════════════════
# TRADE LOG — the shared "memory" that live and backtest both feed,
# and that tuner.py reads to learn which components actually predict wins.
# ═══════════════════════════════════════════════════════════════════

def append_trade_log(record: dict, path: str = None):
    """
    Appends one resolved trade to the JSONL trade log. Expected keys:
      symbol, alert_time, resolved_time, score, entry, sl, tp1, tp2,
      outcome ('tp1_hit'|'tp2_hit'|'sl_hit'|'expired'), components (dict),
      source ('live'|'backtest')
    """
    path = path or cfg.TRADE_LOG_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_trade_log(path: str = None) -> list:
    """Reads the JSONL trade log. Skips (and ignores) any malformed lines."""
    path = path or cfg.TRADE_LOG_FILE
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records
