"""
Pre-Breakout Scanner — Technical Indicators Library
====================================================
Pure-Python implementations. No pandas, no ta-lib, no numpy.
All functions accept a list of OHLCV dicts:
  {"ts": int, "open": float, "high": float, "low": float,
   "close": float, "volume": float}

Return values are documented per function.
"""

import math
from config import (
    RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD, BB_SQUEEZE_PERIOD,
    ATR_PERIOD, OBV_EMA_PERIOD, STOCH_RSI_PERIOD,
    CMF_PERIOD, WILLIAMS_PERIOD, DONCHIAN_PERIOD,
    REGRESSION_PERIOD, TREND_FAST_EMA, TREND_SLOW_EMA,
    ADL_EMA_FAST, ADL_EMA_SLOW, VOLUME_LOOKBACK, VOLUME_SPIKE_RATIO,
)


# ═══════════════════════════════════════════════════════════════════
# PRIMITIVES
# ═══════════════════════════════════════════════════════════════════

def sma(values: list, period: int) -> list:
    """Simple Moving Average. Returns list of same length; None where insufficient data."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i - period + 1 : i + 1]) / period
    return result


def ema(values: list, period: int, seed: float = None) -> list:
    """Exponential Moving Average. Seeds from SMA of first `period` bars."""
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    start = seed if seed is not None else sum(values[:period]) / period
    result.append(start)
    prev = start
    for v in values[period:]:
        cur = v * k + prev * (1 - k)
        result.append(cur)
        prev = cur
    return result


def stdev(values: list) -> float:
    """Population standard deviation of a list."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def _closes(candles): return [c["close"] for c in candles]
def _highs(candles):  return [c["high"]  for c in candles]
def _lows(candles):   return [c["low"]   for c in candles]
def _vols(candles):   return [c["volume"] for c in candles]


# ═══════════════════════════════════════════════════════════════════
# VOLUME EXPLOSION
# ═══════════════════════════════════════════════════════════════════

def calc_volume_explosion(candles: list) -> tuple:
    """
    Compares last candle volume against VOLUME_LOOKBACK-bar average.
    Returns: (is_explosion: bool, ratio: float, price_change_pct: float)
    """
    if len(candles) < VOLUME_LOOKBACK + 2:
        return False, 0.0, 0.0
    lookback = candles[-(VOLUME_LOOKBACK + 1):-1]
    avg_vol = sum(c["volume"] for c in lookback) / len(lookback)
    if avg_vol <= 0:
        return False, 0.0, 0.0
    cur_vol = candles[-1]["volume"]
    ratio   = cur_vol / avg_vol
    o, cl   = candles[-1]["open"], candles[-1]["close"]
    pct     = ((cl - o) / o * 100) if o > 0 else 0.0
    return ratio >= VOLUME_SPIKE_RATIO, round(ratio, 2), round(pct, 2)


# ═══════════════════════════════════════════════════════════════════
# CLOSE LOCATION VALUE (volume direction confirmation — VSA-style)
# ═══════════════════════════════════════════════════════════════════

def calc_close_location_value(candles: list) -> float | None:
    """
    CLV (Close Location Value) for the most recent candle.
    Tells you WHERE in the candle's range the close happened —
    this is what separates "volume on buying" from "volume on selling".

      1.0 = closed at the high  -> strong buying pressure absorbed the volume
      0.5 = closed mid-range    -> indecisive / two-sided volume
      0.0 = closed at the low   -> strong selling pressure, volume was distribution

    Returns None if the candle has zero range (high == low).
    """
    c   = candles[-1]
    rng = c["high"] - c["low"]
    if rng <= 0:
        return None
    return round((c["close"] - c["low"]) / rng, 3)


# ═══════════════════════════════════════════════════════════════════
# RSI
# ═══════════════════════════════════════════════════════════════════

def calc_rsi(candles: list, period: int = RSI_PERIOD) -> float:
    """
    Wilder RSI. Returns current RSI value (0-100), or None if insufficient data.
    """
    closes = _closes(candles)
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


# ═══════════════════════════════════════════════════════════════════
# MACD
# ═══════════════════════════════════════════════════════════════════

