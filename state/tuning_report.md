# Self-Tuning Report

Trade log: 2120 total (228 live, 1892 backtest) — 2118 decided (win/loss), 2 expired/inconclusive.
Overall win rate: **42.4%** (898W / 1220L)

## Per-Signal Win-Rate Analysis

| Component | Weight | With | Without | Δ (pp) | Suggested |
|---|---|---|---|---|---|
| rsi_healthy | WEIGHT_RSI | 41.9% (n=1432) | 43.6% (n=663) | -1.7 | 10 (no change) |
| macd_bullish_cross | WEIGHT_MACD | 41.9% (n=315) | 42.5% (n=1780) | -0.6 | 10 (no change) |
| bb_squeeze | WEIGHT_BB_SQUEEZE | 41.6% (n=505) | 42.7% (n=1590) | -1.1 | 15 (no change) |
| donchian_breakout | WEIGHT_DONCHIAN | 43.3% (n=864) | 41.8% (n=1231) | +1.5 | 6 (no change) |
| trend_bullish | WEIGHT_TREND_EMA | 44.4% (n=816) | 41.2% (n=1279) | +3.2 | 10 (no change) |
| adl_accumulating | WEIGHT_ADL_CHAIKIN | 43.6% (n=1847) | 33.9% (n=248) | +9.7 | 10 → **11** |
| obv_rising | WEIGHT_OBV | 41.9% (n=1772) | 45.5% (n=323) | -3.6 | 5 (no change) |
| htf_confirmed | HTF_CONFIRM_BONUS | 41.6% (n=507) | 42.7% (n=1588) | -1.1 | 5 (no change) |
| golden_cross_bullish | WEIGHT_GOLDEN_CROSS | 42.8% (n=1167) | 41.9% (n=928) | +0.9 | 8 (no change) |
| death_cross_active | GOLDEN_CROSS_PENALTY | 41.8% (n=926) | 42.9% (n=1169) | -1.2 | 10 (no change) |
| bullish_divergence | WEIGHT_BULLISH_DIVERGENCE | 36.1% (n=255) | 43.3% (n=1840) | -7.2 | 8 (no change) |
| bearish_divergence | BEARISH_DIVERGENCE_PENALTY | 42.7% (n=241) | 42.4% (n=1854) | +0.3 | 12 (no change) |
| rs_leading | WEIGHT_RELATIVE_STRENGTH | 42.3% (n=1520) | 42.8% (n=575) | -0.5 | 7 (no change) |
| early_move | EARLY_MOVE_BONUS | 43.0% (n=1106) | 41.8% (n=989) | +1.3 | 5 (no change) |

## Score Threshold Sweep

| Threshold | Trades | Win Rate |
|---|---|---|
| 50 | 1792 | 42.7% |
| 55 | 1597 | 41.7% |
| 60 | 1414 | 41.7% |
| 65 | 1184 | 42.0% ← current |
| 70 | 947 | 42.3% |
| 75 | 694 | 42.7% |
| 80 | 474 | 42.2% |
| 85 | 283 | 42.8% |

_Note: backtest trades don't replay the live-only microstructure gates (taker buy/sell ratio, order book, cross-exchange validation), so this is directionally useful, not an exact simulation of live alerts._