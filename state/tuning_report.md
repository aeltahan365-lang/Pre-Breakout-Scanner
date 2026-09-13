# Self-Tuning Report

Trade log: 1963 total (204 live, 1759 backtest) — 1963 decided (win/loss), 0 expired/inconclusive.
Overall win rate: **43.0%** (845W / 1118L)

## Per-Signal Win-Rate Analysis

| Component | Weight | With | Without | Δ (pp) | Suggested |
|---|---|---|---|---|---|
| rsi_healthy | WEIGHT_RSI | 42.7% (n=1334) | 43.9% (n=608) | -1.2 | 10 (no change) |
| macd_bullish_cross | WEIGHT_MACD | 42.6% (n=282) | 43.2% (n=1660) | -0.6 | 10 (no change) |
| bb_squeeze | WEIGHT_BB_SQUEEZE | 42.8% (n=465) | 43.2% (n=1477) | -0.4 | 15 (no change) |
| donchian_breakout | WEIGHT_DONCHIAN | 43.8% (n=784) | 42.7% (n=1158) | +1.1 | 6 (no change) |
| trend_bullish | WEIGHT_TREND_EMA | 45.0% (n=744) | 41.9% (n=1198) | +3.1 | 10 (no change) |
| adl_accumulating | WEIGHT_ADL_CHAIKIN | 44.3% (n=1708) | 34.2% (n=234) | +10.1 | 10 → **11** |
| obv_rising | WEIGHT_OBV | 42.6% (n=1638) | 46.1% (n=304) | -3.5 | 5 (no change) |
| htf_confirmed | HTF_CONFIRM_BONUS | 41.0% (n=471) | 43.8% (n=1471) | -2.8 | 5 (no change) |
| golden_cross_bullish | WEIGHT_GOLDEN_CROSS | 43.3% (n=1098) | 42.9% (n=844) | +0.4 | 8 (no change) |
| death_cross_active | GOLDEN_CROSS_PENALTY | 42.8% (n=843) | 43.3% (n=1099) | -0.5 | 10 (no change) |
| bullish_divergence | WEIGHT_BULLISH_DIVERGENCE | 35.7% (n=238) | 44.1% (n=1704) | -8.4 | 8 (no change) |
| bearish_divergence | BEARISH_DIVERGENCE_PENALTY | 42.4% (n=217) | 43.2% (n=1725) | -0.8 | 12 (no change) |
| rs_leading | WEIGHT_RELATIVE_STRENGTH | 42.9% (n=1397) | 43.5% (n=545) | -0.5 | 7 (no change) |
| early_move | EARLY_MOVE_BONUS | 43.3% (n=1017) | 42.9% (n=925) | +0.3 | 5 (no change) |

## Score Threshold Sweep

| Threshold | Trades | Win Rate |
|---|---|---|
| 50 | 1660 | 43.3% |
| 55 | 1473 | 42.2% |
| 60 | 1307 | 42.4% |
| 65 | 1092 | 42.7% ← current |
| 70 | 879 | 42.7% |
| 75 | 646 | 42.7% |
| 80 | 442 | 42.1% |
| 85 | 264 | 42.4% |

_Note: backtest trades don't replay the live-only microstructure gates (taker buy/sell ratio, order book, cross-exchange validation), so this is directionally useful, not an exact simulation of live alerts._