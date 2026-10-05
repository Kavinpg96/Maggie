"""Small NSE/BSE watchlist and source-timestamped intraday market snapshots."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import statistics
import tempfile
from zoneinfo import ZoneInfo

import requests

_WATCHLIST_PATH = Path.home() / ".local" / "share" / "maggie_ai" / "market_watchlist.json"
_MAX_SYMBOLS = 4
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9&_-]{0,19}\.(?:NS|BO)$")
_INDEX_SYMBOLS = {"^NSEI", "^BSESN"}
_DEFAULT_SYMBOLS = ["^NSEI", "^BSESN"]
_INDIA_TZ = ZoneInfo("Asia/Kolkata")
_USER_AGENT = "Maggie-AI/1.0 (market dashboard)"


def normalize_symbols(value) -> list[str]:
    """Normalize user-entered NSE/BSE tickers, defaulting unsuffixed names to NSE."""
    if isinstance(value, str):
        candidates = value.split(",")
    elif isinstance(value, list):
        candidates = value
    else:
        raise ValueError("Enter stock symbols separated by commas.")

    symbols = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            raise ValueError("Each stock symbol must be text.")
        symbol = candidate.strip().upper().replace(" ", "")
        if not symbol:
            continue
        if symbol not in _INDEX_SYMBOLS:
            if "." not in symbol:
                symbol += ".NS"
        if symbol not in _INDEX_SYMBOLS and not _SYMBOL_PATTERN.fullmatch(symbol):
            raise ValueError(
                f"Invalid symbol {candidate.strip()!r}; use an NSE .NS or BSE .BO "
                "symbol, or ^NSEI/^BSESN for the major indices."
            )
        if symbol not in symbols:
            symbols.append(symbol)
    if len(symbols) > _MAX_SYMBOLS:
        raise ValueError(f"Track at most {_MAX_SYMBOLS} symbols to limit feed requests.")
    return symbols


def get_watchlist() -> list[str]:
    if not _WATCHLIST_PATH.exists():
        return list(_DEFAULT_SYMBOLS)
    try:
        data = json.loads(_WATCHLIST_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("The saved market watchlist is not a list.")
        return normalize_symbols(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Could not read the market watchlist: {exc}") from exc


def set_watchlist(symbols) -> list[str]:
    normalized = normalize_symbols(symbols)
    _WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix=".market-watchlist-", dir=_WATCHLIST_PATH.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as watchlist_file:
            json.dump(normalized, watchlist_file)
            watchlist_file.flush()
            os.fsync(watchlist_file.fileno())
        os.replace(temporary_path, _WATCHLIST_PATH)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise
    return normalized


def _fetch_symbol(symbol: str) -> dict:
    response = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": "1d", "interval": "1m"},
        headers={"User-Agent": _USER_AGENT},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json().get("chart", {})
    if payload.get("error"):
        raise RuntimeError(str(payload["error"].get("description", "Quote unavailable")))
    results = payload.get("result") or []
    if not results:
        raise RuntimeError("No intraday quote data was returned.")

    chart = results[0]
    quote = (chart.get("indicators", {}).get("quote") or [{}])[0]
    timestamps = chart.get("timestamp") or []
    closes = quote.get("close") or []
    samples = [
        (int(timestamp), float(close))
        for timestamp, close in zip(timestamps, closes)
        if close is not None and math.isfinite(float(close))
    ]
    if not samples:
        raise RuntimeError("No valid intraday prices were returned.")

    recent = samples[-40:]
    x_values = [(timestamp - recent[0][0]) / 60.0 for timestamp, _ in recent]
    y_values = [price for _, price in recent]
    x_mean = statistics.fmean(x_values)
    y_mean = statistics.fmean(y_values)
    variance = sum((x - x_mean) ** 2 for x in x_values)
    slope = (
        sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        / variance
        if len(recent) >= 3 and variance
        else 0.0
    )
    last_timestamp, last_price = samples[-1]
    projection = max(0.0, last_price + slope * 5)
    projection_change_pct = (
        (projection - last_price) / last_price * 100 if last_price else 0.0
    )
    previous_close = chart.get("meta", {}).get("previousClose")
    if previous_close is None:
        previous_close = chart.get("meta", {}).get("chartPreviousClose")
    change_pct = (
        (last_price - float(previous_close)) / float(previous_close) * 100
        if previous_close
        else None
    )

    return {
        "symbol": symbol,
        "name": chart.get("meta", {}).get("longName")
        or chart.get("meta", {}).get("shortName")
        or symbol,
        "exchange": chart.get("meta", {}).get("fullExchangeName") or "NSE/BSE",
        "currency": chart.get("meta", {}).get("currency") or "INR",
        "price": last_price,
        "change_pct": change_pct,
        "quote_timestamp": datetime.fromtimestamp(
            last_timestamp, _INDIA_TZ
        ).isoformat(),
        "history": [
            {
                "timestamp": datetime.fromtimestamp(timestamp, _INDIA_TZ).isoformat(),
                "price": price,
            }
            for timestamp, price in recent
        ],
        "projection_price_5m": projection,
        "projection_change_pct_5m": projection_change_pct,
        "trend": (
            "up"
            if projection_change_pct > 0.05
            else "down"
            if projection_change_pct < -0.05
            else "sideways"
        ),
        "source": "Yahoo Finance chart feed",
        "interval": "1 minute",
    }


def get_market_snapshot(symbols=None) -> dict:
    symbols = normalize_symbols(get_watchlist() if symbols is None else symbols)
    items = []
    with ThreadPoolExecutor(max_workers=min(len(symbols), 4) or 1) as executor:
        futures = {
            executor.submit(_fetch_symbol, symbol): symbol for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                items.append(future.result())
            except (
                requests.RequestException,
                RuntimeError,
                TypeError,
                ValueError,
                KeyError,
            ) as exc:
                items.append({"symbol": symbol, "error": str(exc)})
    items.sort(key=lambda item: symbols.index(item["symbol"]))
    return {
        "updated_at": datetime.now(_INDIA_TZ).isoformat(),
        "symbols": symbols,
        "items": items,
        "refresh_seconds": 10,
        "quote_interval": "1 minute",
    }
