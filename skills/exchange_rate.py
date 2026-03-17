"""
exchange_rate.py — שערי מטבע חיים עם cache לשעה
"""

import json
import time
from pathlib import Path

try:
    import requests
    _requests_ok = True
except ImportError:
    _requests_ok = False

CACHE_FILE = Path(__file__).parent.parent / "data" / "exchange_rates_cache.json"
CACHE_TTL  = 3600  # שעה אחת בשניות

# שערים לגיבוי (נכון בערך למרץ 2026)
_FALLBACK_RATES = {"EUR": 3.78, "USD": 3.52, "GBP": 4.48, "CNY": 0.49, "GBP": 4.48}


def get_exchange_rate(currency: str) -> dict:
    """
    מחזיר שער המרה של מטבע לשקל (ILS).
    תומך ב: EUR, USD, GBP, CNY ועוד.
    מחזיר: {"currency": "EUR", "rate": 3.59, "updated": "2026-03-14 22:00"}
    """
    currency = currency.upper().strip()

    # 1. בדוק cache
    cached = _load_cache()
    if cached and currency in cached:
        entry = cached[currency]
        if time.time() - entry.get("timestamp", 0) < CACHE_TTL:
            return {
                "currency": currency,
                "rate":     entry["rate"],
                "updated":  entry["updated"],
                "source":   "cache",
            }

    # 2. שלוף שער חי
    if not _requests_ok:
        rate = _FALLBACK_RATES.get(currency)
        return {"currency": currency, "rate": rate, "updated": "offline", "source": "fallback"}

    try:
        resp = requests.get(
            "https://api.exchangerate-api.com/v4/latest/ILS",
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()

        rates_from_ils = data.get("rates", {})
        if currency not in rates_from_ils:
            return {"currency": currency, "rate": None, "error": f"מטבע {currency} לא נמצא"}

        ils_to_cur = rates_from_ils[currency]
        rate = round(1 / ils_to_cur, 4) if ils_to_cur else None

        from datetime import datetime
        updated = datetime.now().strftime("%Y-%m-%d %H:%M")

        # עדכן cache
        if not cached:
            cached = {}
        cached[currency] = {"rate": rate, "updated": updated, "timestamp": time.time()}
        _save_cache(cached)

        return {"currency": currency, "rate": rate, "updated": updated, "source": "live"}

    except Exception as e:
        rate = _FALLBACK_RATES.get(currency)
        return {
            "currency": currency,
            "rate":     rate,
            "updated":  "offline",
            "error":    str(e),
            "source":   "fallback",
        }


def get_multiple_rates(currencies: list) -> dict:
    """שולף שערים של מספר מטבעות"""
    return {cur: get_exchange_rate(cur) for cur in currencies}


def format_rate(info: dict) -> str:
    """פורמט לתצוגה: '1 EUR = 3.78 ₪ (עדכון: 2026-03-14 22:00)'"""
    cur = info.get("currency", "")
    rate = info.get("rate")
    if rate is None:
        return f"שגיאה: {info.get('error', 'שגיאה לא ידועה')}"
    src = "🔴 offline" if info.get("source") == "fallback" else "🟢 live" if info.get("source") == "live" else "🟡 cache"
    return f"1 {cur} = {rate} ₪  ({src}, עדכון: {info.get('updated','')})"


# --- עזר ---

def _load_cache() -> dict:
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
