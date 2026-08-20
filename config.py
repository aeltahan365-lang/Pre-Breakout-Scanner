"""
Pre-Breakout Scanner — Centralized Configuration
=================================================
Edit values here to tune sensitivity, scoring, and behavior.
No other file needs to be touched for parameter changes.
"""

# ── Exchanges ──────────────────────────────────────────────────────
# Binance is the sole exchange for both scanning and live execution — data
# and order routing come from the same venue, so there's no cross-exchange
# slippage between "what the scanner saw" and "what got filled."
PRIMARY_EXCHANGE   = "binance"
QUOTE              = "USDT"

# ── Timeframes ────────────────────────────────────────────────────
TIMEFRAME_PRIMARY  = "15m"         # scanning timeframe
TIMEFRAME_CONFIRM  = "1h"          # higher-TF confirmation
CANDLES_PRIMARY    = 100           # candles fetched on 15m
CANDLES_CONFIRM    = 220           # candles fetched on 1h (needs 200+ for the 50/200 golden/death cross)

# ── Volume ────────────────────────────────────────────────────────
VOLUME_LOOKBACK       = 20         # bars to average for baseline
VOLUME_SPIKE_RATIO    = 3.5        # current / avg must exceed this
MIN_QUOTE_VOLUME_24H  = 150_000    # $USD — skip low-liquidity pairs
RATE_LIMIT_SLEEP      = 0.15       # seconds between API calls

# ── Volume Direction (separates real buying volume from selling/
#    distribution volume — a high-volume candle that closes near its
#    low, or where most trades were sell-side, is NOT a breakout) ──
MIN_CLV                  = 0.55    # close must sit in upper 55% of candle range
MIN_TAKER_BUY_RATIO      = 0.55    # ≥55% of recent traded volume must be buyer-initiated
USE_CRYPTOCOM_VALIDATION = True    # also cross-check buy ratio on Crypto.com when the pair is listed there (bonus confirmation, never a hard block — most Binance small-caps aren't listed on Crypto.com)

# ── Order Book Imbalance (reject breakouts facing a sell wall) ───
ORDER_BOOK_DEPTH_PCT      = 0.02   # measure depth within ±2% of best bid/ask
MIN_ORDER_BOOK_BID_RATIO  = 0.40   # below this, sellers dominate near price — likely rejection

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

# ── Scoring Weights ───────────────────────────────────────────────
# Each section contributes up to N points; score is clipped to 0-100 at the
# end, so the "budget" below intentionally exceeds 100 (a genuinely
# high-conviction setup — vol + squeeze + trend + institutional confluence —
# should be able to hit 100 without every single sub-signal maxing out).
WEIGHT_VOLUME_EXPLOSION  = 25   # core trigger
WEIGHT_BB_SQUEEZE        = 15   # pre-breakout coil (leading — the whole point of "pre" breakout)
WEIGHT_RSI               = 10   # healthy zone (38-68, see build_score)
WEIGHT_MACD              = 10   # bullish cross
WEIGHT_DONCHIAN          = 6    # channel breakout — intentionally lower: by definition this fires
                                 # AFTER price already broke the range, so it's the most lagging
                                 # signal in the suite. Kept as confirmation, not a primary driver.
WEIGHT_TREND_EMA         = 10   # EMA alignment
WEIGHT_ADL_CHAIKIN       = 10   # accumulation/distribution
WEIGHT_LIN_REGRESSION    = 5    # slope + position
WEIGHT_OBV               = 5    # OBV rising with price

# ── Institutional-Grade Signals ───────────────────────────────────
# The kind of confluence a discretionary desk checks before sizing a long:
# higher-TF trend regime, momentum divergence, and performance vs the market
# beta (BTC) — not just "did volume and price move on this one candle."
USE_GOLDEN_CROSS            = True
MA_FAST_PERIOD               = 50
MA_SLOW_PERIOD               = 200
WEIGHT_GOLDEN_CROSS          = 8     # 1h 50/200 EMA golden cross just formed, or already in a bullish regime
GOLDEN_CROSS_PENALTY         = 10    # 1h is in a death-cross regime — you'd be longing against the higher-TF trend

USE_DIVERGENCE_DETECTION     = True
DIVERGENCE_LOOKBACK          = 40    # bars (15m) scanned for swing highs/lows
WEIGHT_BULLISH_DIVERGENCE    = 8     # price low fading while RSI/MACD momentum rises — real accumulation
BEARISH_DIVERGENCE_PENALTY   = 12    # price still rising but momentum fading — the classic "buying the top" trap

