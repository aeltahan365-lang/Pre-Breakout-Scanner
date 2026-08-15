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
USE_CRYPTOCOM_VALIDATION = True    # also cross-check buy ratio on Crypto.com when the pair is listed there (bonus confirmation, never a hard block — most KuCoin small-caps aren't listed on Crypto.com)

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

# ── Bottom Reversal Detector (v4 — PRIMARY pipeline) ─────────────────
# The v3 pipeline above requires a volume spike that has ALREADY happened —
# by definition that's a lagging, post-the-fact confirmation. Most real
# moves start from a coin finding a bottom (a base after a decline) and
# showing bullish divergence (price stops making new lows while momentum
# / volume start turning up) — that's visible BEFORE the big volume candle
# prints. This block detects that setup on its own; the v3 volume-spike
# pipeline below is kept as a SECONDARY "confirmed breakout" pathway for
# moves that are already launched, not the primary trigger anymore.
REVERSAL_STRUCTURE_TIMEFRAME = TIMEFRAME_CONFIRM   # "1h" — a real bottom is a multi-day structural
                                                    # event, not something visible on a single 15m bar
REVERSAL_LOOKBACK_BARS   = 80     # ~3.3 days of 1h bars — window scanned for the base / lowest low
REVERSAL_MIN_BASE_BARS   = 3      # bars since the exact low before we'll call it "basing" — avoids
                                   # calling bottom on the falling knife itself, mid-crash
REVERSAL_PROXIMITY_PCT   = 8.0    # price must be within this % of the lookback low to count as "near the bottom"
REVERSAL_PRIOR_DECLINE_PCT = 8.0  # min decline into the low (local high -> low, within the lookback
                                   # window) required to confirm this followed a real downtrend, not chop
REVERSAL_MIN_VOL_RATIO   = 1.2    # only need a MODEST volume pickup to trigger (vs 3.5x for the
                                   # breakout pipeline) — catching it early means volume hasn't
                                   # exploded yet, just started picking up off the base
REVERSAL_ACCUM_LOOKBACK  = 24     # 15m bars scanned for the Wyckoff volume dry-up/expansion signature

WEIGHT_R_BOTTOM_STRUCTURE = 20   # price is basing near the lookback low after a confirmed decline
WEIGHT_R_HIGHER_LOW       = 10   # latest swing low sits above the prior one — structure already turning
WEIGHT_R_DIVERGENCE       = 25   # RSI/MACD bullish divergence — the core "diverging to move up" trigger
WEIGHT_R_ACCUMULATION     = 15   # Wyckoff volume signature: selling drying up, buying expanding
WEIGHT_R_CMF              = 8    # Chaikin Money Flow turning/staying positive
WEIGHT_R_ADL              = 8    # ADL+Chaikin accumulation signal
WEIGHT_R_OBV              = 7    # OBV rising while price is still basing (quiet accumulation)
WEIGHT_R_MOMENTUM_TURN    = 10   # StochRSI turning up out of oversold
WEIGHT_R_BB_SQUEEZE       = 8    # volatility contracting at the base (coiling before the move)
WEIGHT_R_EARLY_VOLUME     = 7    # modest volume pickup (sweet spot), not a fully launched breakout
WEIGHT_R_HTF_AGREEMENT    = 5    # 1h regime isn't fighting the reversal (or a fresh golden cross)
WEIGHT_R_DERIVATIVES      = 10   # free futures proxy for on-chain/smart-money positioning (see below)

REVERSAL_SCORE_THRESHOLD    = 60   # minimum score to send a reversal alert (0-100)
REVERSAL_MAX_ALERTS_PER_RUN = 10

# ── Derivatives Positioning (free keyless proxy for on-chain / "smart
#    money" flow) ──────────────────────────────────────────────────────
# True per-altcoin on-chain data (exchange netflows, whale wallets, active
# addresses) needs a paid provider (Glassnode/CryptoQuant/Nansen/Santiment)
# — none of those keys exist in this repo. Perpetual futures funding rate
# and open interest are the free, keyless stand-in: negative funding means
# shorts are paying longs (crowded, over-leveraged shorts = squeeze fuel
# right at a base), which is the same crowd-positioning signal on-chain
# exchange-flow data is trying to capture, just read through the
# derivatives market instead of the blockchain. Live-only (like taker
# buy/sell ratio) — can't be replayed cheaply against history, so it's a
# bonus in the live scanner only, never a hard gate.
USE_DERIVATIVES_CONTEXT   = True
DERIVATIVES_EXCHANGE      = "binanceusdm"   # ccxt USDT-M perpetuals — public endpoints, no API key needed

# ── Scoring Thresholds ───────────────────────────────────────────
SCORE_THRESHOLD         = 65    # minimum score to send alert (0-100) — SECONDARY "confirmed breakout" pipeline
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
