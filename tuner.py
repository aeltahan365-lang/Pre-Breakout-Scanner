"""
Pre-Breakout Scanner — Self-Tuning Analysis
==============================================
Reads state/trade_log.jsonl (fed by both the live scanner and backtest.py)
and answers: "which of our signals actually predict wins, and is our
threshold in the right place?"

Design principles, deliberately conservative:
  - A component's win-rate delta is only trusted once BOTH the "present"
    and "absent" groups have >= TUNER_MIN_SAMPLE_SIZE resolved trades.
    Below that, sample noise dominates and any suggestion would be a guess
    dressed up as data.
  - Any single tuning pass caps a weight change at +/-TUNER_MAX_WEIGHT_NUDGE
    (default 20%). This is a nudge toward the data, not a full re-optimization
    — it takes several runs to substantially reshape the weight profile,
    which is intentional (avoids overfitting to one noisy week).
  - This script never pushes to config.py directly. --apply writes the
    change into config.py's text (for the CI workflow to diff and open a
    PR from) — a human still approves before it goes live, because this
    controls real trading alerts.

Run manually:  python tuner.py            (report only, no changes)
               python tuner.py --apply     (writes suggested changes into config.py)
"""

import os
import re
import sys

import config as cfg
from engine import load_trade_log, COMPONENT_WEIGHT_MAP, COMPONENT_WEIGHT_MAP_REVERSAL

WIN_OUTCOMES = {"tp1_hit", "tp2_hit"}
LOSS_OUTCOMES = {"sl_hit"}
# "expired" trades are excluded from win-rate math (neither won nor lost
# against a level) but counted in the report for transparency.


def _win_rate(trades: list) -> tuple:
    wins = sum(1 for t in trades if t["outcome"] in WIN_OUTCOMES)
    losses = sum(1 for t in trades if t["outcome"] in LOSS_OUTCOMES)
    decided = wins + losses
    return (wins / decided if decided else None), decided, wins, losses


def analyze_components(resolved: list, component_map: dict = COMPONENT_WEIGHT_MAP) -> list:
    """
    For each component in `component_map` (COMPONENT_WEIGHT_MAP for the
    breakout pipeline, COMPONENT_WEIGHT_MAP_REVERSAL for the reversal
    pipeline — they score different signals, so must be analyzed
    separately), splits resolved trades into "present" vs "absent" groups
    and computes the win-rate delta.
    Returns a list of dicts, one per component with enough data to trust.
    """
    findings = []
    for component, (weight_attr, direction) in component_map.items():
        with_true  = [t for t in resolved if t.get("components", {}).get(component) is True]
        with_false = [t for t in resolved if t.get("components", {}).get(component) is False]

        wr_true,  n_true,  _, _  = _win_rate(with_true)
        wr_false, n_false, _, _  = _win_rate(with_false)

        if wr_true is None or wr_false is None or n_true < cfg.TUNER_MIN_SAMPLE_SIZE or n_false < cfg.TUNER_MIN_SAMPLE_SIZE:
            findings.append({
                "component": component, "weight_attr": weight_attr, "direction": direction,
                "trusted": False, "n_true": n_true, "n_false": n_false,
                "wr_true": wr_true, "wr_false": wr_false,
            })
            continue

        delta = wr_true - wr_false                     # positive = "present" wins more often
        effective = delta if direction > 0 else -delta   # for penalties, "confirmed bad" = positive effective

        nudge = max(-cfg.TUNER_MAX_WEIGHT_NUDGE, min(cfg.TUNER_MAX_WEIGHT_NUDGE, effective * 0.6))
        current_weight = getattr(cfg, weight_attr, None)
        new_weight = None
        if current_weight is not None and abs(nudge) >= 0.02:   # ignore sub-2% noise-level nudges
            new_weight = max(1, round(current_weight * (1 + nudge)))
            if new_weight == current_weight:
                new_weight = None

        findings.append({
            "component": component, "weight_attr": weight_attr, "direction": direction,
            "trusted": True, "n_true": n_true, "n_false": n_false,
            "wr_true": round(wr_true * 100, 1), "wr_false": round(wr_false * 100, 1),
            "delta_pp": round(delta * 100, 1), "nudge_pct": round(nudge * 100, 1),
            "current_weight": current_weight, "suggested_weight": new_weight,
        })
    return findings


def sweep_thresholds(resolved: list, sweep_values: list = None) -> list:
    # Only trades with a numeric composite score are relevant here — e.g.
    # news-catalyst trades (components={"news_catalyst": True}) don't go
    # through build_score and are logged with score=None.
    sweep_values = sweep_values if sweep_values is not None else cfg.TUNER_THRESHOLD_SWEEP
    scored = [t for t in resolved if isinstance(t.get("score"), (int, float))]
    rows = []
    for th in sweep_values:
        subset = [t for t in scored if t["score"] >= th]
        wr, n, wins, losses = _win_rate(subset)
        rows.append({"threshold": th, "n": n, "win_rate": round(wr * 100, 1) if wr is not None else None,
                    "wins": wins, "losses": losses})
    return rows