USE_RELATIVE_STRENGTH        = True
RS_LOOKBACK                  = 20    # bars (15m) compared against BTC over the same window
WEIGHT_RELATIVE_STRENGTH     = 7     # coin is genuinely outperforming BTC, not just riding a market-wide move
RS_LAGGARD_PENALTY           = 6     # coin is UNDERPERFORMING BTC despite the volume spike — likely just beta, not alpha

# ── Chart-Reading Signals (researched from Peter Brandt's classical
#    charting, the Wyckoff Method, and standard Fibonacci/support-
#    resistance technique used industry-wide, incl. by Gareth Soloway) ──
# Deliberately excludes anything that isn't a documented, codifiable rule:
# no Benjamin Cowen-style log-regression/"Risk Metric" (needs years of
# price history + on-chain/sentiment data — wrong fit for fast-rotating
# 15m altcoins) and no proprietary named tactics that were never publicly
# specified with an actual formula. See PR description / commit message
# for the full research writeup and source links.
USE_SWING_LEVELS              = True
SWING_LOOKBACK                = 80    # bars (15m) scanned for fractal pivots
SWING_PIVOT_WINDOW            = 3     # a bar is a pivot if it's the high/low of this many bars on each side
SWING_CLUSTER_PCT             = 0.5   # merge pivots within this % of each other into one level
SWING_PROXIMITY_PCT           = 1.5   # price counts as "at" a level within this %
WEIGHT_SWING_SUPPORT          = 6     # basing near a known swing-support cluster
SWING_RESISTANCE_PENALTY      = 8     # sitting right under a known swing-resistance cluster — breakout likely to stall

USE_FIB_CONFLUENCE            = True
FIB_LOOKBACK                  = 60    # bars (15m) scanned for the most recent swing leg
WEIGHT_FIB_GOLDEN_POCKET      = 5     # price sitting in the 61.8-65% retracement zone of that leg

USE_WYCKOFF_SPRING            = True
WYCKOFF_RANGE_LOOKBACK        = 20    # bars forming the "trading range" a spring dips below
WYCKOFF_RECENT_BARS           = 5     # spring must have occurred within this many of the most recent bars
WEIGHT_WYCKOFF_SPRING         = 10    # false breakdown + reclaim on low volume — a leading shakeout signal

# ── Market Sentiment / News (free, keyless sources) ───────────────
USE_FEAR_GREED               = True
FEAR_GREED_EXTREME_GREED     = 80    # alternative.me Fear & Greed Index — euphoria zone
FEAR_GREED_THRESHOLD_BUMP    = 8     # raise the score bar during euphoria — don't chase blow-off tops

USE_NEWS_FILTER              = True
NEWS_LOOKBACK_HOURS          = 24    # coin-specific negative catalyst window (hard block)
NEWS_MARKET_LOOKBACK_HOURS   = 12    # market-wide negative catalyst window (pauses the whole cycle)
WEIGHT_POSITIVE_NEWS         = 5     # coin has a recent positive catalyst headline

# ── News-Catalyst Alerts ──────────────────────────────────────────
# A SEPARATE, lighter-weight pathway from the main volume-spike pipeline
# above. The main pipeline requires price/volume to have ALREADY moved
# before news even factors in (news is just a bonus/veto there). This path
# makes news the PRIMARY trigger: a fresh positive headline plus only a
# modest confirming price/volume reaction is enough to alert — the whole
# point is to catch a coin because of the catalyst, not after the crowd
# has already piled in and the 3.5x volume gate finally trips.
USE_NEWS_CATALYST_ALERTS       = True
NEWS_CATALYST_MAX_AGE_HOURS    = 6     # only act on genuinely fresh headlines
NEWS_CATALYST_MIN_VOL_RATIO    = 1.5   # much lower bar than VOLUME_SPIKE_RATIO (3.5) — news is the trigger, not volume
MAX_NEWS_CATALYST_ALERTS_PER_RUN = 5

# ── Scoring Thresholds ───────────────────────────────────────────
SCORE_THRESHOLD         = 65    # minimum score to send alert (0-100)
HTF_CONFIRM_BONUS       =  5    # added if 1h also looks bullish
EARLY_MOVE_BONUS        =  5    # added if price change is still early (see EARLY_MOVE_MIN/MAX_PCT)
EARLY_MOVE_MIN_PCT      = 0.3
EARLY_MOVE_MAX_PCT      = 3.0   # tightened from 8.0 — past ~3% on a single 15m candle the move is
                                 # usually already well underway, which is exactly how "pre-breakout"
                                 # alerts end up firing near the top instead of before it.

