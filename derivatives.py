"""
Pre-Breakout Scanner — Derivatives Positioning (free on-chain-style proxy)
=============================================================================
True per-altcoin on-chain data (exchange netflows, whale wallets, active
addresses) needs a paid provider (Glassnode/CryptoQuant/Nansen/Santiment) —
none of those keys exist in this repo. Perpetual futures funding rate and
open interest are the free, keyless equivalent a discretionary desk actually
watches for "smart money" positioning: they move on the same crowd
psychology on-chain exchange-flow data is trying to capture, just measured
through the derivatives market instead of the blockchain.

  funding_rate negative  -> shorts are paying longs -> shorts are crowded
                             and over-leveraged -> classic short-squeeze fuel
                             right at a base/bottom
  open interest falling  -> leveraged positions are being closed/liquidated
                             into the decline -> weak hands flushed out,
                             a healthier base to reverse from than one where
                             OI kept climbing (= more leverage still stacked,
                             more room for another flush)

Live-only: like taker buy/sell ratio and order book imbalance, this needs a
fresh network call and has no free historical endpoint to replay against —
so it's an optional bonus in the live scanner only, applied after a symbol
has already passed the OHLCV-only reversal gate (keeps the extra API calls
bounded to genuinely interesting candidates). It is never a hard gate — a
symbol simply not listed on futures loses the bonus, not the signal.
"""


def get_derivatives_context(futures_exchange, symbol: str) -> dict | None:
    """
    `symbol` is the spot ccxt symbol, e.g. 'XYZ/USDT'. Maps to the USDT-M
    perpetual unified symbol ('XYZ/USDT:USDT') and pulls funding rate +
    open interest, best-effort. Returns None if the pair isn't listed on
    the futures market, or every call fails — never raises.
    """
    if futures_exchange is None:
        return None

    base = symbol.split("/")[0]
    fut_symbol = f"{base}/USDT:USDT"
    try:
        if fut_symbol not in futures_exchange.markets:
            return None
    except Exception:
        return None

    funding_rate = None
    try:
        fr = futures_exchange.fetch_funding_rate(fut_symbol)
        funding_rate = fr.get("fundingRate")
    except Exception:
        pass

    open_interest = None
    try:
        oi = futures_exchange.fetch_open_interest(fut_symbol)
        open_interest = oi.get("openInterestAmount") or oi.get("openInterestValue")
    except Exception:
        pass

    if funding_rate is None and open_interest is None:
        return None

    return {
        "funding_rate":  funding_rate,
        "open_interest": open_interest,
        # No free historical open-interest endpoint to diff against yet —
        # reserved for when/if one becomes available. Never fabricated.
        "oi_change_pct": None,
    }