def suggest_threshold(sweep: list, current: int) -> int | None:
    """Only recommends a change if a higher-or-equal-count threshold shows a
    meaningfully better (>=5pp) win rate with enough sample size — otherwise
    leaves SCORE_THRESHOLD alone."""
    current_row = next((r for r in sweep if r["threshold"] == current), None)
    if not current_row or current_row["win_rate"] is None:
        return None
    best = current_row
    for r in sweep:
        if r["n"] >= cfg.TUNER_MIN_SAMPLE_SIZE and r["win_rate"] is not None and r["win_rate"] > best["win_rate"] + 5:
            best = r
    return best["threshold"] if best["threshold"] != current else None


def _component_table(component_findings: list) -> list:
    lines = ["| Component | Weight | With | Without | Δ (pp) | Suggested |", "|---|---|---|---|---|---|"]
    for f in component_findings:
        if not f["trusted"]:
            lines.append(f"| {f['component']} | {f['weight_attr']} | n={f['n_true']} | n={f['n_false']} | "
                         f"*insufficient data (need {cfg.TUNER_MIN_SAMPLE_SIZE}+ each)* | — |")
        else:
            sug = f"{f['current_weight']} → **{f['suggested_weight']}**" if f["suggested_weight"] is not None else f"{f['current_weight']} (no change)"
            lines.append(f"| {f['component']} | {f['weight_attr']} | {f['wr_true']}% (n={f['n_true']}) | "
                         f"{f['wr_false']}% (n={f['n_false']}) | {f['delta_pp']:+.1f} | {sug} |")
    return lines


def _threshold_table(sweep: list, current: int, suggested) -> list:
    lines = ["| Threshold | Trades | Win Rate |", "|---|---|---|"]
    for r in sweep:
        marker = " ← current" if r["threshold"] == current else ""
        marker += " ← suggested" if r["threshold"] == suggested else ""
        lines.append(f"| {r['threshold']} | {r['n']} | {r['win_rate']}%{marker} |" if r["win_rate"] is not None
                    else f"| {r['threshold']} | {r['n']} | n/a |")
    return lines


def build_report(all_trades: list, resolved_all: list,
                 resolved_breakout: list, breakout_findings: list, breakout_sweep: list, breakout_suggested,
                 resolved_reversal: list, reversal_findings: list, reversal_sweep: list, reversal_suggested) -> str:
    wr, n, wins, losses = _win_rate(resolved_all)
    expired = sum(1 for t in all_trades if t["outcome"] == "expired")
    live_n = sum(1 for t in all_trades if t.get("source") == "live")
    bt_n = sum(1 for t in all_trades if t.get("source") == "backtest")

    wr_b, n_b, wins_b, losses_b = _win_rate(resolved_breakout)
    wr_r, n_r, wins_r, losses_r = _win_rate(resolved_reversal)

    lines = [
        "# Self-Tuning Report",
        "",
        f"Trade log: {len(all_trades)} total ({live_n} live, {bt_n} backtest) — "
        f"{n} decided (win/loss), {expired} expired/inconclusive.",
        f"Overall win rate: **{round(wr*100,1) if wr is not None else 'n/a'}%** ({wins}W / {losses}L)",
        f"  - 🚀 Breakout (secondary): {round(wr_b*100,1) if wr_b is not None else 'n/a'}% ({wins_b}W / {losses_b}L)",
        f"  - 🔄 Reversal (primary): {round(wr_r*100,1) if wr_r is not None else 'n/a'}% ({wins_r}W / {losses_r}L)",
        "",
        "## 🚀 Breakout Pipeline — Per-Signal Win-Rate Analysis",
        "",
    ] + _component_table(breakout_findings) + [
        "", "### Breakout Score Threshold Sweep", "",
    ] + _threshold_table(breakout_sweep, cfg.SCORE_THRESHOLD, breakout_suggested)

    if breakout_suggested and breakout_suggested != cfg.SCORE_THRESHOLD:
        lines += ["", f"**Suggested SCORE_THRESHOLD: {cfg.SCORE_THRESHOLD} → {breakout_suggested}** "
                     f"(>=5pp win-rate improvement with sufficient sample size)."]

    lines += [
        "",
        "## 🔄 Reversal Pipeline — Per-Signal Win-Rate Analysis",
        "",
    ] + _component_table(reversal_findings) + [
        "", "### Reversal Score Threshold Sweep", "",
    ] + _threshold_table(reversal_sweep, cfg.REVERSAL_SCORE_THRESHOLD, reversal_suggested)

    if reversal_suggested and reversal_suggested != cfg.REVERSAL_SCORE_THRESHOLD:
        lines += ["", f"**Suggested REVERSAL_SCORE_THRESHOLD: {cfg.REVERSAL_SCORE_THRESHOLD} → {reversal_suggested}** "
                     f"(>=5pp win-rate improvement with sufficient sample size)."]

    lines += [
        "",
        "_Note: backtest trades don't replay the live-only microstructure gates "
        "(taker buy/sell ratio, order book, cross-exchange validation, derivatives "
        "positioning), so this is directionally useful, not an exact simulation of "
        "live alerts. News-catalyst trades are excluded from both pipelines' "
        "component tables (they don't go through build_score / build_reversal_score) "
        "but are counted in the overall total above._",
    ]
    return "\n".join(lines)


