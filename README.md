# ⚡ Pre-Breakout Scanner v4

**Advanced crypto pre-breakout detection system — runs fully automated on GitHub's free servers every 15 minutes. No computer, no Colab, no VPS needed.**

---

## What's New in v4 — Bottom Reversal Detector (the pipeline is now PRIMARY, not the volume spike)

v3's core gate was a volume spike that had **already happened** (≥3.5x average) — by definition a lagging, after-the-fact confirmation signal. That's exactly why a coin can be up all day with nothing but silence from the scanner: real moves usually start from a coin finding a bottom (a base after a decline) and showing bullish divergence — momentum and volume quietly turning up while price is still flat or making marginal new lows — well *before* any single candle prints a 3.5x volume spike. By the time that spike shows up, a meaningful chunk of the move is often already gone.

v4 adds a second, independent detection pipeline that answers the actual question a discretionary trader asks first: **has this coin reached the bottom, and is it diverging to move up?**

| | 🔄 Bottom Reversal (v4, PRIMARY) | 🚀 Confirmed Breakout (v2/v3, SECONDARY) |
|---|---|---|
| Trigger | Price basing near a confirmed decline's low + bullish divergence | Volume already spiked ≥3.5x with indicator confluence |
| Timing | Early — before the big move | Late — move is already underway |
| Volume required | Modest pickup (≥1.2x) | Large spike (≥3.5x) |
| Conviction | Lower (earlier-stage) | Higher (already confirmed) |
| Structure check | 1h swing-low/higher-low + prior-decline confirmation | — |
| Momentum check | RSI/MACD bullish divergence, StochRSI turning up | RSI zone, MACD cross |
| Volume signature | Wyckoff-style down-volume dry-up / up-volume expansion | Single-candle volume ratio |
| Smart-money proxy | Futures funding rate / open interest (see below) | — |
| Telegram tag | `🔄 BOTTOM REVERSAL` | `🚀 CONFIRMED BREAKOUT` |

Both pipelines run on every scanned symbol every cycle (candles are fetched once and shared), so a coin can legitimately alert twice at different points in its move: once as a 🔄 reversal near the bottom, and again later as a 🚀 confirmed breakout once it actually launches. Cooldowns are tracked independently per pipeline so the second alert isn't suppressed by the first.

### On-chain / smart-money positioning — the free, keyless version

True per-altcoin on-chain data (exchange netflows, whale wallets, active addresses) needs a paid provider (Glassnode/CryptoQuant/Nansen/Santiment) — this repo intentionally stays keyless, so instead the reversal pipeline pulls the free equivalent from perpetual futures markets (Binance USDT-M, via `ccxt`, public endpoints only):

- **Funding rate** — negative funding means shorts are paying longs, i.e. shorts are crowded and over-leveraged right at a base. That's classic short-squeeze fuel, and it reflects the same crowd-positioning psychology on-chain exchange-flow data is trying to capture, just read through the derivatives market instead of the blockchain.
- **Open interest** — used opportunistically as a secondary read (falling OI into the decline suggests leveraged weak hands were flushed out, a healthier base to reverse from).

This is a **live-only bonus**, applied only after a symbol has already passed the OHLCV-only reversal gate (bounds the extra API calls to genuinely interesting candidates) — never a hard requirement, so a coin simply not listed on futures loses the bonus points, not the signal.

### v3 recap — Institutional-Grade Signals (kept, now the SECONDARY pipeline)

v2 had a real problem: alerts tended to fire *after* a coin had already pumped and was rolling back over, because the core gate (a volume spike that already happened) and several of the scoring inputs (MACD cross, Donchian breakout) are lagging-by-definition confirmation signals. v3 added the context a discretionary desk checks before sizing a long, specifically to catch setups earlier and reject setups that are already extended:

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

## Backtesting & Self-Tuning (the learning loop)

A separate weekly workflow (`backtest.yml`) closes the loop: it replays the **exact same scoring logic** the live scanner uses against real historical KuCoin data, resolves every simulated signal against its own future candles (deterministically, since it's history), and logs the result. Combined with live results (the scanner already tracks whether every real alert's SL/TP1/TP2 got hit), this builds up a growing dataset of "what actually worked."

