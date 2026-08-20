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
| News-Catalyst Alerts (news as the *primary* trigger) | ❌ | ✅ separate `📰 NEWS CATALYST` pathway |
| "Early move" bonus window | 0.3–8% | **0.3–3%** (tightened — 8% is often already most of the move) |
| Donchian breakout weight | 10 pts | **6 pts** (most lagging signal in the suite, downweighted) |

All of it uses **free, keyless APIs** (alternative.me Fear & Greed Index, public RSS feeds from CoinDesk/Cointelegraph/Decrypt/CryptoSlate for news) — no new secrets or signups required.

### News-Catalyst Alerts (news as the trigger, not just a filter)

Everything above still requires price/volume to move *first* — news only adjusts the score of a candidate the volume-spike gate already found. That's backwards for genuine news-driven moves: by the time a coin has already spiked 3.5x, the catalyst has often been priced in.

News-Catalyst Alerts are a separate, independent pass: a fresh (within `NEWS_CATALYST_MAX_AGE_HOURS`, default 6h) positive headline — partnership, listing, mainnet launch, upgrade, adoption, ETF approval, institutional inflow, buyback, token burn, airdrop — plus just a **modest** confirming reaction (`NEWS_CATALYST_MIN_VOL_RATIO`, default 1.5x average volume, vs. 3.5x for the main pipeline) is enough to fire on its own. These are tagged `📰 NEWS CATALYST` in Telegram and explicitly marked as a separate, less-confirmed signal type — they skip the full institutional scoring suite, so treat them as an earlier/rawer heads-up, not a high-conviction signal like the main alerts.

### Chart-Reading Signals (researched from real technical-analysis methodology)

Three more scoring components, added after researching what's actually publicly documented and codifiable from well-known chart analysts (Peter Brandt's classical charting, the Wyckoff Method's accumulation schematic, and the standard Fibonacci/support-resistance technique used industry-wide — including by traders like Gareth Soloway). Each is genuinely deterministic — no discretionary "read the chart" judgment, just rules that operate on the same OHLCV candles the rest of the engine already uses:

| Signal | What it checks | Points |
|---|---|---|
| **Swing Support/Resistance** | Clusters recent fractal pivot highs/lows into support/resistance zones; bonus if price is basing near a support zone, penalty if it's sitting right under a resistance zone (a breakout there is more likely to stall) | `WEIGHT_SWING_SUPPORT` (+6) / `SWING_RESISTANCE_PENALTY` (−8) |
| **Fibonacci Golden Pocket** | Finds the most recent swing-low → swing-high leg and checks if price has pulled back into the 61.8–65% retracement zone — the classic "golden pocket" bounce area | `WEIGHT_FIB_GOLDEN_POCKET` (+5) |
| **Wyckoff Spring** | Detects a false breakdown below a recent trading range's support, on below-average volume, that gets reclaimed within a few bars — a shakeout, not real distribution, and unlike most of this engine's signals it's a *leading* indicator that fires before the breakout | `WEIGHT_WYCKOFF_SPRING` (+10) |

**Deliberately excluded** (researched and ruled out, not overlooked): Benjamin Cowen's logarithmic-regression bands and "Risk Metric" — he's never published the exact formula, open-source recreations are acknowledged approximations, and the underlying inputs (years of price history, on-chain data, Google Trends) don't exist for a 15-minute altcoin scanner anyway. Same for any analyst's proprietary named tactics that were never publicly specified with an actual rule (marketing terms, not methodology) — those aren't something code can honestly implement, so they were left out rather than guessed at.

Toggle each independently with `USE_SWING_LEVELS` / `USE_FIB_CONFLUENCE` / `USE_WYCKOFF_SPRING` in `config.py`. Like every other component, the self-tuner (below) automatically tracks whether each one actually correlates with wins once enough live/backtest trades accumulate.

## Backtesting & Self-Tuning (the learning loop)

A separate weekly workflow (`backtest.yml`) closes the loop: it replays the **exact same scoring logic** the live scanner uses against real historical Binance data, resolves every simulated signal against its own future candles (deterministically, since it's history), and logs the result. Combined with live results (the scanner already tracks whether every real alert's SL/TP1/TP2 got hit), this builds up a growing dataset of "what actually worked."

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