def _set_config_value(content: str, attr: str, new_value) -> str:
    """Replaces ATTR = <value> [# comment] with the new value, preserving any
    trailing comment and a readable gap before it."""
    pattern = rf"^({re.escape(attr)}\s*=\s*)[^\n#]+?(\s*)((?:#.*)?)$"

    def _replace(m):
        prefix, _, comment = m.group(1), m.group(2), m.group(3)
        return f"{prefix}{new_value}   {comment}" if comment else f"{prefix}{new_value}"

    new_content, count = re.subn(pattern, _replace, content, count=1, flags=re.MULTILINE)
    return new_content if count else content


def apply_changes(breakout_findings: list, breakout_suggested,
                  reversal_findings: list, reversal_suggested,
                  config_path: str = "config.py") -> list:
    """Writes suggested weight/threshold changes into config.py's text. Returns list of applied changes."""
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    applied = []
    for f in breakout_findings + reversal_findings:
        if f.get("trusted") and f.get("suggested_weight") is not None:
            content = _set_config_value(content, f["weight_attr"], f["suggested_weight"])
            applied.append(f"{f['weight_attr']}: {f['current_weight']} -> {f['suggested_weight']}")

    if breakout_suggested and breakout_suggested != cfg.SCORE_THRESHOLD:
        content = _set_config_value(content, "SCORE_THRESHOLD", breakout_suggested)
        applied.append(f"SCORE_THRESHOLD: {cfg.SCORE_THRESHOLD} -> {breakout_suggested}")

    if reversal_suggested and reversal_suggested != cfg.REVERSAL_SCORE_THRESHOLD:
        content = _set_config_value(content, "REVERSAL_SCORE_THRESHOLD", reversal_suggested)
        applied.append(f"REVERSAL_SCORE_THRESHOLD: {cfg.REVERSAL_SCORE_THRESHOLD} -> {reversal_suggested}")

    if applied:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
    return applied


def main():
    apply_mode = "--apply" in sys.argv

    all_trades = load_trade_log()
    resolved_all = [t for t in all_trades if t.get("outcome") in WIN_OUTCOMES | LOSS_OUTCOMES]

    if len(resolved_all) < cfg.TUNER_MIN_SAMPLE_SIZE:
        print(f"Only {len(resolved_all)} decided trades in the log (need {cfg.TUNER_MIN_SAMPLE_SIZE}+ for any "
              f"trustworthy analysis) — run backtest.py first, or wait for more live results. No changes made.")
        return

    # Old trade-log entries predate the reversal pipeline and carry no
    # "pipeline" field — treat those as "breakout" (the only pipeline that
    # existed then). News-catalyst trades are excluded from both component
    # analyses (different scoring path entirely) but stay in resolved_all
    # for the overall win-rate stat.
    resolved_breakout = [t for t in resolved_all if t.get("pipeline", "breakout") == "breakout"]
    resolved_reversal = [t for t in resolved_all if t.get("pipeline") == "reversal"]

    breakout_findings = analyze_components(resolved_breakout, COMPONENT_WEIGHT_MAP)
    breakout_sweep = sweep_thresholds(resolved_breakout)
    breakout_suggested = suggest_threshold(breakout_sweep, cfg.SCORE_THRESHOLD)

    reversal_findings = analyze_components(resolved_reversal, COMPONENT_WEIGHT_MAP_REVERSAL)
    reversal_sweep = sweep_thresholds(resolved_reversal)
    reversal_suggested = suggest_threshold(reversal_sweep, cfg.REVERSAL_SCORE_THRESHOLD)

    report = build_report(all_trades, resolved_all,
                          resolved_breakout, breakout_findings, breakout_sweep, breakout_suggested,
                          resolved_reversal, reversal_findings, reversal_sweep, reversal_suggested)

    print(report)

    report_path = "state/tuning_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    if apply_mode:
        applied = apply_changes(breakout_findings, breakout_suggested, reversal_findings, reversal_suggested)
        if applied:
            print("\n--- Applied changes ---")
            for a in applied:
                print(f"  {a}")
        else:
            print("\nNo changes met the confidence/threshold bar this run.")


if __name__ == "__main__":
    main()