# ── Alert Behavior ───────────────────────────────────────────────
ALERT_COOLDOWN_MINUTES  = 60    # re-alert same symbol only after this
MAX_ALERTS_PER_RUN      = 10    # cap to avoid Telegram flood
STATE_FILE              = "state/known_symbols.json"
TRADE_LOG_FILE          = "state/trade_log.jsonl"   # every resolved trade (live + backtest), for the tuner

# ── Backtesting ────────────────────────────────────────────────────
BACKTEST_DAYS           = 30    # how far back to replay
BACKTEST_MAX_SYMBOLS    = 25    # top-N by 24h quote volume — bounds API calls/runtime
BACKTEST_MIN_QUOTE_VOL  = MIN_QUOTE_VOLUME_24H
BACKTEST_STEP_BARS      = 1     # evaluate every Nth 15m bar (1 = every bar, slower but thorough)
BACKTEST_SCORE_FLOOR    = 40    # record candidates down to this score (below it isn't interesting even for threshold-sweeping)
BACKTEST_MAX_HOLD_BARS  = 192   # 48h at 15m bars (matches scanner.OUTCOME_EXPIRY_HOURS)

# ── Self-Tuning ──────────────────────────────────────────────────
TUNER_MIN_SAMPLE_SIZE   = 20    # minimum trades WITH and WITHOUT a component before trusting its win-rate delta
TUNER_MAX_WEIGHT_NUDGE  = 0.20  # cap a single tuning pass to a +/-20% change per weight
TUNER_THRESHOLD_SWEEP   = [50, 55, 60, 65, 70, 75, 80, 85]

# ── Telegram ─────────────────────────────────────────────────────
import os
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── TradingView base URL ──────────────────────────────────────────
# Used to generate clickable chart links in alerts.
TV_BASE = "https://www.tradingview.com/chart/?symbol={exchange}:{base}USDT"

# ── Live Auto-Trading (real money — read this whole section) ──────
# OFF by default. This flag is the master kill switch: with it False (or
# unset) the scanner only ever alerts on Telegram, exactly like before —
# no order is ever placed. Flip it to "true" as a GitHub Actions repo
# *variable* (Settings → Secrets and variables → Actions → Variables tab,
# NOT a secret) so it can be toggled instantly without a code push/redeploy.
AUTO_TRADING_ENABLED = os.environ.get("AUTO_TRADING_ENABLED", "false").strip().lower() == "true"

# Binance API credentials — must be a Trade-only key (NO withdrawal
# permission) on a dedicated sub-account, never the main account key.
# Set as GitHub Actions *secrets*, never committed to the repo.
BINANCE_API_KEY    = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

# Binance's spot testnet (testnet.binance.vision) — paper-trades against a
# simulated order book with fake funds. Defaults to True so a first-time
# setup can't accidentally fire real orders; the user must deliberately set
# BINANCE_TESTNET=false (as a repo variable) once they've watched it behave
# correctly on testnet and are ready to risk real funds.
BINANCE_TESTNET = os.environ.get("BINANCE_TESTNET", "true").strip().lower() == "true"

# ── Position sizing — risk-based, scaled by signal confidence ─────
# Quantity is sized so that if the Stop Loss is hit, the realized loss
# equals `risk_pct` of account equity — never a fixed coin quantity.
# risk_pct itself scales linearly with score: SCORE_THRESHOLD -> MIN,
# 100 -> MAX. A 65-score signal risks the least; a 100-score signal risks
# the most (still capped at MAX_TRADE_RISK_PCT).
MIN_TRADE_RISK_PCT     = 1.0    # % of equity risked at the alert threshold score
MAX_TRADE_RISK_PCT     = 2.0    # % of equity risked at a perfect (100) score
MAX_POSITION_NOTIONAL_PCT = 20.0  # hard cap on position value regardless of stop distance
                                    # (protects against a too-tight SL sizing an oversized position)
MAX_CONCURRENT_POSITIONS = 5    # refuse new entries once this many auto-trades are open

# ── Daily loss circuit breaker ─────────────────────────────────────
# Realized PnL (SL/TP fills only, not unrealized) is tracked per UTC day.
# Once losses reach this % of the day's starting equity, AUTO_TRADING
# halts completely — no new entries — until a human clears the halt flag
# in state/trading_state.json (or re-runs `python trader.py --resume`
# after reviewing what happened). It does NOT reset automatically at
# midnight; a halt always requires a human look.
MAX_DAILY_LOSS_PCT = 5.0

TRADING_STATE_FILE = "state/trading_state.json"   # open positions, daily PnL, halt flag