1. **Loads all active Binance USDT spot pairs** with $150k+ daily volume
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
10. **Alert Cooldown** — same symbol won't be alerted again for 60 minutes
11. **Telegram Alert** — rich message with score, reasons, SL/TP, institutional context (regime, relative strength, Fear & Greed), TradingView link
12. **Auto-Trade (optional, off by default)** — if `AUTO_TRADING_ENABLED` is on, places a real Binance order sized by risk %, see [Live Auto-Trading](#live-auto-trading-real-money) below

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

That's it. The system runs automatically every 15 minutes from now on, sending Telegram alerts only — no funds are ever touched. To let it place real trades, see [Live Auto-Trading](#live-auto-trading-real-money) below (separate opt-in, off by default).

---

## File Structure

```
pre-breakout-scanner/
├── scanner.py          ← Main orchestrator (live, every 15 min)
├── engine.py           ← Shared scoring logic — used by scanner.py AND backtest.py
├── backtest.py         ← Historical replay engine (weekly)
├── tuner.py            ← Reads trade_log.jsonl, suggests weight/threshold changes
├── indicators.py       ← All TA indicators, incl. golden/death cross, divergence, relative strength
├── news.py             ← Fear & Greed + keyless news sentiment (RSS feeds, alternative.me)
├── trader.py           ← Live auto-trading: position sizing, order execution, daily loss circuit breaker (off by default)
├── config.py           ← All tunable parameters in one place
├── requirements.txt    ← Only 2 dependencies: ccxt + requests
├── state/
│   ├── known_symbols.json   ← Auto-updated each run (tracks symbols + cooldowns)
│   ├── trade_log.jsonl      ← Every resolved trade, live + backtest (the learning data)
│   ├── trading_state.json   ← Auto-trading only: open positions, daily PnL, halt flag
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
| `MAX_ALERTS_PER_RUN` | 10 | Cap to prevent Telegram flood |
| `USE_GOLDEN_CROSS` / `USE_DIVERGENCE_DETECTION` / `USE_RELATIVE_STRENGTH` | True | Set False to disable any individual institutional signal |
| `USE_NEWS_FILTER` / `USE_FEAR_GREED` | True | Set False to disable the news/sentiment layer entirely (no network calls to alternative.me / news RSS feeds) |
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
Binance • 14:30 UTC
```

---

## Live Auto-Trading (real money)

**Off by default.** With `AUTO_TRADING_ENABLED` unset (or `false`), nothing in this section runs — the scanner only ever sends Telegram alerts, exactly as before. Turning this on lets the scanner place real Binance orders with real money on every qualifying signal, with no human in the loop per trade. Read this whole section before enabling it.

### How it works

- **Venue**: Binance only (spot). Trading and market data both come from Binance — no cross-exchange slippage between what the scanner saw and what got filled.
- **Position sizing**: risk-based, not a fixed coin amount. Quantity is sized so that if the Stop Loss is hit, the loss equals a `risk_pct` of current account equity. `risk_pct` scales linearly with the signal's score — a 65-score signal risks `MIN_TRADE_RISK_PCT` (default 1%), a 100-score signal risks `MAX_TRADE_RISK_PCT` (default 2%). A `MAX_POSITION_NOTIONAL_PCT` cap (default 20%) additionally protects against an unusually tight stop sizing an oversized position.
- **Daily loss circuit breaker**: `MAX_DAILY_LOSS_PCT` (default 5%). Once realized losses for the current UTC day reach this % of the day's starting equity, auto-trading **halts completely** — no new entries — until a human clears it. It does **not** reset automatically at midnight.
- **Order management**: on entry, a market buy is placed, followed by a `STOP_LOSS_LIMIT` sell (protective stop) and a `LIMIT` sell (take-profit target). These are two independent orders, not a native Binance OCO — every scan cycle (~15 min) `trader.reconcile_positions()` checks both, cancels whichever didn't fill once the other does, and logs the realized PnL against the daily loss cap. **This means protective orders are only reconciled every ~15 minutes, not continuously — this is a batch system, not a real-time desk.**
- **Concurrency cap**: `MAX_CONCURRENT_POSITIONS` (default 5) — no new entries once that many auto-trades are open.
- If the stop order fails to place right after a buy fills, the position is closed immediately at market rather than left unprotected, and you're notified on Telegram.

### Setup

1. On Binance, create a **dedicated sub-account** for this bot (isolates its funds/trades from your main account) and fund it with only what you're willing to have this system trade.
2. Create an API key on that sub-account with **Enable Spot & Margin Trading only — leave "Enable Withdrawals" OFF.** This is the single most important safety step: even a fully compromised key can't move funds out, only trade with what's already there.
3. In the repo → **Settings → Secrets and variables → Actions**:
   - **Secrets** tab: add `BINANCE_API_KEY` and `BINANCE_API_SECRET`.
   - **Variables** tab: add `AUTO_TRADING_ENABLED` = `true`, and `BINANCE_TESTNET` = `true` initially.
4. Run the workflow manually a few times with `BINANCE_TESTNET=true` and watch the Telegram messages ("AUTO-TRADE OPENED", TP/SL results) to confirm sizing and behavior look right against Binance's testnet (fake funds, real-ish order book).
5. Only once you're satisfied, change the `BINANCE_TESTNET` **variable** to `false`. From that point every trade uses real funds.

### Kill switch

Set the `AUTO_TRADING_ENABLED` repo **variable** to `false` — takes effect on the next scheduled run (within 15 min), no code change or redeploy needed. This stops new entries; it does **not** cancel already-open protective orders (those stay live on Binance until they fill or you cancel them manually).

If the daily loss cap trips, the scanner halts itself automatically and pings Telegram. To resume after reviewing what happened:

```
python trader.py            # view current state (open positions, halt reason, daily PnL)
python trader.py --resume   # clear the halt flag
```

### What this does NOT do

- No leverage, no margin, no futures/derivatives — spot only.
- No partial take-profit — the automated exit targets TP1 only (the alert's TP2 is informational).
- No protection against Binance API outages, network failures between GitHub Actions runs, or the ~15-minute reconciliation gap mid-cycle — this is documented risk, not solved risk.

---

## Important Notes

- **First run**: No "new listing" alerts sent — all current symbols are recorded as baseline. From the second run onward, new listings are detected.
- **GitHub Actions timing**: Scheduled jobs may be delayed a few minutes during peak hours — this is normal and free.
- **GitHub free tier**: 2,000 minutes/month for private repos. Each scan takes ~3–5 min → this system uses ~600 min/month (~30% of free quota).
- **This system is independent** from any Wyckoff/VSA or other system you run — it does not modify any shared state.
- **News/sentiment sources are free and keyless** (alternative.me, public RSS feeds) — no new GitHub secrets needed. News originally ran on CryptoCompare's API but that now requires a registered key (HTTP 401 as of 2026-08), so it switched to RSS. The coin-news and market-wide checks are simple keyword matching, not NLP — treat them as a blunt red/green-flag filter, not a guarantee.
- **A cycle can come back with zero alerts and a "paused" summary ping** — that means market-wide risk-off news was detected and no new longs were evaluated that cycle, by design.

---

## نظرة عامة بالعربية

هذا النظام يرصد الأزواج التي على وشك الاختراق (Pre-Breakout) في منصة Binance قبل أن يحدث الاختراق، ويرسل تنبيهاً على Telegram يحتوي على:

- **السكور من 100** مع أسباب مفصّلة
- **11 مؤشراً فنياً** تشمل: انفجار الحجم، RSI، MACD، BB Squeeze، OBV، CMF، ADL+Chaikin، دونشيان، قناة الانحدار الخطي، Williams %R، StochRSI
- **تأكيد على الفريم الساعي (1h)**
- **فلتر BTC** لتجنب الإشارات الخاطئة في سوق هابط
- **Stop Loss وTarget مبنيان على ATR**
- **رابط TradingView مباشر**
- **تنفيذ تلقائي اختياري (مطفأ افتراضياً)** — راجع قسم [Live Auto-Trading](#live-auto-trading-real-money) قبل تفعيله؛ فيه سقف خسارة يومي 5%، وحد أقصى 1-2% من الرصيد لكل صفقة، ومفتاح إيقاف فوري (kill switch)

### إشارات قراءة الشارت (بعد بحث حقيقي، مش تخمين)

بناءً على طلب بحث عن استراتيجيات المحللين الكبار المعروفين بقراءة الشارت (زي Benjamin Cowen و Gareth Soloway)، تم البحث فعلياً وطلوع 3 إشارات جديدة قابلة للبرمجة فعلياً (يعني قاعدة رياضية واضحة، مش مجرد "إحساس" بالسوق):

- **مناطق الدعم والمقاومة (Swing Support/Resistance)** — بيلقط القمم والقيعان السابقة القريبة من السعر الحالي، ويدي بونص لو العملة قاعدة (basing) فوق دعم قوي، وخصم لو قاعدة تحت مقاومة (يبقى الاختراق ممكن يترفض هناك)
- **منطقة فيبوناتشي الذهبية (Fibonacci Golden Pocket)** — بيحسب آخر موجة صعود، ويشوف لو السعر رجع لمنطقة الـ 61.8%-65% ارتداد، وهي منطقة الارتداد الكلاسيكية اللي بيراقبها أغلب المحللين الفنيين
- **Wyckoff Spring** — بيكشف كسر وهمي تحت الدعم بحجم تداول ضعيف يترد بسرعة (يعني تنضيف للأيدي الضعيفة مش بيع حقيقي) — دي إشارة **مبكرة** (قبل الاختراق)، عكس أغلب إشارات النظام التانية اللي بتتأكد بعد ما الحركة تبدأ

**اتم استبعاده عمداً** بعد البحث: طريقة Benjamin Cowen في الـ logarithmic regression و"Risk Metric" — هو نفسه ما نشرش المعادلة الدقيقة أبداً، والنسخ المتاحة كلها تقريبية بالاعتراف من أصحابها، وكمان محتاجة بيانات سنين طويلة وبيانات on-chain مش متاحة لسكانر بيشتغل كل 15 دقيقة على عملات صغيرة. وبرضو أي أسلوب "سري" لمحلل تاني اتسوّق باسمه بس مفيش قاعدة واضحة منشورة له — تم استبعاده لأن مفيش طريقة أبرمجه صح من غير ما أخمّن.
