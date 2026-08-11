# ⚡ Pre-Breakout Scanner v3

**Advanced crypto pre-breakout detection system — runs fully automated on GitHub's free servers every 15 minutes. No computer, no Colab, no VPS needed.**

---

## What's New in v3 — Institutional-Grade Signals

v2 had a real problem: alerts tended to fire *after* a coin had already pumped and was rolling back over, because the core gate (a volume spike that already happened) and several of the scoring inputs (MACD cross, Donchian breakout) are lagging-by-definition confirmation signals. v3 adds the context a discretionary desk checks before sizing a long, specifically to catch setups earlier and reject setups that are already extended:

| Feature | v2 | v3 |
|---|---|---|
| Golden Cross / Death Cross (1h, 50/200 EMA) | ❌ | ✅ regime filter + score bonus/penalty |
| RSI + MACD divergence detection | ❌ | ✅ bearish divergence penalizes "buying the top" |
| Relative Strength vs BTC | ❌ | ✅ rejects moves that are just BTC-wide beta |
| Fear & Greed Index | ❌ | ✅ raises the bar during euphoric markets |
| Coin-specific negative news (hack/delist/lawsuit) | ❌ | ✅ hard-blocks the alert |
| Market-wide risk-off news | ❌ | ✅ pauses the whole scan cycle |
| Positive news catalyst | ❌ | ✅ small score bonus |
| "Early move" bonus window | 0.3–8% | **0.3–3%** (tightened — 8% is often already most of the move) |
| Donchian breakout weight | 10 pts | **6 pts** (most lagging signal in the suite, downweighted) |

All of it uses **free, keyless APIs** (alternative.me Fear & Greed Index, CryptoCompare public news) — no new secrets or signups required.

## Backtesting & Self-Tuning (the learning loop)

A separate weekly workflow (`backtest.yml`) closes the loop: it replays the **exact same scoring logic** the live scanner uses against real historical KuCoin data, resolves every simulated signal against its own future candles (deterministically, since it's history), and logs the result. Combined with live results (the scanner already tracks whether every real alert's SL/TP1/TP2 got hit), this builds up a growing dataset of "what actually worked."

- **`engine.py`** — the OHLCV-only scoring logic, factored out so live scanning and backtesting call the *identical* code path. No drift between what's backtested and what's live.
- **`backtest.py`** — walks forward through ~30 days of history across the top-volume symbols, bar by bar, recording every candidate and its eventual outcome to `state/trade_log.jsonl`.
- **`tuner.py`** — reads the accumulated trade log and asks, per signal: *does this component actually correlate with wins?* Only trusts a component once there's enough sample size in both the "present" and "absent" groups (default 20+ each) — no tuning off a handful of trades. It also sweeps `SCORE_THRESHOLD` to see if a different bar would have produced a better win rate.

