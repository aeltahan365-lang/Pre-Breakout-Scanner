# Self-Tuning Report

Trade log: 701 total (0 live, 701 backtest) — 701 decided (win/loss), 0 expired/inconclusive.
Overall win rate: **44.4%** (311W / 390L)

## Per-Signal Win-Rate Analysis

| Component | Weight | With | Without | Δ (pp) | Suggested |
|---|---|---|---|---|---|
| rsi_healthy | WEIGHT_RSI | 45.1% (n=532) | 42.0% (n=169) | +3.1 | 10 (no change) |
| macd_bullish_cross | WEIGHT_MACD | 39.2% (n=125) | 45.5% (n=576) | -6.3 | 10 (no change) |
| bb_squeeze | WEIGHT_BB_SQUEEZE | 38.9% (n=167) | 46.1% (n=534) | -7.1 | 15 → **14** |
| donchian_breakout | WEIGHT_DONCHIAN | 42.6% (n=209) | 45.1% (n=492) | -2.5 | 6 (no change) |
| trend_bullish | WEIGHT_TREND_EMA | 46.5% (n=217) | 43.4% (n=484) | +3.2 | 10 (no change) |
| adl_accumulating | WEIGHT_ADL_CHAIKIN | 44.9% (n=619) | 40.2% (n=82) | +4.7 | 10 (no change) |
| obv_rising | WEIGHT_OBV | 43.3% (n=564) | 48.9% (n=137) | -5.6 | 5 (no change) |
| htf_confirmed | HTF_CONFIRM_BONUS | 48.4% (n=157) | 43.2% (n=544) | +5.2 | 5 (no change) |
| golden_cross_bullish | WEIGHT_GOLDEN_CROSS | 46.2% (n=333) | 42.7% (n=368) | +3.6 | 8 (no change) |
| death_cross_active | GOLDEN_CROSS_PENALTY | 42.7% (n=368) | 46.2% (n=333) | -3.6 | 10 (no change) |
| bullish_divergence | WEIGHT_BULLISH_DIVERGENCE | 35.7% (n=98) | 45.8% (n=603) | -10.1 | 8 (no change) |
| bearish_divergence | BEARISH_DIVERGENCE_PENALTY | 41.0% (n=78) | 44.8% (n=623) | -3.8 | 12 (no change) |
| rs_leading | WEIGHT_RELATIVE_STRENGTH | 44.7% (n=461) | 43.8% (n=240) | +0.9 | 7 (no change) |
| early_move | EARLY_MOVE_BONUS | 43.1% (n=304) | 45.3% (n=397) | -2.2 | 5 (no change) |

## Score Threshold Sweep

| Threshold | Trades | Win Rate |
|---|---|---|
| 50 | 555 | 44.1% |
| 55 | 484 | 42.8% |
| 60 | 416 | 43.3% |
| 65 | 338 | 42.9% ← current |
| 70 | 255 | 41.6% |
| 75 | 184 | 42.4% |
| 80 | 121 | 45.5% |
| 85 | 73 | 43.8% |

_Note: backtest trades don't replay the live-only microstructure gates (taker buy/sell ratio, order book, cross-exchange validation), so this is directionally useful, not an exact simulation of live alerts._