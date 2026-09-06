# Self-Tuning Report

Trade log: 1728 total (180 live, 1548 backtest) — 1728 decided (win/loss), 0 expired/inconclusive.
Overall win rate: **43.7%** (755W / 973L)

## Per-Signal Win-Rate Analysis

| Component | Weight | With | Without | Δ (pp) | Suggested |
|---|---|---|---|---|---|
| rsi_healthy | WEIGHT_RSI | 43.1% (n=1173) | 45.2% (n=535) | -2.2 | 10 (no change) |
| macd_bullish_cross | WEIGHT_MACD | 41.5% (n=246) | 44.1% (n=1462) | -2.7 | 10 (no change) |
| bb_squeeze | WEIGHT_BB_SQUEEZE | 43.3% (n=413) | 43.9% (n=1295) | -0.5 | 15 (no change) |
| donchian_breakout | WEIGHT_DONCHIAN | 44.7% (n=698) | 43.1% (n=1010) | +1.6 | 6 (no change) |
| trend_bullish | WEIGHT_TREND_EMA | 46.3% (n=659) | 42.1% (n=1049) | +4.1 | 10 (no change) |
| adl_accumulating | WEIGHT_ADL_CHAIKIN | 44.9% (n=1516) | 34.4% (n=192) | +10.5 | 10 → **11** |
| obv_rising | WEIGHT_OBV | 43.3% (n=1442) | 46.2% (n=266) | -3.0 | 5 (no change) |
| htf_confirmed | HTF_CONFIRM_BONUS | 42.8% (n=402) | 44.0% (n=1306) | -1.2 | 5 (no change) |
| golden_cross_bullish | WEIGHT_GOLDEN_CROSS | 44.3% (n=909) | 43.1% (n=799) | +1.3 | 8 (no change) |
| death_cross_active | GOLDEN_CROSS_PENALTY | 43.1% (n=799) | 44.3% (n=909) | -1.3 | 10 (no change) |
| bullish_divergence | WEIGHT_BULLISH_DIVERGENCE | 35.5% (n=217) | 44.9% (n=1491) | -9.5 | 8 (no change) |
| bearish_divergence | BEARISH_DIVERGENCE_PENALTY | 43.7% (n=197) | 43.7% (n=1511) | -0.1 | 12 (no change) |
| rs_leading | WEIGHT_RELATIVE_STRENGTH | 43.9% (n=1220) | 43.2% (n=488) | +0.7 | 7 (no change) |
| early_move | EARLY_MOVE_BONUS | 43.1% (n=889) | 44.4% (n=819) | -1.4 | 5 (no change) |

## Score Threshold Sweep

| Threshold | Trades | Win Rate |
|---|---|---|
| 50 | 1450 | 44.1% |
| 55 | 1286 | 43.1% |
| 60 | 1136 | 43.1% |
| 65 | 954 | 43.4% ← current |
| 70 | 761 | 43.5% |
| 75 | 559 | 43.1% |
| 80 | 386 | 42.7% |
| 85 | 234 | 41.9% |

_Note: backtest trades don't replay the live-only microstructure gates (taker buy/sell ratio, order book, cross-exchange validation), so this is directionally useful, not an exact simulation of live alerts._