**Nothing self-modifies without review.** The weekly workflow commits the new trade-log data straight to `main` (it's just accumulated data), but any suggested change to `config.py`'s weights or threshold goes out as a **pull request** with the full analysis in the description — a human still signs off before it changes what real alerts look like. Run it manually any time with:

```
python backtest.py      # replay history, append to state/trade_log.jsonl
python tuner.py          # report only, no changes
python tuner.py --apply  # writes suggested changes into config.py (for review before committing)
```

Known limitation: the backtest can't replay the live-only microstructure gates (taker buy/sell ratio, order book imbalance, cross-exchange validation) since those need live data that doesn't exist historically — so it's directionally useful, not a byte-for-byte simulation of what live alerts would have fired.

## What's New in v2

| Feature | v1 | v2 |
|---|---|---|
| Technical indicators | 4 | **11** |
| Timeframes | 15m only | **15m + 1h confirmation** |
| Exchanges | KuCoin only | **KuCoin + Binance cross-validation** |
| BTC market filter | ❌ | ✅ |
| Alert cooldown | ❌ | ✅ 60 min per symbol |
| Stop Loss / Take Profit | ❌ | ✅ ATR-based |
| TradingView chart link | ❌ | ✅ |
| BB Squeeze detection | ❌ | ✅ |
| OBV divergence check | ❌ | ✅ |
| RSI / MACD | ❌ | ✅ |
| Scan log artifacts | ❌ | ✅ 7-day retention |

---

## How It Works

Every 15 minutes GitHub Actions runs `scanner.py`, which:

1. **Loads all active KuCoin USDT spot pairs** with $150k+ daily volume
2. **BTC Context Check** — if BTC is in a bear trend, score threshold is raised by +10 to avoid false signals in a down market
3. **Fear & Greed Check** — if the market is in Extreme Greed (≥80), the score threshold is raised further (euphoric markets are where "pre-breakout" alerts most often turn out to be blow-off tops)
4. **Market-Wide News Check** — if there's an acute market-wide negative headline (exchange collapse, regulatory crackdown, flash crash) in the last 12h, the whole scan cycle is paused — no new longs into a risk-off tape
5. **Coin-Specific News Gate** — any symbol with a recent hack/delisting/lawsuit/fraud headline is hard-blocked before any indicators are even computed
6. **Volume Gate** — only symbols with a volume spike ≥ 3.5× their 20-bar average pass through (fast filter, avoids computing all indicators on every symbol)
7. **Full indicator suite** (only on volume-spike candidates):
   - RSI (14) — checks for healthy zone, not overbought
   - MACD (12/26/9) — bullish cross + histogram momentum
   - Bollinger Band Squeeze — detects the coil → explosion pattern
   - ATR (14) — used for SL/TP sizing
   - OBV — confirms volume is accumulating with price
   - Stochastic RSI — secondary momentum check
   - Chaikin Money Flow (CMF) — institutional money flow
   - Williams %R — overbought/oversold context
   - ADL + Chaikin Oscillator — accumulation vs. distribution
   - Donchian Channel Breakout — price breaking multi-bar high
   - Linear Regression Channel — slope + position (z-score)
   - EMA Trend (20/50) + Swing structure — auto trend direction
   - **RSI + MACD Divergence** — bearish divergence (price up, momentum fading) penalizes the score; this is the main defense against alerting near a local top
   - **Relative Strength vs BTC** — coin's % move over the lookback window compared to BTC's — rejects signals that are just market-wide beta, not real alpha
8. **1-hour Confirmation + Golden/Death Cross** — fetches 1h candles, checks if higher timeframe agrees, and evaluates the 50/200 EMA regime (fresh golden cross = bonus, death-cross regime = penalty)
9. **Composite Score (0–100)** — each indicator contributes weighted points
10. **Binance Cross-Validation** — if the same pair shows a volume spike on Binance too, it's a stronger signal. No Binance listing → signal is kept but score is reduced by 10 pts
11. **Alert Cooldown** — same symbol won't be alerted again for 60 minutes
12. **Telegram Alert** — rich message with score, reasons, SL/TP, institutional context (regime, relative strength, Fear & Greed), TradingView link

### Scoring Weights

| Signal | Max Points |
|---|---|
| Volume Explosion (>3.5× avg) | 25 |
| BB Squeeze → Expansion | 15 |
| RSI in healthy zone (38–68) | 10 |
| MACD Bullish Cross | 10 |
| EMA Trend Bullish | 10 |
| ADL + Chaikin Accumulation | 10 |
| Donchian Channel Breakout | 6 *(intentionally low — this fires after the range already broke)* |
| Linear Regression Channel | 5 |
| OBV Rising | 5 |
| Golden Cross / bullish 1h regime | +8 *(death cross: −10 penalty)* |
| Bullish Divergence (RSI/MACD) | +8 *(bearish divergence: −12 penalty)* |
| Relative Strength vs BTC | +7 *(underperforming BTC: −6 penalty)* |
| Positive news catalyst | +5 |
| 1h HTF Bonus | +5 |
| Early Price Move (0.3–3%) | +5 *(already >3% underway: −5 penalty)* |

Score is clipped to 0–100. **Default alert threshold: 65/100** (raised automatically during BTC bear trends or Extreme Greed).

---

## Setup (5 minutes)

### Step 1 — Create a Telegram Bot

1. Open Telegram → search `@BotFather` → send `/newbot`
2. Follow prompts → you'll get a **Bot Token** like `123456:ABCxyz...`
3. Search `@userinfobot` → send any message → it gives your **Chat ID** (numbers only)
4. Find your new bot by name → send it `/start`

### Step 2 — Add GitHub Secrets

In your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your bot token from Step 1 |
| `TELEGRAM_CHAT_ID` | Your Chat ID from Step 1 |

### Step 3 — Verify the Workflow

1. Go to **Actions** tab in your repo
2. Click **Pre-Breakout Scanner v2**
3. Click **Run workflow** → **Run workflow** (manual trigger)
4. After ~2 minutes check Telegram — you should receive a silent summary message

That's it. The system runs automatically every 15 minutes from now on.

---

## File Structure

```
pre-breakout-scanner/
├── scanner.py          ← Main orchestrator (live, every 15 min)
├── engine.py           ← Shared scoring logic — used by scanner.py AND backtest.py
├── backtest.py         ← Historical replay engine (weekly)
├── tuner.py            ← Reads trade_log.jsonl, suggests weight/threshold changes
├── indicators.py       ← All TA indicators, incl. golden/death cross, divergence, relative strength
├── news.py             ← Fear & Greed + keyless news sentiment (CryptoCompare, alternative.me)
├── config.py           ← All tunable parameters in one place
├── requirements.txt    ← Only 2 dependencies: ccxt + requests
├── state/
│   ├── known_symbols.json   ← Auto-updated each run (tracks symbols + cooldowns)
│   ├── trade_log.jsonl      ← Every resolved trade, live + backtest (the learning data)
│   └── tuning_report.md     ← Latest self-tuning analysis (regenerated weekly)
└── .github/
    └── workflows/
        ├── scan.yml         ← Live scanner, every 15 minutes
        └── backtest.yml     ← Backtest + self-tune, weekly (opens a PR for review)
```

---

## Tuning the Scanner

All parameters are in **`config.py`**. Key ones:

| Parameter | Default | Effect |
|---|---|---|
| `VOLUME_SPIKE_RATIO` | 3.5× | Lower = more signals (noisier), Higher = fewer (cleaner) |
| `SCORE_THRESHOLD` | 65 | Lower = more alerts, Higher = fewer, high-conviction only |
| `MIN_QUOTE_VOLUME_24H` | $150,000 | Increase to focus on larger caps only |
| `ALERT_COOLDOWN_MINUTES` | 60 | Prevent alert spam on same symbol |
| `CROSS_VALIDATE` | True | Set False to skip Binance check (faster) |
| `MAX_ALERTS_PER_RUN` | 10 | Cap to prevent Telegram flood |
| `USE_GOLDEN_CROSS` / `USE_DIVERGENCE_DETECTION` / `USE_RELATIVE_STRENGTH` | True | Set False to disable any individual institutional signal |
| `USE_NEWS_FILTER` / `USE_FEAR_GREED` | True | Set False to disable the news/sentiment layer entirely (no network calls to alternative.me / CryptoCompare) |
| `FEAR_GREED_EXTREME_GREED` | 80 | Lower = threshold gets raised sooner during greedy markets |
| `EARLY_MOVE_MAX_PCT` | 3.0 | Lower = stricter about how "early" a move must still be to get the bonus |

---

## Understanding the Alert

```
⚡ PRE-BREAKOUT ALERT — XYZ/USDT
Score: 82/100  🟢🟢 HIGH

💰 Price:  0.04521
📊 Volume: 5.2x avg  |  Candle: +3.1%
🕐 HTF:    ✅ 1h confirms

📐 Risk Management (ATR=0.000812)
  🔴 Stop Loss:  0.04399
  🟡 Target 1:   0.04683  (R/R 1.5x)
  🟢 Target 2:   0.04805  (R/R 3.5x)

Signals:
  📈 Volume 5.2x average
  🔥 BB Squeeze breakout (bw=1.82%)
  ✅ RSI healthy (54.3)
  ✅ MACD bullish cross
  ✅ Donchian channel breakout (+0.4%)
  ✅ EMA trend bullish
  ✅ ADL+Chaikin: accelerating accumulation
  ✅ 1h trend bullish (HTF confirmation)
  ✅ Early price move (+3.1%) — not late

📈 Open on TradingView
KuCoin • 14:30 UTC
```

---

## Important Notes

- **First run**: No "new listing" alerts sent — all current symbols are recorded as baseline. From the second run onward, new listings are detected.
- **GitHub Actions timing**: Scheduled jobs may be delayed a few minutes during peak hours — this is normal and free.
- **GitHub free tier**: 2,000 minutes/month for private repos. Each scan takes ~3–5 min → this system uses ~600 min/month (~30% of free quota).
- **This system is independent** from any Wyckoff/VSA or other system you run — it does not modify any shared state.
- **News/sentiment sources are free and keyless** (alternative.me, CryptoCompare) — no new GitHub secrets needed. The coin-news and market-wide checks are simple keyword matching, not NLP — treat them as a blunt red/green-flag filter, not a guarantee.
- **A cycle can come back with zero alerts and a "paused" summary ping** — that means market-wide risk-off news was detected and no new longs were evaluated that cycle, by design.

---

## نظرة عامة بالعربية

هذا النظام يرصد الأزواج التي على وشك الاختراق (Pre-Breakout) في منصة KuCoin قبل أن يحدث الاختراق، ويرسل تنبيهاً على Telegram يحتوي على:

- **السكور من 100** مع أسباب مفصّلة
- **11 مؤشراً فنياً** تشمل: انفجار الحجم، RSI، MACD، BB Squeeze، OBV، CMF، ADL+Chaikin، دونشيان، قناة الانحدار الخطي، Williams %R، StochRSI
- **تأكيد على الفريم الساعي (1h)**
- **تأكيد متقاطع مع Binance**
- **فلتر BTC** لتجنب الإشارات الخاطئة في سوق هابط
- **Stop Loss وTarget مبنيان على ATR**
- **رابط TradingView مباشر**

جميع الإعدادات القابلة للتعديل موجودة في `config.py`.
