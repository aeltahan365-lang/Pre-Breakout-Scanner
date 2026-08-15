"""
Pre-Breakout Scanner — Miss Hunter (weekly evidence-based tuning)
====================================================================
backtest.py answers "of the candidates we WOULD have flagged, how did they
do?" — but a symbol that never passes the hard gates (bottom structure,
prior decline, reversal evidence, volume explosion) never produces a
candidate at all, so it never shows up in that analysis. This script
answers the other half of the question: "of the coins that actually
pumped last week, which ones did we never even look at twice — and why?"

For every real pump found in the last MISS_HUNTER_LOOKBACK_DAYS across the
same symbol universe backtest.py uses:
  1. Replay both pipelines in the hours immediately before/at the pump's
     start — did either one fire in time to matter?
  2. If not, pinpoint the EXACT gate that blocked it (not near a low? no
     divergence? volume too quiet? score just short?) by walking the same
     gate sequence evaluate_reversal_candidate / evaluate_candidate use.
  3. Aggregate misses into patterns and propose small, capped, PR-reviewed
     config nudges — same "nothing self-modifies without review" philosophy
     as tuner.py.

Run manually:  python miss_hunter.py
               python miss_hunter.py --apply   (writes suggested nudges into config.py)
Or via the weekly `backtest.yml` GitHub Actions workflow, alongside tuner.py.
"""

import os
import sys
import time
from collections import Counter

import ccxt

import config as cfg
from backtest import log, ohlcv_to_dicts, fetch_ohlcv_range, pick_symbol_universe, _window_ending_at
from tuner import _set_config_value
from engine import evaluate_candidate, evaluate_reversal_candidate
from indicators import (
    calc_bottom_structure,
    calc_accumulation_signature,
    calc_rsi_divergence,
    calc_macd_divergence,
    calc_stoch_rsi,
    calc_volume_explosion,
)


# ═══════════════════════════════════════════════════════════════════
# PUMP DETECTION
# ═══════════════════════════════════════════════════════════════════

def find_pumps(candles_15m: list, start_idx: int, window_bars: int, min_pct: float) -> list:
    """
    Scans candles_15m[start_idx:] for local pump events: price rallying
    >= min_pct from a bar's low to the highest high within the following
    window_bars. Non-overlapping — once a pump is found, scanning resumes
    after its peak, so one big move isn't double-counted.
    Returns a list of dicts: {start_idx, peak_idx, low, high, pct}.
    """
    pumps = []
    n = len(candles_15m)
    i = start_idx
    while i < n - 1:
        low = candles_15m[i]["low"]
        future = candles_15m[i + 1: i + 1 + window_bars]
        if not future:
            break
        peak_offset = max(range(len(future)), key=lambda k: future[k]["high"])
        peak_high = future[peak_offset]["high"]
        pct = ((peak_high - low) / low * 100) if low else 0.0
        if pct >= min_pct:
            peak_idx = i + 1 + peak_offset
            pumps.append({"start_idx": i, "peak_idx": peak_idx, "low": low,
                          "high": peak_high, "pct": round(pct, 2)})
            i = peak_idx + 1
        else:
            i += 1
    return pumps


# ═══════════════════════════════════════════════════════════════════
# MISS DIAGNOSIS — walk the same gate sequence the live pipelines use
# ═══════════════════════════════════════════════════════════════════