def calc_macd(candles: list,
              fast: int = MACD_FAST,
              slow: int = MACD_SLOW,
              signal_period: int = MACD_SIGNAL) -> dict:
    """
    Returns dict:
      macd_line  : float
      signal_line: float
      histogram  : float
      bullish_cross: bool  (macd crossed above signal in last 2 bars)
      momentum   : 'strengthening' | 'weakening' | 'neutral'
    """
    closes = _closes(candles)
    fast_ema  = ema(closes, fast)
    slow_ema  = ema(closes, slow)
    macd_line = [
        (f - s) if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema)
    ]
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal_period:
        return {"macd_line": None, "signal_line": None, "histogram": None,
                "bullish_cross": False, "momentum": "neutral"}

    sig_series   = ema(valid_macd, signal_period)
    cur_macd     = valid_macd[-1]
    cur_signal   = sig_series[-1]
    prev_macd    = valid_macd[-2] if len(valid_macd) > 1 else cur_macd
    prev_signal  = sig_series[-2] if len(sig_series) > 1 and sig_series[-2] is not None else cur_signal

    histogram    = cur_macd - cur_signal if cur_signal is not None else 0.0
    prev_histo   = prev_macd - prev_signal if prev_signal is not None else 0.0

    # Bullish cross: macd was below signal, now above
    bullish_cross = (prev_macd < prev_signal) and (cur_macd > cur_signal) if cur_signal is not None else False

    if histogram > prev_histo > 0:
        momentum = "strengthening"
    elif histogram < prev_histo < 0:
        momentum = "weakening"
    else:
        momentum = "neutral"

    return {
        "macd_line":    round(cur_macd, 6),
        "signal_line":  round(cur_signal, 6) if cur_signal else None,
        "histogram":    round(histogram, 6),
        "bullish_cross": bullish_cross,
        "momentum":     momentum,
    }


# ═══════════════════════════════════════════════════════════════════
# BOLLINGER BANDS + SQUEEZE DETECTOR
# ═══════════════════════════════════════════════════════════════════

def calc_bollinger(candles: list,
                   period: int = BB_PERIOD,
                   std_mult: float = BB_STD) -> dict:
    """
    Returns dict:
      upper, middle, lower : float
      bandwidth            : float  (% of middle)
      percent_b            : float  (price position within bands 0-1)
      squeeze_detected     : bool   (bandwidth at N-bar low, expanding now)
    """
    closes = _closes(candles)
    if len(closes) < period + BB_SQUEEZE_PERIOD:
        return {"upper": None, "middle": None, "lower": None,
                "bandwidth": None, "percent_b": None, "squeeze_detected": False}

    # Current band
    window  = closes[-period:]
    middle  = sum(window) / period
    sd      = stdev(window)
    upper   = middle + std_mult * sd
    lower   = middle - std_mult * sd
    bw      = (upper - lower) / middle * 100 if middle else 0

    # Percent-B
    pct_b = (closes[-1] - lower) / (upper - lower) if (upper - lower) else 0.5

    # Squeeze: bandwidth hit a recent low then started expanding
    bw_history = []
    for i in range(BB_SQUEEZE_PERIOD + 1, 0, -1):
        win = closes[-(period + i): -i] if i > 0 else closes[-period:]
        if len(win) < period:
            bw_history.append(bw)
            continue
        m  = sum(win) / period
        s  = stdev(win)
        bw_history.append(((m + std_mult * s) - (m - std_mult * s)) / m * 100 if m else 0)

    squeeze_detected = False
    if len(bw_history) >= 2:
        min_bw   = min(bw_history[:-1])
        prev_bw  = bw_history[-1]
        # squeeze = prev bandwidth was the minimum AND current is expanding
        squeeze_detected = (prev_bw <= min_bw * 1.05) and (bw > prev_bw)

    return {
        "upper":            round(upper, 8),
        "middle":           round(middle, 8),
        "lower":            round(lower, 8),
        "bandwidth":        round(bw, 4),
        "percent_b":        round(pct_b, 4),
        "squeeze_detected": squeeze_detected,
    }


# ═══════════════════════════════════════════════════════════════════
# ATR (Average True Range)
# ═══════════════════════════════════════════════════════════════════

