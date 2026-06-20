# ⚡ Pre-Breakout Scanner v2

**Advanced crypto pre-breakout detection system — runs fully automated on GitHub's free servers every 15 minutes. No computer, no Colab, no VPS needed.**

---

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
3. **Volume Gate** — only symbols with a volume spike ≥ 3.5× their 20-bar average pass through (fast filter, avoids computing all indicators on every symbol)
4. **Full indicator suite** (only on volume-spike candidates):
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
5. **1-hour Confirmation** — fetches 1h candles and checks if higher timeframe agrees
6. **Composite Score (0–100)** — each indicator contributes weighted points
7. **Binance Cross-Validation** — if the same pair shows a volume spike on Binance too, it's a stronger signal. No Binance listing → signal is kept but score is reduced by 10 pts
8. **Alert Cooldown** — same symbol won't be alerted again for 60 minutes
9. **Telegram Alert** — rich message with score, reasons, SL/TP, TradingView link

### Scoring Weights

| Signal | Max Points |
|---|---|
| Volume Explosion (>3.5× avg) | 25 |
| BB Squeeze → Expansion | 15 |
| RSI in healthy zone (38–68) | 10 |
| MACD Bullish Cross | 10 |
| Donchian Channel Breakout | 10 |
| EMA Trend Bullish | 10 |
| ADL + Chaikin Accumulation | 10 |
| Linear Regression Channel | 5 |
| OBV Rising | 5 |
| 1h HTF Bonus | +5 |
| Early Price Move (0.3–8%) | +5 |

**Default alert threshold: 65/100**

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
├── scanner.py          ← Main orchestrator
├── indicators.py       ← All 11 TA indicators (pure Python, zero extra deps)
├── config.py           ← All tunable parameters in one place
├── requirements.txt    ← Only 2 dependencies: ccxt + requests
├── state/
│   └── known_symbols.json   ← Auto-updated each run (tracks symbols + cooldowns)
└── .github/
    └── workflows/
        └── scan.yml    ← GitHub Actions definition
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