def diagnose_reversal_miss(candles_15m: list, candles_1h: list, ts_1h: list,
                           btc_15m: list, btc_ts: list, idx: int) -> dict:
    window = candles_15m[max(0, idx - cfg.CANDLES_PRIMARY + 1): idx + 1]
    if len(window) < cfg.REVERSAL_ACCUM_LOOKBACK + 10:
        return {"reason": "insufficient_15m_history"}

    htf_window = _window_ending_at(candles_1h, ts_1h, window[-1]["ts"], cfg.CANDLES_CONFIRM)
    if not htf_window or len(htf_window) < cfg.REVERSAL_LOOKBACK_BARS + 5:
        return {"reason": "insufficient_1h_history"}

    bottom = calc_bottom_structure(htf_window, lookback=cfg.REVERSAL_LOOKBACK_BARS)
    if not bottom["near_low"]:
        return {"reason": "not_near_low", "pct_from_low": bottom.get("pct_from_low"),
                "bars_since_low": bottom.get("bars_since_low")}
    if not bottom["prior_trend_down"]:
        return {"reason": "no_prior_decline", "decline_pct": bottom.get("decline_pct")}

    rsi_div  = calc_rsi_divergence(window)
    macd_div = calc_macd_divergence(window)
    stoch    = calc_stoch_rsi(window)
    accum    = calc_accumulation_signature(window, lookback=cfg.REVERSAL_ACCUM_LOOKBACK)
    has_evidence = (rsi_div.get("bullish") or macd_div.get("bullish") or
                    stoch.get("turning_up") or accum.get("accumulating"))
    if not has_evidence:
        return {"reason": "no_reversal_evidence"}

    _, vol_ratio, _ = calc_volume_explosion(window)
    if vol_ratio < cfg.REVERSAL_MIN_VOL_RATIO:
        return {"reason": "vol_too_quiet", "vol_ratio": vol_ratio}

    btc_window = _window_ending_at(btc_15m, btc_ts, window[-1]["ts"], cfg.RS_LOOKBACK + 5)
    result = evaluate_reversal_candidate(window, candles_1h=htf_window, btc_candles_15m=btc_window or None)
    if result is None:
        return {"reason": "gate_failed_other"}
    if result["score"] < cfg.REVERSAL_SCORE_THRESHOLD:
        weak = [k for k, v in result["components"].items() if v is False]
        return {"reason": "score_below_threshold", "score": result["score"],
                "gap": round(cfg.REVERSAL_SCORE_THRESHOLD - result["score"], 1), "weak_components": weak}
    return {"reason": "unexplained"}   # shouldn't normally happen given the caller already checked this bar


def diagnose_breakout_miss(candles_15m: list, candles_1h: list, ts_1h: list,
                           btc_15m: list, btc_ts: list, idx: int) -> dict:
    window = candles_15m[max(0, idx - cfg.CANDLES_PRIMARY + 1): idx + 1]
    if len(window) < cfg.VOLUME_LOOKBACK + 10:
        return {"reason": "insufficient_15m_history"}

    explosion, vol_ratio, _ = calc_volume_explosion(window)
    if not explosion:
        return {"reason": "no_volume_spike", "vol_ratio": vol_ratio}

    htf_window = _window_ending_at(candles_1h, ts_1h, window[-1]["ts"], cfg.CANDLES_CONFIRM)
    btc_window = _window_ending_at(btc_15m, btc_ts, window[-1]["ts"], cfg.RS_LOOKBACK + 5)
    result = evaluate_candidate(window, candles_1h=htf_window or None, btc_candles_15m=btc_window or None)
    if result is None:
        return {"reason": "clv_gate"}
    if result["score"] < cfg.SCORE_THRESHOLD:
        weak = [k for k, v in result["components"].items() if v is False]
        return {"reason": "score_below_threshold", "score": result["score"],
                "gap": round(cfg.SCORE_THRESHOLD - result["score"], 1), "weak_components": weak}
    return {"reason": "unexplained"}


# ═══════════════════════════════════════════════════════════════════
# PER-SYMBOL HUNT
# ═══════════════════════════════════════════════════════════════════

