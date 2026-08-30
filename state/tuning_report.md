# Self-Tuning Report

Trade log: 1419 total (157 live, 1262 backtest) — 1419 decided (win/loss), 0 expired/inconclusive.
Overall win rate: **43.1%** (611W / 808L)

## Per-Signal Win-Rate Analysis

| Component | Weight | With | Without | Δ (pp) | Suggested |
|---|---|---|---|---|---|
| rsi_healthy | WEIGHT_RSI | 42.2% (n=980) | 45.1% (n=419) | -2.9 | 10 (no change) |
| macd_bullish_cross | WEIGHT_MACD | 40.8% (n=206) | 43.5% (n=1193) | -2.7 | 10 (no change) |
| bb_squeeze | WEIGHT_BB_SQUEEZE | 41.6% (n=339) | 43.6% (n=1060) | -2.0 | 15 (no change) |
| donchian_breakout | WEIGHT_DONCHIAN | 43.8% (n=544) | 42.7% (n=855) | +1.1 | 6 (no change) |
| trend_bullish | WEIGHT_TREND_EMA | 46.1% (n=519) | 41.4% (n=880) | +4.7 | 10 (no change) |
| adl_accumulating | WEIGHT_ADL_CHAIKIN | 44.4% (n=1241) | 32.9% (n=158) | +11.5 | 10 → **11** |
| obv_rising | WEIGHT_OBV | 42.6% (n=1170) | 45.4% (n=229) | -2.8 | 5 (no change) |
| htf_confirmed | HTF_CONFIRM_BONUS | 43.6% (n=337) | 42.9% (n=1062) | +0.7 | 5 (no change) |
| golden_cross_bullish | WEIGHT_GOLDEN_CROSS | 43.4% (n=731) | 42.8% (n=668) | +0.6 | 8 (no change) |
| death_cross_active | GOLDEN_CROSS_PENALTY | 42.8% (n=668) | 43.4% (n=731) | -0.6 | 10 (no change) |
| bullish_divergence | WEIGHT_BULLISH_DIVERGENCE | 33.9% (n=171) | 44.4% (n=1228) | -10.5 | 8 → **7** |
| bearish_divergence | BEARISH_DIVERGENCE_PENALTY | 40.9% (n=164) | 43.4% (n=1235) | -2.5 | 12 (no change) |
| rs_leading | WEIGHT_RELATIVE_STRENGTH | 43.2% (n=970) | 42.9% (n=429) | +0.3 | 7 (no change) |
| early_move | EARLY_MOVE_BONUS | 43.0% (n=703) | 43.2% (n=696) | -0.3 | 5 (no change) |

## Score Threshold Sweep

| Threshold | Trades | Win Rate |
|---|---|---|
| 50 | 1167 | 43.3% |
| 55 | 1039 | 42.1% |
| 60 | 908 | 42.2% |
| 65 | 761 | 42.8% ← current |
| 70 | 603 | 43.1% |
| 75 | 442 | 43.4% |
| 80 | 301 | 42.9% |
| 85 | 182 | 41.8% |

_Note: backtest trades don't replay the live-only microstructure gates (taker buy/sell ratio, order book, cross-exchange validation), so this is directionally useful, not an exact simulation of live alerts._