- **`engine.py`** — the OHLCV-only scoring logic for BOTH pipelines (`evaluate_candidate` for breakout, `evaluate_reversal_candidate` for reversal), factored out so live scanning and backtesting call the *identical* code path. No drift between what's backtested and what's live.
- **`backtest.py`** — walks forward through ~30 days of history across the top-volume symbols, bar by bar, evaluating BOTH pipelines at every step and recording every candidate (tagged `pipeline: "breakout"` or `"reversal"`) and its eventual outcome to `state/trade_log.jsonl`.
- **`tuner.py`** — reads the accumulated trade log and asks, per signal **per pipeline**: *does this component actually correlate with wins?* Breakout and reversal components are analyzed separately (they're different signals entirely — mixing them would corrupt the comparison), each with its own trust threshold (default 20+ samples each) and its own threshold sweep (`SCORE_THRESHOLD` for breakout, `REVERSAL_SCORE_THRESHOLD` for reversal).

**Nothing self-modifies without review.** The weekly workflow commits the new trade-log data straight to `main` (it's just accumulated data), but any suggested change to `config.py`'s weights or thresholds goes out as a **pull request** with the full per-pipeline analysis in the description — a human still signs off before it changes what real alerts look like. Run it manually any time with:

```
python backtest.py      # replay history, append to state/trade_log.jsonl (both pipelines)
python tuner.py          # report only, no changes
python tuner.py --apply  # writes suggested changes into config.py (for review before committing)
```

Known limitations: the backtest can't replay the live-only microstructure gates (taker buy/sell ratio, order book imbalance, cross-exchange validation, futures funding-rate/OI positioning) since those need live data that doesn't exist historically — so it's directionally useful, not a byte-for-byte simulation of what live alerts would have fired. Old trade-log entries predate the reversal pipeline and are treated as `pipeline: "breakout"` by both the backtest dedup logic and the tuner.

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
2. **BTC Context Check** — if BTC is in a bear trend, the *breakout* threshold is raised by +10 (a bottom-reversal detector is expected to be active during bearish conditions — that's when bottoms form — so this does NOT raise the reversal threshold)
3. **Fear & Greed Check** — if the market is in Extreme Greed (≥80), BOTH thresholds are raised (euphoric markets are where "pre-breakout" alerts most often turn out to be blow-off tops, and a "dip" during euphoria is often a fake base, not a real bottom)
4. **Market-Wide News Check** — if there's an acute market-wide negative headline (exchange collapse, regulatory crackdown, flash crash) in the last 12h, the whole scan cycle is paused — no new longs into a risk-off tape
5. **Coin-Specific News Gate** — any symbol with a recent hack/delisting/lawsuit/fraud headline is hard-blocked before either pipeline runs
6. **Candles fetched once per symbol** (15m + 1h), shared by both pipelines below — no duplicate API calls
7. **🔄 PRIMARY: Bottom Reversal pipeline** (`evaluate_reversal_candidate`, runs on every symbol):
   - **Bottom structure (1h)** — is price basing within `REVERSAL_PROXIMITY_PCT` of the lookback low, at least `REVERSAL_MIN_BASE_BARS` bars after that low printed, following a confirmed prior decline of ≥`REVERSAL_PRIOR_DECLINE_PCT`%? Also checks for a **higher-low** swing structure (the classic first sign a downtrend has broken)
   - **Reversal evidence gate** — requires at least one of: RSI/MACD bullish divergence, StochRSI turning up from oversold, or a Wyckoff accumulation volume signature. "Near a low" alone is not a signal — it could just keep falling
   - **Modest volume gate** — only needs `REVERSAL_MIN_VOL_RATIO` (1.2x), not a full spike — catching it early means volume hasn't exploded yet
   - **Full scoring suite**: RSI/MACD divergence, Wyckoff volume dry-up/expansion signature, CMF, ADL+Chaikin, OBV, StochRSI/Williams %R momentum turn, BB Squeeze, early volume pickup, 1h regime agreement, relative strength vs BTC, **futures funding rate / open interest** (live-only bonus, fetched only for candidates that already passed the gates above)
   - **Structural stop-loss** — placed just under the base low (if the base breaks, the reversal thesis is invalidated), not a generic ATR multiple
8. **🚀 SECONDARY: Confirmed Breakout pipeline** (`evaluate_candidate`, unchanged from v2/v3 — requires a volume spike ≥3.5× that has *already* happened):
   - RSI (14), MACD (12/26/9), Bollinger Band Squeeze, ATR, OBV, Stochastic RSI, CMF, Williams %R, ADL + Chaikin Oscillator, Donchian Channel Breakout, Linear Regression Channel, EMA Trend + swing structure, Golden/Death Cross regime (1h, 50/200 EMA), RSI+MACD bearish-divergence penalty, Relative Strength vs BTC
   - **Live-only microstructure gates**: CLV (close location value), taker buy/sell ratio, order book imbalance, Binance cross-validation — reject volume spikes that are actually distribution, not buying
9. **Composite Score (0–100)** for each pipeline independently — clipped, each with its own alert threshold
10. **Alert Cooldown** — tracked **per pipeline** (`symbol#reversal`, `symbol#breakout`, `symbol#news`) — a coin can legitimately fire a reversal alert at the bottom, then a separate breakout alert later once it actually launches
11. **Telegram Alerts** — `🔄 BOTTOM REVERSAL` (primary) sent first, then `🚀 CONFIRMED BREAKOUT` (secondary), then `📰 NEWS CATALYST` — each tagged, scored, and carrying SL/TP + a TradingView link

### Scoring Weights — 🔄 Bottom Reversal (primary)

| Signal | Max Points |
|---|---|
| Bullish Divergence (RSI/MACD) | 25 *(the core "diverging to move up" trigger)* |
| Bottom Structure (near the lookback low, after a confirmed decline) | 20 |
| Wyckoff Accumulation Volume Signature (down-vol dry-up + up-vol expansion) | 15 |
| Momentum Turn (StochRSI out of oversold) | 10 |
| Higher-Low Structure | 10 |
| Futures Funding Rate / OI (live-only smart-money proxy) | 10 |
| CMF Positive | 8 |
| ADL + Chaikin Accumulation | 8 |
| BB Squeeze (coiling at the base) | 8 |
| OBV Rising | 7 |
| Early Volume Pickup (1.2×–2.5×, modest — not a launched breakout) | 7 |
| 1h Regime Agreement / fresh Golden Cross | 5 |
| Relative Strength vs BTC (leading while basing) | +5 |
| Positive news catalyst | +5 |

Score is clipped to 0–100. **Default alert threshold: `REVERSAL_SCORE_THRESHOLD` = 60/100.**

### Scoring Weights — 🚀 Confirmed Breakout (secondary)

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

Score is clipped to 0–100. **Default alert threshold: `SCORE_THRESHOLD` = 65/100** (raised automatically during BTC bear trends or Extreme Greed).

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
2. Click **Pre-Breakout Scanner v4**
3. Click **Run workflow** → **Run workflow** (manual trigger)
4. After ~2 minutes check Telegram — you should receive a silent summary message

That's it. The system runs automatically every 15 minutes from now on.

---

## File Structure

```
pre-breakout-scanner/
├── scanner.py          ← Main orchestrator (live, every 15 min) — runs BOTH pipelines per symbol
├── engine.py           ← Shared scoring logic — evaluate_candidate (breakout) + evaluate_reversal_candidate
│                          (reversal), used by scanner.py AND backtest.py
├── backtest.py         ← Historical replay engine (weekly) — backtests BOTH pipelines
├── tuner.py            ← Reads trade_log.jsonl, suggests weight/threshold changes PER PIPELINE
├── indicators.py       ← All TA indicators, incl. bottom structure, accumulation signature,
│                          golden/death cross, divergence, relative strength
├── derivatives.py      ← Free futures funding-rate/OI proxy for on-chain/smart-money positioning
├── news.py             ← Fear & Greed + keyless news sentiment (RSS feeds, alternative.me)
├── config.py           ← All tunable parameters in one place
├── requirements.txt    ← Only 2 dependencies: ccxt + requests
├── state/
│   ├── known_symbols.json   ← Auto-updated each run (tracks symbols + per-pipeline cooldowns)
│   ├── trade_log.jsonl      ← Every resolved trade, live + backtest, tagged with pipeline (the learning data)
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
| **Reversal pipeline (primary)** | | |
| `REVERSAL_SCORE_THRESHOLD` | 60 | Lower = more reversal alerts, Higher = fewer, higher-conviction only |
| `REVERSAL_PROXIMITY_PCT` | 8.0% | How close to the lookback low price must be to count as "basing" — lower = stricter |
| `REVERSAL_PRIOR_DECLINE_PCT` | 8.0% | Minimum decline into the low required to confirm a real downtrend preceded it, not chop |
| `REVERSAL_MIN_BASE_BARS` | 3 | Bars since the exact low before it counts as "basing" — avoids calling bottom on the falling knife |
| `REVERSAL_MIN_VOL_RATIO` | 1.2× | Minimum volume pickup to trigger — deliberately much lower than the breakout pipeline's 3.5x |
| `REVERSAL_LOOKBACK_BARS` | 80 (1h) | Window scanned for the base/lowest low — ~3.3 days |
| `REVERSAL_MAX_ALERTS_PER_RUN` | 10 | Cap to prevent Telegram flood |
| `USE_DERIVATIVES_CONTEXT` | True | Set False to skip the futures funding-rate/OI positioning bonus |
| **Breakout pipeline (secondary)** | | |
| `VOLUME_SPIKE_RATIO` | 3.5× | Lower = more signals (noisier), Higher = fewer (cleaner) |
| `SCORE_THRESHOLD` | 65 | Lower = more alerts, Higher = fewer, high-conviction only |
| `CROSS_VALIDATE` | True | Set False to skip Binance check (faster) |
| `MAX_ALERTS_PER_RUN` | 10 | Cap to prevent Telegram flood |
| `USE_GOLDEN_CROSS` / `USE_DIVERGENCE_DETECTION` / `USE_RELATIVE_STRENGTH` | True | Set False to disable any individual institutional signal |
| `EARLY_MOVE_MAX_PCT` | 3.0 | Lower = stricter about how "early" a move must still be to get the bonus |
| **Shared** | | |
| `MIN_QUOTE_VOLUME_24H` | $150,000 | Increase to focus on larger caps only |
| `ALERT_COOLDOWN_MINUTES` | 60 | Prevent alert spam on same symbol — tracked independently per pipeline |
| `USE_NEWS_FILTER` / `USE_FEAR_GREED` | True | Set False to disable the news/sentiment layer entirely (no network calls to alternative.me / news RSS feeds) |
| `FEAR_GREED_EXTREME_GREED` | 80 | Lower = threshold gets raised sooner during greedy markets (both pipelines) |

---

## Understanding the Alert

**🔄 Bottom Reversal (primary) — fires BEFORE the big move:**

```
🔄 BOTTOM REVERSAL — XYZ/USDT
Score: 78/100  🟢🟢 HIGH

💰 Price:  0.04021
🔻 Structure: 14 bars (1h) since the low  |  +2.85% off the base
📐 ✅ higher low

📐 Risk Management (structural stop under the base)
  🔴 Stop Loss:  0.03918
  🟡 Target 1:   0.04176  (R/R 1.5x)
  🟢 Target 2:   0.04330  (R/R 3.0x)

Signals:
  🔻 Basing 14 bars past the low (+2.85% off it) after a confirmed decline
  📐 Higher low structure — the downtrend structure has already broken
  ✅ RSI + MACD bullish divergence — momentum turning up under price (price LL vs RSI HL)
  ✅ Volume signature: selling drying up, buying volume expanding (accumulation)
  ✅ CMF positive (0.09) — money flowing in
  🔄 StochRSI turning up from oversold (K=24.1)
  🔥 BB Squeeze — volatility coiling at the base (bw=2.4%)
  📈 Early volume pickup (1.6x avg) — first signs of interest, not yet crowded
  ✅ Negative funding rate (-0.021%/8h) — shorts crowded and paying, squeeze fuel

📈 Open on TradingView
Early-stage/primary signal — lower conviction than a confirmed breakout, by design.
KuCoin • 14:30 UTC
```

**🚀 Confirmed Breakout (secondary) — fires AFTER the volume spike:**

```
🚀 CONFIRMED BREAKOUT — XYZ/USDT
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
Confirmed/secondary signal — the move is already underway.
KuCoin • 14:30 UTC
```

---

## Important Notes

- **First run**: No "new listing" alerts sent — all current symbols are recorded as baseline. From the second run onward, new listings are detected.
- **v4 fetches 1h candles for every symbol now**, not just the ones that already spiked — the reversal pipeline needs that history to detect a bottom on every pass. This means more API calls per cycle than v3; if you hit GitHub Actions' free-tier minutes or exchange rate limits, raise `MIN_QUOTE_VOLUME_24H` (fewer symbols scanned) or `RATE_LIMIT_SLEEP` first.
- **GitHub Actions timing**: Scheduled jobs may be delayed a few minutes during peak hours — this is normal and free.
- **GitHub free tier**: 2,000 minutes/month for private repos. Monitor actual usage in the Actions tab after the v4 change — budget for more than v3's ~600 min/month given the additional 1h fetches.
- **This system is independent** from any Wyckoff/VSA or other system you run — it does not modify any shared state.
- **News/sentiment sources are free and keyless** (alternative.me, public RSS feeds) — no new GitHub secrets needed. News originally ran on CryptoCompare's API but that now requires a registered key (HTTP 401 as of 2026-08), so it switched to RSS. The coin-news and market-wide checks are simple keyword matching, not NLP — treat them as a blunt red/green-flag filter, not a guarantee.
- **A cycle can come back with zero alerts and a "paused" summary ping** — that means market-wide risk-off news was detected and no new longs were evaluated that cycle, by design.
- **Reversal alerts are earlier and lower-conviction by design.** They fire before the breakout pipeline's volume-spike gate would ever trip, which means a higher false-positive rate is the expected tradeoff for catching moves early — the whole point of pairing two independent pipelines is that neither has to compromise between "early" and "confirmed" on its own.
- **True on-chain data isn't in this system.** The `🔄` derivatives bonus (funding rate / open interest) is a free proxy from perpetual futures markets, not actual blockchain data — see "On-chain / smart-money positioning" above for why, and what it would take to wire in a real provider.

---

## نظرة عامة بالعربية

هذا النظام يرصد فرص الدخول المبكر في العملات الرقمية على منصة KuCoin عبر مسارين مستقلّين يعملان في كل دورة فحص:

- **🔄 اكتشاف القاع والانعكاس (المسار الأساسي في v4)** — يحلّل هل وصلت العملة لقاع بعد هبوط حقيقي، وهل بدأ الزخم والحجم بالانحراف (Divergence) للأعلى قبل أن يظهر أي انفجار حجم كبير. يعتمد على: هيكل القاع على فريم الساعة (قرب القاع + قاع أعلى من السابق)، تباعد RSI/MACD الصعودي، توقيع الحجم على طريقة Wyckoff (جفاف البيع + توسع الشراء)، StochRSI الخارج من التشبع البيعي، ومؤشر بديل مجاني لتدفقات "الأموال الذكية" (سعر التمويل والفائدة المفتوحة في سوق العقود الآجلة، بدل بيانات on-chain المدفوعة).
- **🚀 تأكيد الاختراق (المسار الثانوي، من v2/v3)** — يتطلب انفجار حجم ≥3.5x قد حدث بالفعل، مع تأكيد من 11 مؤشراً فنياً (RSI، MACD، BB Squeeze، OBV، CMF، ADL+Chaikin، دونشيان، قناة الانحدار الخطي، Williams %R، StochRSI، القوة النسبية مقابل BTC).
- **📰 تنبيهات الأخبار** — عندما يكون الخبر الإيجابي هو المحفّز نفسه، وليس مجرد فلتر لاحق.

كل مسار له سجّل تهدئة (cooldown) مستقل، بحيث يمكن أن تصلك إشارة انعكاس عند القاع، ثم إشارة اختراق منفصلة لاحقاً عندما تنطلق العملة فعلاً. جميع الإعدادات القابلة للتعديل موجودة في `config.py`.