def hunt_symbol(symbol: str, candles_15m: list, candles_1h: list, btc_15m: list, btc_ts: list,
                eval_start_idx: int) -> list:
    ts_1h = [c["ts"] for c in candles_1h]
    pumps = find_pumps(candles_15m, eval_start_idx, cfg.MISS_HUNTER_PUMP_WINDOW_BARS,
                       cfg.MISS_HUNTER_PUMP_MIN_PCT)
    results = []

    for p in pumps:
        start_idx = p["start_idx"]
        if start_idx < cfg.CANDLES_PRIMARY:
            continue   # not enough history before this pump to evaluate fairly

        lo = max(0, start_idx - cfg.MISS_HUNTER_CHECK_BARS_BEFORE)
        hi = min(len(candles_15m) - 1, start_idx + cfg.MISS_HUNTER_CHECK_BARS_INTO)

        reversal_caught_at = breakout_caught_at = None
        for idx in range(lo, hi + 1):
            window = candles_15m[max(0, idx - cfg.CANDLES_PRIMARY + 1): idx + 1]
            if len(window) < cfg.VOLUME_LOOKBACK + 10:
                continue
            htf_window = _window_ending_at(candles_1h, ts_1h, window[-1]["ts"], cfg.CANDLES_CONFIRM)
            btc_window = _window_ending_at(btc_15m, btc_ts, window[-1]["ts"], cfg.RS_LOOKBACK + 5)

            if reversal_caught_at is None:
                r = evaluate_reversal_candidate(window, candles_1h=htf_window or None,
                                                btc_candles_15m=btc_window or None)
                if r is not None and r["score"] >= cfg.REVERSAL_SCORE_THRESHOLD:
                    reversal_caught_at = idx

            if breakout_caught_at is None:
                b = evaluate_candidate(window, candles_1h=htf_window or None, btc_candles_15m=btc_window or None)
                if b is not None and b["score"] >= cfg.SCORE_THRESHOLD:
                    breakout_caught_at = idx

        entry = {
            "symbol": symbol, "pump_pct": p["pct"], "start_idx": start_idx,
            "reversal_caught": reversal_caught_at is not None,
            "breakout_caught": breakout_caught_at is not None,
        }
        if reversal_caught_at is not None:
            entry["reversal_bars_early"] = start_idx - reversal_caught_at
        else:
            entry["reversal_miss"] = diagnose_reversal_miss(candles_15m, candles_1h, ts_1h,
                                                             btc_15m, btc_ts, start_idx)
        if breakout_caught_at is not None:
            entry["breakout_bars_early"] = start_idx - breakout_caught_at
        else:
            entry["breakout_miss"] = diagnose_breakout_miss(candles_15m, candles_1h, ts_1h,
                                                             btc_15m, btc_ts, start_idx)
        results.append(entry)

    return results


# ═══════════════════════════════════════════════════════════════════
# AGGREGATION + SUGGESTIONS
# ═══════════════════════════════════════════════════════════════════

def aggregate(all_pumps: list) -> dict:
    total = len(all_pumps)
    reversal_caught = sum(1 for p in all_pumps if p["reversal_caught"])
    breakout_caught = sum(1 for p in all_pumps if p["breakout_caught"])
    either_caught   = sum(1 for p in all_pumps if p["reversal_caught"] or p["breakout_caught"])

    reversal_miss_reasons = Counter(p["reversal_miss"]["reason"] for p in all_pumps if not p["reversal_caught"])
    breakout_miss_reasons = Counter(p["breakout_miss"]["reason"] for p in all_pumps if not p["breakout_caught"])

    reversal_weak = Counter()
    for p in all_pumps:
        if not p["reversal_caught"] and p["reversal_miss"]["reason"] == "score_below_threshold":
            reversal_weak.update(p["reversal_miss"].get("weak_components", []))
    breakout_weak = Counter()
    for p in all_pumps:
        if not p["breakout_caught"] and p["breakout_miss"]["reason"] == "score_below_threshold":
            breakout_weak.update(p["breakout_miss"].get("weak_components", []))

    return {
        "total": total, "reversal_caught": reversal_caught, "breakout_caught": breakout_caught,
        "either_caught": either_caught,
        "reversal_miss_reasons": reversal_miss_reasons, "breakout_miss_reasons": breakout_miss_reasons,
        "reversal_weak": reversal_weak, "breakout_weak": breakout_weak,
    }


def _nudge_toward(current: float, target: float, direction: int) -> float | None:
    """
    direction=+1: may only raise `current` toward `target` (loosens a
                  "must be within X%" style gate).
    direction=-1: may only lower `current` toward `target` (loosens a
                  "must be at least X" style gate).
    Capped to +/- MISS_HUNTER_MAX_NUDGE_PCT of the current value per pass.
    Returns None if the nudge would be a no-op or point the wrong way.
    """
    max_delta = abs(current) * cfg.MISS_HUNTER_MAX_NUDGE_PCT
    if direction > 0:
        bounded = min(target, current + max_delta)
        return round(bounded, 4) if bounded > current else None
    else:
        bounded = max(target, current - max_delta)
        return round(bounded, 4) if bounded < current else None