def calc_atr(candles: list, period: int = ATR_PERIOD) -> float:
    """Returns current ATR value. Used for SL/TP sizing."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h   = candles[i]["high"]
        l   = candles[i]["low"]
        pc  = candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    # Wilder smoothing
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return round(atr, 8)


# ═══════════════════════════════════════════════════════════════════
# OBV (On-Balance Volume)
# ═══════════════════════════════════════════════════════════════════

def calc_obv(candles: list) -> dict:
    """
    Returns dict:
      current_obv : float
      obv_trend   : 'rising' | 'falling' | 'flat'
      obv_divergence: bool  (price making new high but OBV not confirming)
    """
    if len(candles) < OBV_EMA_PERIOD + 1:
        return {"current_obv": None, "obv_trend": "flat", "obv_divergence": False}

    obv = [0.0]
    for i in range(1, len(candles)):
        if candles[i]["close"] > candles[i - 1]["close"]:
            obv.append(obv[-1] + candles[i]["volume"])
        elif candles[i]["close"] < candles[i - 1]["close"]:
            obv.append(obv[-1] - candles[i]["volume"])
        else:
            obv.append(obv[-1])

    obv_ema = ema(obv, OBV_EMA_PERIOD)
    cur_ema  = next((v for v in reversed(obv_ema) if v is not None), 0)
    prev_ema = next((v for v in reversed(obv_ema[:-1]) if v is not None), 0)

    trend = "rising" if cur_ema > prev_ema else ("falling" if cur_ema < prev_ema else "flat")

    # Divergence: price made new 10-bar high but OBV didn't
    recent_closes = [c["close"] for c in candles[-10:]]
    recent_obv    = obv[-10:]
    price_new_high = recent_closes[-1] >= max(recent_closes[:-1])
    obv_new_high   = recent_obv[-1]  >= max(recent_obv[:-1])
    divergence     = price_new_high and not obv_new_high

    return {
        "current_obv":  round(obv[-1], 2),
        "obv_trend":    trend,
        "obv_divergence": divergence,
    }


# ═══════════════════════════════════════════════════════════════════
# Stochastic RSI
# ═══════════════════════════════════════════════════════════════════

def calc_stoch_rsi(candles: list, period: int = STOCH_RSI_PERIOD) -> dict:
    """
    Returns dict: k (0-100), d (3-bar SMA of k), zone ('oversold'|'neutral'|'overbought')
    """
    closes = _closes(candles)
    if len(closes) < period * 2 + 1:
        return {"k": None, "d": None, "zone": "neutral"}
    # Build RSI series
    rsi_series = []
    for i in range(period, len(closes) + 1):
        sub = [{"close": c} for c in closes[:i]]
        # minimal RSI calc on sub
        gains, losses = [], []
        for j in range(1, len(sub)):
            diff = sub[j]["close"] - sub[j-1]["close"]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        if len(gains) < period:
            continue
        ag = sum(gains[:period]) / period
        al = sum(losses[:period]) / period
        for j in range(period, len(gains)):
            ag = (ag * (period - 1) + gains[j]) / period
            al = (al * (period - 1) + losses[j]) / period
        rs = ag / al if al != 0 else 100
        rsi_series.append(100 - 100 / (1 + rs))

    if len(rsi_series) < period:
        return {"k": None, "d": None, "zone": "neutral"}

    window = rsi_series[-period:]
    lo, hi = min(window), max(window)
    k = (rsi_series[-1] - lo) / (hi - lo) * 100 if hi != lo else 50
    d = sum(rsi_series[-3:]) / 3

    zone = "oversold" if k < 20 else ("overbought" if k > 80 else "neutral")
    return {"k": round(k, 2), "d": round(d, 2), "zone": zone}


# ═══════════════════════════════════════════════════════════════════
# CMF (Chaikin Money Flow)
# ═══════════════════════════════════════════════════════════════════

def calc_cmf(candles: list, period: int = CMF_PERIOD) -> float:
    """
    Returns CMF value (-1 to +1). Positive = accumulation, Negative = distribution.
    """
    if len(candles) < period:
        return None
    window = candles[-period:]
    mfv_sum = 0.0
    vol_sum = 0.0
    for c in window:
        h, l, cl, vol = c["high"], c["low"], c["close"], c["volume"]
        if h != l:
            mfm  = ((cl - l) - (h - cl)) / (h - l)
            mfv_sum += mfm * vol
        vol_sum += vol
    return round(mfv_sum / vol_sum, 4) if vol_sum else 0.0


# ═══════════════════════════════════════════════════════════════════
# Williams %R
# ═══════════════════════════════════════════════════════════════════

def calc_williams_r(candles: list, period: int = WILLIAMS_PERIOD) -> float:
    """
    Returns Williams %R (-100 to 0).
    Above -20 = overbought, Below -80 = oversold.
    """
    if len(candles) < period:
        return None
    window = candles[-period:]
    hh = max(c["high"]  for c in window)
    ll = min(c["low"]   for c in window)
    cl = candles[-1]["close"]
    if hh == ll:
        return -50.0
    return round(((hh - cl) / (hh - ll)) * -100, 2)


# ═══════════════════════════════════════════════════════════════════
# ADL + Chaikin Oscillator
# ═══════════════════════════════════════════════════════════════════

def calc_adl_chaikin(candles: list) -> dict:
    """
    Returns dict:
      adl_trend    : 'rising' | 'falling'
      chaikin_value: float
      signal       : 'accumulation_accelerating' | 'accumulation' |
                     'distribution_accelerating' | 'distribution'
    """
    adl, cum = [], 0.0
    for c in candles:
        h, l, cl, vol = c["high"], c["low"], c["close"], c["volume"]
        mfm  = ((cl - l) - (h - cl)) / (h - l) if h != l else 0.0
        cum += mfm * vol
        adl.append(cum)

    e3  = ema(adl, ADL_EMA_FAST)
    e10 = ema(adl, ADL_EMA_SLOW)
    chai = [(a - b) if a is not None and b is not None else None
            for a, b in zip(e3, e10)]
    valid = [v for v in chai if v is not None]
    if len(valid) < 2:
        return {"adl_trend": "flat", "chaikin_value": 0.0, "signal": "neutral"}

    cur, prev = valid[-1], valid[-2]
    adl_trend = "rising" if adl[-1] > adl[-min(10, len(adl))] else "falling"

    if cur > 0 and cur > prev:
        sig = "accumulation_accelerating"
    elif cur > 0:
        sig = "accumulation"
    elif cur < 0 and cur < prev:
        sig = "distribution_accelerating"
    else:
        sig = "distribution"

    return {"adl_trend": adl_trend, "chaikin_value": round(cur, 4), "signal": sig}


# ═══════════════════════════════════════════════════════════════════
# Donchian Channel Breakout
# ═══════════════════════════════════════════════════════════════════

def calc_donchian(candles: list, period: int = DONCHIAN_PERIOD) -> dict:
    """
    Returns dict:
      breakout_up  : bool
      upper        : float  (highest high of prior N bars)
      lower        : float  (lowest low of prior N bars)
      breakout_pct : float  (how far above upper the close is, in %)
    """
    if len(candles) < period + 1:
        return {"breakout_up": False, "upper": None, "lower": None, "breakout_pct": 0.0}
    prior   = candles[-(period + 1):-1]
    upper   = max(c["high"] for c in prior)
    lower   = min(c["low"]  for c in prior)
    close   = candles[-1]["close"]
    bkout   = close > upper
    bk_pct  = ((close - upper) / upper * 100) if (bkout and upper) else 0.0
    return {
        "breakout_up":  bkout,
        "upper":        round(upper, 8),
        "lower":        round(lower, 8),
        "breakout_pct": round(bk_pct, 3),
    }


# ═══════════════════════════════════════════════════════════════════
# Linear Regression Channel
# ═══════════════════════════════════════════════════════════════════

def calc_linear_regression(candles: list, period: int = REGRESSION_PERIOD) -> dict:
    """
    Returns dict:
      slope_pct : float  (normalized slope as % of avg price per bar)
      z_score   : float  (current price deviation from regression line in SD units)
      in_channel: bool   (-2 < z_score < 2 and slope > 0)
    """
    closes = _closes(candles[-period:])
    n = len(closes)
    if n < period:
        return {"slope_pct": 0.0, "z_score": 0.0, "in_channel": False}
    xs     = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(closes) / n
    num    = sum((xs[i] - x_mean) * (closes[i] - y_mean) for i in range(n))
    den    = sum((xs[i] - x_mean) ** 2 for i in range(n))
    slope  = num / den if den else 0.0
    inter  = y_mean - slope * x_mean
    resid  = [closes[i] - (slope * xs[i] + inter) for i in range(n)]
    std    = math.sqrt(sum(r ** 2 for r in resid) / n) if n else 0.0
    pred   = slope * (n - 1) + inter
    z      = (closes[-1] - pred) / std if std else 0.0
    norm_slope = (slope / y_mean) * 100 if y_mean else 0.0
    return {
        "slope_pct":  round(norm_slope, 4),
        "z_score":    round(z, 2),
        "in_channel": slope > 0 and -2.0 < z < 2.0,
    }


# ═══════════════════════════════════════════════════════════════════
# Auto Trend (EMA + Swing High/Low)
# ═══════════════════════════════════════════════════════════════════

def calc_trend(candles: list,
               fast: int = TREND_FAST_EMA,
               slow: int = TREND_SLOW_EMA) -> str:
    """
    Returns 'bullish' | 'bearish' | 'sideways'
    Uses EMA alignment + swing structure confirmation.
    """
    closes = _closes(candles)
    if len(closes) < slow + 2:
        return "sideways"
    ef = ema(closes, fast)
    es = ema(closes, slow)
    f, s = ef[-1], es[-1]
    if f is None or s is None:
        return "sideways"
    ema_trend = "bullish" if f > s else "bearish"

    recent = candles[-10:]
    prior  = candles[-20:-10]
    rh = max(c["high"] for c in recent)
    ph = max(c["high"] for c in prior)
    rl = min(c["low"]  for c in recent)
    pl = min(c["low"]  for c in prior)

    if rh > ph and rl > pl:
        swing = "bullish"
    elif rh < ph and rl < pl:
        swing = "bearish"
    else:
        swing = "sideways"

    return ema_trend if ema_trend == swing else "sideways"


# ═══════════════════════════════════════════════════════════════════
# HIGHER-TIMEFRAME CONFIRMATION (1h)
# ═══════════════════════════════════════════════════════════════════

def htf_confirmation(candles_1h: list) -> dict:
    """
    Quick sanity check on 1h candles.
    Returns dict: bullish (bool), trend (str), rsi (float)
    """
    if not candles_1h or len(candles_1h) < 30:
        return {"bullish": False, "trend": "unknown", "rsi": None}
    trend   = calc_trend(candles_1h)
    rsi_val = calc_rsi(candles_1h)
    # 1h is bullish if: trend is bullish AND RSI is not overbought (< 75)
    bullish = trend == "bullish" and (rsi_val is None or rsi_val < 75)
    return {"bullish": bullish, "trend": trend, "rsi": rsi_val}


# ═══════════════════════════════════════════════════════════════════
# COMPOSITE SCORER
# ═══════════════════════════════════════════════════════════════════

def build_score(
    vol_ratio:      float,
    price_chg_pct:  float,
    rsi:            float,
    macd:           dict,
    bb:             dict,
    donchian:       dict,
    lin_reg:        dict,
    trend:          str,
    adl_chai:       dict,
    obv:            dict,
    htf:            dict,
) -> tuple:
    """
    Returns (score: int [0-100], reasons: list[str])
    """
    from config import (
        WEIGHT_VOLUME_EXPLOSION, WEIGHT_BB_SQUEEZE, WEIGHT_RSI,
        WEIGHT_MACD, WEIGHT_DONCHIAN, WEIGHT_TREND_EMA,
        WEIGHT_ADL_CHAIKIN, WEIGHT_LIN_REGRESSION, WEIGHT_OBV,
        VOLUME_SPIKE_RATIO, HTF_CONFIRM_BONUS, EARLY_MOVE_BONUS,
    )
    score   = 0
    reasons = []

    # ── 1. Volume Explosion (0 → WEIGHT_VOLUME_EXPLOSION) ──
    vol_pts = min(WEIGHT_VOLUME_EXPLOSION, (vol_ratio / VOLUME_SPIKE_RATIO) * (WEIGHT_VOLUME_EXPLOSION * 0.7))
    score  += vol_pts
    reasons.append(f"📈 Volume {vol_ratio}x average")

    # ── 2. BB Squeeze → Expansion ──
    if bb.get("squeeze_detected"):
        score  += WEIGHT_BB_SQUEEZE
        reasons.append(f"🔥 BB Squeeze breakout (bw={bb.get('bandwidth','?')}%)")
    elif bb.get("bandwidth") is not None and bb["bandwidth"] < 3.0:
        score  += WEIGHT_BB_SQUEEZE * 0.5
        reasons.append(f"⚡ BB bandwidth very tight ({bb['bandwidth']}%) — coiling")

    # ── 3. RSI (healthy zone 38-68, not overbought) ──
    if rsi is not None:
        if 38 <= rsi <= 68:
            score  += WEIGHT_RSI
            reasons.append(f"✅ RSI healthy ({rsi})")
        elif rsi > 80:
            score  -= 8
            reasons.append(f"⚠️ RSI overbought ({rsi}) — possible late entry")
        elif rsi < 30:
            score  += WEIGHT_RSI * 0.4   # possible bounce but risky
            reasons.append(f"🔄 RSI oversold ({rsi}) — reversal watch")

    # ── 4. MACD ──
    if macd.get("bullish_cross"):
        score  += WEIGHT_MACD
        reasons.append("✅ MACD bullish cross")
    elif macd.get("momentum") == "strengthening" and macd.get("histogram", 0) > 0:
        score  += WEIGHT_MACD * 0.6
        reasons.append("📊 MACD histogram expanding bullish")

    # ── 5. Donchian Breakout ──
    if donchian.get("breakout_up"):
        score  += WEIGHT_DONCHIAN
        pct = donchian.get("breakout_pct", 0)
        reasons.append(f"✅ Donchian channel breakout (+{pct}% above upper)")

    # ── 6. EMA Trend ──
    if trend == "bullish":
        score  += WEIGHT_TREND_EMA
        reasons.append("✅ EMA trend bullish (fast > slow + swing structure)")
    elif trend == "bearish":
        score  -= WEIGHT_TREND_EMA
        reasons.append("⚠️ EMA trend bearish — counter-trend signal")

    # ── 7. ADL + Chaikin ──
    sig = adl_chai.get("signal", "")
    if sig == "accumulation_accelerating":
        score  += WEIGHT_ADL_CHAIKIN
        reasons.append("✅ ADL+Chaikin: accelerating accumulation")
    elif sig == "accumulation":
        score  += WEIGHT_ADL_CHAIKIN * 0.5
        reasons.append("📊 ADL+Chaikin: accumulation")
    elif sig == "distribution_accelerating":
        score  -= 5
        reasons.append("⚠️ ADL+Chaikin: accelerating distribution")

    # ── 8. Linear Regression ──
    if lin_reg.get("in_channel"):
        score  += WEIGHT_LIN_REGRESSION
        reasons.append(f"✅ Inside rising regression channel (z={lin_reg.get('z_score')})")
    elif lin_reg.get("z_score", 0) > 2.5:
        reasons.append(f"⚠️ Price extended above regression (z={lin_reg.get('z_score')}) — pullback risk")

    # ── 9. OBV ──
    if obv.get("obv_trend") == "rising":
        score  += WEIGHT_OBV
        reasons.append("✅ OBV rising (volume confirms price)")
    if obv.get("obv_divergence"):
        score  -= 5
        reasons.append("⚠️ OBV bearish divergence — caution")

    # ── 10. Higher-TF bonus ──
    if htf.get("bullish"):
        score  += HTF_CONFIRM_BONUS
        reasons.append(f"✅ 1h trend bullish (HTF confirmation)")

    # ── 11. Early price move bonus ──
    if 0.3 <= price_chg_pct <= 8.0:
        score  += EARLY_MOVE_BONUS
        reasons.append(f"✅ Early price move ({price_chg_pct}%) — not late")
    elif price_chg_pct > 10:
        score  -= 5
        reasons.append(f"⚠️ Large candle ({price_chg_pct}%) — may be extended")

    score = max(0, min(100, round(score)))
    return score, reasons
