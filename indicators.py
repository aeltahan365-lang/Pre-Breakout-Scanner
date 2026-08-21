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
    MA_FAST_PERIOD, MA_SLOW_PERIOD, DIVERGENCE_LOOKBACK,
    REVERSAL_PROXIMITY_PCT, REVERSAL_MIN_BASE_BARS, REVERSAL_PRIOR_DECLINE_PCT,
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
    Returns dict:
      k (0-100), d (3-bar SMA of k), zone ('oversold'|'neutral'|'overbought')
      turning_up : bool  (K is rising and was recently oversold/low — the
                          "coming off the bottom" trigger for the reversal detector)
    """
    closes = _closes(candles)
    if len(closes) < period * 2 + 1:
        return {"k": None, "d": None, "zone": "neutral", "turning_up": False}
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
        return {"k": None, "d": None, "zone": "neutral", "turning_up": False}

    window = rsi_series[-period:]
    lo, hi = min(window), max(window)
    k = (rsi_series[-1] - lo) / (hi - lo) * 100 if hi != lo else 50
    d = sum(rsi_series[-3:]) / 3

    k_prev = None
    turning_up = False
    if len(rsi_series) > period:
        prev_window = rsi_series[-period - 1: -1]
        lo2, hi2 = min(prev_window), max(prev_window)
        k_prev = (rsi_series[-2] - lo2) / (hi2 - lo2) * 100 if hi2 != lo2 else 50
        turning_up = k > k_prev and (k_prev < 25 or k < 35)

    zone = "oversold" if k < 20 else ("overbought" if k > 80 else "neutral")
    return {"k": round(k, 2), "d": round(d, 2), "zone": zone, "turning_up": turning_up}


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
# BOTTOM STRUCTURE (v4 — the "has this coin reached the bottom" gate)
# ═══════════════════════════════════════════════════════════════════
# Everything above (volume explosion, Donchian breakout, MACD cross) fires
# on the way UP, after a move has already started. This is the other half
# of the picture: is price currently basing near a multi-bar low, after a
# real prior decline (not just chop)? Run this on a higher timeframe (1h)
# — a genuine bottom is a multi-day structural event, not something you can
# read off a single 15m candle.

def calc_bottom_structure(candles: list, lookback: int) -> dict:
    """
    Returns dict:
      lowest_low        : float | None  (lowest low in the lookback window)
      bars_since_low     : int  | None  (bars since that low printed)
      pct_from_low        : float | None (current close vs lowest_low, in %)
      near_low            : bool  (within REVERSAL_PROXIMITY_PCT of the low,
                                   AND at least REVERSAL_MIN_BASE_BARS have
                                   passed since it printed — not still falling)
      higher_low          : bool  (latest swing low sits above the prior
                                   swing low — classic reversal structure)
      prior_trend_down    : bool  (price fell at least REVERSAL_PRIOR_DECLINE_PCT%
                                   from a local high into the low — confirms
                                   this follows a real decline, not sideways chop)
    """
    empty = {"lowest_low": None, "bars_since_low": None, "pct_from_low": None,
             "near_low": False, "higher_low": False, "prior_trend_down": False,
             "decline_pct": None}
    if len(candles) < lookback + 5:
        return empty

    window = candles[-lookback:]
    lows = _lows(window)
    lowest_low = min(lows)
    low_idx = max(i for i, v in enumerate(lows) if v == lowest_low)   # most recent occurrence
    bars_since_low = (len(window) - 1) - low_idx

    close = candles[-1]["close"]
    pct_from_low = ((close - lowest_low) / lowest_low * 100) if lowest_low else 0.0

    near_low = (
        bars_since_low >= REVERSAL_MIN_BASE_BARS and
        0 <= pct_from_low <= REVERSAL_PROXIMITY_PCT
    )

    # Prior decline: the highest high BEFORE the low, vs the low itself.
    pre_low_segment = window[:low_idx + 1] if low_idx > 0 else window[:1]
    pre_high = max(c["high"] for c in pre_low_segment)
    decline_pct = ((pre_high - lowest_low) / pre_high * 100) if pre_high else 0.0
    prior_trend_down = decline_pct >= REVERSAL_PRIOR_DECLINE_PCT

    # Swing-low structure: is the latest swing low higher than the one before it?
    swing_idxs = _find_swing_points(lows, window=3, kind="low")
    higher_low = False
    if len(swing_idxs) >= 2:
        i1, i2 = swing_idxs[-2], swing_idxs[-1]
        higher_low = lows[i2] > lows[i1]

    return {
        "lowest_low":       round(lowest_low, 10) if lowest_low else None,
        "bars_since_low":   bars_since_low,
        "pct_from_low":     round(pct_from_low, 3),
        "near_low":         near_low,
        "higher_low":       higher_low,
        "prior_trend_down": prior_trend_down,
        "decline_pct":      round(decline_pct, 3),
    }


# ═══════════════════════════════════════════════════════════════════
# ACCUMULATION SIGNATURE (Wyckoff-style volume dry-up / expansion)
# ═══════════════════════════════════════════════════════════════════

def calc_accumulation_signature(candles: list, lookback: int) -> dict:
    """
    During genuine accumulation at a bottom, volume on down-closing candles
    should shrink (sellers exhausted) while volume on up-closing candles
    should expand (buyers stepping in) as the base develops. Splits the
    lookback window in half and compares first vs second.

    Returns dict: down_vol_first, up_vol_first, down_vol_second, up_vol_second,
    down_shrinking (bool), up_expanding (bool), accumulating (bool, both true)
    """
    empty = {"down_vol_first": 0.0, "up_vol_first": 0.0, "down_vol_second": 0.0,
             "up_vol_second": 0.0, "down_shrinking": False, "up_expanding": False,
             "accumulating": False}
    if len(candles) < lookback:
        return empty

    window = candles[-lookback:]
    mid = len(window) // 2
    first, second = window[:mid], window[mid:]

    def _down_up_avg(seg):
        down = [c["volume"] for c in seg if c["close"] < c["open"]]
        up   = [c["volume"] for c in seg if c["close"] >= c["open"]]
        return (
            sum(down) / len(down) if down else 0.0,
            sum(up) / len(up) if up else 0.0,
        )

    down1, up1 = _down_up_avg(first)
    down2, up2 = _down_up_avg(second)

    down_shrinking = down1 > 0 and down2 < down1 * 0.85
    up_expanding   = up1 > 0 and up2 > up1 * 1.15

    return {
        "down_vol_first":  round(down1, 6),
        "up_vol_first":    round(up1, 6),
        "down_vol_second": round(down2, 6),
        "up_vol_second":   round(up2, 6),
        "down_shrinking":  down_shrinking,
        "up_expanding":    up_expanding,
        "accumulating":    down_shrinking and up_expanding,
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
# GOLDEN CROSS / DEATH CROSS (50/200 MA regime — run on 1h)
# ═══════════════════════════════════════════════════════════════════
# The classic institutional trend-regime signal. A 15m volume spike inside
# a 1h death-cross regime is a long fighting the higher-timeframe trend —
# exactly the kind of setup that tends to fail and reverse fast.

def calc_golden_death_cross(candles_htf: list,
                            fast: int = MA_FAST_PERIOD,
                            slow: int = MA_SLOW_PERIOD,
                            lookback_cross: int = 5) -> dict:
    """
    Detects a Golden Cross (fast EMA crosses above slow EMA) or Death Cross
    (fast EMA crosses below slow EMA) within the last `lookback_cross` bars.

    Returns dict:
      event            : 'golden_cross' | 'death_cross' | 'none'
      fast_ma, slow_ma : float | None (current values)
      trend            : 'bullish' | 'bearish' | 'unknown'
      bars_since_cross : int | None
    """
    closes = _closes(candles_htf)
    if len(closes) < slow + lookback_cross + 1:
        return {"event": "none", "fast_ma": None, "slow_ma": None,
                "trend": "unknown", "bars_since_cross": None}

    ef = ema(closes, fast)
    es = ema(closes, slow)
    diffs = [(f - s) if f is not None and s is not None else None
             for f, s in zip(ef, es)]
    valid_idx = [i for i, v in enumerate(diffs) if v is not None]
    if len(valid_idx) < lookback_cross + 1:
        return {"event": "none", "fast_ma": ef[-1], "slow_ma": es[-1],
                "trend": "unknown", "bars_since_cross": None}

    trend = "bullish" if diffs[valid_idx[-1]] > 0 else "bearish"
    event, bars_since = "none", None

    for k in range(1, min(lookback_cross, len(valid_idx) - 1) + 1):
        i_cur, i_prev = valid_idx[-k], valid_idx[-k - 1]
        cur, prev = diffs[i_cur], diffs[i_prev]
        if prev <= 0 < cur:
            event, bars_since = "golden_cross", k - 1
            break
        if prev >= 0 > cur:
            event, bars_since = "death_cross", k - 1
            break

    return {
        "event":            event,
        "fast_ma":          round(ef[-1], 8) if ef[-1] is not None else None,
        "slow_ma":          round(es[-1], 8) if es[-1] is not None else None,
        "trend":            trend,
        "bars_since_cross": bars_since,
    }


# ═══════════════════════════════════════════════════════════════════
# DIVERGENCE DETECTION (RSI & MACD vs price)
# ═══════════════════════════════════════════════════════════════════
# This is the single biggest lever against "alerting after it already
# pumped and is rolling over": bearish divergence (price still pushing up,
# momentum already fading) is the textbook late-entry warning.

def _find_swing_points(values: list, window: int = 3, kind: str = "low") -> list:
    """Local pivot detector: index i is a swing low/high if it's the
    min/max of the (2*window+1)-bar segment centered on it."""
    idxs = []
    n = len(values)
    for i in range(window, n - window):
        seg = values[i - window: i + window + 1]
        if kind == "low" and values[i] == min(seg):
            idxs.append(i)
        elif kind == "high" and values[i] == max(seg):
            idxs.append(i)
    return idxs


def calc_rsi_divergence(candles: list,
                        lookback: int = DIVERGENCE_LOOKBACK,
                        pivot_window: int = 3) -> dict:
    """
    Classic RSI divergence over the last `lookback` bars:
      bullish : price makes a LOWER low, RSI makes a HIGHER low
                (selling pressure fading -> potential reversal up)
      bearish : price makes a HIGHER high, RSI makes a LOWER high
                (momentum fading into the rally -> exhaustion / late entry)
    Returns dict: bullish (bool), bearish (bool), detail (str|None)
    """
    full_closes = _closes(candles)
    if len(candles) < lookback + RSI_PERIOD + 5:
        return {"bullish": False, "bearish": False, "detail": None}

    offset = len(candles) - lookback
    window_closes = full_closes[-lookback:]

    rsi_series = []
    for i in range(lookback):
        sub = full_closes[: offset + i + 1]
        rsi_series.append(calc_rsi([{"close": c} for c in sub]) if len(sub) >= RSI_PERIOD + 1 else None)

    lows_idx  = _find_swing_points(window_closes, pivot_window, "low")
    highs_idx = _find_swing_points(window_closes, pivot_window, "high")

    bullish = bearish = False
    detail = None

    if len(lows_idx) >= 2:
        i1, i2 = lows_idx[-2], lows_idx[-1]
        if rsi_series[i1] is not None and rsi_series[i2] is not None:
            if window_closes[i2] < window_closes[i1] and rsi_series[i2] > rsi_series[i1]:
                bullish = True
                detail = f"price LL ({window_closes[i1]:.6g}→{window_closes[i2]:.6g}) vs RSI HL ({rsi_series[i1]}→{rsi_series[i2]})"

    if len(highs_idx) >= 2:
        i1, i2 = highs_idx[-2], highs_idx[-1]
        if rsi_series[i1] is not None and rsi_series[i2] is not None:
            if window_closes[i2] > window_closes[i1] and rsi_series[i2] < rsi_series[i1]:
                bearish = True
                detail = f"price HH ({window_closes[i1]:.6g}→{window_closes[i2]:.6g}) vs RSI LH ({rsi_series[i1]}→{rsi_series[i2]})"

    return {"bullish": bullish, "bearish": bearish, "detail": detail}


def calc_macd_divergence(candles: list,
                         lookback: int = DIVERGENCE_LOOKBACK,
                         pivot_window: int = 3) -> dict:
    """
    Same idea as RSI divergence, using the MACD histogram instead:
      bullish : price lower low, histogram higher low
      bearish : price higher high, histogram lower high
    Returns dict: bullish (bool), bearish (bool), detail (str|None)
    """
    closes = _closes(candles)
    if len(candles) < lookback + MACD_SLOW + MACD_SIGNAL + 5:
        return {"bullish": False, "bearish": False, "detail": None}

    fast_ema = ema(closes, MACD_FAST)
    slow_ema = ema(closes, MACD_SLOW)
    macd_line = [(f - s) if f is not None and s is not None else None
                 for f, s in zip(fast_ema, slow_ema)]
    valid_positions = [i for i, v in enumerate(macd_line) if v is not None]
    if len(valid_positions) < MACD_SIGNAL + lookback:
        return {"bullish": False, "bearish": False, "detail": None}

    valid_macd = [macd_line[i] for i in valid_positions]
    sig_series = ema(valid_macd, MACD_SIGNAL)
    histogram = [None] * len(candles)
    for pos, m, s in zip(valid_positions, valid_macd, sig_series):
        histogram[pos] = (m - s) if s is not None else None

    window_closes = closes[-lookback:]
    window_hist   = histogram[-lookback:]

    lows_idx  = _find_swing_points(window_closes, pivot_window, "low")
    highs_idx = _find_swing_points(window_closes, pivot_window, "high")

    bullish = bearish = False
    detail = None

    if len(lows_idx) >= 2:
        i1, i2 = lows_idx[-2], lows_idx[-1]
        if window_hist[i1] is not None and window_hist[i2] is not None:
            if window_closes[i2] < window_closes[i1] and window_hist[i2] > window_hist[i1]:
                bullish = True
                detail = "MACD histogram rising while price makes a lower low"

    if len(highs_idx) >= 2:
        i1, i2 = highs_idx[-2], highs_idx[-1]
        if window_hist[i1] is not None and window_hist[i2] is not None:
            if window_closes[i2] > window_closes[i1] and window_hist[i2] < window_hist[i1]:
                bearish = True
                detail = "MACD histogram falling while price makes a higher high"

    return {"bullish": bullish, "bearish": bearish, "detail": detail}


# ═══════════════════════════════════════════════════════════════════
# RELATIVE STRENGTH VS BTC
# ═══════════════════════════════════════════════════════════════════
# No institutional desk reads an altcoin move in isolation — everything is
# read against the market beta (BTC). A volume spike that's just BTC-wide
# chop dragging the alt along is not the same setup as genuine outperformance.

def calc_relative_strength(coin_candles: list, btc_candles: list, lookback: int) -> dict:
    """
    Returns dict: coin_pct, btc_pct, rs_spread (coin_pct - btc_pct), leading (bool)
    or all-None/False if there isn't enough data on either series.
    """
    if len(coin_candles) < lookback + 1 or len(btc_candles) < lookback + 1:
        return {"coin_pct": None, "btc_pct": None, "rs_spread": None, "leading": False}
    c0, c1 = coin_candles[-lookback - 1]["close"], coin_candles[-1]["close"]
    b0, b1 = btc_candles[-lookback - 1]["close"], btc_candles[-1]["close"]
    coin_pct = ((c1 - c0) / c0 * 100) if c0 else 0.0
    btc_pct  = ((b1 - b0) / b0 * 100) if b0 else 0.0
    spread   = coin_pct - btc_pct
    return {
        "coin_pct":  round(coin_pct, 2),
        "btc_pct":   round(btc_pct, 2),
        "rs_spread": round(spread, 2),
        "leading":   spread > 0,
    }


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
    golden_cross:   dict = None,
    rsi_div:        dict = None,
    macd_div:       dict = None,
    rel_strength:   dict = None,
    coin_news:      dict = None,
) -> tuple:
    """
    Returns (score: int [0-100], reasons: list[str])
    """
    from config import (
        WEIGHT_VOLUME_EXPLOSION, WEIGHT_BB_SQUEEZE, WEIGHT_RSI,
        WEIGHT_MACD, WEIGHT_DONCHIAN, WEIGHT_TREND_EMA,
        WEIGHT_ADL_CHAIKIN, WEIGHT_LIN_REGRESSION, WEIGHT_OBV,
        VOLUME_SPIKE_RATIO, HTF_CONFIRM_BONUS, EARLY_MOVE_BONUS,
        EARLY_MOVE_MIN_PCT, EARLY_MOVE_MAX_PCT,
        WEIGHT_GOLDEN_CROSS, GOLDEN_CROSS_PENALTY,
        WEIGHT_BULLISH_DIVERGENCE, BEARISH_DIVERGENCE_PENALTY,
        WEIGHT_RELATIVE_STRENGTH, RS_LAGGARD_PENALTY, RS_LOOKBACK,
        WEIGHT_POSITIVE_NEWS,
    )
    golden_cross = golden_cross or {}
    rsi_div      = rsi_div or {}
    macd_div     = macd_div or {}
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
    if EARLY_MOVE_MIN_PCT <= price_chg_pct <= EARLY_MOVE_MAX_PCT:
        score  += EARLY_MOVE_BONUS
        reasons.append(f"✅ Early price move ({price_chg_pct}%) — not late")
    elif price_chg_pct > EARLY_MOVE_MAX_PCT:
        score  -= 5
        reasons.append(f"⚠️ Move already {price_chg_pct}% underway — later entry, reduced edge")

    # ── 12. Golden / Death Cross regime (1h, 50/200 EMA) ──
    if golden_cross.get("event") == "golden_cross":
        score  += WEIGHT_GOLDEN_CROSS
        reasons.append(f"🌟 Golden Cross just formed on 1h ({golden_cross.get('bars_since_cross')} bars ago) — bullish regime shift")
    elif golden_cross.get("trend") == "bullish":
        score  += WEIGHT_GOLDEN_CROSS * 0.5
        reasons.append("✅ 1h regime bullish (50 EMA > 200 EMA)")
    elif golden_cross.get("event") == "death_cross":
        score  -= GOLDEN_CROSS_PENALTY
        reasons.append("☠️ Death Cross active on 1h — long is fighting the higher-TF trend")
    elif golden_cross.get("trend") == "bearish":
        score  -= GOLDEN_CROSS_PENALTY * 0.5
        reasons.append("⚠️ 1h regime bearish (50 EMA < 200 EMA)")

    # ── 13. Momentum Divergence (RSI + MACD) ──
    if rsi_div.get("bullish") or macd_div.get("bullish"):
        score  += WEIGHT_BULLISH_DIVERGENCE
        detail = rsi_div.get("detail") or macd_div.get("detail") or ""
        reasons.append(f"✅ Bullish divergence — momentum building under price ({detail})")
    if rsi_div.get("bearish") or macd_div.get("bearish"):
        score  -= BEARISH_DIVERGENCE_PENALTY
        detail = rsi_div.get("detail") or macd_div.get("detail") or ""
        reasons.append(f"⚠️ Bearish divergence — momentum fading into the move, classic late-entry warning ({detail})")

    # ── 14. Relative Strength vs BTC ──
    if rel_strength and rel_strength.get("rs_spread") is not None:
        if rel_strength["leading"]:
            score  += WEIGHT_RELATIVE_STRENGTH
            reasons.append(f"✅ Outperforming BTC ({rel_strength['rs_spread']:+.2f}pp over {RS_LOOKBACK} bars) — genuine relative strength")
        else:
            score  -= RS_LAGGARD_PENALTY
            reasons.append(f"⚠️ Underperforming BTC ({rel_strength['rs_spread']:+.2f}pp) — may just be market-wide beta, not a real breakout")

    # ── 15. News catalyst ──
    if coin_news and coin_news.get("positive"):
        score  += WEIGHT_POSITIVE_NEWS
        reasons.append(f"📰 Positive catalyst: {coin_news.get('headline')}")

    score = max(0, min(100, round(score)))
    return score, reasons


# ═══════════════════════════════════════════════════════════════════
# COMPOSITE SCORER — BOTTOM REVERSAL (v4 PRIMARY pipeline)
# ═══════════════════════════════════════════════════════════════════
# Unlike build_score() above (which scores a move that's already underway),
# this scores a coin that has NOT broken out yet: it's basing near a low
# after a real decline, and momentum/volume are starting to diverge from
# price (turning up while price is still flat or making marginal new lows).
# The point is to catch the setup before the volume-spike pipeline's 3.5x
# gate would ever trigger.

def build_reversal_score(
    bottom:        dict,
    rsi_div:       dict,
    macd_div:      dict,
    stoch:         dict,
    accum:         dict,
    cmf:           float,
    adl_chai:      dict,
    obv:           dict,
    bb:            dict,
    will_r:        float,
    vol_ratio:     float,
    golden_cross:  dict = None,
    rel_strength:  dict = None,
    derivatives:   dict = None,
    coin_news:     dict = None,
) -> tuple:
    """
    Returns (score: int [0-100], reasons: list[str])
    """
    from config import (
        WEIGHT_R_BOTTOM_STRUCTURE, WEIGHT_R_HIGHER_LOW, WEIGHT_R_DIVERGENCE,
        WEIGHT_R_ACCUMULATION, WEIGHT_R_CMF, WEIGHT_R_ADL, WEIGHT_R_OBV,
        WEIGHT_R_MOMENTUM_TURN, WEIGHT_R_BB_SQUEEZE, WEIGHT_R_EARLY_VOLUME,
        WEIGHT_R_HTF_AGREEMENT, WEIGHT_R_DERIVATIVES, WEIGHT_POSITIVE_NEWS,
        REVERSAL_MIN_VOL_RATIO,
    )
    golden_cross = golden_cross or {}
    score   = 0
    reasons = []

    # ── 1. Bottom structure — the "reached the bottom" half of the setup ──
    score += WEIGHT_R_BOTTOM_STRUCTURE
    reasons.append(f"🔻 Basing {bottom.get('bars_since_low')} bars past the low "
                    f"({bottom.get('pct_from_low'):+.2f}% off it) after a confirmed decline")
    if bottom.get("higher_low"):
        score += WEIGHT_R_HIGHER_LOW
        reasons.append("📐 Higher low structure — the downtrend structure has already broken")

    # ── 2. Bullish divergence — the core "diverging to move up" trigger ──
    if rsi_div.get("bullish") and macd_div.get("bullish"):
        score += WEIGHT_R_DIVERGENCE
        reasons.append(f"✅ RSI + MACD bullish divergence — momentum turning up under price ({rsi_div.get('detail')})")
    elif rsi_div.get("bullish") or macd_div.get("bullish"):
        score += WEIGHT_R_DIVERGENCE * 0.6
        detail = rsi_div.get("detail") or macd_div.get("detail")
        reasons.append(f"✅ Bullish divergence detected — momentum turning up under price ({detail})")

    # ── 3. Accumulation volume signature (Wyckoff) ──
    if accum.get("accumulating"):
        score += WEIGHT_R_ACCUMULATION
        reasons.append("✅ Volume signature: selling drying up, buying volume expanding (accumulation)")
    elif accum.get("down_shrinking"):
        score += WEIGHT_R_ACCUMULATION * 0.4
        reasons.append("📊 Selling volume drying up into the base")

    # ── 4. CMF ──
    if cmf is not None:
        if cmf > 0.05:
            score += WEIGHT_R_CMF
            reasons.append(f"✅ CMF positive ({cmf}) — money flowing in")
        elif cmf > 0:
            score += WEIGHT_R_CMF * 0.5
            reasons.append(f"📊 CMF turning positive ({cmf})")

    # ── 5. ADL + Chaikin ──
    sig = adl_chai.get("signal", "")
    if sig in ("accumulation", "accumulation_accelerating"):
        score += WEIGHT_R_ADL
        reasons.append(f"✅ ADL+Chaikin: {sig.replace('_', ' ')}")

    # ── 6. OBV ──
    if obv.get("obv_trend") == "rising":
        score += WEIGHT_R_OBV
        reasons.append("✅ OBV rising while price bases — quiet accumulation")

    # ── 7. Momentum turn (StochRSI / Williams %R) ──
    if stoch.get("turning_up"):
        score += WEIGHT_R_MOMENTUM_TURN
        reasons.append(f"🔄 StochRSI turning up from oversold (K={stoch.get('k')})")
    elif stoch.get("zone") == "oversold":
        score += WEIGHT_R_MOMENTUM_TURN * 0.3
        reasons.append(f"🔄 StochRSI oversold (K={stoch.get('k')}) — watch for the turn")

    if will_r is not None and will_r > -80:
        score += 3
        reasons.append(f"↗️ Williams %R leaving oversold ({will_r})")

    # ── 8. BB Squeeze — volatility contraction at the bottom ──
    if bb.get("squeeze_detected"):
        score += WEIGHT_R_BB_SQUEEZE
        reasons.append(f"🔥 BB Squeeze — volatility coiling at the base (bw={bb.get('bandwidth','?')}%)")
    elif bb.get("bandwidth") is not None and bb["bandwidth"] < 4.0:
        score += WEIGHT_R_BB_SQUEEZE * 0.5
        reasons.append(f"⚡ BB bandwidth tight ({bb['bandwidth']}%) — coiling")

    # ── 9. Early volume pickup — sweet spot is MODEST, not a launched breakout ──
    if REVERSAL_MIN_VOL_RATIO <= vol_ratio <= 2.5:
        score += WEIGHT_R_EARLY_VOLUME
        reasons.append(f"📈 Early volume pickup ({vol_ratio}x avg) — first signs of interest, not yet crowded")
    elif 2.5 < vol_ratio <= 4.0:
        score += WEIGHT_R_EARLY_VOLUME * 0.5
        reasons.append(f"📈 Volume picking up ({vol_ratio}x avg)")
    elif vol_ratio > 4.0:
        reasons.append(f"⚠️ Volume already {vol_ratio}x avg — move may already be underway, less of an early entry")

    # ── 10. HTF / regime agreement — not fighting the higher timeframe ──
    if golden_cross.get("event") == "golden_cross":
        score += WEIGHT_R_HTF_AGREEMENT
        reasons.append("🌟 1h Golden Cross just formed — regime already turning")
    elif golden_cross.get("trend") != "bearish":
        score += WEIGHT_R_HTF_AGREEMENT * 0.5
        reasons.append("✅ 1h regime not bearish — reversal isn't fighting the higher timeframe")

    # ── 11. Relative strength vs BTC — basing while BTC is weak is a stronger tell ──
    if rel_strength and rel_strength.get("rs_spread") is not None and rel_strength["leading"]:
        score += 5
        reasons.append(f"✅ Outperforming BTC even while basing ({rel_strength['rs_spread']:+.2f}pp)")

    # ── 12. Derivatives positioning — free futures proxy for on-chain/smart-money flow ──
    if derivatives:
        fr = derivatives.get("funding_rate")
        if fr is not None and fr < 0:
            score += WEIGHT_R_DERIVATIVES
            reasons.append(f"✅ Negative funding rate ({fr*100:.3f}%/8h) — shorts crowded and paying, squeeze fuel")
        elif fr is not None and fr < 0.0002:
            score += WEIGHT_R_DERIVATIVES * 0.4
            reasons.append(f"📊 Funding rate low ({fr*100:.3f}%/8h) — positioning not overheated")
        oi_chg = derivatives.get("oi_change_pct")
        if oi_chg is not None and oi_chg < -5:
            reasons.append(f"📉 Open interest down {abs(oi_chg):.1f}% into the base — weak hands flushed out")

    # ── 13. News catalyst ──
    if coin_news and coin_news.get("positive"):
        score += WEIGHT_POSITIVE_NEWS
        reasons.append(f"📰 Positive catalyst: {coin_news.get('headline')}")

    score = max(0, min(100, round(score)))
    return score, reasons