def suggest_adjustments(all_pumps: list) -> list:
    """
    Evidence-based, capped, human-reviewed config nudges — mirrors tuner.py's
    conservative philosophy (minimum sample size, capped step size, never
    auto-applied without --apply, and even then only lands in a PR).
    Only proposes LOOSENING a gate that's provably excluding real pumps —
    never tightens off miss data (that's what tuner.py's win-rate analysis
    on trades that DID fire is for).
    """
    suggestions = []
    n = cfg.MISS_HUNTER_MIN_SAMPLE_SIZE

    def _avg(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    not_near_low = [p["reversal_miss"] for p in all_pumps
                    if not p["reversal_caught"] and p["reversal_miss"]["reason"] == "not_near_low"]
    if len(not_near_low) >= n:
        avg_pct = _avg(m.get("pct_from_low") for m in not_near_low)
        if avg_pct is not None:
            new_val = _nudge_toward(cfg.REVERSAL_PROXIMITY_PCT, avg_pct, direction=+1)
            if new_val is not None:
                suggestions.append({
                    "attr": "REVERSAL_PROXIMITY_PCT", "current": cfg.REVERSAL_PROXIMITY_PCT, "suggested": new_val,
                    "n": len(not_near_low),
                    "rationale": f"{len(not_near_low)} missed pumps failed only the proximity-to-low gate "
                                 f"(avg {avg_pct:.1f}% off the low vs the {cfg.REVERSAL_PROXIMITY_PCT}% limit)",
                })

    no_decline = [p["reversal_miss"] for p in all_pumps
                 if not p["reversal_caught"] and p["reversal_miss"]["reason"] == "no_prior_decline"]
    if len(no_decline) >= n:
        avg_decline = _avg(m.get("decline_pct") for m in no_decline)
        if avg_decline is not None:
            new_val = _nudge_toward(cfg.REVERSAL_PRIOR_DECLINE_PCT, avg_decline, direction=-1)
            if new_val is not None:
                suggestions.append({
                    "attr": "REVERSAL_PRIOR_DECLINE_PCT", "current": cfg.REVERSAL_PRIOR_DECLINE_PCT,
                    "suggested": new_val, "n": len(no_decline),
                    "rationale": f"{len(no_decline)} missed pumps based after a real but smaller decline "
                                 f"(avg {avg_decline:.1f}% vs the {cfg.REVERSAL_PRIOR_DECLINE_PCT}% minimum required)",
                })

    too_quiet = [p["reversal_miss"] for p in all_pumps
                if not p["reversal_caught"] and p["reversal_miss"]["reason"] == "vol_too_quiet"]
    if len(too_quiet) >= n:
        avg_vol = _avg(m.get("vol_ratio") for m in too_quiet)
        if avg_vol is not None and avg_vol > 0.5:
            new_val = _nudge_toward(cfg.REVERSAL_MIN_VOL_RATIO, avg_vol, direction=-1)
            if new_val is not None:
                suggestions.append({
                    "attr": "REVERSAL_MIN_VOL_RATIO", "current": cfg.REVERSAL_MIN_VOL_RATIO, "suggested": new_val,
                    "n": len(too_quiet),
                    "rationale": f"{len(too_quiet)} missed pumps had everything else lined up but volume never "
                                 f"reached the {cfg.REVERSAL_MIN_VOL_RATIO}x minimum (avg {avg_vol:.2f}x)",
                })

    for pipeline, attr, current, reason_key in [
        ("reversal", "REVERSAL_SCORE_THRESHOLD", cfg.REVERSAL_SCORE_THRESHOLD, "reversal_miss"),
        ("breakout", "SCORE_THRESHOLD", cfg.SCORE_THRESHOLD, "breakout_miss"),
    ]:
        near_misses = [p[reason_key] for p in all_pumps
                      if not p[f"{pipeline}_caught"] and p[reason_key]["reason"] == "score_below_threshold"]
        if len(near_misses) >= n:
            scores = sorted(m["score"] for m in near_misses)
            median_score = scores[len(scores) // 2]
            new_val = _nudge_toward(current, median_score, direction=-1)
            if new_val is not None:
                suggestions.append({
                    "attr": attr, "current": current, "suggested": round(new_val),
                    "n": len(near_misses),
                    "rationale": f"{len(near_misses)} missed pumps scored below {attr} but median score among "
                                 f"them was {median_score} — {round(current - median_score, 1)} pts short on average",
                })

    return suggestions


def apply_suggestions(suggestions: list, config_path: str = "config.py") -> list:
    """Writes suggested gate/threshold nudges into config.py's text. Returns list of applied changes."""
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    applied = []
    for s in suggestions:
        content = _set_config_value(content, s["attr"], s["suggested"])
        applied.append(f"{s['attr']}: {s['current']} -> {s['suggested']}")

    if applied:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
    return applied


# ═══════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════

def build_report(all_pumps: list, agg: dict, suggestions: list, symbols_scanned: int) -> str:
    total = agg["total"]
    pct = lambda n: f"{(n / total * 100):.0f}%" if total else "n/a"

    lines = [
        "# Miss Hunter Report",
        "",
        f"Scanned {symbols_scanned} symbols over the last {cfg.MISS_HUNTER_LOOKBACK_DAYS} days, "
        f"looking for real pumps (≥{cfg.MISS_HUNTER_PUMP_MIN_PCT}% low→high within "
        f"{cfg.MISS_HUNTER_PUMP_WINDOW_BARS * 15} minutes).",
        "",
        f"**{total} pumps found.** Caught by 🔄 reversal: **{agg['reversal_caught']}** ({pct(agg['reversal_caught'])}) "
        f"| Caught by 🚀 breakout: **{agg['breakout_caught']}** ({pct(agg['breakout_caught'])}) "
        f"| Caught by either: **{agg['either_caught']}** ({pct(agg['either_caught'])})",
        "",
        "## 🔄 Reversal — Why Missed Pumps Were Missed",
        "",
        "| Reason | Count | Share of misses |",
        "|---|---|---|",
    ]
    r_missed = total - agg["reversal_caught"]
    for reason, count in agg["reversal_miss_reasons"].most_common():
        lines.append(f"| {reason} | {count} | {(count/r_missed*100):.0f}% |" if r_missed else f"| {reason} | {count} | n/a |")

    if agg["reversal_weak"]:
        lines += ["", "Most commonly missing signal among near-misses (scored but fell short):", ""]
        for comp, count in agg["reversal_weak"].most_common(5):
            lines.append(f"  - `{comp}`: absent in {count} near-miss(es)")

    lines += [
        "",
        "## 🚀 Breakout — Why Missed Pumps Were Missed",
        "",
        "| Reason | Count | Share of misses |",
        "|---|---|---|",
    ]
    b_missed = total - agg["breakout_caught"]
    for reason, count in agg["breakout_miss_reasons"].most_common():
        lines.append(f"| {reason} | {count} | {(count/b_missed*100):.0f}% |" if b_missed else f"| {reason} | {count} | n/a |")

    if agg["breakout_weak"]:
        lines += ["", "Most commonly missing signal among near-misses (scored but fell short):", ""]
        for comp, count in agg["breakout_weak"].most_common(5):
            lines.append(f"  - `{comp}`: absent in {count} near-miss(es)")

    lines += ["", "## Suggested Adjustments", ""]
    if suggestions:
        lines.append("| Parameter | Current | Suggested | Evidence |")
        lines.append("|---|---|---|---|")
        for s in suggestions:
            lines.append(f"| `{s['attr']}` | {s['current']} | **{s['suggested']}** | {s['rationale']} (n={s['n']}) |")
    else:
        lines.append(f"No pattern had {cfg.MISS_HUNTER_MIN_SAMPLE_SIZE}+ supporting misses this run — "
                     f"no changes suggested. This is expected in quiet weeks; the bar is intentionally high "
                     f"to avoid tuning off a handful of pumps.")

    lines += [
        "",
        "_Note: every suggestion here only LOOSENS a gate that provably excluded real pumps — it never tightens "
        "off miss data (that's tuner.py's job, using win-rate correlation on trades that DID fire). Each nudge is "
        f"capped to ±{cfg.MISS_HUNTER_MAX_NUDGE_PCT*100:.0f}% of its current value per run, same conservative "
        "philosophy as the self-tuner. Live-only bonuses (derivatives positioning, taker buy/sell ratio, order "
        "book, cross-exchange validation) aren't replayed here — a pump might have been catchable live via one "
        "of those even where this report shows a miss._",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    apply_mode = "--apply" in sys.argv
    log("🔎 Pre-Breakout Scanner — Miss Hunter starting")
    exchange = ccxt.kucoin({"enableRateLimit": True})

    symbols = pick_symbol_universe(exchange)
    log(f"📊 Miss-hunt universe: {len(symbols)} symbols (top by 24h volume), "
        f"{cfg.MISS_HUNTER_LOOKBACK_DAYS} days")

    until_ms = int(time.time() * 1000)
    since_btc = until_ms - (cfg.MISS_HUNTER_LOOKBACK_DAYS + 4) * 86400 * 1000
    raw_btc = fetch_ohlcv_range(exchange, "BTC/USDT", cfg.TIMEFRAME_PRIMARY, since_btc, until_ms)
    btc_15m = ohlcv_to_dicts(raw_btc)
    btc_ts  = [c["ts"] for c in btc_15m]
    log(f"📡 BTC/USDT 15m candles loaded: {len(btc_15m)}")

    all_pumps = []
    for n, symbol in enumerate(symbols, 1):
        try:
            since_15m = until_ms - (cfg.MISS_HUNTER_LOOKBACK_DAYS + 4) * 86400 * 1000
            since_1h  = until_ms - (cfg.MISS_HUNTER_LOOKBACK_DAYS + 12) * 86400 * 1000

            raw_15m = fetch_ohlcv_range(exchange, symbol, cfg.TIMEFRAME_PRIMARY, since_15m, until_ms)
            raw_1h  = fetch_ohlcv_range(exchange, symbol, cfg.TIMEFRAME_CONFIRM, since_1h, until_ms)
            candles_15m = ohlcv_to_dicts(raw_15m)
            candles_1h  = ohlcv_to_dicts(raw_1h)

            eval_start_ms = until_ms - cfg.MISS_HUNTER_LOOKBACK_DAYS * 86400 * 1000
            eval_start_idx = next((i for i, c in enumerate(candles_15m)
                                   if c["ts"] >= eval_start_ms and i >= cfg.CANDLES_PRIMARY), None)
            if eval_start_idx is None:
                log(f"  [{n}/{len(symbols)}] {symbol}: insufficient history, skipped")
                continue

            pumps = hunt_symbol(symbol, candles_15m, candles_1h, btc_15m, btc_ts, eval_start_idx)
            all_pumps.extend(pumps)
            log(f"  [{n}/{len(symbols)}] {symbol}: {len(pumps)} pump(s) found")
        except Exception as e:
            log(f"  [{n}/{len(symbols)}] {symbol}: ⚠️  hunt failed: {e}")
            continue

    agg = aggregate(all_pumps)
    suggestions = suggest_adjustments(all_pumps)
    report = build_report(all_pumps, agg, suggestions, len(symbols))

    print(report)

    report_path = "state/miss_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    if apply_mode:
        applied = apply_suggestions(suggestions)
        if applied:
            print("\n--- Applied changes ---")
            for a in applied:
                print(f"  {a}")
        else:
            print("\nNo changes met the confidence bar this run.")

    log(f"✅ Miss hunt complete — {agg['total']} pumps analyzed, "
        f"{agg['either_caught']} caught by either pipeline, {len(suggestions)} suggestion(s)")


if __name__ == "__main__":
    main()
