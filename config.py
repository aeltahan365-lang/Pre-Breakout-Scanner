"""
Pre-Breakout Scanner — Centralized Configuration
=================================================
Edit values here to tune sensitivity, scoring, and behavior.
No other file needs to be touched for parameter changes.
"""

# ── Exchanges ──────────────────────────────────────────────────────
# Primary exchange is always KuCoin. Binance is used for cross-validation.
# Set CROSS_VALIDATE = False to skip Binance (faster but less precise).
PRIMARY_EXCHANGE   = "kucoin"
SECONDARY_EXCHANGE = "binance"
CROSS_VALIDATE     = True          # require signal on ≥1 more exchange
QUOTE              = "USDT"

# ── Timeframes ────────────────────────────────────────────────────
TIMEFRAME_PRIMARY  = "15m"         # scanning timeframe
TIMEFRAME_CONFIRM  = "1h"          # higher-TF confirmation
CANDLES_PRIMARY    = 100           # candles fetched on 15m
CANDLES_CONFIRM    = 60            # candles fetched on 1h

# ── Volume ────────────────────────────────────────────────────────
VOLUME_LOOKBACK       = 20         # bars to average for baseline
VOLUME_SPIKE_RATIO    = 3.5        # current / avg must exceed this
MIN_QUOTE_VOLUME_24H  = 150_000    # $USD — skip low-liquidity pairs
RATE_LIMIT_SLEEP      = 0.15       # seconds between API calls

# ── Indicator Periods ────────────────────────────────────────────
RSI_PERIOD         = 14
MACD_FAST          = 12
MACD_SLOW          = 26
MACD_SIGNAL        = 9
BB_PERIOD          = 20
BB_STD             = 2.0
BB_SQUEEZE_PERIOD  = 5             # look back N bars to detect squeeze exit
ATR_PERIOD         = 14
OBV_EMA_PERIOD     = 20            # EMA on OBV for trend
STOCH_RSI_PERIOD   = 14
CMF_PERIOD         = 20
WILLIAMS_PERIOD    = 14
DONCHIAN_PERIOD    = 20
REGRESSION_PERIOD  = 30
TREND_FAST_EMA     = 20
TREND_SLOW_EMA     = 50
ADL_EMA_FAST       = 3
ADL_EMA_SLOW       = 10

# ── Scoring Weights (must sum to 100) ────────────────────────────
# Each section contributes max N points to the composite score.
WEIGHT_VOLUME_EXPLOSION  = 25   # core trigger
WEIGHT_BB_SQUEEZE        = 15   # pre-breakout coil
WEIGHT_RSI               = 10   # healthy zone (40-65)
WEIGHT_MACD              = 10   # bullish cross
WEIGHT_DONCHIAN          = 10   # channel breakout
WEIGHT_TREND_EMA         = 10   # EMA alignment
WEIGHT_ADL_CHAIKIN       = 10   # accumulation/distribution
WEIGHT_LIN_REGRESSION    = 5    # slope + position
WEIGHT_OBV               = 5    # OBV rising with price

# ── Scoring Thresholds ───────────────────────────────────────────
SCORE_THRESHOLD         = 65    # minimum score to send alert (0-100)
HTF_CONFIRM_BONUS       =  5    # added if 1h also looks bullish
EARLY_MOVE_BONUS        =  5    # added if price change 0.5%-8%

# ── Alert Behavior ───────────────────────────────────────────────
ALERT_COOLDOWN_MINUTES  = 60    # re-alert same symbol only after this
MAX_ALERTS_PER_RUN      = 10    # cap to avoid Telegram flood
STATE_FILE              = "state/known_symbols.json"

# ── Telegram ─────────────────────────────────────────────────────
import os
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── TradingView base URL ──────────────────────────────────────────
# Used to generate clickable chart links in alerts.
TV_BASE = "https://www.tradingview.com/chart/?symbol={exchange}:{base}USDT"
