"""
Pre-Breakout Scanner — News & Market Sentiment
================================================
Lightweight, keyless news/sentiment layer. Goals:

  1. Don't fire a "pre-breakout" long into a coin that just got hit with a
     hack / delisting / lawsuit headline (the price action can look exactly
     like a bullish volume spike while it's actually a dump).
  2. Gauge overall market mood the way a discretionary desk would before
     sizing a long — via the Fear & Greed Index.
  3. Pause new signal generation entirely during acute market-wide bad news
     (exchange collapse, regulatory crackdown, flash crash).

No API keys required:
  - Fear & Greed Index : alternative.me
  - News               : CryptoCompare public news endpoint

This is deliberately simple keyword matching, not NLP — it's a blunt
"is there an obvious red/green flag headline" filter, not a sentiment model.
"""

import time
import requests

FNG_URL         = "https://api.alternative.me/fng/?limit=1"
NEWS_URL        = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
REQUEST_TIMEOUT = 10

NEGATIVE_KEYWORDS = [
    "hack", "hacked", "exploit", "exploited", "drain", "drained", "rug pull",
    "rugpull", "lawsuit", "sued", "sec charges", "charged", "fraud",
    "delist", "delisting", "insolvent", "insolvency", "bankrupt", "bankruptcy",
    "halts withdrawals", "pauses withdrawals", "investigation", "banned",
    "security breach", "vulnerability", "compromised", "scam",
]

POSITIVE_KEYWORDS = [
    "partnership", "integrates", "integration", "listed on", "listing",
    "mainnet launch", "upgrade", "adoption", "etf approval", "approved",
    "institutional inflow", "buyback", "token burn", "airdrop",
]

MARKET_WIDE_NEGATIVE_KEYWORDS = [
    "market crash", "flash crash", "sec sues", "sec charges", "doj charges",
    "exchange hack", "exchange collapse", "contagion", "bank run",
    "stablecoin depeg", "regulatory crackdown", "trading halt",
]


def fetch_fear_greed() -> dict | None:
    """Returns {'value': int 0-100, 'classification': str} or None on failure."""
    try:
        resp = requests.get(FNG_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()["data"][0]
        return {"value": int(data["value"]), "classification": data["value_classification"]}
    except Exception:
        return None


def fetch_latest_news(limit: int = 50) -> list:
    """Returns a list of {'title','body','categories','published_on','url'}, or [] on failure."""
    try:
        resp = requests.get(NEWS_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        items = resp.json().get("Data", [])[:limit]
        return [
            {
                "title":        it.get("title", ""),
                "body":         it.get("body", ""),
                "categories":   it.get("categories", ""),
                "published_on": it.get("published_on", 0),
                "url":          it.get("url", ""),
            }
            for it in items
        ]
    except Exception:
        return []


def _mentions_coin(text: str, base_symbol: str) -> bool:
    """Rough word-boundary match on the ticker. Heuristic, not exact NLP —
    can false-positive on tickers that are also common words (e.g. 'FLOW')."""
    text_low = f" {text.lower()} "
    return f" {base_symbol.lower()} " in text_low


def check_coin_news(base_symbol: str, news_items: list, max_age_hours: int) -> dict:
    """
    Scans already-fetched news_items for anything mentioning this coin's
    ticker within the last `max_age_hours`.
    Returns dict: negative (bool), positive (bool), headline (str|None)
    """
    cutoff = time.time() - max_age_hours * 3600
    negative = positive = False
    headline = None

    for item in news_items:
        if item["published_on"] < cutoff:
            continue
        blob = f"{item['title']} {item.get('categories', '')}"
        if not _mentions_coin(blob, base_symbol):
            continue
        low = blob.lower()
        if any(kw in low for kw in NEGATIVE_KEYWORDS):
            return {"negative": True, "positive": False, "headline": item["title"]}
        if any(kw in low for kw in POSITIVE_KEYWORDS) and headline is None:
            positive = True
            headline = item["title"]

    return {"negative": negative, "positive": positive, "headline": headline}


def check_market_wide_news(news_items: list, max_age_hours: int) -> dict:
    """
    Looks for high-impact, market-wide negative headlines (not coin-specific).
    Returns dict: risk_off (bool), headline (str|None)
    """
    cutoff = time.time() - max_age_hours * 3600
    for item in news_items:
        if item["published_on"] < cutoff:
            continue
        low = f"{item['title']} {item.get('categories', '')}".lower()
        if any(kw in low for kw in MARKET_WIDE_NEGATIVE_KEYWORDS):
            return {"risk_off": True, "headline": item["title"]}
    return {"risk_off": False, "headline": None}
