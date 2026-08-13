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
  - News               : public RSS feeds from major crypto outlets

News used to run on CryptoCompare's min-api news endpoint, but as of
2026-08 it returns HTTP 401 "API key required" — that provider locked its
free tier behind registration. Switched to RSS (CoinDesk, Cointelegraph,
Decrypt, CryptoSlate) since that's genuinely keyless by design and needs
no new dependency (stdlib XML parsing only).

This is deliberately simple keyword matching, not NLP — it's a blunt
"is there an obvious red/green flag headline" filter, not a sentiment model.
"""

import time
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FNG_URL         = "https://api.alternative.me/fng/?limit=1"
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://cryptoslate.com/feed/",
]
REQUEST_TIMEOUT = 10
# Some APIs bot-block the bare `requests` default User-Agent; this is a
# cheap, safe defensive header regardless of root cause.
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PreBreakoutScanner/1.0)"}

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
        resp = requests.get(FNG_URL, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()["data"][0]
        return {"value": int(data["value"]), "classification": data["value_classification"]}
    except Exception as e:
        print(f"[news.py] fetch_fear_greed failed: {type(e).__name__}: {e}")
        return None


def _parse_rss_date(date_str: str) -> int:
    """Parses an RSS pubDate (RFC 822, e.g. 'Wed, 12 Aug 2026 18:00:00 GMT') to epoch seconds."""
    if not date_str:
        return 0
    try:
        dt = parsedate_to_datetime(date_str)
        return int(dt.timestamp())
    except Exception:
        return 0


def _fetch_rss_feed(url: str, limit: int) -> list:
    """Fetches and parses one RSS feed into the shared news-item shape.
    Namespace-agnostic <item> lookup so this works whether or not the feed
    declares extra XML namespaces (most crypto-news RSS feeds do)."""
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for el in root.iter():
            if el.tag.split("}")[-1] != "item":
                continue
            title = (el.findtext("title") or "").strip()
            link = (el.findtext("link") or "").strip()
            pub_date = el.findtext("pubDate") or ""
            categories = ",".join(c.text for c in el.findall("category") if c.text)
            items.append({
                "title":        title,
                "body":         "",
                "categories":   categories,
                "published_on": _parse_rss_date(pub_date),
                "url":          link,
            })
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        print(f"[news.py] RSS fetch failed for {url}: {type(e).__name__}: {e}")
        return []


def fetch_latest_news(limit: int = 50) -> list:
    """
    Aggregates recent crypto news across RSS_FEEDS into the shared shape:
    {'title','body','categories','published_on','url'}, newest first.
    Returns [] only if every feed failed — logs each feed's failure via
    _fetch_rss_feed so a total outage is diagnosable, not silent.
    """
    per_feed = max(5, limit // len(RSS_FEEDS))
    all_items = []
    for feed_url in RSS_FEEDS:
        all_items.extend(_fetch_rss_feed(feed_url, per_feed))
    all_items.sort(key=lambda x: x["published_on"], reverse=True)
    if not all_items:
        print("[news.py] All RSS feeds returned 0 items this cycle")
    return all_items[:limit]


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


def match_symbols_to_news(symbols: list, news_items: list, max_age_hours: int) -> dict:
    """
    Scans news_items for POSITIVE-keyword headlines mentioning any of the
    given symbols' base tickers within max_age_hours. This is what powers
    the news-catalyst alert path: news as the trigger, not just a filter.

    Returns {base_symbol: {"headline", "url", "published_on"}} — first
    (most recent, since CryptoCompare returns newest-first) positive match
    per symbol.
    """
    cutoff = time.time() - max_age_hours * 3600
    bases = {s.split("/")[0] for s in symbols}
    matches = {}
    for item in news_items:
        if item["published_on"] < cutoff:
            continue
        blob = f"{item['title']} {item.get('categories', '')}"
        low = blob.lower()
        if not any(kw in low for kw in POSITIVE_KEYWORDS):
            continue
        for base in bases:
            if base in matches:
                continue
            if _mentions_coin(blob, base):
                matches[base] = {
                    "headline": item["title"],
                    "url": item.get("url"),
                    "published_on": item["published_on"],
                }
    return matches


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
